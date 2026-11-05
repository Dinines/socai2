"""Typed contracts used by the opt-in baseline store; no model calls here."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from .enums import (
    AnalysisState,
    ChangeKind,
    ConclusionState,
    Delivery,
    Origin,
    ReadState,
    Validation,
)

FULL_EXECUTOR_VERSION = "socai2.baseline-executor.v2"
FULL_EXECUTOR_VERSIONS = {"socai2.baseline-executor.v1", FULL_EXECUTOR_VERSION}


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Actor(Contract):
    # User name is supplied by the authenticated principal, never the request body.
    user_id: UUID
    name: str = Field(min_length=1)

    def snapshot(self):
        return {"type": "user", "user_id": str(self.user_id), "name_snapshot": self.name,
                "service_name": None, "service_version": None}


class Scope(Contract):
    kind: Literal["whole_case", "selected_alerts", "explicit_objects"]
    alert_ids: list[UUID]
    object_keys: list[str]
    window_start: AwareDatetime | None
    window_end: AwareDatetime | None
    limitations: list[str]

    @model_validator(mode="after")
    def valid_window(self):
        if (self.window_start is None) != (self.window_end is None):
            raise ValueError("window requires both endpoints")
        if self.window_start and self.window_start > self.window_end:
            raise ValueError("window start exceeds end")
        if len(set(self.alert_ids)) != len(self.alert_ids):
            raise ValueError("duplicate scope member")
        return self


class EvidenceRef(Contract):
    # This first store supports resolvable internal references only. External
    # evidence must first be persisted by a Tool as an artifact with provenance.
    type: Literal["alert_material", "artifact", "task_revision", "result"]
    id: UUID
    external: None
    source_path: str | None
    row_keys: list[str]
    role: Literal["observation", "source_label", "prior_analysis", "human_statement", "execution_receipt"]


class Limits(Contract):
    max_model_calls: int | None = Field(ge=0)
    max_tokens: int | None = Field(ge=0)
    max_tool_calls: int | None = Field(ge=0)
    max_rows_per_query: int | None = Field(ge=0)
    deadline_at: AwareDatetime | None
    policy_version: str = Field(min_length=1)


class Start(Contract):
    expected_scope_revision: int = Field(ge=0)
    operation_key: UUID
    window_start: AwareDatetime | None = None
    window_end: AwareDatetime | None = None
    comparison_result_id: UUID | None = None

    @model_validator(mode="after")
    def valid_window(self):
        Scope(kind="whole_case", alert_ids=[], object_keys=[], window_start=self.window_start,
              window_end=self.window_end, limitations=[])
        return self


class Finding(Contract):
    id: str
    statement: str
    state: Literal["observed", "inferred", "unresolved", "withdrawn"]
    scope: Scope
    support: list[EvidenceRef]
    counterevidence: list[EvidenceRef]
    limitations: list[str]


class Question(Contract):
    id: str
    text: str
    scope: Scope
    evidence_requirements: list[str]
    state: Literal["open", "answered", "unresolved", "not_attempted"]
    answer: str | None
    evidence_refs: list[EvidenceRef]
    limitations: list[str]


class Target(Contract):
    object_key: str
    display_name: str


class Recommendation(Contract):
    id: str
    action_type: str
    targets: list[Target]
    reason: str
    approval_requirement: Literal["required", "not_required", "unknown"]
    source_refs: list[EvidenceRef]
    limitations: list[str]


class Impact(Contract):
    summary: str | None
    supported_changes: list[str]
    cannot_generalize: list[str]
    affected_scope: Scope
    next_steps: list[str]


class MemberDelivery(Contract):
    alert_id: UUID
    read_state: ReadState
    assessment_state: AnalysisState
    conclusion_covered: bool
    assessment: str | None
    limitations: str | None
    evidence_refs: list[EvidenceRef]

    @model_validator(mode="after")
    def valid_coverage(self):
        if self.conclusion_covered and self.assessment_state not in {"analyzed", "unresolved"}:
            raise ValueError("conclusion coverage requires analysis")
        return self


class Publication(Contract):
    """Trusted executor output after validation, never a public request body.

    accepted records the executor's validation outcome; this persistence layer
    checks identity/shape/coverage, not the truth of a model's prose.
    """
    operation_key: UUID
    terminal_state: Literal["completed", "failed", "cancelled"]
    stop_reason: str = Field(min_length=1)
    stop_detail: str | None = None
    title: str = Field(min_length=1)
    conclusion: str | None
    conclusion_state: ConclusionState
    conclusion_origin: Origin
    validation_state: Validation
    closing_note: str
    findings: list[Finding]
    questions: list[Question]
    recommendations: list[Recommendation]
    change_kind: ChangeKind
    change_summary: str | None
    case_impact: Impact
    graph_artifact_id: UUID | None = None
    report_artifact_id: UUID | None = None
    delivery_state: Delivery
    members: list[MemberDelivery]

    @model_validator(mode="after")
    def valid_result(self):
        if (self.conclusion_state == "unavailable") != (self.conclusion is None):
            raise ValueError("conclusion and availability disagree")
        if self.conclusion is not None and not self.conclusion.strip():
            raise ValueError("blank conclusion")
        if len({m.alert_id for m in self.members}) != len(self.members):
            raise ValueError("duplicate member delivery")
        if self.delivery_state == "complete" and any(
            m.assessment_state not in {"analyzed", "unresolved"} for m in self.members
        ):
            raise ValueError("complete delivery must account for every member")
        return self


class Claim(Contract):
    run_id: UUID
    case_id: UUID
    scope_revision: int
    state: str
    newly_claimed: bool
    input_artifact_id: UUID
    started_at: datetime
