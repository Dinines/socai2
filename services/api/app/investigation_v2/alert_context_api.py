"""Alert entry into saved triage, incident and Case investigation records."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.v1.deps import CurrentUser, require_permission
from app.db.rls import TenantDBSession
from app.models.alert import Alert
from app.services.alert_projection import alert_source, alert_objects, detection_fields, assignee_names
from .case_links import source_incident
from .incident_reader import latest_triage, saved_correlation_basis
from .related_investigations import read_related
from .result_api import _explicit_bearer

router = APIRouter(prefix="/api/v2/investigation/alerts", tags=["alert-investigation-context"])


@router.get("/{alert_id}/investigation-context")
async def context(alert_id: UUID, db: TenantDBSession,
                  _credential: Annotated[None, Depends(_explicit_bearer)],
                  user: Annotated[CurrentUser, Depends(require_permission("alerts:read"))],
                  limit: int = Query(default=20, ge=1, le=50), cursor: str | None = None):
    user.require_permission("cases:read")
    alert = (await db.execute(select(Alert).where(
        Alert.tenant_id == user.tenant_id, Alert.id == alert_id))).scalar_one_or_none()
    if alert is None:
        raise HTTPException(404, "alert_not_found")
    triage = (await latest_triage(db, user.tenant_id, [alert_id])).get(str(alert_id))
    incident_id = source_incident(alert)
    names = await assignee_names(db, user.tenant_id, [alert])
    return {"alert_id": str(alert_id), "title": alert.title, "severity": alert.severity,
            "status": alert.status, "disposition": alert.disposition, "saved_analysis": alert.ai_summary,
            "source": alert_source(alert), "objects": alert_objects(alert), "detection": detection_fields(alert),
            "legacy_case_id": alert.case_id,
            "assigned_to_id": alert.assigned_to_id, "assigned_at": alert.assigned_at, "assigned_to_name": names.get(alert.assigned_to_id),
            "incident_id": str(incident_id) if incident_id else None,
            "correlation_basis": saved_correlation_basis(alert),
            "incident_url": f"/api/v2/investigation/incidents/{incident_id}" if incident_id else None,
            "triage": triage, "triage_url": f"/api/v1/investigations/{triage.run_id}" if triage else None,
            "processing_context_url": f"/api/v1/alerts/{alert_id}/processing-context",
            "case_links_url": f"/api/v2/investigation/case-links?alert_id={alert_id}",
            "executions_url": f"/api/v2/investigation/executions?alert_id={alert_id}",
            "investigations": await read_related(db, user.tenant_id, [alert_id], subject=f"alert:{alert_id}",
                                                 limit=limit, cursor=cursor)}
