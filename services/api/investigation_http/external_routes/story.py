"""External Case story read; business selection stays behind its use-case port."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from investigation_http.contracts import Severity, StoryPage, StoryQuery
from investigation_http.dependencies import (
    CurrentUser,
    require_permission,
    story_service,
)
from investigation_http.errors import invoke, query_input
from investigation_http.ports import CaseStory

ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
Service = Annotated[CaseStory, Depends(story_service)]
router = APIRouter(prefix="/socai2/cases", tags=["socai2-case-story"])


@router.get("/{case_id}/story", response_model=StoryPage)
async def read_story(request: Request, case_id: UUID, user: ReadUser, service: Service,
    q: Annotated[str | None, Query(max_length=200)] = None,
    severity: Severity | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=2048)] = None):
    if set(request.query_params) - {"q", "severity", "limit", "cursor"} or any(
        len(request.query_params.getlist(key)) != 1 for key in request.query_params):
        raise HTTPException(422, "story_query_parameter_not_supported")
    query = query_input(StoryQuery, q=q, severity=severity, limit=limit, cursor=cursor)
    return await invoke(service.read(user.tenant_id, case_id, query))
