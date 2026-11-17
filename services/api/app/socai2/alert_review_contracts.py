"""Read-only alert review candidates; old public alert DTOs remain unchanged."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from .baseline_contracts import Contract
from .exploration_contracts import ExplorationExcludedObject, ExplorationObject
from .page_contracts import AlertFacts

ReviewRule = Literal["same_host_and_tactic", "same_ip", "same_hash_algorithm_and_value"]


class AlertReviewQuery(Contract):
    time_from: AwareDatetime | None = None
    time_to: AwareDatetime | None = None
    limit: int = Field(default=5, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def window(self):
        if (self.time_from is None) != (self.time_to is None):
            raise ValueError("both_window_bounds_required")
        if self.time_from is not None and self.time_to <= self.time_from:
            raise ValueError("window_end_must_follow_start")
        return self


class AlertReviewTactic(Contract):
    label: str = Field(description="双方 detection.tactics 中完全相同的非空原标签；不是已确认的攻击行为。")
    seed_source_paths: list[str] = Field(description="起点材料中的 $.detection.tactics[index] 路径，保留重复标签各位置。")
    candidate_source_paths: list[str] = Field(description="候选材料中的同标签数组路径；材料 ID 见所属 match.candidate.material_id。")


class AlertReviewMatch(Contract):
    rule: ReviewRule = Field(description="同主机且同战术，或同IP，或同明确算法哈希；仅是人工复核依据。")
    seed: ExplorationObject = Field(description="起点当前材料中实际参与匹配的对象。")
    candidate: ExplorationObject = Field(description="候选当前材料中实际参与匹配的对象，保留原件 ID/值/字段路径。")
    shared_tactics: list[AlertReviewTactic] = Field(description="同主机规则必有共同检测战术及双方来源；IP/哈希规则为空数组。")


class AlertReviewCandidate(Contract):
    alert: AlertFacts = Field(description="原告警事实，含名称/严重程度/发生时间及当前处理状态/判定/版本；点击 alert.id 用 E28 打开。")
    matched_rules: list[ReviewRule] = Field(description="该候选满足的去重规则；多规则命中仍只返回一条告警。")
    time_delta_seconds: float | None = Field(description="候选与起点真实发生时间之差的绝对秒数；起点时间未知时 null。")
    matches: list[AlertReviewMatch] = Field(description="全部匹配对象对及具体依据，按双方对象 ID 排序，不将条数当作恶意分数。")
    incident_ids: list[UUID] = Field(description="候选当前所属事件 ID；可由 E29 回查。")
    case_ids: list[UUID] = Field(description="候选当前所属 Case ID；可由 E03 回查，本查询不增删成员。")


class AlertReviewScope(Contract):
    source_alert_id: UUID = Field(description="本次复核起点告警 ID；结果排除它自身。")
    source_material_id: UUID | None = Field(description="实际读取的起点 latest_material_id；没有材料时 null。")
    source_event_time: datetime | None = Field(description="起点真实发生时间，未知为 null，不用入库时间代替。")
    source_namespace: str = Field(description="起点告警来源范围，候选必须完全相同；对象 namespace 另逐对核对。")
    time_from: datetime = Field(description="实际候选事件时间下界，包含。")
    time_to: datetime = Field(description="实际候选事件时间上界，不包含。")
    window_basis: Literal["seed_lookback", "explicit"] = Field(description="默认回看配置30天至起点发生时刻；explicit为调用方明确范围，可包含起点之后的记录。")
    unavailable_rules: list[ReviewRule] = Field(description="起点缺少所需对象或有效战术时列出无法使用的规则；不是查询失败。")
    excluded_objects: list[ExplorationExcludedObject] = Field(description="不支持对象及算法/格式非法hash，不把这些对象当作可匹配线索。")


class AlertReviewPage(Contract):
    items: list[AlertReviewCandidate] = Field(description="按event_time倒序、alert.id倒序的当前页；空数组仅表示该范围无匹配。")
    total: int = Field(ge=0, description="完整时间范围去重后的候选告警数，不受分页影响。")
    next_cursor: str | None = Field(description="相同起点与窗口下一页，null结束；起点材料或范围变化409，坏游标422。")
    scope: AlertReviewScope = Field(description="本次实际起点、时间窗与不可用规则。")
    observed_at: datetime = Field(description="单次只读一致快照的数据库时间；跨请求不冻结候选集合。")


class AlertReviewCursor(Contract):
    fingerprint: str
    event_time: AwareDatetime
    alert_id: UUID
