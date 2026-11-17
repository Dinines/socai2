"""External Run record views; URL fields belong to the HTTP boundary."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investigation_http.contracts import (
    ArtifactKind,
    MaterialState,
    ResultDetail,
    RunDetail,
    StepKind,
    StepState,
    TraceView,
)


class RecordView(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArtifactReference(RecordView):
    role: Literal["input", "output", "reused"]
    artifact_id: UUID
    run_id: UUID | None
    subject_type: Literal["alert", "incident", "case"]
    subject_id: UUID
    content_url: str


class RunStepView(RecordView):
    id: UUID
    run_id: UUID
    seq: int
    parent_step_id: UUID | None
    retry_of_step_id: UUID | None
    stage_code: str
    kind: StepKind
    name: str
    state: StepState
    provider: str | None
    implementation_version: str | None
    question_id: str | None
    started_at: datetime | None
    ended_at: datetime | None
    actual_args: dict[str, Any] | None
    returned_rows: int | None
    error: dict[str, Any] | None
    usage: dict[str, Any] | None
    input_artifact_id: UUID | None
    output_artifact_id: UUID | None
    reused_artifact_id: UUID | None
    artifact_refs: list[ArtifactReference]


class RunArtifactView(RecordView):
    id: UUID
    run_id: UUID
    step_id: UUID | None
    kind: ArtifactKind
    schema_version: str
    mime_type: str | None
    file_name: str | None
    size_bytes: int | None
    sha256: str | None
    captured_at: datetime
    material_state: MaterialState
    content_url: str


class RunRecordPage(RecordView):
    run_id: UUID
    subject_type: Literal["alert", "incident", "case"]
    subject_id: UUID
    total: int
    next_cursor: str | None
    observed_at: datetime


class RunStepPage(RunRecordPage):
    items: list[RunStepView]


class RunArtifactPage(RunRecordPage):
    items: list[RunArtifactView]


class DirectoryLinks(RecordView):
    steps_url: str
    artifacts_url: str


class CaseComparisonLinks(RecordView):
    previous_run_url: str | None = Field(description="冻结的上一实际完整调查Run详情；首轮或未记录为null，不按当前历史猜测。")
    comparison_result_url: str | None = Field(description="冻结且可用的前轮Result详情；不可比较或未记录为null。")


class RunDetailWithDirectories(RunDetail, DirectoryLinks, CaseComparisonLinks):
    pass


class ResultDetailWithComparison(ResultDetail, CaseComparisonLinks):
    pass


class TraceWithDirectories(TraceView, DirectoryLinks):
    pass


class RecordErrorDetail(RecordView):
    code: str
    message: str
    context: dict[str, Any]


class RecordError(RecordView):
    detail: RecordErrorDetail


class RecordValidationError(RecordView):
    detail: list[dict[str, Any]]
