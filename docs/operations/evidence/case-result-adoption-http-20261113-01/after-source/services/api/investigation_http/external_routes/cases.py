"""Opt-in new-schema Case surface; the old /cases routes keep their contract."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime

from investigation_http.contracts import (
    ArtifactContent,
    AssessmentHistory,
    AssignmentState,
    AssociationReceipt,
    AssociationRequest,
    BaselinePreparation,
    CaseCloseRequest,
    CaseCreate,
    CaseDataReceipt,
    CaseDataUpdate,
    CaseDetail,
    CaseLifecycleRequest,
    CaseManagementReceipt,
    CaseManagementUpdate,
    CaseManagementView,
    CaseMetric,
    CasePageData,
    CaseQueuePage,
    CaseQueueQuery,
    CaseSort,
    Classification,
    EvidencePublish,
    HistoryPage,
    MemberChange,
    MoveMembers,
    MoveReceipt,
    MutationReceipt,
    PrepareBaseline,
    RecordPage,
    ResultAdoptionPreview,
    ResultAdoptionReceipt,
    ResultAdoptionRequest,
    ResultDetail,
    RunDetail,
    Severity,
    SortOrder,
    Start,
    WorkStatus,
)
from investigation_http.dependencies import CurrentUser, require_permission
from investigation_http.dependencies import case_service as get_service
from investigation_http.errors import actor, invoke, query_input
from investigation_http.ports import CaseOperations

ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
WriteUser = Annotated[CurrentUser, Depends(require_permission("cases:write"))]
Service = Annotated[CaseOperations, Depends(get_service)]
router = APIRouter(prefix="/socai2/cases", tags=["socai2-cases"])


@router.post("", response_model=AssociationReceipt)
async def create_case(body: CaseCreate, user: WriteUser, service: Service):
    return await invoke(service.create_case(user.tenant_id, body, actor=actor(user)))


@router.get("", response_model=CaseQueuePage)
async def case_queue(
    user: ReadUser,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    handling_status: WorkStatus | None = None,
    severity: Severity | None = None,
    owner_id: UUID | None = None,
    assignment_state: AssignmentState | None = None,
    metric: CaseMetric | None = None,
    classification: Classification | Literal["not_set"] | None = None,
    time_from: AwareDatetime | None = None,
    time_to: AwareDatetime | None = None,
    sort_by: CaseSort | None = None,
    sort_order: SortOrder | None = None,
):
    query = query_input(CaseQueueQuery,
        limit=limit,
        cursor=cursor,
        q=q,
        handling_status=handling_status,
        severity=severity,
        owner_id=owner_id,
        assignment_state=assignment_state,
        metric=metric,
        classification=classification,
        time_from=time_from,
        time_to=time_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await invoke(service.read_cases(user.tenant_id, query))


@router.get("/{case_id}", response_model=CaseDetail)
async def case_detail(case_id: UUID, user: ReadUser, service: Service):
    return await invoke(service.read_case(user.tenant_id, case_id))


@router.patch("/{case_id}/page-data", response_model=CaseDataReceipt)
async def update_page_data(
    case_id: UUID, body: CaseDataUpdate, user: WriteUser, service: Service
):
    return await invoke(
        service.update_page_data(user.tenant_id, case_id, body, actor=actor(user))
    )


@router.get("/{case_id}/page-data", response_model=CasePageData)
async def page_data(case_id: UUID, user: ReadUser, service: Service):
    return await invoke(service.read_page_data(user.tenant_id, case_id))


@router.post("/{case_id}/evidence-index", response_model=CaseDataReceipt)
async def publish_evidence(
    case_id: UUID, body: EvidencePublish, user: WriteUser, service: Service
):
    return await invoke(
        service.publish_evidence(user.tenant_id, case_id, body, actor=actor(user))
    )


@router.put("/{case_id}/members", response_model=MutationReceipt)
async def replace_members(
    case_id: UUID, body: MemberChange, user: WriteUser, service: Service
):
    return await invoke(
        service.change_members(user.tenant_id, case_id, body, actor=actor(user))
    )


@router.post("/{case_id}/associations", response_model=AssociationReceipt)
async def associate(
    case_id: UUID, body: AssociationRequest, user: WriteUser, service: Service
):
    return await invoke(
        service.associate(user.tenant_id, case_id, body, actor=actor(user))
    )


@router.post("/{case_id}/members/move", response_model=MoveReceipt)
async def move_members(
    case_id: UUID, body: MoveMembers, user: WriteUser, service: Service
):
    return await invoke(
        service.move_members(user.tenant_id, case_id, body, actor=actor(user))
    )


@router.get("/{case_id}/history", response_model=HistoryPage)
async def history(
    case_id: UUID,
    user: ReadUser,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
):
    return await invoke(
        service.read_history(user.tenant_id, case_id, limit=limit, cursor=cursor)
    )


@router.post("/{case_id}/baseline/prepare", response_model=BaselinePreparation)
async def prepare_baseline(
    case_id: UUID, body: PrepareBaseline, user: WriteUser, service: Service
):
    return await invoke(
        service.prepare_baseline(user.tenant_id, case_id, body, actor=actor(user))
    )


@router.get("/{case_id}/runs/{run_id}", response_model=RunDetail)
async def run_detail(case_id: UUID, run_id: UUID, user: ReadUser, service: Service):
    return await invoke(service.read_run(user.tenant_id, case_id, run_id))


@router.post("/{case_id}/runs/{run_id}/start", response_model=RunDetail)
async def start(
    case_id: UUID, run_id: UUID, body: Start, user: WriteUser, service: Service
):
    try:
        return await invoke(
            service.start_case(user.tenant_id, case_id, run_id, body, actor=actor(user))
        )
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 -- sanitize the external execution boundary
        # No raw database/provider exception goes into a client response. The
        # Run is the source of truth even if execution or response was lost.
        raise HTTPException(
            503,
            {
                "code": "baseline_execution_unavailable_read_run",
                "run_id": str(run_id),
                "read_path": f"/api/v1/socai2/cases/{case_id}/runs/{run_id}",
            },
        ) from None


@router.get("/{case_id}/results/{result_id}", response_model=ResultDetail)
async def result_detail(
    case_id: UUID, result_id: UUID, user: ReadUser, service: Service
):
    return await invoke(service.read_result(user.tenant_id, case_id, result_id))


@router.get("/{case_id}/results/{result_id}/adoption-preview", response_model=ResultAdoptionPreview,
    summary="Preview adoption of a saved whole-case result")
async def preview_result_adoption(request: Request, case_id: UUID, result_id: UUID,
    user: ReadUser, service: Service):
    if request.query_params:
        raise HTTPException(422, "result_adoption_query_parameter_not_supported")
    return await invoke(service.preview_result_adoption(user.tenant_id, case_id, result_id))


@router.post("/{case_id}/results/{result_id}/adopt", response_model=ResultAdoptionReceipt,
    summary="Explicitly adopt a saved whole-case result",
    responses={404: {"description": "Case or Result not found in this scope"},
        409: {"description": "Preview changed, result ineligible, pending work not acknowledged, or operation conflict"}})
async def adopt_result(case_id: UUID, result_id: UUID, body: ResultAdoptionRequest,
    user: WriteUser, service: Service):
    return await invoke(service.adopt_result(user.tenant_id, case_id, result_id, body, actor=actor(user)))


@router.get("/{case_id}/assessments", response_model=AssessmentHistory,
    summary="Read adopted judgment versions and their saved sources")
async def assessment_history(request: Request, case_id: UUID, user: ReadUser, service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0):
    if set(request.query_params) - {"limit", "offset"}:
        raise HTTPException(422, "assessment_history_query_parameter_not_supported")
    return await invoke(service.read_assessment_history(user.tenant_id, case_id, limit=limit, offset=offset))


@router.get(
    "/{case_id}/runs/{run_id}/artifacts/{artifact_id}", response_model=ArtifactContent
)
async def artifact_content(
    case_id: UUID, run_id: UUID, artifact_id: UUID, user: ReadUser, service: Service
):
    return await invoke(
        service.read_artifact(user.tenant_id, case_id, run_id, artifact_id)
    )


@router.get("/{case_id}/artifacts/{artifact_id}", response_model=ArtifactContent)
async def case_source_artifact(
    case_id: UUID, artifact_id: UUID, user: ReadUser, service: Service
):
    return await invoke(
        service.read_artifact(user.tenant_id, case_id, None, artifact_id)
    )


@router.get("/{case_id}/activities", response_model=RecordPage)
async def case_activities(
    case_id: UUID,
    user: ReadUser,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    return await invoke(
        service.read_activities(user.tenant_id, case_id, limit=limit, offset=offset)
    )


@router.get("/{case_id}/runs/{run_id}/materials/{material_id}")
async def frozen_material(
    case_id: UUID, run_id: UUID, material_id: UUID, user: ReadUser, service: Service
):
    return await invoke(
        service.read_frozen_material(user.tenant_id, case_id, run_id, material_id)
    )


@router.get("/{case_id}/management", response_model=CaseManagementView)
async def management(case_id: UUID, user: ReadUser, service: Service):
    return await invoke(service.read_management(user.tenant_id, case_id))


@router.patch("/{case_id}/management", response_model=CaseManagementReceipt)
async def update_management(
    case_id: UUID, body: CaseManagementUpdate, user: WriteUser, service: Service
):
    return await invoke(
        service.manage_case(
            user.tenant_id, case_id, body, actor(user), action="case_management_updated"
        )
    )


@router.post("/{case_id}/close", response_model=CaseManagementReceipt)
async def close_case(
    case_id: UUID, body: CaseCloseRequest, user: WriteUser, service: Service
):
    return await invoke(
        service.manage_case(
            user.tenant_id, case_id, body, actor(user), action="case_closed"
        )
    )


@router.post("/{case_id}/reopen", response_model=CaseManagementReceipt)
async def reopen_case(
    case_id: UUID, body: CaseLifecycleRequest, user: WriteUser, service: Service
):
    return await invoke(
        service.manage_case(
            user.tenant_id, case_id, body, actor(user), action="case_reopened"
        )
    )
