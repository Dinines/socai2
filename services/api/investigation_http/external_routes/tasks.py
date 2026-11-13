"""Opt-in human task surface, separate from machine execution."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from investigation_http.contracts import (
    TaskCreate,
    TaskEdit,
    TaskMutation,
    TaskPage,
    TaskRevisionPage,
    TaskRevisionView,
    TaskView,
)
from investigation_http.dependencies import CurrentUser, require_permission
from investigation_http.dependencies import task_service as get_service
from investigation_http.errors import actor, invoke
from investigation_http.ports import TaskOperations

ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
WriteUser = Annotated[CurrentUser, Depends(require_permission("cases:write"))]
Service = Annotated[TaskOperations, Depends(get_service)]
router = APIRouter(prefix="/socai2/cases/{case_id}/tasks", tags=["socai2-human-tasks"])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=100000)]


@router.post("", response_model=TaskMutation)
async def create(case_id: UUID, body: TaskCreate, user: WriteUser, service: Service):
    return await invoke(service.write(user.tenant_id, case_id, body, actor=actor(user)))


@router.put("/{task_id}", response_model=TaskMutation)
async def edit(
    case_id: UUID, task_id: UUID, body: TaskEdit, user: WriteUser, service: Service
):
    return await invoke(
        service.write(user.tenant_id, case_id, body, actor=actor(user), task_id=task_id)
    )


@router.get("", response_model=TaskPage)
async def listing(
    case_id: UUID,
    user: ReadUser,
    service: Service,
    limit: Limit = 20,
    offset: Offset = 0,
):
    return await invoke(
        service.list(user.tenant_id, case_id, limit=limit, offset=offset)
    )


@router.get("/{task_id}", response_model=TaskView)
async def detail(case_id: UUID, task_id: UUID, user: ReadUser, service: Service):
    return await invoke(service.read(user.tenant_id, case_id, task_id))


@router.get("/{task_id}/revisions", response_model=TaskRevisionPage)
async def revisions(
    case_id: UUID,
    task_id: UUID,
    user: ReadUser,
    service: Service,
    limit: Limit = 20,
    offset: Offset = 0,
):
    return await invoke(
        service.revisions(user.tenant_id, case_id, task_id, limit=limit, offset=offset)
    )


@router.get("/{task_id}/revisions/{revision_id}", response_model=TaskRevisionView)
async def revision(
    case_id: UUID, task_id: UUID, revision_id: UUID, user: ReadUser, service: Service
):
    return await invoke(
        service.read_revision(user.tenant_id, case_id, task_id, revision_id)
    )
