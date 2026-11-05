"""Human task writes never claim a machine Run or adopt a Case judgment."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator, model_validator

from .baseline_contracts import Contract, EvidenceRef, Scope
from .enums import TaskState


class TaskReference(Contract):
    type: Literal["alert_material", "artifact", "result", "task_revision"]
    id: UUID


class TaskFields(Contract):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: str | None = Field(default=None, max_length=10000)
    assignee_id: UUID | None = None
    due_at: AwareDatetime | None = None
    state: TaskState = TaskState.NOT_STARTED
    result_text: str | None = Field(default=None, max_length=20000)
    result_scope: Scope | None = None
    source_refs: list[TaskReference] = Field(default_factory=list, max_length=50)

    @field_validator("title")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("blank task title")
        return value

    @model_validator(mode="after")
    def valid_feedback(self):
        if self.state == TaskState.COMPLETED and (not (self.result_text or "").strip() or self.result_scope is None):
            raise ValueError("completed task requires result and explicit scope")
        if self.result_scope and (len(self.result_scope.alert_ids) > 200 or len(self.result_scope.object_keys) > 200):
            raise ValueError("task scope exceeds limit")
        keys = [(ref.type, ref.id) for ref in self.source_refs]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate source reference")
        return self


class TaskCreate(TaskFields):
    operation_key: UUID
    expected_scope_revision: int = Field(ge=0)
    origin_result_id: UUID | None = None
    origin_finding_id: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def origin_pair(self):
        if self.origin_finding_id is not None and self.origin_result_id is None:
            raise ValueError("finding requires origin result")
        return self


class TaskEdit(TaskFields):
    operation_key: UUID
    expected_scope_revision: int = Field(ge=0)
    expected_row_version: int = Field(ge=1)


class TaskRevisionView(Contract):
    id: UUID
    case_id: UUID
    task_id: UUID
    revision: int
    title: str
    description: str | None
    assignee_id: UUID | None
    due_at: datetime | None
    state: TaskState
    result_text: str | None
    result_scope: Scope | None
    source_refs: list[EvidenceRef]
    completed_at: datetime | None
    completed_by: UUID | None
    changed_at: datetime
    changed_by: UUID


class TaskView(Contract):
    id: UUID
    case_id: UUID
    current_revision_id: UUID
    origin_result_id: UUID | None
    origin_finding_id: str | None
    created_at: datetime
    created_by: UUID | None
    updated_at: datetime
    row_version: int
    current: TaskRevisionView


class TaskMutation(Contract):
    task: TaskView
    changed: bool


class TaskPage(Contract):
    items: list[TaskView]
    total: int
    next_offset: int | None


class TaskRevisionPage(Contract):
    items: list[TaskRevisionView]
    total: int
    next_offset: int | None
