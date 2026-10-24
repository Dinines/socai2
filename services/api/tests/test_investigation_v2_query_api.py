"""New HTTP surface: actual auth/permission code, fake PG/CH, no network."""
from copy import deepcopy
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from app.api.v1.deps import CurrentUser, get_current_user
from app.db.database import get_db
from app.investigation_v2.query_api import create_app
from app.investigation_v2 import records
from test_investigation_records import ARGS, OTHER, TENANT, response, row

SERVICE = "unit-test-only-v2-query-service-not-a-live-credential"
PATH = "/api/v2/investigation/query"


class FakeReadSession:
    def __init__(self):
        self.calls = []

    async def execute(self, statement):
        values = statement.compile().params
        self.calls.append(values)
        exists = UUID(TENANT) if UUID(TENANT) in values.values() else None
        return SimpleNamespace(scalar_one_or_none=lambda: exists)


class V2QueryAPIContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {"ENV": "production", "AISOC_DEV_MODE": "0", "AISOC_API_SERVICE_TOKEN": SERVICE})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.db = FakeReadSession()
        self.app = create_app()
        async def read_session():
            yield self.db
        self.app.dependency_overrides[get_db] = read_session
        self.backend = AsyncMock(return_value=response([row()]))
        self.backend_patch = patch.object(records, "execute_lake_query", self.backend)
        self.backend_patch.start()
        self.addCleanup(self.backend_patch.stop)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://v2-test.invalid")
        self.addAsyncCleanup(self.client.aclose)

    @property
    def headers(self):
        return {"Authorization": "Bearer " + SERVICE, "X-AiSOC-Tenant-ID": TENANT}

    async def send(self, *, body=None, headers=None, path=PATH):
        return await self.client.post(path, json=body or {"tool": "activity_records", "args": deepcopy(ARGS)},
                                      headers=self.headers if headers is None else headers)

    async def test_actual_service_auth_tenant_and_new_dispatch_are_used(self):
        result = await self.send()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["status"], "ok")
        self.assertEqual(result.json()["rows"][0]["tenant_id"], TENANT)
        self.assertEqual(self.backend.await_count, 1)
        self.assertEqual(self.backend.call_args.kwargs["params"]["tenant_id"], TENANT)
        self.assertEqual(len(self.db.calls), 1)

    async def test_missing_or_bad_identity_never_reaches_clickhouse(self):
        for headers, status in (({}, 401), ({"Authorization": "Bearer " + SERVICE}, 403),
                                ({**self.headers, "X-AiSOC-Tenant-ID": "not-a-uuid"}, 400),
                                ({**self.headers, "X-AiSOC-Tenant-ID": OTHER}, 403)):
            with self.subTest(status=status):
                result = await self.send(headers=headers)
                self.assertEqual(result.status_code, status)
        self.assertEqual(self.backend.await_count, 0)

    async def test_permission_check_blocks_a_verified_principal_without_lake_scope(self):
        async def restricted():
            return CurrentUser(UUID(TENANT), UUID(TENANT), "api_service", "unit@example.invalid", scopes=[])
        self.app.dependency_overrides[get_current_user] = restricted
        result = await self.send()
        self.assertEqual(result.status_code, 403)
        self.assertEqual(self.backend.await_count, 0)

    async def test_top_level_identity_and_untrusted_arguments_are_refused(self):
        result = await self.send(body={"tool": "activity_records", "args": ARGS, "tenant_id": OTHER})
        self.assertEqual(result.status_code, 422)
        for added in ({"tenant_id": OTHER}, {"sql": "SELECT *"}, {"url": "http://other.invalid"}, {"headers": {}}):
            result = await self.send(body={"tool": "activity_records", "args": {**ARGS, **added}})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["status"], "rejected")
        self.assertEqual(self.backend.await_count, 0)

    async def test_only_the_new_path_exists_and_no_legacy_tool_fallback(self):
        for path in ("/api/v1/investigate/query", "/api/v1/investigation/query", "/openapi.json", "/docs"):
            self.assertEqual((await self.send(path=path)).status_code, 404)
        result = await self.send(body={"tool": "network_connections", "args": ARGS})
        self.assertEqual(result.json()["reason"], "unknown_v2_tool")
        self.assertEqual(self.backend.await_count, 0)

    async def test_original_records_global_bounds_still_apply(self):
        for changes in ({"limit": 51}, {"end": "2026-10-25T10:00:00Z"}, {"start": "no-timezone"}):
            result = await self.send(body={"tool": "activity_records", "args": {**ARGS, **changes}})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["status"], "rejected")
        self.assertEqual(self.backend.await_count, 0)

    async def test_lifespan_only_closes_owned_clients_without_schema_or_worker_start(self):
        from app.investigation_v2 import query_api
        engine = SimpleNamespace(dispose=AsyncMock())
        with patch.object(query_api.clickhouse, "close_clickhouse", new_callable=AsyncMock) as close_lake, \
                patch.object(query_api.database, "engine", engine):
            async with self.app.router.lifespan_context(self.app):
                self.assertEqual(self.backend.await_count, 0)
            close_lake.assert_awaited_once()
            engine.dispose.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
