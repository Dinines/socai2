"""Direct security boundary: cached runs cannot be read by another tenant."""
import uuid
import pytest
from fastapi import HTTPException
from app.api import investigate
from app.security.tenant_scope import TenantPrincipal

@pytest.mark.asyncio
async def test_run_and_reports_are_owned_by_authenticated_tenant():
    tenant_a,tenant_b=uuid.uuid4(),uuid.uuid4()
    run_id=str(uuid.uuid4())
    investigate._runs[run_id]={'tenant_id':str(tenant_a),'status':'completed','report_md':'marked report','report_html':'<p>marked report</p>'}
    a=TenantPrincipal(tenant_ids=frozenset({tenant_a}),subject='test-a')
    b=TenantPrincipal(tenant_ids=frozenset({tenant_b}),subject='test-b')
    try:
        assert (await investigate.get_investigation(run_id,a))['status']=='completed'
        assert await investigate.get_report_md(run_id,a)=='marked report'
        for read in (investigate.get_investigation,investigate.get_report_md,investigate.get_report_html):
            with pytest.raises(HTTPException) as error:
                await read(run_id,b)
            assert error.value.status_code==404
    finally:investigate._runs.pop(run_id)


def test_scoped_surface_excludes_all_other_execution_routes(monkeypatch):
    from fastapi import FastAPI
    from app.core.scoped_baseline import apply_scope
    app=FastAPI()
    @app.post('/api/v1/triage')
    def unsafe():pass
    @app.get('/readyz')
    def ready():pass
    @app.post('/api/v1/cases/{case_id}/investigate')
    def manual():pass
    monkeypatch.setenv('AISOC_SCOPED_BASELINE','1')
    apply_scope(app,'agents')
    from fastapi.testclient import TestClient
    client=TestClient(app)
    assert client.post('/api/v1/triage').status_code==404
    assert client.post('/api/v1/cases/test/investigate').status_code==200
    assert client.get('/readyz').status_code==200
