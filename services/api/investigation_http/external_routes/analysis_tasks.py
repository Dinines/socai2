"""Read analysis tasks under their business subjects; not human-task management."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from investigation_http.adapters.identity import BusinessContext, business_context
from investigation_http.analysis_task_contracts import (
    AnalysisTaskDetail,
    AnalysisTaskPage,
)
from investigation_http.dependencies import analysis_task_service
from investigation_http.errors import check_query, invoke_record
from investigation_http.ports import AnalysisTaskReads
from investigation_http.run_record_contracts import RecordError, RecordValidationError

Service = Annotated[AnalysisTaskReads, Depends(analysis_task_service)]
Context = Annotated[BusinessContext, Depends(business_context)]
router = APIRouter(responses={
    404: {"model": RecordError, "description": "subject_not_found / analysis_task_not_found"},
    422: {"model": RecordError | RecordValidationError, "description": "invalid_input / invalid_cursor，或字段校验detail数组"},
    503: {"model": RecordError, "description": "service_unavailable"},
})


def subject_routes(kind, label):
    scoped = APIRouter(prefix=f"/socai2/{kind}s/{{subject_id}}/analysis-tasks", tags=[f"socai2-{kind}s"])

    @scoped.get("", response_model=AnalysisTaskPage, summary=f"读取{label}分析任务列表")
    async def task_list(request: Request, subject_id: UUID, user: Context, service: Service,
                        limit: Annotated[int | None, Query(ge=1, description="单页数量，默认/上限由显式任务policy配置。")] = None,
                        cursor: Annotated[str | None, Query(max_length=4096, description="上一页next_cursor，不可跨主体使用。")] = None):
        """包括尚未产生Run的已受理任务；按提交时间倒序，total为全部任务数。GET不受理或启动分析。"""
        check_query(request, {"limit", "cursor"})
        return await invoke_record(service.page(user.tenant_id, kind, subject_id, limit=limit, cursor=cursor))

    @scoped.get("/{task_id}", response_model=AnalysisTaskDetail, summary=f"读取{label}分析任务详情")
    async def task_detail(request: Request, subject_id: UUID, task_id: UUID, user: Context, service: Service):
        """返回原任务状态、实际尝试和结果URL；无Run时不伪造Run，合并任务仍用原ID查询。"""
        check_query(request, set())
        return await invoke_record(service.detail(user.tenant_id, kind, subject_id, task_id))

    return scoped


for kind, label in (("alert", "告警"), ("incident", "事件"), ("case", "案件")):
    router.include_router(subject_routes(kind, label))
