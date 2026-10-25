"""Incident read API, mounted only in the explicit investigation v2 apps."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import CurrentUser, require_permission
from app.db.rls import TenantDBSession
from .incident_reader import IncidentOverview, read_incident
from .query_api import create_app as create_query_app
from .result_api import _explicit_bearer

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
    return result


def create_app():
    app = create_query_app()
    app.title = "Investigation incident overview"
    app.include_router(router)
    return app
