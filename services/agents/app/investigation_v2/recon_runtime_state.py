"""M6.2a pure fixed-runtime controls; commits and M3 admission remain mandatory."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import json
import re
from uuid import NAMESPACE_URL, UUID, uuid5

from .business_profile import BusinessProfileRequest
from .execution_state import ExecutionRejected, _state_copy, reserve
from .execution_store import canonical_json, content_hash, scope_fingerprint, scope_snapshot
from .fixed_recon import COMPLETION_POLICY_REF, EXECUTION_STOPS

RUNTIME_VERSION = "fixed_alert_recon_runtime.v1"
RECON_SCHEMA = "fixed_recon_runtime_state.v1"
SUBTASK = "fixed-source-observation-Q1"
_BUDGET_REJECTIONS = frozenset({"stage stopped after budget breach", "tool call limit reached",
                               "attempt ledger limit reached", "token budget exhausted", "cost budget exhausted"})


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ExecutionRejected(reason)


def _query_input(controls: dict) -> dict:
    members = controls["query_scope"]["members"]
    _require(len(members) == 1, "fixed runtime requires one member")
    member = members[0]
    window = controls["conclusion_scope"]["window"]
    parameters = {key: member[key] for key in ("hostname", "source_ip", "dest_ip", "dst_port", "protocol")}
    parameters.update(start=window["start"], end=window["end"], limit=controls["query_scope"]["max_limit"])
    return {"tool": "activity_records", "member_id": member["alert_id"], "question_id": "Q1", "parameters": parameters}


def make_recon_plan(request: BusinessProfileRequest) -> dict:
    _require(isinstance(request, BusinessProfileRequest), "checked business request required")
    request = replace(request)
    _require(request.profile == "alert_recon", "fixed runtime requires alert profile")
    controls, _ = scope_snapshot(request.context)
    query_input = _query_input(controls)
    scope_hash = scope_fingerprint(request.context)
    fingerprint = content_hash(canonical_json([scope_hash, query_input]))
    step = uuid5(NAMESPACE_URL, f"socai2:{request.context.run_id}:fixed-recon:{fingerprint}")
    plan = {"runtime_version": RUNTIME_VERSION, "completion_policy_ref": COMPLETION_POLICY_REF,
            "tenant_id": str(request.context.tenant_id), "run_id": str(request.context.run_id),
            "scope_hash": scope_hash, "business_profile": request.descriptor,
            "query_input": query_input, "query_fingerprint": fingerprint, "subtask_id": SUBTASK,
            "step_id": str(step), "attempt_id": str(uuid5(step, "attempt-1"))}
    plan["plan_ref"] = "fixed-recon-plan:" + content_hash(canonical_json(plan))
    return json.loads(canonical_json(plan))


def install_recon(state: dict, request: BusinessProfileRequest, *, now: datetime) -> dict:
    result, _ = _state_copy(state, now)
    _require("runtime_version" not in result and "recon" not in result, "runtime already installed; reset forbidden")
    _require(not result["attempts"], "runtime must be frozen before attempts")
    plan = make_recon_plan(request)
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
    plan = recon["plan"]
    body = {key: value for key, value in plan.items() if key != "plan_ref"}
    _require(plan["plan_ref"] == "fixed-recon-plan:" + content_hash(canonical_json(body)), "runtime plan hash mismatch")
    profile = plan["business_profile"]
    profile_body = {key: value for key, value in profile.items() if key != "binding_ref"}
    _require(profile["binding_ref"] == "profile:" + content_hash(canonical_json(profile_body)), "runtime profile hash mismatch")
    _require(plan["runtime_version"] == RUNTIME_VERSION and plan["completion_policy_ref"] == COMPLETION_POLICY_REF,
             "runtime policy version mismatch")
    _require((plan["tenant_id"], plan["run_id"], plan["scope_hash"])
             == (result["tenant_id"], result["run_id"], result["scope_hash"])
             and profile["scope_hash"] == result["scope_hash"], "managed scope mismatch")
    expected = _query_input(result["scope"])
    _require((profile["tenant_id"], profile["run_id"], profile["profile"], profile["target"]["type"], profile["target"]["id"])
             == (result["tenant_id"], result["run_id"], "alert_recon", "alert", expected["member_id"]),
             "managed business target mismatch")
    _require(canonical_json(plan["query_input"]) == canonical_json(expected), "managed query differs from frozen scope")
    fingerprint = content_hash(canonical_json([result["scope_hash"], expected]))
    step = uuid5(NAMESPACE_URL, f"socai2:{result['run_id']}:fixed-recon:{fingerprint}")
    _require(plan["query_fingerprint"] == fingerprint and plan["step_id"] == str(step)
             and plan["attempt_id"] == str(uuid5(step, "attempt-1")) and plan["subtask_id"] == SUBTASK,
             "managed dispatch identity mismatch")
    return result, moment


def claim_recon(state: dict, *, now: datetime) -> tuple[dict, dict]:
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


def validate_recon_reservation(state: dict, *, input_data: dict, request: dict, now: datetime) -> None:
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


def observed_recon_stop(state: dict, *, now: datetime) -> str | None:
    result, moment = _runtime_copy(state, now)
    if result["recon"]["phase"] == "blocked": return result["recon"]["stop_reason"]
    if result["run_total"]["unknown_calls"] or result["stage_usage"]["unsettled_attempts"]: return "unknown_attempt"
    if result["budget_breached"]: return "budget_limit"
    if moment >= datetime.fromisoformat(result["limits"]["deadline"]): return "deadline"
    return None  # A fully used call cap is not itself an after-call failure.


def cancel_recon(state: dict, *, now: datetime) -> dict:
    result, moment = _runtime_copy(state, now)
    _require(result["recon"]["phase"] in {"ready", "claimed"}, "runtime cannot be cancelled in this phase")
    result["recon"].update(phase="blocked", stop_reason="cancelled")
    result["updated_at"] = moment.isoformat(timespec="microseconds")
    return result


def finish_recon(state: dict, *, artifact_id: UUID | str, body_hash: str,
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
    observed = observed_recon_stop(result, now=moment)
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
