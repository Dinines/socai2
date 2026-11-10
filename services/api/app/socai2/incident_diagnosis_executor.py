"""One I synthesis over frozen members; no A queries, Case runs, or actions."""
import asyncio
from uuid import uuid4, uuid5

from sqlalchemy import func, insert, null, select, update

from . import incident_diagnosis_contract as contract
from . import incident_model_boundary, incident_output_adapter
from .baseline_analysis import budget_reason
from .baseline_analysis_model import TenantChatGateway, usage
from .baseline_context import reference
from .baseline_contracts import Limits
from .baseline_enrichment import S, error
from .baseline_store import StoreError, digest, encoded
from .incident_delivery import assess
from .model_errors import ModelCallError
from .model_protocol import prepare_request, response_choices
from .stage_result_contracts import INCIDENT_EXECUTOR_VERSION as VERSION
from .stage_results import D, F, R, artifact
from .structured_output import response_format


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

    async def execute(self, tenant, incident_id, operation_key, *, requested_by=None):
        claim = await self.service.begin(tenant, "incident_diagnosis", incident_id, operation_key, producer=VERSION, limits=None,
            requested_by=requested_by)
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
                from .runtime_policy import active_policy
                prepared = None
                if "query_receipts_version" in source:
                    profile = active_policy().incident_io
                    if profile is None:
                        raise StoreError("incident_boundary_profile_unavailable", 422)
                    messages, source_map, data, prepared = incident_model_boundary.build(source,
                        claim["input_artifact_id"], profile, execution_time=run["started_at"].isoformat())
                else:
                    messages, source_map, data = contract.build(source, claim["input_artifact_id"],
                        execution_time=run["started_at"].isoformat())
            except StoreError as exc:
                await self.stop(tenant, rid, "failed", exc.code)
                return await self.outcome(tenant, claim)
            if not await self.gateway.configure(self.service, tenant):
                await self.stop(tenant, rid, "failed", "model_not_configured")
                return await self.outcome(tenant, claim)
            body = {"model": self.gateway.model, "messages": messages, "max_tokens": active_policy().model.output_tokens["I"], "temperature": 0,
                    "response_format": {"type": "json_schema", "json_schema": {"name": "socai2_incident_boundary",
                        "strict": True, "schema": incident_output_adapter.candidate_schema(prepared)}} if prepared else response_format(contract.Answer, source_map,
                        members=[m["alert"]["id"] for m in source["members"]],
                        member_sources=[sid for sid, ref in source_map.items() if ref["alert_ids"]])}
            body = prepare_request(self.gateway, body)
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
                if not reason:
                    model = await self.step(store, run, "model", stage)
                    request = {"schema_version": VERSION, "provider": self.gateway.provider, "model": self.gateway.model,
                        "schema_profile": getattr(self.gateway, "schema_profile", "standard"),
                        "body": body, "source_map": source_map, "member_coverage": data["members"], "input_omissions": data["omissions"],
                        "view_limitations": data["view_limitations"],
                        "input_omission_details": data["omission_details"],
                        "input_omission_detail_count": data["omission_detail_count"],
                        "input_omission_details_truncated": data["omission_details_truncated"],
                        "reserved_token_upper_bound": measurement["reserved_total_tokens"], "token_measurement": measurement}
                    if prepared:
                        request["incident_boundary"] = prepared["boundary"]
                    request_id = await self.save(store, run, model, "model_request", request)
                    await store.db.execute(update(S).where(*store.where(S, S.c.id == model)).values(
                        input_artifact_id=request_id, provider=self.gateway.provider))
                    deadline = asyncio.get_running_loop().time() + (limits.deadline_at - now).total_seconds()
            if reason:
                await self.stop(tenant, rid, "failed", reason)
                return await self.outcome(tenant, claim)
            try:
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
                    await self.stop(tenant, rid, "failed", exc.rejection_code)
                    return await self.outcome(tenant, claim)
                raise
            recorded = usage(payload)
            rejection, result, validated, diagnostics = None, None, None, []
            review, complete_content = None, None
            try:
                if recorded["usage_state"] != "reported":
                    raise StoreError("model_usage_unknown_or_inconsistent", 422)
                if recorded["total_tokens"] > request["reserved_token_upper_bound"]:
                    raise StoreError("provider_usage_exceeds_reservation", 422)
                choices = response_choices(payload)
                if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                    raise StoreError("model_choices_invalid", 422)
                message = choices[0].get("message")
                if choices[0].get("finish_reason") != "stop":
                    raise StoreError("model_response_not_complete", 422)
                if (not isinstance(message, dict) or not isinstance(message.get("content"), str)
                        or message.get("tool_calls") or message.get("function_call") or message.get("refusal")):
                    raise StoreError("model_content_or_tool_protocol_invalid", 422)
                complete_content = message["content"]
                if prepared:
                    result, validated = incident_output_adapter.parse(complete_content, prepared, diagnostics=diagnostics)
                else:
                    result, validated = contract.parse(complete_content, source_map, data, diagnostics=diagnostics)
            except StoreError as exc:
                rejection = exc.code
                if complete_content is not None:
                    from .stage_answer_review import review_incident
                    review = (incident_output_adapter.review(complete_content, prepared) if prepared
                              else review_incident(complete_content, source_map, data))
            async with self.service.transaction(tenant) as store:
                run, frozen_source = await self.locked(store, rid)
                response_id = await self.save(store, run, model, "model_response", {"schema_version": VERSION,
                    "raw": payload, "usage": recorded, "validation_error": rejection, "validated_members": validated,
                    "validation_diagnostics": diagnostics, "partial_review": review,
                    **({"incident_boundary_version": prepared["boundary"]["version"],
                        "diagnostic_paths": "canonical_incident_answer"} if prepared else {})})
                if review is not None:
                    kept = review["retained_analysis"]
                    delivery = assess(frozen_source, partial_review=review)
                    await store.db.execute(update(D).where(*store.where(D, D.c.source_run_id == rid)).values(
                        summary=None, diagnosis={"validation_state": "partial", "conclusion": None,
                            "findings": kept["findings"], "partial_review_artifact_id": str(response_id),
                            "limitations": review["limitations"], "program_facts": data["program_facts"],
                            "delivery_assessment": delivery},
                        open_questions=kept["open_questions"]))
                    await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
                        delivery_state=delivery["state"], row_version=R.c.row_version + 1))
                now = await store.now()
                await store.db.execute(update(S).where(*store.where(S, S.c.id == model)).values(
                    state="completed" if result else "failed", ended_at=now, output_artifact_id=response_id,
                    usage=recorded, error=error(rejection, now) if rejection else null()))
            if result:
                await self.service.finish(tenant, rid, result, execution_step_id=stage, validated_members=validated)
            else:
                await self.stop(tenant, rid, "failed", rejection)
        except (Exception, asyncio.CancelledError):
            await self.stop(tenant, rid, "unknown", "incident_execution_uncertain")
            raise
        return await self.outcome(tenant, claim)
