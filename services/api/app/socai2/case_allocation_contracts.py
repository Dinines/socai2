"""Case allocation business receipts; HTTP adds navigation URLs."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .baseline_contracts import Contract
from .enums import Severity, WorkStatus


class CaseContinuation(Contract):
    root_case_id: UUID
    previous_case_id: UUID | None
    receiving_case_id: UUID


class InitialTaskReceipt(Contract):
    task_id: UUID
    subject_type: Literal["case"] = "case"
    subject_id: UUID
    status: Literal["accepted"] = "accepted"


class CaseAllocation(Contract):
    case_id: UUID
    scope_revision: int = Field(ge=0)
    created: bool
    changed: bool
    previous_case_id: UUID | None
    added_alert_ids: list[UUID]
    existing_alert_ids: list[UUID]
    linked_incident_ids: list[UUID]
    initial_task: InitialTaskReceipt | None


class IncidentReceiver(Contract):
    incident_id: UUID
    active_case_id: UUID


class CaseAllocationReceipt(Contract):
    operation_key: UUID
    requested_case_id: UUID | None
    primary_case_id: UUID
    continuation_root_case_id: UUID
    receiving_case_id: UUID
    changed: bool
    allocations: list[CaseAllocation]
    incident_receivers: list[IncidentReceiver]
    excluded_alert_ids: list[UUID]


class FollowIncident(Contract):
    operation_key: UUID
    incident_id: UUID


class CaseMemberRemoval(Contract):
    case_id: UUID
    scope_revision: int = Field(ge=0)
    removed_alert_ids: list[UUID]
    changed: bool


class CaseReplacementReceipt(Contract):
    source: CaseMemberRemoval
    allocation: CaseAllocationReceipt


class CaseMoveReceipt(CaseReplacementReceipt):
    moved_alert_ids: list[UUID]


class SharedIncident(Contract):
    incident_id: UUID
    title: str
    current_case_sources: list[Literal["explicit", "member_alert"]]
    related_case_sources: list[Literal["explicit", "member_alert"]]


class RelatedCaseItem(Contract):
    case_id: UUID
    title: str
    handling_status: WorkStatus
    severity: Severity | None
    relation_types: list[Literal["continuation", "shared_incident"]]
    primary_relation: Literal["continuation", "shared_incident"]
    continuation: CaseContinuation | None
    shared_incidents: list[SharedIncident]


class RelatedCasePage(Contract):
    case_id: UUID
    relation_revision: str
    items: list[RelatedCaseItem]
    total: int = Field(ge=0)
    next_cursor: str | None
    observed_at: datetime
