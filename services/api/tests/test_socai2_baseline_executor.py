"""Full manual pipeline in the existing synthetic PG; model/lake substitutes."""
import asyncio
import importlib.util
import json
import traceback
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_executor import BaselineExecutor
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import A, C, F, R, StoreError, encoded
from socai2_test_model_view import model_data, model_messages_data
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker


def helper(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


delivery = helper("test_socai2_baseline_delivery")
c3, deep, lake = delivery.c3, delivery.deep, delivery.lake
T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic full executor reviewer")
S, RESULT = m.RunSteps.__table__, m.Results.__table__


class PipelineGateway:
    provider, model = "synthetic", "synthetic-full-baseline-no-network"

    def __init__(self, modes=("human",), *, hook=None, enabled=True, initial_mutate=None):
        self.modes, self.enabled = modes, enabled
        def change(payload):
            value = json.loads(payload["choices"][0]["message"]["content"])
            original = value["followups"][0]
            value["followups"] = [{**original, "mode": mode,
                "question_id": value["questions"][qid]["id"] if isinstance(qid, int) else qid}
                for mode, qid in [v if isinstance(v, tuple) else (v, 0) for v in modes]]
            data = model_messages_data(self.initial.last_body["messages"])
            if "tool_options" in data:
                for item in value["followups"]:
                    item.update(priority="decision_critical", binding_id=None)
                    if item["mode"] == "query":
                        option = next((o for o in data["tool_options"] if o["tool_name"] == "process_activity"), data["tool_options"][0])
                        item.update(binding_id=option["binding_id"], alert_ids=option["alert_ids"], object_keys=[])
            payload["choices"][0]["message"]["content"] = json.dumps(value)
            if initial_mutate:
                initial_mutate(payload)
        self.initial = c3.SyntheticGateway(mutate=change, hook=hook)
        self.middle = deep.DecisionGateway(two_queries=True)
        self.final = delivery.FinalGateway()
        self.order = []

    async def configure(self, service, tenant):
        assert tenant == T
        return self.enabled

    async def complete(self, body, timeout):
        data = model_messages_data(body["messages"])
        phase = "C6" if data.get("round") == "final_delivery" else "Deep" if "question" in data else "C3"
        self.order.append(phase)
        return await {"C3": self.initial, "Deep": self.middle, "C6": self.final}[phase].complete(body, timeout)


async def run_checks(engine, record, only=None):
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))

    async def rows(query):
        async with service.transaction(T) as store:
            return (await store.db.execute(query)).mappings().all()

    async def new_alert(store, host):
        aid, mid = uuid4(), uuid4()
        await store.db.execute(insert(A).values(id=aid, tenant_id=T, title="synthetic executor alert",
            source_namespace="executor-fixture", source_identity_key=str(aid)))
        await store.db.execute(insert(m.AlertMaterials.__table__).values(id=mid, tenant_id=T, alert_id=aid,
            revision=1, ocsf_json=lake.original(host), detection={}, source_scope={}, material_state="complete", retention={}))
        await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        await store.db.execute(insert(m.AlertObjects.__table__).values(id=uuid4(), tenant_id=T, alert_id=aid,
            material_id=mid, object_type="host", object_role="entity", object_key="host:" + host, namespace="fixture",
            raw_value=host, normalized_value=host, source_path="$.ocsf_json.device.name", attributes={}))
        return aid

    async def fixture():
        cid, host = uuid4(), "synthetic-" + uuid4().hex
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="synthetic full Case", created_by=USER))
            aid = await new_alert(store, host)
            out = await store.replace_members(cid, {aid}, expected_revision=0, actor=ACTOR, operation_id=uuid4())
        request = Start(expected_scope_revision=1, operation_key=uuid4(), window_start=now - timedelta(minutes=5),
            window_end=now + timedelta(minutes=5))
        limits = Limits(max_model_calls=4, max_tool_calls=4, max_tokens=48000, max_rows_per_query=5,
            deadline_at=now + timedelta(seconds=120), policy_version="synthetic-full")
        return cid, UUID(out["pending_run_id"]), aid, host, request, limits

    async def execute(f, gateway, source=None, *, connected=frozenset()):
        cid, rid, _, _, request, limits = f
        with patch("app.socai2.baseline_enrichment.sources.CONNECTED", connected):
            return await service.start_full(T, cid, rid, request, actor=ACTOR, limits=limits,
                gateway=gateway, lake=source or deep.AdaptiveLake())

    async def report(rid):
        artifacts = await rows(select(F).where(F.c.run_id == rid, F.c.kind == "source_snapshot"))
        return next(r["content_json"] for r in artifacts if r["content_json"].get("type") == "delivery_report")

    async def system_closing(f):
        saved = await report(f[1])
        assert saved["result"]["conclusion"].startswith("案件性质待核实。")
        assert saved["result"]["stop_reason"] not in saved["result"]["conclusion"]
        assert "原因：" not in saved["result"]["conclusion"]
        assert saved["result"]["conclusion_state"] == "uncertain"
        assert saved["result"]["conclusion_origin"] == "system"
        assert saved["result"]["validation_state"] == "system_only"
        assert not any(m["conclusion_covered"] for m in saved["result"]["members"])
        case = (await rows(select(C).where(C.c.id == f[0])))[0]
        table = m.CaseAssessments.__table__
        assessment = (await rows(select(table).where(table.c.id == case["current_assessment_id"])))[0]
        assert assessment["conclusion"] == saved["result"]["conclusion"]
        assert assessment["origin"] == "system" and assessment["validity"] == "system_only"
        coverage = m.CaseAssessmentMembers.__table__
        assert not await rows(select(coverage).where(coverage.c.assessment_id == assessment["id"]))
        stage = (await rows(select(S).where(S.c.run_id == f[1], S.c.kind == "stage", S.c.stage_code == "C6")))[0]
        assert stage["state"] == "completed" and stage["ended_at"] and stage["output_artifact_id"]
        from app.socai2.case_reader import CaseReader
        async with service.transaction(T) as store:
            current = (await CaseReader(store).case(f[0]))["current_assessment"]
        assert current["input_freshness"]["state"] == "current", current["input_freshness"]
        assert current["covers_current_members"] is False
        return saved

    async def reject(code, call):
        try:
            await call
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected " + code)

    async def test_full_human_graph_and_no_need_skip_external_queries():
        for modes in ((), ("human", "graph")):
            f, gateway, source = await fixture(), PipelineGateway(modes), deep.AdaptiveLake()
            claim = await execute(f, gateway, source)
            assert claim.newly_claimed and gateway.order == ["C3", "C6"], gateway.order
            saved = await report(f[1])
            assert saved["execution"]["model_calls"] == 2 and saved["execution"]["tool_calls"] == 0
            assert saved["result"]["validation_state"] == "accepted" and saved["result"]["delivery_state"] == "partial"
            routes = saved["execution"]["followup_dispatch"]["routes"]
            assert [r["state"] for r in routes] == ([] if not modes else ["handoff", "completed"])
            assert not await rows(select(m.Tasks.__table__).where(m.Tasks.__table__.c.case_id == f[0]))
            replay = await execute(f, gateway, source)
            assert not replay.newly_claimed and gateway.order == ["C3", "C6"]
            assert len(await rows(select(RESULT).where(RESULT.c.source_run_id == f[1]))) == 1
            if modes:
                items = model_data(gateway.final.last_body["messages"][1]["content"])["items"]
                assert any(isinstance(i["value"], dict) and i["value"].get("followup", {}).get("mode") == "human" for i in items)
                assert all("source_ids" not in i["value"]["followup"] for i in items
                    if isinstance(i["value"], dict) and "followup" in i["value"])

    async def test_full_adaptive_queries_reserve_fourth_call_and_deduplicate_questions():
        f, gateway = await fixture(), PipelineGateway(("query", "deep", ("deep", 1), "human"))
        await execute(f, gateway)
        saved = await report(f[1])
        assert gateway.order == ["C3", "Deep", "Deep", "C6"], (gateway.order, saved)
        assert saved["execution"]["tool_calls"] == 2 and saved["execution"]["total_tokens"] == 4000
        routes = saved["execution"]["followup_dispatch"]["routes"]
        assert routes[0]["mode"] == "query" and routes[0]["state"] == "completed"
        assert "deep_artifact_id" not in routes[0] and routes[0]["query_artifact_id"]
        assert routes[1]["answer_available"] and routes[2]["state"] == "skipped"
        assert routes[2]["reason"] == "final_model_call_reserved", routes
        prompt = model_data(gateway.final.last_body["messages"][1]["content"])
        assert {q["tool_name"] for q in prompt["queries"]} == {"process_activity", "network_connections"}
        assert any(q["observed_rows_in_bounded_fetch"] == 0 for q in prompt["queries"])
        assert any(q["observed_rows_in_bounded_fetch"] == 1 for q in prompt["queries"])
        assert saved["result"]["validation_state"] == "accepted", saved["result"]
        return {"run_id": str(f[1]), "model_order": gateway.order, "tool_calls": 2}

    async def test_full_two_call_policy_saves_final_slot_without_deep_dispatch():
        f, gateway = list(await fixture()), PipelineGateway(("query",))
        f[-1] = f[-1].model_copy(update={"max_model_calls": 2})
        await execute(f, gateway)
        saved = await report(f[1])
        assert gateway.order == ["C3", "C6"]
        assert saved["execution"]["followup_dispatch"]["routes"][0]["state"] == "completed"
        assert saved["execution"]["tool_calls"] == 1

    async def test_full_deep_receipt_reused_by_supporting_direct_query():
        def priorities(payload):
            value = json.loads(payload["choices"][0]["message"]["content"])
            value["followups"][1]["priority"] = "supporting"
            payload["choices"][0]["message"]["content"] = json.dumps(value)
        f, source = await fixture(), deep.AdaptiveLake()
        gateway = PipelineGateway(("deep", "query"), initial_mutate=priorities)
        await execute(f, gateway, source)
        saved = await report(f[1])
        assert gateway.order == ["C3", "Deep", "Deep", "C6"], gateway.order
        assert source.calls == saved["execution"]["tool_calls"] == 2
        assert saved["result"]["validation_state"] == "accepted", saved["result"]
        routes = saved["execution"]["followup_dispatch"]["routes"]
        query = next(r for r in routes if r["followup_index"] == 1)
        assert query["mode"] == "query" and query["reused"] is True
        query_steps = await rows(select(S).where(S.c.run_id == f[1], S.c.stage_code == "C4.query",
            S.c.name == query["resolved_binding_id"]))
        assert len(query_steps) == 1 and query_steps[0]["parent_step_id"] is not None
        data = model_data(gateway.final.last_body["messages"][1]["content"])
        final_route = next(r for r in data["followup_execution"]["routes"] if r["followup_index"] == 1)
        assert final_route["reused"] is True and final_route["projection_id"] == query["projection_id"]
        assert any(q["artifact_id"] == final_route["projection_id"] and q["tool_name"] == "process_activity"
            for q in data["queries"])
        return {"run_id": str(f[1]), "model_order": gateway.order, "tool_calls": 2,
            "reused_prior_Deep_receipt": True, "final_projection_link_preserved": True}

    async def test_full_distinct_direct_queries_keep_final_plan_receipt_links():
        def choose_second_binding(payload):
            value = json.loads(payload["choices"][0]["message"]["content"])
            data = model_messages_data(gateway.initial.last_body["messages"])
            chosen = next(o for o in data["tool_options"] if o["tool_name"] == "network_connections")
            value["followups"][1].update(binding_id=chosen["binding_id"], alert_ids=chosen["alert_ids"])
            payload["choices"][0]["message"]["content"] = json.dumps(value)
        f, source = await fixture(), deep.AdaptiveLake()
        gateway = PipelineGateway(("query", "query"), initial_mutate=choose_second_binding)
        await execute(f, gateway, source)
        saved = await report(f[1])
        assert gateway.order == ["C3", "C6"] and source.calls == saved["execution"]["tool_calls"] == 2
        assert saved["result"]["validation_state"] == "accepted", saved["result"]
        routes = saved["execution"]["followup_dispatch"]["routes"]
        assert len({r["question_id"] for r in routes}) == 1
        assert len({r["projection_id"] for r in routes}) == 2 and not any(r["reused"] for r in routes)
        data = model_data(gateway.final.last_body["messages"][1]["content"])
        queries = {q["artifact_id"]: q for q in data["queries"]}
        linked = {r["followup_index"]: queries[r["projection_id"]]["tool_name"]
            for r in data["followup_execution"]["routes"]}
        assert linked == {0: "process_activity", 1: "network_connections"}
        assert len(gateway.final.last_body["messages"][1]["content"].encode()) <= 8192
        assert len(encoded(gateway.final.last_body["messages"])) <= 12288
        requests = await rows(select(F).where(F.c.run_id == f[1], F.c.kind == "model_request"))
        assert any(r["content_json"]["payload"]["body"] == gateway.final.last_body for r in requests)
        return {"run_id": str(f[1]), "model_order": gateway.order, "tool_calls": 2,
            "plan_to_query_links": linked, "final_request_bytes": len(encoded(gateway.final.last_body))}

    async def test_full_claim_committed_replay_and_scope_changes_wait_for_manual_start():
        f = await fixture()
        entered, release = asyncio.Event(), asyncio.Event()
        async def pause():
            run = (await rows(select(R).where(R.c.id == f[1])))[0]
            assert run["state"] == "running" and run["input_artifact_id"] is not None
            entered.set()
            await release.wait()
        gateway = PipelineGateway(hook=pause)
        task = asyncio.create_task(execute(f, gateway))
        try:
            await asyncio.wait_for(entered.wait(), 25)
            replay = await execute(f, gateway)
            assert not replay.newly_claimed and gateway.order == ["C3"]
            await reject("full_executor_already_claimed", BaselineExecutor(service, T)(replay))
            async with service.transaction(T) as store:
                second, third = await new_alert(store, f[3]), await new_alert(store, f[3])
            added = await service.replace_members(T, f[0], {f[2], second}, expected_revision=1, actor=ACTOR, operation_id=uuid4())
            added2 = await service.replace_members(T, f[0], {f[2], second, third}, expected_revision=2, actor=ACTOR, operation_id=uuid4())
            assert added["pending_run_id"] == added2["pending_run_id"]
            pending = UUID(added2["pending_run_id"])
            next_request = Start(expected_scope_revision=3, operation_key=uuid4(), window_start=f[4].window_start, window_end=f[4].window_end)
            await reject("baseline_already_active", service.start_full(T, f[0], pending, next_request,
                actor=ACTOR, limits=f[5], gateway=gateway))
        finally:
            release.set()
            await task
        saved = await report(f[1])
        assert saved["scope"]["alert_ids"] == [str(f[2])]
        assert (await rows(select(C).where(C.c.id == f[0])))[0]["current_assessment_id"] is None
        run = (await rows(select(R).where(R.c.id == pending)))[0]
        assert run["state"] == "pending_update" and not await rows(select(S).where(S.c.run_id == pending))
        assert gateway.order == ["C3", "C6"]
        # The successor only starts after this explicit user-equivalent call.
        new_gateway = PipelineGateway(enabled=False)
        async with service.transaction(T) as store:
            fresh = f[5].model_copy(update={"deadline_at": await store.now() + timedelta(seconds=120)})
        new_f = (f[0], pending, second, f[3], next_request, fresh)
        await execute(new_f, new_gateway)
        assert set((await report(pending))["scope"]["alert_ids"]) == {str(f[2]), str(second), str(third)}

    async def test_full_cancel_holds_slot_and_does_not_finalize():
        f = await fixture()
        async def cancelled():
            raise asyncio.CancelledError()
        gateway = PipelineGateway(hook=cancelled)
        try:
            await execute(f, gateway)
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("expected cancellation")
        assert (await rows(select(R).where(R.c.id == f[1])))[0]["state"] == "unknown"
        assert gateway.order == ["C3"]
        saved = await system_closing(f)
        assert saved["execution"]["run_state"] == "unknown"
        assert not await rows(select(RESULT).where(RESULT.c.source_run_id == f[1]))
        replay = await execute(f, gateway)
        assert not replay.newly_claimed and replay.state == "unknown" and gateway.order == ["C3"]

    async def test_full_no_model_or_rejected_initial_yields_system_handoff():
        for gateway in (PipelineGateway(enabled=False), PipelineGateway(initial_mutate=lambda p: p.pop("usage")),
                PipelineGateway(initial_mutate=lambda p: p["choices"][0].update(finish_reason="length"))):
            f = await fixture()
            await execute(f, gateway)
            saved = await report(f[1])
            assert not saved["execution"]["followup_dispatch"]["routes"]
            if gateway.initial.calls and gateway.initial.last_payload["choices"][0]["finish_reason"] == "length":
                assert gateway.order == ["C3", "C6"]
                assert saved["result"]["validation_state"] == "accepted"
            else:
                assert gateway.order in ([], ["C3"])
                await system_closing(f)
            if gateway.initial.calls and "usage" not in gateway.initial.last_payload:
                assert saved["execution"]["total_tokens"] is None

    async def test_full_limits_are_not_raised_and_exhaustion_still_delivers_receipt():
        f = await fixture()
        for field, value in (("max_model_calls", 5), ("max_tool_calls", 5), ("max_tokens", 48001),
                ("max_rows_per_query", 201), ("deadline_at", f[5].deadline_at + timedelta(days=1))):
            bad = list(f)
            bad[-1] = f[-1].model_copy(update={field: value})
            await reject("full_executor_limits_outside_policy", execute(bad, PipelineGateway()))
        assert (await rows(select(R).where(R.c.id == f[1])))[0]["state"] == "pending_update"
        assert not await rows(select(S).where(S.c.run_id == f[1]))
        for changes in ({"max_model_calls": 1}, {"max_tokens": 0}, {"deadline_at": f[5].deadline_at - timedelta(days=1)}):
            limited = list(await fixture())
            limited[-1] = limited[-1].model_copy(update=changes)
            gateway = PipelineGateway()
            await execute(limited, gateway)
            if changes == {"max_model_calls": 1}:
                assert gateway.order == ["C6"]
                assert (await report(limited[1]))["result"]["validation_state"] == "accepted"
            else:
                assert not gateway.order
                await system_closing(limited)

    async def test_full_rejected_final_is_retained_without_retry_or_adoption():
        f, gateway = await fixture(), PipelineGateway(("human",))
        gateway.final.mutate = lambda p: p["choices"][0]["message"].update(content="{bad-json")
        await execute(f, gateway)
        saved = await report(f[1])
        assert gateway.order == ["C3", "C6"] and saved["result"]["conclusion"]
        assert saved["result"]["validation_state"] == "system_only"
        await system_closing(f)
        originals = await rows(select(F).where(F.c.run_id == f[1], F.c.kind == "model_response"))
        assert any(r["content_json"]["payload"]["raw"]["choices"][0]["message"]["content"] == "{bad-json" for r in originals)

    async def test_rejected_c3_scope_still_calls_c6_and_saves_case_judgment():
        def wrong_scope(payload):
            data = json.loads(payload["choices"][0]["message"]["content"])
            data["followups"][0]["object_keys"] = ["ip:203.0.113.50"]
            payload["choices"][0]["message"]["content"] = json.dumps(data)
        f, gateway = await fixture(), PipelineGateway(initial_mutate=wrong_scope)
        await execute(f, gateway)
        assert gateway.order == ["C3", "C6"]
        steps = await rows(select(S).where(S.c.run_id == f[1], S.c.kind == "stage"))
        assert next(s for s in steps if s["stage_code"] == "C3")["state"] == "failed"
        final_input = model_messages_data(gateway.final.last_body["messages"])
        assert final_input["preliminary_analysis"]["state"] == "unavailable"
        saved = await report(f[1])
        assert saved["result"]["validation_state"] == "accepted"
        case = (await rows(select(C).where(C.c.id == f[0])))[0]
        table = m.CaseAssessments.__table__
        assessment = (await rows(select(table).where(table.c.id == case["current_assessment_id"])))[0]
        assert assessment["origin"] == "model" and assessment["validity"] == "accepted"
        assert assessment["conclusion"] == saved["result"]["conclusion"]
        return {"case_id": str(f[0]), "run_id": str(f[1]), "order": gateway.order}

    async def test_c6_null_extension_is_audited_without_rewriting_original():
        def extension(payload):
            data = json.loads(payload["choices"][0]["message"]["content"])
            data["analysis"]["conflicts_note"] = None
            payload["choices"][0]["message"]["content"] = json.dumps(data)
        f, gateway = await fixture(), PipelineGateway(())
        gateway.final.mutate = extension
        await execute(f, gateway)
        saved = await report(f[1])
        assert saved["result"]["validation_state"] == "accepted"
        originals = await rows(select(F).where(F.c.run_id == f[1], F.c.kind == "model_response"))
        adapted = next(a["content_json"]["payload"] for a in originals if a["content_json"]["payload"].get("output_adapter"))
        assert adapted["raw"] == gateway.final.last_payload
        assert adapted["output_adapter"]["removed"] == [{"path": ["analysis", "conflicts_note"], "value": None}]
        assert "conflicts_note" not in json.loads(adapted["output_adapter"]["normalized_content"])["analysis"]

    async def test_unavailable_model_view_closes_without_unknown_or_model_call():
        from app.socai2.baseline_store import BaselineStore
        original = BaselineStore.prepare_model_view
        async def unavailable(store, *args, **kwargs):
            view = await original(store, *args, **kwargs)
            return {**view, "ready": False, "reason": "model_view_not_ready"}
        f, gateway = await fixture(), PipelineGateway(())
        with patch.object(BaselineStore, "prepare_model_view", unavailable):
            await execute(f, gateway)
        saved = await system_closing(f)
        assert not gateway.order and saved["result"]["stop_reason"] == "model_view_not_ready"
        run = (await rows(select(R).where(R.c.id == f[1])))[0]
        assert run["state"] == "failed" and run["ended_at"]

    async def test_system_closing_preserves_existing_model_and_human_judgment():
        for origin in ("model", "human"):
            f, gateway = await fixture(), PipelineGateway(())
            await execute(f, gateway)
            async with service.transaction(T) as store:
                case = await store.case(f[0])
                prior = case["current_assessment_id"]
                assert prior
                table = m.CaseAssessments.__table__
                if origin == "human":
                    old = await store.one(select(table).where(table.c.id == prior))
                    prior = uuid4()
                    await store.db.execute(insert(table).values(**{**dict(old), "id": prior,
                        "revision": old["revision"] + 1, "origin": "human", "operation_key": str(uuid4())}))
                    await store.db.execute(update(C).where(C.c.id == f[0]).values(current_assessment_id=prior))
                aid = await new_alert(store, f[3])
                changed = await store.replace_members(f[0], {f[2], aid}, expected_revision=1,
                    actor=ACTOR, operation_id=uuid4())
                now = await store.now()
            request = f[4].model_copy(update={"expected_scope_revision": 2, "operation_key": uuid4()})
            limits = f[5].model_copy(update={"deadline_at": now + timedelta(seconds=120)})
            new = (f[0], UUID(changed["pending_run_id"]), aid, f[3], request, limits)
            await execute(new, PipelineGateway(enabled=False))
            saved = await report(new[1])
            assert saved["result"]["validation_state"] == "system_only" and saved["result"]["conclusion"]
            assert (await rows(select(C).where(C.c.id == f[0])))[0]["current_assessment_id"] == prior

    async def test_full_c2_and_deep_share_four_tool_calls():
        f, gateway, source = await fixture(), PipelineGateway(("deep",)), deep.AdaptiveLake()
        async with service.transaction(T) as store:
            alert = await store.one(select(A).where(A.c.id == f[2]))
            await store.db.execute(insert(m.AlertObjects.__table__).values(id=uuid4(), tenant_id=T, alert_id=f[2],
                material_id=alert["latest_material_id"], object_type="ip", object_role="ioc", object_key="ip:198.51.100.2",
                namespace="fixture", raw_value="198.51.100.2", normalized_value="198.51.100.2",
                source_path="$.ocsf_json.dst_endpoint.ip", attributes={}))
        backgrounds = []
        async def background(service_, tenant, name, args):
            assert tenant == T and args["parameters"]["selectors"]
            backgrounds.append(name)
            async with service_.transaction(tenant) as store:
                return [], await store.now()
        with patch("app.socai2.baseline_enrichment.sources.query", background):
            await execute(f, gateway, source, connected=frozenset({"assets", "history", "threat_intel"}))
        saved = await report(f[1])
        assert backgrounds == ["threat_intel", "assets"]
        background_steps = await rows(select(S).where(S.c.run_id == f[1], S.c.stage_code == "C2", S.c.kind == "tool"))
        assert next(s for s in background_steps if s["name"] == "threat_intel")["actual_args"]["parameters"]["selection"]["reason"] == "explicit_typed_ioc_reputation"
        assert next(s for s in background_steps if s["name"] == "history")["state"] == "skipped"
        assert source.calls == 2 and saved["execution"]["tool_calls"] == 4
        assert gateway.order == ["C3", "Deep", "Deep", "C6"], gateway.order
        second_input = model_data(gateway.middle.bodies[1]["messages"][1]["content"])
        assert any(o["tool_name"] == "network_connections" for o in second_input["tool_options"])
        assert saved["execution"]["followup_dispatch"]["routes"][0]["reason"] == "final_model_call_reserved"

    async def test_full_reserved_call_does_not_hide_insufficient_final_tokens():
        f = list(await fixture())
        def substantial_first_usage(payload):
            payload["usage"] = {"prompt_tokens": 11000, "completion_tokens": 1000, "total_tokens": 12000}
        gateway = PipelineGateway((), initial_mutate=substantial_first_usage)
        f[-1] = f[-1].model_copy(update={"max_tokens": 8000})
        await execute(f, gateway)
        saved = await report(f[1])
        assert gateway.order == [], gateway.order
        await system_closing(f)
        final_step = (await rows(select(S).where(S.c.run_id == f[1], S.c.stage_code == "C6", S.c.kind == "stage")))[0]
        assert final_step["error"]["code"] == "model_token_budget_insufficient", final_step["error"]
        initial_step = (await rows(select(S).where(S.c.run_id == f[1], S.c.stage_code == "C3", S.c.kind == "stage")))[0]
        assert initial_step["error"]["code"] in {"final_model_tokens_reserved", "model_token_budget_insufficient"}
        assert saved["execution"]["total_tokens"] == 0

    async def test_full_provider_error_receipts_c3_deep_c6_keep_run_unadopted():
        from test_socai2_model_errors import ModelCallError, failure
        checked = []
        for phase in ("C3", "Deep", "C6"):
            f = await fixture()
            gateway = PipelineGateway(("deep",) if phase == "Deep" else ())
            failed_calls = []
            async def fail_call(*_, failed_calls=failed_calls):
                failed_calls.append(True)
                raise failure()
            target = {"C3": gateway.initial, "Deep": gateway.middle, "C6": gateway.final}[phase]
            with patch.object(target, "complete", fail_call):
                try:
                    await execute(f, gateway)
                except ModelCallError:
                    pass
                else:
                    raise AssertionError("transport failure must not yield an adopted result")
            assert len(failed_calls) == 1
            steps = await rows(select(S).where(S.c.run_id == f[1], S.c.kind == "model"))
            failed = next(s for s in steps if s["output_artifact_id"] and s["state"] == "unknown")
            artifact = (await rows(select(F).where(F.c.id == failed["output_artifact_id"])))[0]
            data = artifact["content_json"]
            assert data["payload"]["raw"] is None
            assert data["payload"]["transport_error"]["fields"]["param"] == "text.format.schema"
            assert data["usage"]["total_tokens"] is None and failed["usage"]["usage_state"] == "unavailable"
            assert (await rows(select(R).where(R.c.id == f[1])))[0]["state"] == "unknown"
            await system_closing(f)
            checked.append(phase)
        return {"failure_stages_checked": checked, "adopted_results": 0, "attempts_per_failing_stage": 1}

    async def test_full_deepseek_wire_c3_deep_c6_preserves_saved_requests_and_budget():
        from test_socai2_deepseek_union_schema import DeepSeekWireGateway, branches
        f = await fixture()
        delegate = PipelineGateway(("query", "deep", ("deep", 1), "human"))
        gateway = DeepSeekWireGateway(delegate)
        await execute(f, gateway)
        saved = await report(f[1])
        assert delegate.order == ["C3", "Deep", "Deep", "C6"], {"order": delegate.order,
            "result": saved["result"], "limitations": saved["limitations"]}
        assert saved["result"]["validation_state"] == "accepted", saved["result"]
        requests = await rows(select(F).where(F.c.run_id == f[1], F.c.kind == "model_request").order_by(F.c.captured_at))
        actual = [a["content_json"]["payload"]["body"] for a in requests]
        assert actual == gateway.requests
        assert all(b["type"] for body in actual for b in branches(body["text"]["format"]["schema"]))
        assert saved["execution"]["model_calls"] == 4 and saved["execution"]["total_tokens"] == 4000
        return {"model_order": delegate.order, "exact_wire_saved": True, "limits_unchanged": True,
            "final_request_bytes": len(encoded(actual[-1])), "final_request_byte_limit": 48000 - 3000 - 3000 - 256, "model_substitute": True}

    async def test_final_original_followups_survive_new_reanalysis_proposal():
        def initial_text(payload):
            value = json.loads(payload["choices"][0]["message"]["content"])
            for i, item in enumerate(value["followups"]):
                item["objective"] = f"Original scoped confirmation {i}"
            payload["choices"][0]["message"]["content"] = json.dumps(value)
        def revised_text(payload):
            value = json.loads(payload["choices"][0]["message"]["content"])
            value["followups"][0]["objective"] = "New proposal; not the original executed plan"
            payload["choices"][0]["message"]["content"] = json.dumps(value)
        f = await fixture()
        gateway = PipelineGateway(("human", "human"), initial_mutate=initial_text)
        revised_gateway = c3.SyntheticGateway(mutate=revised_text)
        original_finalize = service.finalize
        async def reanalyze_then_finalize(*args, **kwargs):
            revised = await service.reanalyze(*args, gateway=revised_gateway)
            assert revised["state"] == "completed", revised
            return await original_finalize(*args, **kwargs)
        with patch.object(service, "finalize", reanalyze_then_finalize):
            await execute(f, gateway)
        saved = await report(f[1])
        assert saved["result"]["validation_state"] == "accepted", saved["result"]
        data = model_data(gateway.final.last_body["messages"][1]["content"])
        plan_id = saved["execution"]["followup_dispatch"]["initial_analysis_artifact_id"]
        assert data["followup_execution"]["initial_analysis_artifact_id"] == plan_id
        values = [i for i in data["items"] if isinstance(i["value"], dict)]
        planned = [i for i in values if "execution_plan_index" in i["value"]]
        assert {i["value"]["execution_plan_index"]: i["value"]["followup"]["objective"] for i in planned} == {
            0: "Original scoped confirmation 0", 1: "Original scoped confirmation 1"}
        assert all(r["state"] == "handoff" for r in data["followup_execution"]["routes"])
        newest = [i for i in values if i["value"].get("followup", {}).get("objective", "").startswith("New proposal")]
        assert newest and all("execution_plan_index" not in i["value"] for i in newest)
        requests = await rows(select(F).where(F.c.run_id == f[1], F.c.kind == "model_request"))
        request = next(r["content_json"]["payload"] for r in requests
            if r["content_json"]["payload"]["body"] == gateway.final.last_body)
        for item in planned:
            source = request["source_map"][item["id"]]
            assert source["required"] and source["ref"]["id"] == plan_id
            assert source["ref"]["source_path"] == f'$.analysis.followups.{item["value"]["execution_plan_index"]}'
        assert plan_id in request["input_artifact_ids"]
        assert not await rows(select(m.Tasks.__table__).where(m.Tasks.__table__.c.case_id == f[0]))
        assert saved["execution"]["model_calls"] == 3 and saved["execution"]["total_tokens"] == 3000
        return {"model_substitutes": 3, "original_plan_binding_preserved": True,
            "new_proposal_not_marked_executed": True, "human_tasks_created": 0}

    async def test_final_oversize_required_plan_does_not_call_model_or_adopt():
        def oversized(payload):
            value = json.loads(payload["choices"][0]["message"]["content"])
            value["followups"][0]["objective"] = "确认" * 500
            payload["choices"][0]["message"]["content"] = json.dumps(value)
        f, gateway = await fixture(), PipelineGateway(("human",), initial_mutate=oversized)
        await execute(f, gateway)
        saved = await report(f[1])
        assert gateway.order == ["C3"] and gateway.final.calls == 0
        await system_closing(f)
        final_stage = (await rows(select(S).where(S.c.run_id == f[1], S.c.stage_code == "C6")))[0]
        assert final_stage["state"] == "completed" and final_stage["error"]["code"] == "required_model_input_unavailable"
        original_id = saved["execution"]["followup_dispatch"]["initial_analysis_artifact_id"]
        initial = (await rows(select(F).where(F.c.id == UUID(original_id))))[0]["content_json"]
        assert initial["analysis"]["followups"][0]["objective"] == "确认" * 500
        return {"final_model_calls": 0, "system_closing_saved": True, "original_plan_not_truncated": True}

    async def test_full_schema_rejections_release_run_at_c3_deep_and_c6():
        from app.socai2.model_errors import ModelCallError
        checked = []
        for phase in ("C3", "Deep", "C6"):
            f = await fixture()
            gateway = PipelineGateway(("deep",) if phase == "Deep" else ())
            calls = []
            async def reject_schema(*_, calls=calls):
                calls.append(True)
                raise ModelCallError({"http_status": 400, "fields": {
                    "message": 'Grammar error: Unimplemented keys: ["uniqueItems"]'}})
            target = {"C3": gateway.initial, "Deep": gateway.middle, "C6": gateway.final}[phase]
            with patch.object(target, "complete", reject_schema):
                await execute(f, gateway)
            assert len(calls) == 1
            run = (await rows(select(R).where(R.c.id == f[1])))[0]
            assert run["state"] == "failed" and run["ended_at"] is not None
            steps = await rows(select(S).where(S.c.run_id == f[1]))
            assert not any(s["state"] in {"running", "planned", "unknown"} for s in steps)
            failed = next(s for s in steps if s["kind"] == "model" and s["state"] == "failed")
            assert failed["ended_at"] and failed["error"]["code"] == "model_schema_rejected"
            assert failed["usage"]["total_tokens"] is None
            await system_closing(f)
            checked.append(str(f[1]))
        return {"run_ids": checked, "attempts_per_failure": 1, "active_slots_held": 0}

    checks = [test_rejected_c3_scope_still_calls_c6_and_saves_case_judgment,
        test_c6_null_extension_is_audited_without_rewriting_original,
        test_unavailable_model_view_closes_without_unknown_or_model_call,
        test_system_closing_preserves_existing_model_and_human_judgment,
        test_full_deep_receipt_reused_by_supporting_direct_query,
        test_full_distinct_direct_queries_keep_final_plan_receipt_links,
        test_full_schema_rejections_release_run_at_c3_deep_and_c6,
        test_final_original_followups_survive_new_reanalysis_proposal,
        test_final_oversize_required_plan_does_not_call_model_or_adopt,
        test_full_deepseek_wire_c3_deep_c6_preserves_saved_requests_and_budget,
        test_full_provider_error_receipts_c3_deep_c6_keep_run_unadopted,
        test_full_human_graph_and_no_need_skip_external_queries,
        test_full_adaptive_queries_reserve_fourth_call_and_deduplicate_questions,
        test_full_two_call_policy_saves_final_slot_without_deep_dispatch,
        test_full_claim_committed_replay_and_scope_changes_wait_for_manual_start,
        test_full_cancel_holds_slot_and_does_not_finalize,
        test_full_no_model_or_rejected_initial_yields_system_handoff,
        test_full_limits_are_not_raised_and_exhaustion_still_delivers_receipt,
        test_full_rejected_final_is_retained_without_retry_or_adoption,
        test_full_c2_and_deep_share_four_tool_calls,
        test_full_reserved_call_does_not_hide_insufficient_final_tokens]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 180)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- retain original failure evidence
            record(check.__name__, False, traceback.format_exc())
