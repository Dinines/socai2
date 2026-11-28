"""External projections for related Case story and member relations."""
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from investigation_http.contracts import (
    Delivery,
    DirectoryRunKind,
    RunState,
    RunSubject,
    StoryEntry,
    StoryPage,
    StorySummary,
)
from investigation_http.run_directory_contracts import DirectoryResultRef
from investigation_http.run_record_contracts import RecordView


class InvestigationRelation(RecordView):
    kind: Literal["case_owned", "saved_result", "explicit_reference", "frozen_member_overlap"]
    source_type: Literal["case", "result", "artifact", "task_revision", "run"]
    source_id: UUID
    source_url: str


class InvestigationRef(RecordView):
    run_id: UUID
    subject_type: RunSubject
    subject_id: UUID
    run_kind: DirectoryRunKind
    title: str
    state: RunState
    delivery_state: Delivery
    requested_at: AwareDatetime
    detail_url: str
    result_refs: list[DirectoryResultRef]
    relations: list[InvestigationRelation] = Field(min_length=1)


class RelatedStoryEntry(StoryEntry):
    investigation_ref: InvestigationRef | None


class RelatedStoryPage(StoryPage):
    items: list[RelatedStoryEntry]
    summary: StorySummary
    limitations: list[str]


class SharedObject(RecordView):
    object_type: str
    namespace: str
    object_key: str
    label: str
    focus_material_id: UUID
    focus_object_id: UUID
    other_alert_count: int = Field(ge=1)
    material_url: str


class SharedObjectPage(RecordView):
    items: list[SharedObject]
    total: int = Field(ge=0)
    next_cursor: str | None
    limitations: list[str]


class MemberInvestigationPage(RecordView):
    items: list[InvestigationRef]
    total: int = Field(ge=0)
    next_cursor: str | None
    limitations: list[str]


class CaseMemberRelations(RecordView):
    case_id: UUID
    alert_id: UUID
    observed_at: AwareDatetime
    shared_objects: SharedObjectPage
    investigations: MemberInvestigationPage
