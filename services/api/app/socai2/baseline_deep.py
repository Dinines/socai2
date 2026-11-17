"""One owned, bounded Deep loop per frozen question, on the existing Run."""
import asyncio
from uuid import UUID, uuid4

from sqlalchemy import insert, null, select, update

from . import baseline_deep_contract as contract
from .baseline_analysis_model import TenantChatGateway
from .baseline_context import reference
from .baseline_enrichment import S, error
from .baseline_evidence import BaselineEvidence
from .baseline_evidence_tools import LakeGateway
from .baseline_reasoning import ModelSteps
from .baseline_store import StoreError
from .followup_activity import activity, query_record

SCHEMA = contract.SCHEMA


class BaselineDeep(ModelSteps):
    def __init__(self, service):
        super().__init__(service, SCHEMA)

    async def input(self, tenant_id, case_id, run_id, question_id, initial, initial_id, lake):
        from .case_followup_loader import deep
        from .case_model_boundary import selected_profile
        async with self.service.transaction(tenant_id, readonly=True) as store:
            selected_profile(await store.read_context(case_id, run_id))
        return await deep(self, tenant_id, case_id, run_id, question_id, initial, initial_id, lake)

    async def execute(self, tenant_id, case_id, run_id, question_id, gateway=None, lake=None):
        gateway, lake = gateway or TenantChatGateway(), lake or LakeGateway(self.service)
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            context = await store.read_context(case_id, run_id)
            from .case_model_boundary import selected_profile
            selected_profile(context)
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
                from .citation_quality import new_review
                prepared["citation_review"] = new_review()
                from . import case_deep_delivery
                from .case_followup_output import deep_format
                output_format = deep_format(prepared)
                decision, reason, model_id, response_id = await self.call(tenant_id, case_id, run_id,
                    stage_id, "C4.deep", prepared, gateway, case_deep_delivery.parser(prepared),
                    output_format=output_format)
                delivery = await case_deep_delivery.save_receipt(self, tenant_id, case_id, run_id,
                    prepared, model_id, response_id, reason)
                if model_id:
                    iterations.append({"model_step_id": str(model_id), "response_id": str(response_id),
                        "input_artifact_ids": prepared["input_artifact_ids"],
                        "action": decision.action if decision else None, "query_receipt_id": None,
                        "stage_delivery": delivery})
                if reason:
                    failed = model_id is not None and not (prepared.get("unit_delivery") or {}).get("answer")
                    break
                if decision.action != "query":
                    break
                binding = prepared["binding_map"][decision.binding_id]
                queried = await BaselineEvidence(self.service).query(tenant_id, case_id, run_id,
                    binding, question_id, lake, parent_step_id=stage_id)
                iterations[-1]["query_receipt_id"] = queried["artifact_id"]
                iterations[-1]["query_activity"] = query_record(queried)
                decision = None  # a query proposal is not an answer
                if queried["result"]["state"] != "completed":
                    reason = "query_not_completed:" + (queried["projection"]["reason"] or queried["result"]["state"])
                    break
            return await self.finish(tenant_id, case_id, run_id, stage_id, question,
                decision, prepared, iterations, reason, failed)
        except (Exception, asyncio.CancelledError) as exc:
            await self.uncertain(tenant_id, case_id, run_id, stage_id, exc)
            raise

    async def finish(self, tenant_id, case_id, run_id, stage_id, question, decision, prepared, iterations, reason, failed):
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            retained = (prepared or {}).get("unit_delivery") or {}
            answer = decision.answer if decision else (
                contract.Answer.model_validate(retained["answer"]) if retained.get("answer") else None)
            source_map = prepared.get("source_map", {}) if answer else {}
            now = await store.now()
            limits = ["question_level_analysis_not_final_case_judgment", "structure_checked_citations_recorded_not_truth_proven",
                "empty_queries_are_not_counterevidence", "no_automatic_task_creation_or_adoption"]
            if reason:
                limits.append(reason)
            from .case_citation_quality import links
            q = question.model_dump(mode="json")
            q.update(state="answered" if answer and answer.state == "supported" else "unresolved",
                answer=answer.text if answer else None,
                evidence_refs=links(answer.support_ids + answer.counter_ids, source_map, evidence_only=True) if answer else [],
                limitations=[*limits, *(answer.limitations if answer else [])])
            block = {"schema_version": SCHEMA, "domain": "question_deep", "questions": [q],
                "findings": [], "recommendations": [], "limitations": limits}
            refs = [reference("artifact", UUID(i["response_id"]), "execution_receipt") for i in iterations]
            block_id = await self.save(store, run, stage_id, block, "deep_analysis", refs)
            state = "failed" if failed else "completed" if iterations else "skipped"
            queries = [i["query_activity"] for i in iterations if "query_activity" in i]
            value = {"schema_version": SCHEMA, "type": "deep_summary", "run_id": str(run_id),
                "question_id": question.id, "state": state, "stop_reason": reason or decision.action,
                "answer": answer.model_dump(mode="json") if answer else None, "source_map": source_map,
                "citation_review": prepared.get("citation_review") if prepared else None,
                "iterations": iterations, "deep_artifact_id": str(block_id), "limitations": limits,
                "activity": activity("analysis_with_queries" if queries else "material_analysis", queries,
                                     disposition=decision.action if decision else reason),
                "captured_at": now.isoformat()}
            identity = await self.save(store, run, stage_id, value, "source_snapshot", refs)
            await store.db.execute(update(S).where(*store.where(S, S.c.id == stage_id)).values(state=state,
                ended_at=now, output_artifact_id=identity, error=error(reason, now) if reason else null()))
        return value
