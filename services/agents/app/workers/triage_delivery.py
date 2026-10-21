"""Strict delivery guard for the live Kafka auto-triage path.

A start reserves processing, not a model invocation. An unfinished reservation
is deliberately not reclaimed: another process cannot know whether an external
call happened. Completed reads never write the Run, usage, sources or effects.
Direct replay and policy suppression keep their separate entry-point contracts.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from app.agents.dispositions import CANONICAL_DISPOSITIONS
from app.investigator import ledger
from app.investigator.ledger import LedgerPersistError
from app.workers import triage_budget

_NAMESPACE = uuid5(NAMESPACE_URL, "tryaisoc.com/agents/auto-triage")

_READ_KINDS = (
    "organisation_memory_read", "tenant_skill_read", "knowledge_base_read",
    "recent_dispositions_read", "identity_context_read",
)
_ARTIFACT_KINDS = (*_READ_KINDS, "llm_prompt", "llm_response")
_RUN_SQL = """
SELECT id, tenant_id, case_id, raw_alert, model_used, status,
       total_tokens, total_cost_usd, measured_call_count,
       estimated_cost_usd, estimated_call_count, unpriced_call_count
  FROM investigation_runs WHERE id = $1
"""
_EVENTS_SQL = """
SELECT id, run_id, tenant_id, seq, kind, agent, payload, input_hash, output_hash
  FROM investigation_events
 WHERE run_id = $1 AND tenant_id = $2 AND (seq IN (0, 1) OR kind = 'graph_usage')
 ORDER BY seq
"""
_ARTIFACTS_SQL = """
SELECT id, run_id, event_id, tenant_id, kind, content, sha256, size_bytes
  FROM investigation_artifacts
 WHERE run_id = $1 AND tenant_id = $2 AND event_id = $3
   AND kind = ANY($4::text[])
 ORDER BY kind, id
 LIMIT 8
"""


def _fail(reason: str) -> None:
    # Fixed reasons only; no DB messages, payloads or credentials in errors.
    raise LedgerPersistError(f"Auto-triage delivery is not recoverable: {reason}")


def _arguments(run_id: UUID, tenant_id: UUID, alert_id: str, workflow_version: str) -> str:
    if not isinstance(run_id, UUID) or not isinstance(tenant_id, UUID):
        _fail("canonical UUID identity required")
    try:
        canonical = str(UUID(alert_id)) if isinstance(alert_id, str) else ""
    except (ValueError, TypeError, AttributeError):
        canonical = ""
    if not canonical or canonical != alert_id:
        _fail("canonical alert UUID required")
    if not isinstance(workflow_version, str) or not workflow_version.strip() or len(workflow_version) > 200:
        _fail("workflow version required")
    if run_id != uuid5(_NAMESPACE, f"{canonical}:{workflow_version}"):
        _fail("run workflow identity mismatch")
    return canonical


def _object(value: Any, reason: str) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            _fail(reason)
    if not isinstance(value, dict):
        _fail(reason)
    return value


def _number(value: Any, *, minimum: float = 0, maximum: float = float("inf")) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and minimum <= value <= maximum)


def _same_uuid(value: Any, expected: UUID) -> bool:
    return str(value) == str(expected)


def _validate_verdict(payload: dict[str, Any]) -> None:
    if payload.get("verdict") not in CANONICAL_DISPOSITIONS:
        _fail("invalid first verdict")
    if not _number(payload.get("confidence"), maximum=1):
        _fail("invalid first confidence")
    if not isinstance(payload.get("rationale"), str):
        _fail("missing first rationale")
    for field in ("findings", "proposed_actions"):
        if not isinstance(payload.get(field), list):
            _fail(f"invalid first {field}")
    if any(not isinstance(v, str) for v in payload["findings"]):
        _fail("invalid first findings")
    for action in payload["proposed_actions"]:
        if (not isinstance(action, dict) or not isinstance(action.get("action_type"), str)
                or type(action.get("requires_approval")) is not bool):
            _fail("invalid first proposed actions")
    if type(payload.get("auto_closed")) is not bool:
        _fail("invalid first auto-close flag")
    for field in _READ_KINDS:
        if field in payload and not isinstance(payload[field], dict):
            _fail("invalid persisted source read")


def _projection(payload: dict[str, Any], run: Any, *, run_id: UUID,
                tenant_id: UUID, alert_id: str, workflow_version: str,
                graph_usage_events: tuple | list = ()) -> dict[str, Any]:
    """Versioned exact summary, or an explicitly incomplete legacy projection."""
    if "recovery" in payload:
        result = deepcopy(_object(payload["recovery"], "invalid recovery projection"))
        if (type(result.get("schema_version")) is not int or result["schema_version"] != 1
                or result.get("workflow_version") != workflow_version
                or result.get("run_id") != str(run_id) or result.get("tenant_id") != str(tenant_id)
                or result.get("alert_id") != alert_id):
            _fail("recovery identity or version mismatch")
        if (result.get("verdict") != payload["verdict"]
                or result.get("confidence") != payload["confidence"]
                or result.get("findings") != payload["findings"]):
            _fail("recovery differs from first verdict")
        expected_actions = [{"action_type": a["action_type"], "requires_approval": a["requires_approval"]}
                            for a in payload["proposed_actions"]]
        if result.get("proposed_actions") != expected_actions:
            _fail("recovery actions differ from first verdict")
        if (type(result.get("shadow")) is not bool or not isinstance(result.get("incident_id"), str)
                or not result["incident_id"] or result.get("tier") != run["model_used"].split(":", 2)[2]
                or not isinstance(result.get("confidence_basis"), list)
                or not isinstance(result.get("business_context_rules"), list)
                or not isinstance(result.get("business_context_policy"), dict)):
            _fail("incomplete recovery summary")
        cost = result.get("cost")
        if not isinstance(cost, dict):
            _fail("invalid recovery usage")
        for key in ("measured_calls", "estimated_calls", "unpriced_calls", "tokens"):
            if type(cost.get(key)) is not int or cost[key] < 0:
                _fail("invalid recovery usage")
        for key in ("measured_usd", "estimated_usd"):
            if key not in cost or (cost[key] is not None and not _number(cost[key])):
                _fail("invalid recovery cost provenance")
        if not isinstance(cost.get("resolved_models"), list):
            _fail("invalid recovery model provenance")
        # A larger Run is valid only when append-only graph usage events
        # account for the difference. A lower bound would silently accept an
        # unrelated overwrite or duplicate charge as a completed first result.
        deltas = []
        for event in graph_usage_events:
            if (not _same_uuid(event["run_id"], run_id) or not _same_uuid(event["tenant_id"], tenant_id)
                    or type(event["seq"]) is not int or event["seq"] <= 1
                    or event["kind"] != "graph_usage" or event["agent"] != "graph:investigation"):
                _fail("graph usage event identity mismatch")
            graph_payload = _object(event["payload"], "invalid graph usage event")
            canonical = ledger._graph_usage_payload(graph_payload.get("usage"), run_id=run_id, tenant_id=tenant_id)
            if graph_payload != canonical or event["output_hash"] != ledger._graph_usage_hash(canonical):
                _fail("graph usage event provenance mismatch")
            deltas.append(canonical["usage"])
        for key, column in (("tokens", "total_tokens"), ("measured_calls", "measured_call_count"),
                            ("estimated_calls", "estimated_call_count"), ("unpriced_calls", "unpriced_call_count")):
            if type(run[column]) is not int or run[column] != cost[key] + sum(delta[key] for delta in deltas):
                _fail("recovery usage differs from completed run")
        for key, count, column in (("measured_usd", "measured_calls", "total_cost_usd"),
                                   ("estimated_usd", "estimated_calls", "estimated_cost_usd")):
            if cost[count] + sum(delta[count] for delta in deltas):
                if cost[count] and cost[key] is None:
                    _fail("invalid recovery cost provenance")
                expected = ledger._usage_amount(cost[key]) if cost[count] else ledger._usage_amount(0)
                expected += sum((ledger._usage_amount(delta[key]) for delta in deltas if delta[count]),
                                ledger._usage_amount(0))
                if run[column] is None or ledger._usage_amount(run[column]) != expected:
                    _fail("recovery cost differs from completed run")
        result["recovery_format"] = "summary_v1"
    else:
        # Legacy rows did not persist these summary fields. NULL means unknown,
        # including shadow and resolved-model names; a stored zero dollar column
        # alone is not a measurement of a free call.
        measured = run["measured_call_count"]
        estimated = run["estimated_call_count"]
        result = {
            "schema_version": 1, "workflow_version": None,
            "run_id": str(run_id), "tenant_id": str(tenant_id), "alert_id": alert_id,
            "incident_id": None, "shadow": None,
            "verdict": payload["verdict"], "confidence": payload["confidence"],
            "tier": run["model_used"].split(":", 2)[2],
            "findings": deepcopy(payload["findings"]),
            "proposed_actions": [{"action_type": a["action_type"], "requires_approval": a["requires_approval"]}
                                 for a in payload["proposed_actions"]],
            "cost": {"measured_usd": float(run["total_cost_usd"]) if measured else None,
                     "measured_calls": measured,
                     "estimated_usd": float(run["estimated_cost_usd"]) if estimated else None,
                     "estimated_calls": estimated, "unpriced_calls": run["unpriced_call_count"],
                     "resolved_models": None, "tokens": run["total_tokens"]},
            "confidence_basis": None, "business_context_rules": None, "business_context_policy": None,
            "recovery_format": "legacy_first_verdict",
            "legacy_missing_fields": ["workflow_version", "incident_id", "shadow", "confidence_basis",
                                      "business_context_rules", "business_context_policy", "cost.resolved_models"],
        }
    result.update(reused_persisted=True, response_dispatched=False, approvals_raised=[],
                  source_writeback=None, effect_status="not_replayed")
    result["persisted_source_reads"] = {k: deepcopy(payload[k]) for k in _READ_KINDS if k in payload}
    result["source_reads_not_recorded"] = [k for k in _READ_KINDS if k not in payload]
    return result


async def _completed(conn: Any, *, run_id: UUID, tenant_id: UUID, alert_id: str,
                     workflow_version: str) -> dict[str, Any] | None:
    # Deliberately query by PK first. A tenant-filtered miss must never be used
    # as authority to overwrite or claim another tenant's deterministic Run.
    run = await conn.fetchrow(_RUN_SQL, run_id)
    if run is None:
        return None
    if (not _same_uuid(run["id"], run_id) or not _same_uuid(run["tenant_id"], tenant_id)
            or run["case_id"] != alert_id):
        _fail("run identity mismatch")
    raw = _object(run["raw_alert"], "missing run alert identity")
    if raw.get("id") != alert_id:
        _fail("run alert identity mismatch")
    model = run["model_used"]
    if not isinstance(model, str) or not model.startswith("kafka:auto_triage:") or not model.split(":", 2)[2]:
        _fail("run is not Kafka auto-triage")
    if run["status"] != "completed" or model == "kafka:auto_triage:claimed":
        _fail("processing started or outcome unknown")
    events = await conn.fetch(_EVENTS_SQL, run_id, tenant_id)
    by_seq = {}
    for event in events:
        if (not _same_uuid(event["run_id"], run_id) or not _same_uuid(event["tenant_id"], tenant_id)
                or event["seq"] in by_seq):
            _fail("event identity mismatch")
        by_seq[event["seq"]] = event
    first = by_seq.get(1)
    if first is None or first["kind"] != "triage_verdict":
        _fail("missing first triage verdict")
    if first["agent"] != "auto_triage:" + model.split(":", 2)[2]:
        _fail("first verdict tier mismatch")
    payload = _object(first["payload"], "invalid first verdict payload")
    _validate_verdict(payload)
    result = _projection(payload, run, run_id=run_id, tenant_id=tenant_id,
                         alert_id=alert_id, workflow_version=workflow_version,
                         graph_usage_events=[event for seq, event in by_seq.items() if seq > 1])
    artifacts = await conn.fetch(_ARTIFACTS_SQL, run_id, tenant_id, first["id"], list(_ARTIFACT_KINDS))
    exchange = None
    if 0 in by_seq:
        if by_seq[0]["kind"] != "llm_call":
            _fail("invalid first model event")
        exchange = _object(by_seq[0]["payload"], "invalid first model transcript")
        for key in ("input_hash", "output_hash"):
            hashes = (exchange.get(key), by_seq[0].get(key), first.get(key))
            if any(value is not None for value in hashes):
                if (len(set(hashes)) != 1 or not isinstance(hashes[0], str)
                        or len(hashes[0]) != 64
                        or any(c not in "0123456789abcdef" for c in hashes[0])):
                    _fail("first transcript hash linkage mismatch")
    elif first.get("input_hash") is not None or first.get("output_hash") is not None:
        _fail("verdict transcript hashes have no model event")
    seen = set()
    refs = []
    for artifact in artifacts:
        kind, content = artifact["kind"], artifact["content"]
        if (kind not in _ARTIFACT_KINDS or kind in seen
                or not _same_uuid(artifact["run_id"], run_id)
                or not _same_uuid(artifact["tenant_id"], tenant_id)
                or not _same_uuid(artifact["event_id"], first["id"])):
            _fail("artifact identity or multiplicity mismatch")
        seen.add(kind)
        if (not isinstance(content, str) or hashlib.sha256(content.encode("utf-8")).hexdigest() != artifact["sha256"]
                or len(content.encode("utf-8")) != artifact["size_bytes"]):
            _fail("persisted artifact integrity mismatch")
        if kind in _READ_KINDS:
            if kind not in payload or _object(content, "invalid source artifact") != payload[kind]:
                _fail("source artifact differs from first verdict")
        elif exchange is None or content != exchange.get("prompt" if kind == "llm_prompt" else "response"):
            _fail("transcript artifact differs from first model event")
        refs.append({"id": str(artifact["id"]), "kind": kind, "sha256": artifact["sha256"],
                     "size_bytes": artifact["size_bytes"]})
    expected = {kind for kind in _READ_KINDS if kind in payload}
    if exchange is not None:
        for kind, key in (("llm_prompt", "prompt"), ("llm_response", "response")):
            if exchange.get(key):
                expected.add(kind)
    if not expected.issubset(seen):
        _fail("required first-result artifact is missing")
    result["persisted_artifacts"] = refs
    result["source_artifacts_not_recorded"] = [k for k in _READ_KINDS if k not in seen]
    return result


async def _pool() -> Any:
    pool = await ledger.get_pool()
    if pool is None:
        _fail("database unavailable")
    return pool


async def lookup(*, run_id: UUID, tenant_id: UUID, alert_id: str,
                 workflow_version: str) -> dict[str, Any] | None:
    """Return a completed first result, None only for a missing visible Run."""
    _arguments(run_id, tenant_id, alert_id, workflow_version)
    try:
        pool = await _pool()
        async with pool.acquire() as conn:
            async with conn.transaction(isolation="read_committed"):
                await ledger._set_rls_context(conn, tenant_id)
                return await _completed(conn, run_id=run_id, tenant_id=tenant_id,
                                        alert_id=alert_id, workflow_version=workflow_version)
    except LedgerPersistError:
        raise
    except Exception as exc:
        raise LedgerPersistError("Auto-triage delivery lookup failed") from exc


async def claim(*, run_id: UUID, tenant_id: UUID, alert_id: str,
                workflow_version: str, budget: triage_budget.Policy | None = None) -> dict[str, Any] | None:
    """None authorizes one new owner only after its start transaction commits.

    A concurrent loser uses a new READ COMMITTED statement snapshot; unfinished
    or invisible conflicting Runs fail closed. There is no lease stealing.
    """
    _arguments(run_id, tenant_id, alert_id, workflow_version)
    try:
        pool = await _pool()
        async with pool.acquire() as conn:
            async with conn.transaction(isolation="read_committed"):
                await ledger._set_rls_context(conn, tenant_id)
                existing = await _completed(conn, run_id=run_id, tenant_id=tenant_id,
                                            alert_id=alert_id, workflow_version=workflow_version)
                if existing is not None:
                    return existing
                if budget is not None:
                    await triage_budget.check_locked(conn, tenant_id, budget)
                alert = await conn.fetchrow("SELECT id, tenant_id FROM alerts WHERE id = $1 AND tenant_id = $2",
                                            UUID(alert_id), tenant_id)
                if alert is None or not _same_uuid(alert["id"], UUID(alert_id)) or not _same_uuid(alert["tenant_id"], tenant_id):
                    _fail("alert tenant ownership not confirmed")
                inserted = await conn.fetchrow("""
INSERT INTO investigation_runs
  (id, tenant_id, case_id, raw_alert, model_used, status, started_at, created_at)
VALUES ($1, $2, $3, $4::jsonb, 'kafka:auto_triage:claimed', 'running', now(), now())
ON CONFLICT (id) DO NOTHING RETURNING id
""", run_id, tenant_id, alert_id, json.dumps({"id": alert_id}))
                if inserted is None:
                    existing = await _completed(conn, run_id=run_id, tenant_id=tenant_id,
                                                alert_id=alert_id, workflow_version=workflow_version)
                    if existing is None:
                        _fail("conflicting run is not visible")
                    return existing
                if not _same_uuid(inserted["id"], run_id):
                    _fail("claim identity mismatch")
                await conn.execute("""
INSERT INTO investigation_events
 (id, run_id, tenant_id, seq, ts, kind, agent, summary, payload, duration_ms, created_at)
VALUES ($1, $2, $3, -1, now(), 'triage_started', 'auto_triage:delivery',
        'Processing claimed; model invocation is not established', $4::jsonb, 0, now())
""", uuid4(), run_id, tenant_id, json.dumps({"schema_version": 1,
                    "owner_token": str(uuid4()), "workflow_version": workflow_version,
                    "tenant_id": str(tenant_id), "alert_id": alert_id,
                    "processing_started": True, "model_invocation_established": False}))
                if budget is not None:
                    await triage_budget.reserve(conn, run_id=run_id, tenant_id=tenant_id, policy=budget)
            # This return is intentionally outside transaction.__aexit__.
            return None
    except LedgerPersistError as exc:
        if budget is not None and not isinstance(exc, triage_budget.BudgetHold):
            raise triage_budget.BudgetHold("Triage budget claim not confirmed") from exc
        raise
    except Exception as exc:
        if budget is not None:
            raise triage_budget.BudgetHold("Triage budget claim failed; offset must be retained") from exc
        raise LedgerPersistError("Auto-triage delivery claim failed") from exc


lookup_triage_delivery = lookup
claim_triage_delivery = claim
