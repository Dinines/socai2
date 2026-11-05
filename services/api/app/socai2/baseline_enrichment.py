"""C2 background reads, recorded on the already claimed baseline Run.

No scheduler, retries, model calls, or Run completion here. A committed running
stage is a claim, not a reusable pending record. Crash uncertainty stays visible.
"""
import asyncio
from uuid import uuid4

from sqlalchemy import func, insert, null, select, update
from sqlalchemy.exc import DBAPIError

from app.models.socai2 import RunSteps

from . import baseline_enrichment_sources as sources
from .baseline_context import MAX_CONTEXT_BYTES, reference
from .baseline_context import SCHEMA as C1_SCHEMA
from .baseline_contracts import Limits
from .baseline_optional_sources import SourceUnavailable
from .baseline_store import F, StoreError, digest, encoded

S = RunSteps.__table__
SCHEMA = "socai2.baseline-enrichment.v1"
MAX_QUERY_ROWS = 200


def error(code, occurred_at):
    return {"code": code, "message": code, "retryable": False, "occurred_at": occurred_at.isoformat()}


def citation_roles(payload):
    """Query receipts never become activity observations by being model-visible."""
    roles = {}
    if payload.get("state") == "completed":
        for i, row in enumerate(payload.get("rows") or []):
            base = f"$.rows.{i}"
            roles[base] = "source_label"
            if payload["tool_name"] == "ueba":
                roles[base] = "prior_analysis"
            if payload["tool_name"] == "history":
                if row["record"].get("triage"):
                    roles[base + ".record.triage"] = "prior_analysis"
                if row["record"].get("feedback"):
                    roles[base + ".record.feedback"] = "human_statement"
    return roles


class BaselineEnrichment:
    def __init__(self, service):
        self.service = service

    async def artifact(self, store, run, step_id, payload, kind, refs):
        identity = uuid4()
        # Attach the step at INSERT time: artifacts are immutable thereafter.
        body = encoded(payload)
        await store.db.execute(insert(F).values(id=identity, tenant_id=store.tenant_id,
            case_id=run["case_id"], run_id=run["id"], step_id=step_id, kind=kind,
            schema_version=SCHEMA, content_json=payload, mime_type="application/json",
            sha256=digest(payload), size_bytes=len(body), captured_at=await store.now(),
            material_state="complete", source_refs=refs, created_by=run["requested_by"],
            retention={"original_size_bytes": len(body), "retained_size_bytes": len(body),
                "original_sha256": digest(payload), "retained_sha256": digest(payload),
                "truncated": False, "reason": None, "omitted_paths": []}))
        return identity

    async def sequence(self, store, run_id):
        return (await store.db.execute(select(func.coalesce(func.max(S.c.seq), 0)).where(
            *store.where(S, S.c.run_id == run_id)))).scalar_one() + 1

    async def locked(self, store, case_id, run_id):
        await store.case(case_id)
        return await store.run(case_id, run_id)

    async def execute(self, tenant_id, case_id, run_id):
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            prior = await store.one(select(S).where(*store.where(S,
                S.c.run_id == run_id, S.c.stage_code == "C2", S.c.kind == "stage")))
            if prior:
                if prior["state"] != "completed":
                    raise StoreError("enrichment_already_claimed")
                saved = await store.one(select(F).where(*store.where(F,
                    F.c.id == prior["output_artifact_id"], F.c.run_id == run_id)))
                if not saved or digest(saved["content_json"]) != saved["sha256"]:
                    raise StoreError("enrichment_receipt_invalid")
                return saved["content_json"]
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            if await store.one(select(S.c.id).where(*store.where(S, S.c.run_id == run_id,
                    S.c.state.in_(["planned", "running", "unknown"]))).limit(1)):
                raise StoreError("baseline_step_in_progress")
            context = await store.read_context(case_id, run_id)
            c1 = await store.one(select(F.c.id).where(*store.where(F, F.c.run_id == run_id,
                F.c.schema_version == C1_SCHEMA, F.c.kind == "source_snapshot")))
            stage_id = uuid4()
            refs = [reference("artifact", c1["id"], "execution_receipt")]
            await store.db.execute(insert(S).values(id=stage_id, tenant_id=tenant_id, run_id=run_id,
                seq=await self.sequence(store, run_id), kind="stage", stage_code="C2", state="running",
                name="baseline_background_enrichment", implementation_version=sources.VERSION,
                started_at=await store.now(), input_artifact_id=c1["id"]))
        # Claim is committed before any source read. Replays cannot re-dispatch.
        outputs = []
        try:
            plan = sources.selection_plan(context)
            for choice in plan:
                outputs.append(await self.source(tenant_id, case_id, run_id, stage_id,
                    choice["source"], context, refs, selection=choice))
            async with self.service.transaction(tenant_id) as store:
                run = await self.locked(store, case_id, run_id)
                if run["state"] != "running":
                    raise StoreError("baseline_not_running")
                summary = {"schema_version": SCHEMA, "case_id": str(case_id), "run_id": str(run_id),
                    "scope": context.scope.model_dump(mode="json"), "sources": outputs,
                    "selection_policy": "frozen_object_relevance.v1", "selection_plan": plan,
                    "coverage_complete": all(o["outcome"] in {"data", "empty", "not_applicable"}
                        and not o["truncated"] for o in outputs),
                    "limitations": ["background_queries_are_not_complete_case_investigation",
                                    "empty_or_unavailable_sources_are_not_counterevidence"],
                    "captured_at": (await store.now()).isoformat()}
                identity = await self.artifact(store, run, stage_id, summary, "source_snapshot", refs)
                await store.db.execute(update(S).where(*store.where(S, S.c.id == stage_id)).values(
                    state="completed", ended_at=await store.now(), output_artifact_id=identity))
            return summary
        except (Exception, asyncio.CancelledError):
            async with self.service.transaction(tenant_id) as store:
                await self.locked(store, case_id, run_id)
                await store.db.execute(update(S).where(*store.where(S, S.c.run_id == run_id,
                    S.c.stage_code == "C2", S.c.state == "running")).values(
                        state="unknown", error=error("enrichment_dispatch_uncertain", await store.now())))
                await store.mark_unknown(case_id, run_id)
            raise

    async def source(self, tenant_id, case_id, run_id, stage_id, source, context, refs, *, selection=None):
        keys = sources.selectors(context, source)
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            limits = Limits.model_validate(run["limits"])
            now = await store.now()
            dispatch_deadline = (asyncio.get_running_loop().time() + (limits.deadline_at - now).total_seconds()
                                 if limits.deadline_at else None)
            used = (await store.db.execute(select(func.count()).select_from(S).where(*store.where(S,
                S.c.run_id == run_id, S.c.kind == "tool", S.c.state.not_in(["planned", "skipped"])
            )))).scalar_one()
            # The full executor needs evidence capacity after background reads.
            # Keep standalone C2 and already persisted receipts on their original
            # contract; reserve within, never in addition to, the total budget.
            reserved = (min(2, (limits.max_tool_calls or 0) // 2)
                if run["executor_version"] == "socai2.baseline-executor.v1" else 0)
            reason = None
            if not sources.connected(source):
                reason = "source_not_connected"
            elif not keys:
                reason = "no_supported_frozen_objects"
            elif source == "history" and context.scope.window_start is None:
                reason = "history_window_not_defined"
            elif limits.max_tool_calls is None or limits.max_rows_per_query is None or limits.deadline_at is None:
                reason = "execution_limits_not_defined"
            elif used >= limits.max_tool_calls or limits.max_rows_per_query == 0:
                reason = "tool_budget_exhausted"
            elif reserved and used >= limits.max_tool_calls - reserved:
                reason = "tool_budget_reserved_for_evidence"
            elif limits.deadline_at <= now:
                reason = "deadline_reached"
            args = {"tool_name": source, "contract_version": sources.VERSION,
                "scope": context.scope.model_dump(mode="json"),
                "limit": min(limits.max_rows_per_query or 0, MAX_QUERY_ROWS),
                "parameters": {"selectors": keys, "source_scope": "tenant_only",
                    "time_mode": "event_window" if source == "history" else "current_record_snapshot"}}
            if reserved:
                args["parameters"]["reserved_tool_calls_for_evidence"] = reserved
            if selection is not None:
                args["parameters"]["selection"] = selection
            step_id = uuid4()
            await store.db.execute(insert(S).values(id=step_id, tenant_id=tenant_id, run_id=run_id,
                seq=await self.sequence(store, run_id), parent_step_id=stage_id, kind="tool", stage_code="C2",
                state="running" if reason is None else "planned", name=source,
                provider=("neo4j_identity" if source == "graph" else "postgresql") if sources.connected(source) else None,
                implementation_version=sources.VERSION, started_at=now if reason is None else None,
                actual_args=args))
            request_id = await self.artifact(store, run, step_id, args, "tool_request", refs)
            await store.db.execute(update(S).where(*store.where(S, S.c.id == step_id)).values(input_artifact_id=request_id))
        state, rows, captured, truncated = "skipped", None, now, False
        observed_rows, truncation_reasons = None, []
        source_metadata = {}
        if reason is None:
            try:
                async with asyncio.timeout_at(dispatch_deadline):
                    found = await sources.query(self.service, tenant_id, source, args)
                    rows, captured = found[:2]
                    source_metadata = found[2] if len(found) > 2 else {}
                observed_rows = len(rows)
                truncated = len(rows) > args["limit"]
                if truncated:
                    truncation_reasons.append("row_limit")
                if source_metadata.get("source_truncated_count", 0):
                    truncated = True
                    truncation_reasons.append("upstream_row_limit")
                rows = rows[:args["limit"]]
                # Whole rows only. Mark omitted rows; never clip JSON or a fact.
                if len(encoded(rows)) > MAX_CONTEXT_BYTES:
                    truncation_reasons.append("retained_row_bytes_limit")
                while rows and len(encoded(rows)) > MAX_CONTEXT_BYTES:
                    rows.pop()
                    truncated = True
                state = "completed"
            except TimeoutError:
                state, reason, rows = "timeout", "source_deadline_exceeded", None
            except SourceUnavailable as exc:
                state, reason, rows = "failed", "source_unavailable", None
                source_metadata = {"unavailable_reason": str(exc)}
            except DBAPIError as exc:
                code = getattr(exc.orig, "sqlstate", None)
                state, rows = "failed", None
                reason = ("source_unavailable" if code in {"42P01", "42703", "42501"} else
                          "source_query_timeout" if code == "57014" else "source_query_failed")
                if code == "57014":
                    state = "timeout"
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            result = {"schema_version": SCHEMA, "tool_name": source, "contract_version": sources.VERSION,
                "actual_args": args, "state": state, "rows": rows,
                "returned_rows": len(rows) if rows is not None else None, "truncated": truncated,
                "query_id": "local-step:" + str(step_id) if state != "skipped" else None,
                "error": error(reason, await store.now()) if reason else None, "captured_at": captured.isoformat()}
            result_id = await self.artifact(store, run, step_id, result, "tool_response", refs)
            await store.db.execute(update(S).where(*store.where(S, S.c.id == step_id)).values(
                state=state, ended_at=await store.now(), output_artifact_id=result_id,
                returned_rows=result["returned_rows"], error=result["error"] or null()))
        outcome = ("data" if rows else "empty") if state == "completed" else {
            "source_not_connected": "unavailable", "source_unavailable": "unavailable",
            "no_supported_frozen_objects": "not_applicable", "tool_budget_exhausted": "not_attempted_budget",
            "tool_budget_reserved_for_evidence": "not_attempted_budget",
            "deadline_reached": "not_attempted_deadline"}.get(reason, state)
        if state == "completed" and truncated and not rows:
            outcome = "omitted"
        return {"source": source, "step_id": str(step_id), "artifact_id": str(result_id),
            "outcome": outcome, "reason": reason, "returned_rows": result["returned_rows"],
            "observed_rows_in_bounded_fetch": observed_rows, "truncation_reasons": truncation_reasons,
            "source_metadata": source_metadata,
            "truncated": truncated, "planned_object_keys": sorted({k["object_key"] for k in keys}),
            "queried_object_keys": sorted({k["object_key"] for k in keys}) if state != "skipped" else [],
            "queried_alert_ids": sorted({aid for k in keys for aid in k["alert_ids"]}) if state != "skipped" else [],
            "limitations": sources.LIMITATIONS.get(source, ["adapter_not_connected"]),
            "citation_roles": citation_roles(result)}
