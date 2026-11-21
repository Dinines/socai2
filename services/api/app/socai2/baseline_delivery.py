"""C6 final synthesis and atomic report/result publication on the claimed Run."""
import asyncio
import hashlib
from uuid import UUID, uuid4, uuid5

from sqlalchemy import insert, null, select, update

from . import baseline_deep_contract as deep
from . import baseline_delivery_contract as contract
from . import baseline_evidence as evidence
from . import baseline_graph_projection as graph_contract
from .baseline_analysis import domain_block
from .baseline_analysis_model import TenantChatGateway
from .baseline_capacity import CAPACITY_FAILURES, capacity_failure
from .baseline_context import reference
from .baseline_contracts import FULL_EXECUTOR_VERSIONS, Scope
from .baseline_delivery_projection import make_publication, markdown
from .baseline_enrichment import S, error
from .baseline_followup_projection import delivery_followups
from .baseline_model_view import blocked, field_limit
from .baseline_reanalysis import BaselineReanalysis
from .baseline_reasoning import ModelSteps
from .baseline_store import RES, RM, F, R, StoreError, digest, encoded


class BaselineDelivery(ModelSteps):
    def __init__(self, service):
        super().__init__(service, contract.SCHEMA)

    async def bases(self, store, run_id):
        rows = (await store.db.execute(select(F).where(*store.where(F, F.c.run_id == run_id,
            F.c.kind == "source_snapshot", F.c.schema_version.in_([
                evidence.SCHEMA, *deep.READ_SCHEMAS, graph_contract.SCHEMA]))))).mappings().all()
        if any(digest(r["content_json"]) != r["sha256"] for r in rows):
            raise StoreError("evidence_receipt_invalid")
        return sorted([r for r in rows if r["content_json"].get("type") in {
            "materials", "query_projection", "deep_summary", "graph_snapshot"}], key=lambda r: str(r["id"]))

    def current_graph(self, bases):
        state, latest = graph_contract.selected_snapshot(bases)
        if state == "available":
            return latest
        return {**(latest or {}), "state": state, "graph_artifact_id": None, "delivery_state": "none"}

    async def comparison(self, store, run, context):
        rid = str(run["comparison_result_id"]) if run["comparison_result_id"] else None
        selection = (context.update_context or {}).get("comparison_context")
        history = await store.one(select(RES.c.id).where(*store.where(RES, RES.c.case_id == run["case_id"])).limit(1))
        # C1 only freezes selected/adopted results. A failed, unadopted prior
        # Result still means this is not the first recorded investigation.
        meta = {"result_id": rid, "state": "not_selected" if history else "initial",
            "prior_scope": None, "added_alert_ids": [], "removed_alert_ids": [], "shared_alert_ids": [],
            "limitations": ["comparison_is_between_recorded_judgments_not_independent_evidence"]}
        if selection is not None:
            meta["state"] = selection["state"]
            if selection["reason_code"]:
                meta["limitations"].append(selection["reason_code"])
        if not rid:
            return meta, []
        meta["state"] = "unavailable"
        prior = context.prior_results.get(rid)
        if not prior:
            raise StoreError("frozen_comparison_missing")
        row = await store.one(select(F).where(*store.where(F, F.c.case_id == run["case_id"],
            F.c.id == UUID(prior["input_artifact_id"]))))
        if not row or digest(row["content_json"]) != row["sha256"]:
            raise StoreError("comparison_input_invalid")
        try:
            old_scope = Scope.model_validate(row["content_json"]["scope"])
        except (ValueError, TypeError, KeyError):
            meta["limitations"].append("prior_result_scope_not_available")
            return meta, []
        current, old = set(context.alerts), set(map(str, old_scope.alert_ids))
        meta.update(prior_scope=old_scope.model_dump(mode="json"), added_alert_ids=sorted(current - old),
            removed_alert_ids=sorted(old - current), shared_alert_ids=sorted(current & old))
        value = {k: prior[k] for k in ("conclusion", "conclusion_state", "conclusion_origin", "validation_state", "delivery_state")}
        value["comparison_result_id"] = rid
        if (prior["validation_state"] != "accepted" or prior["conclusion_state"] == "unavailable"
                or not prior["conclusion"] or not (current & old) or blocked(value) or len(encoded(value)) > field_limit()):
            meta["limitations"].append("prior_conclusion_not_valid_visible_or_overlapping")
            return meta, []
        meta["state"] = "eligible"
        ref = reference("result", rid, "prior_analysis")
        candidate = {"original": value, "required": True, "entry": {"role": "prior_analysis", "alert_ids": sorted(current & old), "value": value},
            "source": {"ref": ref, "alert_ids": sorted(current & old)}}
        return meta, [candidate]

    async def execute(self, tenant_id, case_id, run_id, gateway=None):
        gateway = gateway or TenantChatGateway()
        # C5 is optional and already settled by the full executor. Do not retry
        # a failed graph or silently rebuild a stale one during final synthesis.
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            prior_delivery = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id,
                S.c.kind == "stage", S.c.stage_code == "C6")))
            if prior_delivery:
                if prior_delivery["state"] in {"running", "planned", "unknown"}:
                    raise StoreError("delivery_already_claimed")
                return await self.read_artifact(store, run_id, prior_delivery["output_artifact_id"])
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            await self.idle(store, run_id)
            context = await store.read_context(case_id, run_id)
            from .case_model_boundary import selected_profile
            selected_profile(context)
            steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == run_id)))).mappings().all()
            capacity_reason = capacity_failure(steps) if context.query_preparation is not None else None
            dispatch_step = next((s for s in steps if s["stage_code"] == "C4.routing" and s["state"] == "completed"), None)
            if run["executor_version"] in FULL_EXECUTOR_VERSIONS and not dispatch_step:
                raise StoreError("full_executor_followups_not_settled")
            dispatch = await self.read_artifact(store, run_id, dispatch_step["output_artifact_id"]) if dispatch_step else None
            initial_plan = await self.read_artifact(store, run_id, UUID(dispatch["initial_analysis_artifact_id"])) if dispatch else None
            execution, planned = delivery_followups(dispatch, initial_plan)
            if not any(s["stage_code"] == "C2" and s["state"] == "completed" for s in steps) or not any(
                    s["stage_code"] == "C3" and s["kind"] == "stage" for s in steps):
                raise StoreError("final_delivery_prerequisites_missing")
            successful = [s for s in steps if s["kind"] == "stage" and s["stage_code"] in {"C3", "C3.reanalysis"}
                and s["state"] == "completed"]
            previous_step = max(successful, key=lambda s: s["seq"]) if successful else None
            previous = await self.read_artifact(store, run_id, previous_step["output_artifact_id"]) if previous_step else None
            bases = await self.bases(store, run_id)
            graph = self.current_graph(bases)
            if graph["graph_artifact_id"]:
                await self.read_artifact(store, run_id, UUID(graph["graph_artifact_id"]))
            comparison, lead = await self.comparison(store, run, context)
            key, stage_id = digest([str(r["id"]) for r in bases]), uuid4()
            await store.db.execute(insert(S).values(id=stage_id, tenant_id=tenant_id, run_id=run_id,
                seq=await self.seq(store, run_id), kind="stage", stage_code="C6", name="final_delivery",
                state="running", implementation_version=contract.SCHEMA, started_at=await store.now(),
                input_artifact_id=run["input_artifact_id"]))
        try:
            prepared = await BaselineReanalysis(self.service).input(tenant_id, case_id, run_id, context,
                previous, previous_step["output_artifact_id"] if previous_step else None, bases,
                instruction=contract.PROMPT,
                extra_data={"round": "final_delivery", "comparison": comparison,
                    **({"preliminary_analysis": {"state": "unavailable", "reason": "no_accepted_main_analysis"}}
                       if previous is None else {}),
                    "followup_execution": execution}, lead_candidates=[*lead, *planned],
                executed_plan_id=dispatch["initial_analysis_artifact_id"] if dispatch else None)
            if dispatch_step:
                prepared["input_artifact_ids"] = list(dict.fromkeys([*prepared["input_artifact_ids"],
                    dispatch["initial_analysis_artifact_id"], str(dispatch_step["output_artifact_id"])]))
            prepared["followup_dispatch"] = dispatch
            from .citation_quality import new_review
            prepared["citation_review"] = new_review()
            from . import case_c6_delivery
            from .case_followup_output import final_format
            parser = case_c6_delivery.parser(prepared, context, comparison)
            output_format = final_format(prepared, context, comparison)
            if capacity_reason:
                value, reason, model_id, response_id = None, capacity_reason, None, None
            else:
                value, reason, model_id, response_id = await self.call(tenant_id, case_id, run_id,
                    stage_id, "C6", prepared, gateway, parser,
                    allow_correction=False,
                    output_format=output_format)
            prepared["stage_delivery"] = await case_c6_delivery.save_receipt(self, tenant_id, case_id, run_id,
                prepared, context, comparison, model_id, response_id, reason)
            return await self.finish(tenant_id, case_id, run_id, stage_id, context, bases, key, graph,
                comparison, prepared, value, reason, model_id, response_id)
        except (Exception, asyncio.CancelledError) as exc:
            await self.uncertain(tenant_id, case_id, run_id, stage_id, exc)
            raise

    async def finish(self, tenant_id, case_id, run_id, stage_id, context, bases, key, graph,
                     comparison, prepared, value, reason, model_id, response_id):
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            await self.idle(store, run_id, stage_id)
            current = await self.bases(store, run_id)
            if digest([str(r["id"]) for r in current]) != key or self.current_graph(current)["graph_artifact_id"] != graph["graph_artifact_id"]:
                raise StoreError("final_evidence_changed")
            if graph["graph_artifact_id"]:
                await self.read_artifact(store, run_id, UUID(graph["graph_artifact_id"]))
            rows = (await store.db.execute(select(RM).where(*store.where(RM, RM.c.run_id == run_id)))).mappings().all()
            members = {r["alert_id"]: r for r in rows}
            pub, limits = make_publication(value, context, members, prepared, comparison, graph,
                uuid5(run_id, "socai2-C6-publication-v1"), reason)
            if context.query_preparation is not None and reason in CAPACITY_FAILURES:
                pub = pub.model_copy(update={"terminal_state": "failed", "stop_reason": "capacity_exceeded",
                                            "stop_detail": reason})
            now = await store.now()
            from .baseline_evidence_index import publish_directory
            directory = await publish_directory(store, run, context, stage_id)
            # C6 always closes the round. A failed/unavailable model is recorded
            # separately; the system closing report is still a completed C6.
            stage_state = "completed"
            refs = [reference("artifact", r["id"], "execution_receipt") for r in bases]
            if response_id:
                refs.append(reference("artifact", response_id, "execution_receipt"))
            if prepared.get("stage_delivery"):
                refs.append(reference("artifact", prepared["stage_delivery"]["artifact_id"], "execution_receipt"))
            if prepared.get("followup_dispatch"):
                refs.append(reference("artifact", prepared["input_artifact_ids"][-1], "execution_receipt"))
            domains = {}
            from .baseline_analysis_contract import Analysis
            retained = (prepared.get("validation_review") or {}).get("retained_analysis")
            visible_analysis = value.analysis if value else Analysis.model_validate(retained) if retained else None
            if visible_analysis:
                for d in visible_analysis.domains:
                    block = domain_block(d, visible_analysis, prepared["source_map"], context)
                    block["schema_version"] = contract.SCHEMA
                    for finding in block["findings"]:
                        finding["scope"]["object_keys"] = []
                    block["limitations"] = [d.reason, *d.limitations,
                        "shared_final_analysis_not_independent_expert_vote", "structure_scope_checked_citations_recorded_not_truth_proven"]
                    domains[d.name] = str(await self.save(store, run, stage_id, block, "domain_analysis", refs))
            steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == run_id)).order_by(S.c.seq))).mappings().all()
            uncertain = any(s["state"] == "unknown" for s in steps)
            model_steps = [s for s in steps if s["kind"] == "model" and s["state"] not in {"planned", "skipped"}]
            known_usage = all((s["usage"] or {}).get("usage_state") == "reported" for s in model_steps)
            totals = sum(s["usage"]["total_tokens"] for s in model_steps) if known_usage else None
            execution = {"model_calls": len(model_steps), "total_tokens": totals,
                "followup_dispatch": prepared.get("followup_dispatch"),
                "usage_state": "reported" if known_usage else "unknown",
                "tool_calls": sum(s["kind"] == "tool" and s["state"] not in {"planned", "skipped"} for s in steps),
                "steps": [{"id": str(s["id"]), "parent_step_id": str(s["parent_step_id"]) if s["parent_step_id"] else None,
                    "kind": s["kind"], "stage_code": s["stage_code"], "question_id": s["question_id"],
                    "state": stage_state if s["id"] == stage_id else s["state"]} for s in steps]}
            report_id, result_id = uuid4(), uuid4()
            pub = pub.model_copy(update={"report_artifact_id": report_id})
            report_result = pub.model_dump(mode="json")
            if uncertain:
                from .baseline_closing import interrupted_report
                await store.mark_unknown(case_id, run_id)
                await store.db.execute(update(R).where(*store.where(R, R.c.id == run_id)).values(delivery_state="partial"))
                run = await store.run(case_id, run_id)
                report_result = interrupted_report(pub, run, local_ended=True)
                execution.update(run_state="unknown", local_state="ended",
                    local_ended_at=now.isoformat(), adoption_eligible=False, comparison_eligible=False)
                result_id = None
            report = {"schema_version": contract.SCHEMA, "type": "delivery_report", "run_id": str(run_id),
                "result_id": str(result_id) if result_id else None,
                "scope": context.scope.model_dump(mode="json"), "evidence_set_key": key,
                "result": report_result,
                "delivery": value.model_dump(mode="json") if isinstance(value, contract.Delivery) else None,
                "retained_output": (prepared.get("c6_delivery") or {}).get("retained_output"),
                "stage_delivery": prepared.get("stage_delivery"),
                "source_map": prepared.get("source_map", {}), "comparison": comparison,
                "validation_review": prepared.get("validation_review"), "correction_result": prepared.get("correction_result"),
                "citation_review": prepared.get("citation_review"),
                "evidence_directory": directory,
                "program_facts": prepared.get("program_facts"),
                "input_artifact_ids": prepared["input_artifact_ids"], "domain_artifact_ids": domains,
                "execution": execution, "limitations": limits + ["structure_scope_checked_citations_recorded_not_truth_proven"],
                "captured_at": now.isoformat()}
            detail_id = await self.save(store, run, stage_id, report, "source_snapshot", refs)
            report_core = {"schema_version": contract.SCHEMA, "result_id": str(result_id) if result_id else None,
                "citation_review": report["citation_review"],
                "program_facts": report["program_facts"],
                **{k: report["result"][k] for k in ("title", "conclusion", "business_verdict", "closing_note", "findings", "questions",
                    "recommendations", "case_impact")}}
            if uncertain:
                report_core.update({k: report_result[k] for k in ("run_state", "local_execution_state",
                    "delivery_state", "adoption_eligible", "comparison_eligible")})
            await store.save_input_artifact(case_id, run_id, report_id, report_core, kind="report_json", schema=contract.SCHEMA,
                captured_at=now, refs=refs, actor_id=run["requested_by"], step_id=stage_id)
            text_id = await self.save_markdown(store, run, stage_id, markdown(report), report_id, detail_id)
            summary_id = uuid4()
            await store.db.execute(update(S).where(*store.where(S, S.c.id == stage_id)).values(
                state=stage_state, ended_at=now, output_artifact_id=summary_id,
                error=error(reason, now) if reason else null()))
            # Result, members, current judgment, reports and the C6 terminal
            # step commit together. Failure cannot publish a different report.
            outcome = ({"run_id": str(run_id), "result_id": None,
                "adoption": {"state": "not_eligible", "reason": "unknown_call_present"}} if uncertain
                else await store.publish(case_id, run_id, pub, result_id=result_id))
            from .subject_risk_opinions import apply_saved
            await apply_saved(store, run)
            summary = {"schema_version": contract.SCHEMA, "type": "delivery_receipt", "run_id": str(run_id),
                "state": stage_state, "reason": reason, "report_artifact_id": str(report_id),
                "detail_artifact_id": str(detail_id),
                "stage_delivery": prepared.get("stage_delivery"),
                "markdown_artifact_id": str(text_id), "domain_artifact_ids": domains,
                "evidence_directory": directory,
                "evidence_set_key": key, "delivery_state": report_result["delivery_state"], "outcome": outcome,
                **({"run_state": "unknown", "local_execution_state": "ended", "closing_state": "saved",
                    "adoption_eligible": False, "comparison_eligible": False} if uncertain else {}),
                "captured_at": now.isoformat()}
            await store.save_input_artifact(case_id, run_id, summary_id, summary, kind="source_snapshot",
                schema=contract.SCHEMA, captured_at=now, refs=[reference("artifact", report_id, "execution_receipt")],
                actor_id=run["requested_by"], step_id=stage_id)
        return summary

    async def save_markdown(self, store, run, step_id, text, report_id, detail_id):
        body = text.encode("utf-8")
        identity, sha = uuid4(), hashlib.sha256(body).hexdigest()
        await store.db.execute(insert(F).values(id=identity, tenant_id=store.tenant_id,
            case_id=run["case_id"], run_id=run["id"], step_id=step_id, kind="report_markdown",
            schema_version=contract.SCHEMA, content_text=text, mime_type="text/markdown", sha256=sha,
            size_bytes=len(body), captured_at=await store.now(), material_state="complete", created_by=run["requested_by"],
            source_refs=[reference("artifact", report_id, "execution_receipt"), reference("artifact", detail_id, "execution_receipt")],
            retention={"original_size_bytes": len(body), "retained_size_bytes": len(body), "original_sha256": sha,
                "retained_sha256": sha, "truncated": False, "reason": None, "omitted_paths": []}))
        return identity
