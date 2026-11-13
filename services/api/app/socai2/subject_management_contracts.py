"""Additive management requests; existing alert/incident read DTOs are reused."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

from .baseline_contracts import Contract
from .enums import Disposition, Severity
from .page_contracts import AlertFacts, IncidentFacts

Reason = Annotated[str, Field(min_length=1, max_length=20000)]
Tag = Annotated[str, Field(min_length=1, max_length=128)]


class Operation(Contract):
    operation_key: UUID = Field(description="本次明确操作的幂等键；同内容重试沿用，不同意图换键。")


class VersionedOperation(Operation):
    expected_row_version: int = Field(ge=1, description="当前详情facts.row_version；过期409。")


class SelectedSubject(Contract):
    id: UUID = Field(description="用户明确选中的告警或事件ID。")
    expected_row_version: int = Field(ge=1, description="该对象当前facts.row_version。")


class Selection(Operation):
    items: list[SelectedSubject] = Field(min_length=1, description="明确选择及各自版本；不允许重复ID，数量上限由服务配置。整批成功或拒绝。")

    @field_validator("items")
    @classmethod
    def distinct_ids(cls, value):
        if len({item.id for item in value}) != len(value):
            raise ValueError("duplicate subject ids")
        return value


class FeedbackFields(Contract):
    disposition: Disposition = Field(description="人工判定；false_positive/benign关闭，已关闭改true_positive/needs_review恢复处理中。")
    reason: Reason = Field(description="人工判断的理由；原文保存，不替换模型分诊。")

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value):
        if not value.strip():
            raise ValueError("reason must not be blank")
        return value


class AlertFeedback(FeedbackFields, VersionedOperation):
    pass


class AlertFeedbackBatch(Selection):
    feedback: FeedbackFields = Field(description="应用于全部明确选中告警的人工判定及理由。")


class ManagementFields(Contract):
    owner_id: UUID | None = Field(default=None, description="同租户已有人员ID；省略保持，null取消分配。")
    tags: list[Tag] | SkipJsonSchema[None] = Field(default=None, max_length=50,
        description="完整标签集合；省略保持，[]清空，不接受null或重复／空白标签。",
        json_schema_extra=lambda s: s.pop('default', None))
    reason: Reason | None = Field(default=None, description="人工状态变更理由；关闭告警必填，保存在活动中。")

    @field_validator("tags", mode="before")
    @classmethod
    def tags_not_null(cls, value):
        if value is None:
            raise ValueError("omit tags to keep them; use [] to clear")
        return value

    @field_validator("reason", check_fields=False)
    @classmethod
    def reason_not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("reason must not be blank")
        return value

    @model_validator(mode="after")
    def actual_change_fields(self):
        fields = self.model_fields_set - {"operation_key", "expected_row_version", "reason",
                                        "resolution_note", "severity_override_reason"}
        if not fields:
            raise ValueError("at least one management field required")
        if self.tags is not None and (any(not t.strip() for t in self.tags) or len(set(self.tags)) != len(self.tags)):
            raise ValueError("tags must be nonblank and unique")
        return self

    @field_validator("handling_status", mode="before", check_fields=False)
    @classmethod
    def state_not_null(cls, value):
        if value is None:
            raise ValueError("handling_status cannot be null")
        return value


class AlertManagementFields(ManagementFields):
    handling_status: Literal["new", "in_progress", "completed"] | SkipJsonSchema[None] = Field(default=None,
        description="人工处理状态；completed须reason；仅分配不改状态，重开不改原判定。",
        json_schema_extra=lambda s: s.pop('default', None))


class IncidentManagementFields(ManagementFields):
    handling_status: Literal["new", "in_progress", "resolved"] | SkipJsonSchema[None] = Field(default=None,
        description="人工处理状态；解决须resolution_note；分配默认推进未解决事件，已解决仅换负责人不重开。",
        json_schema_extra=lambda s: s.pop('default', None))
    severity_override: Severity | None = Field(default=None, description="人工等级覆盖；省略保持，null恢复按成员自动等级。")
    severity_override_reason: Reason | None = Field(default=None, description="设置人工等级覆盖必填理由；须与severity_override一起提交。")
    resolution_note: Reason | None = Field(default=None, description="将事件改为resolved必填；须与handling_status=resolved一起提交。")

    @field_validator("severity_override_reason", "resolution_note")
    @classmethod
    def notes_not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("note must not be blank")
        return value

    @model_validator(mode="after")
    def associated_notes(self):
        if "severity_override_reason" in self.model_fields_set and "severity_override" not in self.model_fields_set:
            raise ValueError("severity_override_reason requires severity_override")
        if self.severity_override is not None and not self.severity_override_reason:
            raise ValueError("severity override requires a reason")
        if self.severity_override is None and self.severity_override_reason is not None:
            raise ValueError("clearing override cannot include an override reason")
        if self.resolution_note is not None and self.handling_status != "resolved":
            raise ValueError("resolution_note requires resolved status")
        if self.handling_status == "resolved" and not self.resolution_note:
            raise ValueError("resolved requires resolution_note")
        return self


class AlertManagementUpdate(AlertManagementFields, VersionedOperation):
    pass


class IncidentManagementUpdate(IncidentManagementFields, VersionedOperation):
    pass


class AlertManagementBatch(Selection):
    changes: AlertManagementFields = Field(description="应用于所选告警的局部修改。")


class IncidentManagementBatch(Selection):
    changes: IncidentManagementFields = Field(description="应用于所选事件的局部修改。")


class SubjectMutationReceipt(Contract):
    kind: Literal["alerts", "incidents"] = Field(description="操作的主体种类。")
    facts: AlertFacts | IncidentFacts = Field(description="提交时保存的主体事实快照；沿用原详情facts字段。重放返回原快照，最新值另GET。")
    changed: bool = Field(description="本次是否产生主体变化；新增人工反馈为true。")
    feedback_id: UUID | None = Field(description="本次新建人工反馈ID；管理操作为null。")
    activity_id: UUID = Field(description="本次活动ID；在该主体records/activities中读取。")


class SubjectBatchReceipt(Operation):
    items: list[SubjectMutationReceipt] = Field(description="按主体UUID排序的逐项保存结果。")
    changed_count: int = Field(ge=0, description="本批changed=true的对象数；不是任务或模型执行数。")
