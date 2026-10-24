"""Strict M3 transactions on the existing ledger tables; no entry-point wiring.

The pool is explicit. Every operation locks the owned Run, sets the tenant in
that transaction, and allocates seq after the lock. This coordinates M3 writers
only; legacy writers do not participate. No Run status/cost fields are changed.
An exception, including an uncertain commit, never grants execution permission.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from .execution_state import (BudgetLimits, OpeningUsage, ExecutionRejected,
                              SCHEMA_VERSION, initial_state, reserve, settle, stage_id_for)
from .scope import ScopeContext

MAX_BODY_BYTES = 1024 * 1024
MAX_STATE_BYTES = 512 * 1024
KINDS = ("unified_execution_started", "unified_attempt_reserved", "unified_attempt_settled")


class ExecutionPersistenceError(RuntimeError):
    """Persistence failed or its commit could not be confirmed. Do not execute/replay."""


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone required")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=str)
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError("unsupported snapshot value")


def canonical_json(value: Any, *, max_bytes: int = MAX_BODY_BYTES) -> str:
    try:
        body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                          allow_nan=False, default=_json_default)
    except (ValueError, TypeError) as exc:
        raise ExecutionRejected("snapshot must be canonical JSON") from exc
    if len(body.encode("utf-8")) > max_bytes:
        raise ExecutionRejected("snapshot exceeds retained byte limit")
    return body


def content_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def scope_snapshot(scope: ScopeContext) -> tuple[dict, dict[str, str]]:
    """Project immutable controls plus source hashes; retain source text once at begin.

    M1 repeats CheckedAlert in member/query views. Its data-only text is not a
    control, so neither view may copy that text into every execution snapshot.
    The content-addressed references still bind every byte of the caller scope.
    """
    if not isinstance(scope, ScopeContext):
        raise ExecutionRejected("trusted M1 scope required")
    sources: dict[str, str] = {}

    def project(value: Any) -> Any:
        if isinstance(value, dict):
            result = {k: project(v) for k, v in value.items() if k != "data_only_text"}
            if "data_only_text" in value:
                text = value["data_only_text"]
                digest = content_hash(text)
                reference = "scope-source:" + digest
                sources[reference] = text
                result["data_only_source"] = {"ref": reference, "sha256": digest,
                                              "size_bytes": len(text.encode("utf-8"))}
            return result
        if isinstance(value, (list, tuple)):
            return [project(v) for v in value]
        return value

    controls = json.loads(canonical_json(project(asdict(scope)), max_bytes=MAX_STATE_BYTES))
    return controls, sources


def scope_fingerprint(scope: ScopeContext) -> str:
    return content_hash(canonical_json(scope_snapshot(scope)[0]))


def _object(value: Any) -> dict:
    parsed = json.loads(value) if isinstance(value, str) else value
    if not isinstance(parsed, dict):
        raise ExecutionRejected("invalid stored object")
    return parsed


class ExecutionStore:
    def __init__(self, pool: Any, *, tenant_id: UUID, run_id: UUID, executor_id: UUID):
        if pool is None:
            raise ExecutionRejected("durable pool required")
        self.pool = pool
        self.tenant_id, self.run_id, self.executor_id = (UUID(str(v)) for v in (tenant_id, run_id, executor_id))
        if any(v.int == 0 for v in (self.tenant_id, self.run_id, self.executor_id)):
            raise ExecutionRejected("nonnil execution identity required")

    @asynccontextmanager
    async def _locked(self):
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("SELECT set_config('app.current_tenant_id', $1, true)", str(self.tenant_id))
                    run = await conn.fetchrow(
                        "SELECT id,tenant_id,status,completed_at,total_tokens,total_cost_usd "
                        "FROM investigation_runs WHERE id=$1 AND tenant_id=$2 FOR UPDATE",
                        self.run_id, self.tenant_id)
                    if run is None:
                        raise ExecutionRejected("owned Run not found")
                    yield conn, dict(run)
        except ExecutionRejected:
            raise
        except Exception as exc:
            # Do not expose driver parameters or credentials in caller errors.
            raise ExecutionPersistenceError("transaction not confirmed; execution/replay forbidden") from exc

    async def _read_artifact(self, conn: Any, artifact_id: UUID, event_id: UUID | None = None) -> dict:
        row = await conn.fetchrow(
            "SELECT a.id,a.event_id,a.kind,a.content,a.sha256,a.size_bytes "
            "FROM investigation_artifacts a JOIN investigation_events e ON e.id=a.event_id "
            "AND e.run_id=a.run_id AND e.tenant_id=a.tenant_id "
            "WHERE a.id=$1 AND a.run_id=$2 AND a.tenant_id=$3",
            artifact_id, self.run_id, self.tenant_id)
        if row is None or (event_id is not None and row["event_id"] != event_id):
            raise ExecutionRejected("artifact ownership/event mismatch")
        result = dict(row)
        body = result["content"]
        if not isinstance(body, str) or len(body.encode("utf-8")) != result["size_bytes"] or content_hash(body) != result["sha256"]:
            raise ExecutionRejected("artifact integrity mismatch")
        return result

    async def _load(self, conn: Any) -> dict:
        event = await conn.fetchrow(
            "SELECT id,seq,kind,payload FROM investigation_events "
            "WHERE run_id=$1 AND tenant_id=$2 AND kind=ANY($3::text[]) ORDER BY seq DESC LIMIT 1",
            self.run_id, self.tenant_id, list(KINDS))
        if event is None:
            raise ExecutionRejected("durable begin required")
        payload = _object(event["payload"])
        artifact = await self._read_artifact(conn, UUID(payload["state_artifact_id"]), event["id"])
        if artifact["kind"] != "unified_state_snapshot" or artifact["sha256"] != payload["state_hash"]:
            raise ExecutionRejected("state reference mismatch")
        state = _object(artifact["content"])
        expected = {"schema_version": SCHEMA_VERSION, "tenant_id": str(self.tenant_id),
                    "run_id": str(self.run_id), "executor_id": str(self.executor_id),
                    "stage_id": stage_id_for(self.tenant_id, self.run_id)}
        if any(state.get(k) != v for k, v in expected.items()):
            raise ExecutionRejected("stored execution identity/owner mismatch")
        if state.get("persistence", {}).get("event_id") != str(event["id"]) or state["persistence"]["seq"] != event["seq"]:
            raise ExecutionRejected("state event mismatch")
        if content_hash(canonical_json(state["scope"])) != state["scope_hash"]:
            raise ExecutionRejected("scope hash mismatch")
        return state

    async def _insert_artifact(self, conn: Any, *, artifact_id: UUID, event_id: UUID, kind: str, body: str) -> None:
        saved = await conn.fetchval(
            "INSERT INTO investigation_artifacts (id,run_id,event_id,tenant_id,kind,content,sha256,size_bytes) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id",
            artifact_id, self.run_id, event_id, self.tenant_id, kind, body, content_hash(body), len(body.encode("utf-8")))
        if saved != artifact_id:
            raise ExecutionPersistenceError("artifact insert not confirmed")

    async def _append(self, conn: Any, state: dict, *, kind: str, body: str, body_id: UUID,
                      body_kind: str, now: datetime, attempt_id: str | None = None) -> dict:
        seq = await conn.fetchval("SELECT COALESCE(MAX(seq),0)+1 FROM investigation_events WHERE run_id=$1", self.run_id)
        event_id, snapshot_id = uuid4(), uuid4()
        receipt = {"event_id": str(event_id), "seq": seq, "state_artifact_id": str(snapshot_id),
                   "body_artifact_id": str(body_id), "body_hash": content_hash(body),
                   "tenant_id": str(self.tenant_id), "run_id": str(self.run_id),
                   "stage_id": state["stage_id"], "attempt_id": attempt_id}
        if kind == "unified_attempt_settled":
            state["attempts"][attempt_id]["completion_receipt"] = dict(receipt)
        state["persistence"] = dict(receipt)
        snapshot = canonical_json(state, max_bytes=MAX_STATE_BYTES)
        payload = {**receipt, "state_hash": content_hash(snapshot)}
        saved = await conn.fetchval(
            "INSERT INTO investigation_events "
            "(id,run_id,tenant_id,seq,ts,kind,agent,summary,payload,input_hash,output_hash) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,$11) RETURNING id",
            event_id, self.run_id, self.tenant_id, seq, now, kind, "unified_executor.v1", kind,
            canonical_json(payload), content_hash(body) if body_kind == "unified_step_input" else None,
            content_hash(body) if body_kind == "unified_step_output" else None)
        if saved != event_id:
            raise ExecutionPersistenceError("event insert not confirmed")
        await self._insert_artifact(conn, artifact_id=body_id, event_id=event_id, kind=body_kind, body=body)
        await self._insert_artifact(conn, artifact_id=snapshot_id, event_id=event_id,
                                    kind="unified_state_snapshot", body=snapshot)
        return {"state": state, "receipt": receipt, "repeated": False}

    async def begin(self, *, scope: ScopeContext, limits: BudgetLimits, opening: OpeningUsage,
                    input_data: Any, parent_deadline: datetime | None = None) -> dict:
        if not isinstance(scope, ScopeContext) or (scope.tenant_id, scope.run_id) != (self.tenant_id, self.run_id):
            raise ExecutionRejected("matching trusted M1 scope required")
        if parent_deadline is not None:
            if parent_deadline.tzinfo is None or parent_deadline.utcoffset() is None:
                raise ExecutionRejected("parent deadline requires timezone")
            limits = replace(limits, deadline=min(limits.deadline, parent_deadline))
        controls, sources = scope_snapshot(scope)
        body = canonical_json({"input": input_data, "scope_sources": sources,
                               "scope_hash": content_hash(canonical_json(controls))})
        body_id = uuid4()
        async with self._locked() as (conn, run):
            exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM investigation_events "
                                         "WHERE run_id=$1 AND kind LIKE 'unified_%')", self.run_id)
            if exists:
                raise ExecutionRejected("stage already began; reset/takeover forbidden")
            now = await conn.fetchval("SELECT clock_timestamp()")
            state = initial_state(scope=controls, input_snapshot_ref="urn:uuid:" + str(body_id),
                                  input_hash=content_hash(body), limits=limits, opening=opening,
                                  executor_id=self.executor_id, now=now)
            state["legacy_run_snapshot"] = json.loads(canonical_json(run))
            result = await self._append(conn, state, kind=KINDS[0], body=body, body_id=body_id,
                                        body_kind="unified_step_input", now=now)
        return result  # only after successful commit

    async def reserve(self, *, scope_hash: str, input_data: Any, **request: Any) -> dict:
        body, body_id = canonical_json(input_data), uuid4()
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            if state["scope_hash"] != scope_hash:
                raise ExecutionRejected("caller scope differs from durable scope")
            now = await conn.fetchval("SELECT clock_timestamp()")
            updated, attempt = reserve(state, **request, input_snapshot_ref="urn:uuid:" + str(body_id),
                                       input_hash=content_hash(body), now=now)
            result = await self._append(conn, updated, kind=KINDS[1], body=body, body_id=body_id,
                                        body_kind="unified_step_input", now=now, attempt_id=attempt["attempt_id"])
        return result

    async def complete(self, *, attempt_id: UUID | str, output_data: Any, outcome: str,
                       actual_tokens: int | None, actual_cost_microusd: int | None, usage_source_ref: str) -> dict:
        body, body_id = canonical_json(output_data), uuid4()
        attempt = str(UUID(str(attempt_id)))
        signature = content_hash(canonical_json(dict(attempt_id=attempt, output_hash=content_hash(body), outcome=outcome,
                    actual_tokens=actual_tokens, actual_cost_microusd=actual_cost_microusd, usage_source_ref=usage_source_ref)))
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            previous = state["attempts"].get(attempt)
            if previous is not None and previous.get("completion_signature"):
                if previous["completion_signature"] != signature:
                    raise ExecutionRejected("completion differs; overwrite forbidden")
                old_receipt = previous["completion_receipt"]
                artifact = await self._read_artifact(conn, UUID(old_receipt["body_artifact_id"]), UUID(old_receipt["event_id"]))
                if artifact["sha256"] != content_hash(body) or artifact["kind"] != "unified_step_output":
                    raise ExecutionRejected("completed output reference mismatch")
                result = {"state": state, "receipt": old_receipt, "repeated": True}
            else:
                now = await conn.fetchval("SELECT clock_timestamp()")
                updated, _ = settle(state, attempt_id=attempt, outcome=outcome, actual_tokens=actual_tokens,
                                    actual_cost_microusd=actual_cost_microusd, usage_source_ref=usage_source_ref, now=now)
                updated["attempts"][attempt]["completion_signature"] = signature
                result = await self._append(conn, updated, kind=KINDS[2], body=body, body_id=body_id,
                                            body_kind="unified_step_output", now=now, attempt_id=attempt)
        return result

    async def load(self) -> dict:
        async with self._locked() as (conn, _):
            result = await self._load(conn)
        return result

    async def read_artifact(self, artifact_id: UUID | str) -> dict:
        async with self._locked() as (conn, _):
            # Verify owner as well as Run/tenant before handing back bodies.
            await self._load(conn)
            result = await self._read_artifact(conn, UUID(str(artifact_id)))
        return result
