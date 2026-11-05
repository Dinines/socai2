"""One manually claimed Run, one C1-C6 pipeline; no queue or automatic resume."""
from uuid import uuid4

from sqlalchemy import insert, select, update

from .baseline_analysis_model import TenantChatGateway
from .baseline_context import reference
from .baseline_contracts import FULL_EXECUTOR_VERSION
from .baseline_enrichment import S
from .baseline_evidence_tools import LakeGateway
from .baseline_reasoning import ModelSteps
from .baseline_store import StoreError

SCHEMA = FULL_EXECUTOR_VERSION


class BaselineExecutor(ModelSteps):
    def __init__(self, service, tenant_id, *, gateway=None, lake=None):
        super().__init__(service, SCHEMA)
        self.tenant_id = tenant_id
        self.gateway = gateway or TenantChatGateway()
        self.lake = lake or LakeGateway(service)

    async def record(self, store, run, code, payload, refs):
        # These completed steps record planning/dispatch decisions. They do not
        # pretend to be an active parent that would conflict with C2-C6 owners.
        identity, now = uuid4(), await store.now()
        await store.db.execute(insert(S).values(id=identity, tenant_id=store.tenant_id,
            run_id=run["id"], seq=await self.seq(store, run["id"]), kind="stage", stage_code=code,
            name=payload["type"], state="running", started_at=now, implementation_version=SCHEMA))
        output_id = await self.save(store, run, identity, payload, "source_snapshot", refs)
        await store.db.execute(update(S).where(*store.where(S, S.c.id == identity)).values(
            state="completed", ended_at=now, output_artifact_id=output_id))
        return output_id

    async def __call__(self, claim):
        tenant_id, case_id, run_id = self.tenant_id, claim.case_id, claim.run_id
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running" or run["executor_version"] != SCHEMA:
                raise StoreError("full_executor_claim_required")
            if await store.one(select(S.c.id).where(*store.where(S, S.c.run_id == run_id,
                    S.c.stage_code == "C1.executor"))):
                raise StoreError("full_executor_already_claimed")
            await self.idle(store, run_id)
            plan_id = await self.record(store, run, "C1.executor", {
                "schema_version": SCHEMA, "type": "execution_plan", "run_id": str(run_id),
                "sequence": ["C1", "C2", "C3", "C4", "C5", "C6"],
                "limits": run["limits"], "final_model_calls_reserved": 1,
                "followup_policy": "C3_order_unique_question_query_or_deep_via_bounded_Deep",
                "limitations": ["call_slot_only_tokens_and_deadline_still_shared",
                    "no_automatic_successor_retry_or_task_creation", "graph_uses_retained_sources_only"],
            }, [reference("artifact", run["input_artifact_id"], "execution_receipt")])

        await self.service.enrich(tenant_id, case_id, run_id)
        initial = await self.service.analyze(tenant_id, case_id, run_id, gateway=self.gateway)
        await self.service.prepare_evidence(tenant_id, case_id, run_id)
        routes, by_question = [], {}
        for index, item in enumerate((initial.get("analysis") or {}).get("followups", [])):
            qid, mode = item["question_id"], item["mode"]
            route = {"followup_index": index, "question_id": qid, "mode": mode}
            if mode == "human":
                route.update(state="handoff", reason="human_confirmation_required_no_task_created")
            elif mode == "graph":
                route.update(state="scheduled", reason="C5_retained_evidence_graph_only")
            else:
                if qid not in by_question:
                    result = await self.service.deepen(tenant_id, case_id, run_id, qid,
                        gateway=self.gateway, lake=self.lake)
                    by_question[qid] = {"state": result["state"], "reason": result["stop_reason"],
                        "deep_artifact_id": result["deep_artifact_id"], "answer_available": result["answer"] is not None}
                route.update(by_question[qid])
            routes.append(route)

        graph = await self.service.build_graph(tenant_id, case_id, run_id)
        for route in routes:
            if route["mode"] == "graph":
                route.update(state="completed", graph_artifact_id=graph["graph_artifact_id"])
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            await self.idle(store, run_id)
            stage = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id,
                S.c.stage_code == "C3", S.c.kind == "stage")))
            await self.record(store, run, "C4.routing", {
                "schema_version": SCHEMA, "type": "followup_dispatch", "run_id": str(run_id),
                "initial_analysis_artifact_id": str(stage["output_artifact_id"]),
                "initial_state": initial["state"], "routes": routes,
                "graph_artifact_id": graph["graph_artifact_id"],
                "limitations": ["completed_Deep_does_not_mean_question_answered",
                    "graph_completion_does_not_mean_external_topology_queried",
                    "unexecuted_or_human_followups_remain_unresolved"],
            }, [reference("artifact", plan_id, "execution_receipt"),
                reference("artifact", stage["output_artifact_id"], "execution_receipt"),
                reference("artifact", graph["graph_artifact_id"], "execution_receipt")])
        # C6 performs post-evidence synthesis and report generation in one call.
        return await self.service.finalize(tenant_id, case_id, run_id, gateway=self.gateway)
