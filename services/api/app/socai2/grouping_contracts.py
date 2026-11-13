"""Input and result for the incident queue summary, independent of transport."""
from datetime import UTC, datetime
from typing import Literal

from pydantic import AwareDatetime, Field, field_validator, model_validator

from .baseline_contracts import Contract


class GroupingQuery(Contract):
    source_namespace: str | None = Field(default=None, min_length=1, max_length=256,
        description="告警来源命名空间，精确匹配且区分大小写；省略表示当前租户全部来源。")
    time_from: AwareDatetime | None = Field(default=None, description="告警event_time起点，包含；须带时区。")
    time_to: AwareDatetime | None = Field(default=None, description="告警event_time终点，不包含；须带时区。")

    @field_validator("source_namespace")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("source_namespace_must_not_be_blank")
        return value

    @field_validator("time_from", "time_to")
    @classmethod
    def utc(cls, value):
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def ordered_window(self):
        if self.time_from is not None and self.time_to is not None and self.time_from >= self.time_to:
            raise ValueError("time_from_must_precede_time_to")
        return self


class GroupingSummary(Contract):
    schema_version: Literal["socai2.incident-grouping.v1"] = "socai2.incident-grouping.v1"
    scope: GroupingQuery = Field(description="实际采用的告警来源和UTC发生时间条件；不是事件表格筛选。")
    alert_count: int = Field(ge=0, description="范围内不同告警数；包括已归并和未归并告警。")
    grouped_alert_count: int = Field(ge=0, description="范围内当前关联事件的不同告警数。")
    ungrouped_alert_count: int = Field(ge=0, description="范围内未关联事件的告警数；等于alert_count-grouped_alert_count。")
    incident_count: int = Field(ge=0, description="范围内已归并告警关联的不同事件数；无范围内成员的事件不计。")
    in_progress_incident_count: int = Field(ge=0, description="上述事件中handling_status=in_progress的数量；不看Run或Case状态。")
    compression_rate: float | None = Field(ge=0, le=1,
        description="(grouped_alert_count-incident_count)/grouped_alert_count；0..1，乘100为百分比。无已归并告警时null；不包含未归并告警，不代表正确率或解决率。")
    observed_at: datetime = Field(description="本次REPEATABLE READ只读快照的观察时间。")
