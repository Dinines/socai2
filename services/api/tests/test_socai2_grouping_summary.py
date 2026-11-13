"""Direct HTTP contract and input checks; SQL semantics use real-PG acceptance."""
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from app.api.v1.deps import CurrentUser, get_current_user
from app.socai2.grouping_contracts import GroupingQuery, GroupingSummary
from httpx import ASGITransport, AsyncClient
from investigation_http.dependencies import grouping_service
from investigation_http.main import app
from pydantic import ValidationError


def test_grouping_query_preserves_source_and_normalizes_time():
    query = GroupingQuery(source_namespace="Exact Source", time_from="2026-11-13T08:00:00+08:00")
    assert query.source_namespace == "Exact Source"
    assert query.time_from == datetime(2026, 11, 13, tzinfo=UTC)
    for values in ({"source_namespace": " "}, {"time_from": "2026-11-13T08:00:00"},
            {"time_from": "2026-11-13T08:00:00Z", "time_to": "2026-11-13T08:00:00Z"}, {"q": "x"}):
        with pytest.raises(ValidationError):
            GroupingQuery(**values)


def test_grouping_addition_keeps_existing_56_contracts():
    before = json.loads((Path(__file__).resolve().parents[3] / "docs/operations/evidence/grouping-summary-20261113-01/before-openapi.json").read_text())
    after = app.openapi()
    assert all(after["paths"][p] == value for p, value in before["paths"].items()
               if p != "/api/v1/socai2/cases/{case_id}/results/{result_id}/adopt")
    assert all(after["components"]["schemas"][name] == value for name, value in before["components"]["schemas"].items() if name != "AdoptCaseAIResult")


@pytest.mark.asyncio
async def test_grouping_literal_route_returns_null_and_rejects_unknown_parameters(monkeypatch):
    class Empty:
        async def read(self, tenant, query):
            assert tenant == UUID(int=1)
            return GroupingSummary(scope=query, alert_count=0, grouped_alert_count=0,
                ungrouped_alert_count=0, incident_count=0, in_progress_incident_count=0,
                compression_rate=None, observed_at=datetime(2026, 11, 13, tzinfo=UTC))
    monkeypatch.setattr(app, "dependency_overrides", dict(app.dependency_overrides))
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(UUID(int=3), UUID(int=1),
        "viewer", "grouping@example.invalid", scopes=["alerts:read"])
    app.dependency_overrides[grouping_service] = Empty
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
        path = "/api/v1/socai2/incidents/grouping-summary"
        response = await client.get(path)
        assert response.status_code == 200 and response.json()["compression_rate"] is None
        for params in ({"q": "x"}, {"handling_status": "new"}, {"limit": 20}, {"sort_by": "severity"},
                {"source_namespace": ""}, {"time_to": "not-a-date"}):
            response = await client.get(path, params=params)
            assert response.status_code == 422, response.text
