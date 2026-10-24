"""M1 immutable scope/questions for the first unified investigation policy.

This module performs no authentication, database reads, tool execution or model
calls. The caller must authenticate TenantPrincipal, verify Run/member tenant
ownership and supply checked source fields before calling initialize_scope.
Structural provenance checks below cannot prove a source record is truthful.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import ipaddress
from typing import Any
from uuid import UUID

from app.security.tenant_scope import TenantPrincipal

POLICY_REF = "network_observation.v1"
SOURCE = "clickhouse.raw_events"
CAPABILITY = "activity_records"
MAX_LIMIT = 10
_PATHS = {"hostname": "hostname", "source_ip": "src_ip", "dest_ip": "dst_ip",
          "dst_port": "raw_event.telemetry[0].dst_port", "protocol": "raw_event.telemetry[0].protocol",
          "source_event_ids": "source_event_ids"}
_QUESTION_IDS = ("Q1", "Q2", "Q3a", "Q3b", "Q4", "Q5")


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _uuid(value: Any) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _text(value: Any, name: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"{name} is required")
    return value


@dataclass(frozen=True)
class UTCWindow:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        for name in ("start", "end"):
            value = getattr(self, name)
            _require(isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None,
                     "window must contain timezone-aware datetimes")
            object.__setattr__(self, name, value.astimezone(timezone.utc))
        _require(self.start < self.end, "window must be nonempty and forward")

    def contains(self, other: UTCWindow) -> bool:
        return self.start <= other.start < other.end <= self.end


@dataclass(frozen=True)
class SourceField:
    parameter: str
    record_ref: str
    path: str
    value: str | int | tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.record_ref, "record_ref")
        _text(self.path, "field path")
        if isinstance(self.value, (list, tuple)):
            _require(all(isinstance(value, str) for value in self.value), "source field array must contain strings")
            object.__setattr__(self, "value", tuple(self.value))
        else:
            _require(type(self.value) in (str, int), "source field value must be scalar or immutable string array")


@dataclass(frozen=True)
class CheckedAlert:
    tenant_id: UUID
    alert_id: UUID
    record_ref: str
    ownership_check_ref: str
    hostname: str
    source_ip: str
    dest_ip: str
    dst_port: int
    protocol: str
    source_event_ids: tuple[UUID, ...]
    fields: tuple[SourceField, ...]
    data_only_text: str = ""

    def __post_init__(self) -> None:
        for name in ("tenant_id", "alert_id"):
            object.__setattr__(self, name, _uuid(getattr(self, name)))
        _text(self.record_ref, "record_ref")
        _text(self.ownership_check_ref, "ownership_check_ref")
        _text(self.hostname, "hostname")
        for name in ("source_ip", "dest_ip"):
            object.__setattr__(self, name, str(ipaddress.ip_address(getattr(self, name))))
        _require(type(self.dst_port) is int and self.dst_port == 443 and self.protocol == "TCP",
                 "network_observation.v1 supports only TCP port 443")
        object.__setattr__(self, "source_event_ids", tuple(_uuid(item) for item in self.source_event_ids))
        _require(bool(self.source_event_ids) and len(set(self.source_event_ids)) == len(self.source_event_ids),
                 "source_event_ids must be nonempty and unique")
        object.__setattr__(self, "fields", tuple(self.fields))
        _require(all(isinstance(item, SourceField) for item in self.fields), "checked fields must be SourceField values")
        _require(len(self.fields) == len(_PATHS) and {item.parameter for item in self.fields} == set(_PATHS),
                 "checked fields must provide each required parameter exactly once")
        expected = {key: getattr(self, key) for key in _PATHS}
        expected["source_event_ids"] = tuple(str(item) for item in self.source_event_ids)
        for field in self.fields:
            _require(field.record_ref == self.record_ref and field.path == _PATHS[field.parameter]
                     and field.value == expected[field.parameter], "source field does not match checked alert value/path")
        _require(isinstance(self.data_only_text, str), "data_only_text must be text")


@dataclass(frozen=True)
class OmittedMember:
    tenant_id: UUID
    alert_id: UUID
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", _uuid(self.tenant_id))
        object.__setattr__(self, "alert_id", _uuid(self.alert_id))
        _text(self.reason, "omission reason")


@dataclass(frozen=True)
class CheckedMemberSnapshot:
    source_ref: str
    total_members: int | None
    selected: tuple[CheckedAlert, ...]
    omitted: tuple[OmittedMember, ...] = ()
    view_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.source_ref, "member snapshot source")
        for name in ("selected", "omitted", "view_limitations"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        _require(bool(self.selected) and all(isinstance(item, CheckedAlert) for item in self.selected),
                 "at least one checked selected member is required")
        _require(all(isinstance(item, OmittedMember) for item in self.omitted), "invalid omitted member")
        for reason in self.view_limitations:
            _text(reason, "view limitation")
        ids = [item.alert_id for item in (*self.selected, *self.omitted)]
        _require(len(set(ids)) == len(ids), "member identities must be unique across selected and omitted")
        if self.total_members is None:
            _require(bool(self.view_limitations), "unknown total requires view limitations")
        else:
            _require(type(self.total_members) is int and self.total_members >= len(ids), "inconsistent member total")
            _require(self.total_members == len(ids) or bool(self.view_limitations), "unlisted members require a limitation")

    @property
    def unlisted_members(self) -> int | None:
        return None if self.total_members is None else self.total_members - len(self.selected) - len(self.omitted)


@dataclass(frozen=True)
class EntityRef:
    kind: str
    value: str


@dataclass(frozen=True)
class PrincipalScope:
    tenant_ids: frozenset[UUID]
    subject: str
    delegated: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_ids", frozenset(_uuid(item) for item in self.tenant_ids))
        _text(self.subject, "principal subject")
        _require(type(self.delegated) is bool, "principal delegated flag must be boolean")


@dataclass(frozen=True)
class ConclusionScope:
    member_ids: tuple[UUID, ...]
    entities: tuple[EntityRef, ...]
    window: UTCWindow
    objective: str = "verify_source_network_observation"
    evidence_coverage: str = "not_started"
    investigated_members: int = 0


@dataclass(frozen=True)
class QueryScope:
    members: tuple[CheckedAlert, ...]
    window: UTCWindow
    sources: tuple[str, ...] = (SOURCE,)
    capabilities: tuple[str, ...] = (CAPABILITY,)
    relation: str = "checked_alert_fields"
    max_depth: int = 0
    max_limit: int = MAX_LIMIT


@dataclass(frozen=True)
class Question:
    question_id: str
    purpose: str
    evidence_requirements: tuple[str, ...]
    allowed_capabilities: tuple[str, ...]
    dependencies: tuple[str, ...]
    entities: tuple[EntityRef, ...]
    critical: bool = True
    decision_dependency: bool = True
    capability_gaps: tuple[str, ...] = ()
    applicability: str = "applicable"
    policy_reason: str = ""
    processing_status: str = "pending"
    answer_status: str = "unassessed"

    def __post_init__(self) -> None:
        for name in ("evidence_requirements", "allowed_capabilities", "dependencies", "entities", "capability_gaps"):
            object.__setattr__(self, name, tuple(getattr(self, name)))


def _questions(entities: tuple[EntityRef, ...]) -> tuple[Question, ...]:
    return (
        Question("Q1", "What does the source actually record?",
                 ("event identity and source", "absolute time and endpoints", "observed action and outcome", "original source record"),
                 (CAPABILITY,), (), entities),
        Question("Q2", "Which records are explicitly linked to the selected alert?",
                 ("exact tenant and event IDs", "field provenance; proximity alone is insufficient"),
                 (CAPABILITY,), ("Q1",), entities, critical=False, decision_dependency=False,
                 policy_reason="Supporting linkage question for source-record verification; it does not establish causality or overall investigation completion."),
        Question("Q3a", "What evidence supports the nature of this activity?",
                 ("evidence supporting malicious, benign or erroneous activity",),
                 (CAPABILITY,), ("Q1", "Q2"), entities, critical=False, decision_dependency=False,
                 capability_gaps=("Network observations alone cannot establish malice or benign intent; corroboration source unavailable.",),
                 policy_reason="This limited objective verifies source observations, not a malicious or benign verdict; the behavior question is retained unassessed."),
        Question("Q3b", "What evidence supports business authorization?",
                 ("explicit authorization or denial tied to the activity",), (), ("Q1",), entities,
                 critical=False, decision_dependency=False,
                 capability_gaps=("No authorization source is available; absence does not establish unauthorized activity.",),
                 policy_reason="Business authorization is outside this source-record objective; the authorization question is retained unassessed and independent of behavior."),
        Question("Q4", "What impact is evidenced within the explicit scope?",
                 ("affected entities and demonstrated effects",), (CAPABILITY,), ("Q1", "Q2"), entities,
                 critical=False, decision_dependency=False,
                 capability_gaps=("An observation with unknown outcome does not establish successful connection or wider impact.",),
                 policy_reason="Wider impact is outside the limited source-record objective; retaining this question does not promise full investigation coverage."),
        Question("Q5", "Which material and questions remain uncovered?",
                 ("source availability, limits and omissions", "selected versus investigated members"),
                 (CAPABILITY,), ("Q1", "Q2"), entities),
    )


def validate_questions(questions: tuple[Question, ...], entities: tuple[EntityRef, ...]) -> None:
    ids = [question.question_id for question in questions]
    _require(len(ids) == len(set(ids)), "duplicate question ID")
    _require(set(ids) == set(_QUESTION_IDS), "all six core questions must be retained")
    by_id = {question.question_id: question for question in questions}
    for question in questions:
        required = question.question_id in {"Q1", "Q5"}
        _require(question.critical is required and question.decision_dependency is required,
                 "question criticality differs from the limited objective policy")
        if not required:
            _text(question.policy_reason, "non-decision question policy reason")
        _require(question.processing_status == "pending" and question.answer_status == "unassessed", "initial questions cannot contain answers")
        _require(set(question.entities).issubset(entities), "question entity is outside scope")
        _require(set(question.allowed_capabilities).issubset({CAPABILITY}), "unknown question capability")
        _require(set(question.dependencies).issubset(by_id), "question dependency is missing")
        _require(question.applicability in ("applicable", "not_applicable", "exempt"), "unknown question applicability")
        if question.applicability != "applicable":
            _text(question.policy_reason, "exemption policy reason")
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(question_id: str) -> None:
        _require(question_id not in visiting, "question dependency cycle")
        if question_id in done:
            return
        visiting.add(question_id)
        for dependency in by_id[question_id].dependencies:
            visit(dependency)
        visiting.remove(question_id)
        done.add(question_id)

    for question_id in ids:
        visit(question_id)
    _require(tuple(questions) == _questions(entities), "question definitions differ from the approved fixed policy")


@dataclass(frozen=True)
class ScopeContext:
    tenant_id: UUID
    run_id: UUID
    revision: int
    policy_ref: str
    principal: PrincipalScope
    member_snapshot: CheckedMemberSnapshot
    conclusion_scope: ConclusionScope
    query_scope: QueryScope
    questions: tuple[Question, ...]
    target_type: str = "explicit_set"


def initialize_scope(*, principal: TenantPrincipal, tenant_id: UUID | str, run_id: UUID | str,
                     snapshot: CheckedMemberSnapshot, window: UTCWindow, target_type: str = "explicit_set",
                     policy_ref: str = POLICY_REF, revision: int = 1,
                     previous: ScopeContext | None = None) -> ScopeContext:
    """Freeze already-checked caller inputs; never infer ownership from their text."""
    _require(isinstance(principal, TenantPrincipal), "trusted caller must supply TenantPrincipal")
    tenant, run = _uuid(tenant_id), _uuid(run_id)
    identity = PrincipalScope(frozenset(principal.tenant_ids), principal.subject, principal.delegated)
    _require(tenant in identity.tenant_ids, "requested tenant is outside principal scope")
    _require(target_type == "explicit_set", "unsupported target type")
    _require(policy_ref == POLICY_REF, "unsupported policy revision")
    _require(isinstance(window, UTCWindow) and window.end - window.start <= timedelta(minutes=5), "policy window exceeds five minutes")
    _require(isinstance(snapshot, CheckedMemberSnapshot), "checked member snapshot is required")
    _require(all(member.tenant_id == tenant for member in (*snapshot.selected, *snapshot.omitted)), "member tenant differs from principal tenant")
    _require(type(revision) is int and revision >= 1, "scope revision must be a positive integer")
    if previous is None:
        _require(revision == 1, "initial scope revision must be one")
    else:
        _require((previous.tenant_id, previous.run_id, previous.policy_ref) == (tenant, run, policy_ref)
                 and revision == previous.revision + 1, "scope revision must explicitly follow the previous snapshot")
    entities = tuple(dict.fromkeys(entity for member in snapshot.selected for entity in
                                  (EntityRef("host", member.hostname), EntityRef("ip", member.source_ip), EntityRef("ip", member.dest_ip))))
    conclusion = ConclusionScope(tuple(member.alert_id for member in snapshot.selected), entities, window)
    queries = QueryScope(snapshot.selected, window)
    questions = _questions(entities)
    validate_questions(questions, entities)
    return ScopeContext(tenant, run, revision, policy_ref, identity, snapshot, conclusion, queries, questions)


@dataclass(frozen=True)
class QueryRequest:
    tenant_id: UUID
    run_id: UUID
    scope_revision: int
    member_id: UUID
    window: UTCWindow
    fields: tuple[SourceField, ...]
    source: str = SOURCE
    capability: str = CAPABILITY
    relation: str = "checked_alert_fields"
    depth: int = 0
    limit: int = MAX_LIMIT
    origin: str = "trusted_program"  # Metadata only; model candidates get the same checks.

    def __post_init__(self) -> None:
        for name in ("tenant_id", "run_id", "member_id"):
            object.__setattr__(self, name, _uuid(getattr(self, name)))
        object.__setattr__(self, "fields", tuple(self.fields))


@dataclass(frozen=True)
class QueryAdmission:
    allowed: bool
    reason: str
    tenant_id: UUID
    run_id: UUID
    scope_revision: int
    request: QueryRequest
    policy_ref: str = POLICY_REF


def admit_query(context: ScopeContext, request: QueryRequest) -> QueryAdmission:
    """Evaluate a candidate without execution or changing conclusion membership."""
    scope = context.query_scope
    member = next((member for member in scope.members if member.alert_id == request.member_id), None)
    reason = "admitted_by_fixed_policy"
    if type(request.scope_revision) is not int or (request.tenant_id, request.run_id, request.scope_revision) != (context.tenant_id, context.run_id, context.revision):
        reason = "context_identity_mismatch"
    elif request.source not in scope.sources or request.capability not in scope.capabilities:
        reason = "source_or_capability_not_allowed"
    elif request.relation != scope.relation or type(request.depth) is not int or request.depth != 0:
        reason = "relationship_or_depth_not_allowed"
    elif type(request.limit) is not int or not 1 <= request.limit <= scope.max_limit:
        reason = "query_limit_not_allowed"
    elif not isinstance(request.window, UTCWindow) or not scope.window.contains(request.window):
        reason = "query_window_outside_scope"
    elif member is None:
        reason = "member_outside_conclusion_scope"
    elif request.fields != member.fields:
        reason = "field_provenance_or_value_mismatch"
    return QueryAdmission(reason == "admitted_by_fixed_policy", reason, context.tenant_id,
                          context.run_id, context.revision, request)
