"""External one-layer candidate read through a dedicated core use-case port."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime

from investigation_http.contracts import ExplorationPage, ExplorationQuery
from investigation_http.dependencies import (
    CurrentUser,
    exploration_service,
    require_permission,
)
from investigation_http.errors import invoke, query_input
from investigation_http.ports import CaseExploration

router = APIRouter(prefix="/socai2/cases", tags=["socai2-case-exploration"])
ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
Service = Annotated[CaseExploration, Depends(exploration_service)]


@router.get("/{case_id}/exploration-candidates", response_model=ExplorationPage)
async def candidates(request: Request, case_id: UUID, user: ReadUser, service: Service,
    alert_id: UUID | None = None, object_id: UUID | None = None,
    time_from: AwareDatetime | None = None, time_to: AwareDatetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=4096)] = None):
    if set(request.query_params) - {"alert_id", "object_id", "time_from", "time_to", "limit", "cursor"} or any(
        len(request.query_params.getlist(key)) != 1 for key in request.query_params):
        raise HTTPException(422, "exploration_query_parameter_not_supported")
    query = query_input(ExplorationQuery, alert_id=alert_id, object_id=object_id,
        time_from=time_from, time_to=time_to, limit=limit, cursor=cursor)
    return await invoke(service.read(user.tenant_id, case_id, query))
