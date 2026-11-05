"""C6 real isolated PG transaction checks with explicit model/lake substitutes."""
import asyncio
import copy
import hashlib
import importlib.util
import json
import traceback
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import baseline_delivery_contract as contract
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import (
    A,
    BaselineStore,
    C,
    F,
    R,
    StoreError,
    digest,
    encoded,
)
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


c3 = helper("test_socai2_baseline_analysis")
lake = helper("test_socai2_baseline_evidence")
deep = helper("test_socai2_baseline_deep")
T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic C6 reviewer")
S, RESULT = m.RunSteps.__table__, m.Results.__table__
CONTRACTS = json.loads((Path(__file__).parents[1] / "app/socai2/contracts.schema.json").read_text("utf-8"))


def reply_for(body):
    data = model_data(body["messages"][1]["content"])
    initial = c3.reply_for(body)
    own = {aid: next(i["id"] for i in data["items"] if aid in i["alert_ids"] and not (
        isinstance(i["value"], dict) and "comparison_result_id" in i["value"]))
        for aid in data["members"]}
    ids = list(data["members"])
    comparison = data["comparison"]
    baseline = next((i["id"] for i in data["items"] if isinstance(i["value"], dict)
        and i["value"].get("comparison_result_id") == comparison["result_id"] and comparison["result_id"]), None)
    kind = "initial" if comparison["state"] == "initial" else "expanded" if baseline else "not_comparable"
    return {"analysis": initial, "conclusion": {"text": "synthetic final conclusion: authorization unresolved",
            "state": "uncertain", "alert_ids": ids, "support_ids": list(dict.fromkeys(own.values())),
            "limitations": ["synthetic partial evidence; not a proven attack"]},
        "closing_note": "synthetic final synthesis retained; confirm authorization",
        "comparison": {"kind": kind, "summary": None if kind == "initial" else "synthetic comparison within explicitly selected scope",
            "support_ids": [baseline, own[ids[0]]] if baseline else []},
        "impact": {"summary": "actual impact remains unconfirmed", "alert_ids": [], "support_ids": [],
            "supported_changes": [], "cannot_generalize": ["no inference from graph reachability"], "next_steps": ["verify authorization"]},
        "recommendations": [{"id": "R1", "action_type": "investigate", "object_keys": [],
            "reason": "verify approval within frozen scope", "source_ids": [own[ids[0]]], "limitations": ["not executed"]}]}


class FinalGateway(c3.SyntheticGateway):
    model = "synthetic-C6-no-network"

    async def complete(self, body, timeout):
        assert timeout > 0 and body["max_tokens"] == 3000 and len(encoded(body["messages"])) <= 12288
        assert len(body["messages"][1]["content"].encode()) <= 8192
        self.calls += 1
        self.last_body = copy.deepcopy(body)
        if self.hook:
            await self.hook()
        value = reply_for(body)
        payload = {"id": "synthetic-final-response", "choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(value)}}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 500, "total_tokens": 1000}}
        if self.mutate:
            self.mutate(payload)
        self.last_payload = copy.deepcopy(payload)
        return payload


async def run_checks(engine, record, only=None):
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))

    async def rows(query):
        async with service.transaction(T) as store:
            return (await store.db.execute(query)).mappings().all()

    async def new_alert(store, host):
        aid, mid = uuid4(), uuid4()
        await store.db.execute(insert(A).values(id=aid, tenant_id=T, title="synthetic final alert",
            source_namespace="delivery-fixture", source_identity_key=str(aid)))
        await store.db.execute(insert(m.AlertMaterials.__table__).values(id=mid, tenant_id=T, alert_id=aid,
            revision=1, ocsf_json=lake.original(host), detection={}, source_scope={}, material_state="complete", retention={}))
        await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        await store.db.execute(insert(m.AlertObjects.__table__).values(id=uuid4(), tenant_id=T, alert_id=aid,
            material_id=mid, object_type="host", object_role="entity", object_key="host:" + host, namespace="fixture",
            raw_value=host, normalized_value=host, source_path="$.ocsf_json.device.name", attributes={}))
        return aid

    async def fixture(calls=4, *, prior_case=None, comparison=None, initial_gateway=None):
        cid, host = (prior_case[0], prior_case[2]) if prior_case else (uuid4(), "synthetic-" + uuid4().hex)
        async with service.transaction(T) as store:
            now = await store.now()
            if not prior_case:
                await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="synthetic final Case", created_by=USER))
            aid = await new_alert(store, host)
            aids = [*prior_case[1], aid] if prior_case else [aid]
            scope = await store.replace_members(cid, set(aids), expected_revision=1 if prior_case else 0,
                actor=ACTOR, operation_id=uuid4())
        rid = UUID(scope["pending_run_id"])
        async def idle(claim):
            pass
        await service.start(T, cid, rid, Start(expected_scope_revision=2 if prior_case else 1, operation_key=uuid4(),
            window_start=now - timedelta(minutes=5), window_end=now + timedelta(minutes=5), comparison_result_id=comparison),
            actor=ACTOR, executor=idle, executor_version="synthetic-C6", limits=Limits(max_model_calls=calls,
                max_tool_calls=4, max_tokens=24000, max_rows_per_query=5, deadline_at=now + timedelta(seconds=120), policy_version="synthetic-C6"))
        with patch("app.socai2.baseline_enrichment.sources.CONNECTED", frozenset()):
            await service.enrich(T, cid, rid)
        await service.analyze(T, cid, rid, gateway=initial_gateway or c3.SyntheticGateway())
        return cid, rid, aids, host

    async def report(out):
        return (await rows(select(F).where(F.c.id == UUID(out["detail_artifact_id"]))))[0]["content_json"]

    async def reject(code, call):
        try:
            await call
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected " + code)

    async def test_c6_final_report_result_adoption_and_replay():
        cid, rid, aids, _ = await fixture()
        gateway = FinalGateway()
        out = await service.finalize(T, cid, rid, gateway=gateway)
        assert out["state"] == "completed", out
        assert out == await service.finalize(T, cid, rid, gateway=gateway) and gateway.calls == 1
        assert out["outcome"]["adoption"]["state"] == "adopted"
        saved = await report(out)
        core = (await rows(select(F).where(F.c.id == UUID(out["report_artifact_id"]))))[0]["content_json"]
        Draft202012Validator({**CONTRACTS, "$ref": "#/$defs/report_result"}, format_checker=FormatChecker()).validate(core)
        assert core["result_id"] == saved["result_id"] == out["outcome"]["result_id"]
        row = (await rows(select(RESULT).where(RESULT.c.id == UUID(out["outcome"]["result_id"]))))[0]
        for key in ("conclusion", "conclusion_state", "conclusion_origin", "validation_state", "closing_note", "findings",
                "questions", "recommendations", "change_kind", "change_summary", "case_impact", "delivery_state"):
            assert saved["result"][key] == row[key], key
        assert saved["result"]["delivery_state"] == "partial" and saved["execution"]["model_calls"] == 2
        assert saved["result"]["case_impact"]["affected_scope"]["alert_ids"] == []
        assert saved["result"]["case_impact"]["affected_scope"]["object_keys"] == []
        assert all(not f["scope"]["object_keys"] for f in saved["result"]["findings"])
        assert len(saved["domain_artifact_ids"]) == 4 and saved["execution"]["total_tokens"] == 2000
        assert saved["result"]["recommendations"][0]["approval_requirement"] == "unknown"
        for key in ("findings", "questions", "recommendations", "case_impact"):
            Draft202012Validator({**CONTRACTS, "$ref": "#/$defs/" + key}, format_checker=FormatChecker()).validate(row[key])
        text = (await rows(select(F).where(F.c.id == UUID(out["markdown_artifact_id"]))))[0]
        assert text["sha256"] == hashlib.sha256(text["content_text"].encode()).hexdigest()
        assert saved["result"]["conclusion"] in text["content_text"]
        assert len(saved["result"]["members"]) == len(aids)
        assert (await rows(select(C).where(C.c.id == cid)))[0]["handling_status"] == "new"
        return {"result_id": out["outcome"]["result_id"], "report_id": out["report_artifact_id"]}

    async def test_c6_is_fourth_model_after_deep_without_extra_report_call():
        cid, rid, _, _ = await fixture()
        middle = await service.deepen(T, cid, rid, "detection_facts", gateway=deep.DecisionGateway(), lake=lake.SyntheticLake())
        assert middle["state"] == "completed"
        out = await service.finalize(T, cid, rid, gateway=FinalGateway())
        assert out["state"] == "completed", out
        saved = await report(out)
        assert saved["execution"]["model_calls"] == 4 and saved["execution"]["tool_calls"] == 1
        assert saved["execution"]["total_tokens"] == 4000

    async def test_c6_exhaustion_and_unknown_usage_are_system_handoffs():
        cid, rid, _, _ = await fixture(calls=1)
        gateway = FinalGateway()
        out = await service.finalize(T, cid, rid, gateway=gateway)
        assert out["reason"] == "model_call_budget_exhausted" and gateway.calls == 0
        saved = await report(out)
        assert saved["result"]["conclusion"] is None and saved["result"]["conclusion_origin"] == "system"
        assert out["outcome"]["adoption"]["state"] == "not_eligible"
        assert all(not m["conclusion_covered"] for m in saved["result"]["members"])
        cid, rid, _, _ = await fixture()
        unknown = FinalGateway(mutate=lambda payload: payload.pop("usage"))
        out = await service.finalize(T, cid, rid, gateway=unknown)
        assert out["reason"] == "model_usage_unknown_or_inconsistent"
        saved = await report(out)
        assert saved["execution"]["total_tokens"] is None and saved["execution"]["usage_state"] == "unknown"

    async def test_c6_selected_comparison_has_frozen_old_scope_and_new_members():
        cid, rid, aids, host = await fixture()
        first = await service.finalize(T, cid, rid, gateway=FinalGateway())
        old_hash = digest(await report(first))
        cid, rid, new_aids, _ = await fixture(prior_case=(cid, aids, host), comparison=UUID(first["outcome"]["result_id"]))
        out = await service.finalize(T, cid, rid, gateway=FinalGateway())
        assert out["state"] == "completed", out
        saved = await report(out)
        assert saved["result"]["change_kind"] == "expanded"
        assert saved["comparison"]["added_alert_ids"] == [str(new_aids[-1])]
        assert saved["comparison"]["shared_alert_ids"] == list(map(str, aids))
        assert digest(await report(first)) == old_hash
        assert any(r["ref"]["type"] == "result" and r["ref"]["id"] == first["outcome"]["result_id"] for r in saved["source_map"].values())

    async def test_c6_unselected_history_does_not_claim_initial_comparison():
        cid, rid, aids, host = await fixture()
        await service.finalize(T, cid, rid, gateway=FinalGateway())
        cid, rid, _, _ = await fixture(prior_case=(cid, aids, host))
        out = await service.finalize(T, cid, rid, gateway=FinalGateway())
        saved = await report(out)
        assert saved["comparison"]["state"] == "not_selected" and saved["result"]["change_kind"] == "not_comparable"

    async def test_c6_concurrent_owner_and_scope_change_prevent_stale_adoption():
        cid, rid, aids, host = await fixture()
        async def during_model():
            await reject("delivery_already_claimed", service.finalize(T, cid, rid, gateway=FinalGateway()))
            await reject("baseline_step_in_progress", service.reanalyze(T, cid, rid, gateway=c3.SyntheticGateway()))
            async with service.transaction(T) as store:
                extra = await new_alert(store, host)
            out = await service.replace_members(T, cid, set(aids + [extra]), expected_revision=1, actor=ACTOR, operation_id=uuid4())
            assert out["pending_run_id"] != str(rid)
        out = await service.finalize(T, cid, rid, gateway=FinalGateway(hook=during_model))
        assert out["state"] == "completed" and out["outcome"]["adoption"]["state"] == "stale_scope", out
        assert (await report(out))["scope"]["alert_ids"] == list(map(str, aids))
        assert len(await rows(select(S).where(S.c.run_id == rid, S.c.kind == "model", S.c.stage_code == "C6"))) == 1

    async def test_c6_rebuilds_stale_graph_before_claim():
        cid, rid, _, _ = await fixture()
        before = await service.build_graph(T, cid, rid)
        prepared = await service.prepare_evidence(T, cid, rid)
        binding = next(iter(prepared["catalog"]["bindings"]))
        await service.query_evidence(T, cid, rid, binding, "member_relationships", gateway=lake.SyntheticLake(0))
        out = await service.finalize(T, cid, rid, gateway=FinalGateway())
        saved = await report(out)
        assert out["state"] == "completed" and saved["result"]["graph_artifact_id"] != before["graph_artifact_id"]

    async def test_c6_invalid_output_is_preserved_without_adoption():
        cid, rid, _, _ = await fixture()
        def bad(payload):
            obj = json.loads(payload["choices"][0]["message"]["content"])
            obj["conclusion"]["support_ids"] = ["S_NOT_SEEN"]
            payload["choices"][0]["message"]["content"] = json.dumps(obj)
        gateway = FinalGateway(mutate=bad)
        out = await service.finalize(T, cid, rid, gateway=gateway)
        assert out["state"] == "failed" and out["outcome"]["adoption"]["state"] == "not_eligible"
        assert (await report(out))["result"]["conclusion"] is None
        response = (await rows(select(F).where(F.c.run_id == rid, F.c.kind == "model_response", F.c.schema_version == contract.SCHEMA)))[0]
        assert response["content_json"]["payload"]["raw"] == gateway.last_payload

    async def test_c6_publication_commit_failure_is_atomic():
        cid, rid, _, _ = await fixture()
        original = BaselineStore.publish
        async def invalid_commit(store, case_id, run_id, pub, **kwargs):
            out = await original(store, case_id, run_id, pub, **kwargs)
            await store.db.execute(update(C).where(C.c.id == cid).values(current_assessment_id=uuid4()))
            return out
        with patch.object(BaselineStore, "publish", invalid_commit):
            try:
                await service.finalize(T, cid, rid, gateway=FinalGateway())
            except IntegrityError:
                pass
            else:
                raise AssertionError("deferred FK must roll back publication")
        assert not await rows(select(RESULT).where(RESULT.c.source_run_id == rid))
        assert not await rows(select(F).where(F.c.run_id == rid, F.c.kind.in_(["report_json", "report_markdown"])))
        assert (await rows(select(C).where(C.c.id == cid)))[0]["current_assessment_id"] is None
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "unknown"
        assert len(await rows(select(F).where(F.c.run_id == rid, F.c.kind == "model_response", F.c.schema_version == contract.SCHEMA))) == 1

    async def test_c6_request_commit_failure_does_not_dispatch():
        cid, rid, _, _ = await fixture()
        original = BaselineStore.save_input_artifact
        async def invalid_request(store, *args, **kwargs):
            if kwargs.get("kind") == "model_request" and kwargs.get("schema") == contract.SCHEMA:
                kwargs["actor_id"] = uuid4()
            return await original(store, *args, **kwargs)
        gateway = FinalGateway()
        with patch.object(BaselineStore, "save_input_artifact", invalid_request):
            try:
                await service.finalize(T, cid, rid, gateway=gateway)
            except IntegrityError:
                pass
            else:
                raise AssertionError("request commit should fail")
        assert gateway.calls == 0 and not await rows(select(RESULT).where(RESULT.c.source_run_id == rid))

    async def test_c6_cancel_unknown_and_tenant_isolation():
        cid, rid, _, _ = await fixture()
        await reject("case_not_found", service.finalize(OTHER, cid, rid, gateway=FinalGateway()))
        async def cancel():
            raise asyncio.CancelledError()
        gateway = FinalGateway(hook=cancel)
        try:
            await service.finalize(T, cid, rid, gateway=gateway)
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("cancel must propagate")
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "unknown"
        await reject("delivery_already_claimed", service.finalize(T, cid, rid, gateway=gateway))
        assert gateway.calls == 1 and not await rows(select(RESULT).where(RESULT.c.source_run_id == rid))

    async def test_c6_contract_scope_roles_comparison_and_report_schema():
        cid, rid, _, _ = await fixture()
        gateway = FinalGateway()
        out = await service.finalize(T, cid, rid, gateway=gateway)
        assert out["state"] == "completed", out
        saved, context = await report(out), await service.read_context(T, cid, rid)
        data = model_data(gateway.last_body["messages"][1]["content"])
        valid = json.loads(gateway.last_payload["choices"][0]["message"]["content"])
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", **contract.Delivery.model_json_schema()}
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(valid)
        mutations = [lambda v: v["conclusion"].update(state="supported"),
            lambda v: v["conclusion"].update(alert_ids=[str(uuid4())]),
            lambda v: v["comparison"].update(kind="revised", summary="invented previous result"),
            lambda v: v["recommendations"][0].update(object_keys=["outside:host"]),
            lambda v: v.update(delivery_state="complete"),
            lambda v: v["analysis"]["members"].clear(),
            lambda v: v["conclusion"].update(support_ids=["unseen"]),
            lambda v: v["conclusion"].update(text="   ")]
        prior = next(sid for sid, source in saved["source_map"].items() if source["ref"]["role"] == "prior_analysis")
        mutations.append(lambda v: v["impact"].update(alert_ids=list(data["members"]), support_ids=[prior], supported_changes=["unproven impact"]))
        for mutate in mutations:
            changed = copy.deepcopy(valid)
            mutate(changed)
            try:
                contract.parse(json.dumps(changed), saved["source_map"], context, data["members"], saved["comparison"])
            except AnalysisRejected:
                pass
            else:
                raise AssertionError("invalid final contract accepted")
        assert contract.citation_roles(saved) == {"$.delivery": "prior_analysis", "$.result": "prior_analysis"}
        duplicate = json.dumps(valid)[:-1] + ', "closing_note":"duplicate"}'
        try:
            contract.parse(duplicate, saved["source_map"], context, data["members"], saved["comparison"])
        except AnalysisRejected as exc:
            assert str(exc) == "duplicate_json_key"
        else:
            raise AssertionError("duplicate output keys accepted")
        # Source markup cannot create a link/image in the deterministic report.
        changed = copy.deepcopy(saved)
        changed["result"]["closing_note"] = '<img src="x"> ![x](https://example.invalid)'
        from app.socai2.baseline_delivery_projection import markdown
        rendered = markdown(changed)
        assert "<img" not in rendered and "![x](" not in rendered
        return {"rejected_contract_variants": len(mutations) + 1}

    async def test_c6_no_initial_analysis_and_unavailable_comparison():
        cid, rid, aids, host = await fixture(initial_gateway=c3.SyntheticGateway(enabled=False))
        gateway = FinalGateway()
        old = await service.finalize(T, cid, rid, gateway=gateway)
        assert old["reason"] == "no_accepted_main_analysis" and gateway.calls == 0
        cid, rid, _, _ = await fixture(prior_case=(cid, aids, host), comparison=UUID(old["outcome"]["result_id"]))
        out = await service.finalize(T, cid, rid, gateway=FinalGateway())
        saved = await report(out)
        assert out["state"] == "completed", out
        assert saved["comparison"]["state"] == "unavailable" and saved["result"]["change_kind"] == "not_comparable"
        assert not any(s["ref"]["type"] == "result" for s in saved["source_map"].values())

    async def test_c6_failed_unadopted_history_is_not_initial():
        cid, rid, aids, host = await fixture(initial_gateway=c3.SyntheticGateway(enabled=False))
        first = await service.finalize(T, cid, rid, gateway=FinalGateway())
        assert first["outcome"]["adoption"]["state"] == "not_eligible"
        cid, rid, _, _ = await fixture(prior_case=(cid, aids, host))
        context = await service.read_context(T, cid, rid)
        assert not context.prior_results
        out = await service.finalize(T, cid, rid, gateway=FinalGateway())
        saved = await report(out)
        assert out["state"] == "completed" and saved["comparison"]["state"] == "not_selected", out
        assert saved["result"]["change_kind"] == "not_comparable"

    checks = [test_c6_final_report_result_adoption_and_replay, test_c6_is_fourth_model_after_deep_without_extra_report_call,
        test_c6_exhaustion_and_unknown_usage_are_system_handoffs, test_c6_selected_comparison_has_frozen_old_scope_and_new_members,
        test_c6_unselected_history_does_not_claim_initial_comparison, test_c6_concurrent_owner_and_scope_change_prevent_stale_adoption,
        test_c6_rebuilds_stale_graph_before_claim, test_c6_invalid_output_is_preserved_without_adoption,
        test_c6_publication_commit_failure_is_atomic, test_c6_request_commit_failure_does_not_dispatch,
        test_c6_cancel_unknown_and_tenant_isolation, test_c6_contract_scope_roles_comparison_and_report_schema,
        test_c6_no_initial_analysis_and_unavailable_comparison, test_c6_failed_unadopted_history_is_not_initial]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 180)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- preserve original failures
            record(check.__name__, False, traceback.format_exc())
