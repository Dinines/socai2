"""Pure manual alert start identities, never a durable admission or permission.

The caller must authenticate the current tenant/actor and check investigation:run
and alerts:read on every request. Budget policies are selected by trusted server
configuration. Retained intents must already have owned storage/hash checks.
No current Alert load, persistence, deadline creation, claim or dispatch occurs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from uuid import NAMESPACE_URL, UUID, uuid5

from .business_profile import OBJECTIVE, PROFILE_VERSION
from .execution_state import BudgetLimits, ExecutionRejected
from .execution_store import canonical_json, content_hash
from .fixed_recon import COMPLETION_POLICY_REF
from .recon_runtime_state import RUNTIME_VERSION
from .scope import POLICY_REF, TenantPrincipal, UTCWindow

REQUEST_VERSION = "alert_recon_start_request.v1"
INTENT_SCHEMA = "alert_recon_start_intent.v1"
BUDGET_SCHEMA = "fixed_alert_start_budget.v1"
OPERATION_NAMESPACE = "socai2:investigation-v2:start-operation"
MAX_DURATION_SECONDS = 180


def _require(value: bool, reason: str) -> None:
    if not value:
        raise ExecutionRejected(reason)


def _identity(value, name: str) -> UUID:
    try:
        _require(isinstance(value, (UUID, str)), name + " requires a nonnil UUID")
        parsed = UUID(str(value))
        _require(parsed.int != 0, name + " requires a nonnil UUID")
        return parsed
    except (ValueError, TypeError, AttributeError):
        raise ExecutionRejected(name + " requires a nonnil UUID") from None


@dataclass(frozen=True)
class StartBudgetPolicy:
    max_model_calls: int
    max_tool_calls: int
    max_tokens: int
    max_cost_microusd: int
    max_unsettled: int
    duration_seconds: int
    config_ref: str
    legacy_model_limit_mapping: str

    def __post_init__(self) -> None:
        _require(type(self.duration_seconds) is int and 1 <= self.duration_seconds <= MAX_DURATION_SECONDS,
                 "start duration requires an integer in 1..180 seconds")
        # Reuse M3's strict integer/combined limit contract without a real clock
        # or actual deadline. Only the duration is retained in this pure policy.
        BudgetLimits(**{key: value for key, value in asdict(self).items() if key != "duration_seconds"},
                     deadline=datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=self.duration_seconds))
        _require(self.max_model_calls == self.max_tokens == 0 and type(self.max_cost_microusd) is int
                 and self.max_cost_microusd == 0 and self.max_tool_calls in (0, 1) and self.max_unsettled == 1,
                 "start policy exceeds the supported fixed program path")

    @property
    def descriptor(self) -> dict:
        return {"schema": BUDGET_SCHEMA, **asdict(self)}


def normalize_alert_start(*, principal: TenantPrincipal, tenant_id: UUID | str, actor_id: UUID | str,
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
        "window": {"start": window.start.isoformat(timespec="microseconds"), "end": window.end.isoformat(timespec="microseconds")},
        "budget_policy": budget_policy.descriptor}
    # Stable tenant/key namespace: changing any request terms must collide with
    # the original operation, rather than silently selecting another Run.
    run = uuid5(NAMESPACE_URL, canonical_json([OPERATION_NAMESPACE, str(tenant), str(key)]))
    body = {"schema": INTENT_SCHEMA, "request": request, "request_hash": content_hash(canonical_json(request)),
            "run_id": str(run), "executor_id": str(uuid5(run, "exclusive-initial-start-owner"))}
    body["intent_ref"] = "alert-start-intent:" + content_hash(canonical_json(body))
    return json.loads(canonical_json(body))


def _checked_intent(value: dict) -> dict:
    """Structural reconstruction only; caller still proves retained ownership."""
    try:
        request = value["request"]
        policy = request["budget_policy"]
        _require(policy["schema"] == BUDGET_SCHEMA, "unsupported retained start budget schema")
        normalized = normalize_alert_start(
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


def replay_decision(intent: dict, retained_intent: dict | None = None) -> dict:
    """No match may begin/execute here, even after a structurally matching retry."""
    current = _checked_intent(intent)
    if retained_intent is not None:
        original = _checked_intent(retained_intent)
        _require((original["request"]["tenant_id"], original["request"]["operation_key"])
                 == (current["request"]["tenant_id"], current["request"]["operation_key"]),
                 "retained operation identity differs")
        _require(canonical_json(original) == canonical_json(current), "operation key is bound to a different start request")
    return {"schema": "alert_recon_start_decision.v1", "run_id": current["run_id"], "intent_ref": current["intent_ref"],
            "decision": "read_existing_only" if retained_intent is not None else "requires_atomic_admission",
            "may_begin": False, "external_call_authorized": False, "persistence_status": "not_verified_by_pure_contract"}
