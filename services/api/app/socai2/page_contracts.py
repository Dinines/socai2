"""Opt-in alert/incident field DTOs; no page mutations or legacy fallback."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from .baseline_contracts import Contract
from .enums import (
    BusinessVerdict,
    AlertStatus,
    AssignmentState,
    Disposition,
    ScoreState,
    Severity,
    TimeSource,
    WorkStatus,
)
from .subject_risk_contracts import SubjectRisk

Subject = Literal["alerts", "incidents"]
Section = Literal["members", "incidents", "objects", "sources", "source_artifacts", "assets", "cases", "comments", "activities", "related_alerts", "responses"]


class SharedFacts(Contract):
    id: UUID
    source_namespace: str
    title: str
    description: str | None
    owner_id: UUID | None
    assignment_state: AssignmentState
    owner_source_value: str | None
    assigned_at: datetime | None
    tags: list[str]
    priority_value: Decimal | None
    priority_state: ScoreState
    priority_source: str | None
    priority_basis: dict[str, Any] | None
    business_updated_at: datetime
    reopened_at: datetime | None
    row_version: int


class AlertFacts(SharedFacts):
    source_alert_id: str | None
    vendor_alert_id: str | None
    connector_id: UUID | None
    connector_type: str | None
    original_vendor: str | None
    category: str | None
    severity: Severity | None
    severity_raw: str | None
    event_time: datetime | None
    event_time_source: TimeSource
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    ingested_at: datetime
    source_updated_at: datetime
    handling_status: AlertStatus
    disposition: Disposition | None
    closed_at: datetime | None
    closed_by: UUID | None
    latest_material_id: UUID | None
    latest_triage_id: UUID | None
    latest_feedback_id: UUID | None
    latest_explanation_id: UUID | None


class IncidentFacts(SharedFacts):
    risk: SubjectRisk | None = Field(default=None, description="已保存的当前等级、初值、每轮意见链接及系统优先级；旧记录为null，不由GET补算，意见不等于已生效。")
    source_incident_id: str
    handling_status: WorkStatus
    severity_override: Severity | None
    severity_override_reason: str | None
    severity_override_at: datetime | None
    severity_override_by: UUID | None
    resolution_note: str | None
    resolved_at: datetime | None
    resolved_by: UUID | None
    created_at: datetime
    latest_diagnosis_id: UUID | None


class TacticCount(Contract):
    label: str
    alert_count: int


class BaselineCounts(Contract):
    running: int
    unknown: int


class DerivedFields(Contract):
    severity_group: Literal["high", "medium", "low"] | None
    false_positive: bool | None = None
    member_count: int | None = None
    first_activity_at: datetime | None = None
    last_activity_at: datetime | None = None
    unknown_event_time_count: int | None = None
    unknown_severity_count: int | None = None
    severity_auto: Severity | None = None
    severity_effective: Severity | None = None
    severity_source: Literal["manual_override", "member_max"] | None = None
    updated_at: datetime | None = None
    tactics: list[TacticCount]
    tactic_counting_note: str
    object_count: int
    baseline_execution_counts: BaselineCounts


class SubjectView(Contract):
    kind: Subject
    facts: AlertFacts | IncidentFacts
    owner_name: str | None
    owner_resolution: Literal["unassigned", "resolved", "unresolved"]
    derived: DerivedFields
    material: dict[str, Any] | None
    triage: dict[str, Any] | None = Field(description="分诊评估。当前有效分诊的 attck_mappings 为已校验映射数组。旧评估、无可用映射或失效分诊为 null。")
    feedback: dict[str, Any] | None
    analysis_url: str
    section_urls: dict[str, str]


class CaseReceiving(Contract):
    active_case_id: UUID | None
    can_receive_automatically: bool
    reason_code: Literal["no_target", "closed", "auto_window_expired"] | None


class IncidentDerivedFields(DerivedFields):
    severity_source: Literal["manual_override", "member_max", "model", "initial_policy", "unknown"] | None = None


class IncidentSubjectView(SubjectView):
    derived: IncidentDerivedFields
    case_receiving: CaseReceiving
    business_verdict: BusinessVerdict | None = Field(default=None, description="Saved model verdict of facts.latest_diagnosis_id, or null.")


class SubjectPage(Contract):
    kind: Subject
    items: list[SubjectView]
    total: int
    next_before_id: UUID | None
    overall_stats: dict[str, int]
    observed_at: datetime
    filtered_total: int = Field(ge=0, description="全部筛选命中数，不受当前页或游标影响；total仍是全租户总数。")
    next_cursor: str | None = Field(description="绑定租户、主体、筛选及排序的下一页游标；null表示末页。")


class IncidentSubjectPage(SubjectPage):
    items: list[IncidentSubjectView]


class RecordPage(Contract):
    items: list[dict[str, Any]]
    total: int
    next_offset: int | None
    observed_at: datetime
    limitations: list[str]


class ContentView(Contract):
    metadata: dict[str, Any]
    availability: str
    content_json: Any = None
    content_text: str | None = None


class TraceView(Contract):
    run: dict[str, Any]
    steps: list[dict[str, Any]]
    steps_total: int
    steps_truncated: bool
    artifacts: list[dict[str, Any]]
    artifacts_total: int
    artifacts_truncated: bool
    usage: dict[str, Any]
    tool_calls: int
    duration_seconds: float | None
    last_recorded_at: datetime
    observed_at: datetime
