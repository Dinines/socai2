"""One initial C3 pass on the existing Run. No Tool dispatch or publication."""
import asyncio
import json
from uuid import UUID, uuid4

from sqlalchemy import func, insert, null, select, update

from . import baseline_analysis_contract as contract
from . import baseline_model_view as view
from . import baseline_tool_catalog as catalog
from .baseline_analysis_model import MAX_OUTPUT_TOKENS, TenantChatGateway, usage
from .baseline_capacity import MAX_MESSAGE_BYTES, remaining_seconds, reservation_for
from .baseline_context import reference
from .baseline_contracts import FULL_EXECUTOR_VERSION, FULL_EXECUTOR_VERSIONS, Limits
from .baseline_dispatch import offered_bindings
from .baseline_enrichment import S, error
from .baseline_execution_schema import compact_execution_wire, execution_format
from .baseline_store import RM, F, StoreError, digest, encoded
from .model_errors import ModelCallError
from .model_input_view import case_model_data
from .model_protocol import prepare_request, response_choices
from .structured_output import response_format

SCHEMA = contract.SCHEMA


def messages(prepared, context, tool_payloads, options=None):
    data = json.loads(prepared["messages"][1]["content"])
    data, source_map = case_model_data(data, context, tool_payloads)
    instruction = contract.PROMPT
    if options is not None:
        instruction = "\n".join(line for line in instruction.splitlines() if not line.startswith("followups只提需求")) + "\n" + contract.EXECUTION_PROMPT
    output = [{"role": "system", "content": prepared["messages"][0]["content"] + "\n" + instruction},
              {"role": "user", "content": encoded(data).decode("utf-8")}]
    if options is not None:
        if view.blocked(catalog.data(options)):
            raise StoreError("analysis_input_contract_or_size", 422)
        # Facts keep the original 8 KiB limit. Capabilities are a separate user
        # data message; the complete group still shares the original 12 KiB cap.
        # Only repeated scope metadata is hoisted. Never remove evidence to fit
        # a capability; every unoffered original remains in C4.materials.
        output.append(catalog.message(options))
        while options and len(encoded(output)) > MAX_MESSAGE_BYTES:
            options.pop()
            output[-1] = catalog.message(options)
    if len(output[1]["content"].encode()) > view.MAX_MODEL_BYTES or len(encoded(output)) > MAX_MESSAGE_BYTES or any(view.blocked(m["content"]) for m in output):
        raise StoreError("analysis_input_contract_or_size", 422)
    return output, source_map


def reserved_calls(run, stage_code):
    # Read the persisted executor identity, never a request-controlled flag.
    return int(run["executor_version"] in FULL_EXECUTOR_VERSIONS and stage_code != "C6")


def budget_reason(steps, limits, request_bytes, now, *, reserve_calls=0, reservation=None):
    if limits.max_model_calls is None or limits.max_tokens is None or limits.deadline_at is None:
        return "model_limits_not_defined"
    if limits.deadline_at <= now:
        return "deadline_reached"
    if reservation and remaining_seconds(limits, now, reservation) < 1:
        return "final_model_time_reserved"
    attempts = [s for s in steps if s["kind"] == "model" and s["state"] not in {"planned", "skipped"}]
    if len(attempts) >= limits.max_model_calls:
        return "model_call_budget_exhausted"
    if len(attempts) >= limits.max_model_calls - reserve_calls:
        return "final_model_call_reserved"
    used = 0
    for step in attempts:
        reported = step["usage"] or {}
        total = reported.get("total_tokens")
        if reported.get("usage_state") != "reported" or type(total) is not int or total < 0:
            return "prior_model_usage_unknown"
        used += total
    if request_bytes + MAX_OUTPUT_TOKENS + 256 > limits.max_tokens - used:
        return "model_token_budget_insufficient"
    if reservation and request_bytes + MAX_OUTPUT_TOKENS + 256 + reservation["conservative_units"] > limits.max_tokens - used:
        return "final_model_tokens_reserved"
    return None


def domain_block(domain, analysis, source_map, context):
    findings = []
    for item in analysis.findings:
        if item.id not in domain.finding_ids:
            continue
        scope = context.scope.model_dump(mode="json")
        # A finding declares member alerts, not every object in the whole Case.
        # Object-level attribution requires its own explicit evidence.
        scope.update(kind="selected_alerts", alert_ids=list(map(str, item.alert_ids)), object_keys=[])
        findings.append({"id": item.id, "statement": item.statement, "state": item.state,
            "scope": scope, "support": [source_map[s]["ref"] for s in item.support_ids],
            "counterevidence": [source_map[s]["ref"] for s in item.counter_ids],
            "limitations": item.limitations})
    return {"schema_version": SCHEMA, "domain": domain.name, "applicability": domain.applicability, "questions": [],
        "findings": findings, "recommendations": [], "limitations": [domain.reason, *domain.limitations,
            "shared_initial_model_pass_not_independent_expert_vote", "structure_validated_not_truth_proven"]}


class BaselineAnalysis:
    def __init__(self, service):
        self.service = service
        self.schema = SCHEMA

    async def locked(self, store, case_id, run_id):
        await store.case(case_id)
        return await store.run(case_id, run_id)

    async def next_seq(self, store, run_id):
        return (await store.db.execute(select(func.coalesce(func.max(S.c.seq), 0)).where(
            *store.where(S, S.c.run_id == run_id)))).scalar_one() + 1

    async def artifact(self, store, run, step, payload, kind, refs):
        identity = uuid4()
        await store.save_input_artifact(run["case_id"], run["id"], identity, payload, kind=kind,
            schema=self.schema, captured_at=await store.now(), refs=refs, actor_id=run["requested_by"], step_id=step)
        return identity

    async def execute(self, tenant_id, case_id, run_id, gateway=None, lake=None):
        gateway = gateway or TenantChatGateway()
        bindings, options, excluded = None, None, []
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["executor_version"] == FULL_EXECUTOR_VERSION:
                self.schema = contract.EXECUTION_SCHEMA
            prior = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id,
                S.c.kind == "stage", S.c.stage_code == "C3")))
            if prior:
                if prior["state"] in {"running", "unknown", "planned"}:
                    raise StoreError("analysis_already_claimed")
                artifact = await store.one(select(F).where(*store.where(F,
                    F.c.id == prior["output_artifact_id"], F.c.run_id == run_id)))
                if not artifact or digest(artifact["content_json"]) != artifact["sha256"]:
                    raise StoreError("analysis_receipt_invalid")
                return artifact["content_json"]
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            if await store.one(select(S.c.id).where(*store.where(S, S.c.run_id == run_id,
                    S.c.state.in_(["planned", "running", "unknown"]))).limit(1)):
                raise StoreError("baseline_step_in_progress")
            prepared = await store.prepare_model_view(case_id, run_id)
            context = await store.read_context(case_id, run_id)
            if run["executor_version"] == FULL_EXECUTOR_VERSION:
                from .baseline_evidence import BaselineEvidence
                from .baseline_evidence_tools import LakeGateway
                material, _ = await BaselineEvidence(self.service).prepared(store, run)
                steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == run_id)))).mappings().all()
                options, bindings, excluded = offered_bindings(material["catalog"], Limits.model_validate(run["limits"]),
                    await store.now(), steps, lake or LakeGateway(self.service))
            tool_rows = (await store.db.execute(select(F.c.id, F.c.content_json, F.c.sha256).where(
                *store.where(F, F.c.run_id == run_id, F.c.kind == "tool_response")))).mappings().all()
            if any(digest(r["content_json"]) != r["sha256"] for r in tool_rows):
                raise StoreError("enrichment_receipt_invalid")
            tool_payloads = {str(r["id"]): r["content_json"] for r in tool_rows}
            stage_id = uuid4()
            await store.db.execute(insert(S).values(id=stage_id, tenant_id=tenant_id, run_id=run_id,
                seq=await self.next_seq(store, run_id), kind="stage", stage_code="C3", state="running",
                name="initial_main_and_domain_analysis", implementation_version=self.schema,
                started_at=await store.now(), input_artifact_id=UUID(prepared["artifact_id"])))
        refs = [reference("artifact", prepared["artifact_id"], "execution_receipt")]
        model_id = None
        phase = "preparation"
        try:
            if not prepared["ready"]:
                return await self.finish(tenant_id, case_id, run_id, stage_id, None,
                    "skipped", "model_view_not_ready", refs)
            try:
                prompt, source_map = messages(prepared, context, tool_payloads, options)
                if bindings is not None:
                    offered = {o["binding_id"] for o in options}
                    excluded.extend({"binding_id": b["binding_id"], "reason": "binding_catalog_input_limit"}
                        for alias, b in bindings.items() if alias not in offered)
                    bindings = {alias: b for alias, b in bindings.items() if alias in offered}
            except StoreError:
                return await self.finish(tenant_id, case_id, run_id, stage_id, None,
                    "skipped", "analysis_input_contract_or_size", refs)
            if not await gateway.configure(self.service, tenant_id):
                return await self.finish(tenant_id, case_id, run_id, stage_id, None,
                    "skipped", "model_not_configured", refs)
            body = {"model": gateway.model, "messages": prompt, "max_tokens": MAX_OUTPUT_TOKENS, "temperature": 0,
                    "response_format": response_format(contract.Analysis if bindings is None else contract.ExecutionAnalysis, source_map,
                        members=context.alerts, questions=[q.id for q in context.questions],
                        objects=context.scope.object_keys, bindings=bindings or ())}
            if bindings is not None:
                body["response_format"] = execution_format(body["response_format"], bindings)
            body = prepare_request(gateway, body)
            if bindings is not None:
                body = compact_execution_wire(body)
            async with self.service.transaction(tenant_id) as store:
                run = await self.locked(store, case_id, run_id)
                if run["state"] != "running":
                    raise StoreError("baseline_not_running")
                limits, now = Limits.model_validate(run["limits"]), await store.now()
                steps = (await store.db.execute(select(S).where(*store.where(S,
                    S.c.run_id == run_id)))).mappings().all()
                reservation = await reservation_for(store, run, steps)
                reason = budget_reason(steps, limits, len(encoded(body)), now, reserve_calls=reserved_calls(run, "C3"), reservation=reservation)
                if reason is None:
                    deadline = asyncio.get_running_loop().time() + remaining_seconds(limits, now, reservation, "C3")
                    model_id = uuid4()
                    await store.db.execute(insert(S).values(id=model_id, tenant_id=tenant_id, run_id=run_id,
                        seq=await self.next_seq(store, run_id), parent_step_id=stage_id, kind="model", stage_code="C3",
                        state="running", name="main_with_domain_views", provider=gateway.provider,
                        implementation_version=self.schema, started_at=now))
                    request = {"schema_version": self.schema, "provider": gateway.provider, "model": gateway.model,
                        "schema_profile": getattr(gateway, "schema_profile", "standard"),
                        "direction": "request", "payload": {"body": body, "source_map": source_map,
                            "input_view_id": prepared["artifact_id"], "input_view_sha256": digest({k: v for k, v in prepared.items() if k != "artifact_id"}),
                            "reserved_token_upper_bound": len(encoded(body)) + MAX_OUTPUT_TOKENS + 256,
                            "binding_map": bindings, "unoffered_bindings": excluded, "final_reservation": reservation},
                        "captured_at": now.isoformat(), "request_id": None, "usage": None}
                    request_id = await self.artifact(store, run, model_id, request, "model_request", refs)
                    await store.db.execute(update(S).where(*store.where(S, S.c.id == model_id)).values(input_artifact_id=request_id))
            if reason:
                return await self.finish(tenant_id, case_id, run_id, stage_id, None, "skipped", reason, refs)
            # The model claim and exact input are committed before dispatch.
            phase = "model_dispatch"
            try:
                async with asyncio.timeout_at(deadline):
                    payload = await gateway.complete(body, max(0, deadline - asyncio.get_running_loop().time()))
            except ModelCallError as exc:
                async with self.service.transaction(tenant_id) as store:
                    run = await self.locked(store, case_id, run_id)
                    if run["state"] != "running":
                        raise StoreError("baseline_not_running")
                    response = {"schema_version": self.schema, "provider": gateway.provider, "model": gateway.model,
                        "direction": "response", "payload": exc.payload(), "captured_at": (await store.now()).isoformat(),
                        "request_id": None, "usage": usage(None)}
                    response_id = await self.artifact(store, run, model_id, response, "model_response", refs)
                    await store.db.execute(update(S).where(*store.where(S, S.c.id == model_id)).values(
                        output_artifact_id=response_id, usage=usage(None)))
                    if exc.rejection_code:
                        now = await store.now()
                        await store.db.execute(update(S).where(*store.where(S, S.c.id == model_id)).values(
                            state="failed", ended_at=now, error=error(exc.rejection_code, now)))
                if exc.rejection_code:
                    return await self.finish(tenant_id, case_id, run_id, stage_id, model_id,
                        "failed", exc.rejection_code, refs, response_id=response_id)
                raise
            phase = "response_processing"
            recorded_usage = usage(payload)
            analysis, rejection = None, None
            try:
                if recorded_usage["usage_state"] != "reported":
                    raise contract.AnalysisRejected("model_usage_unknown_or_inconsistent")
                if recorded_usage["total_tokens"] > len(encoded(body)) + MAX_OUTPUT_TOKENS + 256:
                    raise contract.AnalysisRejected("provider_usage_exceeds_reservation")
                choices = response_choices(payload)
                if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                    raise contract.AnalysisRejected("model_choices_invalid")
                choice, content = choices[0], choices[0].get("message")
                if choice.get("finish_reason") != "stop":
                    raise contract.AnalysisRejected("model_response_not_complete")
                if (not isinstance(content, dict) or content.get("tool_calls") or content.get("function_call")
                        or content.get("refusal") or not isinstance(content.get("content"), str)):
                    raise contract.AnalysisRejected("model_content_or_tool_protocol_invalid")
                analysis = contract.parse(content["content"], source_map, context, prepared["coverage"], bindings=bindings)
            except contract.AnalysisRejected as exc:
                rejection = str(exc)
            response = {"schema_version": self.schema, "provider": gateway.provider, "model": gateway.model,
                "direction": "response", "payload": {"raw": payload, "validation_error": rejection},
                "captured_at": None, "request_id": recorded_usage["request_id"], "usage": recorded_usage}
            phase = "response_publication"
            return await self.finish(tenant_id, case_id, run_id, stage_id, model_id,
                "completed" if analysis else "failed", rejection, refs, response, analysis, source_map, context,
                basis={"binding_map": bindings, "unoffered_bindings": excluded} if bindings is not None else None)
        except (Exception, asyncio.CancelledError) as exc:
            # No retry after transport/commit uncertainty. Retain the active Run.
            async with self.service.transaction(tenant_id) as store:
                await self.locked(store, case_id, run_id)
                failure = error("analysis_dispatch_uncertain", await store.now())
                # Exception messages may contain provider URLs, keys or source
                # data. Persist only a code-owned phase and exception type.
                failure["message"] = f"{phase}:{type(exc).__name__}"
                await store.db.execute(update(S).where(*store.where(S, S.c.run_id == run_id,
                    S.c.stage_code == "C3", S.c.state == "running")).values(state="unknown",
                        error=failure))
                await store.mark_unknown(case_id, run_id)
            raise

    async def finish(self, tenant_id, case_id, run_id, stage_id, model_id, state, reason, refs,
                     response=None, analysis=None, source_map=None, context=None, *, response_id=None,
                     phase="C3_initial", basis=None):
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            now, domain_artifacts = await store.now(), {}
            if response:
                response["captured_at"] = now.isoformat()
                response_id = await self.artifact(store, run, model_id, response, "model_response", refs)
                await store.db.execute(update(S).where(*store.where(S, S.c.id == model_id)).values(
                    state=state, ended_at=now, output_artifact_id=response_id, usage=response["usage"],
                    error=error(reason, now) if reason else null()))
            if analysis:
                for domain in analysis.domains:
                    block = domain_block(domain, analysis, source_map, context)
                    block["schema_version"] = self.schema
                    identity = await self.artifact(store, run, model_id,
                        block, "domain_analysis",
                        [reference("artifact", response_id, "execution_receipt")])
                    domain_artifacts[domain.name] = str(identity)
                for member in analysis.members:
                    # Source material was not read in full by this metadata view.
                    # Do not change read_state to read or claim final coverage.
                    await store.db.execute(update(RM).where(*store.where(RM, RM.c.run_id == run_id,
                        RM.c.alert_id == member.alert_id)).values(analysis_state=member.state))
            summary = {"schema_version": self.schema, "case_id": str(case_id), "run_id": str(run_id),
                "stage": phase, "state": state, "reason": reason,
                "validation": "structure_scope_sources_checked" if analysis else "not_accepted",
                "analysis": analysis.model_dump(mode="json") if analysis else None,
                "source_map": source_map or {}, "domain_artifact_ids": domain_artifacts,
                "domains_not_executed": [] if analysis else list(contract.DOMAINS),
                "limitations": ["initial_shared_model_pass" if phase == "C3_initial" else "post_evidence_shared_model_pass", "semantic_accuracy_not_proven",
                    "raw_material_not_fully_read", "not_full_baseline_delivery",
                    "only_offered_query_bindings_executable" if self.schema == contract.EXECUTION_SCHEMA
                        else "followups_are_not_executable_tool_requests"],
                "captured_at": now.isoformat()}
            if basis is not None:
                summary["basis"] = basis
            identity = await self.artifact(store, run, stage_id, summary, "source_snapshot", refs)
            await store.db.execute(update(S).where(*store.where(S, S.c.id == stage_id)).values(
                state=state, ended_at=now, output_artifact_id=identity,
                error=error(reason, now) if reason else null()))
            return summary
