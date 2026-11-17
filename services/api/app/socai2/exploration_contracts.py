"""Typed read-only exploration requests and source-backed candidate responses."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from .baseline_contracts import Contract
from .page_contracts import AlertFacts


class ExplorationQuery(Contract):
    alert_id: UUID | None = None
    object_id: UUID | None = None
    time_from: AwareDatetime | None = None
    time_to: AwareDatetime | None = None
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def complete_selection(self):
        if self.alert_id and self.object_id:
            raise ValueError("choose_alert_or_object")
        if (self.time_from is None) != (self.time_to is None):
            raise ValueError("both_window_bounds_required")
        if self.time_from is not None and self.time_to <= self.time_from:
            raise ValueError("window_end_must_follow_start")
        return self


class ExplorationObject(Contract):
    id: UUID = Field(description="alert_objects原对象ID，可作为下一次object_id；不是图内部节点ID。")
    alert_id: UUID
    material_id: UUID = Field(description="匹配时的最新材料ID；E31按此版本回查原文。")
    object_type: str
    namespace: str = Field(description="原对象身份范围；本次双方必须完全相同，不表示统一资产身份。")
    object_key: str = Field(description="原对象键，未改写。")
    raw_value: str = Field(description="收到的原对象值。")
    normalized_value: str = Field(description="原存储值；普通类型按此值精确比较，不追加模糊或别名归并。")
    source_path: str = Field(description="对应材料中实际来源字段路径。")
    algorithm: str | None = Field(default=None, description="hash的明确算法按MD5/SHA1/SHA256/SHA512规范显示；其他类型null。原属性在原对象/材料读取。")


class ExplorationMatch(Contract):
    basis: Literal["same_source_value", "same_hash_algorithm_and_value"] = Field(description="前者为同来源同类型值，后者还核对明确哈希算法和格式；均不证明攻击因果。")
    seed: ExplorationObject = Field(description="起点中的实际对象记录。")
    candidate: ExplorationObject = Field(description="候选告警中的实际匹配对象记录。")


class ExplorationExcludedObject(Contract):
    object_id: UUID
    reason: Literal["unsupported_object_type", "hash_algorithm_or_value_invalid"]


class ExplorationScope(Contract):
    seed_kind: Literal["case", "alert", "object"]
    seed_alert_ids: list[UUID] = Field(description="本次实际查询起点告警；候选不重复返回这些告警。")
    source_namespace: str | None = Field(description="Case绑定的告警来源范围，候选必须相同。")
    case_scope_revision: int
    time_from: datetime | None = Field(description="实际事件时间起点，包含；无起点且未指定窗口时null。")
    time_to: datetime | None = Field(description="实际事件时间终点，不包含；无起点且未指定窗口时null。")
    window_basis: Literal["explicit", "seed_event_times", "no_seeds"]
    excluded_objects: list[ExplorationExcludedObject] = Field(description="多对象起点中未参与查询的对象和原因；不悄悄当作无关联。")


class ExplorationCandidate(Contract):
    alert: AlertFacts = Field(description="原告警事实DTO；E28按alert.id回查。")
    shared_object_count: int = Field(ge=1, description="去重后的共享对象数，重复来源路径不重复计数。")
    time_delta_seconds: float | None = Field(default=None, ge=0, description="候选距任一匹配起点告警已知event_time的最短秒数；起点时间全未知为null。")
    already_in_case: bool = Field(description="该告警当前是否已为本案正式成员；展开/预览不会加入。")
    case_ids: list[UUID] = Field(description="该告警当前所属Case ID，保留其他案件归属。")
    incident_ids: list[UUID] = Field(description="该告警当前所属事件ID。")
    matches: list[ExplorationMatch] = Field(description="所有匹配对象对及原始材料依据；按对象ID稳定排序。")


class ExplorationPage(Contract):
    items: list[ExplorationCandidate]
    total: int = Field(ge=0, description="整个查询范围命中告警数；SQL先去重统计再分页。")
    next_cursor: str | None = Field(description="相同查询下一页；null结束。起点或范围变化409，需重新查询。")
    scope: ExplorationScope
    observed_at: datetime = Field(description="本请求同一只读数据库快照的观察时间；不保证跨请求快照不变。")


class ExplorationCursor(Contract):
    fingerprint: str
    shared: int = Field(ge=1)
    delta: float | None = Field(default=None, ge=0)
    alert_id: UUID
