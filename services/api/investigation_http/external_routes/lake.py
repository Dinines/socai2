"""Scoped event reads and complete material lookup; no ingestion or analysis."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime

from investigation_http.adapters.identity import BusinessContext, business_context
from investigation_http.dependencies import lake_read_service
from investigation_http.lake_contracts import (
    LakeErrorResponse,
    LakeMaterial,
    LakeReadError,
    LakeRecordRef,
    LakeSearch,
    LakeSearchHttpResult,
)
from investigation_http.ports import LakeReads

Service = Annotated[LakeReads, Depends(lake_read_service)]
Context = Annotated[BusinessContext, Depends(business_context)]
router = APIRouter(prefix="/socai2/lake/events", tags=["socai2-lake"], responses={
    404: {"model": LakeErrorResponse, "description": "指定版本材料不存在"},
    422: {"model": LakeErrorResponse, "description": "查询参数、范围或游标不符合合同"},
    502: {"model": LakeErrorResponse, "description": "查询明确失败，不能当作查空"},
    503: {"model": LakeErrorResponse, "description": "查询profile或数据源未配置"},
    504: {"model": LakeErrorResponse, "description": "查询执行结果未知，不能当作查空或完整材料"},
})


def check_query(request, allowed):
    if set(request.query_params) - allowed or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params):
        raise HTTPException(422, {"code": "invalid_lake_query_parameters", "state": "failed"})


async def invoke(call):
    try:
        return await call
    except LakeReadError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "state": exc.state}) from None


@router.post("/search", response_model=LakeSearchHttpResult, summary="按来源、时间及可选对象查询湖事件")
async def search(request: Request, body: LakeSearch, user: Context, service: Service):
    """按来源与时间浏览，可指定设备/源端点/目的端点的host或IP；结果带完整材料引用。只读，不启动调查。"""
    check_query(request, set())
    return await invoke(service.search(user.tenant_id, body))


@router.get("/{event_id}/material", response_model=LakeMaterial, summary="读取湖事件版本的完整原文")
async def material(request: Request, event_id: UUID, user: Context, service: Service,
                   source_namespace: Annotated[str, Query(max_length=512)],
                   mapping_version: Annotated[str, Query(max_length=128)],
                   source_version: Annotated[str, Query(max_length=256)],
                   event_time: AwareDatetime, class_uid: Annotated[int, Query(ge=0, le=4294967295)]):
    """使用搜索结果material_url精确读回。正文不截断；旧preview和完整性不明单独标记。"""
    check_query(request, {"source_namespace", "mapping_version", "source_version", "event_time", "class_uid"})
    ref = LakeRecordRef(event_id=event_id, source_namespace=source_namespace, mapping_version=mapping_version,
                        source_version=source_version, event_time=event_time, class_uid=class_uid)
    return await invoke(service.material(user.tenant_id, ref))
