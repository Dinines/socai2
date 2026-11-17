"""Strict immutable stage-delivery receipts; storage uses existing artifacts."""
import hashlib
import json
import re
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    model_validator,
)

from .baseline_contracts import Contract, EvidenceRef
from .baseline_store import digest

VERSION = "socai2.stage-delivery.v1"
Sha = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class Original(Contract):
    artifact_id: UUID
    kind: Literal["request", "response", "received_fragment"]
    sha256: Sha


class ExecutionError(Contract):
    code: StrictStr
    message: StrictStr
    retryable: StrictBool
    occurred_at: AwareDatetime


class Execution(Contract):
    kind: Literal["model", "tool", "program"]
    call_state: Literal["completed", "failed", "unknown", "skipped"]
    local_state: Literal["ended"]
    local_ended_at: AwareDatetime
    request_dispatched: StrictBool | None
    finish_reason: StrictStr | None
    error: ExecutionError | None
    retry_allowed: StrictBool
    retry_reason: StrictStr


class Parse(Contract):
    state: Literal["complete_json", "closed_units", "unusable", "no_response"]
    truncated: StrictBool
    reasons: list[StrictStr]


class Delivery(Contract):
    state: Literal["complete", "partial", "none"]
    reasons: list[StrictStr]


class Gap(Contract):
    path: StrictStr
    reason_code: StrictStr


class ResolvedRef(Contract):
    source_id: StrictStr
    alert_ids: list[UUID]
    ref: EvidenceRef


class Unit(Contract):
    path: StrictStr
    kind: StrictStr
    value: Any
    original_artifact_id: UUID
    original_content_path: StrictStr
    value_span: tuple[StrictInt, StrictInt]
    value_sha256: Sha
    declared_scope: dict | None
    resolved_refs: list[ResolvedRef]
    structure_state: Literal["valid"]
    quality_issues: list[dict]

    @model_validator(mode="after")
    def valid_span(self):
        if not 0 <= self.value_span[0] < self.value_span[1]:
            raise ValueError("stage_delivery_invalid_span")
        return self


class Use(Contract):
    material_paths: list[StrictStr]
    dispatch_paths: list[StrictStr]
    conclusion_available: StrictBool
    adoption_eligible: StrictBool
    comparison_eligible: StrictBool
    reasons: list[StrictStr]


class Quality(Contract):
    policy: StrictStr
    state: Literal["not_checked", "checked", "issues_recorded"]
    issues: list[dict]
    processing: list[dict]
    references: list[dict]
    prose_quality: Literal["not_checked"]


class StageDelivery(Contract):
    schema_version: Literal["socai2.stage-delivery.v1"]
    type: Literal["stage_delivery"]
    run_id: UUID
    step_id: UUID
    stage: StrictStr
    input_artifact_id: UUID
    originals: list[Original]
    execution: Execution
    parse: Parse
    delivery: Delivery
    retained_units: list[Unit]
    missing_units: list[Gap]
    invalid_units: list[Gap]
    quality: Quality
    use: Use

    @model_validator(mode="after")
    def validate_links(self):
        paths = [u.path for u in self.retained_units]
        if len(self.originals) != len({o.artifact_id for o in self.originals}):
            raise ValueError("stage_delivery_original_identity_duplicate")
        originals = {o.artifact_id for o in self.originals if o.kind != "request"}
        if len(paths) != len(set(paths)) or any(u.original_artifact_id not in originals for u in self.retained_units):
            raise ValueError("stage_delivery_unit_identity_invalid")
        if not set(self.use.dispatch_paths) <= set(self.use.material_paths) <= set(paths):
            raise ValueError("stage_delivery_use_not_retained")
        if (self.delivery.state == "none") != (not paths):
            raise ValueError("stage_delivery_state_unit_mismatch")
        return self


def original_value(value, path):
    if not re.fullmatch(r"\$(?:\.[^.[\]]+|\[\d+\])+", path):
        raise ValueError("stage_delivery_content_path_invalid")
    for name, index in re.findall(r"\.([^.[\]]+)|\[(\d+)\]", path[1:]):
        value = value[name] if name else value[int(index)]
    if not isinstance(value, str):
        raise TypeError("stage_delivery_original_content_not_string")
    return value


def validate_sources(receipt, originals):
    """Check the saved source bodies, not a normalized copy of their JSON."""
    value = StageDelivery.model_validate(receipt)
    for original in value.originals:
        if digest(originals[str(original.artifact_id)]) != original.sha256:
            raise ValueError("stage_delivery_original_hash_mismatch")
    for unit in value.retained_units:
        text = original_value(originals[str(unit.original_artifact_id)], unit.original_content_path)
        start, end = unit.value_span
        part = text[start:end]
        if end > len(text) or hashlib.sha256(part.encode("utf-8")).hexdigest() != unit.value_sha256:
            raise ValueError("stage_delivery_unit_hash_mismatch")
        if json.loads(part) != unit.value:
            raise ValueError("stage_delivery_unit_value_mismatch")
    return value
