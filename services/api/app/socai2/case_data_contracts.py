"""Stable page data; independent of model outputs and execution stages."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator, model_validator

from .baseline_contracts import Contract, EvidenceRef

SCHEMA = "socai2.case-evidence.v1"
KIND = "case_evidence_index"
Classification = Literal["true_positive", "informational", "false_positive"]
Text = Annotated[str, Field(min_length=1, max_length=500, pattern=r"\S")]


class CaseDataUpdate(Contract):
    operation_key: UUID
    expected_row_version: int = Field(ge=1)
    classification: Classification | None
    due_at: AwareDatetime | None
    source: Literal["manual", "import"]
    source_note: Text


class SavedReference(EvidenceRef):
    source_path: Annotated[str, Field(min_length=1, max_length=2000)]
    row_keys: list[str] = Field(max_length=0)

    @field_validator("source_path")
    @classmethod
    def pointer(cls, value):
        if not value.startswith("/"):
            raise ValueError("source_path must be a JSON pointer into the saved row")
        return value


class Threat(Contract):
    namespace: Text
    key: Text
    label: Text
    source_refs: list[SavedReference] = Field(min_length=1, max_length=20)


class EvidenceObject(Contract):
    material_id: UUID
    object_key: Text


class EvidenceEntry(Contract):
    evidence_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]+:[^\s]+$", max_length=300)]
    title: Text
    type: Text
    alert_ids: list[UUID] = Field(min_length=1, max_length=200)
    object_keys: list[EvidenceObject] = Field(max_length=50)
    source_refs: list[SavedReference] = Field(min_length=1, max_length=30)
    verdict: Literal["malicious", "suspicious", "clean", "unknown", "conflicting"]
    verdict_sources: list[SavedReference] = Field(max_length=30)
    threat: Threat | None
    remediation: SavedReference | None
    state: Literal["active", "withdrawn"]

    @model_validator(mode="after")
    def semantics(self):
        if len(set(self.alert_ids)) != len(self.alert_ids):
            raise ValueError("duplicate member")
        if self.verdict != "unknown" and not self.verdict_sources:
            raise ValueError("verdict requires saved sources")
        if self.verdict == "conflicting" and len({(r.type, r.id, r.source_path) for r in self.verdict_sources}) < 2:
            raise ValueError("conflict requires both sources")
        if self.remediation and self.remediation.role != "execution_receipt":
            raise ValueError("remediation requires an execution receipt")
        return self


class EvidenceIndex(Contract):
    schema_version: Literal["socai2.case-evidence.v1"]
    scope_revision: int = Field(ge=0)
    alert_ids: list[UUID] = Field(max_length=200)
    supersedes_artifact_id: UUID | None
    availability_state: Literal["available", "partial", "unavailable"]
    limitations: list[Text] = Field(max_length=30)
    entries: list[EvidenceEntry] = Field(max_length=500)

    @model_validator(mode="after")
    def unique_and_scoped(self):
        if len(set(self.alert_ids)) != len(self.alert_ids):
            raise ValueError("duplicate index member")
        if len({e.evidence_id for e in self.entries}) != len(self.entries):
            raise ValueError("duplicate evidence_id")
        if any(not set(e.alert_ids) <= set(self.alert_ids) for e in self.entries):
            raise ValueError("entry outside frozen scope")
        if self.availability_state != "available" and not self.limitations:
            raise ValueError("partial/unavailable needs a limitation")
        if self.availability_state == "unavailable" and self.entries:
            raise ValueError("unavailable index cannot publish entries")
        return self


class EvidencePublish(Contract):
    operation_key: UUID
    expected_row_version: int = Field(ge=1)
    expected_current_artifact_id: UUID | None
    index: EvidenceIndex


class CaseDataReceipt(Contract):
    case_id: UUID
    row_version: int
    changed: bool
    current_evidence_artifact_id: UUID | None


class EvidenceView(Contract):
    artifact_id: UUID | None
    state: Literal["available", "partial", "unavailable", "not_recorded", "invalid_reference"]
    evidence_count: int | None
    threat_count: int | None
    covered_alert_ids: list[UUID]
    uncovered_alert_ids: list[UUID]
    excluded_evidence_ids: list[str]
    limitations: list[str]
    entries: list[EvidenceEntry]
    index: EvidenceIndex | None


class AssessmentPageView(Contract):
    id: UUID
    conclusion: str
    origin: Literal["model", "human", "system", "legacy"]
    validity: str
    scope_revision: int
    formed_at: AwareDatetime
    adopted_at: AwareDatetime
    alert_ids: list[UUID]
    sources: list[dict]


class CasePageData(Contract):
    schema_version: Literal["socai2.case-page-data.v1"] = "socai2.case-page-data.v1"
    classification: Classification | None
    due_at: AwareDatetime | None
    determination: str | None
    assessment: AssessmentPageView | None
    evidence: EvidenceView
