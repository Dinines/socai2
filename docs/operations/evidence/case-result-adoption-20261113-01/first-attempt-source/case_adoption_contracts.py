"""Internal fixed-result adoption contracts; not the reserved Q HTTP DTO."""
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import Field, StringConstraints

from .baseline_contracts import Contract
from .case_contracts import ResultView, RunView

ReviewToken = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class AdoptedAssessment(Contract):
    id: UUID
    case_id: UUID
    revision: int
    scope_revision: int
    conclusion: str
    origin: str
    validity: str
    formed_at: datetime
    adopted_at: datetime
    adopted_by: UUID | None
    actor: dict[str, Any]
    reason: str | None
    sources: list[dict[str, Any]]
    members: list[dict[str, Any]]
    results: list[ResultView]


class ResultAdoptionPreview(Contract):
    case_id: UUID
    case_row_version: int
    scope_revision: int
    handling_status: str
    review_token: ReviewToken
    current_assessment: AdoptedAssessment | None
    candidate: ResultView
    source_run: RunView
    current_alert_ids: list[UUID]
    members: list[dict[str, Any]]
    uncovered_alert_ids: list[UUID]
    outside_alert_ids: list[UUID]
    input_freshness: dict[str, Any]
    unfinished_tasks: list[dict[str, Any]]
    unfinished_runs: list[dict[str, Any]]
    requires_pending_work_acknowledgement: bool
    can_adopt: bool
    refusal_reasons: list[str]


class ResultAdoptionRequest(Contract):
    operation_key: UUID
    expected_review_token: ReviewToken
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    acknowledge_pending_work: bool = False


class ResultAdoptionReceipt(Contract):
    case_id: UUID
    result_id: UUID
    assessment_id: UUID
    previous_assessment_id: UUID | None
    assessment_revision: int
    case_row_version: int


class AssessmentHistory(Contract):
    items: list[AdoptedAssessment]
    total: int = Field(ge=0)
    next_offset: int | None
