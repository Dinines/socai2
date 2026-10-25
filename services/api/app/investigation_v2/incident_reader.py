"""Current Fusion Incident members and their saved triage results."""
from collections import Counter
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.investigation import InvestigationEvent, InvestigationRun


class SavedTriage(BaseModel):
    event_id: UUID
    run_id: UUID
    recorded_at: datetime
    summary: str
    verdict: str | None
    rationale: str | None
    auto_closed: bool | None
    findings: list[Any] = Field(default_factory=list)
    proposed_actions: list[Any] = Field(default_factory=list)


class IncidentMember(BaseModel):
    alert_id: UUID
    title: str
    severity: str
    status: str | None
    disposition: str | None
    event_time: datetime
    updated_at: datetime | None
    case_id: UUID | None
    connector_id: UUID | None
    source_alert_id: str | None
    saved_analysis: str | None
    recommendations: list[Any] = Field(default_factory=list)
    triage: SavedTriage | None
    alert_url: str


class IncidentOverview(BaseModel):
    incident_id: UUID
    tenant_id: UUID
    title: str
    severity: str
    member_count: int
    first_seen: datetime
    last_seen: datetime
    source_updated_at: datetime | None
    by_status: dict[str, int]
    by_disposition: dict[str, int]
    by_triage_verdict: dict[str, int]
    members_without_saved_triage: int
    entities: list[dict[str, str]]
    mitre_tactics: list[str]
    mitre_techniques: list[str]
    members: list[IncidentMember]
    # Incident handling state is not inferred from member or Run statuses.
    handling_status: str | None = None
    ai_overview: str | None = None
    ai_overview_metadata: dict[str, Any] | None = None


def _strings(values: Any) -> list[str]:
    return [value for value in values if isinstance(value, str) and value] if isinstance(values, list) else []


def _entities(alerts: list[Alert]) -> list[dict[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for alert in alerts:
        for kind, field in (("host", "affected_hosts"), ("user", "affected_users"), ("ip", "affected_ips")):
            pairs.update((kind, value) for value in _strings(getattr(alert, field)))
        for entity in alert.entities or []:
            if isinstance(entity, dict):
                kind, value = entity.get("type"), entity.get("value")
                if isinstance(kind, str) and isinstance(value, str) and kind and value:
                    pairs.add((kind, value))
    return [{"type": kind, "value": value} for kind, value in sorted(pairs)]


def _triage(event: InvestigationEvent) -> SavedTriage:
    payload = event.payload if isinstance(event.payload, dict) else {}
    return SavedTriage(
        event_id=event.id, run_id=event.run_id, recorded_at=event.ts, summary=event.summary,
        verdict=payload.get("verdict"), rationale=payload.get("rationale"),
        auto_closed=payload.get("auto_closed"),
        findings=payload.get("findings") or [], proposed_actions=payload.get("proposed_actions") or [],
    )


async def read_incident(db: AsyncSession, *, tenant_id: UUID, incident_id: UUID) -> IncidentOverview | None:
    """Read PG membership and the latest explicit per-member triage verdict.

    Redis correlation windows may already have expired. The PG Alert row's
    ID is the canonical member identity; neither Redis member IDs nor the
    historically overloaded Run.case_id establish that relationship.
    """
    members_query = (
        select(Alert)
        .where(
            Alert.tenant_id == tenant_id,
            Alert.enrichment_data["socai2_fusion"]["incident_id"].astext == str(incident_id),
        )
        .order_by(Alert.event_time, Alert.id)
    )
    alerts = list((await db.execute(members_query)).scalars().all())
    if not alerts:
        return None

    member_ids = [str(alert.id) for alert in alerts]
    triage_query = (
        select(InvestigationRun.raw_alert["id"].astext.label("alert_id"), InvestigationEvent)
        .join(InvestigationRun, InvestigationRun.id == InvestigationEvent.run_id)
        .where(
            InvestigationRun.tenant_id == tenant_id,
            InvestigationEvent.tenant_id == tenant_id,
            InvestigationRun.raw_alert["id"].astext.in_(member_ids),
            InvestigationEvent.kind == "triage_verdict",
        )
        .order_by(InvestigationEvent.ts.desc(), InvestigationEvent.id.desc())
    )
    latest: dict[str, SavedTriage] = {}
    for alert_id, event in (await db.execute(triage_query)).all():
        if alert_id not in latest:
            latest[alert_id] = _triage(event)

    members = [IncidentMember(
        alert_id=alert.id, title=alert.title, severity=alert.severity,
        status=alert.status, disposition=alert.disposition,
        event_time=alert.event_time, updated_at=alert.updated_at,
        case_id=alert.case_id, connector_id=alert.connector_id, source_alert_id=alert.external_id,
        saved_analysis=alert.ai_summary, recommendations=alert.ai_recommendations or [],
        triage=latest.get(str(alert.id)), alert_url=f"/api/v1/alerts/{alert.id}",
    ) for alert in alerts]
    severity_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    severity = max((alert.severity for alert in alerts), key=lambda value: severity_order.get(value, -1))
    updated = [alert.updated_at for alert in alerts if alert.updated_at is not None]
    updated.extend(triage.recorded_at for triage in latest.values())
    return IncidentOverview(
        incident_id=incident_id, tenant_id=tenant_id, title=f"Incident: {alerts[0].title}",
        severity=severity, member_count=len(members),
        first_seen=min(alert.first_seen for alert in alerts), last_seen=max(alert.last_seen for alert in alerts),
        source_updated_at=max(updated) if updated else None,
        by_status=dict(Counter(member.status or "unknown" for member in members)),
        by_disposition=dict(Counter(member.disposition or "unassessed" for member in members)),
        by_triage_verdict=dict(Counter(triage.verdict or "unknown" for triage in latest.values())),
        members_without_saved_triage=len(members) - len(latest),
        entities=_entities(alerts),
        mitre_tactics=sorted({value for alert in alerts for value in _strings(alert.mitre_tactics)}),
        mitre_techniques=sorted({value for alert in alerts for value in _strings(alert.mitre_techniques)}),
        members=members,
    )
