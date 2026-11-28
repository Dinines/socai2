"""Incident aggregates on SQL substitutes; no persisted fixtures or model calls."""
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from app.socai2.baseline_store import BaselineStore
from app.socai2.page_contracts import (
    DerivedFields,
    IncidentDerivedFields,
    IncidentSubjectPage,
)
from app.socai2.page_reader import PageReader
from pydantic import ValidationError
from sqlalchemy.dialects import sqlite

TENANT, OTHER, INCIDENT, ELSEWHERE = (UUID(int=n) for n in range(1, 5))
NOW = datetime(2026, 11, 25, tzinfo=UTC)
FIELDS = {"active_member_count", "unknown_status_member_count", "detection_sources"}


class ArrayAggregate:
    """SQLite substitute for PostgreSQL array_agg; DISTINCT stays in the query."""

    def __init__(self):
        self.values = []

    def step(self, value):
        self.values.append(value)

    def finalize(self):
        return json.dumps(self.values)


def member_database():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("ATTACH DATABASE ':memory:' AS socai2")
    db.create_aggregate("array_agg", 1, ArrayAggregate)
    db.execute("""CREATE TABLE socai2.alerts (
        id TEXT, tenant_id TEXT, handling_status TEXT, connector_type TEXT,
        source_namespace TEXT, severity TEXT, event_time TEXT, business_updated_at TEXT)""")
    db.execute("""CREATE TABLE socai2.incident_alerts (
        tenant_id TEXT, incident_id TEXT, alert_id TEXT)""")
    # Repeated connector, namespace fallback, closed and unknown members.
    # An empty connector is deliberately retained, matching ?? rather than ||.
    members = [
        (TENANT, INCIDENT, "new", "lyc_connector_b", "lyc_fallback_unused"),
        (TENANT, INCIDENT, "in_progress", "lyc_connector_b", "lyc_fallback_unused"),
        (TENANT, INCIDENT, "completed", None, "lyc_namespace_a"),
        (TENANT, INCIDENT, "unknown", "", "lyc_fallback_unused"),
        (TENANT, ELSEWHERE, "new", "lyc_other_incident", "lyc_other_incident"),
        (OTHER, INCIDENT, "unknown", "lyc_other_tenant", "lyc_other_tenant"),
    ]
    for number, (tenant, incident, status, connector, namespace) in enumerate(members, 10):
        alert = UUID(int=number).hex
        db.execute("INSERT INTO socai2.alerts VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL)",
                   (alert, tenant.hex, status, connector, namespace))
        db.execute("INSERT INTO socai2.incident_alerts VALUES (?, ?, ?)",
                   (tenant.hex, incident.hex, alert))
    return db


def incident_row(identity):
    return {"id": identity, "tenant_id": TENANT, "source_namespace": "lyc_incident_source",
            "source_incident_id": str(identity), "title": "incident aggregate fixture", "description": None,
            "owner_id": None, "assignment_state": "unassigned", "owner_source_value": None,
            "assigned_at": None, "tags": [], "priority_value": None, "priority_state": "not_provided",
            "priority_source": None, "priority_basis": None, "business_updated_at": NOW,
            "reopened_at": None, "row_version": 1, "handling_status": "resolved",
            "severity_override": None, "severity_override_reason": None, "severity_override_at": None,
            "severity_override_by": None, "resolution_note": None, "resolved_at": NOW,
            "resolved_by": None, "created_at": NOW, "latest_diagnosis_id": None}


async def incident_view(monkeypatch, identity):
    monkeypatch.setattr("app.socai2.analysis_task_policy.AnalysisTaskPolicy.load", Mock(return_value=None))
    monkeypatch.setattr("app.socai2.case_relationship_reader.receiving_status", AsyncMock(return_value={
        "active_case_id": None, "can_receive_automatically": False, "reason_code": "no_target"}))
    ancillary = Mock()
    ancillary.mappings.return_value.all.return_value = []
    ancillary.scalar_one.return_value = 0
    session = Mock(execute=AsyncMock(return_value=ancillary))
    reader = PageReader(BaselineStore(session, TENANT), "incidents", identity)
    with closing(member_database()) as db:
        async def rows(query):
            if "members" not in query.selected_columns:
                return []  # Baseline execution status is unrelated to membership.
            sql = str(query.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
            result = dict(db.execute(sql).fetchone())
            result["detection_sources"] = json.loads(result["detection_sources"]) if result["detection_sources"] else None
            return [result]

        monkeypatch.setattr(reader, "rows", rows)
        return await reader.view(incident_row(identity))


@pytest.mark.asyncio
async def test_member_aggregates_include_all_states_and_only_current_tenant_incident(monkeypatch):
    view = await incident_view(monkeypatch, INCIDENT)
    derived = view.derived
    assert derived.member_count == 4
    assert derived.active_member_count == 2
    assert derived.unknown_status_member_count == 1
    assert derived.detection_sources == ["", "lyc_connector_b", "lyc_namespace_a"]
    # The incident is resolved; member handling states still determine activity.
    assert view.facts.handling_status == "resolved"
    page = IncidentSubjectPage(kind="incidents", items=[view], total=1, filtered_total=1,
                               next_before_id=None, next_cursor=None, overall_stats={}, observed_at=NOW)
    assert page.model_dump()["items"][0]["derived"] == view.model_dump()["derived"]


@pytest.mark.asyncio
async def test_zero_members_returns_real_zeros_and_no_incident_source(monkeypatch):
    view = await incident_view(monkeypatch, UUID(int=99))
    assert view.derived.member_count == 0
    assert view.derived.active_member_count == 0
    assert view.derived.unknown_status_member_count == 0
    assert view.derived.detection_sources == []


def test_incident_schema_keeps_missing_aggregates_nullable_and_alerts_unchanged():
    base = {"severity_group": None, "tactics": [], "tactic_counting_note": "", "object_count": 0,
            "baseline_execution_counts": {"running": 0, "unknown": 0}}
    assert {key: IncidentDerivedFields(**base).model_dump()[key] for key in FIELDS} == dict.fromkeys(FIELDS)
    assert not FIELDS & DerivedFields.model_fields.keys()
    assert not FIELDS & DerivedFields(**base).model_dump().keys()
    for field in ("active_member_count", "unknown_status_member_count"):
        with pytest.raises(ValidationError):
            IncidentDerivedFields(**base, **{field: -1})
