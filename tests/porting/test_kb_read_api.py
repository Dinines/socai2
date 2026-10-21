"""Real Bearer/scopes/tenant HTTP chain with a database double.

These assertions exercise the production SQL builder and response shape;
actual PostgreSQL FTS/ranking/cutoff behavior is a separate live acceptance.
No auth dependency is overridden and no KB synthesis model is called.
"""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.knowledge_base import router
from app.core.security import hash_api_key
from app.db.database import get_db

TENANT_A = UUID('77777777-7777-7777-7777-777777777777')
TENANT_B = UUID('99999999-9999-9999-9999-999999999999')
URL = '/api/v1/kb/runbooks/for-triage'
QUERY = 'backup account evidence'
SPLIT = datetime(2026, 5, 1, tzinfo=UTC)


def token(name):
    return 'aisoc_' + name + '-kb-read-unit-only'


class Result:
    def __init__(self, scalar=None, rows=()):
        self.scalar = scalar
        self.rows = rows

    def scalar_one_or_none(self):
        return self.scalar

    def fetchall(self):
        return self.rows


class Session:
    def __init__(self):
        self.calls = []
        self.keys = {}
        self.rls_tenant = None
        self.fail = False
        self.empty = False
        self.undated = False
        for name, tenant, scopes, active, expires in [
            ('a', TENANT_A, ['knowledge_base:read'], True, None),
            ('b', TENANT_B, ['knowledge_base:read'], True, None),
            ('alerts', TENANT_A, ['alerts:read'], True, None),
            ('settings', TENANT_A, ['settings:read'], True, None),
            ('revoked', TENANT_A, ['knowledge_base:read'], False, None),
            ('expired', TENANT_A, ['knowledge_base:read'], True, datetime.now(UTC) - timedelta(minutes=1)),
        ]:
            self.keys[hash_api_key(token(name))] = SimpleNamespace(
                id=uuid4(), tenant_id=tenant, user_id=None, scopes=scopes,
                is_active=active, expires_at=expires, key_prefix='kb-unit-' + name)

    async def execute(self, statement, parameters=None):
        sql = str(statement)
        params = dict(parameters or statement.compile().params)
        self.calls.append((sql, params))
        if 'FROM api_keys' in sql:
            key = self.keys.get(params.get('hashed_key_1'))
            return Result(scalar=key if key and key.is_active else None)
        if sql.startswith('UPDATE api_keys'):
            return Result()
        if "set_config('app.current_tenant_id'" in sql:
            self.rls_tenant = params['tid']
            return Result()
        if 'FROM aisoc_kb_documents' in sql:
            assert str(params['tenant_id']) == self.rls_tenant
            assert params['kinds'] == ['runbook', 'playbook', 'sop']
            assert 'tenant_id = :tenant_id' in sql
            assert "plainto_tsquery('english', :q)" in sql and 'ORDER BY rank DESC, id' in sql
            if self.fail:
                raise RuntimeError('injected KB query failure')
            cutoff = 'as_of' in params
            if cutoff:
                assert 'WHERE created_at <= :as_of AND updated_at <= :as_of' in sql
                assert 'created_at <= :as_of AND updated_at > :as_of' in sql
            return Result(rows=[SimpleNamespace(
                excluded_after_cutoff=1 if cutoff else 0,
                excluded_after_update=1 if cutoff else 0,
                excluded_after_cutoff_total=2 if cutoff else 0,
                without_timestamp=1 if self.undated else 0,
                id=None if self.empty else UUID(self.rls_tenant), title='Backup evidence',
                doc_kind='runbook', source_url='https://example.invalid/synthetic',
                chunk_index=0, chunk_total=1, content='Backup account evidence for tenant ' + self.rls_tenant,
                created_at=None if self.undated else SPLIT - timedelta(days=2),
                updated_at=None if self.undated else SPLIT - timedelta(days=1), rank=.5,
            )])
        raise AssertionError('Unexpected query: ' + sql)

    @property
    def kb_queries(self):
        return [(sql, params) for sql, params in self.calls if 'FROM aisoc_kb_documents' in sql]


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('AISOC_DEV_AUTH_BYPASS', 'false')
    monkeypatch.setenv('AISOC_AGENTS_SERVICE_TOKEN', 'legacy-kb-unit-only')
    db = Session()
    app = FastAPI()
    app.include_router(router, prefix='/api/v1')

    async def database():
        yield db

    app.dependency_overrides[get_db] = database
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, db


@pytest.mark.parametrize('name,tenant', [('a', TENANT_A), ('b', TENANT_B)])
@pytest.mark.parametrize('explicit', [False, True])
def test_bearer_read_scope_uses_own_tenant_and_returns_updated_at(boundary, name, tenant, explicit):
    client, db = boundary
    params = {'q': QUERY, **({'tenant_id': str(tenant)} if explicit else {})}
    response = client.get(URL, params=params, headers={'Authorization': 'Bearer ' + token(name)})
    assert response.status_code == 200
    body = response.json()
    assert body['tenant_id'] == str(tenant) and body['as_of'] is None
    assert body['chunks'][0]['content'].endswith(str(tenant))
    assert body['chunks'][0]['updated_at'] == '2026-04-30T00:00:00Z'
    assert body['excluded_after_cutoff_total'] == body['excluded_after_cutoff'] == body['excluded_after_update'] == 0
    assert db.rls_tenant == str(tenant) and len(db.kb_queries) == 1
    assert db.kb_queries[0][1] == {'q': QUERY, 'tenant_id': tenant, 'kinds': ['runbook', 'playbook', 'sop'], 'limit': 3}


@pytest.mark.parametrize('name,wanted', [('a', TENANT_B), ('b', TENANT_A)])
def test_tenant_intersection_rejects_cross_read_even_with_shared_header(boundary, name, wanted):
    client, db = boundary
    response = client.get(URL, params={'q': QUERY, 'tenant_id': str(wanted)}, headers={
        'Authorization': 'Bearer ' + token(name), 'X-AiSOC-Service-Token': 'legacy-kb-unit-only'})
    assert response.status_code == 403
    assert db.rls_tenant is None and db.kb_queries == []


@pytest.mark.parametrize('headers,status', [
    ({}, 401), ({'X-AiSOC-Service-Token': 'legacy-kb-unit-only'}, 401),
    ({'Authorization': 'Bearer ' + token('unknown')}, 401),
    ({'Authorization': 'Bearer ' + token('revoked')}, 401),
    ({'Authorization': 'Bearer ' + token('expired')}, 401),
    ({'Authorization': 'Bearer ' + token('alerts')}, 403),
    ({'Authorization': 'Bearer ' + token('settings')}, 403),
])
def test_unauthorised_identity_or_missing_exact_scope_rejected_before_kb_query(boundary, headers, status):
    client, db = boundary
    response = client.get(URL, params={'q': QUERY}, headers=headers)
    assert response.status_code == status
    assert db.rls_tenant is None and db.kb_queries == []


def test_cutoff_echoes_bound_instant_and_preserves_disjoint_rejection_counts(boundary):
    client, db = boundary
    response = client.get(URL, params={'q': QUERY, 'as_of': SPLIT.isoformat()}, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 200
    body = response.json()
    assert body['as_of'] == '2026-05-01T00:00:00Z'
    assert body['excluded_after_cutoff'] == body['excluded_after_update'] == 1
    assert body['excluded_after_cutoff_total'] == 2
    assert db.kb_queries[0][1]['as_of'] == SPLIT


def test_empty_cutoff_retains_counts_and_is_success(boundary):
    client, db = boundary
    db.empty = True
    response = client.get(URL, params={'q': QUERY, 'as_of': SPLIT.isoformat()}, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 200
    assert response.json()['chunks'] == [] and response.json()['excluded_after_cutoff_total'] == 2


def test_missing_timestamp_projection_is_visible_without_claiming_real_schema_allows_null(boundary):
    client, db = boundary
    db.undated = True
    response = client.get(URL, params={'q': QUERY}, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 200
    body = response.json()
    assert body['without_timestamp'] == 1 and body['chunks'][0]['created_at'] is None and body['chunks'][0]['updated_at'] is None


def test_query_database_failure_is_503_not_empty_success(boundary):
    client, db = boundary
    db.fail = True
    response = client.get(URL, params={'q': QUERY}, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 503 and response.json()['detail'] == 'Database error'
    assert len(db.kb_queries) == 1


@pytest.mark.parametrize('method,path,body', [
    ('POST', '/api/v1/kb/ingest', {'title': 'Synthetic unit document', 'content': 'Backup account evidence only.'}),
    ('DELETE', '/api/v1/kb/documents/77777777-7777-7777-7777-777777777777', None),
])
def test_exact_read_key_cannot_write_or_delete_kb(boundary, method, path, body):
    client, db = boundary
    response = client.request(method, path, json=body, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 403 and db.kb_queries == []
