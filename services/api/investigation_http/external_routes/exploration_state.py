"""External browsing save/restore, separate from internal investigation execution."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from investigation_http.contracts import (
    ExplorationBase,
    ExplorationSave,
    ExplorationSaved,
    ExplorationSnapshot,
)
from investigation_http.dependencies import (
    CurrentUser,
    exploration_state_service,
    require_permission,
)
from investigation_http.errors import actor, invoke
from investigation_http.ports import CaseExplorationState

router = APIRouter(prefix="/socai2/cases", tags=["socai2-case-exploration"])
ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
WriteUser = Annotated[CurrentUser, Depends(require_permission("cases:write"))]
Service = Annotated[CaseExplorationState, Depends(exploration_state_service)]


def query_only(request, allowed=()):
    if set(request.query_params) - set(allowed) or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params):
        raise HTTPException(422, "exploration_query_parameter_not_supported")


@router.get("/{case_id}/exploration-base", response_model=ExplorationBase)
async def read_base(request: Request, case_id: UUID, user: ReadUser, service: Service, run_id: UUID | None = None):
    query_only(request, {"run_id"})
    return await invoke(service.read_base(user.tenant_id, case_id, run_id))


@router.put("/{case_id}/exploration", response_model=ExplorationSnapshot)
async def save(request: Request, case_id: UUID, body: ExplorationSave, user: WriteUser, service: Service):
    query_only(request)
    return await invoke(service.save(user.tenant_id, case_id, body, actor=actor(user)))


@router.get("/{case_id}/exploration", response_model=ExplorationSaved)
async def read(request: Request, case_id: UUID, user: ReadUser, service: Service):
    query_only(request)
    return await invoke(service.read(user.tenant_id, case_id))
