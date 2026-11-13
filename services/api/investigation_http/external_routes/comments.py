"""External Case comment HTTP; persistence is supplied through a use-case port."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from investigation_http.contracts import (
    CaseCommentCreate,
    CaseCommentPage,
    CaseCommentView,
)
from investigation_http.dependencies import (
    CurrentUser,
    comment_service,
    require_permission,
)
from investigation_http.errors import actor, invoke
from investigation_http.ports import CaseComments

ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
WriteUser = Annotated[CurrentUser, Depends(require_permission("cases:write"))]
Service = Annotated[CaseComments, Depends(comment_service)]
router = APIRouter(prefix="/socai2/cases", tags=["socai2-case-comments"])


@router.post("/{case_id}/comments", response_model=CaseCommentView)
async def create_comment(case_id: UUID, body: CaseCommentCreate, user: WriteUser, service: Service):
    return await invoke(service.create(user.tenant_id, case_id, body, actor=actor(user)))


@router.get("/{case_id}/comments", response_model=CaseCommentPage)
async def list_comments(request: Request, case_id: UUID, user: ReadUser, service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0):
    if set(request.query_params) - {"limit", "offset"}:
        raise HTTPException(422, "comment_query_parameter_not_supported")
    return await invoke(service.list(user.tenant_id, case_id, limit=limit, offset=offset))
