"""The transport boundary translates existing application errors exactly once."""

from fastapi import HTTPException
from pydantic import ValidationError

from investigation_http.contracts import Actor, StoreError


def query_input(model, **values):
    try:
        return model(**values)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_context=False, include_url=False, include_input=False)) from None


def check_query(request, allowed):
    if set(request.query_params) - allowed or any(
        len(request.query_params.getlist(key)) != 1 for key in request.query_params
    ):
        raise record_error("invalid_input", 422)


def actor(user):
    if user.workload_service:
        raise HTTPException(403, "case_user_actor_required")
    return Actor(user_id=user.user_id, name=user.email)


async def invoke(call):
    try:
        return await call
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None


def provide(factory, *args):
    try:
        return factory(*args)
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None


def record_error(code, status):
    messages = {"run_not_found": "调查记录不存在", "step_not_found": "该调查中没有此步骤",
                "subject_not_found": "业务对象不存在", "analysis_task_not_found": "该对象下的分析任务不存在",
                "operation_conflict": "同一操作编号已用于不同请求", "subject_closed": "业务对象已关闭",
                "empty_scope": "业务对象没有可分析成员",
                "invalid_cursor": "分页游标无效或不属于当前查询", "invalid_input": "查询参数不符合约定",
                "service_unavailable": "调查记录读取服务不可用"}
    return HTTPException(status, {"code": code, "message": messages.get(code, code), "context": {}})


async def invoke_record(call):
    try:
        return await call
    except StoreError as exc:
        raise record_error(exc.code, exc.status) from None
