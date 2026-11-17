"""Direct allocation transport checks; core substitutes, no database execution."""
import asyncio
from uuid import UUID

import pytest
from app.socai2.baseline_store import StoreError
from app.socai2.case_allocation_contracts import (
    CaseAllocationReceipt,
    CaseMoveReceipt,
    CaseReplacementReceipt,
)
from app.socai2.case_service import CaseService
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.services import CaseBackend
from investigation_http.dependencies import case_service
from investigation_http.main import app

TENANT, ACTOR, CASE, NEXT, ALERT, EXCLUDED, TASK, KEY = (UUID(int=n) for n in range(1, 9))


def allocation():
    return CaseAllocationReceipt(operation_key=KEY, requested_case_id=CASE, primary_case_id=CASE,
        continuation_root_case_id=CASE, receiving_case_id=NEXT, changed=True,
        allocations=[{"case_id": CASE, "scope_revision": 2, "created": False, "changed": False,
            "previous_case_id": None, "added_alert_ids": [], "existing_alert_ids": [ALERT],
            "linked_incident_ids": [], "initial_task": None},
            {"case_id": NEXT, "scope_revision": 1, "created": True, "changed": True, "previous_case_id": CASE,
                "added_alert_ids": [UUID(int=11)], "existing_alert_ids": [], "linked_incident_ids": [],
                "initial_task": {"task_id": TASK, "subject_id": NEXT}}],
        incident_receivers=[], excluded_alert_ids=[EXCLUDED])


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.setattr(app.state, "business_context", BusinessContext(TENANT, ACTOR, "Configured recorder"), raising=False)
    monkeypatch.setitem(app.dependency_overrides, case_service, lambda: CaseBackend(None))
    return ASGITransport(app=app)


@pytest.mark.parametrize("operation,method,path,status", [
    ("create_case", "POST", "/cases", 201),
    ("associate", "POST", f"/cases/{CASE}/associations", 200),
    ("change_members", "PUT", f"/cases/{CASE}/members", 200),
    ("move_members", "POST", f"/cases/{CASE}/members/move", 200),
])
def test_real_route_serializes_actual_allocation_identity(monkeypatch, transport, operation, method, path, status):
    core = allocation()
    body = {"operation_key": str(KEY), "alert_ids": [str(ALERT)]}
    if operation == "create_case":
        body["title"] = "Synthetic case"
        core = core.model_copy(update={"requested_case_id": None})
    elif operation == "move_members":
        body.update(target_case_id=str(NEXT), expected_source_scope_revision=1, expected_target_scope_revision=1)
    else:
        body["expected_scope_revision"] = 1
    if operation == "change_members":
        body["alert_ids"] = []  # Empty replacement is valid; creation remains nonempty.
    removal = {"case_id": CASE, "scope_revision": 2, "removed_alert_ids": [ALERT], "changed": True}
    result = (CaseMoveReceipt(source=removal, allocation=core, moved_alert_ids=[ALERT]) if operation == "move_members"
        else CaseReplacementReceipt(source=removal, allocation=core) if operation == "change_members" else core)
    saved = result.model_dump(mode="json")
    calls = []

    async def substitute(self, tenant_id, *args, actor):
        calls.append((tenant_id, args, actor))
        return result

    monkeypatch.setattr(CaseService, operation, substitute)

    async def check():
        async with AsyncClient(transport=transport, base_url="http://isolated.local") as client:
            response = await client.request(method, "/api/v1/socai2" + path, json=body)
        assert "authorization" not in response.request.headers
        assert response.status_code == status, response.text
        value = response.json()
        public = value.get("allocation", value)
        expected = core.model_dump(mode="json")
        for item in public["allocations"]:
            assert item.pop("case_url") == f"/api/v1/socai2/cases/{item['case_id']}"
            if task := item["initial_task"]:
                assert task.pop("status_url") == f"/api/v1/socai2/cases/{NEXT}/analysis-tasks/{TASK}"
        assert public == expected
        if "allocation" in value:
            assert value["source"] == saved["source"]
        if operation == "move_members":
            assert value["moved_alert_ids"] == saved["moved_alert_ids"]
        assert result.model_dump(mode="json") == saved, "HTTP must not rewrite the core receipt"
        assert len(calls) == 1 and calls[0][0] == TENANT and calls[0][2].user_id == ACTOR
        if operation == "change_members":
            assert calls[0][1][-1].alert_ids == []

    asyncio.run(check())


@pytest.mark.parametrize("core_code,status,public_code,public_status", [
    ("operation_key_conflict", 409, "operation_conflict", 409),
    ("case_scope_revision_conflict", 409, "scope_conflict", 409),
    ("resolved_case_scope_policy_not_enabled", 409, "subject_closed", 409),
    ("case_incident_members_unavailable", 409, "empty_scope", 409),
    ("case_not_found", 404, "case_not_found", 404),
    ("case_actor_not_in_tenant", 403, "service_unavailable", 503),
])
def test_allocation_business_errors_are_not_authentication(monkeypatch, transport, core_code, status, public_code, public_status):
    async def fail(*args, **kwargs):
        raise StoreError(core_code, status)
    monkeypatch.setattr(CaseService, "create_case", fail)

    async def check():
        async with AsyncClient(transport=transport, base_url="http://isolated.local") as client:
            response = await client.post("/api/v1/socai2/cases", json={
                "operation_key": str(KEY), "title": "Synthetic", "alert_ids": [str(ALERT)]})
        assert response.status_code == public_status
        assert response.json()["detail"]["code"] == public_code
    asyncio.run(check())


def test_allocation_input_rejected_before_core(monkeypatch, transport):
    async def unexpected(*args, **kwargs):
        raise AssertionError("Invalid request reached the core")
    monkeypatch.setattr(CaseService, "create_case", unexpected)

    async def check():
        body = {"operation_key": str(KEY), "title": "Synthetic", "alert_ids": [str(ALERT)]}
        async with AsyncClient(transport=transport, base_url="http://isolated.local") as client:
            for path, value in [("/cases?extra=yes", body), ("/cases", {**body, "run_id": str(TASK)}),
                                ("/cases", {**body, "alert_ids": []})]:
                response = await client.post("/api/v1/socai2" + path, json=value)
                assert response.status_code == 422
    asyncio.run(check())
