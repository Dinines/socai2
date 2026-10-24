"""Pure M3.1 accounting for one owned investigation stage.

The caller authenticates the scope and owns durable begin/reserve/settle
transactions. These functions perform no IO and do not prove persistence or
freshness. ``now`` must come from the store's authoritative clock; tests inject
it. A reservation authorizes nothing until its transaction has committed.
All returned values are detached JSON data. There is no automatic retry,
reconciliation of unknown outcomes, or reset of an existing stage.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

SCHEMA_VERSION = "investigation_execution.v1"
EXECUTOR_VERSION = "unified_executor.v1"
POLICY_REF = "network_observation.v1"
MAX_ATTEMPTS = 64


class ExecutionRejected(ValueError):
    """An invalid contract or inadmissible next attempt (no state change)."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ExecutionRejected(message)


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    _require(type(value) is int and value >= minimum, f"{name} must be an integer >= {minimum}")
    return value


def _text(value: Any, name: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"{name} is required")
    return value


def _uuid(value: Any, name: str) -> str:
    try:
        _require(isinstance(value, (str, UUID)), f"{name} must be a UUID")
        parsed = UUID(str(value))
        _require(parsed.int != 0, f"{name} must not be nil")
        return str(parsed)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ExecutionRejected(f"{name} must be a nonnil UUID") from exc


def _time(value: Any, name: str) -> datetime:
    _require(isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None,
             f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="microseconds")


def _hash(value: Any) -> str:
    _require(isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
             "input_hash must be a lowercase SHA256 hex digest")
    return value


def _copy(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (ValueError, TypeError) as exc:
        raise ExecutionRejected("state and scope must be JSON-safe") from exc


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BudgetLimits:
    max_model_calls: int
    max_tool_calls: int
    max_tokens: int
    max_cost_microusd: int | None
    max_unsettled: int
    deadline: datetime
    config_ref: str
    legacy_model_limit_mapping: str

    def __post_init__(self) -> None:
        for name in ("max_model_calls", "max_tool_calls", "max_tokens"):
            _integer(getattr(self, name), name)
        if self.max_cost_microusd is not None:
            _integer(self.max_cost_microusd, "max_cost_microusd")
        _integer(self.max_unsettled, "max_unsettled", 1)
        _require(self.max_model_calls + self.max_tool_calls <= MAX_ATTEMPTS,
                 "combined call limits must be <= 64")
        _require(self.max_unsettled <= MAX_ATTEMPTS, "max_unsettled must be <= 64")
        object.__setattr__(self, "deadline", _time(self.deadline, "deadline"))
        _text(self.config_ref, "config_ref")
        _text(self.legacy_model_limit_mapping, "legacy_model_limit_mapping")


@dataclass(frozen=True)
class OpeningUsage:
    model_calls: int
    known_tokens: int
    known_cost_microusd: int | None
    unknown_calls: int
    unpriced_calls: int
    source_ref: str

    def __post_init__(self) -> None:
        for name in ("model_calls", "known_tokens", "unknown_calls", "unpriced_calls"):
            _integer(getattr(self, name), name)
        if self.known_cost_microusd is not None:
            _integer(self.known_cost_microusd, "known_cost_microusd")
        _require(self.unknown_calls <= self.model_calls and self.unpriced_calls <= self.model_calls,
                 "opening unknown/unpriced calls must belong to opening model attempts")
        _text(self.source_ref, "source_ref")


def stage_id_for(tenant_id: str | UUID, run_id: str | UUID) -> str:
    tenant = _uuid(tenant_id, "tenant_id")
    run = _uuid(run_id, "run_id")
    return str(uuid5(NAMESPACE_URL, f"socai2:{tenant}:{run}:investigation_stage.v1"))


def _summarize(state: dict) -> None:
    attempts = list(state["attempts"].values())
    stage = {
        "model_calls": sum(a["kind"] == "model" for a in attempts),
        "tool_calls": sum(a["kind"] == "tool" for a in attempts),
        "known_tokens": sum(a["actual_tokens"] for a in attempts if a["actual_tokens"] is not None),
        "reserved_tokens": sum(a["remaining_tokens"] for a in attempts),
        "known_cost_microusd": sum(a["actual_cost_microusd"] for a in attempts if a["actual_cost_microusd"] is not None),
        "reserved_cost_microusd": sum(a["remaining_cost_microusd"] or 0 for a in attempts),
        "unsettled_attempts": sum(a["unsettled"] for a in attempts),
        "unknown_attempts": sum(a["status"] == "unknown" or (a["status"] == "responded" and a["unsettled"]) for a in attempts),
        "unpriced_attempts": sum(a["status"] == "responded" and a["actual_cost_microusd"] is None for a in attempts),
    }
    stage["tokens_complete"] = all(a["actual_tokens"] is not None for a in attempts)
    stage["cost_complete"] = all(a["actual_cost_microusd"] is not None for a in attempts)
    stage["total_tokens"] = stage["known_tokens"] if stage["tokens_complete"] else None
    stage["total_cost_microusd"] = stage["known_cost_microusd"] if stage["cost_complete"] else None
    state["stage_usage"] = stage
    opening = state["opening_usage"]
    run = {
        "model_calls": opening["model_calls"] + stage["model_calls"],
        "tool_calls": stage["tool_calls"],
        "known_tokens": opening["known_tokens"] + stage["known_tokens"],
        "known_cost_microusd": (opening["known_cost_microusd"] or 0) + stage["known_cost_microusd"],
        "unknown_calls": opening["unknown_calls"] + stage["unknown_attempts"],
        "unpriced_calls": opening["unpriced_calls"] + stage["unpriced_attempts"],
        "unsettled_attempts": stage["unsettled_attempts"],
        "tokens_complete": opening["unknown_calls"] == 0 and stage["tokens_complete"],
        "cost_complete": opening["known_cost_microusd"] is not None and opening["unknown_calls"] == 0
                         and opening["unpriced_calls"] == 0 and stage["cost_complete"],
    }
    run["total_tokens"] = run["known_tokens"] if run["tokens_complete"] else None
    run["total_cost_microusd"] = run["known_cost_microusd"] if run["cost_complete"] else None
    state["run_total"] = run


def initial_state(*, scope: dict, input_snapshot_ref: str, input_hash: str,
                  limits: BudgetLimits, opening: OpeningUsage, executor_id: str | UUID,
                  now: datetime) -> dict:
    """Construct only; the store must independently prove that begin is fresh."""
    _require(type(limits) is BudgetLimits and type(opening) is OpeningUsage, "typed limits and opening usage required")
    frozen_scope = _copy(scope)
    _require(isinstance(frozen_scope, dict), "scope must be an object")
    tenant = _uuid(frozen_scope.get("tenant_id"), "scope tenant_id")
    run = _uuid(frozen_scope.get("run_id"), "scope run_id")
    revision = _integer(frozen_scope.get("revision"), "scope revision", 1)
    _require(frozen_scope.get("policy_ref") == POLICY_REF, "unsupported scope policy")
    questions = frozen_scope.get("questions")
    _require(isinstance(questions, list) and all(isinstance(q, dict) for q in questions), "scope questions required")
    ids = [q.get("question_id") for q in questions]
    _require(set(ids) == {"Q1", "Q2", "Q3a", "Q3b", "Q4", "Q5"} and len(ids) == 6,
             "scope must preserve the six M1 questions")
    started = _time(now, "now")
    _require(started < limits.deadline, "deadline reached")
    policy = asdict(limits)
    policy["deadline"] = _iso(limits.deadline)
    policy["currency"] = "USD"
    state = {
        "schema_version": SCHEMA_VERSION, "executor_version": EXECUTOR_VERSION,
        "budget_scope": "investigation_stage", "stage_id": stage_id_for(tenant, run),
        "tenant_id": tenant, "run_id": run, "executor_id": _uuid(executor_id, "executor_id"),
        "scope_revision": revision, "policy_ref": POLICY_REF,
        "scope": frozen_scope, "scope_hash": _fingerprint(frozen_scope),
        "input_snapshot_ref": _text(input_snapshot_ref, "input_snapshot_ref"), "input_hash": _hash(input_hash),
        "limits": policy, "opening_usage": asdict(opening), "attempts": {},
        "budget_breached": False, "breach_reasons": [],
        "started_at": _iso(started), "updated_at": _iso(started),
    }
    _summarize(state)
    return state


def _state_copy(state: dict, now: datetime) -> tuple[dict, datetime]:
    result = _copy(state)
    _require(isinstance(result, dict) and result.get("schema_version") == SCHEMA_VERSION, "unsupported state")
    _require(result["stage_id"] == stage_id_for(result["tenant_id"], result["run_id"]), "stage identity mismatch")
    _uuid(result["executor_id"], "executor_id")
    scope = result["scope"]
    _require(_fingerprint(scope) == result["scope_hash"] and scope["revision"] == result["scope_revision"]
             and scope["policy_ref"] == result["policy_ref"] == POLICY_REF
             and str(scope["tenant_id"]) == result["tenant_id"] and str(scope["run_id"]) == result["run_id"],
             "frozen scope mismatch")
    moment = _time(now, "now")
    _require(moment >= datetime.fromisoformat(result["updated_at"]), "time must not go backwards")
    _summarize(result)
    return result, moment


def reserve(state: dict, *, step_id: str | UUID, attempt_id: str | UUID, subtask_id: str,
            question_id: str, kind: str, reserve_tokens: int, reserve_cost_microusd: int | None,
            input_snapshot_ref: str, input_hash: str, retry_of: str | UUID | None = None,
            now: datetime) -> tuple[dict, dict]:
    result, moment = _state_copy(state, now)
    limits, usage = result["limits"], result["stage_usage"]
    _require(not result["budget_breached"], "stage stopped after budget breach")
    _require(moment < datetime.fromisoformat(limits["deadline"]), "deadline reached")
    step, attempt = _uuid(step_id, "step_id"), _uuid(attempt_id, "attempt_id")
    _require(attempt not in result["attempts"], "attempt already exists")
    _text(subtask_id, "subtask_id")
    _require(question_id in [q["question_id"] for q in result["scope"]["questions"]], "question outside scope")
    _require(kind in ("model", "tool"), "kind must be model or tool")
    _integer(reserve_tokens, "reserve_tokens")
    _require(reserve_tokens > 0 if kind == "model" else reserve_tokens == 0,
             "model requires token reservation; tool tokens must be zero")
    if reserve_cost_microusd is not None:
        _integer(reserve_cost_microusd, "reserve_cost_microusd")
    _require(limits["max_cost_microusd"] is None or reserve_cost_microusd is not None,
             "cost-capped attempts require a cost reservation")
    _text(input_snapshot_ref, "input_snapshot_ref")
    _hash(input_hash)
    earlier = [a for a in result["attempts"].values() if a["step_id"] == step]
    previous = max(earlier, key=lambda a: a["attempt_number"]) if earlier else None
    retry = _uuid(retry_of, "retry_of") if retry_of is not None else None
    if previous:
        _require(retry == previous["attempt_id"], "existing step requires explicit retry of latest attempt")
        _require(not previous["unsettled"], "unsettled attempt cannot be retried")
        _require((kind, subtask_id, question_id) == (previous["kind"], previous["subtask_id"], previous["question_id"]),
                 "retry must preserve logical step identity")
    else:
        _require(retry is None, "first step attempt cannot be a retry")
    _require(usage[f"{kind}_calls"] < limits[f"max_{kind}_calls"], f"{kind} call limit reached")
    _require(len(result["attempts"]) < MAX_ATTEMPTS, "attempt ledger limit reached")
    _require(usage["unsettled_attempts"] < limits["max_unsettled"], "unsettled limit reached")
    _require(usage["known_tokens"] + usage["reserved_tokens"] + reserve_tokens <= limits["max_tokens"],
             "token budget exhausted")
    if limits["max_cost_microusd"] is not None:
        _require(usage["known_cost_microusd"] + usage["reserved_cost_microusd"] + reserve_cost_microusd
                 <= limits["max_cost_microusd"], "cost budget exhausted")
    receipt = {
        "attempt_id": attempt, "step_id": step, "attempt_number": len(earlier) + 1,
        "subtask_id": subtask_id, "question_id": question_id, "kind": kind, "retry_of": retry,
        "input_snapshot_ref": input_snapshot_ref, "input_hash": input_hash,
        "status": "reserved", "unsettled": True,
        "reserve_tokens": reserve_tokens, "reserve_cost_microusd": reserve_cost_microusd,
        "remaining_tokens": reserve_tokens, "remaining_cost_microusd": reserve_cost_microusd,
        "actual_tokens": None, "actual_cost_microusd": None, "usage_source_ref": None,
        "reserved_at": _iso(moment), "settled_at": None,
    }
    result["attempts"][attempt] = receipt
    result["updated_at"] = _iso(moment)
    _summarize(result)
    return result, _copy(receipt)


def settle(state: dict, *, attempt_id: str | UUID, outcome: str, actual_tokens: int | None,
           actual_cost_microusd: int | None, usage_source_ref: str,
           now: datetime) -> tuple[dict, dict]:
    """Retain late actual usage, even if it exceeds an estimate or deadline.

    The store handles idempotent completion fingerprints. A second settlement
    here is rejected, including an attempted rewrite of an unknown outcome.
    """
    result, moment = _state_copy(state, now)
    attempt = _uuid(attempt_id, "attempt_id")
    _require(attempt in result["attempts"], "unknown attempt")
    receipt = result["attempts"][attempt]
    _require(receipt["status"] == "reserved", "attempt already completed")
    _require(outcome in ("responded", "no_request", "unknown"), "unsupported outcome")
    _text(usage_source_ref, "usage_source_ref")
    for name, value in (("actual_tokens", actual_tokens), ("actual_cost_microusd", actual_cost_microusd)):
        if value is not None:
            _integer(value, name)
    if outcome == "unknown":
        _require(actual_tokens is None and actual_cost_microusd is None, "unknown outcome cannot claim actual usage")
    elif outcome == "no_request":
        _require(actual_tokens in (None, 0) and actual_cost_microusd in (None, 0), "no request cannot consume usage")
        actual_tokens = actual_cost_microusd = 0
    else:
        _require(receipt["kind"] != "tool" or actual_tokens in (None, 0), "tool cannot claim model tokens")
    receipt.update(status=outcome, actual_tokens=actual_tokens, actual_cost_microusd=actual_cost_microusd,
                   usage_source_ref=usage_source_ref, settled_at=_iso(moment))
    if outcome != "unknown":
        if actual_tokens is not None:
            receipt["remaining_tokens"] = 0
        if actual_cost_microusd is not None or result["limits"]["max_cost_microusd"] is None:
            receipt["remaining_cost_microusd"] = 0
        receipt["unsettled"] = actual_tokens is None or (actual_cost_microusd is None and result["limits"]["max_cost_microusd"] is not None)
    reasons = []
    if actual_tokens is not None and actual_tokens > receipt["reserve_tokens"]:
        reasons.append(f"{attempt}:tokens_exceeded_reservation")
    if actual_cost_microusd is not None and receipt["reserve_cost_microusd"] is not None and actual_cost_microusd > receipt["reserve_cost_microusd"]:
        reasons.append(f"{attempt}:cost_exceeded_reservation")
    result["updated_at"] = _iso(moment)
    _summarize(result)
    if result["stage_usage"]["known_tokens"] > result["limits"]["max_tokens"]:
        reasons.append("stage:tokens_exceeded_limit")
    cap = result["limits"]["max_cost_microusd"]
    if cap is not None and result["stage_usage"]["known_cost_microusd"] > cap:
        reasons.append("stage:cost_exceeded_limit")
    result["breach_reasons"] = list(dict.fromkeys(result["breach_reasons"] + reasons))
    result["budget_breached"] = bool(result["breach_reasons"])
    return result, _copy(receipt)
