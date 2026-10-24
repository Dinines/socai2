"""Internal v2 read HTTP/auth boundary; mocked reader, no real auth gateway/PG."""
from contextlib import ExitStack
import os
from pathlib import Path
import ssl
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.result_api import create_app, TOKEN_ENV, DSN_ENV, CA_ENV
from app.investigation_v2.execution_state import ExecutionRejected
from app.investigation_v2.execution_store import ExecutionPersistenceError
import test_owned_result_reader_contract as owned_fixtures

TOKEN = "test-only-internal-v2-read-token-64-chars-safe"
TENANT, ACTOR, RUN = (UUID(int=i) for i in (1, 2, 3))
PATH = "/internal/investigation-v2/runs/" + str(RUN)


class ResultAPIContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.payload = dict(schema="owned_fixed_recon_result.v1", tenant_id=str(TENANT), run_id=str(RUN),
            profile="alert_recon", target={"type": "alert", "id": str(UUID(int=4))}, objective="verify_source_network_observation",
            publication_state="not_published", manifest=None, markdown=None, notification=None, legacy_run_status="running")
        self.reader = SimpleNamespace(read=AsyncMock(return_value=self.payload), close=AsyncMock())
        self.app = create_app(reader=self.reader, read_token=TOKEN)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://isolated-read")
        self.headers = {"Authorization": "Bearer " + TOKEN, "X-AiSOC-Tenant-ID": str(TENANT), "X-AiSOC-Actor-ID": str(ACTOR)}

    async def asyncTearDown(self): await self.client.aclose()

    async def test_valid_gateway_identity_calls_owned_reader_only(self):
        response = await self.client.get(PATH, headers=self.headers)
        self.assertEqual(response.status_code, 200);self.assertEqual(response.json(), self.payload)
        kwargs = self.reader.read.await_args.kwargs
        self.assertEqual((kwargs["tenant_id"], kwargs["run_id"]), (TENANT, RUN))
        self.assertEqual(kwargs["current_principal"].tenant_ids, frozenset({TENANT}))
        self.assertIn(str(ACTOR), kwargs["current_principal"].subject)
        self.assertTrue(kwargs["current_principal"].delegated)

    async def test_missing_wrong_or_other_auth_scheme_never_calls_reader(self):
        for authorization in (None, "Bearer wrong", "Basic " + TOKEN):
            headers = {**self.headers}
            if authorization is None: headers.pop("Authorization")
            else: headers["Authorization"] = authorization
            with self.subTest(authorization=authorization): self.assertEqual((await self.client.get(PATH, headers=headers)).status_code, 401)
        self.reader.read.assert_not_awaited()

    async def test_missing_invalid_or_nil_tenant_actor_is_rejected(self):
        for key in ("X-AiSOC-Tenant-ID", "X-AiSOC-Actor-ID"):
            for value in (None, "not-a-uuid", str(UUID(int=0))):
                headers = {**self.headers}
                if value is None: headers.pop(key)
                else: headers[key] = value
                with self.subTest(key=key, value=value): self.assertEqual((await self.client.get(PATH, headers=headers)).status_code, 400)
        self.reader.read.assert_not_awaited()

    async def test_get_body_or_query_cannot_supply_scope_or_owner(self):
        self.assertEqual((await self.client.get(PATH + "?owner=override", headers=self.headers)).status_code, 400)
        self.assertEqual((await self.client.request("GET", PATH, headers=self.headers, json={"scope": "all"})).status_code, 400)
        self.reader.read.assert_not_awaited()

    async def test_current_token_is_checked_on_every_request(self):
        self.assertEqual((await self.client.get(PATH, headers=self.headers)).status_code, 200)
        self.app.state.read_token = "replacement-internal-v2-read-token-64-chars-safe"
        self.assertEqual((await self.client.get(PATH, headers=self.headers)).status_code, 401)
        self.assertEqual(self.reader.read.await_count, 1)

    async def test_owned_missing_integrity_and_persistence_errors_are_sanitized(self):
        for error, status in ((ExecutionRejected("owned Run not found"), 404), (ExecutionRejected("PRIVATE_SOURCE_DETAIL"), 409), (ExecutionPersistenceError("PRIVATE_DRIVER_DETAIL"), 503)):
            self.reader.read.side_effect = error
            response = await self.client.get(PATH, headers=self.headers)
            with self.subTest(status=status):
                self.assertEqual(response.status_code, status);self.assertNotIn("PRIVATE", response.text);self.assertNotIn(TOKEN, response.text)

    async def test_wrong_response_tenant_run_or_schema_never_leaks_payload(self):
        for key, value in (("tenant_id", str(UUID(int=99))), ("run_id", str(UUID(int=99))), ("schema", "legacy.v1")):
            self.reader.read.return_value = {**self.payload, key: value, "private": "PRIVATE_WRONG_OWNER"}
            response = await self.client.get(PATH, headers=self.headers)
            with self.subTest(key=key):self.assertEqual(response.status_code, 502);self.assertNotIn("PRIVATE", response.text)

    async def test_old_paths_start_and_docs_are_absent(self):
        for path in ("/api/v1/investigations", "/api/investigate", "/docs", "/openapi.json"):
            self.assertEqual((await self.client.get(path)).status_code, 404)
        self.assertEqual((await self.client.post(PATH, headers=self.headers)).status_code, 405)
        self.reader.read.assert_not_awaited()

    async def test_explicit_token_is_required_without_old_or_dev_fallback(self):
        with patch.dict(os.environ, {"AISOC_SERVICE_TOKEN": TOKEN, "AISOC_DEV_MODE": "1"}, clear=True):
            with self.assertRaises(ValueError): create_app(reader=self.reader)
        for token in ("", "short", " " * 32):
            with self.assertRaises(ValueError): create_app(reader=self.reader, read_token=token)

    async def test_injected_reader_is_not_closed_and_no_pool_is_created(self):
        with patch("asyncpg.create_pool", new=AsyncMock(side_effect=AssertionError("no pool"))) as pool:
            async with self.app.router.lifespan_context(self.app): self.assertIs(self.app.state.reader, self.reader)
        pool.assert_not_awaited();self.reader.close.assert_not_awaited()

    async def test_owned_pool_uses_explicit_tls_bounded_config_and_is_closed(self):
        pool = SimpleNamespace(close=AsyncMock(), terminate=Mock())
        with patch.dict(os.environ, {DSN_ENV: "postgresql://test-only:test-only@localhost/test_only"}, clear=True):
            with patch("asyncpg.create_pool", new=AsyncMock(return_value=pool)) as created:
                app = create_app(read_token=TOKEN)
                async with app.router.lifespan_context(app): self.assertIsNotNone(app.state.reader)
        kwargs = created.await_args.kwargs
        self.assertEqual((kwargs["min_size"], kwargs["max_size"], kwargs["command_timeout"]), (1, 2, 10))
        self.assertEqual(kwargs["ssl"].verify_mode, ssl.CERT_REQUIRED);self.assertTrue(kwargs["ssl"].check_hostname)
        pool.close.assert_awaited_once();pool.terminate.assert_not_called();self.assertIsNone(app.state.reader)

    async def test_no_old_database_fallback_when_explicit_pg_is_absent(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test-only:test-only@localhost/old_test_only"}, clear=True):
            app = create_app(read_token=TOKEN)
            with self.assertRaises(ValueError):
                async with app.router.lifespan_context(app): pass

    async def test_http_to_actual_owned_reader_returns_frozen_manifest_without_new_rows(self):
        fixture = owned_fixtures.OwnedResultReaderContractTests();await fixture.asyncSetUp()
        saved = await fixture.store.publish(fixture.request);before = fixture.snapshot()
        app = create_app(reader=fixture.reader, read_token=TOKEN)
        headers = {**self.headers, "X-AiSOC-Tenant-ID": str(fixture.store.tenant_id)}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated-read") as client:
            response = await client.get("/internal/investigation-v2/runs/" + str(fixture.store.run_id), headers=headers)
            missing = await client.get("/internal/investigation-v2/runs/" + str(UUID(int=99)), headers=headers)
        self.assertEqual(response.status_code, 200);self.assertEqual(missing.status_code, 404)
        for key in ("manifest", "manifest_artifact", "execution_snapshot", "markdown"): self.assertEqual(response.json()[key], saved[key])
        self.assertEqual(fixture.snapshot(), before)


if __name__ == "__main__": unittest.main()
