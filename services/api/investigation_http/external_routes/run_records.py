"""Complete external record reads, independent of investigation execution."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from investigation_http.adapters.identity import BusinessContext, business_context
from investigation_http.dependencies import run_record_service
from investigation_http.errors import check_query, invoke_record
from investigation_http.ports import RunRecords
from investigation_http.run_record_contracts import (
    RecordError,
    RecordValidationError,
    RunArtifactPage,
    RunStepPage,
    RunStepView,
    StepKind,
)

Service = Annotated[RunRecords, Depends(run_record_service)]
Context = Annotated[BusinessContext, Depends(business_context)]
Limit = Annotated[int | None, Query(ge=1, description="单页数量；省略使用profile默认值，上限由同一profile配置。")]
Cursor = Annotated[str | None, Query(max_length=4096, description="上一页next_cursor；保持Run和筛选条件一致。")]
router = APIRouter(prefix="/socai2/analysis-runs", tags=["socai2-run-records"], responses={
    404: {"model": RecordError, "description": "run_not_found / step_not_found"},
    422: {"model": RecordError | RecordValidationError, "description": "invalid_input / invalid_cursor，或字段校验detail数组"},
    503: {"model": RecordError, "description": "service_unavailable"},
})


@router.get("/{run_id}/steps", response_model=RunStepPage, summary="完整分页读取调查步骤")
async def steps(request: Request, run_id: UUID, user: Context, service: Service,
                limit: Limit = None, cursor: Cursor = None, kind: StepKind | None = None):
    """返回真实步骤、输入/输出/复用原件来源。kind=tool仅列工具步骤；不启动分析或查询工具。"""
    check_query(request, {"limit", "cursor", "kind"})
    return await invoke_record(service.page(user.tenant_id, run_id, "steps", limit=limit, cursor=cursor, kind=kind))


@router.get("/{run_id}/steps/{step_id}", response_model=RunStepView, summary="定位单个调查步骤")
async def step(request: Request, run_id: UUID, step_id: UUID, user: Context, service: Service):
    """按父Run核对步骤归属；包含实际参数、执行状态、错误及原件引用。"""
    check_query(request, set())
    return await invoke_record(service.step(user.tenant_id, run_id, step_id))


@router.get("/{run_id}/artifacts", response_model=RunArtifactPage, summary="完整分页读取调查原件目录")
async def artifacts(request: Request, run_id: UUID, user: Context, service: Service,
                    limit: Limit = None, cursor: Cursor = None, step_id: UUID | None = None):
    """返回元数据及content_url。step_id包括本Run中该步骤产生及引用的原件；跨Run复用沿步骤来源链接读取。"""
    check_query(request, {"limit", "cursor", "step_id"})
    return await invoke_record(service.page(user.tenant_id, run_id, "artifacts", limit=limit, cursor=cursor, step_id=step_id))
