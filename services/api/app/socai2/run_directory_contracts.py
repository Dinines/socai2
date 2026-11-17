"""Query inputs for the unified Run directory, independent of HTTP."""
from datetime import UTC
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator, model_validator

from .baseline_contracts import Contract
from .enums import RunState

RunSubject = Literal["alert", "incident", "case"]
DirectoryRunKind = Literal["alert_basic", "incident_diagnosis", "baseline", "ai_question", "targeted"]
AnalysisIntent = Literal["initial", "check", "rerun", "targeted", "synthesis"]


class RunDirectoryQuery(Contract):
    subject_type: RunSubject | None = None
    subject_id: UUID | None = None
    run_kind: DirectoryRunKind | None = None
    intent: AnalysisIntent | None = None
    state: RunState | None = None
    time_from: AwareDatetime | None = None
    time_to: AwareDatetime | None = None
    limit: int | None = Field(default=None, ge=1)
    cursor: str | None = Field(default=None, max_length=4096)

    @field_validator("time_from", "time_to")
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def valid_scope(self):
        if self.subject_id is not None and self.subject_type is None:
            raise ValueError("subject_id_requires_subject_type")
        if self.time_from is not None and self.time_to is not None and self.time_from >= self.time_to:
            raise ValueError("time_from_must_precede_time_to")
        return self
