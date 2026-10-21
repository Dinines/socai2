"""Default investigation result and PDF reads require the same Case/Run binding."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import cases


def owned_case_db():
    result = MagicMock()
    result.fetchone.return_value = object()
    return MagicMock(execute=AsyncMock(return_value=result))


@pytest.mark.asyncio
@pytest.mark.parametrize("reader", ["case_investigation_run", "case_investigation_report_md", "case_investigation_pdf"])
@pytest.mark.parametrize("run_case", [None, "foreign-case"])
async def test_report_read_refuses_a_missing_or_different_case_binding(monkeypatch, reader, run_case):
    tenant, case_id = uuid4(), uuid4()
    monkeypatch.setattr(cases, "_resolve_case_id", AsyncMock(return_value=case_id))
    proxy = AsyncMock(return_value=httpx.Response(200, json={"case_id": run_case, "status": "completed"}))
    monkeypatch.setattr(cases, "_agents_proxy", proxy)
    with pytest.raises(HTTPException) as error:
        await getattr(cases, reader)(case_id="CASE-1", run_id="marked-run", db=owned_case_db(), user=SimpleNamespace(tenant_id=tenant))
    assert error.value.status_code == 404
    assert proxy.await_count == 1  # No report bytes requested after a failed binding.


@pytest.mark.asyncio
async def test_pdf_resolves_case_ownership_before_any_agents_request(monkeypatch):
    resolve = AsyncMock(side_effect=HTTPException(status_code=404, detail="Case not found"))
    monkeypatch.setattr(cases, "_resolve_case_id", resolve)
    proxy = AsyncMock()
    monkeypatch.setattr(cases, "_agents_proxy", proxy)
    with pytest.raises(HTTPException) as error:
        await cases.case_investigation_pdf("foreign-case", "marked-run", object(), SimpleNamespace(tenant_id=uuid4()))
    assert error.value.status_code == 404
    proxy.assert_not_awaited()


@pytest.mark.asyncio
async def test_uuid_case_is_checked_in_the_authenticated_tenant(monkeypatch):
    tenant, foreign_case = uuid4(), uuid4()
    db = owned_case_db()
    db.execute.return_value.fetchone.return_value = None
    proxy = AsyncMock()
    monkeypatch.setattr(cases, "_agents_proxy", proxy)
    with pytest.raises(HTTPException) as error:
        await cases.case_investigation_pdf(str(foreign_case), "marked-run", db, SimpleNamespace(tenant_id=tenant))
    assert error.value.status_code == 404
    statement = db.execute.await_args.args[0]
    assert "id = :id AND tenant_id = :tenant_id" in str(statement)
    assert statement.compile().params == {"id": foreign_case, "tenant_id": tenant}
    proxy.assert_not_awaited()


@pytest.mark.asyncio
async def test_pdf_for_an_owned_case_and_run_keeps_tenant_header_and_bytes(monkeypatch):
    tenant, case_id = uuid4(), uuid4()
    resolve = AsyncMock(return_value=case_id)
    monkeypatch.setattr(cases, "_resolve_case_id", resolve)
    proxy = AsyncMock(side_effect=[
        httpx.Response(200, json={"case_id": str(case_id), "status": "completed"}),
        httpx.Response(200, content=b"%PDF-marked", headers={"content-type": "application/pdf"}),
    ])
    monkeypatch.setattr(cases, "_agents_proxy", proxy)
    db = owned_case_db()
    result = await cases.case_investigation_pdf("CASE-1", "marked-run", db, SimpleNamespace(tenant_id=tenant))
    resolve.assert_awaited_once_with("CASE-1", db, tenant)
    assert [c.args[1] for c in proxy.await_args_list] == [
        "/api/v1/investigations/marked-run", "/api/v1/investigations/marked-run/report.pdf"
    ]
    assert all(c.kwargs["headers"] == {"X-AiSOC-Tenant-ID": str(tenant)} for c in proxy.await_args_list)
    assert result.body == b"%PDF-marked" and result.media_type == "application/pdf"
