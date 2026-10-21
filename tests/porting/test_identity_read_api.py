"""Real Bearer/scope/tenant chain with an isolated graph-query double.

Cypher shape and helper response validation are checked here; these doubles
do not establish actual Neo4j path isolation or historical HR reconstruction.
"""
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4
import asyncio
import hashlib
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.graph import router
from app.core.security import hash_api_key
from app.db.database import get_db
from app.services import incident_context as context

TENANT_A = UUID('77777777-7777-7777-7777-777777777777')
TENANT_B = UUID('99999999-9999-9999-9999-999999999999')
URL = '/api/v1/graph/identity-context'
SPLIT = datetime(2026, 5, 1, tzinfo=UTC)


def token(name):
    return 'aisoc_' + name + '-identity-read-unit-only'


def row(tenant, *, suffix='one', stamp=SPLIT - timedelta(days=1), status='native', linked=True):
    return {
        'identity_id': str(tenant) + ':identity-' + suffix, 'identity_id_kind': 'business_id',
        'employee_id': str(tenant) + ':employee-' + suffix if linked else None,
        'employee_id_kind': 'business_id' if linked else None,
        'department_id': str(tenant) + ':department' if linked else None,
        'department_id_kind': 'business_id' if linked else None,
        'manager_id': None, 'manager_id_kind': None,
        'account': 'SvC-Review', 'provider': 'directory-' + suffix,
        'employee': 'Synthetic ' + str(tenant) if linked else None,
        'title': 'Current analyst' if linked else None, 'is_active': False if linked else None,
        'employment_type': 'service' if linked else None,
        'start_date': date(2025, 1, 2) if linked else None,
        'end_date': '2026-03-01' if linked else None,
        'imported_at': stamp if status == 'native' else None,
        'imported_at_status': status, 'imported_at_raw': stamp,
        'department': 'Synthetic team' if linked else None,
        'manager': None, 'manager_email': None, 'employee_linked': linked,
        'relationship_source': {'employee_identity': 'AUTHENTICATES_AS' if linked else None,
                                'employee_department': 'BELONGS_TO' if linked else None,
                                'manager_employee': None},
    }


class Result:
    def __init__(self, scalar=None, rows=()):
        self.scalar, self.rows = scalar, rows

    def scalar_one_or_none(self):
        return self.scalar

    async def data(self):
        return deepcopy(self.rows)


class AuthSession:
    def __init__(self):
        self.keys, self.calls = {}, []
        for name, tenant, scopes, active, expires in [
            ('a', TENANT_A, ['graph:read'], True, None),
            ('b', TENANT_B, ['graph:read'], True, None),
            ('alerts', TENANT_A, ['alerts:read'], True, None),
            ('settings', TENANT_A, ['settings:read'], True, None),
            ('revoked', TENANT_A, ['graph:read'], False, None),
            ('expired', TENANT_A, ['graph:read'], True, datetime.now(UTC) - timedelta(minutes=1)),
        ]:
            self.keys[hash_api_key(token(name))] = SimpleNamespace(
                id=uuid4(), tenant_id=tenant, user_id=None, scopes=scopes,
                is_active=active, expires_at=expires, key_prefix='identity-unit-' + name)

    async def execute(self, statement, parameters=None):
        sql = str(statement)
        params = dict(parameters or statement.compile().params)
        self.calls.append((sql, params))
        if 'FROM api_keys' in sql:
            key = self.keys.get(params.get('hashed_key_1'))
            return Result(scalar=key if key and key.is_active else None)
        if sql.startswith('UPDATE api_keys') or "set_config('app.current_tenant_id'" in sql:
            return Result()
        raise AssertionError('Unexpected authentication database query')


class GraphSession:
    def __init__(self):
        self.calls, self.failure, self.mutate = [], None, None
        self.rows = {str(tenant): [row(tenant)] for tenant in (TENANT_A, TENANT_B)}

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))
        if self.failure:
            raise self.failure
        assert cypher == context._IDENTITY_BY_ACCOUNT_CYPHER
        assert 'global_labels' not in params
        candidates = [item for item in self.rows[params['tenant_id']]
                      if item['account'].lower() in params['accounts']]
        cutoff = params['as_of']
        late = [item for item in candidates if cutoff and item['imported_at_status'] == 'native' and item['imported_at'] > cutoff]
        unknown = [item for item in candidates if cutoff and item['imported_at_status'] != 'native']
        eligible = [item for item in candidates if item not in late + unknown]
        eligible.sort(key=lambda item: (item['account'].lower(), item['provider'] or '', item['identity_id'],
                                        item['employee_id'] or '', item['department_id'] or '', item['manager_id'] or ''))
        selected = eligible[:params['limit']]
        envelope = {'identities': selected, 'candidate_count': len(candidates), 'eligible_count': len(eligible),
                    'truncated_count': len(eligible) - len(selected), 'excluded_after_cutoff': len(late),
                    'excluded_unverifiable_import': len(unknown),
                    'import_timestamp_missing': sum(item['imported_at_status'] == 'missing' for item in candidates)}
        if self.mutate:
            self.mutate(envelope)
        return Result(rows=[envelope])


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('AISOC_DEV_AUTH_BYPASS', 'false')
    monkeypatch.setenv('AISOC_AGENTS_SERVICE_TOKEN', 'legacy-identity-unit-only')
    auth, graph = AuthSession(), GraphSession()
    app = FastAPI()
    app.include_router(router, prefix='/api/v1')

    async def database():
        yield auth

    @asynccontextmanager
    async def graph_session():
        yield graph

    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(context.neo4j_db, 'get_identity_read_session', graph_session)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, graph


def fingerprint(tenant, value):
    projection = {'tenant_id': str(tenant), **{key: value[key] for key in context.IDENTITY_SOURCE_FIELDS}}
    return hashlib.sha256(json.dumps(projection, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


@pytest.mark.parametrize('name,tenant', [('a', TENANT_A), ('b', TENANT_B)])
@pytest.mark.parametrize('explicit', [False, True])
def test_graph_read_only_key_uses_own_tenant_and_canonical_json_projection(boundary, name, tenant, explicit):
    client, graph = boundary
    params = {'accounts': 'SVC-REVIEW', **({'tenant_id': str(tenant)} if explicit else {})}
    response = client.get(URL, params=params, headers={'Authorization': 'Bearer ' + token(name)})
    assert response.status_code == 200
    body = response.json()
    assert body['tenant_id'] == str(tenant) and body['accounts'] == ['svc-review'] and body['limit'] == 5
    assert body['source_status'] == 'success' and body['source_reason'] is None and body['as_of'] is None
    value = body['identities'][0]
    assert value['identity_id'].startswith(str(tenant)) and value['is_active'] is False
    assert value['imported_at'] == '2026-04-30T00:00:00+00:00' and value['start_date'] == '2025-01-02'
    assert value['row_source_sha256'] == fingerprint(tenant, value)
    assert set(value) == set(context.IDENTITY_SOURCE_FIELDS) | {'row_source_sha256'}
    assert body['candidate_count'] == body['eligible_count'] == body['without_timestamp'] == 1
    assert graph.calls[0][1]['tenant_id'] == str(tenant)


@pytest.mark.parametrize('name,wanted', [('a', TENANT_B), ('b', TENANT_A)])
def test_cross_tenant_refused_before_graph_even_with_shared_header(boundary, name, wanted):
    client, graph = boundary
    response = client.get(URL, params={'accounts': 'svc-review', 'tenant_id': str(wanted)}, headers={
        'Authorization': 'Bearer ' + token(name), 'X-AiSOC-Service-Token': 'legacy-identity-unit-only'})
    assert response.status_code == 403 and not graph.calls


@pytest.mark.parametrize('headers,status', [
    ({}, 401), ({'X-AiSOC-Service-Token': 'legacy-identity-unit-only'}, 401),
    ({'Authorization': 'Bearer ' + token('unknown')}, 401),
    ({'Authorization': 'Bearer ' + token('revoked')}, 401),
    ({'Authorization': 'Bearer ' + token('expired')}, 401),
    ({'Authorization': 'Bearer ' + token('alerts')}, 403),
    ({'Authorization': 'Bearer ' + token('settings')}, 403),
])
def test_missing_identity_or_exact_scope_is_rejected_before_graph(boundary, headers, status):
    client, graph = boundary
    response = client.get(URL, params={'accounts': 'svc-review'}, headers=headers)
    assert response.status_code == status and not graph.calls


def test_account_normalization_and_empty_match_never_queries_graph(boundary):
    client, graph = boundary
    headers = {'Authorization': 'Bearer ' + token('a')}
    response = client.get(URL, params=[('accounts', ' SvC-ReView '), ('accounts', 'svc-review')], headers=headers)
    assert response.status_code == 200 and graph.calls[-1][1]['accounts'] == ['svc-review']
    graph.calls.clear()
    body = client.get(URL, params={'accounts': '  '}, headers=headers).json()
    assert body['source_status'] == 'no_match' and body['accounts'] == [] and body['identities'] == []
    assert body['candidate_count'] == 0 and not graph.calls


def test_cutoff_filters_late_and_unverifiable_before_limit_and_preserves_full_counts(boundary):
    client, graph = boundary
    graph.rows[str(TENANT_A)] = [
        row(TENANT_A, suffix='00-late', stamp=SPLIT + timedelta(days=1)),
        row(TENANT_A, suffix='01-missing', stamp=None, status='missing'),
        row(TENANT_A, suffix='02-text', stamp='not a valid date', status='unsupported'),
        row(TENANT_A, suffix='04-old'), row(TENANT_A, suffix='03-old'),
    ]
    response = client.get(URL, params={'accounts': 'svc-review', 'as_of': SPLIT.isoformat(), 'limit': 1},
                          headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 200
    body = response.json()
    assert body['as_of'] == '2026-05-01T00:00:00Z'
    assert body['candidate_count'] == 5 and body['eligible_count'] == 2 and body['truncated_count'] == 1
    assert body['excluded_after_cutoff'] == 1 and body['excluded_unverifiable_import'] == 2
    assert body['import_timestamp_missing'] == body['without_timestamp'] == 1
    assert body['identities'][0]['identity_id'].endswith('03-old')


@pytest.mark.parametrize('status,raw_stamp', [('missing', None), ('unsupported', '2026-04-01T00:00:00Z'), ('unsupported', 'bad-date')])
def test_live_unknown_stamp_is_explicit_and_raw_value_only_fingerprinted(boundary, status, raw_stamp):
    client, graph = boundary
    graph.rows[str(TENANT_A)] = [row(TENANT_A, stamp=raw_stamp, status=status)]
    body = client.get(URL, params={'accounts': 'svc-review'}, headers={'Authorization': 'Bearer ' + token('a')}).json()
    value = body['identities'][0]
    assert value['imported_at'] is None and value['imported_at_status'] == status
    assert 'imported_at_raw' not in value and len(value['imported_at_raw_sha256']) == 64
    assert body['excluded_after_cutoff'] == body['excluded_unverifiable_import'] == 0
    assert body['without_timestamp'] == 1


def test_unlinked_identity_and_unknown_active_are_retained_without_invented_employee(boundary):
    client, graph = boundary
    graph.rows[str(TENANT_A)] = [row(TENANT_A, stamp=None, status='missing', linked=False)]
    body = client.get(URL, params={'accounts': 'svc-review'}, headers={'Authorization': 'Bearer ' + token('a')}).json()
    value = body['identities'][0]
    assert not value['employee_linked'] and value['employee_id'] is None and value['employee'] is None
    assert value['is_active'] is None and set(value['relationship_source'].values()) == {None}


@pytest.mark.parametrize('bad_active', ['false', 0, 1])
def test_non_boolean_active_is_unknown_not_python_truthiness(boundary, bad_active):
    client, graph = boundary
    graph.rows[str(TENANT_A)][0]['is_active'] = bad_active
    response = client.get(URL, params={'accounts': 'svc-review'}, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 200 and response.json()['identities'][0]['is_active'] is None


@pytest.mark.parametrize('exception,reason', [
    (ConnectionError('private host is deliberately not returned'), 'graph_unavailable'),
    (TimeoutError(), 'graph_timeout'), (RuntimeError('private query is deliberately not returned'), 'graph_query_failed'),
    (ValueError('bad source'), 'invalid_source_response'),
])
def test_graph_failure_is_same_shape_503_not_empty_success(boundary, exception, reason):
    client, graph = boundary
    graph.failure = exception
    response = client.get(URL, params={'accounts': 'svc-review', 'as_of': SPLIT.isoformat()},
                          headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 503
    body = response.json()
    assert body['source_status'] == 'unavailable' and body['source_reason'] == reason
    assert body['tenant_id'] == str(TENANT_A) and body['as_of'] == '2026-05-01T00:00:00Z'
    assert body['identities'] == [] and body['candidate_count'] == 0
    assert 'private' not in response.text


@pytest.mark.parametrize('mutator', [
    lambda data: data.update(candidate_count=True), lambda data: data.update(candidate_count=99),
    lambda data: data.update(eligible_count=-1), lambda data: data.update(import_timestamp_missing=99),
    lambda data: data['identities'][0].update(account='other-account'),
    lambda data: data['identities'][0].update(imported_at_status='invented'),
    lambda data: data['identities'][0].update(title=17),
    lambda data: data['identities'][0].update(employee_id_kind=None),
    lambda data: data['identities'][0].update(employee_linked=False),
    lambda data: data['identities'][0].update(relationship_source={}),
])
def test_malformed_graph_envelope_is_explicit_failure(boundary, mutator):
    client, graph = boundary
    graph.mutate = mutator
    response = client.get(URL, params={'accounts': 'svc-review'}, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 503 and response.json()['source_reason'] == 'invalid_source_response'


@pytest.mark.parametrize('params', [
    {'accounts': 'svc-review', 'as_of': '2026-05-01T00:00:00'},
    {'accounts': 'svc-review', 'limit': 0}, {'accounts': 'svc-review', 'limit': 26},
    [('accounts', 'account-' + str(index)) for index in range(26)],
])
def test_invalid_cutoff_or_limits_refused_before_graph(boundary, params):
    client, graph = boundary
    response = client.get(URL, params=params, headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 422 and not graph.calls


def test_current_projection_changes_hash_without_inventing_historical_version(boundary):
    client, graph = boundary
    headers = {'Authorization': 'Bearer ' + token('a')}
    first = client.get(URL, params={'accounts': 'svc-review'}, headers=headers).json()['identities'][0]
    graph.rows[str(TENANT_A)][0]['title'] = 'Changed current title 审核'
    second = client.get(URL, params={'accounts': 'svc-review'}, headers=headers).json()['identities'][0]
    assert first['identity_id'] == second['identity_id'] and first['imported_at'] == second['imported_at']
    assert first['row_source_sha256'] != second['row_source_sha256'] == fingerprint(TENANT_A, second)


def test_graph_reader_cannot_import_directory(boundary):
    client, graph = boundary
    response = client.post('/api/v1/graph/context/import', json={'employees': []},
                           headers={'Authorization': 'Bearer ' + token('a')})
    assert response.status_code == 403 and not graph.calls


async def test_helper_timeout_is_bounded_and_typed(monkeypatch):
    class Slow:
        async def run(self, *args, **kwargs):
            await asyncio.sleep(1)

    monkeypatch.setattr(context, 'QUERY_TIMEOUT_SECONDS', .01)
    result = await context.read_identity_context_for_accounts(str(TENANT_A), ['svc-review'], session=Slow())
    assert result.status == 'unavailable' and result.reason == 'graph_timeout' and not result.identities


def test_driver_temporal_projection_normalizes_to_utc_before_hashing():
    class DriverStamp:
        def to_native(self):
            return datetime(2026, 4, 30, 9, 30, tzinfo=timezone(timedelta(hours=9, minutes=30)))

    source = row(TENANT_A, stamp=DriverStamp())
    value = context._identity_projection(source, str(TENANT_A))
    assert value['imported_at'] == '2026-04-30T00:00:00+00:00'
    assert value['row_source_sha256'] == fingerprint(TENANT_A, value)


@pytest.mark.parametrize('class_name,reason', [('IdentityGraphNotConfigured', 'graph_not_configured'), ('AuthError', 'graph_auth_failed')])
async def test_dedicated_session_configuration_and_auth_failures_are_typed(monkeypatch, class_name, reason):
    error = type(class_name, (RuntimeError,), {})

    @asynccontextmanager
    async def unavailable():
        raise error('private credential detail is never surfaced')
        yield

    monkeypatch.setattr(context.neo4j_db, 'get_identity_read_session', unavailable)
    found = await context.read_identity_context_for_accounts(str(TENANT_A), ['svc-review'])
    assert found.status == 'unavailable' and found.reason == reason and not found.identities
