"""Manual Case management; existing Case field meanings remain unchanged."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

from .baseline_contracts import Contract
from .case_contracts import CaseView
from .enums import Severity


class CaseManagementUpdate(Contract):
    operation_key: UUID = Field(description="一次逻辑修改的幂等键；同意图重试沿用原值。")
    expected_row_version: int = Field(ge=1, description="从当前Case读取的行版本；过期返回409。")
    title: str | SkipJsonSchema[None] = Field(default=None, min_length=1, max_length=200,
        description="案件名称；省略保持，不接受null或空白。", json_schema_extra=lambda s: s.pop('default', None))
    description: str | None = Field(default=None, max_length=20000, description="案件说明；省略保持，null清空。")
    owner_id: UUID | None = Field(default=None, description="同租户已有用户ID；省略保持，null取消分配；不自动改处理状态。")
    severity: Severity | None = Field(default=None, description="人工严重程度；省略保持，null清空；不改变成员告警等级。")
    tags: list[Annotated[str, Field(min_length=1, max_length=128)]] | SkipJsonSchema[None] = Field(default=None, max_length=50,
        description="完整标签集合；省略保持，[]清空，不接受null、空白或重复标签。", json_schema_extra=lambda s: s.pop('default', None))
    handling_status: Literal["new", "in_progress"] | SkipJsonSchema[None] = Field(default=None,
        description="未结案案件的人工处理状态；省略保持，结案和重开使用各自接口。", json_schema_extra=lambda s: s.pop('default', None))

    @field_validator("title", "tags", "handling_status", mode="before")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("field cannot be null; omit to keep the current value")
        return value

    @model_validator(mode="after")
    def explicit_fields(self):
        fields = self.model_fields_set - {"operation_key", "expected_row_version"}
        if not fields:
            raise ValueError("at least one management field required")
        for name in fields & {"title", "tags", "handling_status"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        if self.title is not None and not self.title.strip():
            raise ValueError("title must not be blank")
        if self.tags is not None and (any(not t.strip() for t in self.tags) or len(set(self.tags)) != len(self.tags)):
            raise ValueError("tags must be nonblank and unique")
        return self


class CaseLifecycleRequest(Contract):
    operation_key: UUID = Field(description="本次结案或重开的幂等键。")
    expected_row_version: int = Field(ge=1, description="当前Case行版本；发生变化后需重新读取。")
    reason: str | None = Field(default=None, min_length=1, max_length=20000,
        description="人工理由，保存到活动；有未完任务时结案必填，其他情况可省略，不接受空白。")

    @field_validator("reason")
    @classmethod
    def reason_nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("reason must not be blank")
        return value


class CaseCloseRequest(CaseLifecycleRequest):
    acknowledge_open_tasks: bool = Field(default=False, description="是否已确认当前未完人工任务；有未完任务时须true并填写reason，任务不会被取消。")


class CaseBlockingRun(Contract):
    id: UUID = Field(description="阻止结案的本案Run ID。")
    state: Literal["running", "unknown"] = Field(description="running正在执行；unknown执行结果未明确，两者均阻止结案。")


class CaseManagementView(Contract):
    case: CaseView = Field(description="当前已保存的Case管理字段和行版本，与Case详情一致。")
    open_task_count: int = Field(ge=0, description="当前修订为not_started/in_progress的人工任务数；历史版本不重复计数。")
    blocking_runs: list[CaseBlockingRun] = Field(description="本案running/unknown Run；空列表表示没有执行状态阻塞，不表示没有待办。")
    can_close: bool = Field(description="案件未结案且无阻塞Run；如requires_open_task_confirmation为true仍须确认及理由。")
    can_reopen: bool = Field(description="当前案件是否已解决，可由人显式重开。")
    requires_open_task_confirmation: bool = Field(description="未结案且存在未完人工任务；关闭请求须确认并提供理由。")


class CaseManagementReceipt(Contract):
    case: CaseView = Field(description="本次操作保存后的Case快照；幂等重放返回原回执，新状态请重新GET。")
    changed: bool = Field(description="是否实际改变Case字段；false不增加行版本，幂等重放保留原回执。")
