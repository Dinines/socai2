"""Direct ASGI reservation contract checks; no PG, model, or Tool is used."""
import unittest
from unittest.mock import patch
from uuid import UUID

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_case_ai as api
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

CASE = UUID(int=1)
MESSAGE = UUID(int=2)
RESULT = UUID(int=3)
OP = str(UUID(int=4))
BASE = f"/api/v1/socai2/cases/{CASE}"
REQUESTS = (
    (f"{BASE}/ai/messages", {"operation_key": OP, "question": "现有证据有什么限制？"}),
    (f"{BASE}/ai/messages/{MESSAGE}/save", {"operation_key": OP, "title": "待核实事实", "conclusion": "需要人工确认授权"}),
    (f"{BASE}/results/{RESULT}/adopt", {"operation_key": OP, "expected_scope_revision": 1}),
)


class ReservedCaseAITest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.principal = CurrentUser(UUID(int=5), UUID(int=6), "admin", "synthetic@example.invalid",
                                     scopes=["cases:write"])
        self.app = FastAPI()
        self.app.include_router(api.router, prefix="/api/v1")

        async def current_user():
            return self.principal

        self.app.dependency_overrides[get_current_user] = current_user
        self.client = AsyncClient(transport=ASGITransport(app=self.app), base_url="http://synthetic.local")
        self.enabled = patch.object(api.settings, "SOCAI2_CASE_API_ENABLED", True)
        self.enabled.start()
        self.addCleanup(self.enabled.stop)

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_reservations_do_not_create_or_execute(self):
        # Every business entry remains forbidden; auth is substituted separately.
        with patch("app.db.database.AsyncSessionLocal", side_effect=AssertionError("business DB used")), \
             patch("app.socai2.case_service.CaseService", side_effect=AssertionError("Case service used")):
            for path, body in REQUESTS:
                with self.subTest(path=path):
                    first = await self.client.post(path, json=body)
                    second = await self.client.post(path, json=body)
                    self.assertEqual(first.status_code, 501)
                    self.assertEqual(first.json(), second.json())
                    detail = first.json()["detail"]
                    self.assertEqual(detail["code"], "case_ai_not_implemented")
                    self.assertEqual(detail["status"], "not_implemented")
                    self.assertEqual(set(detail), {"code", "status", "message"})

    async def test_access_and_disabled_boundaries(self):
        for path, body in REQUESTS:
            with self.subTest(path=path, boundary="disabled"), patch.object(api.settings, "SOCAI2_CASE_API_ENABLED", False):
                response = await self.client.post(path, json=body)
                self.assertEqual(response.status_code, 503)
            with self.subTest(path=path, boundary="read_only"):
                self.principal.scopes = ["cases:read"]
                self.assertEqual((await self.client.post(path, json=body)).status_code, 403)
                self.principal.scopes = ["cases:write"]
            with self.subTest(path=path, boundary="workload"):
                self.principal.workload_service = "synthetic-worker"
                self.assertEqual((await self.client.post(path, json=body)).status_code, 403)
                self.principal.workload_service = None

        async def unauthenticated():
            raise HTTPException(401, "authentication_required")

        self.app.dependency_overrides[get_current_user] = unauthenticated
        for path, body in REQUESTS:
            with self.subTest(path=path, boundary="unauthenticated"):
                self.assertEqual((await self.client.post(path, json=body)).status_code, 401)

    async def test_request_validation_and_openapi(self):
        for path, body in REQUESTS:
            with self.subTest(path=path, boundary="tenant_injection"):
                self.assertEqual((await self.client.post(path, json={**body, "tenant_id": str(UUID(int=7))})).status_code, 422)
        self.assertEqual((await self.client.post(REQUESTS[0][0], json={"operation_key": OP, "question": "   "})).status_code, 422)
        self.assertEqual((await self.client.post(REQUESTS[2][0], json={"operation_key": OP, "expected_scope_revision": -1})).status_code, 422)
        schema = self.app.openapi()
        self.assertEqual(len(schema["paths"]), 3)
        for path in schema["paths"].values():
            self.assertIn("501", path["post"]["responses"])
            self.assertNotIn("200", path["post"]["responses"])


if __name__ == "__main__":
    unittest.main()
