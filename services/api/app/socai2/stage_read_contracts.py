"""Read contracts for A/I analysis; current adoption is distinct from freshness."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

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


class StagePage(Contract):
    subject_id: UUID
    kind: Literal["alert_basic", "incident_diagnosis"]
    current_pointer_id: UUID | None
    current: StageEntry | None
    current_unavailable_reason: str | None
    entries: list[StageEntry]
    next_before_run_id: UUID | None
