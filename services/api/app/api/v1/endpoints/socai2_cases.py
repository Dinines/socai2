"""Opt-in new-schema Case surface; the old /cases routes keep their contract."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.deps import CurrentUser, require_permission
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.socai2.baseline_contracts import Actor, Start
from app.socai2.baseline_store import StoreError
from app.socai2.case_contracts import (
    ArtifactContent,
    AssociationReceipt,
    AssociationRequest,
    BaselinePreparation,
    CaseCreate,
    CaseDetail,
    CaseMetric,
    CaseQueuePage,
    CaseQueueQuery,
    HistoryPage,
    MemberChange,
    MoveMembers,
    MoveReceipt,
    MutationReceipt,
    PrepareBaseline,
    ResultDetail,
    RunDetail,
)
from app.socai2.case_service import CaseService
from app.socai2.enums import AssignmentState, Severity, WorkStatus


def get_service():
    if not settings.SOCAI2_CASE_API_ENABLED:
        raise HTTPException(503, "socai2_case_api_not_enabled")
    return CaseService(AsyncSessionLocal)


ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
WriteUser = Annotated[CurrentUser, Depends(require_permission("cases:write"))]
Service = Annotated[CaseService, Depends(get_service)]
router = APIRouter(prefix="/socai2/cases", tags=["socai2-cases"])


def actor(user):
    if user.workload_service:
        raise HTTPException(403, "case_user_actor_required")
    return Actor(user_id=user.user_id, name=user.email)


async def invoke(call):
    try:
        return await call
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None


@router.post("", response_model=AssociationReceipt)
async def create_case(body: CaseCreate, user: WriteUser, service: Service):
    return await invoke(service.create_case(user.tenant_id, body, actor=actor(user)))


@router.get("", response_model=CaseQueuePage)
async def case_queue(user: ReadUser, service: Service,
                     limit: Annotated[int, Query(ge=1, le=50)] = 20,
                     cursor: Annotated[str | None, Query(max_length=1024)] = None,
                     q: Annotated[str | None, Query(max_length=200)] = None,
                     handling_status: WorkStatus | None = None,
                     severity: Severity | None = None, owner_id: UUID | None = None,
                     assignment_state: AssignmentState | None = None, metric: CaseMetric | None = None):
    query = CaseQueueQuery(limit=limit, cursor=cursor, q=q, handling_status=handling_status,
        severity=severity, owner_id=owner_id, assignment_state=assignment_state, metric=metric)
    return await invoke(service.read_cases(user.tenant_id, query))


@router.get("/{case_id}", response_model=CaseDetail)
async def case_detail(case_id: UUID, user: ReadUser, service: Service):
    return await invoke(service.read_case(user.tenant_id, case_id))


@router.put("/{case_id}/members", response_model=MutationReceipt)
async def replace_members(case_id: UUID, body: MemberChange, user: WriteUser, service: Service):
    return await invoke(service.change_members(user.tenant_id, case_id, body, actor=actor(user)))


@router.post("/{case_id}/associations", response_model=AssociationReceipt)
async def associate(case_id: UUID, body: AssociationRequest, user: WriteUser, service: Service):
    return await invoke(service.associate(user.tenant_id, case_id, body, actor=actor(user)))


@router.post("/{case_id}/members/move", response_model=MoveReceipt)
async def move_members(case_id: UUID, body: MoveMembers, user: WriteUser, service: Service):
    return await invoke(service.move_members(user.tenant_id, case_id, body, actor=actor(user)))


@router.get("/{case_id}/history", response_model=HistoryPage)
async def history(case_id: UUID, user: ReadUser, service: Service,
                  limit: Annotated[int, Query(ge=1, le=100)] = 20,
                  cursor: Annotated[str | None, Query(max_length=512)] = None):
    return await invoke(service.read_history(user.tenant_id, case_id, limit=limit, cursor=cursor))


@router.post("/{case_id}/baseline/prepare", response_model=BaselinePreparation)
async def prepare_baseline(case_id: UUID, body: PrepareBaseline, user: WriteUser, service: Service):
    return await invoke(service.prepare_baseline(user.tenant_id, case_id, body, actor=actor(user)))


@router.get("/{case_id}/runs/{run_id}", response_model=RunDetail)
async def run_detail(case_id: UUID, run_id: UUID, user: ReadUser, service: Service):
    return await invoke(service.read_run(user.tenant_id, case_id, run_id))


@router.post("/{case_id}/runs/{run_id}/start", response_model=RunDetail)
async def start(case_id: UUID, run_id: UUID, body: Start, user: WriteUser, service: Service):
    try:
        return await invoke(service.start_case(user.tenant_id, case_id, run_id, body, actor=actor(user)))
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 -- sanitize the external execution boundary
        # No raw database/provider exception goes into a client response. The
        # Run is the source of truth even if execution or response was lost.
        raise HTTPException(503, {"code": "baseline_execution_unavailable_read_run", "run_id": str(run_id),
            "read_path": f"/api/v1/socai2/cases/{case_id}/runs/{run_id}"}) from None


@router.get("/{case_id}/results/{result_id}", response_model=ResultDetail)
async def result_detail(case_id: UUID, result_id: UUID, user: ReadUser, service: Service):
    return await invoke(service.read_result(user.tenant_id, case_id, result_id))


@router.get("/{case_id}/runs/{run_id}/artifacts/{artifact_id}", response_model=ArtifactContent)
async def artifact_content(case_id: UUID, run_id: UUID, artifact_id: UUID, user: ReadUser, service: Service):
    return await invoke(service.read_artifact(user.tenant_id, case_id, run_id, artifact_id))


@router.get("/{case_id}/runs/{run_id}/materials/{material_id}")
async def frozen_material(case_id: UUID, run_id: UUID, material_id: UUID, user: ReadUser, service: Service):
    return await invoke(service.read_frozen_material(user.tenant_id, case_id, run_id, material_id))
