"""Member-to-Case entry points using the existing user and tenant dependencies."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.v1.deps import CurrentUser, require_permission
from app.db.rls import TenantDBSession
from .case_links import CaseLinkRequest, link_case, list_links
from .result_api import _explicit_bearer

router = APIRouter(prefix="/api/v2/investigation/case-links", tags=["case-links"])


@router.post("")
async def create_link(request: CaseLinkRequest, response: Response, db: TenantDBSession,
                      _credential: Annotated[None, Depends(_explicit_bearer)],
                      user: Annotated[CurrentUser, Depends(require_permission("cases:write"))]):
    user.require_permission("cases:read")
    user.require_permission("alerts:read")
    receipt, fresh = await link_case(db, user.tenant_id, user.user_id, request)
    response.status_code = 201 if fresh else 200
    return receipt


@router.get("")
async def read_links(db: TenantDBSession,
                     _credential: Annotated[None, Depends(_explicit_bearer)],
                     user: Annotated[CurrentUser, Depends(require_permission("cases:read"))],
                     incident_id: UUID | None = None, alert_id: UUID | None = None,
                     limit: int = Query(default=20, ge=1, le=50), cursor: str | None = None):
    user.require_permission("alerts:read")
    return await list_links(db, user.tenant_id, incident_id=incident_id, alert_id=alert_id, limit=limit, cursor=cursor)
