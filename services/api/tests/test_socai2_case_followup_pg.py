"""Configured C3 -> query/Deep -> C6 with real isolated persistence only."""
import copy
import json
from types import SimpleNamespace
from uuid import UUID

from app.models.socai2 import Results
from app.socai2.baseline_context import reference
from app.socai2.baseline_dispatch import dispatch_followups
from app.socai2.baseline_executor import SCHEMA, BaselineExecutor
from app.socai2.baseline_store import F, R
from jsonschema import Draft202012Validator
from socai2_test_model_view import synthetic_measure
from sqlalchemy import select
from test_socai2_baseline_evidence import SyntheticLake
from test_socai2_case_boundary_pg import role_finding
from test_socai2_case_followup_boundary import final_answer

T = UUID(int=1)


class Gateway:
    provider, model = "synthetic", "synthetic-followup-no-network"

    def __init__(self, service, cid, rid, mode):
        self.service, self.cid, self.rid, self.mode = service, cid, rid, mode
        self.calls, self.deep_calls, self.final_calls = 0, 0, 0
        self.requests, self.responses = [], []

    async def configure(self, *_):
        return True

    async def measure(self, body, stage):
        return await synthetic_measure(body, stage)

    async def complete(self, body, timeout):
        assert timeout > 0
        self.calls += 1
        async with self.service.transaction(T, readonly=True) as store:
            request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.run_id == self.rid, F.c.kind == "model_request"))
                .order_by(F.c.captured_at.desc()).limit(1))).scalar_one()["payload"]
            context = await store.read_context(self.cid, self.rid)
            material = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.run_id == self.rid, F.c.content_json["type"].astext == "materials")))).scalar_one()
        assert request["body"] == body
        assert request["followup_boundary"]["records"]
        assert "business-id" in body["messages"][1]["content"]
        stage = request["case_boundary"]["stage"]
        if stage == "Deep":
            self.deep_calls += 1
            if self.deep_calls == 1:
                assert request["binding_map"]
                binding = next(alias for alias, bid in request["binding_map"].items()
                               if material["catalog"]["bindings"][bid]["tool_name"] == "process_activity")
                answer = {"action": "query", "binding_id": binding,
                          "reason": "Synthetic request for one query.", "answer": None}
            else:
                assert request["followup_boundary"]["query_facts"][0]["observed_rows_in_bounded_fetch"] == 1
                sid = next(s for s, row in request["source_map"].items() if row.get("membership_basis") == "query_binding_only")
                answer = {"action": "answer", "binding_id": None, "reason": "Synthetic bounded answer.",
                    "answer": {"state": "unresolved", "text": "Synthetic query returned data; authorization still unknown.",
                        "support_ids": [sid], "counter_ids": [], "alternatives": [], "limitations": ["Synthetic only."]}}
        else:
            self.final_calls += 1
            comparison = request["followup_boundary"]["program_metadata"]["comparison"]
            if self.mode == "fallback":
                assert "没有可用的C3判断" in body["messages"][1]["content"]
            else:
                rows = request["followup_boundary"]["records"]
                expected_questions = {q.id for q in context.questions if q.id != "coverage"}
                assert any(r["block"] == "C3" and {q["id"] for q in r["value"]["questions"]} == expected_questions
                           for r in rows)
                assert any(r["block"] == "Deep" and r["value"]["support_ids"] for r in rows)
                assert any(r["block"] == "plan" and r["value"]["followup"]["source_ids"] for r in rows)
                assert all(d["visible_id"] for d in request["followup_boundary"]["dependencies"])
            answer = final_answer(request, context, comparison)
            if self.mode == "correction" and self.final_calls == 1:
                answer["analysis"]["members"][0].update(state="analyzed", evidence_ids=[])
            if self.mode == "correction" and self.final_calls == 2:
                assert json.loads(body["messages"][-1]["content"])["errors"][0]["subject_id"] == "A1"
            if self.mode == "recommendation_correction" and self.final_calls == 2:
                assert any(e["code"] == "recommendation_needs_sources"
                           for e in json.loads(body["messages"][-1]["content"])["errors"])
            if self.mode == "scope_recovery" and self.final_calls == 1:
                answer["analysis"]["domains"][0]["finding_ids"] = ["F99"]
                answer["impact"].update(alert_ids=list(answer["conclusion"]["alert_ids"]),
                                        support_ids=answer["conclusion"]["support_ids"][:1])
            if self.mode == "scope_recovery" and self.final_calls == 2:
                feedback = json.loads(body["messages"][-1]["content"])
                assert any(e.get("code") == "unknown_local_finding" for e in feedback["errors"])
                assert any(e["path"] == ["impact", "support_ids"] and e["uncovered_members"] for e in feedback["errors"])
                assert feedback["local_findings"] == []
            if self.mode in {"role_recovery", "role_partial"}:
                role_finding(answer, request, "C6")
                if self.final_calls == 2:
                    feedback = json.loads(body["messages"][-1]["content"])
                    assert any(e.get("code") == "non_observation_promoted_to_observed" for e in feedback["errors"])
        Draft202012Validator(body["response_format"]["json_schema"]["schema"]).validate(answer)
        if stage == "C6" and (self.mode == "role_partial" or self.mode == "role_recovery" and self.final_calls == 1):
            role_finding(answer, request, "C6", invalid=True)
        if stage == "C6" and self.mode == "partial":
            answer["analysis"]["members"][0]["evidence_ids"] = ["invalid-source"]
        if stage == "C6" and self.mode == "recommendation_correction" and self.final_calls == 1:
            # A provider can ignore the generation constraint; preserve and reject its raw reply.
            answer["recommendations"][0]["source_ids"] = []
        reply = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}],
                 "usage": {"prompt_tokens": 200, "completion_tokens": 200, "total_tokens": 400}}
        self.requests.append(copy.deepcopy(request))
        self.responses.append(copy.deepcopy(reply))
        return reply


async def scenario(service, sample, initial, mode):
    cid, rid = sample["case_id"], sample["run_id"]
    gateway, lake = Gateway(service, cid, rid, mode), SyntheticLake()
    routes = await dispatch_followups(service, T, cid, rid,
        (initial.get("analysis") or {}).get("followups", []), (initial.get("basis") or {}).get("binding_map", {}),
        gateway=gateway, lake=lake)
    graph = await service.build_graph(T, cid, rid)
    executor = BaselineExecutor(service, T, gateway=SimpleNamespace(), lake=SimpleNamespace())
    async with service.transaction(T) as store:
        run = (await store.db.execute(select(R).where(*store.where(R, R.c.case_id == cid, R.c.id == rid)))).mappings().one()
        from app.models.socai2 import RunSteps
        steps = RunSteps.__table__
        c3 = (await store.db.execute(select(steps).where(*store.where(steps, steps.c.run_id == rid,
            steps.c.stage_code == "C3", steps.c.kind == "stage")))).mappings().one()
        await executor.record(store, run, "C4.routing", {"schema_version": SCHEMA, "type": "followup_dispatch",
            "run_id": str(rid), "initial_analysis_artifact_id": str(c3["output_artifact_id"]),
            "initial_state": initial["state"], "routes": routes, "graph_artifact_id": graph["graph_artifact_id"],
            "limitations": ["Synthetic integration only."]}, [reference("artifact", c3["output_artifact_id"], "execution_receipt")])
    out = await service.finalize(T, cid, rid, gateway=gateway)
    assert out["state"] == "completed", out
    assert gateway.final_calls == (2 if mode in {"correction", "partial", "scope_recovery", "role_recovery", "role_partial", "recommendation_correction"} else 1), out
    assert gateway.deep_calls == (0 if mode == "fallback" else 2), out
    assert lake.calls == (0 if mode == "fallback" else 1), out
    assert out == await service.finalize(T, cid, rid, gateway=gateway)
    async with service.transaction(T, readonly=True) as store:
        report = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
            F.c.id == UUID(out["report_artifact_id"]))))).scalar_one()
        run = (await store.db.execute(select(R).where(*store.where(R, R.c.case_id == cid, R.c.id == rid)))).mappings().one()
        result_table = Results.__table__
        result = (await store.db.execute(select(result_table).where(*store.where(result_table,
            result_table.c.source_run_id == rid)))).mappings().one()
        if mode in {"partial", "role_partial"}:
            assert run["state"] == "completed" and run["stop_reason"] == "partial_analysis_saved_conclusion_rejected"
            assert result["validation_state"] == "rejected" and result["delivery_state"] == "partial"
        else:
            assert run["state"] == "completed", (out, report)
            assert report["recommendations"][0]["id"] == result["recommendations"][0]["id"] == "R1"
        requests = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
            F.c.run_id == rid, F.c.kind == "model_request")))).scalars().all()
        assert all(any(req["payload"]["body"] == sent["body"] for req in requests) for sent in gateway.requests)
        if mode in {"role_recovery", "role_partial"}:
            assert len(requests) == 6
            responses = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.run_id == rid, F.c.kind == "model_response")))).scalars().all()
            assert len(responses) == 6
            assert all(any(r["payload"]["raw"] == original for r in responses) for original in gateway.responses)
            role_errors = [r for r in responses if r["payload"].get("validation_error") == "non_observation_promoted_to_observed"]
            assert len(role_errors) == (4 if mode == "role_partial" else 2)
            if mode == "role_recovery":
                assert result["validation_state"] == "accepted"
        if mode == "recommendation_correction":
            responses = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.run_id == rid, F.c.kind == "model_response")))).scalars().all()
            rejected = [r for r in responses if r["payload"].get("validation_error") == "recommendation_needs_sources"]
            assert len(rejected) == 1
            assert rejected[0]["payload"]["raw"] == gateway.responses[-2]
            assert result["validation_state"] == "accepted" and result["delivery_state"] == "complete"
    if mode in {"valid", "recommendation_correction"}:
        from app.api.v1.endpoints import socai2_cases as api
        from app.socai2.case_service import CaseService
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        app = FastAPI()
        app.include_router(api.router)
        app.dependency_overrides[api.get_service] = lambda: CaseService(service.sessions)
        app.dependency_overrides[api.ReadUser.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=T)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            response = await client.get(f"/socai2/cases/{cid}/results/{result['id']}")
            assert response.status_code == 200
            saved = response.json()["result"]
            assert all(saved[key] == result[key] for key in ("conclusion","validation_state","delivery_state","recommendations"))
            response = await client.get(f"/socai2/cases/{cid}")
            assert response.status_code == 200
            current = response.json()["current_assessment"]
            assert current["value"]["conclusion"] == result["conclusion"]
            assert current["value"]["validity"] == "accepted" and current["covers_current_members"]
    return {**sample, "real_model_calls": 0, "substitute_deep_calls": gateway.deep_calls,
            "substitute_final_calls": gateway.final_calls, "substitute_lake_calls": lake.calls,
            "run_state": run["state"], "c6_idempotent_replay": True,
            "final_result_and_current_assessment_gets": mode in {"valid", "recommendation_correction"},
            "final_recommendation_correction_and_gets": mode == "recommendation_correction"}
