"""External Case story read; business selection stays behind its use-case port."""
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from investigation_http.contracts import (
    MemberRelationsQuery,
    RelatedStoryQuery,
    Severity,
    StoryPage,
    StoryQuery,
)
from investigation_http.dependencies import (
    CurrentUser,
    require_permission,
    story_service,
)
from investigation_http.errors import invoke, query_input
from investigation_http.ports import CaseStory
from investigation_http.story_contracts import CaseMemberRelations, RelatedStoryPage

ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
Service = Annotated[CaseStory, Depends(story_service)]
router = APIRouter(prefix="/socai2/cases", tags=["socai2-case-story"])


def check_query(request, model):
    if set(request.query_params) - set(model.model_fields) or any(
        len(request.query_params.getlist(key)) != 1 for key in request.query_params
    ):
        raise HTTPException(422, "story_query_parameter_not_supported")


@router.get("/{case_id}/story", response_model=StoryPage | RelatedStoryPage)
async def read_story(request: Request, case_id: UUID, user: ReadUser, service: Service,
    q: Annotated[str | None, Query(max_length=200)] = None,
    severity: Severity | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
    view: Literal["related"] | None = None,
    focus_alert_id: UUID | None = None):
    model = StoryQuery if view is None else RelatedStoryQuery
    check_query(request, model)
    values = {"q": q, "severity": severity, "limit": limit, "cursor": cursor}
    if view is not None:
        values.update(view=view, focus_alert_id=focus_alert_id)
    query = query_input(model, **values)
    return await invoke(service.read(user.tenant_id, case_id, query))


@router.get("/{case_id}/members/{alert_id}/relations", response_model=CaseMemberRelations)
async def read_member_relations(request: Request, case_id: UUID, alert_id: UUID,
    user: ReadUser, service: Service,
    objects_limit: Annotated[int, Query(ge=1, le=100)] = 20,
    objects_cursor: Annotated[str | None, Query(max_length=2048)] = None,
    runs_limit: Annotated[int, Query(ge=1, le=100)] = 20,
    runs_cursor: Annotated[str | None, Query(max_length=2048)] = None):
    check_query(request, MemberRelationsQuery)
    query = query_input(MemberRelationsQuery, objects_limit=objects_limit, objects_cursor=objects_cursor,
                        runs_limit=runs_limit, runs_cursor=runs_cursor)
    return await invoke(service.read_member_relations(user.tenant_id, case_id, alert_id, query))
