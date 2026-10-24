"""Portable full producer outcomes; auth remains the API's original dependency."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
from uuid import UUID

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.api.v1.deps import CurrentUser, get_current_user, is_dev_mode
from app.db.database import get_db
from app.investigation_v2.program_start_api import create_app
from app.investigation_v2.program_start_gateway import (
    ProgramStartGateway, checked_start_outcome, normalized_start_body, operation_identity,
    URL_ENV, TOKEN_ENV, READ_TOKEN_ENV, MAX_BYTES, MAX_BODY_BYTES, _canonical,
)
from app.investigation_v2.program_result_gateway import CompatibleResultReadGateway
from test_investigation_v2_query_api import FakeReadSession
from test_investigation_compatible_result_api import reseal

FIXTURE = Path(__file__).parent / "fixtures" / "investigation_program_start_outcomes.json"
DOCUMENT = json.loads(FIXTURE.read_text("utf-8"))
CASES = DOCUMENT["cases"]
TENANT, ACTOR, ALERT = (UUID(DOCUMENT["provenance"][k]) for k in ("tenant_id", "actor_id", "alert_id"))
OTHER = UUID(int=999)
KEY = UUID(CASES["normal_initial"]["request_body"]["operation_key"])
API_AUTH = "test-only-API-service-read-credential-not-live"
WRITE_AUTH = "test-only-isolated-start-write-credential-not-live"
READ_AUTH = "test-only-compatible-result-read-credential-not-live"


class StartOutcomeProtocolTests(unittest.TestCase):
    def check(self, p, read_only=False):
        return checked_start_outcome(p, tenant_id=TENANT, alert_id=ALERT, operation_key=KEY, read_only=read_only)

    def refuse(self, mutate, name="normal_initial"):
        p = deepcopy(CASES[name]["outcome"]); mutate(p)
        with self.assertRaises((ValueError, KeyError, TypeError, AttributeError)):
            self.check(p)

    def test_all_fifteen_real_producer_outcomes_unchanged(self):
        self.assertEqual(len(CASES), 15)
        for name, row in CASES.items():
            p = deepcopy(row["outcome"]); before = _canonical(p)
            self.assertIs(self.check(p, read_only=not name.endswith("_initial")), p)
            self.assertEqual(_canonical(p), before)
            self.assertEqual(p["result"]["markdown"], row["outcome"]["result"]["markdown"])

    def test_stable_operation_and_owner_formula(self):
        run, executor = operation_identity(TENANT, KEY)
        self.assertEqual(str(run), "477863ed-d657-50c5-b93b-fa70cf8388d3")
        self.assertEqual(str(executor), "95f44eba-a761-5810-b0eb-a88f9a3835aa")
        for tenant, key in ((OTHER, KEY), (TENANT, OTHER)):
            with self.assertRaises(ValueError):
                checked_start_outcome(CASES["normal_initial"]["outcome"], tenant_id=tenant, alert_id=ALERT, operation_key=key, read_only=False)

    def test_all_outer_admission_runtime_keys_closed(self):
        original = CASES["normal_initial"]["outcome"]
        for field in (None, "admission", "runtime"):
            value = original if field is None else original[field]
            for key in value:
                self.refuse(lambda p, f=field, k=key: (p if f is None else p[f]).pop(k))
            self.refuse(lambda p, f=field: (p if f is None else p[f]).update(extra=True))

    def test_receipt_reference_shapes_and_nested_keys(self):
        for field in ("admission_artifact",):
            for key, bad in (("artifact_id", str(UUID(int=0))), ("sha256", "A"*64), ("extra", True)):
                self.refuse(lambda p, f=field, k=key, v=bad: p["admission"][f].update({k:v}))
        for field in ("input", "state"):
            for key in ("artifact_id", "sha256"):
                self.refuse(lambda p, f=field, k=key: p["admission"]["begin"][f].update({k:"bad"}))
        for key in ("event_id", "input", "state"):
            self.refuse(lambda p, k=key: p["admission"]["begin"].pop(k))
        self.refuse(lambda p: p["admission"]["begin"].update(extra=True))
        for key in ("admission_event_id", "intent_ref", "request_hash", "executor_id"):
            self.refuse(lambda p, k=key: p["admission"].update({k:"bad"}))

    def test_external_authority_and_all_flags_require_real_bool(self):
        for bad in (0, 1, "false", None):
            self.refuse(lambda p, v=bad: p.update(external_call_authorized=v))
            for key in ("external_call_authorized", "fresh", "may_enter_runtime"):
                self.refuse(lambda p, k=key, v=bad: p["admission"].update({k:v}))
            for key in ("entered_by_this_invocation", "http_attempted_by_this_invocation", "publication_attempted_by_this_invocation"):
                self.refuse(lambda p, k=key, v=bad: p["runtime"].update({k:v}))

    def test_version_mode_status_and_committed_only(self):
        for key, bad in (("schema", "old.v1"), ("mode", "unknown")):
            self.refuse(lambda p, k=key, v=bad: p.update({k:v}))
        for key, bad in (("schema", "old.v1"), ("persistence_status", "unknown"), ("phase", "future"), ("original_deadline", "2026-10-23T10:00:00")):
            self.refuse(lambda p, k=key, v=bad: p["admission"].update({k:v}))
        for status in (None, "ready", [], 1):
            self.refuse(lambda p, v=status: p["runtime"].update(status=v))

    def test_read_route_cannot_accept_first_start_or_execution_flags(self):
        with self.assertRaises(ValueError): self.check(CASES["normal_initial"]["outcome"], read_only=True)
        for key, bad in (("status", "stopped"), ("entered_by_this_invocation", True), ("http_attempted_by_this_invocation", True), ("publication_attempted_by_this_invocation", True)):
            self.refuse(lambda p, k=key, v=bad: p["runtime"].update({k:v}), "normal_read")
        for key in ("fresh", "may_enter_runtime"):
            self.refuse(lambda p, k=key: p["admission"].update({k:True}), "normal_read")

    def test_nonstopped_coordinated_result_never_published(self):
        for status in ("in_progress_or_interrupted", "blocked_handoff_pending"):
            p = deepcopy(CASES["admission_ACK_read"]["outcome"])
            p["mode"] = "coordinated"; p["admission"].update(fresh=True, may_enter_runtime=True)
            p["runtime"].update(entered_by_this_invocation=True, status=status)
            self.check(p)
            p["runtime"]["publication_attempted_by_this_invocation"] = True
            with self.assertRaises(ValueError): self.check(p)
        self.refuse(lambda p: p["runtime"].update(status="in_progress_or_interrupted", publication_attempted_by_this_invocation=False))

    def test_admission_phase_is_commit_observation_not_final_phase(self):
        p = CASES["normal_initial"]["outcome"]
        self.assertEqual(p["admission"]["phase"], "ready")
        self.assertEqual(p["runtime"]["status"], "stopped")
        self.check(p)

    def test_owned_identity_target_objective_no_old_family(self):
        for key, bad in (("schema", "owned_fixed_recon_result.v1"), ("tenant_id", str(OTHER)), ("run_id", str(OTHER)), ("target", {"type":"alert","id":str(OTHER)}), ("objective", "maliciousness")):
            self.refuse(lambda p, k=key, v=bad: p["result"].update({k:v}))

    def test_complete_nested_manifest_MD_execution_and_section_hashes_checked(self):
        self.refuse(lambda p: p["result"].update(markdown=p["result"]["markdown"]+"changed"))
        self.refuse(lambda p: p["result"]["execution_snapshot"].update(stop_reason="changed"))
        def drift(p):
            p["result"]["manifest"]["snapshots"]["evidence"]["section"] = "/preparation/evidence_document"
            reseal(p["result"])
        self.refuse(drift)

    def test_complete_unpublished_candidate_checked(self):
        self.refuse(lambda p: p["result"]["candidate"]["result"].update(facts=[]), "owner_cancelled_read")

    def test_request_normalizes_offsets_UUID_and_only_known_fields(self):
        body = deepcopy(CASES["normal_initial"]["request_body"])
        body["window"] = {"start":"2026-10-23T18:00:00+08:00", "end":"2026-10-23T18:05:00+08:00"}
        self.assertEqual(normalized_start_body(_canonical(body)), CASES["normal_initial"]["request_body"])


class StartAPITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {"ENV":"production", "AISOC_DEV_MODE":"0", "AISOC_API_SERVICE_TOKEN":API_AUTH, READ_TOKEN_ENV:READ_AUTH})
        self.env.start(); self.addCleanup(self.env.stop)
        self.payload = deepcopy(CASES["normal_initial"]["outcome"])
        self.body = deepcopy(CASES["normal_initial"]["request_body"])
        self.calls, self.read_calls, self.raw, self.stream, self.error, self.status = [], [], None, None, None, 200
        async def backend(request):
            self.calls.append(request)
            if self.error: raise self.error
            if self.stream is not None: return httpx.Response(self.status, stream=self.stream)
            return httpx.Response(self.status, content=self.raw) if self.raw is not None else httpx.Response(self.status, json=self.payload if self.status == 200 else {"detail":"PRIVATE_DSN_TOKEN"}, headers={"Location":"http://bad.invalid/"})
        async def read_backend(request):
            self.read_calls.append(request); return httpx.Response(200, json=self.payload["result"])
        self.gateway = ProgramStartGateway(backend_url="http://write.invalid", start_token=WRITE_AUTH, transport=httpx.MockTransport(backend))
        read = CompatibleResultReadGateway(backend_url="http://read.invalid", read_token=READ_AUTH, transport=httpx.MockTransport(read_backend))
        self.app = create_app(start_gateway=self.gateway, result_gateway=read)
        self.db = FakeReadSession()
        async def db_session(): yield self.db
        self.app.dependency_overrides[get_db] = db_session
        self.scopes = ["investigation:run", "alerts:read", "cases:read"]
        async def current(): return CurrentUser(ACTOR, TENANT, "analyst", "test@example.invalid", scopes=list(self.scopes))
        self.app.dependency_overrides[get_current_user] = current
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://api.invalid")
        self.addAsyncCleanup(self.client.aclose)

    @property
    def path(self): return f"/api/v2/investigation/alerts/{ALERT}/start"
    @property
    def headers(self): return {"Authorization":"Bearer "+API_AUTH, "X-AiSOC-Tenant-ID":str(TENANT)}
    async def send(self, *, path=None, headers=None, raw=None):
        return await self.client.post(path or self.path, headers=self.headers if headers is None else headers,
            content=_canonical(self.body) if raw is None else raw)

    async def test_full_first_response_and_server_credential_current_actor(self):
        response = await self.send(); self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.payload); self.assertEqual(len(self.calls), 1)
        req = self.calls[0]
        self.assertEqual(req.url.path, f"/internal/investigation-v2/alerts/{ALERT}/start")
        self.assertEqual(req.headers["Authorization"], "Bearer "+WRITE_AUTH)
        self.assertEqual(req.headers["X-AiSOC-Tenant-ID"], str(TENANT))
        self.assertEqual(req.headers["X-AiSOC-Actor-ID"], str(ACTOR))
        self.assertEqual(json.loads(req.content), self.body)

    async def test_all_actual_outcomes_through_API_complete_canonical_and_MD_preserved(self):
        for name, row in CASES.items():
            with self.subTest(name=name):
                self.payload, self.body = deepcopy(row["outcome"]), deepcopy(row["request_body"])
                path = self.path if name.endswith("_initial") else self.path.removesuffix("start")+"operation-read"
                response = await self.send(path=path); self.assertEqual(response.status_code, 200)
                self.assertEqual(_canonical(response.json()), _canonical(self.payload))
                self.assertEqual(response.json()["result"]["markdown"], self.payload["result"]["markdown"])
        self.assertEqual(len(self.calls), 15)

    async def test_each_permission_missing_denies_before_body_backend(self):
        for missing in ("investigation:run", "alerts:read"):
            self.scopes = [v for v in ("investigation:run", "alerts:read") if v != missing]
            self.assertEqual((await self.send(raw=b"x"*(MAX_BODY_BYTES+1))).status_code, 403)
        self.assertEqual(self.calls, [])

    async def test_original_shared_read_service_token_cannot_start_or_operation_read(self):
        self.app.dependency_overrides.pop(get_current_user)
        for path in (self.path, self.path.removesuffix("start")+"operation-read"):
            self.assertEqual((await self.send(path=path)).status_code, 403)
        self.assertEqual(self.calls, [])

    async def test_start_uses_run_and_alerts_read_GET_keeps_cases_read(self):
        self.scopes = ["investigation:run", "alerts:read"]
        self.assertEqual((await self.send()).status_code,200)
        response=await self.client.get(f"/api/v2/investigation/runs/{self.payload['result']['run_id']}",headers=self.headers)
        self.assertEqual(response.status_code,403); self.assertEqual(len(self.calls),1); self.assertEqual(self.read_calls,[])

    async def test_explicit_bearer_blocks_demo_before_invalid_body_and_path(self):
        self.app.dependency_overrides.pop(get_current_user)
        with patch.dict(os.environ, {"ENV":"development", "AISOC_DEV_AUTH_BYPASS":"1", "AISOC_PUBLISHED_BIND_ADDRS":"127.0.0.1"}):
            self.assertTrue(is_dev_mode())
            for headers in ({}, {"Authorization":"Basic abc"}, {"Authorization":"Bearer "}):
                self.assertEqual((await self.send(headers=headers, raw=b"bad", path="/api/v2/investigation/alerts/bad/start")).status_code, 401)
            self.assertEqual((await self.send(headers={"Authorization":"Bearer invalid-not-a-token"})).status_code, 401)
        self.assertEqual(self.calls, [])

    async def test_permissions_and_credentials_rechecked_next_request(self):
        self.assertEqual((await self.send()).status_code, 200)
        self.scopes.remove("investigation:run"); self.assertEqual((await self.send()).status_code, 403)
        self.app.dependency_overrides.pop(get_current_user)
        with patch.dict(os.environ, {"AISOC_API_SERVICE_TOKEN":"rotated-test-only-credential-not-live"}):
            self.assertEqual((await self.send()).status_code, 401)
        self.assertEqual(len(self.calls), 1)

    async def test_client_actor_and_tenant_overrides_ignored(self):
        response = await self.send(headers={**self.headers,"X-AiSOC-Actor-ID":str(OTHER),"X-AiSOC-Tenant-ID":str(OTHER)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.calls[0].headers["X-AiSOC-Tenant-ID"], str(TENANT))
        self.assertEqual(self.calls[0].headers["X-AiSOC-Actor-ID"], str(ACTOR))

    async def test_all_query_overrides_and_bad_path_denied(self):
        for suffix in ("?owner=x", "?tenant_id=x", "?", "?budget=0"):
            if suffix == "?": continue  # No parameter is semantically empty.
            self.assertEqual((await self.send(path=self.path+suffix)).status_code, 400)
        self.assertEqual((await self.send(path=self.path.replace(str(ALERT),str(UUID(int=0))))).status_code, 400)
        self.assertEqual((await self.send(path=self.path.replace(str(ALERT),"bad"))).status_code, 422)
        self.assertEqual(self.calls, [])

    async def test_body_extra_control_fields_duplicate_keys_and_wrong_type_refused(self):
        for key in ("owner", "run_id", "budget", "profile", "target", "trigger", "permissions", "intent", "tool"):
            body = deepcopy(self.body); body[key] = "override"
            self.assertEqual((await self.send(raw=_canonical(body))).status_code, 422)
        for raw in (b'{"operation_key":"x","operation_key":"y"}', b'[]', b'null', b'{}', b'\xff', b'NaN', b'['*1200+b']'*1200):
            self.assertEqual((await self.send(raw=raw)).status_code, 422)
        self.assertEqual(self.calls, [])

    async def test_window_nil_operation_and_missing_version_refused(self):
        variants=[]
        for value in (str(UUID(int=0)), 66, None):
            body=deepcopy(self.body); body["operation_key"]=value; variants.append(body)
        for window in ({"start":"2026-10-23T10:00:00","end":"2026-10-23T10:05:00"},
                       {"start":"2026-10-23T10:00:00Z","end":"2026-10-23T10:05:01Z"},
                       {"start":"2026-10-23T10:05:00Z","end":"2026-10-23T10:00:00Z"}):
            body=deepcopy(self.body); body["window"]=window; variants.append(body)
        for value in ("old.v1", None):
            body=deepcopy(self.body); body["request_version"]=value; variants.append(body)
        for body in variants: self.assertEqual((await self.send(raw=_canonical(body))).status_code, 422)
        self.assertEqual(self.calls, [])

    async def test_streaming_body_limit_stops_early(self):
        seen=[]
        async def content():
            for i in range(4): seen.append(i); yield b"x"*2049
        response=await self.client.post(self.path,headers=self.headers,content=content())
        self.assertEqual(response.status_code,413); self.assertEqual(seen,[0,1]); self.assertEqual(self.calls,[])

    async def test_normalized_request_bytes_only(self):
        self.body["window"]={"start":"2026-10-23T18:00:00+08:00","end":"2026-10-23T18:05:00+08:00"}
        self.assertEqual((await self.send()).status_code,200)
        self.assertEqual(json.loads(self.calls[0].content),CASES["normal_initial"]["request_body"])

    async def test_operation_read_full_check_rejects_coordinated_reply(self):
        response=await self.send(path=self.path.removesuffix("start")+"operation-read")
        self.assertEqual(response.status_code,502); self.assertEqual(len(self.calls),1)
        self.assertTrue(self.calls[0].url.path.endswith("/operation-read"))

    async def test_result_GET_and_query_routes_preserved_no_legacy_routes(self):
        response=await self.client.get(f"/api/v2/investigation/runs/{self.payload['result']['run_id']}",headers=self.headers)
        self.assertEqual(response.status_code,200); self.assertEqual(response.json(),self.payload['result'])
        self.assertEqual(self.calls,[]); self.assertEqual(len(self.read_calls),1)
        query = await self.client.post("/api/v2/investigation/query", headers=self.headers, json={"tool":"activity_records.v1","args":{}})
        self.assertEqual(query.status_code,403)  # Original lake:query gate still applies.
        for path in ("/api/v1/investigations/anything","/docs","/openapi.json"):
            self.assertEqual((await self.send(path=path)).status_code,404)
        self.assertEqual((await self.client.get(self.path,headers=self.headers)).status_code,405)

    async def test_backend_statuses_sanitized_and_never_redirect_or_retry(self):
        for status in (409,413,422,500,502,503,504,401,403,404,302,400,201):
            expected=status if status in (409,413,422) else (503 if status in (500,502,503,504) else 502)
            self.status=status; before=len(self.calls); response=await self.send()
            self.assertEqual(response.status_code,expected); self.assertEqual(len(self.calls),before+1)
            for private in ("PRIVATE","write.invalid",WRITE_AUTH): self.assertNotIn(private,response.text)

    async def test_network_timeout_is_unknown_one_dispatch(self):
        for error in (httpx.ReadTimeout("PRIVATE"),httpx.ConnectError("PRIVATE")):
            self.error=error; before=len(self.calls); response=await self.send()
            self.assertEqual(response.status_code,503); self.assertEqual(len(self.calls),before+1)
            self.assertIn("unknown",response.text); self.assertNotIn("PRIVATE",response.text)

    async def test_malformed_duplicate_nonfinite_and_deep_response_refused(self):
        for raw in (b'\xff',b'bad',b'{"a":1,"a":2}',b'{"x":NaN}',b'['*1200+b']'*1200):
            self.raw=raw; self.assertEqual((await self.send()).status_code,502)
        self.assertEqual(len(self.calls),5)

    async def test_response_stream_size_bounded_before_parse_and_closed(self):
        class Stream(httpx.AsyncByteStream):
            count=0; closed=False
            async def __aiter__(self):
                for _ in range(3): self.count+=1; yield b"x"*(MAX_BYTES//2+1)
            async def aclose(self): self.closed=True
        self.stream=Stream(); response=await self.send()
        self.assertEqual(response.status_code,502); self.assertEqual(self.stream.count,2)
        self.assertTrue(self.stream.closed); self.assertEqual(len(self.calls),1)

    async def test_total_deadline_covers_slow_chunks_and_cleanup_is_bounded(self):
        class Stream(httpx.AsyncByteStream):
            count=0; close_entered=False; close_cancelled=False
            async def __aiter__(self):
                while True:
                    await asyncio.sleep(.01); self.count+=1; yield b" "
            async def aclose(self):
                self.close_entered=True
                try: await asyncio.sleep(5)
                except asyncio.CancelledError: self.close_cancelled=True; raise
        self.stream=Stream(); started=time.monotonic()
        with patch("app.investigation_v2.program_start_gateway.REQUEST_TIMEOUT_SECONDS",.18), patch("app.investigation_v2.program_start_gateway.CLOSE_TIMEOUT_SECONDS",.025):
            response=await self.send()
        self.assertEqual(response.status_code,503); self.assertEqual(len(self.calls),1)
        self.assertGreaterEqual(self.stream.count,2); self.assertLess(time.monotonic()-started,1)
        self.assertTrue(self.stream.close_entered); self.assertTrue(self.stream.close_cancelled)

    async def test_total_deadline_also_covers_send(self):
        async def slow(request): self.calls.append(request); await asyncio.sleep(5)
        self.gateway._transport=httpx.MockTransport(slow)
        with patch("app.investigation_v2.program_start_gateway.REQUEST_TIMEOUT_SECONDS",.025):
            response=await self.send()
        self.assertEqual(response.status_code,503); self.assertEqual(len(self.calls),1)

    async def test_complete_body_implicit_EOF_response_close_is_bounded(self):
        payload=_canonical(self.payload)
        class Stream(httpx.AsyncByteStream):
            close_entered=False; close_cancelled=False
            async def __aiter__(self): yield payload
            async def aclose(self):
                self.close_entered=True
                try: await asyncio.sleep(5)
                except asyncio.CancelledError: self.close_cancelled=True; raise
        self.stream=Stream(); started=time.monotonic()
        with patch("app.investigation_v2.program_start_gateway.REQUEST_TIMEOUT_SECONDS",.4), patch("app.investigation_v2.program_start_gateway.CLOSE_TIMEOUT_SECONDS",.025):
            response=await self.send()
        self.assertEqual(response.status_code,200); self.assertEqual(response.json(),self.payload)
        self.assertEqual(len(self.calls),1); self.assertTrue(self.stream.close_entered); self.assertTrue(self.stream.close_cancelled)
        self.assertLess(time.monotonic()-started,.3)

    async def test_client_transport_close_is_bounded_without_replay(self):
        owner=self
        class Transport(httpx.AsyncBaseTransport):
            close_entered=False; close_cancelled=False
            async def handle_async_request(self,request):
                owner.calls.append(request); return httpx.Response(200,json=owner.payload)
            async def aclose(self):
                self.close_entered=True
                try: await asyncio.sleep(5)
                except asyncio.CancelledError: self.close_cancelled=True; raise
        transport=Transport(); self.gateway._transport=transport; started=time.monotonic()
        with patch("app.investigation_v2.program_start_gateway.CLOSE_TIMEOUT_SECONDS",.025): response=await self.send()
        self.assertEqual(response.status_code,200); self.assertEqual(len(self.calls),1)
        self.assertTrue(transport.close_entered); self.assertTrue(transport.close_cancelled)
        self.assertLess(time.monotonic()-started,.6)

    async def test_caller_cancellation_propagates_without_second_request(self):
        entered=asyncio.Event(); cancelled=asyncio.Event()
        async def blocked(request):
            self.calls.append(request); entered.set()
            try: await asyncio.Event().wait()
            except asyncio.CancelledError: cancelled.set(); raise
        self.gateway._transport=httpx.MockTransport(blocked)
        task=asyncio.create_task(self.send()); await asyncio.wait_for(entered.wait(),1); task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertTrue(cancelled.is_set()); self.assertEqual(len(self.calls),1)

    async def test_read_write_credential_separation_rechecked_each_request(self):
        with patch.dict(os.environ,{READ_TOKEN_ENV:WRITE_AUTH}):
            self.assertEqual((await self.send()).status_code,502)
        self.assertEqual(self.calls,[])

    async def test_full_nested_failure_returns_502_with_one_backend_call(self):
        self.payload["result"]["manifest"]["snapshots"]["evidence"]["section"]="/preparation/evidence_document"
        reseal(self.payload["result"])
        self.assertEqual((await self.send()).status_code,502); self.assertEqual(len(self.calls),1)


class StartConfigurationTests(unittest.TestCase):
    def test_only_explicit_new_config_no_old_env_fallback(self):
        with patch.dict(os.environ,{"AISOC_INVESTIGATION_V2_READ_URL":"http://old.invalid","AISOC_INVESTIGATION_V2_READ_TOKEN":WRITE_AUTH},clear=True):
            with self.assertRaises(ValueError): ProgramStartGateway.from_environment()
        with patch.dict(os.environ,{URL_ENV:"http://write.invalid/",TOKEN_ENV:WRITE_AUTH},clear=True):
            self.assertIsInstance(ProgramStartGateway.from_environment(),ProgramStartGateway)

    def test_URL_and_strong_separate_credential(self):
        for url in ("","file:///tmp/test","http://user:pass@host","http://host?token=x","http://host/path","http://host#x","http://host:bad","http://host:99999","http://ho st"):
            with self.assertRaises(ValueError): ProgramStartGateway(backend_url=url,start_token=WRITE_AUTH)
        for token in (None,"short","x"*257,"x"*32+" ","密"*40):
            with self.assertRaises(ValueError): ProgramStartGateway(backend_url="http://write.invalid",start_token=token)
        with patch.dict(os.environ,{READ_TOKEN_ENV:WRITE_AUTH}):
            with self.assertRaises(ValueError): ProgramStartGateway(backend_url="http://write.invalid",start_token=WRITE_AUTH)


if __name__ == "__main__": unittest.main()
