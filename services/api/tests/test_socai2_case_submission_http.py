"""Public Case admission wiring; core persistence is substituted here."""
import asyncio
import json
from pathlib import Path
from uuid import UUID

import pytest
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_store import StoreError
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.analysis_submissions import AnalysisSubmissionBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.dependencies import analysis_submission_service
from investigation_http.main import app

TENANT, ACTOR, CASE, TASK, KEY = (UUID(int=i) for i in range(7201, 7206))
POLICY = Path(__file__).resolve().parents[3] / "deploy/local-investigation/analysis-tasks.json"


@pytest.fixture
def transport(monkeypatch):
    policy = AnalysisTaskPolicy(**json.loads(POLICY.read_text()))
    monkeypatch.setattr(app.state, "business_context", BusinessContext(TENANT, ACTOR, "Case submission fixture"), raising=False)
    monkeypatch.setitem(app.dependency_overrides, analysis_submission_service,
        lambda: AnalysisSubmissionBackend(None, policy=policy))
    return ASGITransport(app=app)


@pytest.mark.parametrize("mode", ["check", "rerun"])
def test_public_case_post_passes_only_business_intent(monkeypatch, transport, mode):
    calls = []

    async def submit(self, tenant_id, **request):
        calls.append((tenant_id, request))
        return {"task_id": TASK, "subject_type": "case", "subject_id": CASE, "status": "accepted"}

    monkeypatch.setattr(AnalysisTaskService, "submit", submit)

    async def check():
        async with AsyncClient(transport=transport, base_url="http://isolated.local") as client:
            response = await client.post(f"/api/v1/socai2/cases/{CASE}/investigations",
                json={"operation_key": str(KEY), "mode": mode})
        assert "authorization" not in response.request.headers
        assert response.status_code == 202, response.text
        assert response.json() == {"task_id": str(TASK), "subject_type": "case", "subject_id": str(CASE),
            "status": "accepted", "status_url": f"/api/v1/socai2/cases/{CASE}/analysis-tasks/{TASK}"}
        assert calls == [(TENANT, {"kind": "case_investigation", "subject_id": CASE,
            "intent": mode, "source": "user", "operation_key": KEY, "submitted_by": ACTOR})]

    asyncio.run(check())


def test_public_case_submission_rejects_old_execution_and_identity_parameters(monkeypatch, transport):
    async def unexpected(*args, **kwargs):
        raise AssertionError("Invalid input reached admission")

    monkeypatch.setattr(AnalysisTaskService, "submit", unexpected)

    async def check():
        path = f"/api/v1/socai2/cases/{CASE}/investigations"
        body = {"operation_key": str(KEY), "mode": "check"}
        async with AsyncClient(transport=transport, base_url="http://isolated.local") as client:
            invalid = [{}, {**body, "mode": "initial"}, {**body, "operation_key": "bad"}]
            invalid += [{**body, key: value} for key, value in (
                ("expected_scope_revision", 1), ("comparison_result_id", str(TASK)),
                ("window_start", "2026-11-15T00:00:00Z"), ("tenant_id", str(TENANT)),
                ("actor_id", str(ACTOR)), ("kind", "case_investigation"))]
            for value in invalid:
                response = await client.post(path, json=value)
                assert response.status_code == 422
            response = await client.post(path + "?mode=check", json=body)
            assert response.status_code == 422 and response.json()["detail"]["code"] == "invalid_input"

    asyncio.run(check())


@pytest.mark.parametrize("code,status,expected", [
    ("operation_key_conflict", 409, "operation_conflict"),
    ("subject_scope_empty", 409, "empty_scope"),
    ("subject_closed", 409, "subject_closed"),
    ("subject_not_found", 404, "subject_not_found"),
    ("service_unavailable", 503, "service_unavailable"),
])
def test_public_case_admission_preserves_business_failure(monkeypatch, transport, code, status, expected):
    async def fail(*args, **kwargs):
        raise StoreError(code, status)

    monkeypatch.setattr(AnalysisTaskService, "submit", fail)

    async def check():
        async with AsyncClient(transport=transport, base_url="http://isolated.local") as client:
            response = await client.post(f"/api/v1/socai2/cases/{CASE}/investigations",
                json={"operation_key": str(KEY), "mode": "check"})
        assert response.status_code == status
        assert response.json()["detail"]["code"] == expected
        assert "task_id" not in response.json()

    asyncio.run(check())
