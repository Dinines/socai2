"""Real HTTP Bearer/scope/tenant chain, with a database double.

Production SQL construction and canonical API-projection fingerprints are
exercised here. Live PostgreSQL ordering/cutoff/RLS are separate acceptance;
this suite does not claim historical note versions or execute feedback writes.
"""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4
import hashlib
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.feedback import router
from app.core.security import hash_api_key
from app.db.database import get_db

TENANT_A = UUID('77777777-7777-7777-7777-777777777777')
TENANT_B = UUID('99999999-9999-9999-9999-999999999999')
URL = '/api/v1/feedback/recent-dispositions'
RULE = 'R-DISP-A'
SPLIT = datetime(2026, 5, 1, tzinfo=UTC)


def token(name):
    return 'aisoc_' + name + '-dispositions-unit-only'


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
        self.reason_code = 'expected_service_account'
        self.ai_disposition = 'true_positive'
        self.note = 'Synthetic personal opinion: verify current ownership.'
        for name, tenant, scopes, active, expires in [
            ('a', TENANT_A, ['alerts:read'], True, None),
            ('b', TENANT_B, ['alerts:read'], True, None),
            ('settings', TENANT_A, ['settings:read'], True, None),
            ('kb', TENANT_A, ['knowledge_base:read'], True, None),
            ('revoked', TENANT_A, ['alerts:read'], False, None),
            ('expired', TENANT_A, ['alerts:read'], True, datetime.now(UTC) - timedelta(minutes=1)),
        ]:
            self.keys[hash_api_key(token(name))] = SimpleNamespace(
                id=uuid4(), tenant_id=tenant, user_id=None, scopes=scopes,
                is_active=active, expires_at=expires, key_prefix='disp-unit-' + name)

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
        if 'FROM aisoc_analyst_feedback' in sql:
            assert str(params['tenant_id']) == self.rls_tenant
            assert 'tenant_id = :tenant_id' in sql
            assert 'ORDER BY by_rule DESC, created_at DESC, feedback_id' in sql
            assert 'id AS feedback_id' in sql and 'AS by_entity' in sql
            if self.fail:
                raise RuntimeError('injected feedback query failure')
            if 'as_of' in params:
                assert 'WHERE created_at <= :as_of' in sql
            by_rule, by_entity = params['rule_id'] == RULE, 'disp-host-a' in params['entities']
            return Result(rows=[SimpleNamespace(
                excluded_after_cutoff=2 if 'as_of' in params else 0, without_timestamp=0,
                feedback_id=UUID(self.rls_tenant),
                analyst_disposition=None if self.empty or not (by_rule or by_entity) else 'benign_true_positive',
                ai_disposition=self.ai_disposition, reason_code=self.reason_code,
                scope='entity', scope_value='DISP-HOST-A', rule_id=RULE, note=self.note,
                created_at=SPLIT - timedelta(days=1), by_rule=by_rule, by_entity=by_entity,
            )])
        raise AssertionError('Unexpected query: ' + sql)

    @property
    def feedback_queries(self):
        return [(sql, params) for sql, params in self.calls if 'FROM aisoc_analyst_feedback' in sql]


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('AISOC_DEV_AUTH_BYPASS', 'false')
    monkeypatch.setenv('AISOC_AGENTS_SERVICE_TOKEN', 'legacy-disp-unit-only')
    db = Session()
    app = FastAPI()
    app.include_router(router, prefix='/api/v1')

    async def database():
        yield db

    app.dependency_overrides[get_db] = database
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, db


def fingerprint(tenant, row):
    payload = {'tenant_id': str(tenant), **{key: value for key, value in row.items() if key != 'row_source_sha256'}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


@pytest.mark.parametrize('name,tenant', [('a', TENANT_A), ('b', TENANT_B)])
@pytest.mark.parametrize('explicit', [False, True])
def test_read_key_uses_own_tenant_and_returns_identity_time_match_and_projection_hash(boundary, name, tenant, explicit):
    client, db = boundary
    params = {'rule_id': RULE, **({'tenant_id': str(tenant)} if explicit else {})}
    response = client.get(URL, params=params, headers={'Authorization': 'Bearer ' + token(name)})
    assert response.status_code == 200
    body = response.json()
    assert body['tenant_id'] == str(tenant) and body['as_of'] is None
    row = body['dispositions'][0]
    assert row['feedback_id'] == str(tenant)
    assert row['created_at'] == row['decided_at'] == '2026-04-30T00:00:00+00:00'
    assert row['by_rule'] and not row['by_entity']
    assert row['row_source_sha256'] == fingerprint(tenant, row)
    assert db.rls_tenant == str(tenant) and len(db.feedback_queries) == 1


@pytest.mark.parametrize('name,wanted', [('a', TENANT_B), ('b', TENANT_A)])
def test_cross_tenant_refused_before_rls_and_query_even_with_shared_header(boundary, name, wanted):
    client, db = boundary
    response = client.get(URL, params={'rule_id': RULE, 'tenant_id': str(wanted)}, headers={
        'Authorization': 'Bearer ' + token(name), 'X-AiSOC-Service-Token': 'legacy-disp-unit-only'})
    assert response.status_code == 403
    assert db.rls_tenant is None and db.feedback_queries == []


@pytest.mark.parametrize('headers,status', [
    ({}, 401), ({'X-AiSOC-Service-Token': 'legacy-disp-unit-only'}, 401),
    ({'Authorization': 'Bearer ' + token('unknown')}, 401),
    ({'Authorization': 'Bearer ' + token('revoked')}, 401),
    ({'Authorization': 'Bearer ' + token('expired')}, 401),
    ({'Authorization': 'Bearer ' + token('settings')}, 403),
    ({'Authorization': 'Bearer ' + token('kb')}, 403),
])
def test_invalid_identity_or_missing_exact_scope_rejected_before_query(boundary, headers, status):
    client, db = boundary
    response = client.get(URL, params={'rule_id': RULE}, headers=headers)
    assert response.status_code == status
    assert db.rls_tenant is None and db.feedback_queries == []


def test_entity_binding_normalizes_and_reports_actual_match_flags(boundary):
    client, db = boundary
    response = client.get(URL, params=[('rule_id', 'unrelated'), ('entities', ' DISP-HOST-A '), ('entities', 'disp-host-a')],
                          headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 200
    row = response.json()['dispositions'][0]
    assert not row['by_rule'] and row['by_entity']
    assert db.feedback_queries[0][1]['entities'] == ['disp-host-a']


def test_cutoff_is_bound_and_echoed_with_excluded_count(boundary):
    client, db = boundary
    response = client.get(URL, params={'rule_id': RULE, 'as_of': SPLIT.isoformat()}, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 200
    assert response.json()['as_of'] == '2026-05-01T00:00:00Z'
    assert response.json()['excluded_after_cutoff'] == 2
    assert db.feedback_queries[0][1]['as_of'] == SPLIT


def test_empty_cutoff_is_success_and_preserves_counts(boundary):
    client, db = boundary
    db.empty = True
    response = client.get(URL, params={'rule_id': RULE, 'as_of': SPLIT.isoformat()}, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 200
    assert response.json()['dispositions'] == [] and response.json()['excluded_after_cutoff'] == 2


def test_database_failure_is_503_not_empty_success(boundary):
    client, db = boundary
    db.fail = True
    response = client.get(URL, params={'rule_id': RULE}, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 503 and response.json()['detail'] == 'Database error'


def test_unknown_legacy_vocabulary_is_returned_with_label_fallback_not_http_failure(boundary):
    client, db = boundary
    db.reason_code, db.ai_disposition = 'retired_reason', 'legacy_verdict'
    response = client.get(URL, params={'rule_id': RULE}, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 200
    row = response.json()['dispositions'][0]
    assert row['reason_code'] == row['reason_label'] == 'retired_reason' and row['ai_disposition'] == 'legacy_verdict'
    assert row['row_source_sha256'] == fingerprint(TENANT_A, row)


def test_current_note_projection_change_changes_hash_but_not_stable_identity(boundary):
    client, db = boundary
    headers = {'Authorization': 'Bearer ' + token('a')}
    first = client.get(URL, params={'rule_id': RULE}, headers=headers).json()['dispositions'][0]
    db.note = 'Changed current note: 审核当前证据.\nNo historical version is reconstructed.'
    second = client.get(URL, params={'rule_id': RULE}, headers=headers).json()['dispositions'][0]
    assert first['feedback_id'] == second['feedback_id'] and first['created_at'] == second['created_at']
    assert first['row_source_sha256'] != second['row_source_sha256'] == fingerprint(TENANT_A, second)


@pytest.mark.parametrize('path,body', [
    ('/api/v1/feedback/alert-override', {'alert_id': str(TENANT_A), 'original_verdict': 'true_positive', 'corrected_verdict': 'benign_true_positive', 'reason': 'synthetic test'}),
    ('/api/v1/feedback/redisposition/apply', {'alert_ids': [str(TENANT_A)], 'new_disposition': 'benign_true_positive', 'confirmation_token': 'synthetic-unit-only'}),
])
def test_read_key_cannot_override_or_redisposition(boundary, path, body):
    client, db = boundary
    response = client.post(path, json=body, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 403 and db.feedback_queries == []
