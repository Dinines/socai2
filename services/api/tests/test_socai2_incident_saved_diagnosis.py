"""Direct E29 projection checks with synthetic rows and the real read SQL."""

import json
import sqlite3
from contextlib import closing
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from app.socai2.baseline_store import BaselineStore
from app.socai2.page_reader import PageReader
from investigation_http.main import app
from sqlalchemy.dialects import sqlite
from test_socai2_incident_member_aggregates import (
    ELSEWHERE,
    INCIDENT,
    OTHER,
    TENANT,
    incident_row,
)

PUBLISHED, ADOPTED_RUN, LATEST_RUN, UNVERIFIABLE = (UUID(int=n) for n in range(10, 14))


@pytest.fixture
def incident_fixture(monkeypatch):
    monkeypatch.setattr("app.socai2.analysis_task_policy.AnalysisTaskPolicy.load", Mock(return_value=None))
    monkeypatch.setattr("app.socai2.case_relationship_reader.receiving_status", AsyncMock(return_value={
        "active_case_id": None, "can_receive_automatically": False, "reason_code": "no_target"}))
    reject_freshness = Mock(side_effect=AssertionError("overview must not calculate freshness"))
    reject_history = AsyncMock(side_effect=AssertionError("overview must not read history"))
    monkeypatch.setattr("app.socai2.page_reader.freshness_sql", reject_freshness)
    monkeypatch.setattr("app.socai2.stage_reader.StageReader.entry", reject_history)
    monkeypatch.setattr("app.socai2.stage_reader.StageReader.page", reject_history)

    row = incident_row(INCIDENT)
    row["latest_diagnosis_id"] = PUBLISHED
    ancillary = Mock()
    ancillary.mappings.return_value.all.return_value = []
    ancillary.scalar_one.return_value = 0
    ancillary.scalar_one_or_none.return_value = None
    store = BaselineStore(Mock(execute=AsyncMock(return_value=ancillary)), TENANT)
    reader = PageReader(store, "incidents", INCIDENT)
    monkeypatch.setattr(reader, "subject", AsyncMock(return_value=row))

    async def rows(statement):
        if "members" in statement.selected_columns:
            return [{"members": 0, "active_members": 0, "unknown_status_members": 0, "detection_sources": [],
                     "first_activity_at": None, "last_activity_at": None, "member_updated_at": None,
                     "rank": None, "unknown_times": 0, "unknown_severities": 0}]
        return []

    monkeypatch.setattr(reader, "rows", rows)
    with closing(sqlite3.connect(":memory:")) as db:
        db.row_factory = sqlite3.Row
        db.executescript("""
            ATTACH DATABASE ':memory:' AS socai2;
            CREATE TABLE socai2.runs (id TEXT, tenant_id TEXT, incident_id TEXT, kind TEXT,
                state TEXT, delivery_state TEXT, stop_reason TEXT, requested_at TEXT);
            CREATE TABLE socai2.incident_diagnoses (id TEXT, tenant_id TEXT, incident_id TEXT,
                source_run_id TEXT, state TEXT, summary TEXT, diagnosis TEXT, open_questions TEXT, business_verdict TEXT);
        """)
        db.executemany("INSERT INTO socai2.runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
            (ADOPTED_RUN.hex, TENANT.hex, INCIDENT.hex, "incident_diagnosis", "completed", "complete", None, "1"),
            (LATEST_RUN.hex, TENANT.hex, INCIDENT.hex, "incident_diagnosis", "failed", "none", "synthetic_failed", "2"),
            (UUID(int=14).hex, TENANT.hex, ELSEWHERE.hex, "incident_diagnosis", "completed", "complete", None, "3"),
            (UUID(int=15).hex, OTHER.hex, INCIDENT.hex, "incident_diagnosis", "completed", "complete", None, "3"),
            (UUID(int=16).hex, TENANT.hex, INCIDENT.hex, "baseline", "completed", "complete", None, "3"),
        ])
        db.executemany("INSERT INTO socai2.incident_diagnoses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            (PUBLISHED.hex, TENANT.hex, INCIDENT.hex, ADOPTED_RUN.hex, "completed", "Saved summary",
             json.dumps({"conclusion": "Saved conclusion", "other": "not part of the overview"}),
             json.dumps([" First? ", {"question": "Second?", "text": "Unused"}, {"text": "Third?"}, ""]), "needs_review"),
            (PUBLISHED.hex, OTHER.hex, INCIDENT.hex, ADOPTED_RUN.hex, "completed", "Wrong tenant", None, None, None),
            (PUBLISHED.hex, TENANT.hex, ELSEWHERE.hex, ADOPTED_RUN.hex, "completed", "Wrong event", None, None, None),
            (UNVERIFIABLE.hex, TENANT.hex, INCIDENT.hex, UUID(int=14).hex, "completed", "Wrong Run", None, None, None),
        ])
        reads = []

        async def one(statement):
            sql = str(statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
            reads.append(sql)
            values = db.execute(sql).fetchall()
            assert len(values) <= 1
            if not values:
                return None
            result = dict(values[0])
            for field in ("id", "source_run_id", "run_id"):
                if result.get(field) is not None:
                    result[field] = UUID(result[field])
            for field in ("conclusion", "open_questions"):
                if result.get(field) is not None:
                    result[field] = json.loads(result[field])
            return result

        monkeypatch.setattr(store, "one", one)
        yield reader, row, reads


@pytest.mark.asyncio
async def test_detail_keeps_the_older_adopted_result_and_newer_failed_attempt(incident_fixture):
    reader, _, reads = incident_fixture
    body = (await reader.incident_detail()).model_dump(mode="json")
    assert body["published_diagnosis"] == {
        "id": str(PUBLISHED), "source_run_id": str(ADOPTED_RUN), "summary": "Saved summary",
        "conclusion": "Saved conclusion", "open_questions": [" First? ", "Second?", "Third?"],
    }
    assert body["latest_attempt"] == {"run_id": str(LATEST_RUN), "state": "failed",
                                      "delivery_state": "none", "stop_reason": "synthetic_failed"}
    assert body["business_verdict"] == "needs_review"
    assert len(reads) == 2 and "LIMIT 1" in reads[0]


@pytest.mark.asyncio
async def test_detail_null_adoption_and_list_without_saved_projection(incident_fixture):
    reader, row, reads = incident_fixture
    row["latest_diagnosis_id"] = None
    detail = await reader.incident_detail()
    assert detail.published_diagnosis is None and detail.latest_attempt.run_id == LATEST_RUN
    assert len(reads) == 1

    row["latest_diagnosis_id"] = UNVERIFIABLE
    detail = await reader.incident_detail()
    assert detail.published_diagnosis is None and detail.latest_attempt.run_id == LATEST_RUN
    view = await reader.view(row)
    assert {"published_diagnosis", "latest_attempt"}.isdisjoint(view.model_dump())
    assert view.derived.active_member_count == 0


def test_saved_projection_schema_is_exclusive_to_incident_detail():
    spec = app.openapi()
    schemas = spec["components"]["schemas"]
    prefix = "/api/v1/socai2"
    paths = {
        "/incidents": "IncidentSubjectPage", "/incidents/{incident_id}": "IncidentDetailView",
        "/alerts/{alert_id}": "SubjectView", "/incidents/{incident_id}/analysis": "IncidentStagePage",
        "/incidents/{incident_id}/analysis/runs/{run_id}": "IncidentStageEntry",
    }
    for route, schema in paths.items():
        assert spec["paths"][prefix + route]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{schema}"}
    fields = {"published_diagnosis", "latest_attempt"}
    assert fields <= set(schemas["IncidentDetailView"]["properties"])
    for schema in ("IncidentSubjectView", "SubjectView", "IncidentStagePage", "IncidentStageEntry"):
        assert fields.isdisjoint(schemas[schema]["properties"])
    assert {"active_member_count", "unknown_status_member_count", "detection_sources"} <= set(
        schemas["IncidentDerivedFields"]["properties"])
