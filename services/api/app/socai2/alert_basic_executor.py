"""A: three bounded background queries and one model; no legacy side effects."""
import asyncio
from app.core.operational_logging import log_context
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import func, insert, null, select, update
from sqlalchemy.exc import DBAPIError

from . import ai_delivery_store
from . import baseline_enrichment_sources as sources
from .alert_model_boundary import build
from .alert_output_adapter import schema
from .baseline_analysis import budget_reason
from .baseline_analysis_model import TenantChatGateway, usage
from .baseline_context import reference
from .baseline_contracts import Limits
from .baseline_enrichment import S, error
from .baseline_store import StoreError, digest, encoded
from .model_errors import ModelCallError
from .model_protocol import prepare_request
from .runtime_policy import active_policy, execution_policy
from .stage_result_contracts import ALERT_EXECUTOR_VERSION as VERSION
from .stage_results import F, R, artifact


class AlertBasicExecutor:
    def __init__(self, service, *, gateway=None, query=None):
        self.service = service
        self.gateway = gateway or TenantChatGateway()
        self.query = query or sources.query

    async def locked(self, store, run_id):
        run, _, source = await self.service.locked(store, run_id)
        if run["kind"] != "alert_basic" or run["executor_version"] != VERSION or run["state"] != "running":
            raise StoreError("alert_execution_not_running")
        return run, source

    async def save(self, store, run, step, kind, payload):
        identity = uuid4()
        await artifact(store, run, identity, kind, payload, await store.now(),
            [reference("artifact", run["input_artifact_id"], "execution_receipt")], step_id=step, schema_version=VERSION)
        return identity

    async def step(self, store, run, kind, name, *, state="running", parent=None, args=None):
        identity = uuid4()
        seq = (await store.db.execute(select(func.coalesce(func.max(S.c.seq), 0)).where(
            *store.where(S, S.c.run_id == run["id"])))).scalar_one() + 1
        await store.db.execute(insert(S).values(id=identity, tenant_id=store.tenant_id, run_id=run["id"],
            seq=seq, kind=kind, stage_code="A", name=name, state=state, parent_step_id=parent,
            implementation_version=VERSION, actual_args=args if args is not None else null(),
            started_at=await store.now() if state == "running" else None))
        return identity

    async def outcome(self, tenant, claim):
        async with self.service.transaction(tenant, readonly=True) as store:
            run = await store.one(select(R).where(*store.where(R, R.c.id == claim["run_id"])))
            return {**claim, "state": run["state"], "stop_reason": run["stop_reason"]}

    async def execute(self, tenant, alert_id, operation_key, *, requested_by=None, dispatch_context=None, frozen_source=None):
        profile = execution_policy("alert_io").alert_io
        claim = await self.service.begin(tenant, "alert_basic", alert_id, operation_key, producer=VERSION, limits=None,
            requested_by=requested_by, dispatch_context=dispatch_context, frozen_source=frozen_source)
        if not claim["newly_claimed"]:
            return await self.outcome(tenant, claim)
        rid = claim["run_id"]
        try:
            async with self.service.transaction(tenant) as store:
                run, source = await self.locked(store, rid)
                frozen = await store.one(select(F).where(*store.where(F, F.c.id == run["input_artifact_id"], F.c.run_id == rid)))
                if (frozen["material_state"] != "complete" or digest(source) != frozen["sha256"]
                        or len(encoded(source)) != frozen["size_bytes"]):
                    raise StoreError("alert_input_snapshot_invalid", 422)
                stage = await self.step(store, run, "stage", "alert_basic_analysis")
            queries = [await self.background(tenant, rid, stage, source, name) for name in ("assets", "history", "threat_intel")]
            try:
                messages, source_map, data, prepared = build(source, claim["input_artifact_id"], queries, profile,
                    execution_time=run["started_at"].isoformat())
                response_format = schema(source_map)
            except StoreError as exc:
                await self.fail(tenant, rid, stage, exc.code)
                return await self.outcome(tenant, claim)
            if not await self.gateway.configure(self.service, tenant):
                await self.fail(tenant, rid, stage, "model_not_configured")
                return await self.outcome(tenant, claim)
            attempt = 0
            body = {"model": self.gateway.model, "messages": messages, "max_tokens": active_policy().model.output_tokens["A"], "temperature": 0,
                    "response_format": response_format}
            body = prepare_request(self.gateway, body)
            async with self.service.transaction(tenant) as store:
                meter_run, _ = await self.locked(store, rid)
                meter_seconds = (Limits.model_validate(meter_run["limits"]).deadline_at - await store.now()).total_seconds()
            try:
                from .token_budget import measure_with_deadline
                measurement = await measure_with_deadline(self.gateway, body, "A", meter_seconds)
            except StoreError as exc:
                await self.fail(tenant, rid, stage, exc.code)
                return await self.outcome(tenant, claim)
            async with self.service.transaction(tenant) as store:
                run, _ = await self.locked(store, rid)
                limits, now = Limits.model_validate(run["limits"]), await store.now()
                steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == rid)))).mappings().all()
                reason = budget_reason(steps, limits, len(encoded(body)), now, measurement=measurement)
                if not reason:
                    model = await self.step(store, run, "model", "alert_triage_and_explanation", parent=stage)
                    request = {"schema_version": VERSION, "provider": self.gateway.provider, "model": self.gateway.model,
                        "schema_profile": getattr(self.gateway, "schema_profile", "standard"),
                        "body": body, "source_map": source_map, "input_omissions": data["omissions"],
                        "view_coverage": data["view_coverage"], "view_limitations": data["view_limitations"],
                        "input_omission_details": data["omission_details"],
                        "input_omission_detail_count": data["omission_detail_count"],
                        "input_omission_details_truncated": data["omission_details_truncated"],
                        "reserved_token_upper_bound": measurement["reserved_total_tokens"], "token_measurement": measurement,
                        "correction": None}
                    request["alert_boundary"] = prepared["boundary"]
                    request_id = await self.save(store, run, model, "model_request", request)
                    await store.db.execute(update(S).where(*store.where(S, S.c.id == model)).values(
                        input_artifact_id=request_id, provider=self.gateway.provider))
                    deadline = asyncio.get_running_loop().time() + (limits.deadline_at - now).total_seconds()
            if reason:
                await self.fail(tenant, rid, stage, reason)
                return await self.outcome(tenant, claim)
            # Both exact request and running claim have committed before I/O.
            try:
                with log_context(run_id=rid, step_id=model, stage="A", operation="model_complete"):
                    async with asyncio.timeout_at(deadline):
                        payload = await self.gateway.complete(body, max(0, deadline - asyncio.get_running_loop().time()))
            except ModelCallError as exc:
                async with self.service.transaction(tenant) as store:
                    run, _ = await self.locked(store, rid)
                    response_id = await self.save(store, run, model, "model_response",
                        {"schema_version": VERSION, **exc.payload(), "usage": usage(None)})
                    await store.db.execute(update(S).where(*store.where(S, S.c.id == model)).values(
                        output_artifact_id=response_id, usage=usage(None)))
                    if exc.rejection_code:
                        now = await store.now()
                        await store.db.execute(update(S).where(*store.where(S, S.c.id == model)).values(
                            state="failed", ended_at=now, error=error(exc.rejection_code, now)))
                if exc.rejection_code:
                    await self.fail(tenant, rid, stage, exc.rejection_code)
                    return await self.outcome(tenant, claim)
                raise  # Keep the existing uncertainty transition; never retry or adopt.
            from .citation_quality import seal
            recorded = usage(payload)
            async with self.service.transaction(tenant) as store:
                run, _ = await self.locked(store, rid)
                original_id = await self.save(store, run, model, "source_snapshot",
                    {"schema_version": VERSION, "artifact_role": "model_original_response",
                     "request_artifact_id": str(request_id), "attempt": attempt, "raw": payload, "usage": recorded})
            received = ai_delivery_store.receive_payload("A", payload, prepared, original_id, recorded, request)
            result, rejection = received["result"], received["rejection"]
            citation_review = received["quality"]
            citation_review.update(original_response_artifact_id=str(original_id), request_artifact_id=str(request_id), attempt=attempt)
            complete_content = received["content"]
            async with self.service.transaction(tenant) as store:
                run, _ = await self.locked(store, rid)
                response_id = await self.save(store, run, model, "model_response",
                    {"schema_version": VERSION, "raw": payload, "usage": recorded, "validation_error": rejection,
                     "validation_diagnostics": received["invalid_units"], "partial_review": None,
                     "received_analysis": received["analysis"],
                     "citation_review": seal(citation_review, complete_content, result.model_dump(mode="json") if result else None),
                     "correction_feedback": None,
                     "alert_boundary_version": profile.version})
                await ai_delivery_store.save(store, run, stage, request_id, original_id, received)
                now = await store.now()
                await store.db.execute(update(S).where(*store.where(S, S.c.id == model)).values(
                    state="completed" if result else "failed", ended_at=now, output_artifact_id=response_id,
                    usage=recorded, error=error(rejection, now) if rejection and not result else null()))
            if result:
                await self.service.finish(tenant, rid, result, execution_step_id=stage,
                    alert_delivery_state=received["delivery"]["state"])
            else:
                await self.fail(tenant, rid, stage, rejection)
        except (Exception, asyncio.CancelledError) as exc:
            # Never overwrite a commit that actually succeeded, nor redispatch.
            from .analysis_dispatch_types import classify_failure
            failure = classify_failure(exc, stage="execute")
            async with self.service.transaction(tenant) as store:
                run, _, _ = await self.service.locked(store, rid)
                if run["state"] == "running":
                    now = await store.now()
                    await store.db.execute(update(S).where(*store.where(S, S.c.run_id == rid,
                        S.c.state.in_(["running", "planned"]))).values(state=failure.outcome,
                            ended_at=now if failure.outcome == "failed" else None, error=error(failure.error_code, now)))
                    await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
                        state=failure.outcome, ended_at=now if failure.outcome == "failed" else None,
                        stop_reason=failure.error_code, row_version=R.c.row_version + 1))
            raise
        return await self.outcome(tenant, claim)

    async def fail(self, tenant, rid, stage, reason):
        async with self.service.transaction(tenant) as store:
            await self.locked(store, rid)
            now = await store.now()
            await store.db.execute(update(S).where(*store.where(S, S.c.id == stage)).values(
                state="failed", ended_at=now, error=error(reason, now)))
            await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
                state="failed", ended_at=now, stop_reason=reason, row_version=R.c.row_version + 1))

    async def background(self, tenant, rid, stage, source, name):
        member = source["members"][0]
        context = SimpleNamespace(alerts={member["alert"]["id"]: SimpleNamespace(objects=member["objects"])})
        keys = sources.selectors(context, name)
        end = member["alert"].get("event_time")
        start = (datetime.fromisoformat(end) - timedelta(hours=24)).isoformat() if end else None
        async with self.service.transaction(tenant) as store:
            run, _ = await self.locked(store, rid)
            limits, now = Limits.model_validate(run["limits"]), await store.now()
            reason = ("no_supported_frozen_objects" if not keys else
                "history_window_not_defined" if name == "history" and not end else
                "source_not_connected" if name not in sources.CONNECTED else None)
            used = (await store.db.execute(select(func.count()).select_from(S).where(*store.where(S,
                S.c.run_id == rid, S.c.kind == "tool", S.c.state.not_in(["skipped", "planned"]))))).scalar_one()
            if not reason and (limits.max_tool_calls is None or limits.max_rows_per_query is None or limits.deadline_at is None):
                reason = "execution_limits_not_defined"
            if not reason and (used >= limits.max_tool_calls or limits.max_rows_per_query == 0):
                reason = "tool_budget_exhausted"
            if not reason and limits.deadline_at <= now:
                reason = "deadline_reached"
            args = {"tool_name": name, "contract_version": sources.VERSION,
                "scope": {"kind": "selected_alerts", "alert_ids": [member["alert"]["id"]],
                    "object_keys": sorted({k["object_key"] for k in keys}), "window_start": start, "window_end": end,
                    "limitations": ["history_24h_before_alert_time"] if name == "history" else []},
                "limit": min(limits.max_rows_per_query or 0, 200), "parameters": {"selectors": keys, "source_scope": "tenant_only"}}
            step = await self.step(store, run, "tool", name, state="planned" if reason else "running", parent=stage, args=args)
            request_id = await self.save(store, run, step, "tool_request", args)
            await store.db.execute(update(S).where(*store.where(S, S.c.id == step)).values(
                input_artifact_id=request_id, provider="postgresql"))
            deadline = asyncio.get_running_loop().time() + (limits.deadline_at - now).total_seconds() if not reason else None
        rows, state, captured, observed = None, "skipped", now, None
        truncation = []
        overflow_rows = []
        if not reason:
            try:
                async with asyncio.timeout_at(deadline):
                    rows, captured = await self.query(self.service, tenant, name, args)
                observed = len(rows)
                if observed > args["limit"]:
                    truncation.append("row_limit")
                # Keep every received row. Only the bounded business rows are
                # used downstream; the fetch sentinel remains in the receipt.
                rows, overflow_rows = rows[:args["limit"]], rows[args["limit"]:]
                state = "completed"
            except TimeoutError:
                state, reason = "timeout", "source_deadline_exceeded"
            except DBAPIError as exc:
                state = "failed"
                code = getattr(exc.orig, "sqlstate", None)
                reason = "source_unavailable" if code in {"42P01", "42501"} else "source_query_failed"
        async with self.service.transaction(tenant) as store:
            run, _ = await self.locked(store, rid)
            payload = {"schema_version": VERSION, "tool_name": name, "contract_version": sources.VERSION,
                "state": state, "reason": reason, "actual_args": args, "rows": rows,
                "returned_rows": len(rows) if rows is not None else None, "observed_rows_in_bounded_fetch": observed,
                "overflow_rows": overflow_rows,
                "truncated": bool(truncation), "truncation_reasons": truncation, "captured_at": captured.isoformat(),
                "query_id": "local-step:" + str(step) if state != "skipped" else None,
                "limitations": sources.LIMITATIONS[name]}
            identity = await self.save(store, run, step, "tool_response", payload)
            now = await store.now()
            await store.db.execute(update(S).where(*store.where(S, S.c.id == step)).values(state=state, ended_at=now,
                output_artifact_id=identity, returned_rows=payload["returned_rows"], error=error(reason, now) if reason else null()))
        return identity, payload
