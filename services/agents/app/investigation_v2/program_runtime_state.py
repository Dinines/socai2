"""Pure manual program-runtime state; all actual admission remains in M3.

The caller supplies an owned M1 scope, authoritative clock and frozen state.
This closed policy cannot upgrade old states or authorize IO from a plan hash.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import json
import re
from uuid import NAMESPACE_URL, UUID, uuid5

from .business_profile import BusinessProfileRequest, PROFILE_VERSION, OBJECTIVE
from .execution_state import ExecutionRejected, _state_copy, reserve, SCHEMA_VERSION
from .execution_store import canonical_json, content_hash, scope_fingerprint, scope_snapshot
from .fixed_recon import EXECUTION_STOPS
from .program_recon import COMPLETION_POLICY_REF, FACT_POLICY_REF, RESULT_SCHEMA, PREPARATION_SCHEMA
from .program_material import MATERIAL_SCHEMA, MATERIAL_POLICY_REF
from .scope import POLICY_REF
from .recon_runtime_state import _query_input

RUNTIME_VERSION = "program_alert_recon_runtime.v1"
RECON_SCHEMA = "program_recon_runtime_state.v1"
PLAN_SCHEMA = "program_recon_plan.v1"
HANDOFF_SCHEMA = "program_recon_runtime_handoff.v1"
UNADOPTED_RESULT_SCHEMA = "program_runtime_unadopted_result.v1"
SUBTASK = "program-source-observation-Q1"
_BUDGET_REJECTIONS = frozenset({"stage stopped after budget breach", "tool call limit reached",
                               "attempt ledger limit reached", "token budget exhausted", "cost budget exhausted"})


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ExecutionRejected(reason)


def policy_versions() -> dict:
    """A fresh closed combination, never selected by source prose or caller."""
    return {"execution_schema": SCHEMA_VERSION, "runtime_version": RUNTIME_VERSION, "state_schema": RECON_SCHEMA,
        "plan_schema": PLAN_SCHEMA, "material_schema": MATERIAL_SCHEMA, "material_policy_ref": MATERIAL_POLICY_REF,
        "fact_policy_ref": FACT_POLICY_REF, "completion_policy_ref": COMPLETION_POLICY_REF,
        "preparation_schema": PREPARATION_SCHEMA, "result_schema": RESULT_SCHEMA,
        "handoff_schema": HANDOFF_SCHEMA, "unadopted_result_schema": UNADOPTED_RESULT_SCHEMA}


def _expected_profile(controls: dict, scope_hash: str) -> dict:
    """Rebuild a manual alert descriptor from controlled scope, not the plan.

    Scope has no trigger field. The fixed manual policy is the authority here;
    reading a trigger from the descriptor being checked would be self-proof.
    """
    _require(controls["policy_ref"] == POLICY_REF and type(controls["revision"]) is int and controls["revision"] >= 1,
             "unsupported program scope policy or revision")
    snapshot = controls["member_snapshot"]
    _require(type(snapshot["total_members"]) is int and snapshot["total_members"] == 1
             and len(snapshot["selected"]) == 1 and not snapshot["omitted"], "program runtime requires one complete alert")
    member = snapshot["selected"][0]
    _require(canonical_json(controls["query_scope"]["members"]) == canonical_json([member])
             and controls["conclusion_scope"]["member_ids"] == [member["alert_id"]]
             and controls["conclusion_scope"]["objective"] == OBJECTIVE, "program member or objective differs from scope")
    body = {"schema": PROFILE_VERSION, "profile": "alert_recon", "profile_version": PROFILE_VERSION,
        "tenant_id": controls["tenant_id"], "run_id": controls["run_id"],
        "target": {"type": "alert", "id": member["alert_id"], "record_ref": member["record_ref"],
                   "ownership_check_ref": member["ownership_check_ref"]},
        "objective": OBJECTIVE, "policy_ref": POLICY_REF, "trigger": "manual", "scope_hash": scope_hash,
        "scope_revision": controls["revision"], "delivery_target": {"type": "alert", "id": member["alert_id"]},
        "completion_basis": "target_alert", "member_coverage": {
            "source_ref": snapshot["source_ref"], "membership_revision": None,
            "all_member_ids": [member["alert_id"]], "selected_member_ids": [member["alert_id"]],
            "omitted_members": [], "view_limitations": list(snapshot["view_limitations"]),
            "selection_covers_target": True, "investigated_members": 0, "evidence_coverage": "not_started"}}
    body["binding_ref"] = "profile:" + content_hash(canonical_json(body))
    return body


def _plan_from_controls(controls: dict, scope_hash: str) -> dict:
    profile = _expected_profile(controls, scope_hash)
    query_input = _query_input(controls)
    versions = policy_versions()
    fingerprint = content_hash(canonical_json([versions, scope_hash, query_input]))
    step = uuid5(NAMESPACE_URL, f"socai2:{controls['run_id']}:program-recon:{fingerprint}")
    plan = {"schema": PLAN_SCHEMA, "runtime_version": RUNTIME_VERSION, "completion_policy_ref": COMPLETION_POLICY_REF,
        "policy_versions": versions, "tenant_id": controls["tenant_id"], "run_id": controls["run_id"],
        "scope_hash": scope_hash, "business_profile": profile, "query_input": query_input,
        "query_fingerprint": fingerprint, "subtask_id": SUBTASK, "step_id": str(step),
        "attempt_id": str(uuid5(step, "attempt-1"))}
    plan["plan_ref"] = "program-recon-plan:" + content_hash(canonical_json(plan))
    return json.loads(canonical_json(plan))


def make_program_recon_plan(request: BusinessProfileRequest) -> dict:
    _require(isinstance(request, BusinessProfileRequest), "checked business request required")
    request = replace(request)
    _require(request.profile == "alert_recon" and request.trigger == "manual", "program runtime requires manual alert profile")
    controls, _ = scope_snapshot(request.context)
    plan = _plan_from_controls(controls, scope_fingerprint(request.context))
    _require(canonical_json(plan["business_profile"]) == canonical_json(request.descriptor), "program profile differs from checked scope")
    return plan


def install_program_recon(state: dict, request: BusinessProfileRequest, *, now: datetime) -> dict:
    result, _ = _state_copy(state, now)
    _require("runtime_version" not in result and "recon" not in result, "runtime already installed; reset forbidden")
    _require(not result["attempts"], "runtime must be frozen before attempts")
    plan = make_program_recon_plan(request)
    _require((plan["tenant_id"], plan["run_id"], plan["scope_hash"])
             == (result["tenant_id"], result["run_id"], result["scope_hash"]), "runtime scope differs from stage")
    result["runtime_version"] = RUNTIME_VERSION
    result["recon"] = {"schema": RECON_SCHEMA, "plan": plan, "phase": "ready",
                       "claimed_at": None, "stop_reason": None, "handoff": None}
    return result


def _runtime_copy(state: dict, now: datetime) -> tuple[dict, datetime]:
    result, moment = _state_copy(state, now)
    recon = result.get("recon", {})
    _require(result.get("runtime_version") == RUNTIME_VERSION and recon.get("schema") == RECON_SCHEMA,
             "unsupported managed runtime")
    _require(recon.get("phase") in {"ready", "claimed", "blocked", "stopped"}, "invalid runtime phase")
    stop = recon.get("stop_reason")
    _require(stop is None or isinstance(stop, str) and stop in EXECUTION_STOPS, "invalid recorded stop")
    _require(recon["phase"] != "blocked" or stop is not None, "blocked runtime requires stop reason")
    _require(recon["phase"] not in {"ready", "claimed"} or stop is None, "active runtime cannot carry stop reason")
    _require(recon["phase"] == "stopped" or recon.get("handoff") is None, "unfinished runtime has handoff")
    if recon["phase"] == "stopped":
        handoff = recon.get("handoff")
        _require(isinstance(handoff, dict) and set(handoff) == {"artifact_id", "sha256"}, "stopped runtime requires handoff reference")
        try:
            valid_id = isinstance(handoff["artifact_id"], str) and UUID(handoff["artifact_id"]).int != 0
        except (ValueError, TypeError, AttributeError):
            valid_id = False
        _require(valid_id and isinstance(handoff["sha256"], str)
                 and re.fullmatch(r"[0-9a-f]{64}", handoff["sha256"]), "stopped handoff reference invalid")
    plan = recon["plan"]
    _require(isinstance(plan, dict), "program runtime plan required")
    # Exact reconstruction also rejects unknown keys and self-consistent hash
    # rewrites of policy versions, trigger, parameters and dispatch identities.
    expected = _plan_from_controls(result["scope"], result["scope_hash"])
    _require(canonical_json(plan) == canonical_json(expected), "program plan differs from closed frozen policy")
    return result, moment


def claim_program_recon(state: dict, *, now: datetime) -> tuple[dict, dict]:
    result, moment = _runtime_copy(state, now)
    recon, plan = result["recon"], result["recon"]["plan"]
    action = {"claimed": "in_progress_or_interrupted", "blocked": "finalize_blocked", "stopped": "read_handoff"}
    decision = {"action": action.get(recon["phase"]), "needs_commit": False,
                "external_call_authorized": False, "m3_reservation_required": False, "plan_ref": plan["plan_ref"]}
    if recon["phase"] != "ready":
        return result, decision
    _require(not result["attempts"], "unclaimed runtime already has attempts")
    stop = "unknown_attempt" if result["run_total"]["unknown_calls"] or result["stage_usage"]["unsettled_attempts"] else None
    if stop is None:
        try:
            # This disposable copy validates actual M3 rules; it is not a reservation.
            reserve(result, step_id=plan["step_id"], attempt_id=plan["attempt_id"], subtask_id=SUBTASK,
                    question_id="Q1", kind="tool", reserve_tokens=0, reserve_cost_microusd=0,
                    input_snapshot_ref="preflight-only:" + plan["plan_ref"],
                    input_hash=content_hash(canonical_json(plan["query_input"])), now=moment)
        except ExecutionRejected as exc:
            reason = str(exc)
            if reason == "deadline reached": stop = "deadline"
            elif reason in _BUDGET_REJECTIONS: stop = "budget_limit"
            elif reason == "unsettled limit reached": stop = "unknown_attempt"
            else: raise
    recon["phase"] = "blocked" if stop else "claimed"
    recon["stop_reason"] = stop
    recon["claimed_at"] = moment.isoformat(timespec="microseconds")
    result["updated_at"] = recon["claimed_at"]
    decision.update(action="finalize_blocked" if stop else "dispatch_after_commit", needs_commit=True,
                    m3_reservation_required=stop is None)
    return result, decision


def validate_program_reservation(state: dict, *, input_data: dict, request: dict, now: datetime) -> None:
    result, _ = _runtime_copy(state, now)
    recon, plan = result["recon"], result["recon"]["plan"]
    _require(recon["phase"] == "claimed", "managed runtime is not dispatchable")
    expected = {"step_id": plan["step_id"], "attempt_id": plan["attempt_id"], "subtask_id": SUBTASK,
                "question_id": "Q1", "kind": "tool", "reserve_tokens": 0, "reserve_cost_microusd": 0,
                "retry_of": None}
    actual = dict(request)
    for key in ("step_id", "attempt_id"):
        if isinstance(actual.get(key), UUID): actual[key] = str(actual[key])
    actual.setdefault("retry_of", None)
    _require(canonical_json(actual) == canonical_json(expected), "reservation differs from fixed runtime plan")
    _require(canonical_json(input_data) == canonical_json(plan["query_input"]), "input differs from fixed runtime query")


def observed_program_stop(state: dict, *, now: datetime) -> str | None:
    result, moment = _runtime_copy(state, now)
    if result["recon"]["phase"] == "blocked": return result["recon"]["stop_reason"]
    if result["run_total"]["unknown_calls"] or result["stage_usage"]["unsettled_attempts"]: return "unknown_attempt"
    if result["budget_breached"]: return "budget_limit"
    if moment >= datetime.fromisoformat(result["limits"]["deadline"]): return "deadline"
    return None  # A fully used call cap is not itself an after-call failure.


def cancel_program_recon(state: dict, *, now: datetime) -> dict:
    result, moment = _runtime_copy(state, now)
    _require(result["recon"]["phase"] in {"ready", "claimed"}, "runtime cannot be cancelled in this phase")
    result["recon"].update(phase="blocked", stop_reason="cancelled")
    result["updated_at"] = moment.isoformat(timespec="microseconds")
    return result


def finish_program_recon(state: dict, *, artifact_id: UUID | str, body_hash: str,
                 execution_stop: str | None, now: datetime) -> tuple[dict, bool]:
    result, moment = _runtime_copy(state, now)
    _require(isinstance(artifact_id, (str, UUID)) and UUID(str(artifact_id)).int != 0, "handoff artifact UUID required")
    _require(isinstance(body_hash, str) and re.fullmatch(r"[0-9a-f]{64}", body_hash) is not None, "handoff hash required")
    _require(execution_stop is None or isinstance(execution_stop, str) and execution_stop in EXECUTION_STOPS,
             "unsupported runtime stop")
    recon, plan = result["recon"], result["recon"]["plan"]
    handoff = {"artifact_id": str(UUID(str(artifact_id))), "sha256": body_hash}
    if recon["phase"] == "stopped":
        _require(recon["handoff"] == handoff and recon["stop_reason"] == execution_stop, "handoff overwrite forbidden")
        return result, True
    observed = observed_program_stop(result, now=moment)
    _require(execution_stop == observed or execution_stop == "retention_gap" and observed in {None, "unknown_attempt"},
             "runtime stop differs from observed state")
    _require(recon["phase"] in {"blocked", "claimed"}, "runtime must be claimed before finishing")
    if recon["phase"] == "blocked":
        _require(execution_stop == recon["stop_reason"], "recorded stop cannot be replaced")
    attempt = result["attempts"].get(plan["attempt_id"])
    if recon["phase"] == "claimed":
        _require(attempt is not None or execution_stop in {"deadline", "cancelled", "unknown_attempt", "retention_gap"},
                 "missing actual M3 attempt")
        if attempt is not None and attempt["unsettled"]:
            _require(execution_stop in {"unknown_attempt", "retention_gap", "cancelled"}, "unsettled call requires explicit stop")
    recon.update(phase="stopped", handoff=handoff, stop_reason=execution_stop,
                 stopped_at=moment.isoformat(timespec="microseconds"))
    result["updated_at"] = recon["stopped_at"]
    return result, False
