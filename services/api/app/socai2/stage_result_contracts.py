"""Trusted A/I producer outputs, separate from Case results and public HTTP."""
from typing import Literal

from pydantic import Field, model_validator

from .alert_attck import AlertAttckMapping
from .baseline_contracts import Contract, EvidenceRef, Finding, Question, Recommendation
from .enums import BusinessVerdict

ALERT_EXECUTOR_VERSION = "socai2.alert-basic-executor.v4"
ALERT_QUERY_RECEIPT_VERSIONS = {"socai2.alert-basic-executor.v3", ALERT_EXECUTOR_VERSION}
INCIDENT_EXECUTOR_VERSION = "socai2.incident-diagnosis-executor.v4"


class AlertOutput(Contract):
    verdict: Literal["true_positive", "false_positive", "benign", "needs_review"]
    rationale: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    score_state: Literal["not_provided", "not_computed", "disabled", "failed", "available"]
    explanation: str = Field(min_length=1)
    generation_method: Literal["source", "template", "model"]
    source_refs: list[EvidenceRef]
    recommendations: list[Recommendation]
    limitations: list[str]
    attck_mappings: list[AlertAttckMapping] | None = None

    @model_validator(mode="after")
    def score_pair(self):
        if (self.score_state == "available") != (self.confidence is not None):
            raise ValueError("confidence must pair with available score_state")
        return self


class IncidentOutput(Contract):
    summary: str = Field(min_length=1)
    conclusion: str = Field(min_length=1)
    business_verdict: BusinessVerdict | None = None
    findings: list[Finding]
    source_refs: list[EvidenceRef]
    open_questions: list[Question]
    limitations: list[str]
