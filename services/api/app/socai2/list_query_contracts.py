"""Read-only query inputs shared by application readers, independent of HTTP."""
from datetime import UTC
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictInt, field_validator, model_validator

from .baseline_contracts import Contract
from .enums import AlertStatus, AssignmentState, Severity, WorkStatus

SortOrder = Literal["asc", "desc"]
AlertSort = Literal["ingested_at", "event_time", "severity"]
IncidentSort = Literal["created_at", "last_activity_at", "severity"]
CaseSort = Literal["business_updated_at", "created_at", "severity"]
EXTENDED_CASE_FIELDS = {"time_from", "time_to", "sort_by", "sort_order"}


class DatedQuery(Contract):
    time_from: AwareDatetime | None = None
    time_to: AwareDatetime | None = None
    sort_order: SortOrder | None = None

    @field_validator("time_from", "time_to")
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def ordered_window(self):
        if self.time_from is not None and self.time_to is not None and self.time_from >= self.time_to:
            raise ValueError("time_from_must_precede_time_to")
        return self


class SubjectListQuery(DatedQuery):
    limit: int = Field(default=20, ge=1, le=50)
    before_id: UUID | None = None
    cursor: str | None = Field(default=None, max_length=1024)
    q: str | None = Field(default=None, max_length=200)
    severity: Severity | None = None
    owner_id: UUID | None = None
    assignment_state: AssignmentState | None = None

    @field_validator("q")
    @classmethod
    def normalize_search(cls, value):
        return (value.strip() or None) if value is not None else None

    @property
    def legacy(self):
        return all(value is None for value in self.model_dump(exclude={"limit", "before_id", "cursor"}).values())

    @model_validator(mode="after")
    def old_pagination(self):
        if self.before_id is not None and (self.cursor is not None or not self.legacy):
            raise ValueError("before_id_cannot_combine_with_cursor_filters_or_sort")
        return self


class AlertListQuery(SubjectListQuery):
    handling_status: AlertStatus | None = None
    sort_by: AlertSort | None = None


class IncidentListQuery(SubjectListQuery):
    handling_status: WorkStatus | None = None
    sort_by: IncidentSort | None = None


class ListCursor(Contract):
    version: Literal[2] = 2
    kind: Literal["alerts", "incidents", "cases"]
    sort_by: str
    id: UUID
    at: AwareDatetime | None = None
    rank: StrictInt | None = Field(default=None, ge=0, le=4)
    filter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
