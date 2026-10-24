"""Offline composition: two app packages, stdio HTTP transport and SQL doubles.

Run with the project Python and --output <new workspace path>. No sockets, PG,
model, new business Run or legacy application registration are used here.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
MAX_FRAME = 3 * 1024 * 1024
EXCHANGE_SECONDS = 30
API_TOKEN = "test-only-offline-compatible-api-token-not-live"
INTERNAL_TOKEN = "test-only-offline-compatible-internal-token-not-live"
ROTATED_TOKEN = "test-only-offline-compatible-rotated-token-not-live"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class ProbeFailure(RuntimeError):
    pass


class OwnedAgentChannel:
    """One owned process. A failed exchange is terminal and is never replayed."""
    def __init__(self, *, command=None, timeout=EXCHANGE_SECONDS):
        if type(timeout) not in {int, float} or not 0 < timeout <= EXCHANGE_SECONDS:
            raise ProbeFailure("exchange timeout must be within thirty seconds")
        self.command = command or [sys.executable, "-B", str(Path(__file__).resolve()), "--agents"]
        self.timeout = timeout
        self.process = None
        self._stderr = None
        self._failed = False
        self._lock = asyncio.Lock()
        self.exchanges = 0

    async def start(self):
        if self.process is not None or self._failed:
            raise ProbeFailure("channel already started or closed")
        self._stderr = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(self.command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self._stderr, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            self._stderr.close(); self._stderr = None; self._failed = True
            raise ProbeFailure("owned child startup failed") from None

    async def exchange(self, value):
        async with self._lock:
            try:
                if self._failed or self.process is None:
                    raise ProbeFailure("channel unavailable; replay forbidden")
                frame = (canonical(value) + "\n").encode("utf-8")
                if len(frame) > MAX_FRAME:
                    raise ProbeFailure("oversized request frame")
                self.exchanges += 1
                def write_and_read():
                    self.process.stdin.write(frame); self.process.stdin.flush()
                    return self.process.stdout.readline(MAX_FRAME + 1)
                # One deadline covers BOTH the entire blocking write and read.
                raw = await asyncio.wait_for(asyncio.to_thread(write_and_read), self.timeout)
                if not raw or len(raw) > MAX_FRAME or not raw.endswith(b"\n"):
                    raise ProbeFailure("EOF or oversized response frame")
                result = json.loads(raw.decode("utf-8"))
                if type(result) is not dict or "probe_error" in result:
                    raise ProbeFailure("invalid child result")
                return result
            except BaseException:
                self._failed = True
                await self.close()
                raise

    async def close(self):
        self._failed = True
        if self.process is not None:
            process = self.process
            # Only this Popen handle is ever signalled; no PID/name discovery.
            if process.poll() is None:
                process.terminate()
                try: await asyncio.to_thread(process.wait, timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill(); await asyncio.to_thread(process.wait, timeout=5)
            for pipe in (process.stdin, process.stdout):
                if pipe is not None: pipe.close()
        if self._stderr is not None:
            self._stderr.close(); self._stderr = None

    async def finish(self):
        if self.process is None:
            return
        try:
            if not self._failed and self.process.poll() is None:
                await self.exchange({"op": "close"})
                await asyncio.to_thread(self.process.wait, timeout=5)
        finally:
            await self.close()


async def agents_main():
    # This process imports only the Agents app package.
    sys.path[:0] = [str(ROOT / "services/agents"), str(ROOT / "services/agents/tests")]
    import httpx
    from test_compatible_owned_result_reader_contract import CompatibleOwnedResultReaderContractTests
    from test_recon_publication_store_contract import ReconPublicationStoreContractTests
    from test_evidence_view_contract import query, record
    from _compatible_memory_ledger import MemoryLedger
    from app.investigation_v2.program_result_reader import CompatibleOwnedReconResultReader
    from app.investigation_v2.program_result_api import create_app
    from app.investigation_v2.scope import TenantPrincipal

    fixtures = {}
    helper = CompatibleOwnedResultReaderContractTests()
    class ReadLedger(MemoryLedger):
        async def execute(self, sql, *args):
            # The original double only allows its fixture tenant in set_config.
            # Allow any valid session tenant; actual row SELECT still requires
            # the explicit owned run+tenant tuple. This is no RLS simulation.
            assert "set_config('app.current_tenant_id'" in sql and len(args) == 1 and UUID(args[0]).int
    def snapshot(pool):
        return dict(run=deepcopy(pool.run), events=deepcopy(pool.events),
                    artifacts=sorted(deepcopy(list(pool.artifacts.values())), key=lambda a: str(a["id"])))
    async def install(name, fixture, store, pool, *, unknown=False):
        pool = ReadLedger.from_ledger(pool)
        principal = TenantPrincipal(frozenset({store.tenant_id}), "offline-baseline-reader", False)
        reader = CompatibleOwnedReconResultReader(pool)
        expected = await reader.read(current_principal=principal, tenant_id=store.tenant_id, run_id=store.run_id)
        if unknown:
            pool.events[2]["kind"] = "unified_future_control"
        captured = []
        class CapturingReader:
            async def read(self, **kwargs):
                p = kwargs["current_principal"]
                captured.append(dict(subject=p.subject, delegated=p.delegated, tenant_ids=sorted(str(t) for t in p.tenant_ids)))
                return await reader.read(**kwargs)
        app = create_app(reader=CapturingReader(), read_token=INTERNAL_TOKEN)
        fixtures[name] = dict(fixture=fixture, store=store, pool=pool, app=app, captured=captured,
            expected=expected, ledger=snapshot(pool), tool_calls=len(fixture.runtime_fixture.calls))
    for version in ("fixed", "program"):
        for phase in ("published", "candidate", "progress", "observer", "cancelled"):
            f, store, pool = await helper.version_fixture(version, phase)
            await install(version + "_" + phase, f, store, pool)
        f, store, pool = await helper.version_fixture(version, "published")
        await install(version + "_unknown_history", f, store, pool, unknown=True)
    for publish in (False, True):
        fixture = ReconPublicationStoreContractTests(); await fixture.asyncSetUp()
        payload = query([record('"' * 512, event_id=UUID(int=i + 1)) for i in range(10)])
        store = await fixture.normal(payload)
        if publish: await store.publish(fixture.request)
        await install("fixed_blocked_" + ("published" if publish else "candidate"), fixture, store, MemoryLedger.from_ledger(fixture.ledger))
    while True:
        frame = await asyncio.to_thread(sys.stdin.buffer.readline, MAX_FRAME + 1)
        if not frame:
            return
        op = None
        try:
            if len(frame) > MAX_FRAME or not frame.endswith(b"\n"):
                raise ProbeFailure("bad request frame")
            message = json.loads(frame.decode("utf-8")); op = message["op"]
            if op == "close":
                result = {"closed": True}
            elif op == "inventory":
                result = {"cases": {name: dict(expected=f["expected"], ledger=f["ledger"], ledger_sha256=digest(f["ledger"]),
                           tool_calls=f["tool_calls"]) for name, f in fixtures.items()}}
            elif op == "http":
                f = fixtures[message["case"]]; request = message["request"]
                before = snapshot(f["pool"]); calls = len(f["fixture"].runtime_fixture.calls); captures = len(f["captured"])
                assert digest(before) == digest(f["ledger"]) and calls == f["tool_calls"]
                f["app"].state.read_token = ROTATED_TOKEN if message.get("rotated_token") else INTERNAL_TOKEN
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=f["app"]), base_url="http://offline-internal") as client:
                    response = await client.request(request["method"], request["path"], headers=request["headers"], content=request["body"])
                after = snapshot(f["pool"])
                assert digest(after) == digest(before) and calls == len(f["fixture"].runtime_fixture.calls)
                result = dict(status=response.status_code, body_utf8=response.content.decode("utf-8"),
                    ledger_sha256=digest(after), tool_calls=calls,
                    current_principal=f["captured"][-1] if len(f["captured"]) > captures else None)
            else:
                raise ProbeFailure("unknown control operation")
            encoded = (canonical(result) + "\n").encode("utf-8")
            if len(encoded) > MAX_FRAME:
                raise ProbeFailure("oversized response frame")
        except Exception:
            encoded = b'{"probe_error":"offline child verification failed"}\n'
        sys.stdout.buffer.write(encoded); sys.stdout.buffer.flush()
        if op == "close":
            return


def checked_output(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT) or any(part in {".git", ".codex", ".agents"} for part in path.relative_to(ROOT).parts):
        raise ProbeFailure("explicit workspace output required")
    if not path.parent.is_dir():
        raise ProbeFailure("output parent must already exist")
    return path


async def run_probe(output):
    path = checked_output(output)
    # Reserve the destination exclusively BEFORE creating a process.
    with path.open("x", encoding="utf-8") as handle:
        summary = dict(schema="compatible_result_offline_composition.v1", status="incomplete", observations=[])
        channel = OwnedAgentChannel()
        try:
            await channel.start()
            inventory = (await channel.exchange({"op": "inventory"}))["cases"]
            summary["inventory"] = inventory
            # Only this process imports the API app package.
            sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests")]
            import httpx
            from unittest.mock import patch
            from app.api.v1.deps import CurrentUser, get_current_user
            from app.db.database import get_db
            from app.investigation_v2.program_result_api import create_app
            from app.investigation_v2.program_result_gateway import CompatibleResultReadGateway
            from test_investigation_v2_query_api import FakeReadSession
            from test_investigation_records import TENANT, OTHER

            selected, backend_calls, last_internal, rotated, tamper = "program_published", 0, None, False, False
            async def backend(request):
                nonlocal backend_calls, last_internal
                backend_calls += 1
                last_internal = await channel.exchange(dict(op="http", case=selected, rotated_token=rotated,
                    request=dict(method=request.method, path=request.url.raw_path.decode(), headers=dict(request.headers), body=request.content.decode())))
                value = json.loads(last_internal["body_utf8"])
                if tamper and last_internal["status"] == 200:
                    manifest = value["manifest"]
                    manifest["snapshots"]["evidence"]["section"] = "/preparation/model_view"
                    prefix = "program-recon-manifest:" if "program" in value["schema"] else "recon-manifest:"
                    manifest["manifest_ref"] = prefix + digest({k: v for k, v in manifest.items() if k != "manifest_ref"})
                    value["manifest_artifact"]["sha256"] = digest(manifest)
                return httpx.Response(last_internal["status"], json=value)
            gateway = CompatibleResultReadGateway(backend_url="http://stdio-only.invalid", read_token=INTERNAL_TOKEN, transport=httpx.MockTransport(backend))
            app = create_app(gateway=gateway)
            async def db_session(): yield FakeReadSession()
            app.dependency_overrides[get_db] = db_session
            headers = {"Authorization": "Bearer " + API_TOKEN, "X-AiSOC-Tenant-ID": TENANT}
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://offline-api") as client:
                with patch.dict(os.environ, {"ENV": "production", "AISOC_DEV_MODE": "0", "AISOC_API_SERVICE_TOKEN": API_TOKEN}):
                    async def check(name, expected_status, *, sent_headers=None, suffix="", body=None, exact=True, expect_calls=1):
                        nonlocal last_internal
                        before = backend_calls; last_internal = None
                        expected = inventory[selected]["expected"]
                        target_path = "/api/v2/investigation/runs/" + expected["run_id"] + suffix
                        response = await client.request("GET", target_path, headers=headers if sent_headers is None else sent_headers, content=body)
                        assert response.status_code == expected_status, (name, response.status_code)
                        assert backend_calls - before == expect_calls
                        if exact:
                            assert canonical(response.json()) == canonical(expected), name
                            if expected["markdown"] is not None:
                                assert response.json()["markdown"].encode() == expected["markdown"].encode()
                        if last_internal is not None:
                            assert last_internal["ledger_sha256"] == inventory[selected]["ledger_sha256"]
                            assert last_internal["tool_calls"] == inventory[selected]["tool_calls"]
                        summary["observations"].append(dict(case=name, fixture=selected, status=response.status_code,
                            body_utf8=response.content.decode(), body_sha256=hashlib.sha256(response.content).hexdigest(),
                            canonical_sha256=digest(response.json()), backend_calls=backend_calls-before,
                            internal=deepcopy(last_internal)))
                    for selected in inventory:
                        if "unknown_history" in selected: continue
                        for repeat in (False, True):
                            await check(selected + ("_repeat" if repeat else ""), 200)
                    for selected in ("fixed_unknown_history", "program_unknown_history"):
                        await check(selected, 409, exact=False)
                    selected = "program_published"
                    await check("missing_credential", 401, sent_headers={}, exact=False, expect_calls=0)
                    await check("wrong_credential", 401, sent_headers={**headers, "Authorization": "Bearer wrong"}, exact=False, expect_calls=0)
                    for scopes in (["cases:read"], ["alerts:read"]):
                        async def restricted(): return CurrentUser(UUID(int=42), UUID(TENANT), "analyst", "test@example.invalid", scopes=list(scopes))
                        app.dependency_overrides[get_current_user] = restricted
                        await check("missing_permission_" + scopes[0], 403, exact=False, expect_calls=0)
                    scopes = ["cases:read", "alerts:read"]
                    app.dependency_overrides[get_current_user] = restricted
                    await check("current_permissions_before_revoke", 200)
                    scopes.remove("alerts:read")
                    await check("current_permissions_revoked", 403, exact=False, expect_calls=0)
                    app.dependency_overrides.pop(get_current_user)
                    await check("query_override", 400, suffix="?owner=all", exact=False, expect_calls=0)
                    await check("body_override", 400, body=b"{}", exact=False, expect_calls=0)
                    before_nil = backend_calls
                    nil_response = await client.get("/api/v2/investigation/runs/" + str(UUID(int=0)), headers=headers)
                    assert nil_response.status_code == 400 and backend_calls == before_nil
                    for selected in ("fixed_published", "program_published"):
                        tamper = True; await check("tampered_" + selected, 502, exact=False); tamper = False
                    selected = "program_published"; rotated = True
                    await check("rotated_internal_token", 502, exact=False); rotated = False
                    async def foreign(): return CurrentUser(UUID(int=42), UUID(OTHER), "analyst", "test@example.invalid", scopes=["cases:read", "alerts:read"])
                    app.dependency_overrides[get_current_user] = foreign
                    await check("foreign_owned_tenant", 404, exact=False)
                    async def current(): return CurrentUser(UUID(int=42), UUID(TENANT), "analyst", "test@example.invalid", scopes=["cases:read", "alerts:read"])
                    app.dependency_overrides[get_current_user] = current
                    await check("forged_identity_headers", 200, sent_headers={**headers, "X-AiSOC-Tenant-ID": OTHER, "X-AiSOC-Actor-ID": str(UUID(int=99))})
                    principal = last_internal["current_principal"]
                    assert principal == dict(subject="verified-api-reader:" + str(UUID(int=42)), delegated=True, tenant_ids=[TENANT])
            summary.update(status="passed_offline_only", direct_fixture_cases=12, selected_ledger_cases=len(inventory),
                backend_calls=backend_calls, nil_run_refused=True,
                limits=["SQL doubles and stdio HTTP only", "No actual PG/network/user JWT/RBAC/new Run/model/publication/deployment"])
        except BaseException as exc:
            summary.update(status="failed", error_type=type(exc).__name__)
            raise
        finally:
            try:
                await channel.finish()
            except BaseException as exc:
                summary.update(status="failed", cleanup_error_type=type(exc).__name__)
                raise
            finally:
                summary["owned_process"] = dict(pid=channel.process.pid if channel.process else None,
                    returncode=channel.process.returncode if channel.process else None, exchanges=channel.exchanges,
                    stopped=channel.process is None or channel.process.poll() is not None)
                handle.write(canonical(summary) + "\n"); handle.flush()
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.agents:
        asyncio.run(agents_main()); return
    if not args.output: parser.error("--output is required")
    result = asyncio.run(run_probe(args.output))
    print(canonical({k: result[k] for k in ("status", "direct_fixture_cases", "backend_calls", "owned_process")}))


if __name__ == "__main__": main()
