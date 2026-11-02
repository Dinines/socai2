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
from app.services.alert_projection import alert_objects, alert_source, detection_fields, assignee_names


class SavedTriage(BaseModel):
    event_id: UUID
    run_id: UUID
    recorded_at: datetime
    summary: str
    verdict: str | None
    rationale: str | None
    auto_closed: bool | None
    confidence: float | None = None
    score_source: str = "triage_event.payload.confidence"
    score_meaning: str = "confidence_in_paired_verdict_not_risk"
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
    case_id: UUID | None = Field(description="Legacy single pointer; case_ids is the current membership when requested")
    connector_id: UUID | None
    source_alert_id: str | None
    saved_analysis: str | None
    recommendations: list[Any] = Field(default_factory=list)
    triage: SavedTriage | None
    alert_url: str
    correlation_basis: dict[str, Any] | None = None
    source: dict[str, Any] = Field(default_factory=dict)
    detection: dict[str, Any] = Field(default_factory=dict)
    objects: list[dict[str, str]] = Field(default_factory=list)
    mitre_tactics: list[str] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    assets: dict[str, Any] | None = None
    case_ids: list[UUID] | None = None
    case_ids_truncated: bool | None = None
    case_links_url: str | None = None
    assigned_to_id: UUID | None = None
    assigned_at: datetime | None = None
    assigned_to_name: str | None = None


class IncidentOverview(BaseModel):
    incident_id: UUID
    tenant_id: UUID
    title: str
    severity: str
    member_count: int
    first_seen: datetime
    last_seen: datetime
    source_updated_at: datetime | None
    updated_at: datetime | None = None
    tactic_counts: dict[str, int] = Field(default_factory=dict)
    tactic_count_notice: str = "每条告警在各已标记阶段各计1次，阶段数量之和可能超过告警总数；标签不证明攻击事实。"
    object_links: list[dict[str, str]] = Field(default_factory=list)
    asset_coverage: dict[str, Any] | None = None
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
    investigations_url: str | None = None
    executions_url: str | None = None
    investigations: dict[str, Any] | None = None


def _strings(values: Any) -> list[str]:
    return [value for value in values if isinstance(value, str) and value] if isinstance(values, list) else []


def saved_correlation_basis(alert: Alert) -> dict[str, Any] | None:
    """Read the saved decision; never reconstruct historical reasons from today's fields."""
    metadata = alert.enrichment_data if isinstance(alert.enrichment_data, dict) else {}
    fusion = metadata.get("socai2_fusion")
    basis = fusion.get("correlation_basis") if isinstance(fusion, dict) else None
    return basis if isinstance(basis, dict) else None


def _entities(alerts: list[Alert]) -> list[dict[str, str]]:
    pairs = {(item["type"], item["value"]) for alert in alerts for item in alert_objects(alert)}
    return [{"type": kind, "value": value} for kind, value in sorted(pairs)]


def _triage(event: InvestigationEvent) -> SavedTriage:
    payload = event.payload if isinstance(event.payload, dict) else {}
    return SavedTriage(
        event_id=event.id, run_id=event.run_id, recorded_at=event.ts, summary=event.summary,
        verdict=payload.get("verdict"), rationale=payload.get("rationale"),
        auto_closed=payload.get("auto_closed"),
        confidence=payload.get("confidence"),
        findings=payload.get("findings") or [], proposed_actions=payload.get("proposed_actions") or [],
    )


async def latest_triage(db, tenant_id, member_ids):
    query = select(InvestigationRun.raw_alert["id"].astext.label("alert_id"), InvestigationEvent).join(
        InvestigationRun, InvestigationRun.id == InvestigationEvent.run_id).where(
        InvestigationRun.tenant_id == tenant_id, InvestigationEvent.tenant_id == tenant_id,
        InvestigationRun.raw_alert["id"].astext.in_([str(value) for value in member_ids]),
        InvestigationEvent.kind == "triage_verdict",
    ).order_by(InvestigationEvent.ts.desc(), InvestigationEvent.id.desc())
    latest = {}
    for alert_id, event in (await db.execute(query)).all():
        if alert_id not in latest:
            latest[alert_id] = _triage(event)
    return latest


async def read_incident(db: AsyncSession, *, tenant_id: UUID, incident_id: UUID, include_assets=False) -> IncidentOverview | None:
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

    latest = await latest_triage(db, tenant_id, [alert.id for alert in alerts])
    names = await assignee_names(db, tenant_id, alerts)

    members = [IncidentMember(
        alert_id=alert.id, title=alert.title, severity=alert.severity,
        status=alert.status, disposition=alert.disposition,
        event_time=alert.event_time, updated_at=alert.updated_at,
        case_id=alert.case_id, connector_id=alert.connector_id, source_alert_id=alert_source(alert)["source_alert_id"],
        saved_analysis=alert.ai_summary, recommendations=alert.ai_recommendations or [],
        triage=latest.get(str(alert.id)), alert_url=f"/api/v1/alerts/{alert.id}",
        correlation_basis=saved_correlation_basis(alert),
        source=alert_source(alert), detection=detection_fields(alert), objects=alert_objects(alert),
        mitre_tactics=sorted(set(_strings(alert.mitre_tactics))),
        mitre_techniques=sorted(set(_strings(alert.mitre_techniques))),
        case_links_url=f"/api/v2/investigation/case-links?alert_id={alert.id}",
        assigned_to_id=alert.assigned_to_id, assigned_at=alert.assigned_at, assigned_to_name=names.get(alert.assigned_to_id),
    ) for alert in alerts]
    asset_coverage = None
    if include_assets:
        from app.services.processing_context import LIMIT, read_asset_context
        for alert, member in zip(alerts[:LIMIT], members[:LIMIT], strict=True):
            member.assets = await read_asset_context(db, alert)
        asset_coverage = {"read_member_ids": [str(m.alert_id) for m in members[:LIMIT]],
                          "omitted_member_ids": [str(m.alert_id) for m in members[LIMIT:]],
                          "notice": "当前库存匹配；无匹配或查询失败不证明资产不存在，匹配不证明攻击关联。"}
    severity_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    severity = max((alert.severity for alert in alerts), key=lambda value: severity_order.get(value, -1))
    updated = [alert.updated_at for alert in alerts if alert.updated_at is not None]
    business_updated = max(updated) if updated else None
    updated.extend(triage.recorded_at for triage in latest.values())
    return IncidentOverview(
        incident_id=incident_id, tenant_id=tenant_id, title=f"Incident: {alerts[0].title}",
        severity=severity, member_count=len(members),
        first_seen=min(alert.event_time for alert in alerts), last_seen=max(alert.last_seen for alert in alerts),
        updated_at=business_updated,
        tactic_counts=dict(Counter(tactic for member in members for tactic in member.mitre_tactics)),
        object_links=[{"source_alert_id": str(member.alert_id), **item} for member in members for item in member.objects],
        asset_coverage=asset_coverage,
        source_updated_at=max(updated) if updated else None,
        by_status=dict(Counter(member.status or "unknown" for member in members)),
        by_disposition=dict(Counter(member.disposition or "unassessed" for member in members)),
        by_triage_verdict=dict(Counter(triage.verdict or "unknown" for triage in latest.values())),
        members_without_saved_triage=len(members) - len(latest),
        entities=_entities(alerts),
        mitre_tactics=sorted({value for alert in alerts for value in _strings(alert.mitre_tactics)}),
        mitre_techniques=sorted({value for alert in alerts for value in _strings(alert.mitre_techniques)}),
        members=members, investigations_url=f"/api/v2/investigation/incidents/{incident_id}/investigations",
        executions_url=f"/api/v2/investigation/executions?incident_id={incident_id}",
    )
