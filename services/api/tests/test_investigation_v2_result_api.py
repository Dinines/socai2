"""Actual API auth/permissions and gateway checks with PG/HTTP transports fake."""
from copy import deepcopy
import hashlib
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
from app.investigation_v2.result_api import create_app
from app.investigation_v2.result_gateway import ResultReadGateway, URL_ENV, TOKEN_ENV
from test_investigation_v2_query_api import FakeReadSession
from test_investigation_records import TENANT, OTHER

API_AUTH = "test-only-api-result-service-credential-not-live"
READ_AUTH = "test-only-internal-read-credential-not-live"
RUN, ALERT = UUID(int=600), UUID(int=700)
PATH = "/api/v2/investigation/runs/" + str(RUN)


def encoded(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def sha(value): return hashlib.sha256(value).hexdigest()


def seal(payload):
    manifest = payload["manifest"]
    manifest.pop("manifest_ref", None)
    manifest["manifest_ref"] = "recon-manifest:" + sha(encoded(manifest))
    payload["manifest_artifact"]["sha256"] = sha(encoded(manifest))


def published():
    execution = dict(schema="fixed_recon_publication_execution.v1", tenant_id=TENANT, run_id=str(RUN),
        mapping_version="fixed_recon_publication_state.v1", runtime_version="fixed_alert_recon_runtime.v1",
        runtime_plan_ref="fixed-recon-plan:" + "a" * 64, scope_hash="b" * 64,
        run_state="finished", investigation_completeness="complete_for_scope", continuation="none")
    markdown = "# 有限来源核对\n\n来源结果unknown；性质未定，授权未知。\n"
    manifest = dict(schema="fixed_recon_result_manifest.v1", publication_state="published", tenant_id=TENANT,
        run_id=str(RUN), profile="alert_recon", objective="verify_source_network_observation", target={"type": "alert", "id": str(ALERT)},
        version=1, investigation_id=str(RUN), previous_manifest_ref=None, retention={"publication_artifacts": "committed"},
        renderer_version="fixed_recon_markdown.v1", mapping_version="fixed_recon_publication_state.v1", sections_version="fixed_recon_handoff_sections.v1",
        runtime_version=execution["runtime_version"], runtime_plan_ref=execution["runtime_plan_ref"], scope_hash=execution["scope_hash"], completion_policy_ref="bounded_full_window_source_check.v1",
        snapshots={"execution": {"artifact_id": str(UUID(int=1)), "sha256": sha(encoded(execution)), "artifact_schema": execution["schema"]}},
        report={"artifact_id": str(UUID(int=2)), "sha256": sha(markdown.encode()), "renderer_version": "fixed_recon_markdown.v1", "media_type": "text/markdown"})
    payload = dict(schema="owned_fixed_recon_result.v1", tenant_id=TENANT, run_id=str(RUN), profile="alert_recon", target=deepcopy(manifest["target"]),
        objective=manifest["objective"], legacy_run_status="running", publication_state="published", manifest=manifest,
        manifest_artifact={"artifact_id": str(UUID(int=3)), "sha256": ""}, execution_snapshot=execution,
        markdown=markdown, retention="committed", notification=None)
    seal(payload)
    return payload


class ResultGatewayAPIContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {"ENV": "production", "AISOC_DEV_MODE": "0", "AISOC_API_SERVICE_TOKEN": API_AUTH})
        self.env.start();self.addCleanup(self.env.stop)
        self.payload, self.calls, self.backend_status, self.backend_error = published(), [], 200, None
        async def backend(request):
            self.calls.append(request)
            if self.backend_error: raise self.backend_error
            return httpx.Response(self.backend_status, json=self.payload if self.backend_status == 200 else {"detail": "PRIVATE_BACKEND_TOKEN_DSN"},
                                  headers={"Location": "http://untrusted.invalid/"} if self.backend_status == 302 else None)
        self.gateway = ResultReadGateway(backend_url="http://internal-read.invalid", read_token=READ_AUTH, transport=httpx.MockTransport(backend))
        self.app = create_app(gateway=self.gateway)
        self.db = FakeReadSession()
        async def db_session(): yield self.db
        self.app.dependency_overrides[get_db] = db_session
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://api-result")
        self.addAsyncCleanup(self.client.aclose)

    @property
    def headers(self): return {"Authorization": "Bearer " + API_AUTH, "X-AiSOC-Tenant-ID": TENANT}

    async def send(self, *, headers=None, path=PATH): return await self.client.get(path, headers=self.headers if headers is None else headers)

    async def test_actual_service_auth_and_both_read_permissions_reach_internal_get(self):
        response = await self.send()
        self.assertEqual(response.status_code, 200);self.assertEqual(response.json(), self.payload)
        request = self.calls[0]
        self.assertEqual(request.method, "GET");self.assertEqual(request.url.path, "/internal/investigation-v2/runs/" + str(RUN))
        self.assertEqual(request.headers["Authorization"], "Bearer " + READ_AUTH)
        self.assertNotIn(API_AUTH, request.headers["Authorization"])
        self.assertEqual(request.headers["X-AiSOC-Tenant-ID"], TENANT)
        self.assertEqual(len(self.db.calls), 1)

    async def test_missing_bad_or_unknown_tenant_auth_never_forwards(self):
        for headers, status in (({}, 401), ({"Authorization": "Bearer " + API_AUTH}, 403),
                                ({**self.headers, "X-AiSOC-Tenant-ID": "invalid"}, 400), ({**self.headers, "X-AiSOC-Tenant-ID": OTHER}, 403)):
            with self.subTest(status=status): self.assertEqual((await self.send(headers=headers)).status_code, status)
        self.assertEqual(self.calls, [])

    async def test_dev_bypass_cannot_supply_missing_empty_basic_or_bad_bearer(self):
        with patch.dict(os.environ, {"ENV": "development", "AISOC_DEV_AUTH_BYPASS": "1", "AISOC_PUBLISHED_BIND_ADDRS": "127.0.0.1"}):
            self.assertTrue(is_dev_mode())
            demo = await get_current_user(Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)}), credentials=None, db=self.db)
            demo.require_permission("cases:read");demo.require_permission("alerts:read")
            for authorization in (None, "Bearer ", "Basic irrelevant", "Bearer invalid-not-a-token"):
                headers = {"X-AiSOC-Tenant-ID": TENANT}
                if authorization is not None: headers["Authorization"] = authorization
                with self.subTest(authorization=authorization): self.assertEqual((await self.send(headers=headers)).status_code, 401)
        self.assertEqual(self.calls, [])

    async def test_each_permission_is_required_without_widening_api_key_scopes(self):
        for scopes in ([], ["cases:read"], ["alerts:read"]):
            async def restricted(): return CurrentUser(UUID(int=42), UUID(TENANT), "admin", "test@example.invalid", scopes=scopes)
            self.app.dependency_overrides[get_current_user] = restricted
            with self.subTest(scopes=scopes): self.assertEqual((await self.send()).status_code, 403)
        self.assertEqual(self.calls, [])

    async def test_permission_is_checked_again_for_next_request(self):
        scopes = ["cases:read", "alerts:read"]
        async def current(): return CurrentUser(UUID(int=42), UUID(TENANT), "analyst", "test@example.invalid", scopes=list(scopes))
        self.app.dependency_overrides[get_current_user] = current
        self.assertEqual((await self.send()).status_code, 200)
        scopes.remove("alerts:read")
        self.assertEqual((await self.send()).status_code, 403);self.assertEqual(len(self.calls), 1)

    async def test_forged_headers_do_not_override_current_user_tenant_or_actor(self):
        async def current(): return CurrentUser(UUID(int=42), UUID(TENANT), "analyst", "test@example.invalid", scopes=["cases:read", "alerts:read"])
        self.app.dependency_overrides[get_current_user] = current
        self.assertEqual((await self.send(headers={**self.headers, "X-AiSOC-Tenant-ID": OTHER, "X-AiSOC-Actor-ID": str(UUID(int=99))})).status_code, 200)
        self.assertEqual(self.calls[0].headers["X-AiSOC-Tenant-ID"], TENANT)
        self.assertEqual(self.calls[0].headers["X-AiSOC-Actor-ID"], str(UUID(int=42)))

    async def test_body_query_or_owner_overrides_are_refused_without_backend_call(self):
        self.assertEqual((await self.send(path=PATH + "?owner=all")).status_code, 400)
        response = await self.client.request("GET", PATH, headers=self.headers, json={"scope": "all"})
        self.assertEqual(response.status_code, 400);self.assertEqual(self.calls, [])

    async def test_backend_tenant_run_schema_profile_or_extra_fields_are_rejected(self):
        original = deepcopy(self.payload)
        for key, value in (("tenant_id", OTHER), ("run_id", str(UUID(int=99))), ("schema", "legacy"), ("profile", "case_investigation"), ("extra", "PRIVATE_UNEXPECTED")):
            self.payload = {**deepcopy(original), key: value}
            response = await self.send()
            with self.subTest(key=key): self.assertEqual(response.status_code, 502);self.assertNotIn("PRIVATE", response.text)

    async def test_md_manifest_artifact_execution_or_policy_version_mismatch_is_rejected(self):
        original = deepcopy(self.payload)
        for changed in ("markdown", "manifest_ref", "manifest_artifact", "execution", "mapping_version", "execution_ref_schema", "renderer"):
            self.payload = deepcopy(original)
            if changed == "markdown": self.payload["markdown"] += "未经采用的结论"
            elif changed == "manifest_ref": self.payload["manifest"]["manifest_ref"] = "recon-manifest:" + "0" * 64
            elif changed == "manifest_artifact": self.payload["manifest_artifact"]["sha256"] = "0" * 64
            elif changed == "execution": self.payload["execution_snapshot"]["run_state"] = "cancelled"
            elif changed == "mapping_version": self.payload["manifest"]["mapping_version"] = "future.v99";seal(self.payload)
            elif changed == "execution_ref_schema": self.payload["manifest"]["snapshots"]["execution"]["artifact_schema"] = "wrong";seal(self.payload)
            else: self.payload["manifest"]["report"]["renderer_version"] = "wrong";seal(self.payload)
            with self.subTest(changed=changed): self.assertEqual((await self.send()).status_code, 502)

    async def test_unpublished_progress_has_no_formal_md_and_is_preserved(self):
        for key in ("execution_snapshot",): self.payload.pop(key)
        self.payload.update(publication_state="not_published", manifest=None, manifest_artifact=None, markdown=None,
            retention="progress_only", candidate=None, progress={"phase": "ready"}, delivery_gap="result_not_published")
        self.assertEqual((await self.send()).json(), self.payload)
        self.payload["markdown"] = "old report"
        self.assertEqual((await self.send()).status_code, 502)

    async def test_downstream_status_and_timeout_are_sanitized_without_retry_or_redirect(self):
        for backend, expected in ((404, 404), (409, 409), (401, 502), (302, 502), (503, 503)):
            self.backend_status = backend;before = len(self.calls);response = await self.send()
            with self.subTest(backend=backend):
                self.assertEqual(response.status_code, expected);self.assertNotIn("PRIVATE", response.text);self.assertEqual(len(self.calls), before + 1)
        self.backend_error = httpx.ReadTimeout("PRIVATE_TIMEOUT_ENDPOINT")
        before = len(self.calls);response = await self.send()
        self.assertEqual(response.status_code, 503);self.assertNotIn("PRIVATE", response.text);self.assertEqual(len(self.calls), before + 1)

    async def test_only_explicit_new_read_path_is_registered(self):
        for path in ("/api/v1/investigations/" + str(RUN), "/api/v2/investigation/start", "/docs", "/openapi.json"):
            self.assertEqual((await self.send(path=path)).status_code, 404)
        self.assertEqual((await self.client.post(PATH, headers=self.headers)).status_code, 405)
        self.assertEqual(self.calls, [])

    async def test_backend_configuration_never_uses_old_url_or_token_defaults(self):
        with patch.dict(os.environ, {"AISOC_SERVICE_TOKEN": READ_AUTH, "AGENTS_URL": "http://old.invalid", "AISOC_DEV_MODE": "1"}, clear=True):
            with self.assertRaises(ValueError): create_app()
        for url in ("file:///tmp/test", "http://user:password@host", "http://host?token=bad", "http://host/not-root"):
            with self.assertRaises(ValueError): ResultReadGateway(backend_url=url, read_token=READ_AUTH)


if __name__ == "__main__": unittest.main()
