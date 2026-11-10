"""One owned, bounded Deep loop per frozen question, on the existing Run."""
import asyncio
import json
from datetime import datetime
from itertools import zip_longest
from uuid import UUID, uuid4

from sqlalchemy import insert, null, select, update

from . import baseline_deep_contract as contract
from .baseline_analysis_model import TenantChatGateway
from .baseline_context import reference
from .baseline_contracts import Limits
from .baseline_enrichment import S, error
from .baseline_evidence import BaselineEvidence
from .baseline_evidence_tools import LakeGateway
from .baseline_model_view import blocked, field_limit
from .baseline_reasoning import ModelSteps, bounded_input, evidence_candidates
from .baseline_store import F, StoreError, digest, encoded
from .baseline_tool_catalog import capabilities
from .runtime_policy import draft_limit
from .structured_output import response_format

SCHEMA = contract.SCHEMA


class BaselineDeep(ModelSteps):
    def __init__(self, service):
        super().__init__(service, SCHEMA)

    async def input(self, tenant_id, case_id, run_id, question_id, initial, initial_id, lake):
        async with self.service.transaction(tenant_id) as store:
            frozen = await store.read_context(case_id, run_id)
        if frozen.case_input_profile is not None:
            from .case_followup_loader import deep
            return await deep(self, tenant_id, case_id, run_id, question_id, initial, initial_id, lake)
        view = await BaselineEvidence(self.service).model_view(tenant_id, case_id, run_id, question_id)
        if not view["ready"]:
            return {**view, "input_artifact_ids": [view["artifact_id"], str(initial_id)]}
        data, candidates = evidence_candidates(view)
        prior = {"role": "prior_analysis", "question": next(q for q in initial["analysis"]["questions"] if q["id"] == question_id),
                 "followups": [f for f in initial["analysis"]["followups"] if f["question_id"] == question_id]}
        prior_reason = "source_guard_blocked" if blocked(prior) else "whole_field_exceeds_budget" if len(encoded(prior)) > field_limit() else None
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            context = await store.read_context(case_id, run_id)
            base_view = await store.prepare_model_view(case_id, run_id)
            tool_rows = (await store.db.execute(select(F).where(*store.where(F,
                F.c.run_id == run_id, F.c.kind == "tool_response")))).mappings().all()
            if any(digest(r["content_json"]) != r["sha256"] for r in tool_rows):
                raise StoreError("evidence_receipt_invalid")
            tool_payloads = {str(r["id"]): r["content_json"] for r in tool_rows}
            material, material_id = await self.prepared(store, run)
            steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == run_id)))).mappings().all()
            attempts = {s["name"] for s in steps if s["stage_code"] == "C4.query"}
            limits, now = Limits.model_validate(run["limits"]), await store.now()
            used = sum(s["kind"] == "tool" and s["state"] not in {"planned", "skipped"} for s in steps)
            available = (lake.configured() and limits.max_tool_calls is not None and used < limits.max_tool_calls
                and limits.max_rows_per_query is not None and limits.max_rows_per_query > 0
                and limits.deadline_at is not None and (limits.deadline_at - now).total_seconds() >= 1)
            choices = [(bid, b) for bid, b in material["catalog"]["bindings"].items() if bid not in attempts] if available else []
            # Current product snapshots do not depend on a historical window.
            # Lake observations still require a valid frozen interval.
            valid_window = (data["scope"]["window_start"] and data["scope"]["window_end"]
                and datetime.fromisoformat(data["scope"]["window_start"]) < datetime.fromisoformat(data["scope"]["window_end"]))
            choices = [(bid, b) for bid, b in choices if b["tool_name"] == "product_host_details" or valid_window]
            # Disabled/unbound adapters are not executable model choices. The
            # full frozen catalogue and omissions remain in the evidence ledger.
            unavailable = getattr(lake, "unavailable_reason", None)
            if unavailable is not None:
                choices = [(bid, b) for bid, b in choices if unavailable(b) is None]
        background = []
        if base_view["ready"]:
            from .model_input_view import frozen_items, source_members
            original_items = frozen_items(json.loads(base_view["messages"][1]["content"]))
            for item in sorted(original_items, key=lambda item: item["source"]["role"] != "human_statement"):
                owned = source_members(context, item["source"], tool_payloads)
                background.append({"original": item["value"], "entry": {"role": item["source"]["role"],
                    "alert_ids": owned, "value": item["value"], "limitations": item["limitations"]},
                    "source": {"ref": item["source"], "alert_ids": owned},
                    "required": item["source"]["role"] == "human_statement"})
        merged = [item for pair in zip_longest(candidates, background) for item in pair if item]
        for i, item in enumerate(merged, 1):
            item["entry"]["id"] = "E" + str(i)
        candidates = merged
        options, mapping = [], {}
        for bid, binding in sorted(choices):
            alias = "B" + str(len(options) + 1)
            option = {"id": alias, "tool_name": binding["tool_name"], "hostname": binding["hostname"],
                "related_alert_ids": binding["alert_ids"]}
            if len(encoded([*options, option])) > draft_limit():
                break
            options.append(option)
            mapping[alias] = bid
        mandatory = {"scope": data["scope"], "question": data["question"], "members": {
            aid: {**row, "included": 0} for aid, row in data["coverage"].items()},
            "queries": data["queries"], "prior_analysis": None if prior_reason else prior,
            "prior_analysis_omission": prior_reason, "tool_options": options,
            "tool_capabilities": capabilities({o["tool_name"] for o in options}),
            "unoffered_query_count": len(choices) - len(options),
            "tool_availability": ("available" if choices else "no_unqueried_enabled_binding")
                if available else "source_scope_or_remaining_budget_unavailable",
            "limitations": ["tool_members_are_query_bindings_not_row_attribution", "empty_queries_are_not_counterevidence",
                "only_listed_tools_available_no_automatic_scope_expansion"]}
        prepared = bounded_input(mandatory, candidates, contract.PROMPT)
        return {**prepared, "binding_map": mapping,
            "input_artifact_ids": [view["artifact_id"], base_view["artifact_id"], str(initial_id), str(material_id)]}

    async def execute(self, tenant_id, case_id, run_id, question_id, gateway=None, lake=None):
        gateway, lake = gateway or TenantChatGateway(), lake or LakeGateway(self.service)
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            context = await store.read_context(case_id, run_id)
            question = next((q for q in context.questions if q.id == question_id), None)
            if question is None:
                raise StoreError("question_outside_frozen_scope", 422)
            prior = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id,
                S.c.kind == "stage", S.c.stage_code == "C4.deep", S.c.question_id == question_id)))
            if prior:
                if prior["state"] in {"running", "unknown", "planned"}:
                    raise StoreError("deep_already_claimed")
                return await self.read_artifact(store, run_id, prior["output_artifact_id"])
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            await self.idle(store, run_id)
            c3 = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id,
                S.c.kind == "stage", S.c.stage_code == "C3", S.c.state == "completed")))
            if not c3:
                raise StoreError("initial_analysis_required")
            initial_id = c3["output_artifact_id"]
            initial = await self.read_artifact(store, run_id, initial_id)
            if not initial.get("analysis"):
                raise StoreError("initial_analysis_required")
            stage_id = uuid4()
            await store.db.execute(insert(S).values(id=stage_id, tenant_id=tenant_id, run_id=run_id,
                seq=await self.seq(store, run_id), kind="stage", stage_code="C4.deep", question_id=question_id,
                name="question_deep", state="running", implementation_version=SCHEMA,
                started_at=await store.now(), input_artifact_id=initial_id))
        iterations, decision, prepared, reason, failed = [], None, None, None, False
        try:
            await BaselineEvidence(self.service).prepare(tenant_id, case_id, run_id)
            while True:
                prepared = await self.input(tenant_id, case_id, run_id, question_id, initial, initial_id, lake)
                parser = lambda content, p=prepared: contract.parse(content, p["source_map"], p.get("binding_map", {}), question_id)
                output_format = response_format(contract.Decision, prepared["source_map"],
                    questions=[question_id], bindings=prepared.get("binding_map", {}))
                if "followup_boundary" in prepared:
                    from .case_followup_output import deep_format, parse_deep
                    parser = lambda content, p=prepared: parse_deep(content, p)
                    output_format = deep_format(prepared)
                decision, reason, model_id, response_id = await self.call(tenant_id, case_id, run_id,
                    stage_id, "C4.deep", prepared, gateway, parser,
                    output_format=output_format)
                if model_id:
                    iterations.append({"model_step_id": str(model_id), "response_id": str(response_id),
                        "input_artifact_ids": prepared["input_artifact_ids"],
                        "action": decision.action if decision else None, "query_receipt_id": None})
                if reason:
                    failed = model_id is not None
                    break
                if decision.action != "query":
                    break
                binding = prepared["binding_map"][decision.binding_id]
                queried = await BaselineEvidence(self.service).query(tenant_id, case_id, run_id,
                    binding, question_id, lake, parent_step_id=stage_id)
                iterations[-1]["query_receipt_id"] = queried["artifact_id"]
                decision = None  # a query proposal is not an answer
                if queried["result"]["state"] != "completed":
                    reason = "query_not_completed:" + (queried["projection"]["reason"] or queried["result"]["state"])
                    break
            return await self.finish(tenant_id, case_id, run_id, stage_id, question,
                decision, prepared, iterations, reason, failed)
        except (Exception, asyncio.CancelledError):
            await self.uncertain(tenant_id, case_id, run_id, stage_id)
            raise

    async def finish(self, tenant_id, case_id, run_id, stage_id, question, decision, prepared, iterations, reason, failed):
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            answer = decision.answer if decision else None
            source_map = prepared.get("source_map", {}) if answer else {}
            now = await store.now()
            limits = ["question_level_analysis_not_final_case_judgment", "structure_and_sources_checked_not_truth_proven",
                "empty_queries_are_not_counterevidence", "no_automatic_task_creation_or_adoption"]
            if reason:
                limits.append(reason)
            q = question.model_dump(mode="json")
            q.update(state="answered" if answer and answer.state == "supported" else "unresolved",
                answer=answer.text if answer else None,
                evidence_refs=[source_map[s]["ref"] for s in dict.fromkeys(answer.support_ids + answer.counter_ids)] if answer else [],
                limitations=[*limits, *(answer.limitations if answer else [])])
            block = {"schema_version": SCHEMA, "domain": "question_deep", "questions": [q],
                "findings": [], "recommendations": [], "limitations": limits}
            refs = [reference("artifact", UUID(i["response_id"]), "execution_receipt") for i in iterations]
            block_id = await self.save(store, run, stage_id, block, "deep_analysis", refs)
            state = "failed" if failed else "completed" if iterations else "skipped"
            value = {"schema_version": SCHEMA, "type": "deep_summary", "run_id": str(run_id),
                "question_id": question.id, "state": state, "stop_reason": reason or decision.action,
                "answer": answer.model_dump(mode="json") if answer else None, "source_map": source_map,
                "iterations": iterations, "deep_artifact_id": str(block_id), "limitations": limits,
                "captured_at": now.isoformat()}
            identity = await self.save(store, run, stage_id, value, "source_snapshot", refs)
            await store.db.execute(update(S).where(*store.where(S, S.c.id == stage_id)).values(state=state,
                ended_at=now, output_artifact_id=identity, error=error(reason, now) if reason else null()))
        return value
