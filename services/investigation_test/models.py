"""Versioned test records, separate from business task and Run schemas."""
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")]
Text = Annotated[str, Field(min_length=1)]
CaseStatus = Literal["not_run", "blocked", "passed", "failed", "deferred", "not_covered"]
BatchStatus = Literal["planned", "preparing", "running", "finished", "blocked", "failed", "interrupted"]
TERMINAL = {"finished", "failed", "interrupted"}


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Batch(Record):
    id: Identifier
    environment: Identifier
    title: Text
    scenario_version: Text
    execution_state: BatchStatus
    mode: Literal["live", "archive"]
    provenance: Literal["live_execution", "saved_evidence", "synthetic_fixture"]
    started_at: AwareDatetime | None = None
    updated_at: AwareDatetime
    quality_status: Literal["not_assessed", "issues_recorded", "assessed_no_issues"]


class BusinessMapping(Record):
    subject_type: Literal["alert", "incident", "case"]
    subject_id: UUID
    task_id: UUID | None = None
    run_id: UUID | None = None
    result_type: Literal["alert_assessment", "incident_diagnosis", "case_result"] | None = None
    result_id: UUID | None = None

    @model_validator(mode="after")
    def result_source(self):
        if (self.result_type is None) != (self.result_id is None):
            raise ValueError("result type and identity must be paired")
        if self.result_id is not None and self.run_id is None:
            raise ValueError("a result requires its source Run")
        if self.result_type and self.result_type != {
            "alert": "alert_assessment", "incident": "incident_diagnosis", "case": "case_result"
        }[self.subject_type]:
            raise ValueError("result type differs from subject")
        return self


class TestCase(Record):
    id: Identifier
    use_case_id: Identifier
    scenario_id: Identifier
    status: CaseStatus
    expected: Annotated[list[Text], Field(min_length=1)]
    actual: list[Text] = Field(default_factory=list)
    operation_ids: list[Identifier] = Field(default_factory=list)
    evidence_ids: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def pass_has_evidence(self):
        if self.status == "passed" and (not self.actual or not self.evidence_ids):
            raise ValueError("passed requires actual checks and registered evidence")
        return self


class Operation(Record):
    id: Identifier
    case_id: Identifier
    intent: Text
    execution_state: Literal["planned", "accepted", "running", "completed", "failed", "unknown", "skipped"]
    occurred_at: AwareDatetime | None = None
    mappings: list[BusinessMapping] = Field(default_factory=list)
    evidence_ids: list[Identifier] = Field(default_factory=list)


class Preparation(Record):
    status: Literal["not_run", "planned", "inspected", "prepared", "failed"]
    cleanup_mode: Literal["no_cleanup", "planned", "executed"]
    summary: Text
    resources: list[Text] = Field(default_factory=list)
    observed_at: AwareDatetime | None = None
    evidence_ids: list[Identifier] = Field(default_factory=list)


class QualityIssue(Record):
    id: Identifier
    case_id: Identifier
    run_id: UUID | None = None
    stage: Text
    category: Text
    description: Text
    status: Literal["open", "deferred", "resolved"]
    affects_flow: bool
    evidence_ids: Annotated[list[Identifier], Field(min_length=1)]


class EvidenceSource(Record):
    id: Identifier
    path: Text
    label: Text
    mime_type: Annotated[str, Field(pattern=r"^[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+$")]
    visibility: Literal["public"]
    source_ref: str | None = None


class Evidence(Record):
    id: Identifier
    label: Text
    mime_type: str
    size: Annotated[int, Field(ge=0)]
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    source_ref: str | None = None


class Document(Record):
    schema_version: Literal[1]
    batch: Batch
    cases: list[TestCase]
    operations: list[Operation]
    preparation: Preparation
    quality_issues: list[QualityIssue]
    evidence: list[EvidenceSource]

    @model_validator(mode="after")
    def references(self):
        def indexed(values):
            result = {item.id: item for item in values}
            if len(result) != len(values):
                raise ValueError("duplicate record identity")
            return result
        cases, operations = indexed(self.cases), indexed(self.operations)
        indexed(self.quality_issues)
        evidence = indexed(self.evidence)
        for item in [*self.cases, *self.operations, self.preparation, *self.quality_issues]:
            if len(item.evidence_ids) != len(set(item.evidence_ids)) or not set(item.evidence_ids) <= evidence.keys():
                raise ValueError("invalid evidence reference")
        for item in self.cases:
            if len(item.operation_ids) != len(set(item.operation_ids)):
                raise ValueError("duplicate operation reference")
            if any(key not in operations or operations[key].case_id != item.id for key in item.operation_ids):
                raise ValueError("invalid operation reference")
        for item in self.operations:
            if item.case_id not in cases or item.id not in cases[item.case_id].operation_ids:
                raise ValueError("invalid test case reference")
        for issue in self.quality_issues:
            if issue.case_id not in cases:
                raise ValueError("invalid quality test case reference")
            if issue.run_id is not None:
                runs = {m.run_id for op in self.operations if op.case_id == issue.case_id for m in op.mappings}
                if issue.run_id not in runs:
                    raise ValueError("quality Run must be mapped in the same test case")
        if bool(self.quality_issues) != (self.batch.quality_status == "issues_recorded"):
            raise ValueError("quality status and records differ")
        return self


class PublishedDocument(Document):
    evidence: list[Evidence]


class Ledger(Record):
    revision: Annotated[int, Field(ge=1)]
    published_at: AwareDatetime
    document: PublishedDocument


class EvidenceView(Evidence):
    metadata_url: str
    content_url: str


class BatchListItem(Record):
    revision: int
    batch: Batch
    counts: dict[str, int]
    detail_url: str


class BatchView(BatchListItem):
    schema_version: Literal[1] = 1
    links: dict[str, str]
    evidence: list[EvidenceView]


class PreparationView(Record):
    schema_version: Literal[1] = 1
    revision: int
    preparation: Preparation


Item = TypeVar("Item")


class Page(Record, Generic[Item]):
    items: list[Item]
    total: int
    next_cursor: str | None
    observed_at: AwareDatetime


class InvestigationHTTP(Record):
    environment_label: Identifier
    tenant_id: UUID
    contract_sha256: str
    get_operations: int
    read_only: Literal[True]
    runtime_verified: Literal[False]


class Capabilities(Record):
    service_version: str
    viewer_version: str | None = None
    test_api_schema: Literal["socai2.test-api.v1"]
    document_schema_versions: list[int]
    environment_label: str
    read_only: Literal[True]
    latest_preparation_observed_at: AwareDatetime | None
    investigation_http: InvestigationHTTP | None = None
