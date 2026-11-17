"""Direct requests for trusted assembly; no auth service or model is involved."""
import json
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from investigation_http.adapters.identity import configure_trusted_access, load_context
from investigation_http.contracts import StoreError
from investigation_http.dependencies import analysis_submission_service
from investigation_http.external_routes import analysis_submissions, pages


def test_trusted_query_and_execution_use_configured_context(tmp_path, monkeypatch):
    tenant = UUID('00000000-0000-4000-8000-000000000001')
    actor = UUID('00000000-0000-4000-8000-000000000002')
    path = tmp_path / 'context.json'
    path.write_text(json.dumps({'tenant_id': str(tenant), 'actor_id': str(actor), 'actor_name': '业务后端'}))
    monkeypatch.setenv('SOCAI2_HTTP_CONTEXT_FILE', str(path))
    app = FastAPI()
    app.include_router(pages.router, prefix='/api/v1')
    app.include_router(analysis_submissions.incident_router, prefix='/api/v1')
    configure_trusted_access(app)
    app.state.business_context = load_context()
    calls = []

    class Backend:
        async def read(self, tenant_id, *args, **kwargs):
            calls.append(('read', tenant_id, args, kwargs))
            return {'items': [], 'total': 0, 'next_offset': None,
                    'observed_at': '2026-11-14T00:00:00Z', 'limitations': []}

        async def submit(self, tenant_id, kind, identity, request, *, actor_id):
            calls.append(('submit', tenant_id, actor_id, kind))
            raise StoreError('subject_not_found', 404)

    app.dependency_overrides[pages.get_service] = Backend
    app.dependency_overrides[analysis_submission_service] = Backend
    client = TestClient(app)
    # Includes the legacy inline cases-section check, with no credential.
    assert client.get(f'/api/v1/socai2/alerts/{actor}/records/cases').status_code == 200
    assert client.post(f'/api/v1/socai2/alerts/{actor}/analyze', json={'operation_key': str(actor)}).status_code == 404
    response = client.post(f'/api/v1/socai2/incidents/{actor}/diagnose', json={'operation_key': str(actor), 'mode': 'check'})
    assert response.status_code == 404 and response.json()['detail']['code'] == 'subject_not_found'
    assert calls[0][1] == tenant
    assert calls[1] == ('submit', tenant, actor, 'incident')
    assert 'securitySchemes' not in app.openapi()['components']
    assert all('security' not in op for methods in app.openapi()['paths'].values() for op in methods.values())


def test_legacy_application_keeps_its_own_dependency_assembly():
    legacy = FastAPI()
    legacy.include_router(pages.router, prefix='/api/v1')
    assert not legacy.dependency_overrides
    assert 'HTTPBearer' in legacy.openapi()['components']['securitySchemes']
