"""Read contracts for A/I analysis; current adoption is distinct from freshness."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from .baseline_contracts import Contract
from .enums import Delivery, DiagnosisState, Disposition, RunState, ScoreState
from .stage_inputs import Freshness


class StageRunView(Contract):
    id: UUID
    kind: Literal["alert_basic", "incident_diagnosis"]
    state: RunState
    requested_at: datetime
    requested_by: UUID | None
    started_at: datetime | None
    ended_at: datetime | None
    executor_version: str | None
    input_artifact_id: UUID | None
    stop_reason: str | None
    delivery_state: Delivery


class TriageView(Contract):
    id: UUID
    input_material_id: UUID | None
    source_run_id: UUID | None
    verdict: Disposition | None
    rationale: str | None
    confidence: float | None
    score_state: ScoreState
    recommendations: list[dict[str, Any]] | None
    producer: str
    actor: dict[str, Any]
    assessed_at: datetime


class DiagnosisView(Contract):
    id: UUID
    source_run_id: UUID
    revision: int
    state: DiagnosisState
    summary: str | None
    diagnosis: dict[str, Any] | None
    open_questions: list[dict[str, Any]] | None
    input_artifact_id: UUID
    source_fingerprint: str
    producer: str
    requested_at: datetime
    generated_at: datetime | None
    error_code: str | None


class ExplanationView(Contract):
    artifact_id: UUID
    available: bool
    reason: str | None
    content: dict[str, Any] | None


class StageEntry(Contract):
    run: StageRunView
    freshness: Freshness
    is_current_pointer: bool
    valid_for_current_input: bool
    result: TriageView | DiagnosisView | None
    explanation: ExplanationView | None
    partial_analysis: ExplanationView | None = None


class StagePage(Contract):
    subject_id: UUID
    kind: Literal["alert_basic", "incident_diagnosis"]
    current_pointer_id: UUID | None
    current: StageEntry | None
    current_unavailable_reason: str | None
    entries: list[StageEntry]
    next_before_run_id: UUID | None


class IncidentInputSelection(Contract):
    policy: Literal["recently_linked"] = Field(description="本轮采用最近归并成员选择策略。")
    limit: int = Field(ge=1, description="执行时配置的单轮成员上限，与历史分页limit无关。")
    order: Literal["linked_at_desc_alert_id_asc"] = Field(description="按归并时间倒序、告警ID升序稳定选择。")
    captured_at: datetime = Field(description="本轮执行前捕获成员范围的时间。")
    total_member_count: int = Field(ge=0, description="捕获时整个事件的成员数量。")
    selected_count: int = Field(ge=0, description="本轮实际选入的成员数量。")
    omitted_count: int = Field(ge=0, description="捕获时未选入本轮的事件成员数量。")
    selected_alert_ids: list[UUID] = Field(description="按选择顺序排列的冻结告警ID。")
    input_artifact_id: UUID = Field(description="记录本轮范围及材料的输入工件ID。")


class IncidentAnalysisCoverage(Contract):
    state: Literal["complete", "partial", "none", "unknown"] = Field(description="相对捕获时整个事件的实际分析覆盖；与Run交付完整性分开。")
    analyzed_count: int | None = Field(ge=0, description="选入成员中已形成分析且非待核成员的数量；未知为null。")
    unresolved_count: int | None = Field(ge=0, description="选入成员中已分析但仍待核的数量；未知为null。")
    not_analyzed_count: int | None = Field(ge=0, description="选入成员中未完成分析的数量，不包含未选入成员；未知为null。")
    covered_alert_ids: list[UUID] | None = Field(description="已分析及待核成员ID的并集；无法确认时为null。")
    limitations: list[str] = Field(description="保存结果或范围对应的覆盖限制。")


class IncidentStageEntry(StageEntry):
    input_selection: IncidentInputSelection | None = Field(default=None, description="该Run保存的选择回执；历史未保存为null。")
    analysis_coverage: IncidentAnalysisCoverage | None = Field(default=None, description="从该Run实际保存的成员分析恢复；历史无选择回执为null。")


class IncidentStagePage(StagePage):
    current: IncidentStageEntry | None = Field(description="当前采用指针对应的事件诊断，仍需单独查看新鲜度与覆盖。")
    entries: list[IncidentStageEntry] = Field(description="事件诊断历史Run，含失败及未知结果。")
