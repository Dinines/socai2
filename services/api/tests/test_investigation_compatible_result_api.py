"""Real producer DTO fixtures, existing API auth and bounded HTTP transport."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import UUID

import httpx
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.api.v1.deps import CurrentUser, get_current_user, is_dev_mode
from app.db.database import get_db
from app.investigation_v2.program_result_api import create_app
from app.investigation_v2.program_result_gateway import (
    CompatibleResultReadGateway, checked_compatible_result, URL_ENV, TOKEN_ENV,
    MAX_BYTES, _canonical, _sha,
)
from test_investigation_v2_query_api import FakeReadSession
from test_investigation_records import TENANT, OTHER

FIXTURE = Path(__file__).parent / "fixtures" / "investigation_compatible_results.json"
RESULTS = json.loads(FIXTURE.read_text(encoding="utf-8"))["results"]
EDGE_RESULTS = json.loads((FIXTURE.parent / "investigation_compatible_error_candidates.json").read_text(encoding="utf-8"))["results"]
API_AUTH = "test-only-api-compatible-service-credential-not-live"
READ_AUTH = "test-only-compatible-internal-read-credential-not-live"


def seal(value, field, prefix):
    value[field] = prefix + _sha(_canonical({k: v for k, v in value.items() if k != field}))


def reseal(payload):
    if payload["publication_state"] == "published":
        manifest = payload["manifest"]
        manifest["snapshots"]["execution"]["sha256"] = _sha(_canonical(payload["execution_snapshot"]))
        seal(manifest, "manifest_ref", "program-recon-manifest:" if "program" in payload["schema"] else "recon-manifest:")
        payload["manifest_artifact"]["sha256"] = _sha(_canonical(manifest))
    elif payload.get("candidate"):
        candidate = payload["candidate"]; result = candidate["result"]; prep = candidate["preparation"]
        seal(result, "result_ref", result["result_ref"].split(":")[0] + ":")
        if prep:
            prep["result"] = deepcopy(result)
            seal(prep, "preparation_ref", prep["preparation_ref"].split(":")[0] + ":")
        seal(candidate, "handoff_ref", candidate["handoff_ref"].split(":")[0] + ":")


def rebind_program_document(payload, mutate):
    candidate = payload["candidate"]; doc = candidate["preparation"]["program_material_document"]
    old_snapshot = doc["snapshot_ref"]; mutate(doc); seal(doc, "snapshot_ref", "program-material:")
    new_snapshot = doc["snapshot_ref"]
    def walk(value):
        if isinstance(value, dict): return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list): return [walk(v) for v in value]
        return new_snapshot if value == old_snapshot else value
    payload["candidate"] = candidate = walk(candidate)
    result = candidate["result"]; mapping = {}
    for fact in result["facts"]:
        old_id = fact["id"]
        body = {k: fact[k] for k in ("question", "fact", "evidence_refs", "snapshot_ref", "binding_ref", "fact_policy_ref", "material_schema")}
        fact["id"] = "program-field-finding:" + _sha(_canonical(body)); mapping[old_id] = fact["id"]
    for question in result["questions"]: question["finding_ids"] = [mapping[v] for v in question["finding_ids"]]


class CompatibleResultProtocolTests(unittest.TestCase):
    def check(self, payload):
        return checked_compatible_result(payload, tenant_id=UUID(payload["tenant_id"]), run_id=UUID(payload["run_id"]))

    def refuse(self, name, mutate, *, rehash=True):
        payload = deepcopy(RESULTS[name]); mutate(payload)
        if rehash: reseal(payload)
        with self.assertRaises((ValueError, TypeError, KeyError, AttributeError)):
            self.check(payload)

    def test_all_seventeen_actual_producer_DTOs_are_unchanged(self):
        self.assertEqual(len(RESULTS), 17)
        for name, original in RESULTS.items():
            with self.subTest(name=name):
                payload = deepcopy(original); before = _canonical(payload)
                self.assertIs(self.check(payload), payload)
                self.assertEqual(_canonical(payload), before)
                if payload["markdown"] is not None: self.assertEqual(payload["markdown"].encode(), original["markdown"].encode())

    def test_actual_cached_old_markdown_is_exact_3111_byte_reference_only(self):
        p = RESULTS["actual_fixed_cached_reference"]
        self.assertEqual(len(p["markdown"].encode()), 3111)
        self.assertEqual(_sha(p["markdown"].encode()), "e5f4c3fe2d4f4130eb4ad4964260f87f4a63aea9bb31426566dedafdd8ad68ac")
        self.check(p)  # Cached DTO, no database ownership claim here.

    def test_outer_keys_and_identity_are_closed(self):
        for name in ("fixed_published", "program_published", "fixed_progress", "program_candidate"):
            for key in RESULTS[name]:
                self.refuse(name, lambda p, key=key: p.pop(key), rehash=False)
            self.refuse(name, lambda p: p.update(extra=True), rehash=False)
        for key, value in (("schema", "owned_unknown.v1"), ("profile", "case_investigation"), ("objective", "maliciousness"),
                           ("target", {"type": "alert", "id": str(UUID(int=0))}), ("notification", {})):
            self.refuse("program_published", lambda p, k=key, v=value: p.update({k: v}), rehash=False)
        with self.assertRaises(ValueError):
            checked_compatible_result(RESULTS["fixed_published"], tenant_id=UUID(OTHER), run_id=UUID(RESULTS["fixed_published"]["run_id"]))

    def test_manifest_and_execution_exact_keys(self):
        for name in ("fixed_published", "program_published"):
            for field in ("manifest", "execution_snapshot"):
                for key in RESULTS[name][field]:
                    self.refuse(name, lambda p, f=field, k=key: p[f].pop(k), rehash=False)
                self.refuse(name, lambda p, f=field: p[f].update(extra=True))

    def test_family_versions_do_not_fallback_or_accept_mixed_components(self):
        for name in ("fixed_published", "program_published"):
            for key in ("schema", "runtime_version", "mapping_version", "renderer_version", "sections_version", "completion_policy_ref"):
                self.refuse(name, lambda p, k=key: p["manifest"].update({k: "unknown.v1"}))
            self.refuse(name, lambda p: p.update(schema="owned_fixed_recon_result.v1" if "program" in p["schema"] else "owned_program_recon_result.v1"))

    def test_program_full_twelve_versions_required_at_all_sites(self):
        for name, field in (("program_published", "manifest"), ("program_published", "execution_snapshot"), ("program_candidate", "candidate")):
            for key in RESULTS[name][field]["policy_versions"]:
                self.refuse(name, lambda p, f=field, k=key: p[f]["policy_versions"].pop(k))
                self.refuse(name, lambda p, f=field, k=key: p[f]["policy_versions"].update({k: "fixed_old.v1"}))
            self.refuse(name, lambda p, f=field: p[f]["policy_versions"].update(extra="unknown"))
        self.refuse("fixed_published", lambda p: p["manifest"].update(policy_versions={}))

    def test_control_integers_flags_and_m3_usage_reject_python_equal_types(self):
        for value in (True, 1.0):
            for key in ("version", "scope_revision"):
                self.refuse("program_published", lambda p, k=key, v=value: p["manifest"].update({k: v}))
        for value in (False, 0.0, -1):
            self.refuse("program_published", lambda p, v=value: p["execution_snapshot"]["stage_usage"].update(known_tokens=v))
        for key in ("cost_complete", "tokens_complete"):
            self.refuse("program_published", lambda p, k=key: p["execution_snapshot"]["run_total"].update({k: 1}))
        self.refuse("program_published", lambda p: p["execution_snapshot"].update(human_acknowledged=0))
        self.refuse("program_published", lambda p: p["execution_snapshot"]["stage_usage"].update(total_tokens=None))

    def test_hashes_markdown_execution_and_manifest_all_checked(self):
        for name in ("fixed_published", "program_published"):
            self.refuse(name, lambda p: p.update(markdown=p["markdown"] + "changed"), rehash=False)
            self.refuse(name, lambda p: p["manifest_artifact"].update(sha256="a" * 64), rehash=False)
            self.refuse(name, lambda p: p["manifest"].update(manifest_ref="recon-manifest:" + "a" * 64), rehash=False)
            self.refuse(name, lambda p: p["execution_snapshot"].update(stop_reason="changed"), rehash=False)
            self.refuse(name, lambda p: p["manifest"]["report"].update(media_type="text/html"))

    def test_section_refs_paths_and_pinned_handoff_match(self):
        for section in ("questions", "analysis", "evidence"):
            for key, value in (("artifact_id", str(UUID(int=77))), ("sha256", "a" * 64),
                               ("section", "/untrusted"), ("artifact_schema", "fixed_recon_runtime_handoff.v1"),
                               ("sections_version", "fixed_recon_handoff_sections.v1"), ("section_sha256", "bad")):
                self.refuse("program_published", lambda p, s=section, k=key, v=value: p["manifest"]["snapshots"][s].update({k: v}))

    def test_nullable_evidence_five_combinations_are_closed(self):
        for name in ("fixed_blocked_published", "fixed_observer", "program_observer"):
            self.assertIsNone(RESULTS[name]["manifest"]["snapshots"]["evidence"])
            def fake_ready(p):
                p["execution_snapshot"].update(scope_readiness="ready", run_state="finished", investigation_completeness="complete_for_scope", continuation="none")
                p["manifest"]["retention"]["blocking_gaps"] = []
                p["manifest"]["coverage"] = deepcopy(RESULTS["fixed_published"]["manifest"]["coverage"])
            self.refuse(name, fake_ready)
            self.refuse(name, lambda p: p["manifest"]["retention"].update(source_availability="view_ready"))
        for name in ("fixed_published", "program_published"):
            self.refuse(name, lambda p: p["manifest"]["snapshots"].update(evidence=None))
            self.refuse(name, lambda p: p["manifest"]["snapshots"]["evidence"].update(section="/preparation/model_view"))

    def test_nonnull_material_can_be_partial_and_cancelled_stop_need_not_cancelled_reason(self):
        p = RESULTS["program_error_published"]
        self.assertIsNotNone(p["manifest"]["snapshots"]["evidence"])
        self.assertEqual(p["execution_snapshot"]["scope_readiness"], "partial"); self.check(p)
        p = deepcopy(RESULTS["program_cancelled"])
        p["execution_snapshot"]["stop_reason"] = "budget_limit"; reseal(p)
        self.check(p)  # cancellation observation and execution stop are separate.

    def test_retention_counters_source_and_three_dimensions_match(self):
        for key in ("unknown_calls", "unpriced_attempts", "unsettled_attempts"):
            self.refuse("program_published", lambda p, k=key: p["manifest"]["retention"].update({k: 9}))
        for key, value in (("continuation", "awaiting_human"), ("run_state", "running"), ("investigation_completeness", "partial")):
            self.refuse("program_published", lambda p, k=key, v=value: p["execution_snapshot"].update({k: v}))
        self.refuse("program_published", lambda p: p["manifest"].update(source_state_ref=deepcopy(p["manifest"]["stopped_state_ref"])))

    def test_unpublished_progress_cannot_carry_report_or_extra_schema(self):
        for name in ("fixed_progress", "program_progress"):
            self.refuse(name, lambda p: p.update(markdown="report"))
            self.refuse(name, lambda p: p["progress"].update(extra=True))
            self.refuse(name, lambda p: p["progress"]["stage_usage"].update(tool_calls=True))
        self.refuse("program_candidate", lambda p: p.update(candidate=None), rehash=False)
        self.refuse("program_candidate", lambda p: p["progress"].update(phase="ready"))

    def test_candidate_version_profile_identity_and_refs_are_checked(self):
        for name in ("fixed_candidate", "program_candidate"):
            for key in ("schema", "runtime_version", "completion_policy_ref", "runtime_plan_ref"):
                self.refuse(name, lambda p, k=key: p["candidate"].update({k: "unknown.v1"}))
            self.refuse(name, lambda p: p["candidate"]["business_profile"].update(scope_revision=True))
            self.refuse(name, lambda p: p["candidate"]["result"].update(tenant_id=OTHER))
            self.refuse(name, lambda p: p["candidate"]["result"].update(authorization="authorized"))
            self.refuse(name, lambda p: p["candidate"]["result"].update(extra=True))
            self.refuse(name, lambda p: p["candidate"].update(handoff_ref="unknown:" + "a" * 64), rehash=False)

    def test_candidate_preparation_schema_state_and_snapshot_relationships(self):
        for name in ("fixed_candidate", "program_candidate", "fixed_blocked_candidate"):
            for key, value in (("schema", "unknown.v1"), ("material_state", "not_adopted"), ("result", {})):
                self.refuse(name, lambda p, k=key, v=value: p["candidate"]["preparation"].update({k: v}), rehash=False)
            self.refuse(name, lambda p: p["candidate"]["preparation"].update(extra=True))
        self.refuse("program_candidate", lambda p: p["candidate"]["preparation"]["material"].update(source_run_id=str(UUID(int=99))))
        self.refuse("program_candidate", lambda p: p["candidate"]["preparation"]["program_material_document"].update(snapshot_ref="program-material:" + "a" * 64))

    def test_unadopted_and_blocked_candidates_cannot_be_upgraded_to_ready(self):
        for name in ("fixed_blocked_candidate", "fixed_unadopted_candidate", "program_unadopted_candidate"):
            self.refuse(name, lambda p: p["candidate"]["result"].update(scope_readiness="ready"))
            self.refuse(name, lambda p: p["candidate"]["result"].update(snapshot_ref="ev:" + "a" * 64))
        self.refuse("program_unadopted_candidate", lambda p: p["candidate"].update(preparation={}))

    def test_candidate_finding_question_links_and_strict_tags(self):
        self.refuse("program_candidate", lambda p: p["candidate"]["result"]["facts"][0].update(origin="model"))
        self.refuse("program_candidate", lambda p: p["candidate"]["result"]["facts"][0].update(revision=True))
        self.refuse("program_candidate", lambda p: p["candidate"]["result"]["questions"][0].update(critical=1))
        self.refuse("program_candidate", lambda p: p["candidate"]["result"]["questions"][0].update(finding_ids=[]))
        self.refuse("program_candidate", lambda p: p["candidate"]["result"]["model_projection"].update(eligible_for_model=True))

    def test_candidate_historical_usage_may_precede_current_late_settlement(self):
        p = deepcopy(RESULTS["program_unadopted_candidate"])
        p["progress"]["stage_usage"] = deepcopy(RESULTS["program_published"]["execution_snapshot"]["stage_usage"])
        p["progress"]["run_total"] = deepcopy(RESULTS["program_published"]["execution_snapshot"]["run_total"])
        self.check(p)
        self.assertIsNone(p["markdown"])

    def _stopped_candidate_cannot_be_ready(self, name):
        def mutate(p):
            result = p["candidate"]["result"]
            result.update(execution_stop="unknown_attempt", stop_reason="unknown_attempt", blocking_gaps=["execution_unknown_attempt"])
        self.refuse(name, mutate)

    def test_fixed_stopped_candidate_cannot_be_ready(self):
        self._stopped_candidate_cannot_be_ready("fixed_candidate")

    def test_program_stopped_candidate_cannot_be_ready(self):
        self._stopped_candidate_cannot_be_ready("program_candidate")

    def _no_fact_for_an_unknown_question(self, name):
        def mutate(p):
            result = p["candidate"]["result"]; fact = result["facts"][0]; old = fact["id"]
            fact["question"] = "Q9"
            body = {k: fact[k] for k in ("question", "fact", "evidence_refs", "snapshot_ref", "binding_ref")}
            program = "program" in p["schema"]
            if program: body.update({k: fact[k] for k in ("fact_policy_ref", "material_schema")})
            fact["id"] = ("program-field-finding:" if program else "program-finding:") + _sha(_canonical(body))
            for question in result["questions"]:
                question["finding_ids"] = [v for v in question["finding_ids"] if v != old]
        self.refuse(name, mutate)

    def test_fixed_fact_cannot_be_orphaned_under_unknown_question(self):
        self._no_fact_for_an_unknown_question("fixed_candidate")

    def test_program_fact_cannot_be_orphaned_under_unknown_question(self):
        self._no_fact_for_an_unknown_question("program_candidate")

    def test_program_material_query_executed_is_strict_bool_even_rehashed(self):
        self.refuse("program_candidate", lambda p: rebind_program_document(p, lambda d: d["query"].update(executed=1)))

    def test_program_material_returned_count_is_strict_int_even_rehashed(self):
        self.refuse("program_candidate", lambda p: rebind_program_document(p, lambda d: d["query"].update(returned_count=True)))

    def test_program_material_records_is_a_list_even_rehashed(self):
        self.refuse("program_candidate", lambda p: rebind_program_document(p, lambda d: d.update(records=None)))

    def test_fixed_actual_error_candidate_preserves_unknown_count(self):
        self.check(EDGE_RESULTS["fixed_error"])

    def test_program_actual_error_candidate_preserves_unknown_count(self):
        self.check(EDGE_RESULTS["program_error"])

    def test_fixed_actual_no_receipt_error_preserves_unknown_limit(self):
        self.check(EDGE_RESULTS["fixed_error_without_query_receipt"])

    def test_program_actual_no_receipt_error_preserves_unknown_limit(self):
        self.check(EDGE_RESULTS["program_error_without_query_receipt"])

    def test_actual_empty_and_conflict_candidate_variants_remain_legal(self):
        for name in ("fixed_empty", "program_empty", "fixed_conflict", "program_conflict"):
            self.check(EDGE_RESULTS[name])


class CompatibleResultAPITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {"ENV": "production", "AISOC_DEV_MODE": "0", "AISOC_API_SERVICE_TOKEN": API_AUTH})
        self.env.start(); self.addCleanup(self.env.stop)
        self.payload = deepcopy(RESULTS["program_published"])
        self.calls, self.backend_status, self.backend_error, self.raw, self.stream = [], 200, None, None, None
        async def backend(request):
            self.calls.append(request)
            if self.backend_error: raise self.backend_error
            if self.stream is not None: return httpx.Response(200, stream=self.stream)
            if self.raw is not None: return httpx.Response(200, content=self.raw)
            return httpx.Response(self.backend_status, json=self.payload if self.backend_status == 200 else {"detail": "PRIVATE_TOKEN_DSN"}, headers={"Location": "http://untrusted.invalid/"})
        self.gateway = CompatibleResultReadGateway(backend_url="http://compatible-read.invalid", read_token=READ_AUTH, transport=httpx.MockTransport(backend))
        self.app = create_app(gateway=self.gateway); self.db = FakeReadSession()
        async def db_session(): yield self.db
        self.app.dependency_overrides[get_db] = db_session
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://compatible-api")
        self.addAsyncCleanup(self.client.aclose)

    @property
    def path(self): return "/api/v2/investigation/runs/" + self.payload["run_id"]
    @property
    def headers(self): return {"Authorization": "Bearer " + API_AUTH, "X-AiSOC-Tenant-ID": TENANT}
    async def send(self, *, headers=None, path=None):
        return await self.client.get(path or self.path, headers=self.headers if headers is None else headers)

    async def test_actual_service_auth_forwards_current_identity_and_only_server_credential(self):
        response = await self.send()
        self.assertEqual(response.status_code, 200); self.assertEqual(_canonical(response.json()), _canonical(self.payload))
        request = self.calls[0]
        self.assertEqual(request.method, "GET"); self.assertEqual(request.url.path, "/internal/investigation-v2/runs/" + self.payload["run_id"])
        self.assertEqual(request.headers["Authorization"], "Bearer " + READ_AUTH)
        self.assertNotIn(API_AUTH, request.headers["Authorization"])
        self.assertEqual(request.headers["X-AiSOC-Tenant-ID"], TENANT)
        self.assertNotEqual(UUID(request.headers["X-AiSOC-Actor-ID"]).int, 0)
        self.assertEqual(len(self.db.calls), 1)

    async def test_each_producer_DTO_survives_actual_gateway_and_ASGI(self):
        for name, value in RESULTS.items():
            self.payload = deepcopy(value); before = len(self.calls)
            response = await self.send()
            with self.subTest(name=name):
                self.assertEqual(response.status_code, 200); self.assertEqual(_canonical(response.json()), _canonical(value))
                self.assertEqual(len(self.calls), before + 1)

    async def test_eight_additional_actual_error_empty_conflict_candidates_survive_ASGI(self):
        for name, value in EDGE_RESULTS.items():
            self.payload = deepcopy(value)
            response = await self.send()
            with self.subTest(name=name):
                self.assertEqual(response.status_code, 200)
                self.assertEqual(_canonical(response.json()), _canonical(value))

    async def test_missing_wrong_or_foreign_credentials_never_forward(self):
        for headers, status in (({}, 401), ({"Authorization": "Bearer wrong"}, 401),
                                ({"Authorization": "Bearer " + API_AUTH}, 403),
                                ({**self.headers, "X-AiSOC-Tenant-ID": OTHER}, 403),
                                ({**self.headers, "X-AiSOC-Tenant-ID": "bad"}, 400)):
            with self.subTest(status=status): self.assertEqual((await self.send(headers=headers)).status_code, status)
        self.assertEqual(self.calls, [])

    async def test_demo_shortcut_cannot_supply_a_missing_or_invalid_bearer(self):
        with patch.dict(os.environ, {"ENV": "development", "AISOC_DEV_AUTH_BYPASS": "1", "AISOC_PUBLISHED_BIND_ADDRS": "127.0.0.1"}):
            self.assertTrue(is_dev_mode())
            demo = await get_current_user(Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)}), credentials=None, db=self.db)
            demo.require_permission("cases:read"); demo.require_permission("alerts:read")
            for auth in (None, "Basic irrelevant", "Bearer ", "Bearer invalid-not-a-token"):
                headers = {"X-AiSOC-Tenant-ID": TENANT}
                if auth is not None: headers["Authorization"] = auth
                self.assertEqual((await self.send(headers=headers)).status_code, 401)
        self.assertEqual(self.calls, [])

    async def test_both_existing_permissions_are_required(self):
        for scopes in ([], ["cases:read"], ["alerts:read"]):
            async def restricted(): return CurrentUser(UUID(int=42), UUID(TENANT), "admin", "test@example.invalid", scopes=scopes)
            self.app.dependency_overrides[get_current_user] = restricted
            self.assertEqual((await self.send()).status_code, 403)
        self.assertEqual(self.calls, [])

    async def test_current_permissions_and_service_credential_checked_next_request(self):
        scopes = ["cases:read", "alerts:read"]
        async def current(): return CurrentUser(UUID(int=42), UUID(TENANT), "analyst", "test@example.invalid", scopes=list(scopes))
        self.app.dependency_overrides[get_current_user] = current
        self.assertEqual((await self.send()).status_code, 200)
        scopes.remove("alerts:read"); self.assertEqual((await self.send()).status_code, 403)
        self.assertEqual(len(self.calls), 1)
        self.app.dependency_overrides.pop(get_current_user)
        with patch.dict(os.environ, {"AISOC_API_SERVICE_TOKEN": "rotated-test-only-credential-not-live"}):
            self.assertEqual((await self.send()).status_code, 401)
        self.assertEqual(len(self.calls), 1)

    async def test_client_tenant_actor_cannot_override_current_user(self):
        async def current(): return CurrentUser(UUID(int=42), UUID(TENANT), "analyst", "test@example.invalid", scopes=["cases:read", "alerts:read"])
        self.app.dependency_overrides[get_current_user] = current
        self.assertEqual((await self.send(headers={**self.headers, "X-AiSOC-Tenant-ID": OTHER, "X-AiSOC-Actor-ID": str(UUID(int=99))})).status_code, 200)
        self.assertEqual(self.calls[0].headers["X-AiSOC-Tenant-ID"], TENANT)
        self.assertEqual(self.calls[0].headers["X-AiSOC-Actor-ID"], str(UUID(int=42)))

    async def test_overrides_nil_run_invalid_path_and_methods_never_call_backend(self):
        for suffix in ("?owner=all", "?version=old", "?tenant_id=" + OTHER):
            self.assertEqual((await self.send(path=self.path + suffix)).status_code, 400)
        self.assertEqual((await self.client.request("GET", self.path, headers=self.headers, content=b"{}" )).status_code, 400)
        self.assertEqual((await self.send(path="/api/v2/investigation/runs/" + str(UUID(int=0)))).status_code, 400)
        self.assertEqual((await self.send(path="/api/v2/investigation/runs/bad")).status_code, 422)
        self.assertEqual((await self.client.post(self.path, headers=self.headers)).status_code, 405)
        self.assertEqual(self.calls, [])

    async def test_full_checker_failure_is_502_once_without_legacy_fallback(self):
        self.payload["manifest"]["snapshots"]["evidence"]["section"] = "/preparation/evidence_document"
        reseal(self.payload); response = await self.send()
        self.assertEqual(response.status_code, 502); self.assertEqual(len(self.calls), 1)
        self.assertNotIn(READ_AUTH, response.text)

    async def test_status_network_timeout_and_redirect_are_sanitized_once(self):
        for backend, expected in ((404, 404), (409, 409), (400, 502), (401, 502), (403, 502), (302, 502), (500, 503), (502, 503), (503, 503), (504, 503)):
            self.backend_status = backend; before = len(self.calls); response = await self.send()
            self.assertEqual(response.status_code, expected); self.assertEqual(len(self.calls), before + 1)
            self.assertNotIn("PRIVATE", response.text); self.assertNotIn("compatible-read.invalid", response.text)
        for error in (httpx.ReadTimeout("PRIVATE"), httpx.ConnectError("PRIVATE")):
            self.backend_error = error; before = len(self.calls); response = await self.send()
            self.assertEqual(response.status_code, 503); self.assertEqual(len(self.calls), before + 1)

    async def test_malformed_unicode_deep_JSON_and_oversize_are_bounded(self):
        for raw in (b"not json", b"\xff", b"[" * 1200 + b"]" * 1200, b" " * (MAX_BYTES + 1)):
            self.raw = raw; response = await self.send()
            self.assertEqual(response.status_code, 502)
        self.assertEqual(len(self.calls), 4)

    async def test_stream_stops_at_one_MiB_before_parsing_and_closes(self):
        class Stream(httpx.AsyncByteStream):
            count = 0; closed = False
            async def __aiter__(self):
                for _ in range(3):
                    self.count += 1; yield b"x" * (MAX_BYTES // 2 + 1)
            async def aclose(self): self.closed = True
        self.stream = Stream(); response = await self.send()
        self.assertEqual(response.status_code, 502); self.assertEqual(self.stream.count, 2)
        self.assertTrue(self.stream.closed); self.assertEqual(len(self.calls), 1)

    async def test_only_independent_read_and_existing_query_routes(self):
        for path in ("/api/v1/investigations/anything", "/api/v2/investigation/start", "/docs", "/openapi.json"):
            self.assertEqual((await self.send(path=path)).status_code, 404)
        self.assertEqual(self.calls, [])

    async def test_configuration_uses_only_new_explicit_URL_and_token(self):
        with patch.dict(os.environ, {"AISOC_INVESTIGATION_V2_READ_URL": "http://old.invalid", "AISOC_INVESTIGATION_V2_READ_TOKEN": READ_AUTH}, clear=True):
            with self.assertRaises(ValueError): create_app()
        with patch.dict(os.environ, {URL_ENV: "http://compatible.invalid/", TOKEN_ENV: READ_AUTH}, clear=True):
            self.assertIsInstance(CompatibleResultReadGateway.from_environment(), CompatibleResultReadGateway)
        for url in ("", "file:///tmp/test", "http://user:password@host", "http://host?token=bad", "http://host/not-root", "http://host#bad", "http://host:bad", "http://host:99999", "http://ho st"):
            with self.assertRaises(ValueError): CompatibleResultReadGateway(backend_url=url, read_token=READ_AUTH)
        for token in (None, "short", "x" * 257, "x" * 32 + " ", "密" * 40):
            with self.assertRaises(ValueError): CompatibleResultReadGateway(backend_url="http://test.invalid", read_token=token)


if __name__ == "__main__": unittest.main()
