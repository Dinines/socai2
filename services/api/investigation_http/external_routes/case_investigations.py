"""Read the Case investigation directory and resolve a fixed Run."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from investigation_http.case_investigation_contracts import (
    CaseInvestigationLookup,
    CaseInvestigationPage,
)
from investigation_http.dependencies import (
    CurrentUser,
    case_investigation_history_service,
    require_permission,
)
from investigation_http.errors import check_query, invoke_record
from investigation_http.ports import CaseInvestigationHistory
from investigation_http.run_record_contracts import RecordError, RecordValidationError

ReadUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
Service = Annotated[CaseInvestigationHistory, Depends(case_investigation_history_service)]
router = APIRouter(prefix="/socai2/cases", tags=["socai2-case-investigations"], responses={
    404: {"model": RecordError, "description": "案件或案内调查记录不存在"},
    422: {"model": RecordError | RecordValidationError, "description": "查询参数或游标无效"},
    503: {"model": RecordError, "description": "调查记录读取服务不可用"},
})


@router.get("/{case_id}/investigations", response_model=CaseInvestigationPage, summary="读取案件调查历史目录")
async def read_case_investigations(
    request: Request,
    case_id: UUID,
    user: ReadUser,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
):
    check_query(request, {"limit", "cursor"})
    return await invoke_record(service.read(user.tenant_id, case_id, limit=limit, cursor=cursor))


@router.get("/{case_id}/investigations/{run_id}", response_model=CaseInvestigationLookup, summary="定位案内指定调查轮次")
async def lookup_case_investigation(
    request: Request, case_id: UUID, run_id: UUID, user: ReadUser, service: Service,
):
    check_query(request, set())
    return await invoke_record(service.lookup(user.tenant_id, case_id, run_id))
