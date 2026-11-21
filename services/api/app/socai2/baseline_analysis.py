"""One initial C3 pass on the existing Run. No Tool dispatch or publication."""
import asyncio
import json
from uuid import UUID, uuid4

from sqlalchemy import func, insert, null, select, update

from . import baseline_analysis_contract as contract
from . import baseline_model_view as view
from . import baseline_tool_catalog as catalog
from .baseline_analysis_model import TenantChatGateway
from .baseline_capacity import draft_limit, remaining_seconds
from .baseline_context import reference
from .baseline_contracts import FULL_EXECUTOR_VERSION, FULL_EXECUTOR_VERSIONS, Limits
from .baseline_dispatch import offered_bindings
from .baseline_enrichment import S, error
from .baseline_execution_schema import compact_execution_wire
from .baseline_store import RM, F, StoreError, digest, encoded
from .model_input_view import case_model_data

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
        # Preparation is bounded for storage. The final complete wire request
        # is admitted using the actual backend tokenizer and context capacity.
        # Only repeated scope metadata is hoisted. Never remove evidence to fit
        # a capability; every unoffered original remains in C4.materials.
        output.append(catalog.message(options))
        while options and len(encoded(output)) > draft_limit():
            options.pop()
            output[-1] = catalog.message(options)
    if len(output[1]["content"].encode()) > draft_limit() or len(encoded(output)) > draft_limit() or any(view.blocked(m["content"]) for m in output):
        raise StoreError("analysis_input_contract_or_size", 422)
    return output, source_map


def reserved_calls(run, stage_code):
    # Read the persisted executor identity, never a request-controlled flag.
    from .runtime_policy import active_policy
    if run["executor_version"] not in FULL_EXECUTOR_VERSIONS or stage_code == "C6":
        return 0
    configured = active_policy().model.final_reserved_calls
    maximum = (run.get("limits") or {}).get("max_model_calls")
    return min(configured, max(1, maximum - 1)) if maximum is not None else configured


def budget_reason(steps, limits, request_bytes, now, *, reserve_calls=0, reservation=None, measurement=None):
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
        detail = step.get("error") or {}
        if {detail.get("code"), detail.get("usage_issue")} & {"provider_usage_exceeds_reservation", "provider_usage_inconsistent"}:
            return "prior_model_usage_invalid"
        if reported.get("usage_state") != "reported" or type(total) is not int or total < 0:
            if step.get("not_executed"):
                continue
            total = step.get("reserved_tokens")
            if type(total) is not int or total <= 0:
                return "prior_model_usage_unknown"
        used += total
    if measurement is not None and not measurement["context_fits"]:
        return "model_context_capacity_exceeded"
    if measurement is None:
        return "token_measurement_missing"
    required = measurement["reserved_total_tokens"]
    if required > limits.max_tokens - used:
        return "model_token_budget_insufficient"
    if reservation and required + reservation.get("reserved_tokens", reservation.get("conservative_units", 0)) > limits.max_tokens - used:
        return "final_model_tokens_reserved"
    return None


def domain_block(domain, analysis, source_map, context):
    from .case_citation_quality import links
    findings = []
    for item in analysis.findings:
        if item.id not in domain.finding_ids:
            continue
        scope = context.scope.model_dump(mode="json")
        # A finding declares member alerts, not every object in the whole Case.
        # Object-level attribution requires its own explicit evidence.
        scope.update(kind="selected_alerts", alert_ids=list(map(str, item.alert_ids)), object_keys=[])
        findings.append({"id": item.id, "statement": item.statement, "state": item.state,
            "scope": scope, "support": links(item.support_ids, source_map, observed=item.state == "observed"),
            "counterevidence": links(item.counter_ids, source_map),
            "limitations": item.limitations})
    focus = context.scope.model_dump(mode="json")
    focus.update(kind="selected_alerts", alert_ids=list(map(str, domain.alert_ids)), object_keys=[])
    return {"schema_version": SCHEMA, "domain": domain.name, "applicability": domain.applicability,
        "focus_scope": focus, "questions": [],
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
            if run["executor_version"] != FULL_EXECUTOR_VERSION:
                raise StoreError("full_executor_claim_required")
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
            from .baseline_failure import require_idle
            await require_idle(store, run_id)
            context = await store.read_context(case_id, run_id)
            from . import case_model_boundary, case_output_adapter
            case_model_boundary.selected_profile(context)
            prepared = await store.prepare_model_view(case_id, run_id, case_boundary=True)
            bindings, options = {}, []
            if run["executor_version"] == FULL_EXECUTOR_VERSION:
                from .baseline_evidence import BaselineEvidence
                from .baseline_evidence_tools import LakeGateway
                material, _ = await BaselineEvidence(self.service).prepared(store, run)
                steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == run_id)))).mappings().all()
                options, bindings, excluded = offered_bindings(material["catalog"], Limits.model_validate(run["limits"]),
                    await store.now(), steps, lake or LakeGateway(self.service), members=material.get("members"))
            tool_rows = (await store.db.execute(select(F.c.id, F.c.content_json, F.c.sha256).where(
                *store.where(F, F.c.run_id == run_id, F.c.kind == "tool_response")))).mappings().all()
            if any(digest(r["content_json"]) != r["sha256"] for r in tool_rows):
                raise StoreError("enrichment_receipt_invalid")
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
                    "skipped", prepared.get("reason") or "model_view_not_ready", refs)
            try:
                prompt, source_map = case_model_boundary.messages(prepared, context, options)
                if bindings is not None:
                    offered = {o["binding_id"] for o in options}
                    excluded.extend({"binding_id": b["binding_id"], "reason": "binding_catalog_input_limit"}
                        for alias, b in bindings.items() if alias not in offered)
                    bindings = {alias: b for alias, b in bindings.items() if alias in offered}
            except StoreError as exc:
                if exc.code == "case_input_exceeds_prepared_limit":
                    async with self.service.transaction(tenant_id) as store:
                        run = await self.locked(store, case_id, run_id)
                        await self.artifact(store, run, stage_id, {"schema_version": self.schema,
                            "type": "capacity_preflight", "stage": "C3", "dispatch_state": "not_sent",
                            "reason": exc.code, "messages": prepared["unsent_messages"],
                            "source_map": prepared["source_map"], "tool_presentation": prepared.get("tool_presentation")},
                            "source_snapshot", refs)
                return await self.finish(tenant_id, case_id, run_id, stage_id, None,
                    "skipped", exc.code, refs)
            from .baseline_reasoning import ModelSteps
            fmt = case_output_adapter.output_format(prepared, context, bindings)
            call_input = {"ready": True, "messages": prompt, "source_map": source_map,
                "binding_map": bindings, "input_artifact_ids": [prepared["artifact_id"]],
                "input_view_id": prepared["artifact_id"], "omissions": prepared.get("omissions", []),
                "coverage": prepared["coverage"], "unoffered_bindings": excluded}
            from .citation_quality import new_review
            citation_review = call_input["citation_review"] = new_review()
            call_input["case_boundary"] = prepared["case_boundary"]
            call_input["tool_presentation"] = prepared["tool_presentation"]
            from . import case_c3_delivery
            parser = case_c3_delivery.parser(call_input, context, bindings)
            phase = "model_dispatch_and_review"
            outcome = await ModelSteps(self.service, self.schema).call(
                tenant_id, case_id, run_id, stage_id, "C3", call_input, gateway, parser,
                output_format=fmt, wire_transform=compact_execution_wire if bindings is not None else None,
                allow_correction=False)
            from .case_c3_completion_flow import complete_sections
            outcome = await complete_sections(self.service, tenant_id, case_id, run_id, stage_id,
                call_input, context, bindings, fmt, gateway, outcome, schema=self.schema)
            analysis, rejection, model_id, response_id = outcome
            phase = "response_publication"
            return await self.finish(tenant_id, case_id, run_id, stage_id, model_id,
                "completed", rejection, refs,
                analysis=analysis, source_map=source_map, context=context, response_id=response_id,
                basis={"binding_map": bindings, "unoffered_bindings": excluded,
                    "citation_review": citation_review,
                    **({"section_completion": call_input["section_completion_result"]}
                       if "section_completion_result" in call_input else {}),
                    "stage_delivery": call_input["stage_delivery_result"],
                    "validation_review": call_input.get("validation_review"),
                    "correction_result": call_input.get("correction_result")})
        except (Exception, asyncio.CancelledError) as exc:
            from .baseline_failure import settle_unsent
            async with self.service.transaction(tenant_id) as store:
                run = await self.locked(store, case_id, run_id)
                if not await settle_unsent(store, run, exc):
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
            from .case_citation_quality import VALIDATION
            summary = {"schema_version": self.schema, "case_id": str(case_id), "run_id": str(run_id),
                "stage": phase, "state": state, "reason": reason,
                "validation": (VALIDATION if basis and basis.get("citation_review") is not None
                               else "structure_scope_sources_checked") if analysis else "not_accepted",
                "analysis": analysis.model_dump(mode="json") if analysis else None,
                "source_map": source_map or {}, "domain_artifact_ids": domain_artifacts,
                "domains_not_executed": [name for name in contract.DOMAINS if name not in domain_artifacts],
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
