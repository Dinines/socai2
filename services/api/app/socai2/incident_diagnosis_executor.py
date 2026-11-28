"""One I synthesis over frozen members; no A queries, Case runs, or actions."""
import asyncio
from uuid import uuid4, uuid5

from sqlalchemy import func, insert, null, select, update

from app.core.operational_logging import log_context

from . import ai_delivery_store, incident_model_boundary, incident_output_adapter
from .analysis_dispatch_types import ExecutionFailure
from .baseline_analysis import budget_reason
from .baseline_analysis_model import TenantChatGateway, usage
from .baseline_context import reference
from .baseline_contracts import Limits
from .baseline_enrichment import S, error
from .baseline_store import StoreError, digest, encoded
from .model_errors import (
    DEADLINE_BEFORE_DISPATCH,
    INPUT_CONTRACT_REJECTED,
    ModelCallError,
)
from .model_protocol import prepare_request
from .runtime_policy import active_policy, execution_policy
from .stage_result_contracts import INCIDENT_EXECUTOR_VERSION as VERSION
from .stage_results import D, F, R, artifact


class IncidentDiagnosisExecutor:
    def __init__(self, service, *, gateway=None):
        self.service, self.gateway = service, gateway or TenantChatGateway()

    async def locked(self, store, rid):
        run, _, source = await self.service.locked(store, rid)
        if run["kind"] != "incident_diagnosis" or run["executor_version"] != VERSION or run["state"] != "running":
            raise StoreError("incident_execution_not_running")
        return run, source

    async def step(self, store, run, kind, parent=None):
        sid = uuid4()
        seq = (await store.db.execute(select(func.coalesce(func.max(S.c.seq), 0)).where(
            *store.where(S, S.c.run_id == run["id"])))).scalar_one() + 1
        await store.db.execute(insert(S).values(id=sid, tenant_id=store.tenant_id, run_id=run["id"],
            seq=seq, kind=kind, stage_code="I", name="incident_member_synthesis", state="running",
            parent_step_id=parent, started_at=await store.now(), implementation_version=VERSION))
        return sid

    async def save(self, store, run, step, kind, body):
        identity = uuid4()
        await artifact(store, run, identity, kind, body, await store.now(),
            [reference("artifact", run["input_artifact_id"], "execution_receipt")], step_id=step, schema_version=VERSION)
        return identity

    async def outcome(self, tenant, claim):
        async with self.service.transaction(tenant, readonly=True) as store:
            run = await store.one(select(R).where(*store.where(R, R.c.id == claim["run_id"])))
            return {**claim, "diagnosis_id": uuid5(claim["run_id"], "diagnosis"),
                    "state": run["state"], "stop_reason": run["stop_reason"]}

    async def stop(self, tenant, rid, state, code):
        async with self.service.transaction(tenant) as store:
            run, _, _ = await self.service.locked(store, rid)
            if run["state"] != "running":
                return  # Do not overwrite a successful but uncertain commit.
            now = await store.now()
            await store.db.execute(update(S).where(*store.where(S, S.c.run_id == rid,
                S.c.state.in_(["running", "planned"]))).values(state=state,
                ended_at=None if state == "unknown" else now, error=error(code, now)))
            await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(state=state,
                ended_at=None if state == "unknown" else now, stop_reason=code, row_version=R.c.row_version + 1))
            await store.db.execute(update(D).where(*store.where(D, D.c.source_run_id == rid)).values(
                state=state, error={"code": code}))
            from .subject_risk_opinions import apply_saved
            await apply_saved(store, run)

    async def execute(self, tenant, incident_id, operation_key, *, requested_by=None, dispatch_context=None, frozen_source=None):
        profile = execution_policy("incident_io").incident_io
        claim = await self.service.begin(tenant, "incident_diagnosis", incident_id, operation_key, producer=VERSION, limits=None,
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
                    raise StoreError("incident_input_snapshot_invalid", 422)
                stage = await self.step(store, run, "stage")
            try:
                if "query_receipts_version" not in source:
                    raise StoreError("incident_boundary_input_required", 422)
                messages, source_map, data, prepared = incident_model_boundary.build(source,
                    claim["input_artifact_id"], profile, execution_time=run["started_at"].isoformat())
            except StoreError as exc:
                await self.stop(tenant, rid, "failed", exc.code)
                return await self.outcome(tenant, claim)
            if not await self.gateway.configure(self.service, tenant):
                await self.stop(tenant, rid, "failed", "model_not_configured")
                return await self.outcome(tenant, claim)
            attempt = 0
            model_policy = active_policy().model
            body = {"model": self.gateway.model, "messages": messages, "max_tokens": model_policy.output_tokens["I"], "temperature": 0,
                    "response_format": {"type": "json_schema", "json_schema": {"name": "socai2_incident_boundary_verdict_v1",
                        "strict": True, "schema": incident_output_adapter.candidate_schema(prepared)}}}
            body = prepare_request(self.gateway, body, max_structure_whitespace=model_policy.incident_max_structure_whitespace)
            async with self.service.transaction(tenant) as store:
                meter_run, _ = await self.locked(store, rid)
                meter_seconds = (Limits.model_validate(meter_run["limits"]).deadline_at - await store.now()).total_seconds()
            try:
                from .token_budget import measure_with_deadline
                measurement = await measure_with_deadline(self.gateway, body, "I", meter_seconds)
            except StoreError as exc:
                await self.stop(tenant, rid, "failed", exc.code)
                return await self.outcome(tenant, claim)
            async with self.service.transaction(tenant) as store:
                run, _ = await self.locked(store, rid)
                limits, now = Limits.model_validate(run["limits"]), await store.now()
                steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == rid)))).mappings().all()
                reason = budget_reason(steps, limits, len(encoded(body)), now, measurement=measurement)
                model = await self.step(store, run, "model", stage) if not reason else stage
                request = {"schema_version": VERSION, "provider": self.gateway.provider, "model": self.gateway.model,
                    "schema_profile": getattr(self.gateway, "schema_profile", "standard"),
                    "body": body, "source_map": source_map, "member_coverage": data["members"], "input_omissions": data["omissions"],
                    "view_limitations": data["view_limitations"],
                    "input_omission_details": data["omission_details"],
                    "input_omission_detail_count": data["omission_detail_count"],
                    "input_omission_details_truncated": data["omission_details_truncated"],
                    "reserved_token_upper_bound": measurement["reserved_total_tokens"], "token_measurement": measurement,
                    "correction": None, "preflight_error": reason, "preflight_passed": not bool(reason)}
                request["incident_boundary"] = prepared["boundary"]
                request["severity_opinion_version"] = prepared["severity_opinion_version"]
                request["business_verdict_version"] = prepared["business_verdict_version"]
                request_id = await self.save(store, run, model, "model_request", request)
                await store.db.execute(update(S).where(*store.where(S, S.c.id == model)).values(
                    input_artifact_id=request_id, provider=self.gateway.provider))
                deadline = asyncio.get_running_loop().time() + (limits.deadline_at - now).total_seconds()
            if reason:
                await self.stop(tenant, rid, "failed", reason)
                return await self.outcome(tenant, claim)
            try:
                with log_context(run_id=rid, step_id=model, stage="I", operation="model_complete"):
                    async with asyncio.timeout_at(deadline):
                        payload = await self.gateway.complete(body, max(0, deadline - asyncio.get_running_loop().time()))
            except (Exception, asyncio.CancelledError) as exc:
                async with self.service.transaction(tenant) as store:
                    run, _ = await self.locked(store, rid)
                    await ai_delivery_store.save_call_failure(store, run, stage, model, request_id, VERSION, exc)
                if (isinstance(exc, ExecutionFailure) and exc.code in {INPUT_CONTRACT_REJECTED, DEADLINE_BEFORE_DISPATCH}
                        and exc.not_executed and not exc.temporary):
                    await self.stop(tenant, rid, "failed", exc.code)
                    return await self.outcome(tenant, claim)
                if isinstance(exc, ModelCallError) and (exc.envelope_code or exc.rejection_code):
                    await self.stop(tenant, rid, "failed", exc.envelope_code or exc.rejection_code)
                    return await self.outcome(tenant, claim)
                raise
            from .citation_quality import seal
            recorded = usage(payload)
            async with self.service.transaction(tenant) as store:
                run, _ = await self.locked(store, rid)
                original_id = await self.save(store, run, model, "source_snapshot",
                    {"schema_version": VERSION, "artifact_role": "model_original_response",
                     "request_artifact_id": str(request_id), "attempt": attempt, "raw": payload, "usage": recorded})
            received = ai_delivery_store.receive_payload("I", payload, prepared, original_id, recorded, request)
            result, rejection, validated = received["result"], received["rejection"], received["validated_members"]
            citation_review = received["quality"]
            citation_review.update(original_response_artifact_id=str(original_id), request_artifact_id=str(request_id), attempt=attempt)
            complete_content = received["content"]
            async with self.service.transaction(tenant) as store:
                run, _ = await self.locked(store, rid)
                response_id = await self.save(store, run, model, "model_response", {"schema_version": VERSION,
                    "raw": payload, "usage": recorded, "validation_error": rejection, "validated_members": validated,
                    "validation_diagnostics": received["invalid_units"], "partial_review": None,
                    "received_analysis": received["analysis"],
                    "citation_review": seal(citation_review, complete_content, result.model_dump(mode="json") if result else None),
                    "correction_feedback": None,
                    "incident_boundary_version": prepared["boundary"]["version"],
                    "diagnostic_paths": "canonical_incident_answer"})
                await ai_delivery_store.save(store, run, stage, request_id, original_id, received)
                now = await store.now()
                await store.db.execute(update(S).where(*store.where(S, S.c.id == model)).values(
                    state="completed" if result else "failed", ended_at=now, output_artifact_id=response_id,
                    usage=recorded, error=error(rejection, now) if rejection else null()))
            if result:
                await self.service.finish(tenant, rid, result, execution_step_id=stage, validated_members=validated,
                    incident_delivery_state=received["delivery"]["state"])
            else:
                await self.stop(tenant, rid, "failed", rejection)
        except (Exception, asyncio.CancelledError) as exc:
            from .analysis_dispatch_types import classify_failure
            outcome = classify_failure(exc, stage="execute")
            await self.stop(tenant, rid, outcome.outcome, outcome.error_code)
            raise
        return await self.outcome(tenant, claim)
