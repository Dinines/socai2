"""Configured C1/C3 in isolated PostgreSQL; all models and tools are substitutes."""
import asyncio
import copy
import json
import traceback
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import (
    baseline_enrichment_sources,
    case_model_boundary,
    runtime_policy,
)
from app.socai2.baseline_contracts import (
    FULL_EXECUTOR_VERSION,
    Actor,
    Publication,
    Start,
)
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import A, C, F
from app.socai2.stage_results import StageResultService
from jsonschema import Draft202012Validator
from socai2_test_model_view import synthetic_measure
from sqlalchemy import insert, null, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_socai2_ai_boundary_pg import Gateway as AlertGateway
from test_socai2_case_model_boundary import answer_for
from test_socai2_incident_boundary_pg import Gateway as IncidentGateway

T, USER = UUID(int=1), UUID(int=3)
ACTOR = Actor(user_id=USER, name="Synthetic C1/C3 boundary reviewer")


async def empty_query(service, tenant, name, args):
    async with service.transaction(tenant, readonly=True) as store:
        return [], await store.now()


class Gateway:
    provider, model = "synthetic", "synthetic-case-boundary-no-network"

    def __init__(self, service, cid, rid, mode):
        self.service, self.cid, self.rid, self.mode = service, cid, rid, mode
        self.calls, self.requests, self.responses = 0, [], []

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
            frozen = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.run_id == self.rid, F.c.schema_version == case_model_boundary.SCHEMA)))).scalar_one()
            context = await store.read_context(self.cid, self.rid)
        assert request["body"] == body and request["case_boundary"] == frozen["case_boundary"]
        answer = answer_for(frozen, context)
        if self.mode == "followup":
            answer["followups"] = [{"question_id": context.questions[0].id,
                "alert_ids": [m["alert_id"] for m in answer["members"]], "mode": "deep", "objective": "Synthetic one-question check.",
                "required_evidence": "Synthetic query evidence.", "source_ids": [m["evidence_ids"][0] for m in answer["members"]],
                "object_keys": [], "binding_id": None, "priority": "decision_critical"}]
        if self.mode == "correction" and self.calls == 1:
            answer["members"][0].update(state="analyzed", evidence_ids=[])
        if self.mode == "correction" and self.calls == 2:
            previous = json.loads(body["messages"][-2]["content"])
            feedback = json.loads(body["messages"][-1]["content"])
            assert previous["members"][0]["alert_id"] == "A1"
            assert feedback["errors"][0]["subject_id"] == "A1"
            assert all(a.startswith("A") for s in feedback["allowed_sources"] for a in s["alert_ids"])
        Draft202012Validator(body["response_format"]["json_schema"]["schema"]).validate(answer)
        if self.mode == "partial":
            answer["members"][0]["evidence_ids"] = ["invalid-source"]
        reply = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}],
                 "usage": {"prompt_tokens": 200, "completion_tokens": 200, "total_tokens": 400}}
        if self.mode == "rejected":
            reply["choices"][0]["message"]["content"] = "{"
        self.requests.append(copy.deepcopy(body))
        self.responses.append(copy.deepcopy(reply))
        return reply


async def run_checks(engine, record, only=None):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service, stages = BaselineService(sessions), StageResultService(sessions)

    async def fixture(full=False):
        cid, iid, aids, aruns = uuid4(), uuid4(), [uuid4(), uuid4()], []
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="Synthetic C1/C3 test", created_by=USER))
            await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=T,
                source_namespace="synthetic.case-boundary", source_incident_id=str(iid), title="Synthetic event"))
            for aid in aids:
                mid, host = uuid4(), "synthetic-" + str(aid)
                await store.db.execute(insert(A).values(id=aid, tenant_id=T, source_namespace="synthetic.case-boundary",
                    source_identity_key=str(aid), title="Synthetic alert", description="Original collected description.",
                    event_time=now, event_time_source="source"))
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=T, alert_id=aid, revision=1,
                    raw_text="Synthetic original statement.", raw_json={"host": host, "process": {"pid": 42},
                    "custom": {"id": "business-id", "authorized": False, "size": 0}},
                    detection={}, source_scope={}, retention={}, material_state="complete"))
                await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
                await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=T, alert_id=aid, material_id=mid,
                    object_type="host", object_role="entity", object_key="host:" + host, namespace="synthetic.case-boundary",
                    raw_value=host, normalized_value=host, source_path="$.raw_json.host", attributes={}))
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=T, incident_id=iid,
                    alert_id=aid, membership_source="fusion", basis_version="synthetic",
                    correlation_basis={"reason": "explicit synthetic membership"}, source_operation_id=uuid4()))
        for aid in aids:
            result = await stages.execute_alert(T, aid, uuid4(), gateway=AlertGateway(stages, aid), query=empty_query)
            assert result["state"] == "completed", result
            aruns.append(result["run_id"])
        result = await stages.execute_incident(T, iid, uuid4(), gateway=IncidentGateway(stages, iid))
        assert result["state"] == "completed", result
        async with service.transaction(T) as store:
            pending = await store.replace_members(cid, set(aids), expected_revision=0, actor=ACTOR, operation_id=uuid4())
            limits = runtime_policy.active_policy().case.limits(await store.now(), "synthetic.case-boundary.v1")
        rid = UUID(pending["pending_run_id"])
        async def idle(claim):
            from app.socai2.baseline_capacity import final_reservation
            from app.socai2.baseline_executor import BaselineExecutor
            executor = BaselineExecutor(service, T, gateway=SimpleNamespace(), lake=SimpleNamespace())
            async with service.transaction(T) as store:
                run = await store.run(cid, rid)
                context = await store.read_context(cid, rid)
                await executor.record(store, run, "C1.executor", {"schema_version": FULL_EXECUTOR_VERSION,
                    "type": "execution_plan", "run_id": str(rid), "limits": run["limits"],
                    "limitations": ["Synthetic C1/C3 test; no Deep or C6 model dispatch."],
                    "final_reservation": final_reservation(None, context, limits)}, [])
        await service.start(T, cid, rid, Start(expected_scope_revision=1, operation_key=uuid4(),
            window_start=now - timedelta(minutes=5) if full else None,
            window_end=now + timedelta(minutes=5) if full else None), actor=ACTOR,
            executor=idle, executor_version=FULL_EXECUTOR_VERSION, limits=limits)
        sample = {"case_id": cid, "incident_id": iid, "run_id": rid, "alert_ids": aids,
                  "stage_run_ids": [*aruns, result["run_id"]]}
        record("fixture_registered", True, sample)
        with patch.object(baseline_enrichment_sources, "query", empty_query):
            await service.enrich(T, cid, rid)
        await service.prepare_evidence(T, cid, rid)
        return sample

    async def close(sample, store=None):
        cid, rid = sample["case_id"], sample["run_id"]
        context = await store.read_context(cid, rid) if store else await service.read_context(T, cid, rid)
        publication = Publication.model_validate({"operation_key": uuid4(), "terminal_state": "failed",
            "stop_reason": "synthetic_c3_only_test_ended", "title": "Synthetic C3 module test", "conclusion": None,
            "conclusion_state": "unavailable", "conclusion_origin": "system", "validation_state": "system_only",
            "closing_note": "Synthetic C1/C3 check; C4-C6 not executed.", "findings": [], "questions": [],
            "recommendations": [], "change_kind": "initial", "change_summary": None,
            "case_impact": {"summary": None, "supported_changes": [], "cannot_generalize": [],
                "affected_scope": context.scope.model_dump(mode="json"), "next_steps": []}, "delivery_state": "partial",
            "members": [{"alert_id": aid, "read_state": "read", "assessment_state": "unresolved",
                "conclusion_covered": False, "assessment": None, "limitations": "Synthetic C3 only.", "evidence_refs": []}
                for aid in context.alerts]})
        return await store.publish(cid, rid, publication) if store else await service.publish(T, cid, rid, publication)

    async def execute(mode):
        sample = await fixture()
        cid, rid = sample["case_id"], sample["run_id"]
        context = await service.read_context(T, cid, rid)
        assert context.case_input_profile == runtime_policy.active_policy().case_io.identity
        assert all(a.triage_usable and len(a.queries) == 3 for a in context.alerts.values())
        assert all(i.diagnosis_usable for i in context.incidents.values())
        gateway = Gateway(service, cid, rid, mode)
        result = await service.analyze(T, cid, rid, gateway=gateway, lake=SimpleNamespace(configured=lambda: False))
        assert result["analysis"], result
        assert {m["alert_id"] for m in result["analysis"]["members"]} == set(map(str, sample["alert_ids"]))
        async with service.transaction(T, readonly=True) as store:
            fresh = await store.input_freshness(rid)
            assert fresh["state"] == "current", fresh
            arts = (await store.db.execute(select(F).where(*store.where(F, F.c.run_id == rid)))).mappings().all()
            responses = [a for a in arts if a["kind"] == "model_response"]
            assert len(responses) == gateway.calls
            assert all(a["content_json"]["payload"]["raw"] in gateway.responses for a in responses)
        if mode == "correction":
            assert gateway.calls == 2 and result["basis"]["correction_result"]["dispatched"]
        elif mode == "partial":
            assert gateway.calls == 1 and result["analysis"]["members"][0]["state"] == "not_analyzed"
            assert result["analysis"]["members"][1]["state"] == "unresolved"
            assert result["basis"]["validation_review"]["state"] == "partial"
        else:
            assert gateway.calls == 1 and result["state"] == "completed"
            async with service.transaction(T) as store:
                legacy = await store.prepare_model_view(cid, rid)
                current = await store.prepare_model_view(cid, rid, case_boundary=True)
                assert legacy["artifact_id"] != current["artifact_id"]
                assert legacy["schema_version"].startswith("socai2.baseline-model-view.")
                json.loads(legacy["messages"][1]["content"])
                assert "本轮Case的背景查询" in current["messages"][1]["content"]
                assert "business-id" in current["messages"][1]["content"]
                expected_findings = sum(len(i.diagnosis["diagnosis"]["findings"]) for i in context.incidents.values()
                                        if i.diagnosis_usable)
                assert current["input_ledger"]["record_counts"]["finding"] == expected_findings
        await close(sample)
        return {**sample, "c3_substitute_calls": gateway.calls, "real_model_calls": 0,
                "scope": "C1/C2/C3 only; explicit failed Run close, not full Case success"}

    async def test_case_boundary_save_restore_and_legacy_view():
        return await execute("valid")

    async def test_case_boundary_empty_reference_correction():
        return await execute("correction")

    async def test_case_boundary_partial_bad_reference():
        return await execute("partial")

    async def test_case_boundary_freshness_includes_actual_query_steps():
        sample = await fixture()
        cid, rid = sample["case_id"], sample["run_id"]
        context = await service.read_context(T, cid, rid)
        query = next(iter(context.alerts.values())).queries[0]
        async with service.transaction(T) as store:
            assert (await store.input_freshness(rid))["state"] == "current"
            nested = await store.db.begin_nested()
            # Fault injection inside a savepoint: append a late receipt, never
            # modify immutable terminal steps or original tool artifacts.
            steps = m.RunSteps.__table__
            original_step = dict((await store.db.execute(select(steps).where(
                steps.c.tenant_id == T, steps.c.id == UUID(query["step_id"])))).mappings().one())
            original_artifact = dict((await store.db.execute(select(F).where(
                F.c.tenant_id == T, F.c.id == UUID(query["id"])))).mappings().one())
            step_id, artifact_id = uuid4(), uuid4()
            original_step.update(id=step_id, seq=1000, output_artifact_id=artifact_id, name="synthetic_late_receipt",
                                 usage=null(), error=null())
            await store.db.execute(insert(steps).values(**original_step))
            original_artifact.update(id=artifact_id, step_id=step_id)
            await store.db.execute(insert(F).values(**original_artifact))
            base = (await store.db.execute(text("SELECT socai2.baseline_input_freshness(:t,:r)"), {"t": T, "r": rid})).scalar_one()
            assert base["state"] == "current"
            changed = await store.input_freshness(rid)
            assert changed["state"] == "stale" and "paired_alert_queries_changed" in changed["reasons"]
            # The immutable C1 copy and query artifact stay exact.
            assert (await store.read_context(cid, rid)).model_dump() == context.model_dump()
            out = await close(sample, store=store)
            assert out["adoption"]["state"] == "stale_input"
            await nested.rollback()
            assert (await store.input_freshness(rid))["state"] == "current"
        await close(sample)
        return {**sample, "base_v1_current_but_extension_stale": True,
                "stale_adoption_blocked": True, "mutation_rolled_back": True, "real_model_calls": 0}

    async def followup_scenario(mode):
        from test_socai2_case_followup_pg import scenario
        sample = await fixture(full=True)
        cid, rid = sample["case_id"], sample["run_id"]
        gateway = Gateway(service, cid, rid, "rejected" if mode == "fallback" else "followup")
        initial = await service.analyze(T, cid, rid, gateway=gateway, lake=SimpleNamespace(configured=lambda: True))
        assert bool(initial.get("analysis")) == (mode != "fallback"), initial
        return await scenario(service, sample, initial, mode)

    async def test_case_boundary_followups_final_storage():
        return await followup_scenario("valid")

    async def test_case_boundary_followups_final_partial():
        return await followup_scenario("partial")

    async def test_case_boundary_followups_final_correction():
        return await followup_scenario("correction")

    async def test_case_boundary_followups_without_c3():
        return await followup_scenario("fallback")

    for name, check in list(locals().items()):
        if name.startswith("test_case_boundary_") and (not only or name in only):
            try:
                record(name, True, await asyncio.wait_for(check(), 120))
            except Exception:  # noqa: BLE001 -- retain each failure without repeating it
                record(name, False, traceback.format_exc())
