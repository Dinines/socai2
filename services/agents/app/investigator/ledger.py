"""Persistent agent decision ledger (Phase 1A).

Writes investigation runs, events, and artifacts to the same Postgres tables
created by ``services/api/migrations/008_investigation_ledger.sql``.

The agents service uses raw ``asyncpg`` for these writes — it's the only
service that needs database access and we don't want to drag in the full
SQLAlchemy stack just for three tables. The API service exposes the read
side via SQLAlchemy ORM models in ``services/api/app/models/investigation.py``.

Design notes
------------
* All writes are best-effort. If the database is unreachable we log and
  continue — the agent's primary job is to investigate, not to be a
  bookkeeping service. The realtime stream is unaffected.
* The ``investigation_events`` table is append-only and per-run sequence is
  enforced by a ``UNIQUE(run_id, seq)`` constraint, so the writer must keep a
  monotonic counter per run.
* ``tenant_id`` is required by the RLS policies. The agent currently passes a
  string tenant id (e.g. ``"default"``); we resolve it to the canonical UUID
  by looking it up in the ``tenants`` table on first write per run.
"""

from __future__ import annotations

from app.workers import triage_admission

import hashlib
import json
import os
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

import asyncpg
import structlog

from app.investigator.chatops_notify import notify_chatops

logger = structlog.get_logger()


class LedgerPersistError(RuntimeError):
    """Raised by the durable write paths (e.g. :func:`persist_auto_triage`) when
    a real database error occurs, so the caller can retry / dead-letter instead
    of silently losing the outcome (issue #571). A *missing* database (no
    ``DATABASE_URL``) is NOT an error — those paths no-op and return ``False``.
    """


_POOL: asyncpg.Pool | None = None


def _normalise_dsn(url: str) -> str:
    """Convert SQLAlchemy-style DSNs to plain Postgres ones for asyncpg."""
    return url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres+asyncpg://", "postgresql://")


async def get_pool() -> asyncpg.Pool | None:
    """Lazy-init a connection pool. Returns None if no DATABASE_URL is set."""
    global _POOL
    if _POOL is not None:
        return _POOL

    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        logger.debug("ledger.disabled", reason="DATABASE_URL not set")
        return None

    try:
        _POOL = await asyncpg.create_pool(
            dsn=_normalise_dsn(dsn),
            min_size=1,
            max_size=4,
            command_timeout=10,
        )
        logger.info("ledger.pool_initialised")
        return _POOL
    except Exception as exc:  # noqa: BLE001
        logger.warning("ledger.pool_init_failed", error=str(exc))
        return None


async def close_pool() -> None:
    global _POOL
    if _POOL is not None:
        await _POOL.close()
        _POOL = None


# The canonical seed tenant (migration 001). Its slug/name can be renamed by the
# demo seed (slug 'default' → 'demo'), but this UUID is stable — so the 'default'
# placeholder ref resolves here regardless of the current slug. See issue #601.
_CANONICAL_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_PLACEHOLDER_TENANT_REFS = frozenset({"", "default"})


async def _resolve_tenant_id(conn: asyncpg.Connection, tenant_ref: str) -> uuid.UUID | None:
    """Look up the canonical tenant UUID. Accepts a UUID string, slug, or name.

    The ``"default"`` placeholder — the agents service's fallback when a caller
    doesn't pass an explicit tenant — resolves to the canonical seed tenant, or,
    in a single-tenant install, to the sole tenant. This fixes issue #601: the
    demo seed renames the seed tenant's slug from ``default`` to ``demo``, so
    ``"default"`` matched nothing and every investigation was silently skipped.

    Returns None only when the ref is genuinely ambiguous (an unknown ref, or
    ``"default"`` with several tenants and no canonical one). Callers skip the
    write rather than violate the FK — but should log loudly, not at debug.
    """
    ref = (tenant_ref or "").strip()

    # 1. An explicit UUID is trusted as-is.
    try:
        return uuid.UUID(ref)
    except (ValueError, TypeError):
        pass

    # 2. Exact slug / name match.
    row = await conn.fetchrow("SELECT id FROM tenants WHERE slug = $1 OR name = $1 LIMIT 1", ref)
    if row:
        return row["id"]

    # 3. Placeholder ref → the canonical seed tenant (stable UUID, ignoring its
    #    current slug/name), else the sole tenant in a single-tenant install.
    if ref.lower() in _PLACEHOLDER_TENANT_REFS:
        canonical = await conn.fetchrow("SELECT id FROM tenants WHERE id = $1", _CANONICAL_TENANT_ID)
        if canonical:
            return canonical["id"]
        only = await conn.fetch("SELECT id FROM tenants LIMIT 2")
        if len(only) == 1:
            return only[0]["id"]

    return None


async def resolve_tenant(tenant_ref: str) -> uuid.UUID | None:
    """Resolve a tenant ref (UUID string / slug / name) to its UUID, or None.

    Best-effort (no DB configured or lookup failure ⇒ None). Used by the shared
    graph runner to attribute per-node ledger events (issue #569)."""
    pool = await get_pool()
    if pool is None:
        return None
    try:
        async with pool.acquire() as conn:
            return await _resolve_tenant_id(conn, tenant_ref)
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.debug("ledger.resolve_tenant_failed", tenant_ref=tenant_ref, error=str(exc))
        return None


async def _set_rls_context(conn: asyncpg.Connection, tenant_id: uuid.UUID) -> None:
    """Match the API service's set_rls_context — required so the audit-log
    immutability trigger and tenant policies allow our INSERTs.

    The variable is ``app.current_tenant_id``. It said ``app.tenant_id`` until
    2026-09, which is a name no policy in this schema reads, so the scoping
    this function exists to provide was never applied: every policy fell
    through its ``current_tenant_id() IS NULL`` arm and admitted everything.
    Nothing failed, because failing open is what an unset context does — and
    because the role the services connect as bypasses RLS outright.
    """
    await conn.execute("SELECT set_config('app.current_tenant_id', $1, true)", str(tenant_id))


async def start_run(
    *,
    run_id: uuid.UUID,
    case_id: str,
    tenant_ref: str,
    alert_summary: str,
    raw_alert: dict[str, Any] | None,
    model_used: str | None = None,
) -> uuid.UUID | None:
    """Insert a new ``investigation_runs`` row. Returns the resolved tenant
    UUID on success (caller can cache it for subsequent writes), None on
    failure."""
    pool = await get_pool()
    if pool is None:
        return None

    try:
        async with pool.acquire() as conn:
            tenant_id = await _resolve_tenant_id(conn, tenant_ref)
            if tenant_id is None:
                # Loud, not debug (issue #601): the Investigation Ledger is a
                # headline capability — a silent skip leaves it off with no
                # operator signal after the run has already spent compute.
                logger.warning(
                    "ledger.skip_run",
                    reason="unknown_tenant",
                    tenant_ref=tenant_ref,
                    run_id=str(run_id),
                    case_id=case_id,
                    hint="pass an explicit tenant_id (UUID/slug); 'default' resolves only when a canonical or single tenant exists",
                )
                return None
            await _set_rls_context(conn, tenant_id)
            await conn.execute(
                """
                INSERT INTO investigation_runs
                  (id, tenant_id, case_id, alert_summary, raw_alert,
                   model_used, status, started_at, created_at)
                VALUES
                  ($1, $2, $3, $4, $5::jsonb, $6, 'running', now(), now())
                ON CONFLICT (id) DO NOTHING
                """,
                run_id,
                tenant_id,
                case_id,
                alert_summary[:8000] if alert_summary else None,
                json.dumps(raw_alert or {}),
                model_used,
            )
            logger.info(
                "ledger.run_started",
                run_id=str(run_id),
                case_id=case_id,
                tenant_id=str(tenant_id),
            )
            return tenant_id
    except Exception as exc:  # noqa: BLE001
        logger.warning("ledger.start_run_failed", run_id=str(run_id), error=str(exc))
        return None


async def record_event(
    *,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    seq: int,
    kind: str,
    agent: str,
    summary: str,
    payload: dict[str, Any] | None = None,
    input_hash: str | None = None,
    output_hash: str | None = None,
    duration_ms: int = 0,
    timestamp: datetime | None = None,
) -> uuid.UUID | None:
    """Append an immutable event row. Returns the new event id, or None."""
    pool = await get_pool()
    if pool is None:
        return None

    event_id = uuid.uuid4()
    ts = timestamp or datetime.utcnow()

    try:
        async with pool.acquire() as conn:
            await _set_rls_context(conn, tenant_id)
            await conn.execute(
                """
                INSERT INTO investigation_events
                  (id, run_id, tenant_id, seq, ts, kind, agent, summary,
                   payload, input_hash, output_hash, duration_ms, created_at)
                VALUES
                  ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11, $12, now())
                ON CONFLICT (run_id, seq) DO NOTHING
                """,
                event_id,
                run_id,
                tenant_id,
                seq,
                ts,
                kind,
                agent,
                summary[:8000],
                json.dumps(payload or {}),
                input_hash,
                output_hash,
                duration_ms,
            )
            return event_id
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ledger.record_event_failed",
            run_id=str(run_id),
            seq=seq,
            kind=kind,
            error=str(exc),
        )
        return None


async def record_artifact(
    *,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    kind: str,
    content: str,
    event_id: uuid.UUID | None = None,
) -> uuid.UUID | None:
    """Persist a large blob (LLM transcript, full report) inline.

    For now we store inline ``TEXT`` rather than offloading to S3 — the
    schema reserves ``blob_ref`` for later. SHA-256 of the content is
    always recorded so callers can verify integrity.
    """
    pool = await get_pool()
    if pool is None:
        return None

    artifact_id = uuid.uuid4()
    sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    size = len(content.encode("utf-8"))

    try:
        async with pool.acquire() as conn:
            await _set_rls_context(conn, tenant_id)
            await conn.execute(
                """
                INSERT INTO investigation_artifacts
                  (id, run_id, event_id, tenant_id, kind, content,
                   sha256, size_bytes, created_at)
                VALUES
                  ($1, $2, $3, $4, $5, $6, $7, $8, now())
                """,
                artifact_id,
                run_id,
                event_id,
                tenant_id,
                kind,
                content,
                sha,
                size,
            )
            return artifact_id
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ledger.record_artifact_failed",
            run_id=str(run_id),
            kind=kind,
            error=str(exc),
        )
        return None


async def persist_graph_result(
    *, run_id: uuid.UUID, tenant_id: uuid.UUID, seq: int,
    state: dict[str, Any], exchanges: list[dict[str, Any]],
    report_md: str, report_html: str, completion: str,
) -> uuid.UUID:
    """Confirm one graph result and its readable artifacts in one transaction.

    The first triage event/Alert are never updated here. This is the graph's
    own result; usage continues through the separate atomic usage receipt.
    """
    if (type(seq) is not int or seq < 1 or completion not in {"completed", "partial"}
            or state.get("run_id") != str(run_id) or state.get("tenant_id") != str(tenant_id)
            or not report_md or not report_html):
        raise LedgerPersistError("Invalid graph result identity or material")
    content = json.dumps(state, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    payload = {"schema": 1, "run_id": str(run_id), "tenant_id": str(tenant_id),
               "completion": completion, "status": state.get("status"),
               "verdict": state.get("verdict"), "result_sha256": digest}
    artifacts = [("graph_result", content), ("report_md", report_md), ("report_html", report_html)]
    from app.context.attack_context import attack_context_artifacts
    artifacts.extend(attack_context_artifacts(state.get("context_bundle")))
    if exchanges:
        artifacts.append(("graph_llm_exchanges", json.dumps(exchanges, sort_keys=True, ensure_ascii=False)))
    payload["artifacts"] = [{"kind": kind, "sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
                             "size_bytes": len(blob.encode("utf-8"))} for kind, blob in artifacts]
    output_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    pool = await get_pool()
    if pool is None:
        raise LedgerPersistError("Graph result database unavailable")
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await _set_rls_context(conn, tenant_id)
                owner = await conn.fetchrow(
                    "SELECT id FROM investigation_runs WHERE id=$1 AND tenant_id=$2 FOR UPDATE", run_id, tenant_id,
                )
                if owner is None:
                    raise LedgerPersistError("Graph result Run ownership missing")
                event_id = uuid.uuid4()
                inserted = await conn.fetchrow(
                    """INSERT INTO investigation_events
                       (id,run_id,tenant_id,seq,ts,kind,agent,summary,payload,output_hash,created_at)
                       VALUES ($1,$2,$3,$4,now(),'graph_result','graph:investigation',$5,$6::jsonb,$7,now())
                       ON CONFLICT (run_id,seq) DO NOTHING RETURNING id""",
                    event_id, run_id, tenant_id, seq, f"graph {completion}", json.dumps(payload), output_hash,
                )
                if inserted is None:
                    prior = await conn.fetchrow(
                        "SELECT id,tenant_id,kind,agent,payload,output_hash FROM investigation_events WHERE run_id=$1 AND seq=$2",
                        run_id, seq,
                    )
                    prior_payload = json.loads(prior["payload"]) if prior and isinstance(prior["payload"], str) else (prior["payload"] if prior else None)
                    if (prior is None or prior["tenant_id"] != tenant_id or prior["kind"] != "graph_result"
                            or prior["agent"] != "graph:investigation" or prior_payload != payload
                            or prior["output_hash"] != output_hash):
                        raise LedgerPersistError("Graph result conflicts with existing event")
                    return prior["id"]
                for kind, blob in artifacts:
                    encoded = blob.encode("utf-8")
                    await conn.execute(
                        """INSERT INTO investigation_artifacts
                           (id,run_id,event_id,tenant_id,kind,content,sha256,size_bytes,created_at)
                           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,now())""",
                        uuid.uuid4(), run_id, event_id, tenant_id, kind, blob,
                        hashlib.sha256(encoded).hexdigest(), len(encoded),
                    )
                return event_id
    except LedgerPersistError:
        raise
    except Exception as exc:
        raise LedgerPersistError("Graph result transaction failed") from exc


async def complete_run(
    *,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    status: str,
    error: str | None = None,
    iterations: int = 0,
    total_tokens: int | None = None,
    total_cost_usd: float | None = None,
    measured_call_count: int | None = None,
    estimated_cost_usd: float | None = None,
    estimated_call_count: int | None = None,
    unpriced_call_count: int | None = None,
    add_usage: bool = False,
    graph_usage_seq: int | None = None,
    resolved_models: list[str] | None = None,
) -> None:
    """Finalise the run. Status should be 'completed' or 'failed'.

    ``total_cost_usd`` is **measured** cost — what the gateway reported — and
    ``None`` means no call on this run reported one. It is not defaulted to
    ``0.0`` any more: every caller in this service omitted it, so every deep
    investigation closed with a hard-coded zero that the ledger UI rendered as
    ``$0.0000`` beside a run that had made real LLM calls.

    The counts travel with the sums so a consumer can distinguish "measured,
    and it was free" from "nothing measured it" — see migration
    ``055_cost_provenance.sql``.

    Omitted usage preserves existing values. A post-triage graph shares the
    Run with its already persisted triage, so it supplies only its measured
    additional usage with ``add_usage=True`` and an append-only graph usage
    event, committed atomically with the totals. This does not reclaim or
    resume interrupted investigations.
    """
    if add_usage:
        await _complete_graph_usage(
            run_id=run_id, tenant_id=tenant_id, seq=graph_usage_seq,
            status=status, error=error, iterations=iterations,
            usage={"tokens": total_tokens, "measured_usd": total_cost_usd,
                   "measured_calls": measured_call_count,
                   "estimated_usd": estimated_cost_usd,
                   "estimated_calls": estimated_call_count,
                   "unpriced_calls": unpriced_call_count,
                   "resolved_models": resolved_models or []},
        )
        return
    pool = await get_pool()
    if pool is None:
        return

    try:
        async with pool.acquire() as conn:
            await _set_rls_context(conn, tenant_id)
            await conn.execute(
                """
                UPDATE investigation_runs
                   SET status = $2,
                       error = $3,
                       iterations = $4,
                       total_tokens = COALESCE($5, total_tokens),
                       total_cost_usd = COALESCE($6, total_cost_usd),
                       measured_call_count = COALESCE($7, measured_call_count),
                       estimated_cost_usd = COALESCE($8, estimated_cost_usd),
                       estimated_call_count = COALESCE($9, estimated_call_count),
                       unpriced_call_count = COALESCE($10, unpriced_call_count),
                       completed_at = now()
                 WHERE id = $1 AND tenant_id = $11
                """,
                run_id,
                status,
                error,
                iterations,
                total_tokens,
                total_cost_usd,
                measured_call_count,
                estimated_cost_usd,
                estimated_call_count,
                unpriced_call_count,
                tenant_id,
            )
            logger.info(
                "ledger.run_completed",
                run_id=str(run_id),
                status=status,
                iterations=iterations,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ledger.complete_run_failed",
            run_id=str(run_id),
            error=str(exc),
        )


def _usage_amount(value: Any) -> Decimal:
    """The existing Run NUMERIC(10,4) precision; never price unknown calls."""
    try:
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("invalid cost value")
        # Existing triage writes pass float directly to asyncpg's NUMERIC
        # encoder, which preserves its binary value via Decimal(float).
        # Decimal(str(float)) would round some frozen half-unit values in the
        # opposite direction and reject their legitimate persisted totals.
        amount = Decimal(value)
        if not amount.is_finite() or amount < 0:
            raise ValueError("invalid cost value")
        return amount.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    except (ValueError, InvalidOperation) as exc:
        raise LedgerPersistError("Invalid graph usage amount") from exc


def _graph_usage_payload(usage: Any, *, run_id: uuid.UUID, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Canonical, bounded provenance for one graph's observed tracker delta."""
    if not isinstance(usage, dict):
        raise LedgerPersistError("Invalid graph usage")
    value = {}
    for key in ("tokens", "measured_calls", "estimated_calls", "unpriced_calls"):
        if type(usage.get(key)) is not int or usage[key] < 0:
            raise LedgerPersistError("Invalid graph usage counter")
        value[key] = usage[key]
    for key, count in (("measured_usd", "measured_calls"), ("estimated_usd", "estimated_calls")):
        amount = usage.get(key)
        if (value[count] == 0) != (amount is None):
            raise LedgerPersistError("Invalid graph usage cost provenance")
        value[key] = None if amount is None else float(_usage_amount(amount))
    models = usage.get("resolved_models")
    if (not isinstance(models, list) or len(models) > 200
            or any(not isinstance(model, str) or not model or len(model) > 500 for model in models)):
        raise LedgerPersistError("Invalid graph usage model provenance")
    value["resolved_models"] = sorted(set(models))
    return {"schema_version": 1, "run_id": str(run_id), "tenant_id": str(tenant_id), "usage": value}


def _graph_usage_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


async def _complete_graph_usage(
    *, run_id: uuid.UUID, tenant_id: uuid.UUID, seq: int | None,
    status: str, error: str | None, iterations: int, usage: dict[str, Any],
) -> None:
    """Append graph usage and increment its Run together, once at this seq.

    An absent/failed database is not a confirmed aggregate. Conflicting events
    never authorize another addition; ordinary callers of complete_run retain
    their existing best-effort finalisation contract.
    """
    if type(seq) is not int or seq < 1:
        raise LedgerPersistError("Graph usage event sequence required")
    payload = _graph_usage_payload(usage, run_id=run_id, tenant_id=tenant_id)
    digest = _graph_usage_hash(payload)
    pool = await get_pool()
    if pool is None:
        raise LedgerPersistError("Graph usage persistence unavailable")
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await _set_rls_context(conn, tenant_id)
                owner = await conn.fetchrow(
                    "SELECT id FROM investigation_runs WHERE id=$1 AND tenant_id=$2 FOR UPDATE",
                    run_id, tenant_id,
                )
                if owner is None:
                    raise LedgerPersistError("Graph usage Run ownership not confirmed")
                inserted = await conn.fetchrow(
                    """INSERT INTO investigation_events
                         (id, run_id, tenant_id, seq, ts, kind, agent, summary,
                          payload, output_hash, duration_ms, created_at)
                       VALUES ($1,$2,$3,$4,now(),'graph_usage','graph:investigation',
                               'Observed investigation usage; separate from first triage',
                               $5::jsonb,$6,0,now())
                       ON CONFLICT (run_id, seq) DO NOTHING RETURNING id""",
                    uuid.uuid4(), run_id, tenant_id, seq, json.dumps(payload), digest,
                )
                if inserted is None:
                    existing = await conn.fetchrow(
                        "SELECT tenant_id, kind, agent, payload, output_hash FROM investigation_events "
                        "WHERE run_id=$1 AND seq=$2", run_id, seq,
                    )
                    prior = existing["payload"] if existing is not None else None
                    if isinstance(prior, str):
                        prior = json.loads(prior)
                    if (existing is None or existing["tenant_id"] != tenant_id
                            or existing["kind"] != "graph_usage" or existing["agent"] != "graph:investigation"
                            or prior != payload or existing["output_hash"] != digest):
                        raise LedgerPersistError("Graph usage event conflicts with first accounting")
                    return
                delta = payload["usage"]
                written = await conn.execute(
                    """UPDATE investigation_runs
                          SET status=$2, error=$3, iterations=$4,
                              total_tokens=total_tokens+$5,
                              total_cost_usd=CASE WHEN $7 > 0 THEN
                                  CASE WHEN measured_call_count > 0 THEN total_cost_usd ELSE 0 END + $6
                                  ELSE total_cost_usd END,
                              measured_call_count=measured_call_count+$7,
                              estimated_cost_usd=CASE WHEN $9 > 0 THEN
                                  CASE WHEN estimated_call_count > 0 THEN estimated_cost_usd ELSE 0 END + $8
                                  ELSE estimated_cost_usd END,
                              estimated_call_count=estimated_call_count+$9,
                              unpriced_call_count=unpriced_call_count+$10,
                              completed_at=now()
                        WHERE id=$1 AND tenant_id=$11""",
                    run_id, status, error, iterations, delta["tokens"],
                    _usage_amount(delta["measured_usd"]) if delta["measured_usd"] is not None else None,
                    delta["measured_calls"],
                    _usage_amount(delta["estimated_usd"]) if delta["estimated_usd"] is not None else None,
                    delta["estimated_calls"], delta["unpriced_calls"], tenant_id,
                )
                if written != "UPDATE 1":
                    raise LedgerPersistError("Graph usage aggregate not confirmed")
    except LedgerPersistError:
        raise
    except Exception as exc:
        raise LedgerPersistError("Graph usage transaction failed") from exc


def _inserted_a_row(status: Any) -> bool:
    """True when an asyncpg command status reports a row was written.

    ``conn.execute`` returns the tag, e.g. ``"INSERT 0 1"`` for a write and
    ``"INSERT 0 0"`` when ``ON CONFLICT DO NOTHING`` suppressed it. That is
    the only signal distinguishing a first write from a replay, and the
    artifacts have no unique key of their own to lean on.
    """
    try:
        return int(str(status).rsplit(" ", 1)[-1]) > 0
    except (ValueError, IndexError):
        # An unrecognised tag means "do not know". Writing nothing is the
        # safe side: a missing transcript is visibly missing, a duplicated
        # one silently doubles every replayed run.
        return False


async def fail_stale_runs(
    *,
    older_than_seconds: float,
    reason: str,
    limit: int = 500,
) -> list[uuid.UUID]:
    """Close ``investigation_runs`` rows abandoned by a process that is gone.

    The wall-clock deadline in :func:`app.api.investigate._run_and_store` ends
    a run whose process is still alive. A restart, an OOM kill or an ordinary
    rollout leaves the row at ``'running'`` with nothing left to finish it:
    the in-memory run store is gone, so no poller, no WebSocket tail and no
    exception handler will ever write a terminal status. The Investigation
    Ledger then renders a run that never ends.

    Safe on several replicas and safe to re-run: the predicate is part of the
    ``UPDATE``, so two reapers racing the same row close it once and the loser
    simply matches nothing.

    Safe against reaping a *live* run only because the deadline exists — a run
    cannot legitimately outlast its own budget any more, so ``older_than_seconds``
    is set well beyond it (see :mod:`app.investigator.run_reaper`). Shortening
    that margin without the deadline in place would cancel healthy work.

    No RLS context is set: this is a cross-tenant maintenance sweep, and
    migration ``008_investigation_ledger.sql`` writes the policy as
    ``USING (tenant_id = current_tenant_id() OR current_tenant_id() IS NULL)``,
    whose second arm is what admits it. Named here because a future policy that
    drops that arm would turn this into a silent no-op rather than an error.

    Returns the ids closed (empty when there was nothing to do, no database is
    configured, or the sweep failed — the caller logs and retries).
    """
    pool = await get_pool()
    if pool is None:
        return []

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                UPDATE investigation_runs
                   SET status = 'failed',
                       error = COALESCE(NULLIF(error, ''), $2),
                       completed_at = now()
                 WHERE id IN (
                     SELECT id
                       FROM investigation_runs
                      WHERE status = 'running'
                        AND started_at < now() - make_interval(secs => $1::double precision)
                      ORDER BY started_at
                      LIMIT $3
                 )
                RETURNING id
                """,
                float(older_than_seconds),
                reason,
                int(limit),
            )
        closed = [row["id"] for row in rows]
        if closed:
            logger.warning(
                "ledger.stale_runs_closed",
                count=len(closed),
                older_than_seconds=older_than_seconds,
            )
        return closed
    except Exception as exc:  # noqa: BLE001 — the caller backs off and retries
        logger.warning("ledger.fail_stale_runs_failed", error=str(exc))
        return []


def _coerce_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


async def persist_auto_triage(
    *,
    run_id: uuid.UUID,
    alert_id: str | None,
    tenant_ref: str,
    alert_summary: str,
    raw_alert: dict[str, Any] | None,
    tier: str,
    verdict: str,
    confidence: float,
    rationale: str,
    findings: list[str] | None = None,
    proposed_actions: list[dict[str, Any]] | None = None,
    auto_closed: bool = False,
    iterations: int = 0,
    tokens: int = 0,
    cost_usd: float | None = None,
    measured_call_count: int = 0,
    estimated_cost_usd: float | None = None,
    estimated_call_count: int = 0,
    unpriced_call_count: int = 0,
    groundedness: float | None = None,
    ungrounded: bool | None = None,
    shadow: bool = False,
    llm_exchanges: list[dict[str, Any]] | None = None,
    organisation_memory_read: dict[str, Any] | None = None,
    tenant_skill_read: dict[str, Any] | None = None,
    knowledge_base_read: dict[str, Any] | None = None,
    recent_dispositions_read: dict[str, Any] | None = None,
    identity_context_read: dict[str, Any] | None = None,
    recovery_projection: dict[str, Any] | None = None,
    triage_admission_receipt: dict[str, Any] | None = None,
) -> bool:
    """Durably record an auto-triage outcome (issue #571) in ONE transaction:

    * upsert the ``investigation_runs`` row (idempotent on ``id``),
    * append the verdict as an immutable ``investigation_events`` row (seq 1),
    * mark the run completed, and
    * write the disposition/verdict + rationale + recommendations back onto the
      ``alerts`` row so the alert API surfaces the automated verdict.

    A validated ``triage_admission_receipt`` is the selected ordinary-live
    human-review contract: it skips the entire canonical Alert UPDATE,
    including every ai_* column. Its first result must belong to an existing
    ordinary live start; completed retries confirm the original receipt only.

    The first verdict event and its artifacts have first-write keys. The
    generic run/alert updates below are not a replay guard: the Kafka worker
    must recover completed results or own a durable start before reaching
    this write. Other callers retain their existing entry-point contracts.

    Returns ``True`` when written, ``False`` when skipped (no database
    configured, or an unknown tenant — neither is retryable). Raises
    :class:`LedgerPersistError` on a real DB error so the caller can retry /
    dead-letter. A completed run therefore always carries a non-null verdict.

    ``shadow`` (gap-closure Phase 2.1) leaves the analyst's own columns alone:
    ``disposition``, ``status`` and ``resolved_at`` keep whatever they held,
    while the run, the event and the ``ai_*`` columns are written exactly as
    they would be otherwise. ``alerts.disposition`` is the field an analyst
    fills in and the field agreement is later measured against, so a shadow
    verdict landing there would have the agent answering the question it is
    about to be graded on. The guard is in the statement rather than left to
    the caller, so a future caller that forgets to force ``auto_closed`` off
    still cannot close an alert it was only meant to observe.
    """
    advisory = triage_admission_receipt is not None
    projected = (recovery_projection or {}).get("triage_admission")
    if advisory or projected is not None:
        triage_admission.validate_persistence(
            triage_admission_receipt, projection=recovery_projection,
            run_id=str(run_id), tenant_id=str(tenant_ref), alert_id=str(alert_id or ""),
            verdict=verdict, confidence=confidence, auto_closed=auto_closed,
            recommendations=proposed_actions, raw_alert=raw_alert or {}, exchanges=llm_exchanges,
        )
    pool = await get_pool()
    if pool is None:
        return False

    verdict = (verdict or "").strip() or "needs_review"
    recommendations = proposed_actions or []
    alert_uuid = _coerce_uuid(alert_id)

    try:
        async with pool.acquire() as conn:
            tenant_id = await _resolve_tenant_id(conn, tenant_ref)
            if tenant_id is None:
                logger.debug("ledger.auto_triage_skip", reason="unknown_tenant", tenant_ref=tenant_ref)
                return False
            async with conn.transaction():
                await _set_rls_context(conn, tenant_id)
                if advisory:
                    # Ordinary Kafka already committed this exact start/claim.
                    # Do not create or reinterpret a manual, legacy or unknown Run.
                    owner = await conn.fetchrow(
                        "SELECT id, tenant_id, case_id, status, model_used, raw_alert FROM investigation_runs "
                        "WHERE id=$1 FOR UPDATE", run_id,
                    )
                    if (owner is None or str(owner["id"]) != str(run_id) or str(owner["tenant_id"]) != str(tenant_id)
                            or owner["case_id"] != str(alert_id or "")):
                        raise triage_admission.ReviewOnlyHold("Advisory Run ownership mismatch")
                    owner_raw = owner["raw_alert"]
                    if isinstance(owner_raw, str):
                        owner_raw = json.loads(owner_raw)
                    if not isinstance(owner_raw, dict) or owner_raw.get("id") != str(alert_id or ""):
                        raise triage_admission.ReviewOnlyHold("Advisory Run source identity mismatch")
                    if owner["status"] == "completed":
                        # A lost acknowledgement can reach warm pending again.
                        # Reuse the existing ordinary first-result validator on
                        # this connection; no Run/Alert/event/artifact UPDATE.
                        from app.workers import triage_delivery
                        prior = await triage_delivery._completed(
                            conn, run_id=run_id, tenant_id=tenant_id,
                            alert_id=str(alert_id or ""),
                            workflow_version=recovery_projection["workflow_version"],
                        )
                        triage_admission.validate_projection(
                            prior, run_id=str(run_id), tenant_id=str(tenant_id),
                            alert_id=str(alert_id or ""), persisted=True,
                        )
                        if triage_admission._digest(owner_raw) != triage_admission_receipt["source_raw_alert_sha256"]:
                            raise triage_admission.ReviewOnlyHold("Persisted advisory source snapshot changed")
                        if any(prior.get(key) != value for key, value in recovery_projection.items()):
                            raise triage_admission.ReviewOnlyHold("Advisory first result differs")
                        return True
                    if owner["status"] != "running" or owner["model_used"] != "kafka:auto_triage:claimed":
                        raise triage_admission.ReviewOnlyHold("Advisory start is not an ordinary live claim")
                    if await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM investigation_events "
                        "WHERE run_id=$1 AND seq IN (0,1))", run_id,
                    ):
                        raise triage_admission.ReviewOnlyHold("Partial advisory first result requires inspection")
                await conn.execute(
                    """
                    INSERT INTO investigation_runs
                      (id, tenant_id, case_id, alert_summary, raw_alert,
                       model_used, status, started_at, created_at)
                    VALUES
                      ($1, $2, $3, $4, $5::jsonb, $6, 'running', now(), now())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    run_id,
                    tenant_id,
                    str(alert_id or ""),
                    (alert_summary or "")[:8000] or None,
                    json.dumps(raw_alert or {}),
                    f"kafka:auto_triage:{tier}",
                )
                # The model call that produced the verdict, at seq 0 so it
                # precedes it (issue #1276). This path recorded no prompt at
                # all, so the decision taken on every fused alert was the one
                # decision in the platform that could not be replayed.
                #
                # seq 0 rather than renumbering: seq 1 is the verdict's key
                # under `ON CONFLICT (run_id, seq)`, the run id is
                # deterministic, and moving the verdict would let a replay
                # write a second one. Escalation graph steps start at seq 2
                # (`run_escalation(..., seq_start=1)`), so 0 is the free slot
                # and it is also the one the manual path puts its first
                # prompt in.
                for exchange in (llm_exchanges or [])[:1]:
                    await conn.execute(
                        """
                        INSERT INTO investigation_events
                          (id, run_id, tenant_id, seq, ts, kind, agent, summary,
                           payload, input_hash, output_hash, duration_ms, created_at)
                        VALUES
                          ($1, $2, $3, 0, now(), 'llm_call', $4, $5, $6::jsonb, $7, $8, $9, now())
                        ON CONFLICT (run_id, seq) DO NOTHING
                        """,
                        uuid.uuid4(),
                        run_id,
                        tenant_id,
                        str(exchange.get("agent") or "auto_triage"),
                        f"model call: {exchange.get('purpose') or 'triage'}"[:8000],
                        json.dumps(exchange),
                        exchange.get("input_hash"),
                        exchange.get("output_hash"),
                        int(exchange.get("duration_ms") or 0),
                    )

                verdict_event_id = uuid.uuid4()
                # The hashes travel onto the verdict too. An auditor asking
                # "what produced this verdict" reads the verdict row, and a
                # null `input_hash` there is indistinguishable from a run that
                # never called a model — which is a real state on the
                # deterministic path and must stay tellable apart.
                first = (llm_exchanges or [{}])[0]
                written = await conn.execute(
                    """
                    INSERT INTO investigation_events
                      (id, run_id, tenant_id, seq, ts, kind, agent, summary,
                       payload, input_hash, output_hash, duration_ms, created_at)
                    VALUES
                      ($1, $2, $3, 1, now(), 'triage_verdict', $4, $5, $6::jsonb, $7, $8, $9, now())
                    ON CONFLICT (run_id, seq) DO NOTHING
                    """,
                    verdict_event_id,
                    run_id,
                    tenant_id,
                    f"auto_triage:{tier}",
                    ("review_only: human review required; effective confidence unknown; numeric 0 policy sentinel"
                     if advisory else f"verdict={verdict} confidence={confidence:.2f}")[:8000],
                    json.dumps(
                        {
                            "verdict": verdict,
                            "confidence": confidence,
                            "rationale": rationale,
                            "findings": findings or [],
                            "proposed_actions": recommendations,
                            "auto_closed": auto_closed,
                            **({"recovery": recovery_projection} if recovery_projection is not None else {}),
                            **({"organisation_memory_read": organisation_memory_read} if organisation_memory_read is not None else {}),
                            **({"tenant_skill_read": tenant_skill_read} if tenant_skill_read is not None else {}),
                            **({"knowledge_base_read": knowledge_base_read} if knowledge_base_read is not None else {}),
                            **({"recent_dispositions_read": recent_dispositions_read} if recent_dispositions_read is not None else {}),
                            **({"identity_context_read": identity_context_read} if identity_context_read is not None else {}),
                        }
                    ),
                    first.get("input_hash"),
                    first.get("output_hash"),
                    int(first.get("duration_ms") or 0),
                )

                # The literal transcript, attached to the verdict event.
                # `GET /investigations/{run}/explain?step=1` inlines the
                # artifacts of the focal event, which is how the MCP
                # `aisoc_explain_step` tool keeps its documented promise to
                # return "the prompt, response, and tools used".
                #
                # Written inline rather than through `record_artifact`
                # because that acquires its own connection, and a transcript
                # committed separately from the verdict it explains can
                # survive a rollback of the verdict.
                #
                # Skipped entirely when the verdict row already existed.
                # `investigation_artifacts` has no natural key to conflict
                # on, so without this a replay of a deterministic run id
                # would append a second copy of the transcript on every
                # pass while the events it explains stayed at one.
                if not _inserted_a_row(written):
                    llm_exchanges = []
                else:
                    # Adopted material/read states share the first-write
                    # verdict transaction. A retry does not replace or append
                    # either source's immutable receipt.
                    for kind, receipt in (("organisation_memory_read", organisation_memory_read),
                                          ("tenant_skill_read", tenant_skill_read),
                                          ("knowledge_base_read", knowledge_base_read),
                                          ("recent_dispositions_read", recent_dispositions_read),
                                          ("identity_context_read", identity_context_read)):
                        if receipt is None:
                            continue
                        blob = json.dumps(receipt, sort_keys=True, ensure_ascii=False)
                        await conn.execute(
                            """
                            INSERT INTO investigation_artifacts
                              (id, run_id, event_id, tenant_id, kind, content,
                               sha256, size_bytes, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now())
                            """,
                            uuid.uuid4(), run_id, verdict_event_id, tenant_id,
                            kind, blob, hashlib.sha256(blob.encode("utf-8")).hexdigest(),
                            len(blob.encode("utf-8")),
                        )
                for exchange in llm_exchanges or []:
                    for kind, text in (
                        ("llm_prompt", exchange.get("prompt")),
                        ("llm_response", exchange.get("response")),
                    ):
                        if not text:
                            continue
                        blob = str(text)
                        await conn.execute(
                            """
                            INSERT INTO investigation_artifacts
                              (id, run_id, event_id, tenant_id, kind, content,
                               sha256, size_bytes, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now())
                            """,
                            uuid.uuid4(),
                            run_id,
                            verdict_event_id,
                            tenant_id,
                            kind,
                            blob,
                            hashlib.sha256(blob.encode("utf-8")).hexdigest(),
                            len(blob.encode("utf-8")),
                        )
                await conn.execute(
                    # `total_cost_usd` is measured cost only. It used to carry
                    # a list-price guess keyed on a gateway alias, so a local
                    # deployment that spent nothing accrued a per-alert dollar
                    # figure here and everywhere reading from here.
                    #
                    # COALESCE on both sums, matching `complete_run` above.
                    # Both columns are NOT NULL, and `None` is the ordinary
                    # value of `estimated_cost_usd` whenever no estimate was
                    # made — which is every run against a local model, because
                    # there is no list price for `ollama_chat/...`. Binding it
                    # directly made the UPDATE violate the constraint, so the
                    # whole transaction rolled back, the worker retried three
                    # times and dead-lettered the alert. With a model shipped in
                    # CORE that is not an edge case: it was *every* auto-triage
                    # run on a default install, and the console showed no
                    # verdict for an LLM call that had genuinely happened.
                    #
                    # Leaving the column at its DEFAULT 0 is not a claim that
                    # the run cost nothing — `estimated_call_count` and
                    # `unpriced_call_count` are what carry that distinction, and
                    # they are written from the same tuple.
                    """
                    UPDATE investigation_runs
                       SET status = 'completed', iterations = $2,
                           total_tokens = $3,
                           total_cost_usd = COALESCE($4, total_cost_usd),
                           measured_call_count = $5,
                           estimated_cost_usd = COALESCE($6, estimated_cost_usd),
                           estimated_call_count = $7,
                           unpriced_call_count = $8,
                           completed_at = now(),
                           model_used = CASE WHEN model_used = 'kafka:auto_triage:claimed' THEN $9 ELSE model_used END,
                           raw_alert = CASE WHEN model_used = 'kafka:auto_triage:claimed' THEN $10::jsonb ELSE raw_alert END,
                           alert_summary = CASE WHEN model_used = 'kafka:auto_triage:claimed' THEN $11 ELSE alert_summary END
                     WHERE id = $1
                    """,
                    run_id,
                    iterations,
                    tokens,
                    cost_usd,
                    measured_call_count,
                    estimated_cost_usd,
                    estimated_call_count,
                    unpriced_call_count,
                    f"kafka:auto_triage:{tier}",
                    json.dumps(raw_alert or {}),
                    (alert_summary or "")[:8000] or None,
                )
                if alert_uuid is not None and not advisory:
                    # Surface the automated verdict on the alert row. Status is
                    # only advanced to 'resolved' when auto-triage auto-closed a
                    # benign/FP alert at high confidence; otherwise the alert
                    # stays open for escalation / human review.
                    await conn.execute(
                        """
                        UPDATE alerts
                           SET disposition = CASE WHEN $10 THEN disposition ELSE $3 END,
                               ai_score = $4,
                               ai_summary = $5,
                               ai_recommendations = $6::jsonb,
                                   -- If the agent produced a verdict, the alert has
                               -- been triaged: surface that on the status badge
                               -- so investigated alerts stop showing as 'new'.
                               -- Never downgrades a further-along status; shadow
                               -- runs leave it untouched.
                               status = CASE
                               WHEN $7 AND NOT $10 THEN 'resolved'
                               WHEN status = 'new' AND NOT $10 THEN 'triaged'
                               ELSE status
                           END,
                               resolved_at = CASE WHEN $7 AND NOT $10 THEN now() ELSE resolved_at END,
                               -- Nullable on purpose: NULL is "not scored",
                               -- which is a different fact from "scored zero".
                               -- The deterministic path never assesses
                               -- groundedness, and defaulting it would read as
                               -- every such verdict being unsupported.
                               triage_groundedness = $8,
                               triage_ungrounded = $9,
                               updated_at = now()
                         WHERE id = $1 AND tenant_id = $2
                        """,
                        alert_uuid,
                        tenant_id,
                        verdict[:50],
                        float(confidence),
                        (rationale or "")[:8000] or None,
                        json.dumps(recommendations),
                        auto_closed,
                        float(groundedness) if groundedness is not None else None,
                        ungrounded,
                        shadow,
                    )
        logger.info(
            "ledger.auto_triage_persisted",
            run_id=str(run_id),
            verdict=verdict,
            auto_closed=auto_closed,
            shadow=shadow,
            alert_id=str(alert_id or ""),
        )
        return True
    except Exception as exc:  # noqa: BLE001 — re-raised as a typed, retryable error
        logger.warning("ledger.auto_triage_persist_failed", run_id=str(run_id), error=str(exc))
        raise LedgerPersistError(str(exc)) from exc


async def raise_approval(
    *,
    tenant_ref: str,
    run_id: uuid.UUID | None,
    alert_id: Any,
    title: str,
    summary: str,
    risk_level: str,
    action: dict[str, Any],
    requested_by: str = "agent",
) -> uuid.UUID | None:
    """Queue a proposed action for human sign-off, returning the approval id.

    The ``agent_approvals`` table, its API and the whole responder-app
    approvals screen already existed. Nothing ever inserted a row: the API
    docstring said "the agents service calls this" and a grep of this service
    for ``approvals`` returned nothing. So the queue was structurally empty on
    every deployment, and the feature was indistinguishable from a working one
    that simply had no pending work.

    Written from here rather than over HTTP because this is where the rest of
    the triage outcome is persisted, under the same pool and the same RLS
    context, so an approval cannot end up recorded against a verdict that
    failed to save. Best-effort in the same sense as the other ledger writes:
    no database or an unknown tenant is a no-op, because a triage verdict is
    still worth having without one.

    ``ON CONFLICT DO NOTHING`` on the deterministic id makes a Kafka replay
    re-raise the same approval rather than a second copy of it — an operator
    seeing the same containment request twice cannot tell which one is live.
    """
    pool = await get_pool()
    if pool is None:
        return None
    try:
        async with pool.acquire() as conn:
            tenant_id = await _resolve_tenant_id(conn, tenant_ref)
            if tenant_id is None:
                logger.warning(
                    "ledger.approval_skipped_unknown_tenant",
                    tenant_ref=tenant_ref,
                    run_id=str(run_id) if run_id else None,
                )
                return None
            await _set_rls_context(conn, tenant_id)
            approval_id = _deterministic_approval_id(tenant_id, run_id, action)
            await conn.execute(
                """
                INSERT INTO agent_approvals
                    (id, tenant_id, run_id, alert_id, requested_by, title,
                     summary, risk_level, action, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending', now(), now())
                ON CONFLICT (id) DO NOTHING
                """,
                approval_id,
                tenant_id,
                run_id,
                _coerce_uuid(alert_id),
                requested_by[:120],
                title[:200],
                summary,
                risk_level[:20],
                json.dumps(action),
            )
        # Outside the connection block: the approval is durable now, and
        # Slack being slow must not hold a database connection open.
        await notify_chatops(approval_id, title=title, summary=summary, risk_level=risk_level, action=action)
        # The id is returned whether the insert landed or the conflict
        # clause fired: either way this is the approval that governs this
        # action, and a replay must point at the one already queued.
        return approval_id
    except Exception as exc:  # noqa: BLE001 — an approval write must not fail triage
        logger.warning(
            "ledger.raise_approval_failed",
            tenant_ref=tenant_ref,
            run_id=str(run_id) if run_id else None,
            error=str(exc),
        )
        return None


def _deterministic_approval_id(
    tenant_id: uuid.UUID,
    run_id: uuid.UUID | None,
    action: dict[str, Any],
) -> uuid.UUID:
    """One approval per (tenant, run, action type, target), stable across replays."""
    key = "|".join(
        [
            str(tenant_id),
            str(run_id or ""),
            str(action.get("action_type") or ""),
            str(action.get("target") or ""),
        ]
    )
    return uuid.uuid5(_APPROVAL_NAMESPACE, key)


#: Fixed namespace so an approval id is reproducible across processes and
#: restarts. Any constant UUID would do; this one is arbitrary and permanent.
_APPROVAL_NAMESPACE = uuid.UUID("6f1d3b6e-7a4f-5c2b-9f0a-2d5b8c1e4a37")


async def record_suppression(
    *,
    tenant_ref: str,
    signature: str,
    alert_id: Any,
    disposition: str,
    prior_author: str,
) -> bool:
    """Durably record that a repeat alert was auto-suppressed from prior outcome
    memory (Wave 1), so the compounding-reduction metric is measured, not
    estimated. Best-effort: no DB / unknown tenant => no-op (returns False)."""
    pool = await get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            tenant_id = await _resolve_tenant_id(conn, tenant_ref)
            if tenant_id is None:
                return False
            await conn.execute(
                """
                INSERT INTO aisoc_outcome_suppressions
                    (id, tenant_id, signature, alert_id, disposition, prior_author, created_at)
                VALUES (uuid_generate_v4(), $1, $2, $3, $4, $5, now())
                """,
                tenant_id,
                signature,
                _coerce_uuid(alert_id),
                disposition,
                prior_author,
            )
        return True
    except Exception as exc:  # noqa: BLE001 — metric write is best-effort
        logger.debug("ledger.record_suppression_failed", signature=signature, error=str(exc))
        return False
