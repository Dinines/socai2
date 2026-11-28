"""External Case allocation, queries and explicit business operations."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime

from investigation_http.case_allocation_contracts import (
    CaseAllocationReceipt,
    CaseMoveReceipt,
    CaseReplacementReceipt,
    RelatedCasePage,
)
from investigation_http.case_info_contracts import CaseInfoSummary
from investigation_http.contracts import (
    ArtifactContent,
    AssessmentHistory,
    AssignmentState,
    AssociationRequest,
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
    RecordPage,
    ResultAdoptionPreview,
    ResultAdoptionReceipt,
    ResultAdoptionRequest,
    Severity,
    SortOrder,
    WorkStatus,
)
from investigation_http.dependencies import CurrentUser, require_permission
from investigation_http.dependencies import case_service as get_service
from investigation_http.errors import (
    actor,
    check_query,
    invoke,
    invoke_record,
    query_input,
)
from investigation_http.ports import CaseOperations
from investigation_http.record_links import comparison_links, directory_links
from investigation_http.run_record_contracts import (
    RecordError,
    RecordValidationError,
    ResultDetailWithComparison,
    RunDetailWithDirectories,
)

ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
WriteUser = Annotated[CurrentUser, Depends(require_permission("cases:write"))]
Service = Annotated[CaseOperations, Depends(get_service)]
router = APIRouter(prefix="/socai2/cases", tags=["socai2-cases"])
ALLOCATION_RESPONSES = {
    404: {"model": RecordError, "description": "案件、所选告警或事件不存在"},
    409: {"model": RecordError, "description": "operation_conflict / scope_conflict / subject_closed / empty_scope，或来源与续建关系不满足要求"},
    422: {"model": RecordError | RecordValidationError, "description": "invalid_input，或请求字段校验detail数组"},
    503: {"model": RecordError, "description": "service_unavailable；保存未确认时沿原operation_key重放"},
}


@router.post("", response_model=CaseAllocationReceipt, status_code=201, responses=ALLOCATION_RESPONSES)
async def create_case(request: Request, body: CaseCreate, user: WriteUser, service: Service):
    """创建并按容量分配，返回各案版本及真实首轮任务；受理不等于调查完成。"""
    check_query(request, set())
    return await invoke_record(service.create_case(user.tenant_id, body, actor=actor(user)))


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


@router.get("/{case_id}/info-summary", response_model=CaseInfoSummary, responses={
    404: {"model": RecordError, "description": "案件不存在"},
    422: {"model": RecordError | RecordValidationError, "description": "请求无效"},
    503: {"model": RecordError, "description": "案件资料摘要读取服务不可用"},
}, summary="读取案件资料摘要")
async def case_info_summary(request: Request, case_id: UUID, user: ReadUser, service: Service):
    check_query(request, set())
    return await invoke_record(service.read_info_summary(user.tenant_id, case_id))


@router.get("/{case_id}/related-cases", response_model=RelatedCasePage, responses={
    404: {"model": RecordError, "description": "case_not_found"},
    409: {"model": RecordError, "description": "cursor_stale：关联集合或顺序变化，重新读取第一页"},
    422: {"model": RecordError | RecordValidationError, "description": "invalid_input / invalid_cursor，或字段校验detail数组"},
    503: {"model": RecordError, "description": "service_unavailable"},
}, summary="查询容量续建及共享事件关联案件")
async def related_cases(
    request: Request, case_id: UUID, user: ReadUser, service: Service,
    limit: Annotated[int | None, Query(ge=1, description="单页条数，省略时采用配置默认值；最大值由同一配置限制。")] = None,
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
):
    """续建组优先、共享事件组其次，同Case去重并保留两种来源；只读，不改变事件接收目标。"""
    check_query(request, {"limit", "cursor"})
    return await invoke_record(service.read_related_cases(user.tenant_id, case_id, limit=limit, cursor=cursor))


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


@router.put("/{case_id}/members", response_model=CaseReplacementReceipt, responses=ALLOCATION_RESPONSES)
async def replace_members(
    request: Request, case_id: UUID, body: MemberChange, user: WriteUser, service: Service
):
    """仅替换指定案件成员；新增按实际接收案分配，空数组只清空本案。"""
    check_query(request, set())
    return await invoke_record(
        service.change_members(user.tenant_id, case_id, body, actor=actor(user))
    )


@router.post("/{case_id}/associations", response_model=CaseAllocationReceipt, responses=ALLOCATION_RESPONSES)
async def associate(
    request: Request, case_id: UUID, body: AssociationRequest, user: WriteUser, service: Service
):
    """关联告警或完整事件，返回本次全部实际分配与接收目标变化。"""
    check_query(request, set())
    return await invoke_record(
        service.associate(user.tenant_id, case_id, body, actor=actor(user))
    )


@router.post("/{case_id}/members/move", response_model=CaseMoveReceipt, responses=ALLOCATION_RESPONSES)
async def move_members(
    request: Request, case_id: UUID, body: MoveMembers, user: WriteUser, service: Service
):
    """原子移出源案并分配至目标串；保留源案版本与各目标实际成员。"""
    check_query(request, set())
    return await invoke_record(
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


@router.get("/{case_id}/runs/{run_id}", response_model=RunDetailWithDirectories)
async def run_detail(case_id: UUID, run_id: UUID, user: ReadUser, service: Service):
    detail = await invoke(service.read_run(user.tenant_id, case_id, run_id))
    return {**detail, **directory_links(run_id),
        **comparison_links(case_id, detail["run"].comparison_context)}


@router.get("/{case_id}/results/{result_id}", response_model=ResultDetailWithComparison)
async def result_detail(
    case_id: UUID, result_id: UUID, user: ReadUser, service: Service
):
    detail = await invoke(service.read_result(user.tenant_id, case_id, result_id))
    return {**detail, **comparison_links(case_id, detail["result"].comparison_context)}


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
