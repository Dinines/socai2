"""Real FastAPI auth dependency chain with a database double, not live PG.

Bearer parsing, API-key hashing/expiry/revocation, scope checks, tenant
intersection, RLS setup and the endpoint query run without auth overrides.
Live PostgreSQL expiry/filtering is a separate deployment acceptance gate.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.feedback import router
from app.core.security import hash_api_key
from app.db.database import get_db

TENANT_A = UUID("77777777-7777-7777-7777-777777777777")
TENANT_B = UUID("99999999-9999-9999-9999-999999999999")
URL = "/api/v1/feedback/context-statements"


def _token(name):
    return "aisoc_" + name + "-test-only"


class _Result:
    def __init__(self, *, scalar=None, rows=()):
        self._scalar = scalar
        self._rows = rows

    def scalar_one_or_none(self):
        return self._scalar

    def mappings(self):
        return self._rows


class _Session:
    def __init__(self):
        self.keys = {}
        self.calls = []
        self.rls_tenant = None
        self.fail_context = False
        for name, tenant, scopes, active, expires in [
            ("a", TENANT_A, ["alerts:read"], True, None),
            ("b", TENANT_B, ["alerts:read"], True, None),
            ("denied", TENANT_A, ["cases:read"], True, None),
            ("revoked", TENANT_A, ["alerts:read"], False, None),
            ("expired", TENANT_A, ["alerts:read"], True, datetime.now(UTC) - timedelta(minutes=1)),
        ]:
            self.keys[hash_api_key(_token(name))] = SimpleNamespace(
                id=uuid4(),
                tenant_id=tenant,
                user_id=None,
                scopes=scopes,
                is_active=active,
                expires_at=expires,
                key_prefix="test-" + name,
            )

    async def execute(self, statement, parameters=None):
        sql = str(statement)
        bound = dict(parameters or statement.compile().params)
        self.calls.append((sql, bound))
        if "FROM api_keys" in sql:
            key = self.keys.get(bound.get("hashed_key_1"))
            return _Result(scalar=key if key and key.is_active else None)
        if sql.startswith("UPDATE api_keys"):
            return _Result()
        if "set_config('app.current_tenant_id'" in sql:
            self.rls_tenant = bound["tid"]
            return _Result()
        if "FROM aisoc_context_statements" in sql:
            assert bound["tenant_id"] == self.rls_tenant
            if self.fail_context:
                raise RuntimeError("injected context query failure")
            return _Result(rows=[{
                "statement": "Expected maintenance for tenant " + self.rls_tenant,
                "reason_code": "expected_service_account",
                "scope": "entity",
                "scope_value": "test-service",
                "observations": 2,
                "expires_at": None,
            }])
        raise AssertionError("Unexpected query: " + sql)

    @property
    def context_reads(self):
        return [params for sql, params in self.calls if "FROM aisoc_context_statements" in sql]


@pytest.fixture
def http_boundary(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AISOC_DEV_AUTH_BYPASS", "false")
    # Even an API-configured X token alone must not open this GET.
    monkeypatch.setenv("AISOC_AGENTS_SERVICE_TOKEN", "legacy-test-only")
    session = _Session()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def _db():
        yield session

    app.dependency_overrides[get_db] = _db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, session


@pytest.mark.parametrize("name,tenant", [("a", TENANT_A), ("b", TENANT_B)])
def test_real_bearer_dependency_resolves_key_tenant_and_scopes_query(http_boundary, name, tenant):
    client, session = http_boundary
    response = client.get(URL, headers={"Authorization": "Bearer " + _token(name)})

    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(tenant)
    assert str(tenant) in response.json()["statements"][0]["statement"]
    assert session.rls_tenant == str(tenant)
    assert session.context_reads == [{"tenant_id": str(tenant)}]


@pytest.mark.parametrize("name,wanted", [("a", TENANT_B), ("b", TENANT_A)])
def test_key_cannot_read_other_tenant_even_with_legacy_header(http_boundary, name, wanted):
    client, session = http_boundary
    response = client.get(
        URL,
        params={"tenant_id": str(wanted)},
        headers={"Authorization": "Bearer " + _token(name), "X-AiSOC-Service-Token": "legacy-test-only"},
    )

    assert response.status_code == 403
    assert session.rls_tenant is None
    assert session.context_reads == []


@pytest.mark.parametrize("headers,expected", [
    ({}, 401),
    ({"X-AiSOC-Service-Token": "legacy-test-only"}, 401),
    ({"Authorization": "Bearer " + _token("unknown")}, 401),
    ({"Authorization": "Bearer " + _token("revoked")}, 401),
    ({"Authorization": "Bearer " + _token("expired")}, 401),
    ({"Authorization": "Bearer " + _token("denied")}, 403),
])
def test_missing_bad_revoked_expired_or_wrong_scope_identity_is_refused(http_boundary, headers, expected):
    client, session = http_boundary
    response = client.get(URL, params={"tenant_id": str(TENANT_A)}, headers=headers)

    assert response.status_code == expected
    assert session.rls_tenant is None
    assert session.context_reads == []


def test_context_query_failure_is_an_http_failure_not_empty_success(http_boundary):
    client, session = http_boundary
    session.fail_context = True
    response = client.get(URL, headers={"Authorization": "Bearer " + _token("a")})

    assert response.status_code == 500
    assert session.context_reads == [{"tenant_id": str(TENANT_A)}]
