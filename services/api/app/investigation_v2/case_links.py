"""Explicit Alert/Incident member transfers into Cases, without starting analysis."""
from datetime import UTC, datetime
import hashlib
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import DateTime, ForeignKey, select, text, tuple_
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.alert import Alert
from app.models.case import Case
from .pagination import decode_cursor, encode_cursor


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AlertSource(StrictRequest):
    type: Literal["alerts"]
    alert_ids: list[UUID] = Field(min_length=1)

    @field_validator("alert_ids")
    @classmethod
    def unique_members(cls, value):
        if len(value) != len(set(value)) or any(not item.int for item in value):
            raise ValueError("nonempty_unique_member_ids_required")
        return sorted(value)


class IncidentSource(AlertSource):
    type: Literal["incident"]
    incident_id: UUID


class CreateTarget(StrictRequest):
    mode: Literal["create"]
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None


class AttachTarget(StrictRequest):
    mode: Literal["attach"]
    case_id: UUID


class CaseLinkRequest(StrictRequest):
    operation_key: UUID
    source: Annotated[AlertSource | IncidentSource, Field(discriminator="type")]
    target: Annotated[CreateTarget | AttachTarget, Field(discriminator="mode")]

    @field_validator("operation_key")
    @classmethod
    def nonnil_key(cls, value):
        if not value.int:
            raise ValueError("nonnil_operation_key_required")
        return value


class CaseLinkRecord(Base):
    __tablename__ = "investigation_case_links"

    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True)
    operation_key: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    link_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), unique=True, nullable=False)
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("aisoc_cases.id"), nullable=False)
    selected_member_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PGUUID(as_uuid=True)), nullable=False)
    source_incident_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PGUUID(as_uuid=True)), nullable=False)
    intent: Mapped[dict] = mapped_column(JSONB, nullable=False)
    receipt: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def source_incident(alert):
    fusion = (alert.enrichment_data or {}).get("socai2_fusion")
    try:
        return UUID(str(fusion.get("incident_id"))) if isinstance(fusion, dict) else None
    except (ValueError, TypeError):
        return None


async def link_case(db, tenant_id: UUID, actor_id: UUID, request: CaseLinkRequest):
    """Commit the Case change and immutable receipt together; retries only read."""
    intent = {"actor_id": str(actor_id), "request": request.model_dump(mode="json")}
    lock_key = int.from_bytes(hashlib.sha256(
        f"case-link:{tenant_id}:{request.operation_key}".encode()).digest()[:8], "big", signed=True)
    # Transaction-scoped serialization only for the same operation identity.
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    saved = (await db.execute(select(CaseLinkRecord).where(
        CaseLinkRecord.tenant_id == tenant_id, CaseLinkRecord.operation_key == request.operation_key,
    ))).scalar_one_or_none()
    if saved is not None:
        if saved.intent != intent:
            raise HTTPException(409, "case_link_operation_conflict")
        return saved.receipt, False

    target, existing_members = request.target, set()
    if target.mode == "attach":
        case = (await db.execute(select(Case.id, Case.status, Case.alert_ids).where(
            Case.tenant_id == tenant_id, Case.id == target.case_id,
        ).with_for_update())).one_or_none()
        if case is None:
            raise HTTPException(404, "case_not_found")
        if case.status in {"resolved", "closed"}:
            raise HTTPException(409, "case_not_open")
        existing_members = {UUID(str(value)) for value in case.alert_ids or []}

    selected = request.source.alert_ids
    alerts = list((await db.execute(select(Alert).where(
        Alert.tenant_id == tenant_id, Alert.id.in_(selected),
    ).order_by(Alert.id).with_for_update(read=True))).scalars().all())
    if {alert.id for alert in alerts} != set(selected):
        raise HTTPException(404, "alert_not_found")
    selection_kind = "explicit_alerts"
    if request.source.type == "incident":
        incident_id = request.source.incident_id
        current = set((await db.execute(select(Alert.id).where(
            Alert.tenant_id == tenant_id,
            Alert.enrichment_data["socai2_fusion"]["incident_id"].astext == str(incident_id),
        ))).scalars().all())
        if not current:
            raise HTTPException(404, "incident_not_found")
        if any(source_incident(alert) != incident_id for alert in alerts):
            raise HTTPException(409, "incident_membership_changed")
        selection_kind = "all_current" if current == set(selected) else "subset"

    now, link_id = datetime.now(UTC), uuid4()
    case_id = uuid4() if target.mode == "create" else target.case_id
    added, already = sorted(set(selected) - existing_members), sorted(set(selected) & existing_members)
    incident_ids = sorted({value for alert in alerts if (value := source_incident(alert)) is not None})
    if target.mode == "create":
        order = {value: index for index, value in enumerate(("info", "low", "medium", "high", "critical"))}
        severity = max((alert.severity for alert in alerts if alert.severity in order), key=order.get, default="medium")
        # Use the surviving Case table's existing columns/defaults, as the v1 API does.
        await db.execute(text("""INSERT INTO aisoc_cases
            (id, tenant_id, case_number, title, description, severity, status, alert_ids,
             created_by, opened_at, created_at, updated_at)
            VALUES (:id, :tenant, :number, :title, :description, :severity, 'new',
                    CAST(:members AS UUID[]), :actor, :now, :now, :now)"""),
            {"id": case_id, "tenant": tenant_id, "number": f"CASE-{case_id.hex[:24]}",
             "title": target.title, "description": target.description, "severity": severity,
             "members": selected, "actor": str(actor_id), "now": now})
    elif added:
        await db.execute(text("""UPDATE aisoc_cases SET alert_ids = CAST(:members AS UUID[]),
            updated_at = :now WHERE tenant_id = :tenant AND id = :id"""),
            {"members": sorted(existing_members | set(selected)), "now": now, "tenant": tenant_id, "id": case_id})
    receipt = {
        "operation_key": str(request.operation_key), "link_id": str(link_id), "case_id": str(case_id),
        "case_action": "created" if target.mode == "create" else "attached", "source_type": request.source.type,
        "source_incident_ids": list(map(str, incident_ids)), "selected_member_ids": list(map(str, selected)),
        "added_member_ids": list(map(str, added)), "already_linked_member_ids": list(map(str, already)),
        "selection_kind": selection_kind, "created_at": now.isoformat(),
        "case_url": f"/api/v1/cases/{case_id}",
        "investigate_url": f"/api/v2/investigation/cases/{case_id}/investigate",
    }
    db.add(CaseLinkRecord(tenant_id=tenant_id, operation_key=request.operation_key, link_id=link_id,
        case_id=case_id, selected_member_ids=selected, source_incident_ids=incident_ids,
        intent=intent, receipt=receipt, created_at=now))
    await db.commit()
    return receipt, True


async def list_links(db, tenant_id, *, incident_id=None, alert_id=None, limit=20, cursor=None):
    if (incident_id is None) == (alert_id is None):
        raise HTTPException(422, "exactly_one_link_source_required")
    scope = f"case-links:{tenant_id}:{incident_id}:{alert_id}"
    after = decode_cursor(cursor, scope)
    query = select(CaseLinkRecord).where(CaseLinkRecord.tenant_id == tenant_id)
    query = query.where(CaseLinkRecord.source_incident_ids.contains([incident_id]) if incident_id is not None
                        else CaseLinkRecord.selected_member_ids.contains([alert_id]))
    if after:
        query = query.where(tuple_(CaseLinkRecord.created_at, CaseLinkRecord.link_id) < after)
    rows = list((await db.execute(query.order_by(
        CaseLinkRecord.created_at.desc(), CaseLinkRecord.link_id.desc()).limit(limit + 1))).scalars().all())
    items = []
    for row in rows[:limit]:
        items.append({key: row.receipt[key] for key in (
            "link_id", "case_id", "selected_member_ids", "source_incident_ids", "created_at", "case_url")})
        items[-1]["investigations_url"] = f"/api/v2/investigation/cases/{row.case_id}/investigations"
    return {"items": items, "next_cursor": encode_cursor(rows[limit - 1].created_at, rows[limit - 1].link_id, scope)
            if len(rows) > limit else None}
