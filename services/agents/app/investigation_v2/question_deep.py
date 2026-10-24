"""M5.1 pure task/query contracts for one scoped source-record question.

No I/O, model invocation, stage creation, budget reset, or final publication.
The program supplies the checked parent scope and subtask identity. Model
queries remain proposals until the original M1/M2 policy admits their values.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any
from uuid import UUID, uuid5, NAMESPACE_URL

from app.investigation_v2.activity_records import _ALLOWED, _FILTERS, _REQUIRED, _time
from .execution_store import canonical_json, content_hash, scope_fingerprint
from .network_identity import same_network_filter
from .scope import CAPABILITY, POLICY_REF, QueryRequest, ScopeContext, UTCWindow, admit_query

MAX_QUERIES = 1
MAX_MODEL_ROUNDS = 2
_SUBTASK = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")


class DeepRequestRejected(ValueError):
    pass


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise DeepRequestRejected(reason)


@dataclass(frozen=True)
class QuestionTask:
    context: ScopeContext
    question_id: str
    member_id: UUID
    subtask_key: str

    def __post_init__(self) -> None:
        context = self.context
        _require(isinstance(context, ScopeContext) and context.policy_ref == POLICY_REF,
                 "checked_parent_scope_required")
        _require(context.tenant_id in context.principal.tenant_ids, "parent_principal_mismatch")
        _require(self.question_id == "Q1", "first_deep_policy_supports_Q1_only")
        question = next((q for q in context.questions if q.question_id == self.question_id), None)
        _require(question is not None and question.applicability == "applicable"
                 and CAPABILITY in question.allowed_capabilities, "question_capability_not_allowed")
        try:
            member_id = UUID(str(self.member_id))
        except (ValueError, TypeError, AttributeError):
            raise DeepRequestRejected("invalid_member_identity") from None
        object.__setattr__(self, "member_id", member_id)
        member = next((m for m in context.query_scope.members if m.alert_id == member_id), None)
        _require(member is not None and member_id in context.conclusion_scope.member_ids,
                 "member_outside_parent_scope")
        _require(member.tenant_id == context.tenant_id, "member_tenant_mismatch")
        entities = {(e.kind, e.value) for e in question.entities}
        _require({("host", member.hostname), ("ip", member.source_ip), ("ip", member.dest_ip)} <= entities,
                 "member_outside_question_scope")
        _require(isinstance(self.subtask_key, str) and bool(_SUBTASK.fullmatch(self.subtask_key)),
                 "invalid_program_subtask_key")

    @property
    def task_id(self) -> UUID:
        return uuid5(NAMESPACE_URL, canonical_json(["question-deep.v1", scope_fingerprint(self.context),
                                                  self.question_id, str(self.member_id), self.subtask_key]))

    @property
    def member(self):
        return next(m for m in self.context.query_scope.members if m.alert_id == self.member_id)

    @property
    def query_defaults(self) -> dict:
        return {**{key: getattr(self.member, key) for key in _FILTERS},
                "start": self.context.query_scope.window.start.isoformat(),
                "end": self.context.query_scope.window.end.isoformat(),
                "limit": self.context.query_scope.max_limit}

    @property
    def descriptor(self) -> dict:
        question = next(q for q in self.context.questions if q.question_id == self.question_id)
        body = {"task_id": str(self.task_id), "question": self.question_id, "purpose": question.purpose,
                "capability": CAPABILITY, "approved_query_defaults": self.query_defaults,
                "required_parameters": sorted(_REQUIRED), "optional_parameters": ["limit"],
                "max_queries": MAX_QUERIES, "max_model_rounds": MAX_MODEL_ROUNDS,
                "scope_hash": scope_fingerprint(self.context),
                "scope_readiness": "not_evaluated", "overall_assessment_allowed": False}
        return json.loads(canonical_json(body, max_bytes=8 * 1024))


@dataclass(frozen=True)
class AdmittedDeepQuery:
    canonical_doc: str

    @property
    def parameters(self) -> dict:
        return json.loads(self.canonical_doc)["parameters"]

    @property
    def fingerprint(self) -> str:
        return json.loads(self.canonical_doc)["query_fingerprint"]

    @property
    def task_id(self) -> UUID:
        return UUID(json.loads(self.canonical_doc)["task_id"])


def admit_deep_query(task: QuestionTask, proposal: Any, *, seen_queries: frozenset[str] = frozenset()) -> AdmittedDeepQuery:
    """Validate a model proposal without a tool call or a mutation of history.

    The owner supplies observed query fingerprints. Rephrasing a rationale,
    alternate representations of the same instant and the default row limit
    cannot evade duplicate-query checks. Rejections never echo input values.
    """
    _require(isinstance(task, QuestionTask), "program_question_task_required")
    _require(type(seen_queries) is frozenset and all(isinstance(x, str) and _HASH.fullmatch(x) for x in seen_queries),
             "invalid_program_query_history")
    _require(isinstance(proposal, dict) and set(proposal) == {"action", "tool", "parameters", "reason"},
             "query_proposal_shape")
    _require(proposal["action"] == "query" and proposal["tool"] == CAPABILITY, "query_capability_not_allowed")
    _require(isinstance(proposal["reason"], str) and bool(proposal["reason"].strip())
             and len(proposal["reason"].encode("utf-8")) <= 1024, "query_reason_limit")
    args = proposal["parameters"]
    _require(isinstance(args, dict) and _REQUIRED <= args.keys() and args.keys() <= _ALLOWED,
             "missing_or_forbidden_query_arguments")
    _require(all(same_network_filter(key, args[key], getattr(task.member, key))
                 for key in _FILTERS), "query_filter_has_no_provenance")
    try:
        window = UTCWindow(_time(args["start"]), _time(args["end"]))
    except (ValueError, TypeError):
        raise DeepRequestRejected("invalid_absolute_query_window") from None
    request = QueryRequest(task.context.tenant_id, task.context.run_id, task.context.revision,
                           task.member_id, window, task.member.fields,
                           limit=args.get("limit", task.context.query_scope.max_limit), origin="model_query_proposal")
    admission = admit_query(task.context, request)
    _require(admission.allowed, admission.reason)
    parameters = {**{key: getattr(task.member, key) for key in _FILTERS}, "start": window.start.isoformat(),
                  "end": window.end.isoformat(), "limit": request.limit}
    signature = content_hash(canonical_json([scope_fingerprint(task.context), task.question_id,
                                           str(task.member_id), CAPABILITY, parameters]))
    _require(signature not in seen_queries, "duplicate_query")
    return AdmittedDeepQuery(canonical_json({"task_id": str(task.task_id), "question": task.question_id,
                                             "tool": CAPABILITY, "parameters": parameters,
                                             "query_fingerprint": signature, "model_assessed_reason": proposal["reason"],
                                             "tenant_id": str(task.context.tenant_id), "run_id": str(task.context.run_id),
                                             "scope_revision": task.context.revision}, max_bytes=16 * 1024))
