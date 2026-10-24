"""Offline first-start composition across independent API/Agents app packages.

Only SQL doubles, ASGI and explicitly mocked HTTP are used. Test credentials
are public dummy strings. A controlled test policy is not writer exclusion.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
MAX_FRAME = 12 * 1024 * 1024
EXCHANGE_SECONDS = 30
SCENARIOS = ("normal", "zero_budget", "query_unknown", "admission_ACK", "publication_ACK", "response_lost")
API_TOKEN = "test-only-start-composition-user-token-not-live"
WRITE_TOKEN = "test-only-start-composition-write-token-not-live"
READ_TOKEN = "test-only-start-composition-read-token-not-live"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)


def sha(raw): return hashlib.sha256(raw).hexdigest()
def digest(value): return sha(canonical(value).encode("utf-8"))


class ProbeFailure(RuntimeError): pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ProbeFailure("duplicate frame key")
        result[key] = value
    return result


def frame_json(raw):
    if not raw or len(raw) > MAX_FRAME or not raw.endswith(b"\n"):
        raise ProbeFailure("EOF, partial or oversized frame")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                       parse_constant=lambda _: (_ for _ in ()).throw(ProbeFailure("nonfinite frame")))
    if type(value) is not dict or "probe_error" in value:
        raise ProbeFailure("invalid child frame")
    return value


def process_identity(process):
    """Read creation identity through the actual retained Popen OS handle."""
    if os.name != "nt":
        # Popen's retained handle remains the signal target on other hosts.
        return {"pid": process.pid, "popen_identity": id(process)}
    import ctypes
    from ctypes import wintypes
    times = [wintypes.FILETIME() for _ in range(4)]
    get_times = ctypes.WinDLL("kernel32", use_last_error=True).GetProcessTimes
    get_times.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    get_times.restype = wintypes.BOOL
    if not get_times(wintypes.HANDLE(int(process._handle)), *(ctypes.byref(t) for t in times)):
        raise ProbeFailure("owned process creation identity unavailable")
    return {"pid": process.pid, "created_filetime": (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime}


class OwnedAgentChannel:
    """One terminal-on-failure channel; never restart or replay a request."""
    def __init__(self, *, scenario="normal", command=None, timeout=EXCHANGE_SECONDS):
        if scenario not in SCENARIOS or type(timeout) not in {int, float} or not 0 < timeout <= EXCHANGE_SECONDS:
            raise ProbeFailure("explicit scenario and finite positive timeout<=30 required")
        self.command = command or [sys.executable, "-B", str(Path(__file__).resolve()), "--agents", "--scenario", scenario]
        self.timeout, self.process, self.identity, self.exchanges = timeout, None, None, 0
        self._stderr, self._failed, self._lock = None, False, asyncio.Lock()

    async def start(self):
        if self.process is not None or self._failed: raise ProbeFailure("channel already used")
        self._stderr = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(self.command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self._stderr, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.identity = process_identity(self.process)
            return await self.exchange({"op": "ready"})
        except BaseException:
            await self.close()
            raise

    async def exchange(self, value):
        async with self._lock:
            try:
                if self._failed or self.process is None: raise ProbeFailure("failed channel; replay forbidden")
                frame = (canonical(value) + "\n").encode("utf-8")
                if len(frame) > MAX_FRAME: raise ProbeFailure("oversized request frame")
                self.exchanges += 1
                def write_read():
                    self.process.stdin.write(frame); self.process.stdin.flush()
                    return self.process.stdout.readline(MAX_FRAME + 1)
                raw = await asyncio.wait_for(asyncio.to_thread(write_read), self.timeout)
                return frame_json(raw)
            except BaseException:
                self._failed = True
                await self.close()
                raise

    async def close(self):
        self._failed = True
        if self.process is not None:
            process = self.process
            if process.poll() is None:
                if self.identity is not None and process_identity(process) != self.identity:
                    raise ProbeFailure("owned process identity changed; refusal to signal")
                process.terminate()
                try: await asyncio.to_thread(process.wait, timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill(); await asyncio.to_thread(process.wait, timeout=5)
            for pipe in (process.stdin, process.stdout):
                if pipe is not None: pipe.close()
        if self._stderr is not None:
            self._stderr.close(); self._stderr = None

    async def finish(self):
        try:
            if self.process is not None and not self._failed and self.process.poll() is None:
                result = await self.exchange({"op": "close"})
                if result != {"closed": True}: raise ProbeFailure("shutdown acknowledgement invalid")
                await asyncio.to_thread(self.process.wait, timeout=5)
        finally:
            await self.close()

    def receipt(self):
        return dict(identity=self.identity, returncode=self.process.returncode if self.process else None,
                    stopped=self.process is None or self.process.poll() is not None, exchanges=self.exchanges)


def snapshot(db):
    return dict(runs=sorted(deepcopy(list(db.runs.values())), key=lambda r: str(r["id"])),
                events=deepcopy(db.events), artifacts=sorted(deepcopy(list(db.artifacts.values())), key=lambda r: str(r["id"])))


def hydrate_row(row, fields):
    row = deepcopy(row)
    for key in fields: row[key] = UUID(row[key])
    for key in ("ts", "completed_at"):
        if row.get(key) is not None: row[key] = datetime.fromisoformat(row[key])
    return row


async def agents_main(scenario):
    sys.path[:0] = [str(ROOT / "services/agents"), str(ROOT / "services/agents/tests")]
    import httpx
    from unittest.mock import patch
    import test_program_start_coordinator_contract as c
    from test_program_start_api_config import policy_doc
    from _program_admission_memory import AdmissionDatabase
    from app.investigation_v2.program_start_api import create_app, ControlledManualTargetPolicy
    from app.investigation_v2.program_result_api import create_app as read_app
    from app.investigation_v2.program_start_store import ProgramAlertStartStore, ARTIFACT_KIND
    from app.investigation_v2.program_result_reader import CompatibleOwnedReconResultReader
    from app.investigation_v2.program_recon_publication_store import ProgramReconPublicationStore
    from app.investigation_v2.program_recon_runtime import ProgramReconRuntime
    from app.investigation_v2.scope import TenantPrincipal
    from app.investigation_v2.execution_store import canonical_json

    async def forbidden(*args, **kwargs): raise AssertionError("real HTTP/PG or cold execution forbidden")
    fixture = c.ProgramStartCoordinatorTests(); await fixture.asyncSetUp()
    db = fixture.db
    budget = c.a.policy(max_tool_calls=0) if scenario == "zero_budget" else fixture.fixture.policy
    admission = ProgramAlertStartStore(db, budget_policy=budget)
    guard = ControlledManualTargetPolicy.from_document(policy_doc())
    coordinator = fixture.make(admission_store=admission, target_guard=guard, target_policy_ref=guard.policy_ref)
    app = create_app(coordinator=coordinator, start_token=WRITE_TOKEN, budget_policy=budget)
    reader_app = read_app(reader=CompatibleOwnedReconResultReader(db), read_token=READ_TOKEN)
    original_intent = fixture.fixture.intent
    body = {k: deepcopy(original_intent["request"][k]) for k in ("operation_key", "window", "request_version")}
    if scenario == "admission_ACK": db.fail_after_commit = True
    if scenario == "query_unknown":
        async def timeout(request): raise httpx.ReadTimeout("test-only-query-unknown")
        fixture.handler = timeout
    with ExitStack() as stack:
        stack.enter_context(patch.object(httpx.AsyncHTTPTransport, "handle_async_request", forbidden))
        stack.enter_context(patch("asyncpg.create_pool", forbidden))
        if scenario == "publication_ACK":
            original_publish = ProgramReconPublicationStore.publish
            async def lose_ack(store, request):
                db.fail_after_commit = True
                return await original_publish(store, request)
            stack.enter_context(patch.object(ProgramReconPublicationStore, "publish", lose_ack))
        while True:
            raw = await asyncio.to_thread(sys.stdin.buffer.readline, MAX_FRAME + 1)
            if not raw: return
            op = None
            try:
                message = frame_json(raw); op = message.get("op")
                if op == "ready":
                    result = dict(scenario=scenario, tenant_id=str(c.a.e.TENANT), actor_id=str(c.a.ACTOR), alert_id=str(c.a.e.ALERT),
                        run_id=original_intent["run_id"], body=body, budget_policy=budget.descriptor, target_policy=policy_doc(),
                        now=db.now.isoformat(), alerts=list(db.alerts.values()), ledger=snapshot(db))
                elif op == "close": result = {"closed": True}
                elif op == "snapshot":
                    ledger = json.loads(canonical(snapshot(db)))
                    for artifact in ledger["artifacts"]:
                        content = artifact["content"].encode("utf-8")
                        assert len(content) == artifact["size_bytes"] and sha(content) == artifact["sha256"]
                    admitted = [a for a in ledger["artifacts"] if a["kind"] == ARTIFACT_KIND]
                    assert len(admitted) == 1
                    document = json.loads(admitted[0]["content"])
                    assert document["intent"]["request"]["actor_id"] == str(c.a.ACTOR)
                    assert canonical(document["intent"]["request"]["budget_policy"]) == canonical(budget.descriptor)
                    # Independently reconstruct the exact current rows and all
                    # UUID/time types before a fresh actual owned reader.
                    cold = AdmissionDatabase(alert=list(db.alerts.values())[0], now=db.now)
                    runs = [hydrate_row(r, ("id", "tenant_id")) for r in ledger["runs"]]
                    cold.runs = {r["id"]: r for r in runs}
                    cold.events = [hydrate_row(r, ("id", "tenant_id", "run_id")) for r in ledger["events"]]
                    arts = [hydrate_row(r, ("id", "tenant_id", "run_id", "event_id")) for r in ledger["artifacts"]]
                    cold.artifacts = {r["id"]: r for r in arts}
                    with patch.object(ProgramReconRuntime, "begin", forbidden), patch.object(ProgramReconRuntime, "execute", forbidden), patch.object(ProgramReconPublicationStore, "publish", forbidden):
                        owned = await CompatibleOwnedReconResultReader(cold).read(current_principal=c.a.current(),
                            tenant_id=c.a.e.TENANT, run_id=UUID(original_intent["run_id"]))
                    assert canonical(snapshot(cold)) == canonical(ledger)
                    for run in ledger["runs"]:
                        assert (run["status"], run["completed_at"], run["total_tokens"], run["total_cost_usd"]) == ("running", None, 0, 0)
                    result = dict(ledger=ledger, ledger_sha256=digest(ledger), cold_owned=owned, admission=document,
                        tool_calls=len(fixture.calls), tool_requests=[dict(method=r.method, path=str(r.url), headers=dict(r.headers), body_utf8=r.content.decode()) for r in fixture.calls])
                elif op == "http":
                    request = message["request"]
                    chosen = reader_app if request["method"] == "GET" else app
                    before = digest(snapshot(db)); previous_calls = len(fixture.calls)
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=chosen), base_url="http://child-ASGI.invalid") as client:
                        response = await client.request(request["method"], request["path"], headers=request["headers"], content=request["body_utf8"])
                    result = dict(status=response.status_code, body_utf8=response.content.decode("utf-8"), body_sha256=sha(response.content),
                        ledger_sha256=digest(snapshot(db)), rows_changed=before != digest(snapshot(db)),
                        tool_calls=len(fixture.calls), new_tool_calls=len(fixture.calls)-previous_calls)
                else: raise ProbeFailure("unknown child operation")
                encoded = (canonical(result) + "\n").encode("utf-8")
                if len(encoded) > MAX_FRAME: raise ProbeFailure("oversized child frame")
            except Exception:
                encoded = b'{"probe_error":"offline start child verification failed"}\n'
            sys.stdout.buffer.write(encoded); sys.stdout.buffer.flush()
            if op == "close": return


def checked_output(value):
    path = Path(value).resolve()
    if not path.is_relative_to(ROOT) or any(p in {".git", ".agents", ".codex"} for p in path.relative_to(ROOT).parts) or not path.parent.is_dir():
        raise ProbeFailure("new explicit workspace output with existing parent required")
    return path


def retained_process_receipt(channel):
    try:
        return channel.receipt()
    except BaseException as exc:
        return {"stopped": None, "receipt_error_type": type(exc).__name__}


async def run_probe(output, *, scenarios=SCENARIOS):
    path = checked_output(output)
    if not scenarios or len(set(scenarios)) != len(scenarios) or any(s not in SCENARIOS for s in scenarios):
        raise ProbeFailure("explicit unique supported scenarios required")
    with path.open("x", encoding="utf-8") as handle:
        summary = dict(schema="program_start_offline_composition.v1", status="incomplete", cases=[])
        channel = None
        try:
            sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests")]
            import httpx
            from unittest.mock import patch
            from app.api.v1.deps import CurrentUser, get_current_user
            from app.db.database import get_db
            from app.investigation_v2.program_start_api import create_app
            from app.investigation_v2.program_start_gateway import ProgramStartGateway
            from app.investigation_v2.program_result_gateway import CompatibleResultReadGateway
            from test_investigation_v2_query_api import FakeReadSession

            async def forbidden(*args, **kwargs): raise AssertionError("real API transport forbidden")
            with patch.object(httpx.AsyncHTTPTransport, "handle_async_request", forbidden), patch.dict(os.environ,
                {"ENV": "production", "AISOC_DEV_MODE": "0", "AISOC_API_SERVICE_TOKEN": API_TOKEN,
                 "AISOC_INVESTIGATION_COMPAT_READ_TOKEN": READ_TOKEN}):
                for scenario in scenarios:
                    channel = OwnedAgentChannel(scenario=scenario)
                    case = dict(scenario=scenario, observations=[]); summary["cases"].append(case)
                    primary_error = None
                    try:
                        meta = await channel.start(); case["initial"] = meta
                        assert meta["ledger"] == {"runs": [], "events": [], "artifacts": []}
                        scopes = ["investigation:run", "alerts:read", "cases:read"]
                        actor, tenant = UUID(meta["actor_id"]), UUID(meta["tenant_id"])
                        backend_calls, last_internal, last_request, drop_response = 0, None, None, scenario == "response_lost"
                        resolved_current = None
                        async def backend(request):
                            nonlocal backend_calls, last_internal, last_request, drop_response
                            backend_calls += 1
                            last_request = dict(method=request.method, path=request.url.raw_path.decode(), headers=dict(request.headers), body_utf8=request.content.decode())
                            last_internal = await channel.exchange(dict(op="http", request=last_request))
                            if drop_response:
                                drop_response = False
                                raise httpx.ReadTimeout("test-only-parent-dropped-complete-child-response")
                            return httpx.Response(last_internal["status"], content=last_internal["body_utf8"].encode("utf-8"))
                        transport = httpx.MockTransport(backend)
                        app = create_app(start_gateway=ProgramStartGateway(backend_url="http://stdio-write.invalid", start_token=WRITE_TOKEN, transport=transport),
                            result_gateway=CompatibleResultReadGateway(backend_url="http://stdio-read.invalid", read_token=READ_TOKEN, transport=transport))
                        async def current():
                            nonlocal resolved_current
                            user = CurrentUser(actor, tenant, "analyst", "test@example.invalid", scopes=list(scopes))
                            resolved_current = dict(actor_id=str(user.user_id), tenant_id=str(user.tenant_id), scopes=list(user.scopes))
                            return user
                        async def db_session(): yield FakeReadSession()
                        app.dependency_overrides[get_current_user] = current; app.dependency_overrides[get_db] = db_session
                        headers = {"Authorization": "Bearer " + API_TOKEN, "X-AiSOC-Tenant-ID": meta["tenant_id"]}
                        base = f"/api/v2/investigation/alerts/{meta['alert_id']}/"
                        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://parent-ASGI.invalid") as client:
                            async def check(name, status, *, body=None, method="POST", endpoint="start", sent_headers=None, calls=1):
                                nonlocal last_internal, last_request, resolved_current
                                before = backend_calls; last_internal, last_request, resolved_current = None, None, None
                                target = f"/api/v2/investigation/runs/{meta['run_id']}" if method == "GET" else base+endpoint
                                response = await client.request(method, target, headers=headers if sent_headers is None else sent_headers,
                                    content=None if method == "GET" else canonical(meta["body"] if body is None else body).encode())
                                row = dict(case=name, method=method, path=target, status=response.status_code, body_utf8=response.content.decode(),
                                    body_sha256=sha(response.content), backend_calls=backend_calls-before,
                                    API_request=dict(method=response.request.method, path=response.request.url.raw_path.decode(), headers=dict(response.request.headers),
                                        body_utf8=response.request.content.decode(), body_sha256=sha(response.request.content)),
                                    injected_current_user=deepcopy(resolved_current),
                                    backend_request=deepcopy(last_request), internal=deepcopy(last_internal))
                                case["observations"].append(row)
                                assert response.status_code == status, (scenario, name, response.status_code, status)
                                assert backend_calls-before == calls, (scenario, name, "dispatch count")
                                return response.json()
                            # Authorization denials happen before a single IPC
                            # HTTP request. Missing credentials cannot use demo.
                            scopes.remove("investigation:run"); await check("missing_run",403,calls=0)
                            scopes[:]=["investigation:run","cases:read"]; await check("missing_alert_read",403,calls=0)
                            scopes[:]=["investigation:run","alerts:read","cases:read"]
                            await check("missing_credential",401,calls=0,sent_headers={})
                            app.dependency_overrides.pop(get_current_user); await check("original_read_service",403,calls=0)
                            await check("invalid_credential",401,calls=0,sent_headers={"Authorization":"Bearer invalid-not-a-token"})
                            app.dependency_overrides[get_current_user]=current
                            first_status = 503 if scenario in {"admission_ACK","publication_ACK","response_lost"} else 200
                            first = await check("first",first_status,sent_headers={**headers,"X-AiSOC-Tenant-ID":str(UUID(int=999)),"X-AiSOC-Actor-ID":str(UUID(int=999))})
                            first_ledger_hash=last_internal["ledger_sha256"]
                            assert last_request["headers"]["x-aisoc-actor-id"] == meta["actor_id"]
                            assert last_request["headers"]["x-aisoc-tenant-id"] == meta["tenant_id"]
                            read = await check("explicit_read",200,endpoint="operation-read")
                            repeat = await check("repeat_start",200)
                            get = await check("compatible_GET",200,method="GET")
                            assert canonical(read)==canonical(repeat) and canonical(get)==canonical(read["result"])
                            assert read["mode"] == "read_only" and read["runtime"]["entered_by_this_invocation"] is False
                            if first_status == 200: assert canonical(first["result"])==canonical(get)
                            for row in case["observations"][-3:]:
                                assert row["internal"]["rows_changed"] is False and row["internal"]["new_tool_calls"] == 0
                                assert row["internal"]["ledger_sha256"] == first_ledger_hash
                            scopes.remove("investigation:run"); await check("revoked_next_request",403,calls=0); scopes.append("investigation:run")
                            changed = deepcopy(meta["body"]); changed["window"]["end"]="2026-10-23T10:04:00+00:00"
                            await check("same_key_different_window",409,body=changed)
                            actor=UUID(int=999); await check("same_key_different_current_actor",409); actor=UUID(meta["actor_id"])
                            tenant=UUID(int=999); await check("foreign_current_tenant",409); tenant=UUID(meta["tenant_id"])
                            if scenario in {"admission_ACK","query_unknown"}:
                                changed=deepcopy(meta["body"]); changed["operation_key"]=str(UUID(int=67))
                                await check("new_key_active_or_unknown",409,body=changed)
                            final = await channel.exchange({"op":"snapshot"}); case["final"]=final
                            expected = (2,3,0) if scenario=="admission_ACK" else ((5,11,0) if scenario=="zero_budget" else (7,15,1))
                            ledger=final["ledger"]
                            assert (len(ledger["events"]),len(ledger["artifacts"]),final["tool_calls"])==expected
                            assert final["ledger_sha256"]==first_ledger_hash and canonical(final["cold_owned"])==canonical(get)
                            if scenario=="normal": assert get["execution_snapshot"]["scope_readiness"]=="ready"
                            if scenario in {"zero_budget","query_unknown"}: assert get["execution_snapshot"]["scope_readiness"]=="partial"
                            if scenario=="admission_ACK": assert get["progress"]["phase"]=="ready"
                            case["backend_calls"]=backend_calls
                    except BaseException as exc:
                        primary_error = exc
                        case["error_type"] = type(exc).__name__
                        raise
                    finally:
                        cleanup_error = None
                        try:
                            await channel.finish()
                        except BaseException as exc:
                            cleanup_error = exc
                            case["cleanup_error_type"] = type(exc).__name__
                        finally:
                            case["owned_process"] = retained_process_receipt(channel)
                            channel = None  # No second finish or request replay.
                        if cleanup_error is not None and primary_error is None:
                            raise cleanup_error
            summary.update(status="passed_offline_only", scenarios=len(summary["cases"]),
                API_requests=sum(len(c["observations"]) for c in summary["cases"]), backend_calls=sum(c["backend_calls"] for c in summary["cases"]),
                limits=["SQL doubles/ASGI/MockTool/stdio only; no actual PG/network/CH/model/business Run/notification/deployment",
                        "Injected CurrentUser is not real JWT/RBAC; configured target ref is not operational isolation",
                        "Actual new simulated ledger proves this composition, not production data truth or PG locking"])
        except BaseException as exc:
            summary.update(status="failed", error_type=type(exc).__name__)
            raise
        finally:
            try:
                if channel is not None:
                    try: await channel.finish()
                    except BaseException as exc:
                        summary.update(status="failed", cleanup_error_type=type(exc).__name__)
                    finally:
                        if summary["cases"]: summary["cases"][-1]["owned_process"] = retained_process_receipt(channel)
            finally:
                # Saving the primary failure must survive cleanup failure too.
                handle.write(canonical(summary)+"\n"); handle.flush()
        return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents",action="store_true",help=argparse.SUPPRESS)
    parser.add_argument("--scenario",choices=SCENARIOS,default="normal")
    parser.add_argument("--output")
    args=parser.parse_args()
    if args.agents: asyncio.run(agents_main(args.scenario)); return
    if not args.output: parser.error("--output required")
    result=asyncio.run(run_probe(args.output))
    print(canonical({k:result[k] for k in ("status","scenarios","API_requests","backend_calls")}))


if __name__=="__main__": main()
