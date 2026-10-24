"""Pure new manual program start intent; never upgrades an old operation.

Actual authentication, permissions, owned retained artifacts and atomic Run
admission belong to callers. No live deadline, persistence or dispatch here.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
import json
from uuid import NAMESPACE_URL, UUID, uuid5

from .business_profile import OBJECTIVE, PROFILE_VERSION
from .execution_state import ExecutionRejected
from .execution_store import canonical_json, content_hash
from .program_recon import COMPLETION_POLICY_REF
from .program_runtime_state import RUNTIME_VERSION, policy_versions
from .scope import POLICY_REF, TenantPrincipal, UTCWindow
from .start_contract import (StartBudgetPolicy, BUDGET_SCHEMA, OPERATION_NAMESPACE,
                             INTENT_SCHEMA as OLD_INTENT_SCHEMA, _checked_intent as _checked_old_intent,
                             _identity, _require)

REQUEST_VERSION = "program_alert_recon_start_request.v1"
INTENT_SCHEMA = "program_alert_recon_start_intent.v1"


def normalize_program_alert_start(*, principal: TenantPrincipal, tenant_id: UUID | str, actor_id: UUID | str,
                          operation_key: UUID | str, alert_id: UUID | str, window: UTCWindow,
                          budget_policy: StartBudgetPolicy, profile: str, trigger: str, request_version: str) -> dict:
    """Normalize trusted current identity and requested terms; no IO/permission."""
    tenant, actor, key, alert = (_identity(value, name) for name, value in
        (("tenant", tenant_id), ("actor", actor_id), ("operation key", operation_key), ("alert", alert_id)))
    _require(isinstance(principal, TenantPrincipal) and tenant in principal.tenant_ids,
             "current start principal does not permit this tenant")
    _require(profile == "alert_recon" and trigger == "manual" and request_version == REQUEST_VERSION,
             "unsupported manual alert start profile trigger or version")
    # Recheck frozen dataclasses as well: callers cannot mutate/forge attributes
    # then use a retained descriptor as a new trusted policy.
    _require(isinstance(window, UTCWindow), "start requires a checked window of at most five minutes")
    try:
        window = UTCWindow(window.start, window.end)
    except (ValueError, TypeError, AttributeError):
        raise ExecutionRejected("start requires a checked window of at most five minutes") from None
    _require(window.end - window.start <= timedelta(minutes=5), "start requires a checked window of at most five minutes")
    _require(isinstance(budget_policy, StartBudgetPolicy), "trusted explicit start budget policy required")
    budget_policy = StartBudgetPolicy(**asdict(budget_policy))
    request = {"request_version": request_version, "tenant_id": str(tenant), "actor_id": str(actor),
        "operation_key": str(key), "target": {"type": "alert", "id": str(alert)}, "profile": profile,
        "profile_version": PROFILE_VERSION, "trigger": trigger, "objective": OBJECTIVE, "policy_ref": POLICY_REF,
        "runtime_version": RUNTIME_VERSION, "completion_policy_ref": COMPLETION_POLICY_REF,
        "policy_versions": policy_versions(),
        "window": {"start": window.start.isoformat(timespec="microseconds"), "end": window.end.isoformat(timespec="microseconds")},
        "budget_policy": budget_policy.descriptor}
    # Stable tenant/key namespace: changing any request terms must collide with
    # the original operation, rather than silently selecting another Run.
    run = uuid5(NAMESPACE_URL, canonical_json([OPERATION_NAMESPACE, str(tenant), str(key)]))
    body = {"schema": INTENT_SCHEMA, "request": request, "request_hash": content_hash(canonical_json(request)),
            "run_id": str(run), "executor_id": str(uuid5(run, "exclusive-initial-start-owner"))}
    body["intent_ref"] = "program-alert-start-intent:" + content_hash(canonical_json(body))
    return json.loads(canonical_json(body))


def _checked_program_intent(value: dict) -> dict:
    """Structural reconstruction only; caller still proves retained ownership."""
    try:
        request = value["request"]
        policy = request["budget_policy"]
        _require(policy["schema"] == BUDGET_SCHEMA, "unsupported retained start budget schema")
        normalized = normalize_program_alert_start(
            principal=TenantPrincipal(frozenset({_identity(request["tenant_id"], "tenant")}), "retained-format-check", False),
            tenant_id=request["tenant_id"], actor_id=request["actor_id"], operation_key=request["operation_key"],
            alert_id=request["target"]["id"], window=UTCWindow(datetime.fromisoformat(request["window"]["start"]),
                datetime.fromisoformat(request["window"]["end"])),
            budget_policy=StartBudgetPolicy(**{key: field for key, field in policy.items() if key != "schema"}),
            profile=request["profile"], trigger=request["trigger"], request_version=request["request_version"])
        _require(canonical_json(normalized) == canonical_json(value), "start intent structure hash or derived identity differs")
        return normalized
    except ExecutionRejected:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise ExecutionRejected("invalid retained start intent structure") from None


def program_replay_decision(intent: dict, retained_intent: dict | None = None) -> dict:
    """Checked equality can only select a read; no execution authority."""
    current = _checked_program_intent(intent)
    if retained_intent is not None:
        _require(isinstance(retained_intent, dict), "retained program intent must be an object")
        schema = retained_intent.get("schema")
        if schema == INTENT_SCHEMA:
            original = _checked_program_intent(retained_intent)
        elif schema == OLD_INTENT_SCHEMA:
            original = _checked_old_intent(retained_intent)  # format only, never upgrade
        else:
            raise ExecutionRejected("unsupported retained start intent schema")
        _require((original["request"]["tenant_id"], original["request"]["operation_key"])
                 == (current["request"]["tenant_id"], current["request"]["operation_key"]),
                 "retained operation identity differs")
        _require(canonical_json(original) == canonical_json(current), "operation key is bound to a different start request")
    return {"schema": "program_alert_recon_start_decision.v1", "run_id": current["run_id"], "intent_ref": current["intent_ref"],
            "decision": "read_existing_only" if retained_intent is not None else "requires_atomic_admission",
            "may_begin": False, "external_call_authorized": False, "persistence_status": "not_verified_by_pure_contract"}
