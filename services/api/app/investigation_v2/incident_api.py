"""Incident read API, mounted only in the explicit investigation v2 apps."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.deps import CurrentUser, require_permission
from app.db.rls import TenantDBSession
from .incident_reader import IncidentOverview, read_incident
from .incident_summary import attach_summary, generate_summary, load_summary
from .query_api import create_app as create_query_app
from .result_api import _explicit_bearer
from .related_investigations import attach_related, read_related

router = APIRouter(prefix="/api/v2/investigation/incidents", tags=["investigation-incidents"])


@router.get("/{incident_id}", response_model=IncidentOverview)
async def get_incident(
    incident_id: UUID,
    db: TenantDBSession,
    _credential: Annotated[None, Depends(_explicit_bearer)],
    user: Annotated[CurrentUser, Depends(require_permission("alerts:read"))],
):
    result = await read_incident(db, tenant_id=user.tenant_id, incident_id=incident_id)
    if result is None:
        raise HTTPException(404, "incident_not_found")
    record = await load_summary(db, user.tenant_id, incident_id)
    if record is not None and (record.source_refs or {}).get("include_investigations"):
        user.require_permission("cases:read")
        result = await attach_related(db, result)
    return attach_summary(result, record)


@router.get("/{incident_id}/investigations")
async def investigations(incident_id: UUID, db: TenantDBSession,
                         _credential: Annotated[None, Depends(_explicit_bearer)],
                         user: Annotated[CurrentUser, Depends(require_permission("alerts:read"))],
                         limit: int = Query(default=20, ge=1, le=50), cursor: str | None = None):
    user.require_permission("cases:read")
    overview = await read_incident(db, tenant_id=user.tenant_id, incident_id=incident_id)
    if overview is None:
        raise HTTPException(404, "incident_not_found")
    return {"incident_id": str(incident_id), "member_ids": [str(member.alert_id) for member in overview.members],
            "case_links_url": f"/api/v2/investigation/case-links?incident_id={incident_id}",
            **await read_related(db, user.tenant_id, [member.alert_id for member in overview.members],
                                 subject=f"incident:{incident_id}", limit=limit, cursor=cursor)}


@router.post("/{incident_id}/overview/refresh", response_model=IncidentOverview)
async def refresh_overview(
    incident_id: UUID,
    db: TenantDBSession,
    _credential: Annotated[None, Depends(_explicit_bearer)],
    user: Annotated[CurrentUser, Depends(require_permission("alerts:write"))],
    include_investigations: bool = False,
):
    user.require_permission("alerts:read")
    if include_investigations:
        user.require_permission("cases:read")
    overview = await read_incident(db, tenant_id=user.tenant_id, incident_id=incident_id)
    if overview is None:
        raise HTTPException(404, "incident_not_found")
    if include_investigations:
        overview = await attach_related(db, overview)
    result = await generate_summary(db, overview)
    # A failed basic refresh can still return an earlier Case-derived overview.
    if ((result.ai_overview_metadata or {}).get("source_refs") or {}).get("include_investigations"):
        user.require_permission("cases:read")
    await db.commit()
    return result


def create_app():
    app = create_query_app()
    app.title = "Investigation incident overview"
    app.include_router(router)
    return app
