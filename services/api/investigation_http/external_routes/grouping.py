"""External incident queue summary; core reads are injected through a port."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime

from investigation_http.contracts import GroupingQuery, GroupingSummary
from investigation_http.dependencies import (
    CurrentUser,
    grouping_service,
    require_permission,
)
from investigation_http.errors import invoke, query_input
from investigation_http.ports import GroupingReads

User = Annotated[CurrentUser, Depends(require_permission("alerts:read"))]
Service = Annotated[GroupingReads, Depends(grouping_service)]
router = APIRouter(prefix="/socai2/incidents", tags=["socai2-grouping"])


@router.get("/grouping-summary", response_model=GroupingSummary)
async def read_grouping_summary(
    request: Request,
    user: User,
    service: Service,
    source_namespace: Annotated[str | None, Query(min_length=1, max_length=256)] = None,
    time_from: AwareDatetime | None = None,
    time_to: AwareDatetime | None = None,
):
    if set(request.query_params) - {"source_namespace", "time_from", "time_to"}:
        raise HTTPException(422, "grouping_query_parameter_not_supported")
    query = query_input(GroupingQuery, source_namespace=source_namespace, time_from=time_from, time_to=time_to)
    return await invoke(service.read(user.tenant_id, query))
