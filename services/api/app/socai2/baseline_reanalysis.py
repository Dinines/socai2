"""New C3 step for a new evidence set; initial and prior rounds stay immutable."""
import asyncio
import json
from itertools import zip_longest
from uuid import UUID, uuid4

from sqlalchemy import insert, select

from . import baseline_analysis_contract as contract
from . import baseline_deep_contract as deep_contract
from . import baseline_evidence as evidence
from . import baseline_graph_projection as graph_contract
from .baseline_analysis import BaselineAnalysis
from .baseline_analysis_model import TenantChatGateway
from .baseline_context import reference
from .baseline_enrichment import S
from .baseline_final_evidence import query_candidates, share_query_context
from .baseline_reasoning import ModelSteps, bounded_input, evidence_candidates
from .baseline_store import F, StoreError, digest
from .model_input_view import frozen_items, source_members
from .structured_output import response_format


class BaselineReanalysis(ModelSteps):
    def __init__(self, service):
        super().__init__(service, contract.SCHEMA)

    async def input(self, tenant_id, case_id, run_id, context, previous, prior_id, bases, *,
                    instruction=None, extra_data=None, lead_candidates=(), executed_plan_id=None):
        if context.case_input_profile is not None and (extra_data or {}).get("round") == "final_delivery":
            from .case_followup_loader import final
            return await final(self, tenant_id, case_id, run_id, previous, prior_id, bases, extra_data, lead_candidates)
        async with self.service.transaction(tenant_id) as store:
            initial = await store.prepare_model_view(case_id, run_id)
            snapshots = [r["content_json"] for r in bases if r["content_json"].get("type") == "graph_snapshot"]
            newest = max(snapshots, key=lambda r: r["captured_at"]) if snapshots else None
            current_ids = {str(r["id"]) for r in bases if r["content_json"].get("type") in {"materials", "query_projection"}}
            graph_state = "not_built" if not newest else "available" if current_ids <= set(newest["input_artifact_ids"]) else "stale"
            graphs = [(newest, await self.read_artifact(store, run_id, UUID(newest["graph_artifact_id"])))] if graph_state == "available" else []
            rows = (await store.db.execute(select(F).where(*store.where(F, F.c.run_id == run_id,
                F.c.kind == "tool_response")))).mappings().all()
            if any(digest(r["content_json"]) != r["sha256"] for r in rows):
                raise StoreError("evidence_receipt_invalid")
            tools = {str(r["id"]): r["content_json"] for r in rows}
        current = await evidence.BaselineEvidence(self.service).model_view(tenant_id, case_id, run_id, context.questions[0].id)
        inputs = [initial["artifact_id"], current["artifact_id"], *([str(prior_id)] if prior_id else []), *[str(r["id"]) for r in bases]]
        if not initial["ready"] or not current["ready"]:
            return {"ready": False, "reason": "model_view_not_ready", "input_artifact_ids": inputs,
                "messages": [], "source_map": {}, "coverage": {}, "omissions": []}
        old = json.loads(initial["messages"][1]["content"])
        new, observations = evidence_candidates(current)
        final = (extra_data or {}).get("round") == "final_delivery"
        final_observations = []
        if final and new["queries"]:
            final_observations, missing = query_candidates(new["queries"], bases)
            if missing:
                return {"ready": False, "reason": "required_query_evidence_unavailable", "messages": [],
                    "source_map": {}, "coverage": {}, "omissions": missing, "input_artifact_ids": inputs}
            observations = [c for c in observations if c["source"]["membership_basis"] != "query_binding_only"]
        old_candidates, judgments, graph_candidates = [], [], []
        for snapshot, graph in graphs:
            nodes = {n["id"]: n for n in graph["nodes"]}
            records = {eid: item for item in snapshot["records"] for eid in item["edge_ids"]}
            for i, edge in enumerate(graph["edges"]):
                record = records[edge["id"]]
                related = record.get("related_alert_ids", [record["alert_id"]] if record.get("alert_id") else [])
                ref = reference("artifact", snapshot["graph_artifact_id"], "prior_analysis", f"$.edges.{i}")
                graph_candidates.append({"original": [edge, nodes[edge["from"]], nodes[edge["to"]]],
                    "entry": {"role": "prior_analysis", "alert_ids": related,
                        "value": {"relation": edge["relation"], "strength": edge["strength"],
                            "from": nodes[edge["from"]]["label"], "to": nodes[edge["to"]]["label"],
                            "limitations": edge["limitations"] + graph["limitations"]}},
                    "source": {"ref": ref, "alert_ids": related,
                        "membership_basis": record.get("membership_basis", "source_label")}})
        for i, item in enumerate(frozen_items(old)):
            aids = source_members(context, item["source"], tools)
            old_candidates.append({"original": item["value"], "entry": {"role": item["source"]["role"],
                "alert_ids": aids, "value": item["value"], "limitations": item["limitations"]},
                "source": {"ref": item["source"], "alert_ids": aids},
                # Prior A/I judgments stay paired and whole when selected. They
                # must not crowd out facts, time, human feedback or actual plans.
                "required": item["source"]["role"] == "human_statement"
                    or (extra_data or {}).get("round") != "final_delivery" and (
                        item["source"]["source_path"].endswith(".triage") or item["source"]["source_path"].endswith(".diagnosis"))
                    or item["source"]["source_path"].endswith(".alert.event_time")
                    or item["source"]["type"] == "alert_material" and item["source"]["role"] == "observation"})
        all_aids = sorted(context.alerts)
        prior_analysis = (previous or {}).get("analysis")
        if prior_analysis:
            judgments.append({"original": prior_analysis, "entry": {"role": "prior_analysis", "alert_ids": all_aids,
                "value": {"previous_summary": prior_analysis["summary"]}},
                "source": {"ref": reference("artifact", prior_id, "prior_analysis", "$.analysis"), "alert_ids": all_aids}})
        for index, item in enumerate((prior_analysis or {}).get("followups", [])):
            if str(prior_id) == executed_plan_id:
                continue  # The original plan is already retained as required input.
            judgments.append({"original": item, "entry": {"role": "prior_analysis", "alert_ids": item["alert_ids"],
                # S identifiers belonged to the previous request. Do not expose
                # them as if they addressed this request's newly assigned S map.
                "value": {"followup": {k: v for k, v in item.items() if k != "source_ids"}}},
                "source": {"ref": reference("artifact", prior_id, "prior_analysis", f"$.analysis.followups.{index}"),
                    "alert_ids": item["alert_ids"]}})
        for r in bases:
            value = r["content_json"]
            if value.get("type") == "deep_summary" and value.get("answer"):
                judgments.append({"original": value["answer"], "entry": {"role": "prior_analysis", "alert_ids": all_aids,
                    "value": {"question_id": value["question_id"], "answer": {k: value["answer"][k]
                        for k in ("state", "text", "alternatives", "limitations")}}},
                    "source": {"ref": reference("artifact", r["id"], "prior_analysis", "$.answer"), "alert_ids": all_aids}})
        candidates = [*lead_candidates, *final_observations]
        for group in zip_longest(old_candidates, observations, judgments, graph_candidates):
            for item in group:
                if item:
                    candidates.append(item)
        for i, item in enumerate(candidates, 1):
            item["entry"]["id"] = "S" + str(i)
        data = {"scope": old["scope"], "members": {aid: {"included": 0, "material_state": a["material_state"],
            "limitations": a["limitations"]} for aid, a in initial["coverage"].items()},
            "questions": old["questions"], "source_states": old["source_states"], "queries": new["queries"], "graph_state": graph_state,
            "round": "post_evidence_reanalysis", "limitations": ["original_scope_and_material_versions_unchanged",
                "query_binding_only_does_not_prove_alert_membership", "old_analysis_is_not_independent_evidence",
                "derived_graph_is_not_independent_evidence_or_confirmed_impact"]}
        if "program_facts" in old:
            data["program_facts"] = old["program_facts"]
        prompt = contract.PROMPT.replace("C3初始主分析", "C3补证后再分析") + (
            "\n综合本轮新观察与冻结前序资料，逐成员和六问题重新说明当前认识、替代解释和限制。"
            "query_binding_only表示主机/时间匹配，不能据此写为某条告警的observed发现；关系只能暂作inferred或unresolved。"
            "Deep回答和派生图均是prior_analysis，不是独立证据；图连通不证明因果或受影响。"
            "不要只复述旧判断。此步骤不发布最终案件结果。")
        if extra_data:
            data.update(extra_data)
        instruction = instruction or prompt
        if final and new["queries"]:
            share_query_context(data)
            instruction += "\nquery_context字段由所有queries继承；projected_fields仅计投影字段，visible_fields计本次可见字段，partial不是完整查询复核。"
        return {**bounded_input(data, candidates, instruction), "input_artifact_ids": list(dict.fromkeys(inputs)),
                "program_facts": data.get("program_facts")}

    async def execute(self, tenant_id, case_id, run_id, gateway=None):
        gateway = gateway or TenantChatGateway()
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            context = await store.read_context(case_id, run_id)
            rows = (await store.db.execute(select(F).where(*store.where(F, F.c.run_id == run_id,
                F.c.kind == "source_snapshot", F.c.schema_version.in_([
                    evidence.SCHEMA, deep_contract.SCHEMA, graph_contract.SCHEMA]))))
                ).mappings().all()
            if any(digest(r["content_json"]) != r["sha256"] for r in rows):
                raise StoreError("evidence_receipt_invalid")
            bases = sorted([r for r in rows if r["content_json"].get("type") in {
                "materials", "query_projection", "deep_summary", "graph_snapshot"}], key=lambda r: str(r["id"]))
            if not bases:
                raise StoreError("new_evidence_required")
            key = digest([str(r["id"]) for r in bases])
            replay = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id,
                S.c.kind == "stage", S.c.stage_code == "C3.reanalysis", S.c.name == key)))
            if replay:
                if replay["state"] in {"running", "unknown", "planned"}:
                    raise StoreError("reanalysis_already_claimed")
                return await self.read_artifact(store, run_id, replay["output_artifact_id"])
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            await self.idle(store, run_id)
            prior = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id,
                S.c.kind == "stage", S.c.stage_code.in_(["C3", "C3.reanalysis"]),
                S.c.state == "completed")).order_by(S.c.seq.desc()).limit(1))
            if not prior:
                raise StoreError("initial_analysis_required")
            prior_id = prior["output_artifact_id"]
            previous = await self.read_artifact(store, run_id, prior_id)
            if not previous.get("analysis"):
                raise StoreError("initial_analysis_required")
            stage_id = uuid4()
            await store.db.execute(insert(S).values(id=stage_id, tenant_id=tenant_id, run_id=run_id,
                seq=await self.seq(store, run_id), kind="stage", stage_code="C3.reanalysis", name=key,
                state="running", implementation_version=contract.SCHEMA, started_at=await store.now(), input_artifact_id=prior_id))
        try:
            prepared = await self.input(tenant_id, case_id, run_id, context, previous, prior_id, bases)
            parser = lambda content: contract.parse(content, prepared["source_map"], context, prepared["coverage"])
            result, reason, model_id, response_id = await self.call(tenant_id, case_id, run_id,
                stage_id, "C3.reanalysis", prepared, gateway, parser,
                output_format=response_format(contract.Analysis, prepared["source_map"],
                    members=context.alerts, questions=[q.id for q in context.questions],
                    objects=context.scope.object_keys))
            return await BaselineAnalysis(self.service).finish(tenant_id, case_id, run_id, stage_id, model_id,
                "completed" if result else "failed" if model_id else "skipped", reason,
                [reference("artifact", UUID(i), "execution_receipt") for i in prepared["input_artifact_ids"]],
                analysis=result, source_map=prepared.get("source_map"), context=context, response_id=response_id,
                phase="C3_reanalysis", basis={"evidence_set_key": key, "comparison_analysis_artifact_id": str(prior_id),
                    "input_artifact_ids": prepared["input_artifact_ids"]})
        except (Exception, asyncio.CancelledError):
            await self.uncertain(tenant_id, case_id, run_id, stage_id)
            raise
