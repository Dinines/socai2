"""Resolved skill HTTP/auth boundary with the real dependency chain.

API-key hashing, expiry/revocation, scopes, tenant intersection and the real
skill resolver run against a database double. This does not establish live
PostgreSQL RLS or the author/backtest/activation workflow; those have separate
tests and deployment evidence.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.tenant_skills import router
from app.core.security import hash_api_key
from app.db.database import get_db

TENANT_A = UUID("77777777-7777-7777-7777-777777777777")
TENANT_B = UUID("99999999-9999-9999-9999-999999999999")
URL = "/api/v1/tenant-skills/resolved/active"


def _token(name):
    return "aisoc_" + name + "-tenant-skill-test-only"


class _Result:
    def __init__(self, *, scalar=None, rows=()):
        self._scalar = scalar
        self._rows = rows

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _Session:
    def __init__(self):
        self.keys = {}
        self.calls = []
        self.rls_tenant = None
        self.fail_skills = False
        self.empty = False
        now = datetime.now(UTC)
        for name, tenant, scopes, active, expires in [
            ("a", TENANT_A, ["settings:read"], True, None),
            ("b", TENANT_B, ["settings:read"], True, None),
            ("alerts-only", TENANT_A, ["alerts:read"], True, None),
            ("cases-only", TENANT_A, ["cases:read"], True, None),
            ("revoked", TENANT_A, ["settings:read"], False, None),
            ("expired", TENANT_A, ["settings:read"], True, now - timedelta(minutes=1)),
        ]:
            self.keys[hash_api_key(_token(name))] = SimpleNamespace(
                id=uuid4(), tenant_id=tenant, user_id=None, scopes=scopes,
                is_active=active, expires_at=expires, key_prefix="test-" + name,
            )
        self.rows = []
        for tenant in (TENANT_A, TENANT_B):
            for skill_id, status, expires in [
                ("current", "active", now + timedelta(days=1)),
                ("expired", "active", now - timedelta(minutes=1)),
                ("draft", "draft", now + timedelta(days=1)),
                ("retired", "retired", now + timedelta(days=1)),
            ]:
                self.rows.append(SimpleNamespace(
                    tenant_id=tenant, skill_id=skill_id, status=status, version=2,
                    expires_at=expires, activated_at=now - timedelta(hours=1),
                    body={"id": skill_id, "guidance": "tenant " + str(tenant),
                          "plan": ["Review the alert"], "expected_pivots": ["process_activity"]},
                ))

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
        if "FROM aisoc_tenant_skills" in sql:
            # Fail if either the query or explicit RLS context loses the
            # authenticated scope. The real resolver still filters expiry.
            assert bound["tenant_id_1"] == UUID(self.rls_tenant)
            assert bound["status_1"] == "active"
            assert "aisoc_tenant_skills.tenant_id =" in sql
            assert "aisoc_tenant_skills.status =" in sql
            if self.fail_skills:
                raise RuntimeError("injected skill query failure")
            return _Result(rows=[] if self.empty else [
                row for row in self.rows
                if row.tenant_id == bound["tenant_id_1"] and row.status == bound["status_1"]
            ])
        raise AssertionError("Unexpected query: " + sql)

    @property
    def skill_reads(self):
        return [params for sql, params in self.calls if "FROM aisoc_tenant_skills" in sql]


@pytest.fixture
def http_boundary(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AISOC_DEV_AUTH_BYPASS", "false")
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
@pytest.mark.parametrize("explicit_tenant", [False, True])
def test_settings_reader_resolves_own_current_active_unexpired_version(http_boundary, name, tenant, explicit_tenant):
    client, session = http_boundary
    response = client.get(
        URL, params={"tenant_id": str(tenant)} if explicit_tenant else {},
        headers={"Authorization": "Bearer " + _token(name)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == str(tenant)
    assert [row["skill_id"] for row in body["skills"]] == ["current"]
    assert body["skills"][0]["version"] == 2
    assert body["skills"][0]["body"]["guidance"] == "tenant " + str(tenant)
    assert session.rls_tenant == str(tenant)
    assert session.skill_reads == [{"tenant_id_1": tenant, "status_1": "active"}]


@pytest.mark.parametrize("name,wanted", [("a", TENANT_B), ("b", TENANT_A)])
def test_shared_header_cannot_widen_the_bearer_tenant(http_boundary, name, wanted):
    client, session = http_boundary
    response = client.get(
        URL, params={"tenant_id": str(wanted)},
        headers={"Authorization": "Bearer " + _token(name), "X-AiSOC-Service-Token": "legacy-test-only"},
    )

    assert response.status_code == 403
    assert session.rls_tenant is None
    assert session.skill_reads == []


@pytest.mark.parametrize("headers,expected", [
    ({}, 401),
    ({"X-AiSOC-Service-Token": "legacy-test-only"}, 401),
    ({"Authorization": "Bearer " + _token("unknown")}, 401),
    ({"Authorization": "Bearer " + _token("revoked")}, 401),
    ({"Authorization": "Bearer " + _token("expired")}, 401),
    ({"Authorization": "Bearer " + _token("alerts-only")}, 403),
    ({"Authorization": "Bearer " + _token("cases-only")}, 403),
])
def test_missing_bad_revoked_expired_or_wrong_scope_refused_before_query(http_boundary, headers, expected):
    client, session = http_boundary
    response = client.get(URL, params={"tenant_id": str(TENANT_A)}, headers=headers)

    assert response.status_code == expected
    assert session.rls_tenant is None
    assert session.skill_reads == []


def test_valid_empty_read_is_distinct_from_http_failure(http_boundary):
    client, session = http_boundary
    session.empty = True
    response = client.get(URL, headers={"Authorization": "Bearer " + _token("a")})

    assert response.status_code == 200
    assert response.json() == {"tenant_id": str(TENANT_A), "skills": []}
    assert len(session.skill_reads) == 1


def test_skill_query_failure_is_http_failure_not_empty_success(http_boundary):
    client, session = http_boundary
    session.fail_skills = True
    response = client.get(URL, headers={"Authorization": "Bearer " + _token("a")})

    assert response.status_code == 500
    assert len(session.skill_reads) == 1
