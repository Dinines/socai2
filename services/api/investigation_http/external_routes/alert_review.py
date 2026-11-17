"""External human-review candidate query through a dedicated read-only port."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime

from investigation_http.contracts import AlertReviewPage, AlertReviewQuery
from investigation_http.dependencies import (
    CurrentUser,
    alert_review_service,
    require_permission,
)
from investigation_http.errors import invoke, query_input
from investigation_http.ports import AlertReview

router = APIRouter(prefix="/socai2/alerts", tags=["socai2-alert-review"])
ReadUser = Annotated[CurrentUser, Depends(require_permission("alerts:read"))]
Service = Annotated[AlertReview, Depends(alert_review_service)]


@router.get("/{alert_id}/review-candidates", response_model=AlertReviewPage)
async def candidates(request: Request, alert_id: UUID, user: ReadUser, service: Service,
    time_from: AwareDatetime | None = None, time_to: AwareDatetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 5,
    cursor: Annotated[str | None, Query(max_length=4096)] = None):
    if set(request.query_params) - {"time_from", "time_to", "limit", "cursor"} or any(
        len(request.query_params.getlist(key)) != 1 for key in request.query_params):
        raise HTTPException(422, "alert_review_query_parameter_not_supported")
    query = query_input(AlertReviewQuery, time_from=time_from, time_to=time_to, limit=limit, cursor=cursor)
    return await invoke(service.read(user.tenant_id, alert_id, query))
