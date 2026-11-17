"""Persist explicit Incident/Case requests; the shared core schedules execution."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from investigation_http.adapters.identity import BusinessContext, business_context
from investigation_http.analysis_submission_contracts import (
    AnalysisSubmitRequest,
    AnalysisTaskReceipt,
)
from investigation_http.dependencies import analysis_submission_service
from investigation_http.errors import check_query, invoke_record
from investigation_http.ports import AnalysisSubmissions
from investigation_http.run_record_contracts import RecordError, RecordValidationError

Context = Annotated[BusinessContext, Depends(business_context)]
Service = Annotated[AnalysisSubmissions, Depends(analysis_submission_service)]
RESPONSES = {
    404: {"model": RecordError, "description": "subject_not_found"},
    409: {"model": RecordError, "description": "operation_conflict / subject_closed / empty_scope"},
    422: {"model": RecordError | RecordValidationError, "description": "invalid_input，或字段校验detail数组"},
    503: {"model": RecordError, "description": "service_unavailable；同key重放恢复原受理身份"},
}
case_router = APIRouter(prefix="/socai2", responses=RESPONSES)
incident_router = APIRouter(prefix="/socai2", responses=RESPONSES)


@case_router.post("/cases/{case_id}/investigations", response_model=AnalysisTaskReceipt,
             status_code=202, tags=["socai2-cases"], summary="提交案件检查或再次调查")
async def case_investigation(request: Request, case_id: UUID, body: AnalysisSubmitRequest, user: Context, service: Service):
    """保存任务后返回原受理ID及查询地址；202不等于调查已执行。"""
    check_query(request, set())
    return await invoke_record(service.submit(user.tenant_id, "case", case_id, body, actor_id=user.user_id))


@incident_router.post("/incidents/{incident_id}/diagnose", response_model=AnalysisTaskReceipt,
             status_code=202, tags=["socai2-incidents"], summary="提交事件检查或重新诊断")
async def incident_diagnosis(request: Request, incident_id: UUID, body: AnalysisSubmitRequest, user: Context, service: Service):
    """保存任务后返回原受理ID及查询地址；同key同请求回原任务，最新进度读GET。"""
    check_query(request, set())
    return await invoke_record(service.submit(user.tenant_id, "incident", incident_id, body, actor_id=user.user_id))
