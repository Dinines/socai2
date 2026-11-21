"""Typed stored creation evidence, shared by Incident and Case read contracts."""
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictInt, model_validator

from .baseline_contracts import Contract
from .enums import Severity


class RiskPriorityMap(Contract):
    info: StrictInt = Field(ge=0, le=100)
    low: StrictInt = Field(ge=0, le=100)
    medium: StrictInt = Field(ge=0, le=100)
    high: StrictInt = Field(ge=0, le=100)
    critical: StrictInt = Field(ge=0, le=100)


class RiskPolicy(Contract):
    schema_version: Literal["socai2.subject-risk-policy.v1"]
    version: str = Field(min_length=1)
    unknown_initial_severity: Severity
    priority_by_severity: RiskPriorityMap

    @model_validator(mode="after")
    def nonblank_version(self):
        if not self.version.strip():
            raise ValueError("blank risk policy version")
        return self


class RiskMember(Contract):
    alert_id: UUID
    material_id: UUID | None
    material_revision: int | None
    severity: Severity | None


class RiskInitial(Contract):
    level: Severity
    source: Literal["member_max", "initial_policy"]
    members: list[RiskMember]
    evaluated_at: AwareDatetime
    reason_code: Literal["highest_known_member", "source_severity_missing"]


class RiskOpinionLink(Contract):
    run_id: UUID
    artifact_id: UUID
    application_artifact_id: UUID
    started_at: AwareDatetime
    processed_at: AwareDatetime
    level: Severity | None
    reason_code: Literal["raised", "lower_not_applied", "unchanged", "execution_unconfirmed",
        "opinion_missing_or_invalid", "manual_revision_changed", "frozen_scope_changed", "local_scope_only",
        "scope_unavailable", "input_changed", "newer_round_exists"]


class RiskCurrent(Contract):
    level: Severity
    source: Literal["member_max", "initial_policy", "manual", "manual_override", "model", "unknown"]
    updated_at: AwareDatetime
    actor_id: UUID | None
    reason_code: Literal["explicit_creation_request", "initial_rule", "legacy_value_preserved", "model_raise",
                         "manual_set", "manual_rule_restore"]
    reason: str | None = Field(default=None, min_length=1)
    rule_basis: RiskInitial | None = None
    opinion: RiskOpinionLink | None = None


class RiskSystemPriority(Contract):
    value: int = Field(ge=0, le=100)
    severity: Severity
    computed_at: AwareDatetime
    mapping_version: str


class RiskPriorityOverride(Contract):
    value: float = Field(ge=0, le=100, allow_inf_nan=False)
    source: str
    reason: str = Field(min_length=1)
    actor_id: UUID | None
    updated_at: AwareDatetime


class SubjectRisk(Contract):
    schema_version: Literal["socai2.subject-risk.v1"]
    policy: RiskPolicy
    initial: RiskInitial
    current: RiskCurrent
    system_priority: RiskSystemPriority
    manual_severity_revision: int = Field(ge=0)
    latest_opinion: RiskOpinionLink | None = None
    priority_override: RiskPriorityOverride | None = None
