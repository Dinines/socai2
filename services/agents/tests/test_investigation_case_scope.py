"""Default Case investigation ownership survives the temporary route allowlist."""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import investigate
from app.core.scoped_baseline import apply_scope
from app.security.tenant_scope import TenantPrincipal


def principal(tenant):
    return TenantPrincipal(tenant_ids=frozenset({tenant}), subject="investigation-test")


def owned_cases(monkeypatch, rows):
    calls = []

    class Connection:
        async def fetchval(self, query, case_id, tenant_id):
            calls.append((case_id, tenant_id))
            assert "id=$1 AND tenant_id=$2" in query
            return (case_id, tenant_id) in rows

    class Pool:
        @asynccontextmanager
        async def acquire(self):
            yield Connection()

    monkeypatch.setattr(investigate.ledger, "get_pool", AsyncMock(return_value=Pool()))
    return calls


@pytest.mark.parametrize("baseline", ["0", "1"])
@pytest.mark.asyncio
async def test_launch_uses_the_authenticated_tenant_and_owned_case(monkeypatch, baseline):
    monkeypatch.setenv("AISOC_SCOPED_BASELINE", baseline)
    tenant, case_id = uuid4(), uuid4()
    calls = owned_cases(monkeypatch, {(case_id, tenant)})
    tasks = BackgroundTasks()
    body = investigate.InvestigateRequest(alert_summary="Marked alert", raw_alert={"marker": "case-scope"})
    result = await investigate.launch_investigation(str(case_id), body, tasks, principal(tenant))
    try:
        assert calls == [(case_id, tenant)]
        assert result.case_id == str(case_id)
        assert investigate._runs[result.run_id]["tenant_id"] == str(tenant)
        assert len(tasks.tasks) == 1  # Queued only; no model/tool call in this test.
        assert tasks.tasks[0].args == (result.run_id, str(case_id), body)
    finally:
        investigate._runs.pop(result.run_id)


@pytest.mark.parametrize("baseline", ["0", "1"])
@pytest.mark.asyncio
async def test_foreign_case_cannot_create_a_run_or_start_work(monkeypatch, baseline):
    monkeypatch.setenv("AISOC_SCOPED_BASELINE", baseline)
    tenant_a, tenant_b, case_id = uuid4(), uuid4(), uuid4()
    calls = owned_cases(monkeypatch, {(case_id, tenant_b)})
    tasks = BackgroundTasks()
    before = set(investigate._runs)
    with pytest.raises(HTTPException) as error:
        await investigate.launch_investigation(
            str(case_id), investigate.InvestigateRequest(alert_summary="Foreign case"), tasks, principal(tenant_a)
        )
    assert error.value.status_code == 404
    assert calls == [(case_id, tenant_a)]
    assert not tasks.tasks and set(investigate._runs) == before


@pytest.mark.asyncio
async def test_request_tenant_cannot_override_the_principal(monkeypatch):
    tenant_a, tenant_b = uuid4(), uuid4()
    pool = AsyncMock()
    monkeypatch.setattr(investigate.ledger, "get_pool", pool)
    tasks = BackgroundTasks()
    with pytest.raises(HTTPException) as error:
        await investigate.launch_investigation(
            str(uuid4()), investigate.InvestigateRequest(alert_summary="Other tenant", tenant_id=str(tenant_b)),
            tasks, principal(tenant_a),
        )
    assert error.value.status_code == 403
    pool.assert_not_awaited()
    assert not tasks.tasks


@pytest.mark.asyncio
async def test_pdf_report_checks_run_tenant_before_rendering(monkeypatch):
    tenant_a, tenant_b, run_id = uuid4(), uuid4(), str(uuid4())
    investigate._runs[run_id] = {"tenant_id": str(tenant_a), "status": "completed", "report_html": "<p>Marked</p>"}
    renderer = MagicMock()
    renderer.HTML.return_value.write_pdf.return_value = b"%PDF-marked"
    monkeypatch.setitem(__import__("sys").modules, "weasyprint", renderer)
    try:
        assert (await investigate.get_report_pdf(run_id, principal(tenant_a))).body == b"%PDF-marked"
        renderer.reset_mock()
        with pytest.raises(HTTPException) as error:
            await investigate.get_report_pdf(run_id, principal(tenant_b))
        assert error.value.status_code == 404
        renderer.HTML.assert_not_called()
    finally:
        investigate._runs.pop(run_id)


def test_baseline_restores_pdf_without_opening_direct_triage(monkeypatch):
    monkeypatch.setenv("AISOC_SCOPED_BASELINE", "1")
    app = FastAPI()

    @app.get("/api/v1/investigations/{run_id}/report.pdf")
    def pdf(run_id: str):
        return {"run_id": run_id}

    @app.post("/api/v1/triage")
    def graph():
        raise AssertionError("Broader execution must remain unavailable")

    apply_scope(app, "agents")
    with TestClient(app) as client:
        assert client.get("/api/v1/investigations/marked/report.pdf").status_code == 200
        assert client.post("/api/v1/triage").status_code == 404
