"""External saved-analysis directory; does not submit or execute investigations."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import AwareDatetime

from investigation_http.adapters.identity import BusinessContext, business_context
from investigation_http.contracts import (
    AnalysisIntent,
    DirectoryRunKind,
    RunDirectoryQuery,
    RunState,
    RunSubject,
)
from investigation_http.dependencies import run_directory_service
from investigation_http.errors import check_query, invoke_record, query_input
from investigation_http.ports import RunDirectory
from investigation_http.run_directory_contracts import RunDirectoryPage
from investigation_http.run_record_contracts import RecordError, RecordValidationError

Service = Annotated[RunDirectory, Depends(run_directory_service)]
Context = Annotated[BusinessContext, Depends(business_context)]
router = APIRouter(prefix="/socai2/analysis-runs", tags=["socai2-run-records"], responses={
    422: {"model": RecordError | RecordValidationError, "description": "invalid_input / invalid_cursor，或字段校验detail数组"},
    503: {"model": RecordError, "description": "service_unavailable"},
})


@router.get("", response_model=RunDirectoryPage, summary="统一查询告警、事件和案件的分析记录")
async def directory(request: Request, user: Context, service: Service,
                    subject_type: RunSubject | None = None, subject_id: UUID | None = None,
                    run_kind: DirectoryRunKind | None = None, intent: AnalysisIntent | None = None,
                    state: RunState | None = None,
                    time_from: Annotated[AwareDatetime | None, Query(description="Run requested_at下界，含；须带时区。")] = None,
                    time_to: Annotated[AwareDatetime | None, Query(description="Run requested_at上界，不含；须带时区。")] = None,
                    limit: Annotated[int | None, Query(ge=1, description="单页数量，默认及上限由读取profile配置。")] = None,
                    cursor: Annotated[str | None, Query(max_length=4096, description="上一页next_cursor；保持筛选不变。")] = None):
    """按requested_at、run_id倒序分页。统计针对全部筛选结果；task_id/intent只读真实任务关联，历史无关联为null。

    返回输入成员数量、执行/交付状态及实际结果链接。尚无Run的排队任务不计入；GET不触发调查。
    """
    check_query(request, set(RunDirectoryQuery.model_fields))
    query = query_input(RunDirectoryQuery, subject_type=subject_type, subject_id=subject_id, run_kind=run_kind,
                        intent=intent, state=state, time_from=time_from, time_to=time_to, limit=limit, cursor=cursor)
    return await invoke_record(service.read(user.tenant_id, query))
