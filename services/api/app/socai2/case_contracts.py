"""New Case API contracts; persisted lifecycle and conclusion are distinct."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator, model_validator

from .baseline_contracts import Contract, Finding, Impact, Question, Recommendation
from .case_data_contracts import Classification, CasePageData
from .enums import (
    AssignmentState,
    ChangeKind,
    ConclusionState,
    Delivery,
    Origin,
    ResultKind,
    RunKind,
    RunState,
    RunTrigger,
    ScoreState,
    Severity,
    Validation,
    WorkStatus,
)

Label = Annotated[str, Field(min_length=1, max_length=200)]


class MemberChange(Contract):
    operation_key: UUID
    expected_scope_revision: int = Field(ge=0)
    alert_ids: list[UUID] = Field(max_length=200)

    @field_validator("alert_ids")
    @classmethod
    def unique_members(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("duplicate member")
        return values


class CaseCreate(Contract):
    operation_key: UUID
    title: Label
    description: str | None = Field(default=None, max_length=20000)
    severity: Severity | None = None
    tags: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(default_factory=list, max_length=50)
    alert_ids: list[UUID] = Field(default_factory=list, max_length=200)
    incident_ids: list[UUID] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def selection_required(self):
        if not self.alert_ids and not self.incident_ids:
            raise ValueError("alert or incident selection required")
        return self

    @field_validator("title")
    @classmethod
    def title_nonblank(cls, value):
        if not value.strip():
            raise ValueError("blank title")
        return value

    @field_validator("alert_ids", "incident_ids", "tags")
    @classmethod
    def unique_values(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("duplicate value")
        return values


class MutationReceipt(Contract):
    case_id: UUID
    scope_revision: int
    pending_run_id: UUID | None
    changed: bool


class PrepareBaseline(Contract):
    operation_key: UUID
    expected_scope_revision: int = Field(ge=0)


class BaselinePreparation(Contract):
    case_id: UUID
    scope_revision: int
    pending_run_id: UUID
    created: bool


class AssociationRequest(Contract):
    operation_key: UUID
    expected_scope_revision: int = Field(ge=0)
    alert_ids: list[UUID] = Field(default_factory=list, max_length=200)
    incident_ids: list[UUID] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def valid_selection(self):
        if not self.alert_ids and not self.incident_ids:
            raise ValueError("alert or incident selection required")
        if len(set(self.alert_ids)) != len(self.alert_ids) or len(set(self.incident_ids)) != len(self.incident_ids):
            raise ValueError("duplicate selection")
        return self


class AssociationReceipt(MutationReceipt):
    added_alert_ids: list[UUID] = Field(default_factory=list)
    linked_incident_ids: list[UUID] = Field(default_factory=list)


class MoveMembers(Contract):
    operation_key: UUID
    target_case_id: UUID
    expected_source_scope_revision: int = Field(ge=0)
    expected_target_scope_revision: int = Field(ge=0)
    alert_ids: list[UUID] = Field(min_length=1, max_length=200)

    @field_validator("alert_ids")
    @classmethod
    def unique_members(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("duplicate member")
        return values


class MoveReceipt(Contract):
    source: MutationReceipt
    target: MutationReceipt
    moved_alert_ids: list[UUID]
    added_to_target_alert_ids: list[UUID]


class CaseView(Contract):
    id: UUID
    source_namespace: str | None
    title: str
    description: str | None
    handling_status: WorkStatus
    severity: Severity | None
    severity_source: str | None
    owner_id: UUID | None
    assignment_state: AssignmentState
    owner_source_value: str | None
    assigned_at: datetime | None
    tags: list[str]
    priority_value: Decimal | None
    priority_state: ScoreState
    priority_source: str | None
    priority_basis: dict[str, Any] | None
    scope_revision: int
    current_assessment_id: UUID | None
    classification: Classification | None = None
    due_at: AwareDatetime | None = None
    current_evidence_artifact_id: UUID | None = None
    created_at: datetime
    created_by: UUID | None
    business_updated_at: datetime
    resolved_at: datetime | None
    resolved_by: UUID | None
    resolution_note: str | None
    reopened_at: datetime | None
    row_version: int


class RunView(Contract):
    id: UUID
    case_id: UUID
    kind: RunKind
    title: str
    purpose: str
    trigger: RunTrigger
    scope_revision: int | None
    scope_updated_at: datetime | None
    scope_kind: str | None
    window_start: datetime | None
    window_end: datetime | None
    state: RunState
    comparison_result_id: UUID | None
    input_artifact_id: UUID | None
    executor_version: str | None
    requested_at: datetime
    requested_by: UUID | None
    started_at: datetime | None
    ended_at: datetime | None
    stop_reason: str | None
    stop_detail: str | None
    delivery_state: Delivery
    row_version: int


class ResultSummary(Contract):
    id: UUID
    case_id: UUID
    kind: ResultKind
    source_run_id: UUID
    source_answer_id: UUID | None
    title: str
    purpose: str
    conclusion: str | None
    conclusion_state: ConclusionState
    conclusion_origin: Origin
    validation_state: Validation
    closing_note: str
    comparison_result_id: UUID | None
    change_kind: ChangeKind
    change_summary: str | None
    input_artifact_id: UUID
    graph_artifact_id: UUID | None
    report_artifact_id: UUID | None
    supersedes_result_id: UUID | None
    delivery_state: Delivery
    created_at: datetime
    saved_at: datetime
    saved_by: UUID | None
    edited_fields: list[str]
    edit_note: str | None


class ResultView(ResultSummary):
    findings: list[Finding]
    questions: list[Question]
    recommendations: list[Recommendation]
    case_impact: Impact


class HistoryEntry(Contract):
    id: str
    recorded_at: datetime
    run: RunView
    result: ResultSummary | None


class HistoryPage(Contract):
    items: list[HistoryEntry]
    next_cursor: str | None


class HistoryCursor(Contract):
    at: AwareDatetime
    key: Annotated[str, Field(pattern=r"^(run|result):[0-9a-f-]{36}$")]


class StartAvailability(Contract):
    can_start: bool
    reason: Literal["ready", "not_pending", "resolved_case", "scope_changed", "empty_scope", "baseline_active"]


CaseMetric = Literal["awaiting_assignment", "in_progress", "high_severity", "awaiting_human"]


class CaseQueueQuery(Contract):
    limit: int = Field(default=20, ge=1, le=50)
    cursor: str | None = Field(default=None, max_length=1024)
    q: str | None = Field(default=None, max_length=200)
    handling_status: WorkStatus | None = None
    severity: Severity | None = None
    owner_id: UUID | None = None
    assignment_state: AssignmentState | None = None
    metric: CaseMetric | None = None
    classification: Classification | Literal["not_set"] | None = None

    @field_validator("q")
    @classmethod
    def normalize_search(cls, value):
        return (value.strip() or None) if value is not None else None


class CaseQueueCursor(Contract):
    version: Literal[1] = 1
    at: AwareDatetime
    id: UUID
    filter_fingerprint: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class CaseQueueMetrics(Contract):
    awaiting_assignment: int = Field(ge=0)
    in_progress: int = Field(ge=0)
    high_severity: int = Field(ge=0)
    awaiting_human: int = Field(ge=0)


class CaseBaselineRecord(Contract):
    run: RunView
    start_eligibility: StartAvailability


class CaseQueueItem(Contract):
    case: CaseView
    member_count: int = Field(ge=0)
    open_task_count: int = Field(ge=0)
    baseline_records: list[CaseBaselineRecord]
    page_data: CasePageData | None = None


class CaseQueuePage(Contract):
    items: list[CaseQueueItem]
    total: int = Field(ge=0)
    next_cursor: str | None
    metrics: CaseQueueMetrics


def project(model, row):
    return model.model_validate({key: row[key] for key in model.model_fields if key in row})


class CaseDetail(Contract):
    case: CaseView
    members: list[dict[str, Any]]
    member_count: int
    members_truncated: bool
    linked_incidents: list[dict[str, Any]]
    linked_incident_count: int
    linked_incidents_truncated: bool
    current_assessment: dict[str, Any] | None
    baseline_records: list[dict[str, Any]]
    page_data: CasePageData | None = None


class ExecutionSummary(Contract):
    artifact_id: UUID
    availability: str
    schema_version: str | None = None
    capabilities: dict[str, Any] | None = None
    limits: dict[str, Any] | None = None
    final_reservation: dict[str, Any] | None = None
    limitations: list[str] = Field(default_factory=list)


class RunDetail(Contract):
    run: RunView
    result_ids: list[UUID]
    result_count: int
    results_truncated: bool
    start_eligibility: StartAvailability
    current_member_count: int
    input_member_count: int
    members: list[dict[str, Any]]
    members_truncated: bool
    read_counts: dict[str, int]
    analysis_counts: dict[str, int]
    steps: list[dict[str, Any]]
    steps_truncated: bool
    tool_calls: int
    usage: dict[str, Any]
    artifacts: list[dict[str, Any]]
    artifact_counts: dict[str, int]
    artifacts_truncated: bool
    duration_seconds: float | None
    elapsed_seconds: float | None
    last_recorded_at: datetime
    observed_at: datetime
    execution_summary: ExecutionSummary | None = None


class SavedAnswerReference(Contract):
    id: UUID
    conversation_id: UUID
    in_reply_to: UUID | None
    source_run_id: UUID
    input_artifact_id: UUID
    answered_at: datetime


class ResultDetail(Contract):
    result: ResultView
    run: RunView
    source_answer: SavedAnswerReference | None
    members: list[dict[str, Any]]
    member_count: int
    members_truncated: bool
    delivery: dict[str, Any] | None


class ArtifactContent(Contract):
    artifact: dict[str, Any]
    content_json: Any | None
    content_text: str | None
    availability: str
