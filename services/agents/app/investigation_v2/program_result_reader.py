"""Explicit fixed/program owned read service. Authentication/permission is a caller precondition.

No caller-supplied owner or scope, mutable Alert read, dispatch or storage write.
Uses the existing M3 Run row lock to read one current M7 result consistently.
"""
from __future__ import annotations

from uuid import UUID

from .execution_state import ExecutionRejected
from .execution_store import ExecutionPersistenceError, content_hash, canonical_json, KINDS, _object
from .profile_restore import restore_alert_read_request
from .program_profile_restore import restore_program_alert_read_request
from .recon_publication_store import ReconPublicationStore
from .program_recon_publication_store import ProgramReconPublicationStore
from .recon_runtime_state import RUNTIME_VERSION
from .program_runtime_state import RUNTIME_VERSION as PROGRAM_RUNTIME_VERSION
from .recon_runtime_store import CONTROL_KINDS
from .program_runtime_store import CONTROL_KINDS as PROGRAM_CONTROL_KINDS
from .scope import PrincipalScope, TenantPrincipal


def _require(value: bool, reason: str) -> None:
    if not value:
        raise ExecutionRejected(reason)


async def _owned_artifact(conn, *, tenant_id: UUID, run_id: UUID, artifact_id: UUID, event_id: UUID, kind: str):
    # Same owned join/hash contract as M3; bootstrap has no trusted owner yet.
    row = await conn.fetchrow("SELECT a.id,a.run_id,a.tenant_id,a.event_id,a.kind,a.content,a.sha256,a.size_bytes "
        "FROM investigation_artifacts a JOIN investigation_events e ON e.id=a.event_id "
        "AND e.run_id=a.run_id AND e.tenant_id=a.tenant_id "
        "WHERE a.id=$1 AND a.run_id=$2 AND a.tenant_id=$3", artifact_id, run_id, tenant_id)
    _require(row is not None and (row["run_id"], row["tenant_id"], row["event_id"], row["kind"])
             == (run_id, tenant_id, event_id, kind), "owned begin artifact missing or mismatched")
    body = row["content"]
    _require(isinstance(body, str) and type(row["size_bytes"]) is int and len(body.encode("utf-8")) == row["size_bytes"] and content_hash(body) == row["sha256"],
             "owned begin artifact integrity mismatch")
    return dict(row)


_BRANCHES = {
    CONTROL_KINDS[0]: (RUNTIME_VERSION, restore_alert_read_request, ReconPublicationStore, "owned_fixed_recon_result.v1"),
    PROGRAM_CONTROL_KINDS[0]: (PROGRAM_RUNTIME_VERSION, restore_program_alert_read_request, ProgramReconPublicationStore,
                              "owned_program_recon_result.v1"),
}


class CompatibleOwnedReconResultReader:
    def __init__(self, pool):
        _require(pool is not None, "owned result read pool required")
        self.pool = pool

    async def read(self, *, current_principal: TenantPrincipal, tenant_id: UUID, run_id: UUID) -> dict:
        try:
            _require(isinstance(current_principal, TenantPrincipal), "current authenticated reader required")
            current = PrincipalScope(current_principal.tenant_ids, current_principal.subject, current_principal.delegated)
            tenant, run_id = UUID(str(tenant_id)), UUID(str(run_id))
            _require(tenant.int != 0 and run_id.int != 0 and tenant in current.tenant_ids, "current reader tenant is not permitted")
        except ExecutionRejected:
            raise
        except (ValueError, TypeError, AttributeError):
            raise ExecutionRejected("invalid current reader or Run identity") from None
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("SELECT set_config('app.current_tenant_id', $1, true)", str(tenant))
                    run = await conn.fetchrow("SELECT id,tenant_id,status,completed_at,total_tokens,total_cost_usd "
                        "FROM investigation_runs WHERE id=$1 AND tenant_id=$2 FOR UPDATE", run_id, tenant)
                    _require(run is not None and (run["id"], run["tenant_id"]) == (run_id, tenant), "owned Run not found")
                    beginnings = await conn.fetch("SELECT id,tenant_id,run_id,seq,kind,agent,payload,input_hash,output_hash "
                        "FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 AND kind=ANY($3::text[]) ORDER BY seq ASC LIMIT 2",
                        run_id, tenant, [KINDS[0], CONTROL_KINDS[0], PROGRAM_CONTROL_KINDS[0]])
                    _require(len(beginnings) == 1, "exactly one owned managed begin required")
                    event = beginnings[0]
                    branch = _BRANCHES.get(event["kind"])
                    _require(branch is not None, "unsupported owned managed begin")
                    runtime, restore, store_type, schema = branch
                    _require((event["run_id"], event["tenant_id"], event["agent"]) == (run_id, tenant, runtime),
                             "owned begin event identity mismatch")
                    unknown = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM investigation_events "
                        "WHERE run_id=$1 AND tenant_id=$2 AND kind LIKE 'unified_%' "
                        "AND (NOT (kind=ANY($3::text[])) OR agent IS DISTINCT FROM $4))",
                        run_id, tenant, list(store_type.event_kinds), runtime)
                    _require(not unknown, "unknown or mixed managed event; version fallback forbidden")
                    payload = _object(event["payload"])
                    body = await _owned_artifact(conn, tenant_id=tenant, run_id=run_id, artifact_id=UUID(payload["body_artifact_id"]),
                                                 event_id=event["id"], kind="unified_step_input")
                    snapshot = await _owned_artifact(conn, tenant_id=tenant, run_id=run_id, artifact_id=UUID(payload["state_artifact_id"]),
                                                     event_id=event["id"], kind="unified_state_snapshot")
                    original, state = _object(body["content"]), _object(snapshot["content"])
                    _require(payload["body_hash"] == body["sha256"] == event["input_hash"]
                             and payload["state_hash"] == snapshot["sha256"] and event["output_hash"] is None,
                             "owned begin event hash mismatch")
                    _require(type(event["seq"]) is int and event["seq"] >= 1 and type(payload["seq"]) is int
                             and canonical_json(state["persistence"]) == canonical_json({key: value for key, value in payload.items() if key != "state_hash"})
                             and canonical_json([payload["event_id"], payload["seq"], payload["tenant_id"], payload["run_id"], payload["stage_id"], payload["attempt_id"]])
                             == canonical_json([str(event["id"]), event["seq"], str(tenant), str(run_id), state["stage_id"], None])
                             and (state["tenant_id"], state["run_id"]) == (str(tenant), str(run_id)), "owned begin receipt mismatch")
                    request = restore(current_principal=current_principal, begin_input=original, begin_state=state)
                    owner = UUID(state["executor_id"])
                    _require(owner.int != 0, "owned nonnil executor required")
                    store = store_type(self.pool, tenant_id=tenant, run_id=run_id, executor_id=owner)
                    result = await store._read_result_locked(conn, request)
                    result = {**result, "schema": schema, "tenant_id": str(tenant), "run_id": str(run_id),
                        "profile": request.profile, "target": request.descriptor["delivery_target"], "objective": request.objective,
                        "legacy_run_status": run["status"]}
            return result
        except ExecutionRejected:
            raise
        except Exception as exc:
            raise ExecutionPersistenceError("owned result read not confirmed") from exc
