"""Real synthetic PG loop/synthesis checks; no real model or lake calls."""
import asyncio
import copy
import importlib.util
import json
import traceback
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import baseline_analysis as c3
from app.socai2 import baseline_analysis_contract as c3_contract
from app.socai2 import baseline_deep_contract as contract
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_reasoning import ModelSteps
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import A, C, F, R, StoreError
from jsonschema import Draft202012Validator, FormatChecker
from socai2_test_model_view import model_data
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker


def helper(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


initial_helper = helper("test_socai2_baseline_analysis")
lake_helper = helper("test_socai2_baseline_evidence")
T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic Deep reviewer")
CONTRACTS = json.loads((Path(__file__).parents[1] / "app/socai2/contracts.schema.json").read_text("utf-8"))


class DecisionGateway:
    provider, model = "synthetic", "synthetic-deep-no-network"

    def __init__(self, *, hook=None, mutate=None, enabled=True, two_queries=False):
        self.hook, self.mutate, self.enabled, self.two_queries = hook, mutate, enabled, two_queries
        self.bodies, self.payloads = [], []

    async def configure(self, service, tenant):
        assert tenant == T
        return self.enabled

    async def complete(self, body, timeout):
        assert timeout > 0 and "tools" not in body and body["max_tokens"] == 3000
        self.bodies.append(copy.deepcopy(body))
        if self.hook:
            await self.hook()
        data = model_data(body["messages"][1]["content"])
        q = data["question"]["id"]
        selected = None
        if not data["queries"]:
            selected = next((o for o in data["tool_options"] if o["tool_name"] == "process_activity"), None)
        elif self.two_queries and any(r["tool_name"] == "process_activity" and r["observed_rows_in_bounded_fetch"] == 0
                                      for r in data["queries"]):
            selected = next((o for o in data["tool_options"] if o["tool_name"] == "network_connections"), None)
        if selected:
            reply = {"question_id": q, "action": "query", "binding_id": selected["id"], "reason": "合成：据当前未决项补查", "answer": None}
        else:
            found = any(r["observed_rows_in_bounded_fetch"] for r in data["queries"])
            evidence = next((i["id"] for i in data["items"] if i.get("membership_basis") == "query_binding_only"), None)
            reply = {"question_id": q, "action": "answer" if found and evidence else "handoff", "binding_id": None,
                "reason": "合成：按实际返回停止", "answer": {"state": "supported" if found and evidence else "unresolved",
                    "text": "合成：查询返回有限观察，归属与授权仍待核" if found else "合成：未取得所需查询证据，不能排除行为",
                    "support_ids": [evidence] if found and evidence else [], "counter_ids": [],
                    "alternatives": ["其他解释仍需来源核实"], "limitations": ["主机窗口匹配不证明告警归属；来源覆盖未知"]}}
        payload = {"id": "synthetic-deep-" + str(len(self.bodies)), "choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(reply, ensure_ascii=False)}}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 500, "total_tokens": 1000}}
        if self.mutate:
            self.mutate(payload, data)
        self.payloads.append(copy.deepcopy(payload))
        return payload


class AdaptiveLake(lake_helper.SyntheticLake):
    async def query(self, args, query_id, timeout):
        self.count = 0 if args["tool_name"] == "process_activity" else 1
        return await super().query(args, query_id, timeout)


async def run_checks(engine, record, only=None):
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))

    async def rows(query):
        async with service.transaction(T) as store:
            return (await store.db.execute(query)).mappings().all()

    async def make_alert(store, host):
        aid, mid = uuid4(), uuid4()
        await store.db.execute(insert(A).values(id=aid, tenant_id=T, title="synthetic Deep alert",
            source_namespace="deep-fixture", source_identity_key=str(aid)))
        await store.db.execute(insert(m.AlertMaterials.__table__).values(id=mid, tenant_id=T, alert_id=aid,
            revision=1, ocsf_json=lake_helper.original(host), detection={}, source_scope={}, material_state="complete", retention={}))
        await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        await store.db.execute(insert(m.AlertObjects.__table__).values(id=uuid4(), tenant_id=T, alert_id=aid,
            material_id=mid, object_type="host", object_role="entity", object_key="host:" + host, namespace="fixture",
            raw_value=host, normalized_value=host, source_path="$.ocsf_json.device.name", attributes={}))
        return aid

    async def fixture(model_calls=4, tool_calls=4, feedback=False):
        cid, host = uuid4(), "synthetic-" + uuid4().hex
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="synthetic Deep Case", created_by=USER))
            aid = await make_alert(store, host)
            if feedback:
                fid = uuid4()
                await store.db.execute(insert(m.AlertAssessments.__table__).values(id=fid, tenant_id=T,
                    alert_id=aid, kind="human_feedback", verdict="benign", rationale="synthetic authorized maintenance",
                    producer="human", actor=ACTOR.snapshot(), assessed_at=now, operation_key=str(uuid4())))
                await store.db.execute(update(A).where(A.c.id == aid).values(latest_feedback_id=fid))
            out = await store.replace_members(cid, {aid}, expected_revision=0, actor=ACTOR, operation_id=uuid4())
        rid = UUID(out["pending_run_id"])
        async def idle(claim):
            pass
        await service.start(T, cid, rid, Start(expected_scope_revision=1, operation_key=uuid4(),
            window_start=now - timedelta(minutes=5), window_end=now + timedelta(minutes=5)), actor=ACTOR,
            executor=idle, executor_version="synthetic-deep", limits=Limits(max_model_calls=model_calls,
                max_tool_calls=tool_calls, max_rows_per_query=5, max_tokens=24000,
                deadline_at=now + timedelta(seconds=120), policy_version="synthetic-deep"))
        # Source adapters deliberately unavailable for this fixture, not live SQL.
        with patch("app.socai2.baseline_enrichment.sources.CONNECTED", frozenset()):
            await service.enrich(T, cid, rid)
        first = initial_helper.SyntheticGateway()
        initial = await service.analyze(T, cid, rid, gateway=first)
        assert initial["state"] == "completed", initial.get("reason")
        ctx = await service.read_context(T, cid, rid)
        return cid, rid, aid, ctx.questions[0].id, initial

    async def reject(code, task):
        try:
            await task
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected " + code)

    async def test_deep_query_answer_reanalysis_same_run_and_originals():
        cid, rid, _, q, initial = await fixture()
        originals = {r["id"]: r["sha256"] for r in await rows(select(F).where(F.c.run_id == rid))}
        gateway, lake = DecisionGateway(), lake_helper.SyntheticLake()
        deep = await service.deepen(T, cid, rid, q, gateway=gateway, lake=lake)
        assert deep["state"] == "completed" and deep["answer"]["state"] == "supported", deep
        assert len(gateway.bodies) == 2 and lake.calls == 1
        assert deep == await service.deepen(T, cid, rid, q, gateway=gateway, lake=lake)
        synthesis = initial_helper.SyntheticGateway()
        out = await service.reanalyze(T, cid, rid, gateway=synthesis)
        assert out["state"] == "completed" and out["stage"] == "C3_reanalysis", out.get("reason")
        assert out == await service.reanalyze(T, cid, rid, gateway=synthesis) and synthesis.calls == 1
        assert initial == await service.analyze(T, cid, rid, gateway=synthesis)
        artifacts = await rows(select(F).where(F.c.run_id == rid))
        assert all(r["sha256"] == originals[r["id"]] for r in artifacts if r["id"] in originals)
        for row in artifacts:
            schema = {"deep_analysis": "analysis_block", "domain_analysis": "analysis_block", "tool_request": "tool_args",
                "tool_response": "tool_exchange", "model_request": "model_exchange", "model_response": "model_exchange"}.get(row["kind"])
            if schema:
                Draft202012Validator({**CONTRACTS, "$ref": "#/$defs/" + schema}, format_checker=FormatChecker()).validate(row["content_json"])
        steps = await rows(select(c3.S).where(c3.S.c.run_id == rid))
        assert sum(s["kind"] == "model" for s in steps) == 4
        active_tools = [s for s in steps if s["stage_code"] == "C4.query"]
        owner = next(s for s in steps if s["stage_code"] == "C4.deep" and s["kind"] == "stage")
        assert len(active_tools) == 1 and active_tools[0]["parent_step_id"] == owner["id"]
        assert not await rows(select(m.Results.__table__).where(m.Results.source_run_id == rid))
        assert (await rows(select(C).where(C.c.id == cid)))[0]["current_assessment_id"] is None
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "running"
        source_map = out["source_map"]
        assert any(s.get("membership_basis") == "query_binding_only" for s in source_map.values())
        assert any(s["ref"]["role"] == "prior_analysis" for s in source_map.values())

    async def test_deep_uses_empty_return_to_choose_second_query_and_shares_budget():
        cid, rid, _, q, _ = await fixture()
        gateway, lake = DecisionGateway(two_queries=True), AdaptiveLake()
        out = await service.deepen(T, cid, rid, q, gateway=gateway, lake=lake)
        assert out["answer"]["state"] == "supported" and len(gateway.bodies) == 3 and lake.calls == 2, out
        middle = model_data(gateway.bodies[1]["messages"][1]["content"])
        assert middle["queries"][0]["observed_rows_in_bounded_fetch"] == 0
        assert middle["queries"][0]["tool_name"] == "process_activity"
        assert middle["queries"][0]["hostname"] == lake.arguments[0]["parameters"]["hostname"]
        assert middle["queries"][0]["window_start"] == lake.arguments[0]["scope"]["window_start"]
        assert middle["queries"][0]["window_end"] == lake.arguments[0]["scope"]["window_end"]
        assert all(o["tool_name"] != "process_activity" for o in middle["tool_options"])
        assert {a["tool_name"] for a in lake.arguments} == {"process_activity", "network_connections"}
        gateway2 = initial_helper.SyntheticGateway()
        later = await service.reanalyze(T, cid, rid, gateway=gateway2)
        assert later["state"] == "skipped" and later["reason"] == "model_call_budget_exhausted" and gateway2.calls == 0

    async def test_deep_concurrent_owner_and_member_change():
        cid, rid, aid, q, _ = await fixture()
        entered, release = asyncio.Event(), asyncio.Event()
        async def hold():
            steps = await rows(select(c3.S).where(c3.S.c.run_id == rid, c3.S.c.stage_code == "C4.deep"))
            assert any(s["kind"] == "model" and s["state"] == "running" and s["input_artifact_id"] for s in steps)
            entered.set()
            await release.wait()
        gateway = DecisionGateway(hook=hold)
        task = asyncio.create_task(service.deepen(T, cid, rid, q, gateway=gateway, lake=lake_helper.SyntheticLake()))
        try:
            await asyncio.wait_for(entered.wait(), 10)
            await reject("deep_already_claimed", service.deepen(T, cid, rid, q, gateway=DecisionGateway()))
            await reject("baseline_step_in_progress", service.deepen(T, cid, rid, "coverage", gateway=DecisionGateway()))
            await reject("baseline_step_in_progress", service.reanalyze(T, cid, rid, gateway=initial_helper.SyntheticGateway()))
            material = await service.prepare_evidence(T, cid, rid)
            bid = next(iter(material["catalog"]["bindings"]))
            await reject("baseline_step_in_progress", service.query_evidence(T, cid, rid, bid, q, gateway=lake_helper.SyntheticLake()))
            async with service.transaction(T) as store:
                second = await make_alert(store, "later-synthetic-host")
            change = await service.replace_members(T, cid, {aid, second}, expected_revision=1, actor=ACTOR, operation_id=uuid4())
            assert change["pending_run_id"] != str(rid)
        finally:
            release.set()
            await task
        assert all(str(second) not in b["messages"][1]["content"] for b in gateway.bodies)

    async def test_deep_invalid_decision_keeps_raw_without_tool():
        cid, rid, _, q, _ = await fixture()
        def mutate(payload, data):
            value = json.loads(payload["choices"][0]["message"]["content"])
            value["binding_id"] = "not-offered"
            payload["choices"][0]["message"]["content"] = json.dumps(value)
        gateway, lake = DecisionGateway(mutate=mutate), lake_helper.SyntheticLake()
        out = await service.deepen(T, cid, rid, q, gateway=gateway, lake=lake)
        assert out["state"] == "failed" and out["answer"] is None and lake.calls == 0
        raw = await rows(select(F).where(F.c.run_id == rid, F.c.kind == "model_response", F.c.schema_version == contract.SCHEMA))
        assert raw[0]["content_json"]["payload"]["raw"] == gateway.payloads[0]
        assert out == await service.deepen(T, cid, rid, q, gateway=gateway, lake=lake) and len(gateway.bodies) == 1

    async def test_deep_budget_config_empty_and_unknown_usage():
        cid, rid, _, q, _ = await fixture(model_calls=1)
        gateway, lake = DecisionGateway(), lake_helper.SyntheticLake()
        out = await service.deepen(T, cid, rid, q, gateway=gateway, lake=lake)
        assert out["stop_reason"] == "model_call_budget_exhausted" and not gateway.bodies and lake.calls == 0
        cid, rid, _, q, _ = await fixture(tool_calls=0)
        out = await service.deepen(T, cid, rid, q, gateway=DecisionGateway(), lake=lake)
        assert out["stop_reason"] == "handoff" and out["answer"]["state"] == "unresolved" and lake.calls == 0
        cid, rid, _, q, _ = await fixture()
        out = await service.deepen(T, cid, rid, q, gateway=DecisionGateway(enabled=False), lake=lake)
        assert out["stop_reason"] == "model_not_configured"
        cid, rid, _, q, _ = await fixture()
        gateway = DecisionGateway(mutate=lambda p, d: p.pop("usage"))
        out = await service.deepen(T, cid, rid, q, gateway=gateway, lake=lake)
        assert out["state"] == "failed" and out["stop_reason"] == "model_usage_unknown_or_inconsistent"
        later = initial_helper.SyntheticGateway()
        out = await service.reanalyze(T, cid, rid, gateway=later)
        assert out["reason"] == "prior_model_usage_unknown" and later.calls == 0

    async def test_deep_cancel_and_tenant_scope():
        cid, rid, _, q, _ = await fixture()
        gateway, lake = DecisionGateway(), lake_helper.SyntheticLake()
        await reject("case_not_found", service.deepen(OTHER, cid, rid, q, gateway=gateway, lake=lake))
        await reject("question_outside_frozen_scope", service.deepen(T, cid, rid, "outside", gateway=gateway, lake=lake))
        async def cancel():
            raise asyncio.CancelledError()
        gateway.hook = cancel
        try:
            await service.deepen(T, cid, rid, q, gateway=gateway, lake=lake)
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("expected cancelled dispatch")
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "unknown"
        steps = await rows(select(c3.S).where(c3.S.c.run_id == rid, c3.S.c.stage_code == "C4.deep"))
        assert all(s["state"] == "unknown" for s in steps) and lake.calls == 0
        await reject("deep_already_claimed", service.deepen(T, cid, rid, q, gateway=gateway, lake=lake))

    async def test_deep_request_commit_failure_before_model():
        cid, rid, _, q, _ = await fixture()
        gateway, marker = DecisionGateway(), []
        old = ModelSteps.save
        async def fail(self, store, run, step, payload, kind, refs=()):
            identity = await old(self, store, run, step, payload, kind, refs)
            if kind == "model_request":
                await store.db.execute(insert(c3.S).values(id=uuid4(), tenant_id=T, run_id=rid,
                    seq=10000000, parent_step_id=uuid4(), kind="model", stage_code="C4.deep", state="planned", name="synthetic FK failure"))
                marker.append(True)
            return identity
        with patch.object(ModelSteps, "save", fail):
            try:
                await service.deepen(T, cid, rid, q, gateway=gateway, lake=lake_helper.SyntheticLake())
            except IntegrityError as exc:
                assert getattr(exc.orig.__cause__, "constraint_name", None) in {"run_steps_parent_step_id_fk", "run_steps_parent_step_id_scope_fk"}
            else:
                raise AssertionError("expected deferred FK commit failure")
        assert marker == [True] and not gateway.bodies
        assert not await rows(select(F).where(F.c.run_id == rid, F.c.kind == "model_request", F.c.schema_version == contract.SCHEMA))
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "unknown"

    async def test_reanalysis_new_basis_only_and_query_attribution_guard():
        cid, rid, _, q, _ = await fixture()
        await reject("new_evidence_required", service.reanalyze(T, cid, rid, gateway=initial_helper.SyntheticGateway()))
        material = await service.prepare_evidence(T, cid, rid)
        first = await service.reanalyze(T, cid, rid, gateway=initial_helper.SyntheticGateway())
        assert first["state"] == "completed", first.get("reason")
        bid = next(iter(material["catalog"]["bindings"]))
        await service.query_evidence(T, cid, rid, bid, q, gateway=lake_helper.SyntheticLake())
        gateway = initial_helper.SyntheticGateway()
        next_result = await service.reanalyze(T, cid, rid, gateway=gateway)
        assert next_result["state"] == "completed" and first["basis"]["evidence_set_key"] != next_result["basis"]["evidence_set_key"]
        assert first["analysis"] is not None
        body = gateway.last_body
        parsed = initial_helper.reply_for(body)
        related = next(s for s, ref in next_result["source_map"].items() if ref.get("membership_basis") == "query_binding_only")
        parsed["findings"][0].update(state="observed", support_ids=[related])
        ctx = await service.read_context(T, cid, rid)
        data = model_data(body["messages"][1]["content"])
        try:
            c3_contract.parse(json.dumps(parsed), next_result["source_map"], ctx, data["members"])
        except c3_contract.AnalysisRejected as exc:
            assert str(exc) == "direct_alert_membership_not_proven"
        else:
            raise AssertionError("query binding promoted to member fact")

    async def test_deep_contract_and_citation_roles():
        cid, rid, _, q, _ = await fixture(tool_calls=0)
        deep = await service.deepen(T, cid, rid, q, gateway=DecisionGateway(), lake=lake_helper.SyntheticLake())
        row = next(r for r in await rows(select(F).where(F.c.run_id == rid, F.c.schema_version == contract.SCHEMA))
            if r["content_json"].get("type") == "deep_summary")
        assert contract.citation_roles(deep) == {"$.answer": "prior_analysis"}
        async with service.transaction(T) as store:
            run = await store.run(cid, rid)
            members = (await store.db.execute(select(m.RunMembers.__table__).where(m.RunMembers.run_id == rid))).mappings().all()
            ref = {"type": "artifact", "id": str(row["id"]), "role": "prior_analysis", "external": None,
                   "source_path": "$.answer", "row_keys": []}
            pub = SimpleNamespace(model_dump=lambda **_: {"refs": [ref]}, graph_artifact_id=None, report_artifact_id=None)
            await store.validate_result_refs(run, members, pub)
            ref["role"] = "observation"
            await reject("context_citation_path_or_role_invalid", store.validate_result_refs(run, members, pub))
        answer = {"state": "unresolved", "text": "unknown", "support_ids": [], "counter_ids": [], "alternatives": [], "limitations": ["missing"]}
        valid = {"question_id": q, "action": "handoff", "binding_id": None, "reason": "need source", "answer": answer}
        variants = [{**valid, "question_id": "outside"}, {**valid, "sql": "SELECT 1"},
            {**valid, "binding_id": "B1"}, {**valid, "answer": {**answer, "state": "supported"}},
            {**valid, "answer": {**answer, "support_ids": ["E999"]}}, {**valid, "answer": {**answer, "limitations": []}}]
        for value in variants:
            try:
                contract.parse(json.dumps(value), {}, {}, q)
            except c3_contract.AnalysisRejected:
                pass
            else:
                raise AssertionError("invalid Deep decision admitted")
        return {"negative_contract_variants": len(variants)}

    async def test_deep_reads_frozen_human_feedback_and_caps_complete_messages():
        cid, rid, _, q, _ = await fixture(feedback=True, tool_calls=0)
        def answer_with_feedback(payload, data):
            human = next(i for i in data["items"] if i["role"] == "human_statement")
            assert human["value"]["rationale"] == "synthetic authorized maintenance"
            value = {"question_id": q, "action": "answer", "binding_id": None, "reason": "已有冻结人工反馈",
                "answer": {"state": "supported", "text": "合成：存在这一范围的人工反馈，仍是人工陈述",
                    "support_ids": [human["id"]], "counter_ids": [], "alternatives": [], "limitations": ["不升级为机器观察"]}}
            payload["choices"][0]["message"]["content"] = json.dumps(value)
        gateway = DecisionGateway(mutate=answer_with_feedback)
        out = await service.deepen(T, cid, rid, q, gateway=gateway, lake=lake_helper.SyntheticLake())
        assert out["state"] == "completed" and out["answer"]["state"] == "supported"
        assert out["source_map"][out["answer"]["support_ids"][0]]["ref"]["role"] == "human_statement"
        for body in gateway.bodies:
            assert len(c3.encoded(body["messages"])) <= 12288
            assert len(body["messages"][1]["content"].encode()) <= 8192
        schema = json.loads((Path(__file__).parents[1] / "app/socai2/baseline_deep.schema.json").read_text("utf-8"))
        Draft202012Validator(schema).validate(json.loads(gateway.payloads[0]["choices"][0]["message"]["content"]))

    checks = [test_deep_query_answer_reanalysis_same_run_and_originals,
        test_deep_uses_empty_return_to_choose_second_query_and_shares_budget, test_deep_concurrent_owner_and_member_change,
        test_deep_invalid_decision_keeps_raw_without_tool, test_deep_budget_config_empty_and_unknown_usage,
        test_deep_cancel_and_tenant_scope, test_deep_request_commit_failure_before_model,
        test_reanalysis_new_basis_only_and_query_attribution_guard, test_deep_contract_and_citation_roles,
        test_deep_reads_frozen_human_feedback_and_caps_complete_messages]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 180)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- retain original failures
            record(check.__name__, False, traceback.format_exc())
