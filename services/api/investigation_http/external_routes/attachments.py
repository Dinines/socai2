"""External Case attachment reference HTTP; file storage belongs to the backend."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from investigation_http.contracts import (
    CaseAttachmentCreate,
    CaseAttachmentPage,
    CaseAttachmentView,
)
from investigation_http.dependencies import (
    CurrentUser,
    attachment_service,
    require_permission,
)
from investigation_http.errors import actor, invoke
from investigation_http.ports import CaseAttachments

ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
WriteUser = Annotated[CurrentUser, Depends(require_permission("cases:write"))]
Service = Annotated[CaseAttachments, Depends(attachment_service)]
router = APIRouter(prefix="/socai2/cases", tags=["socai2-case-attachments"])


@router.post("/{case_id}/attachments", response_model=CaseAttachmentView)
async def create_attachment(case_id: UUID, body: CaseAttachmentCreate, user: WriteUser, service: Service):
    return await invoke(service.create(user.tenant_id, case_id, body, actor=actor(user)))


@router.get("/{case_id}/attachments", response_model=CaseAttachmentPage)
async def list_attachments(request: Request, case_id: UUID, user: ReadUser, service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0):
    if set(request.query_params) - {"limit", "offset"}:
        raise HTTPException(422, "attachment_query_parameter_not_supported")
    return await invoke(service.list(user.tenant_id, case_id, limit=limit, offset=offset))


@router.get("/{case_id}/attachments/{attachment_id}", response_model=CaseAttachmentView)
async def read_attachment(request: Request, case_id: UUID, attachment_id: UUID, user: ReadUser, service: Service):
    if request.query_params:
        raise HTTPException(422, "attachment_query_parameter_not_supported")
    return await invoke(service.read(user.tenant_id, case_id, attachment_id))
