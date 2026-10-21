"""The two remaining triage-context routes: who may read, and what the cutoff does.

Gap-closure Phase 6.3 gate, API half.

``/feedback/recent-dispositions`` runs PostgreSQL that SQLite cannot parse
(``FILTER (WHERE ...)``, ``LEFT JOIN LATERAL``, ``ANY(CAST(... AS text[]))``,
``context ->> 'rule_id'``), so its filtering is proven against a real database
in ``tests/isolation/test_recent_dispositions_cutoff_live.py``, running the
same ``recent_dispositions_sql`` the route calls. Here: the credential, the
presence or absence of the cutoff predicate, and the counts surviving an empty
result set.

``/graph/identity-context`` now delegates cutoff-before-limit to its typed
graph helper. These route doubles prove credential, scope and response
propagation; production Cypher filtering is separate real-Neo4j evidence.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from app.api.v1.deps import CurrentUser, get_current_user, get_db
from app.api.v1.endpoints import feedback as feedback_endpoint
from app.api.v1.endpoints import graph as graph_endpoint
from app.api.v1.endpoints.feedback import router as feedback_router
from app.api.v1.endpoints.graph import router as graph_router
from fastapi import FastAPI
from fastapi.testclient import TestClient

TENANT = uuid.UUID("aaaaaaaa-0000-0000-0000-0000000000df")
SERVICE_TOKEN = "service-token-for-the-agents-worker"
HEADERS = {"X-AiSOC-Service-Token": SERVICE_TOKEN}
_IDENTITY_READER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT, role="viewer", email="identity@example.invalid", scopes=["graph:read"])
_DISPOSITIONS_READER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT, role="viewer", email="reader@example.invalid", scopes=["alerts:read"])


class _Row:
    def __init__(self, **fields: Any) -> None:
        self.__dict__.update(fields)


class _Result:
    def __init__(self, rows: list[_Row]) -> None:
        self._rows = rows

    def fetchall(self) -> list[_Row]:
        return self._rows


class _Session:
    def __init__(self, rows: list[_Row]) -> None:
        self.rows = rows
        self.statements: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, statement: Any) -> _Result:
        self.statements.append((str(statement), dict(statement.compile().params)))
        return _Result(self.rows)


def _app(session: _Session | None = None, *, user: CurrentUser | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(feedback_router, prefix="/api/v1")
    app.include_router(graph_router, prefix="/api/v1")

    async def _db() -> Any:
        yield session

    app.dependency_overrides[get_db] = _db
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


def _decision_row(**over: Any) -> _Row:
    fields: dict[str, Any] = {
        "excluded_after_cutoff": 0,
        "without_timestamp": 0,
        "feedback_id": uuid.uuid4(),
        "analyst_disposition": "benign_true_positive",
        "ai_disposition": "true_positive",
        "reason_code": "known_admin_tool",
        "scope": "binary",
        "scope_value": "powershell.exe",
        "note": "Nightly reconciliation batch.",
        "created_at": datetime(2026, 4, 2, tzinfo=UTC),
        "rule_id": "rule-encoded-powershell",
        "by_rule": True,
        "by_entity": False,
    }
    fields.update(over)
    return _Row(**fields)


@pytest.fixture
def _service_token(monkeypatch):
    monkeypatch.setenv("AISOC_AGENTS_SERVICE_TOKEN", SERVICE_TOKEN)

    async def _noop(_db, _tenant):
        return None

    monkeypatch.setattr(feedback_endpoint, "set_rls_context", _noop)
    yield


_DISPO_URL = "/api/v1/feedback/recent-dispositions"
_IDENTITY_URL = "/api/v1/graph/identity-context"


class TestRecentDispositionsCredential:
    def test_a_missing_token_is_refused(self, _service_token) -> None:
        client = TestClient(_app(_Session([])))
        assert client.get(_DISPO_URL, params={"tenant_id": str(TENANT), "rule_id": "r"}).status_code == 401

    def test_an_authorised_console_principal_can_read(self, _service_token) -> None:
        user = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT, role="tenant_admin", email="a@example.invalid", scopes=["*"])
        client = TestClient(_app(_Session([]), user=user))
        assert client.get(_DISPO_URL, params={"tenant_id": str(TENANT), "rule_id": "r"}).status_code == 200

    def test_a_configured_shared_header_alone_is_refused(self, _service_token) -> None:
        client = TestClient(_app(_Session([])))
        assert client.get(_DISPO_URL, params={"tenant_id": str(TENANT), "rule_id": "r"}, headers=HEADERS).status_code == 401


class TestRecentDispositionsCutoff:
    def test_no_instant_named_means_no_predicate_and_no_echo(self, _service_token) -> None:
        session = _Session([_decision_row()])
        client = TestClient(_app(session, user=_DISPOSITIONS_READER))
        response = client.get(_DISPO_URL, params={"tenant_id": str(TENANT), "rule_id": "rule-encoded-powershell"}, headers=HEADERS)

        assert response.status_code == 200
        assert response.json()["as_of"] is None
        statement, params = session.statements[0]
        assert "created_at <= " not in statement
        assert "as_of" not in params

    def test_naming_an_instant_puts_the_predicate_in_and_echoes_it(self, _service_token) -> None:
        session = _Session([_decision_row()])
        client = TestClient(_app(session, user=_DISPOSITIONS_READER))
        response = client.get(
            _DISPO_URL,
            params={"tenant_id": str(TENANT), "rule_id": "r", "as_of": "2026-05-01T12:00:00+00:00"},
            headers=HEADERS,
        )

        assert response.json()["as_of"] == "2026-05-01T12:00:00Z"
        statement, params = session.statements[0]
        assert "created_at <= :as_of" in statement
        assert params["as_of"] == datetime(2026, 5, 1, 12, 0, tzinfo=UTC)

    def test_the_counts_survive_a_cutoff_that_refused_everything(self, _service_token) -> None:
        session = _Session([_decision_row(analyst_disposition=None, excluded_after_cutoff=9, without_timestamp=1)])
        client = TestClient(_app(session, user=_DISPOSITIONS_READER))
        body = client.get(
            _DISPO_URL,
            params={"tenant_id": str(TENANT), "rule_id": "r", "as_of": "2026-05-01T12:00:00+00:00"},
            headers=HEADERS,
        ).json()

        assert body["dispositions"] == []
        assert body["excluded_after_cutoff"] == 9
        assert body["without_timestamp"] == 1

    def test_the_reason_label_travels_with_the_code(self, _service_token) -> None:
        """``bad_detection_logic`` is a key in a table the prompt's reader lacks."""
        session = _Session([_decision_row(reason_code="bad_detection_logic")])
        client = TestClient(_app(session, user=_DISPOSITIONS_READER))
        body = client.get(_DISPO_URL, params={"tenant_id": str(TENANT), "rule_id": "r"}, headers=HEADERS).json()

        assert body["dispositions"][0]["reason_label"] == "Bad detection logic"

    def test_an_unknown_reason_code_falls_back_to_the_code_rather_than_raising(self, _service_token) -> None:
        """A row written before a code was retired must not 500 the route."""
        session = _Session([_decision_row(reason_code="retired_code")])
        client = TestClient(_app(session, user=_DISPOSITIONS_READER))
        body = client.get(_DISPO_URL, params={"tenant_id": str(TENANT), "rule_id": "r"}, headers=HEADERS).json()

        assert body["dispositions"][0]["reason_label"] == "retired_code"

    def test_entities_are_lowercased_and_deduplicated_before_binding(self, _service_token) -> None:
        session = _Session([_decision_row()])
        client = TestClient(_app(session, user=_DISPOSITIONS_READER))
        client.get(
            _DISPO_URL,
            params=[("tenant_id", str(TENANT)), ("rule_id", "r"), ("entities", "FIN-APP-03"), ("entities", "fin-app-03")],
            headers=HEADERS,
        )

        _, params = session.statements[0]
        assert params["entities"] == ["fin-app-03"]


class TestIdentityContextRoute:
    @pytest.fixture
    def _graph(self, monkeypatch):
        from app.services.incident_context import IdentityAccountRead

        control = {"identities": [], "calls": [], "excluded_after_cutoff": 0,
                   "excluded_unverifiable_import": 0, "import_timestamp_missing": 0}

        async def _fake(tenant_id, accounts, *, limit=5, as_of=None):
            control["calls"].append((tenant_id, accounts, limit, as_of))
            rows = control["identities"]
            excluded = control["excluded_after_cutoff"]
            unverifiable = control["excluded_unverifiable_import"]
            return IdentityAccountRead(
                status="success" if rows else "no_match", identities=rows, as_of=as_of,
                candidate_count=len(rows) + excluded + unverifiable, eligible_count=len(rows),
                excluded_after_cutoff=excluded, excluded_unverifiable_import=unverifiable,
                import_timestamp_missing=control["import_timestamp_missing"], without_timestamp=len(rows),
            )

        monkeypatch.setattr(graph_endpoint, "read_identity_context_for_accounts", _fake)
        return control

    def test_a_missing_token_is_refused(self, _graph) -> None:
        client = TestClient(_app())
        assert client.get(_IDENTITY_URL, params={"tenant_id": str(TENANT), "accounts": "a"}).status_code == 401
        assert not _graph["calls"]

    def test_shared_service_header_alone_no_longer_authorizes_identity_read(self, _graph) -> None:
        client = TestClient(_app())
        assert client.get(_IDENTITY_URL, params={"accounts": "a"}, headers=HEADERS).status_code == 401
        assert not _graph["calls"]

    def test_import_cutoff_and_excluded_counts_are_delegated_and_echoed(self, _graph) -> None:
        _graph["identities"] = [{"account": "a", "employee": "Before"}]
        _graph["excluded_after_cutoff"] = 1
        client = TestClient(_app(user=_IDENTITY_READER))
        response = client.get(_IDENTITY_URL, params={"accounts": "a", "as_of": "2026-05-01T12:00:00+00:00"})
        assert response.status_code == 200
        body = response.json()
        assert [row["employee"] for row in body["identities"]] == ["Before"]
        assert body["excluded_after_cutoff"] == 1 and body["candidate_count"] == 2
        assert _graph["calls"] == [(str(TENANT), ["a"], 5, datetime(2026, 5, 1, 12, tzinfo=UTC))]

    def test_every_served_row_remains_business_history_untestable(self, _graph) -> None:
        _graph["identities"] = [{"account": "a", "employee": "Current"}, {"account": "b", "employee": "Other"}]
        client = TestClient(_app(user=_IDENTITY_READER))
        body = client.get(_IDENTITY_URL, params=[("accounts", "a"), ("accounts", "b")]).json()
        assert len(body["identities"]) == body["without_timestamp"] == 2

    def test_no_cutoff_means_no_implicit_freeze(self, _graph) -> None:
        _graph["identities"] = [{"account": "a", "employee": "Whenever"}]
        client = TestClient(_app(user=_IDENTITY_READER))
        body = client.get(_IDENTITY_URL, params={"accounts": "a"}).json()
        assert body["as_of"] is None and body["excluded_after_cutoff"] == 0
        assert len(body["identities"]) == 1 and _graph["calls"][0][3] is None

    def test_unverifiable_import_is_explicitly_excluded_from_frozen_read(self, _graph) -> None:
        # Graph classifies missing/text/invalid stamps before LIMIT. The API
        # must preserve that rejection, not reconstruct a historical note.
        _graph["excluded_unverifiable_import"] = 1
        _graph["import_timestamp_missing"] = 1
        client = TestClient(_app(user=_IDENTITY_READER))
        body = client.get(_IDENTITY_URL, params={"accounts": "a", "as_of": "2026-05-01T12:00:00+00:00"}).json()
        assert body["source_status"] == "no_match" and body["identities"] == []
        assert body["excluded_unverifiable_import"] == body["import_timestamp_missing"] == 1
        assert body["without_timestamp"] == 0
