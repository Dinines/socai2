"""Real PG synthetic C3 checks; all model responses are explicit substitutes."""
import asyncio
import copy
import json
import traceback
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import baseline_analysis as c3
from app.socai2 import baseline_analysis_contract as contract
from app.socai2.baseline_analysis_model import TenantChatGateway, usage
from app.socai2.baseline_contracts import Actor, Limits, Publication, Start
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import RM, A, C, F, R, StoreError, digest
from jsonschema import Draft202012Validator, FormatChecker
from socai2_test_model_view import model_data, model_messages_data
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic C3 reviewer")
CONTRACTS = json.loads((Path(__file__).parents[1] / "app/socai2/contracts.schema.json").read_text("utf-8"))


def reply_for(body):
    data = model_messages_data(body["messages"])
    ids = list(data["members"])
    own = {aid: next(i["id"] for i in data["items"] if aid in i["alert_ids"]) for aid in ids}
    findings = [{"id": f"F{i}", "state": "inferred", "statement": explanation,
        "alert_ids": [ids[0]], "support_ids": [own[ids[0]]], "counter_ids": [],
        "alternatives": ["另一解释尚需核实"], "limitations": ["仅合成材料示例"]}
        for i, explanation in enumerate(["可能是自动维护", "可能需要核对授权"], 1)]
    return {"summary": "synthetic initial analysis; not a final judgment",
        "members": [{"alert_id": aid, "state": "unresolved", "summary": "待原始材料补证",
            "evidence_ids": [own[aid]], "limitations": ["只有来源标签"]} for aid in ids],
        "findings": findings, "questions": [{"id": q["id"], "state": "unresolved", "answer": "待补查",
            "evidence_ids": [], "limitations": ["未取得直接观察"]} for q in data["questions"]],
        "domains": [{"name": name, "applicability": "applicable" if name == "identity" else "undetermined",
            "reason": "需要核对授权" if name == "identity" else "缺少此领域材料",
            "alert_ids": ids if name == "identity" else [], "finding_ids": ["F1", "F2"] if name == "identity" else [],
            "limitations": ["待补证"]} for name in contract.DOMAINS],
        "conflicts": [{"id": "X1", "finding_ids": ["F1", "F2"], "state": "unresolved",
            "explanation": "不能根据标签排除替代解释", "evidence_ids": []}],
        "followups": [{"question_id": data["questions"][0]["id"], "alert_ids": [ids[0]], "mode": "human",
            "objective": "确认行为用途", "required_evidence": "明确对象、时间和授权范围",
            "source_ids": [own[ids[0]]], "object_keys": [],
            **({"binding_id": None, "priority": "decision_critical"} if "tool_options" in data else {})}]}


class SyntheticGateway:
    provider, model = "synthetic", "synthetic-c3-no-network"

    def __init__(self, mutate=None, *, enabled=True, hook=None):
        self.mutate, self.enabled, self.hook = mutate, enabled, hook
        self.calls, self.configures, self.last_body, self.last_payload = 0, 0, None, None

    async def configure(self, service, tenant):
        assert tenant == T
        self.configures += 1
        return self.enabled

    async def complete(self, body, timeout):
        assert timeout > 0 and body["max_tokens"] == 3000 and "tools" not in body
        self.calls += 1
        self.last_body = copy.deepcopy(body)
        if self.hook:
            await self.hook()
        raw = reply_for(body)
        payload = {"id": "synthetic-response", "choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(raw, ensure_ascii=False)}}],
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

    async def make_alert(store, title="synthetic C3 alert", fields=None):
        aid, mid = uuid4(), uuid4()
        await store.db.execute(insert(A).values(id=aid, tenant_id=T, title=title,
            source_namespace="c3-test", source_identity_key=str(aid)))
        await store.db.execute(insert(m.AlertMaterials.__table__).values(id=mid, tenant_id=T,
            alert_id=aid, revision=1, raw_text="synthetic retained original", ocsf_json=fields, detection={},
            source_scope={}, material_state="complete", retention={}))
        await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        return aid

    async def fixture(calls=4, tokens=24000, deadline=120, materials=None):
        cid = uuid4()
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="synthetic C3 Case", created_by=USER))
            aids = [await make_alert(store, fields=fields) for fields in (materials or [None, None])]
            out = await store.replace_members(cid, set(aids), expected_revision=0, actor=ACTOR, operation_id=uuid4())
        rid = UUID(out["pending_run_id"])
        limits = Limits(max_model_calls=calls, max_tokens=tokens, max_tool_calls=0,
            max_rows_per_query=0, deadline_at=now + timedelta(seconds=deadline), policy_version="synthetic.c3.v1")
        async def idle(claim):
            pass
        await service.start(T, cid, rid, Start(expected_scope_revision=1, operation_key=uuid4()),
            actor=ACTOR, executor=idle, executor_version="synthetic.c3.v1", limits=limits)
        await service.enrich(T, cid, rid)  # No objects and zero Tool budget: no source queries.
        return cid, rid, aids

    async def reject(code, task):
        try:
            await task
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected " + code)

    async def artifacts(rid, kind=None):
        statement = select(F).where(F.c.run_id == rid, F.c.schema_version == c3.SCHEMA)
        return await rows(statement.where(F.c.kind == kind) if kind else statement)

    def publication(ctx, refs=None):
        return Publication.model_validate({"operation_key": uuid4(), "terminal_state": "failed",
            "stop_reason": "synthetic-test-close", "title": "synthetic handoff", "conclusion": None,
            "conclusion_state": "unavailable", "conclusion_origin": "system", "validation_state": "system_only",
            "closing_note": "synthetic", "findings": [], "questions": [], "recommendations": [],
            "change_kind": "initial", "change_summary": None, "case_impact": {"summary": None,
            "supported_changes": [], "cannot_generalize": [], "affected_scope": ctx.scope.model_dump(mode="json"),
            "next_steps": []}, "delivery_state": "partial", "members": [{"alert_id": aid,
            "read_state": "not_read", "assessment_state": "unresolved", "conclusion_covered": False,
            "assessment": None, "limitations": "synthetic", "evidence_refs": refs or []} for aid in ctx.alerts]})

    async def test_c3_same_run_artifacts_and_usage():
        cid, rid, aids = await fixture()
        gateway = SyntheticGateway()
        result = await service.analyze(T, cid, rid, gateway=gateway)
        assert result["state"] == "completed" and set(result["domain_artifact_ids"]) == set(contract.DOMAINS)
        assert len(result["analysis"]["questions"]) == 6
        assert gateway.calls == 1 and len(result["analysis"]["conflicts"]) == 1
        items = await artifacts(rid)
        assert len(items) == 7  # request + response + four domain blocks + main snapshot
        for item in items:
            assert digest(item["content_json"]) == item["sha256"] and item["case_id"] == cid
            kind = "model_exchange" if item["kind"] in {"model_request", "model_response"} else "analysis_block" if item["kind"] == "domain_analysis" else None
            if kind:
                Draft202012Validator({"$ref": "#/$defs/" + kind, "$defs": CONTRACTS["$defs"]},
                    format_checker=FormatChecker()).validate(item["content_json"])
        request = (await artifacts(rid, "model_request"))[0]["content_json"]
        assert request["payload"]["body"] == gateway.last_body
        response = (await artifacts(rid, "model_response"))[0]["content_json"]
        assert response["payload"]["raw"] == gateway.last_payload
        assert response["usage"]["total_tokens"] == 1000 and response["usage"]["cost"] is None
        assert response["usage"]["cost_state"] == "unpriced"
        assert (await rows(select(R.c.state).where(R.c.id == rid)))[0]["state"] == "running"
        assert (await rows(select(C.c.current_assessment_id).where(C.c.id == cid)))[0]["current_assessment_id"] is None
        members = await rows(select(RM).where(RM.c.run_id == rid))
        assert {m["alert_id"] for m in members} == set(aids)
        assert all(m["read_state"] == "not_read" and m["analysis_state"] == "unresolved" for m in members)
        assert all(s["usage"] is None for s in await rows(select(c3.S).where(c3.S.c.run_id == rid, c3.S.c.kind == "stage")))

    async def test_c3_concurrent_replay_freeze_and_publication():
        cid, rid, aids = await fixture()
        entered, release = asyncio.Event(), asyncio.Event()
        async def hold():
            steps = await rows(select(c3.S).where(c3.S.c.run_id == rid, c3.S.c.kind == "model"))
            assert len(steps) == 1 and steps[0]["state"] == "running" and steps[0]["input_artifact_id"]
            entered.set()
            await release.wait()
        gateway = SyntheticGateway(hook=hold)
        task = asyncio.create_task(service.analyze(T, cid, rid, gateway=gateway))
        try:
            await asyncio.wait_for(entered.wait(), 15)
            await reject("analysis_already_claimed", service.analyze(T, cid, rid, gateway=gateway))
            ctx = await service.read_context(T, cid, rid)
            await reject("baseline_steps_not_settled", service.publish(T, cid, rid, publication(ctx)))
            async with service.transaction(T) as store:
                extra = await make_alert(store, "added after claim")
            changed = await service.replace_members(T, cid, aids + [extra], expected_revision=1,
                actor=ACTOR, operation_id=uuid4())
            assert changed["pending_run_id"] != str(rid)
        finally:
            release.set()
        result = await task
        assert {m["alert_id"] for m in result["analysis"]["members"]} == set(map(str, aids))
        assert result == await service.analyze(T, cid, rid, gateway=gateway)
        assert gateway.calls == 1 and gateway.configures == 1

    async def test_c3_invalid_output_kept_without_adoption():
        cid, rid, _ = await fixture()
        def mutate(payload):
            raw = json.loads(payload["choices"][0]["message"]["content"])
            raw["members"][0]["evidence_ids"] = ["not-visible"]
            payload["choices"][0]["message"]["content"] = json.dumps(raw)
        gateway = SyntheticGateway(mutate)
        out = await service.analyze(T, cid, rid, gateway=gateway)
        assert out["state"] == "failed" and out["reason"] == "source_not_in_model_input"
        assert out["analysis"] is None and not out["domain_artifact_ids"]
        assert (await artifacts(rid, "model_response"))[0]["content_json"]["payload"]["raw"] == gateway.last_payload
        assert out == await service.analyze(T, cid, rid, gateway=gateway) and gateway.calls == 1
        assert all(m["analysis_state"] == "not_analyzed" for m in await rows(select(RM).where(RM.c.run_id == rid)))

    async def test_c3_contract_rejects_scope_role_and_coverage_errors():
        cid, rid, _ = await fixture()
        gateway = SyntheticGateway()
        result = await service.analyze(T, cid, rid, gateway=gateway)
        ctx = await service.read_context(T, cid, rid)
        prepared = await service.prepare_model_view(T, cid, rid)
        raw = copy.deepcopy(result["analysis"])
        source_map = result["source_map"]
        mutations = [
            (lambda v: v["members"].pop(), "member_delivery_incomplete"),
            (lambda v: v["members"].append(v["members"][0]), "duplicate_member_delivery"),
            (lambda v: v["members"][0].update(evidence_ids=v["members"][1]["evidence_ids"]), "source_member_mismatch"),
            (lambda v: v["findings"][0].update(state="observed"), "non_observation_promoted_to_observed"),
            (lambda v: v["findings"][0].update(alert_ids=[str(uuid4())]), "member_outside_run"),
            (lambda v: v["findings"][0].update(counter_ids=v["findings"][0]["support_ids"]), "same_source_as_support_and_counterevidence"),
            (lambda v: v["questions"][0].update(state="answered"), "answered_question_needs_sources"),
            (lambda v: v["questions"][0].update(id="outside"), "question_coverage_incomplete"),
            (lambda v: v["domains"][1].update(name="identity"), "duplicate_domain"),
            (lambda v: v["conflicts"][0].update(state="resolved"), "resolved_conflict_needs_sources"),
            (lambda v: v["followups"][0].update(object_keys=["outside"]), "followup_objects_outside_run"),
            (lambda v: v["domains"][0].update(finding_ids=["missing"]), "unknown_domain_finding"),
        ]
        for mutate, code in mutations:
            value = copy.deepcopy(raw)
            mutate(value)
            try:
                contract.parse(json.dumps(value), source_map, ctx, prepared["coverage"])
            except contract.AnalysisRejected as exc:
                assert str(exc) == code, (str(exc), code)
            else:
                raise AssertionError(code)
        for content in ['{"summary":"a","summary":"b"}', '{"summary":NaN}', '{"summary":']:
            try:
                contract.parse(content, source_map, ctx, prepared["coverage"])
            except contract.AnalysisRejected:
                pass
            else:
                raise AssertionError("invalid JSON accepted")
        return {"invalid_variants": len(mutations) + 3}

    async def test_c3_limits_and_missing_config():
        for calls, tokens, deadline, enabled, expected in [
            (0, 24000, 120, True, "model_call_budget_exhausted"),
            (4, 100, 120, True, "model_token_budget_insufficient"),
            (4, 24000, -1, True, "deadline_reached"),
            (4, 24000, 120, False, "model_not_configured")]:
            cid, rid, _ = await fixture(calls=calls, tokens=tokens, deadline=deadline)
            gateway = SyntheticGateway(enabled=enabled)
            out = await service.analyze(T, cid, rid, gateway=gateway)
            assert out["state"] == "skipped" and out["reason"] == expected
            assert gateway.calls == 0 and not await artifacts(rid, "model_request")

    async def test_c3_prior_unknown_usage_blocks_dispatch():
        cid, rid, _ = await fixture()
        async with service.transaction(T) as store:
            now = await store.now()
            seq = await c3.BaselineAnalysis(service).next_seq(store, rid)
            await store.db.execute(insert(c3.S).values(id=uuid4(), tenant_id=T, run_id=rid,
                seq=seq, kind="model", stage_code="C2", state="failed", name="synthetic_prior",
                started_at=now, ended_at=now, usage=usage({})))
        gateway = SyntheticGateway()
        out = await service.analyze(T, cid, rid, gateway=gateway)
        assert out["reason"] == "prior_model_usage_unknown" and gateway.calls == 0

    async def test_c3_partial_usage_and_truncated_response():
        for mutate, expected in [
            (lambda p: p.update(usage={"prompt_tokens": 5}), "model_usage_unknown_or_inconsistent"),
            (lambda p: p["choices"][0].update(finish_reason="length"), "model_response_not_complete")]:
            cid, rid, _ = await fixture()
            gateway = SyntheticGateway(mutate)
            out = await service.analyze(T, cid, rid, gateway=gateway)
            assert out["state"] == "failed" and out["reason"] == expected and not out["analysis"]
            assert (await artifacts(rid, "model_response"))[0]["content_json"]["payload"]["raw"] == gateway.last_payload
        assert usage({"usage": {"prompt_tokens": True, "completion_tokens": 0}})["input_tokens"] is None
        assert usage({"usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 99}})["usage_state"] == "partial"

    async def test_c3_cancel_unknown_and_tenant_isolation():
        cid, rid, _ = await fixture()
        gateway = SyntheticGateway()
        await reject("case_not_found", service.analyze(OTHER, cid, rid, gateway=gateway))
        assert gateway.calls == 0 and gateway.configures == 0
        async def cancelled():
            raise asyncio.CancelledError
        gateway.hook = cancelled
        try:
            await service.analyze(T, cid, rid, gateway=gateway)
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("cancellation hidden")
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "unknown"
        uncertain = await rows(select(c3.S).where(c3.S.c.run_id == rid, c3.S.c.state == "unknown"))
        assert uncertain and all(row["error"]["message"] == "model_dispatch:CancelledError" for row in uncertain)
        await reject("analysis_already_claimed", service.analyze(T, cid, rid, gateway=gateway))
        assert gateway.calls == 1

    async def test_c3_guard_and_prior_analysis_citations():
        cid, rid, _ = await fixture()
        gateway = SyntheticGateway()
        with patch.object(contract, "PROMPT", "x" * 13000):
            out = await service.analyze(T, cid, rid, gateway=gateway)
        assert out["reason"] == "analysis_input_contract_or_size" and gateway.calls == 0
        cid, rid, _ = await fixture()
        await service.analyze(T, cid, rid, gateway=SyntheticGateway())
        main = (await artifacts(rid, "source_snapshot"))[0]
        ctx = await service.read_context(T, cid, rid)
        ref = {"type": "artifact", "id": str(main["id"]), "external": None,
               "source_path": "$.analysis", "row_keys": [], "role": "observation"}
        await reject("context_citation_path_or_role_invalid", service.publish(T, cid, rid, publication(ctx, [ref])))
        ref["role"] = "prior_analysis"
        outcome = await service.publish(T, cid, rid, publication(ctx, [ref]))
        assert outcome["adoption"]["state"] == "not_eligible"

    async def test_c3_model_adapter_uses_existing_guarded_transport():
        gateway = TenantChatGateway()
        from app.services.llm_resolver import LlmConfig
        gateway.config = LlmConfig(True, "https://model.invalid/v1", "synthetic", "fixture-not-a-real-key", "tenant", "")
        seen = []
        async def no_network(**kwargs):
            seen.append(kwargs)
            return {"synthetic": True}
        body = {"model": "synthetic", "messages": [{"role": "user", "content": "synthetic"}],
            "max_tokens": 3000, "response_format": {"type": "json_object"}}
        with patch("app.socai2.baseline_analysis_model.safe_chat_completions_request", no_network):
            await gateway.complete(body, 5)
            try:
                await gateway.complete(body, 0)
            except TimeoutError:
                pass
            else:
                raise AssertionError("expired transport was dispatched")
        assert len(seen) == 1 and seen[0]["timeout"] == 5 and seen[0]["messages"] == body["messages"]
        assert "api_key" not in body and "api_key" in seen[0]

    async def test_c3_request_commit_failure_does_not_dispatch():
        cid, rid, _ = await fixture()
        gateway = SyntheticGateway()
        original = c3.BaselineAnalysis.artifact
        inserted_before_commit = []
        async def deferred_failure(self, store, run, step, payload, kind, refs):
            identity = await original(self, store, run, step, payload, kind, refs)
            if kind == "model_request":
                # Genuine deferred FK failure on COMMIT, not a failed model mock.
                await store.db.execute(insert(c3.S).values(id=uuid4(), tenant_id=T, run_id=rid,
                    seq=10000000, parent_step_id=uuid4(), kind="model", stage_code="C3",
                    state="planned", name="synthetic_deferred_fk_failure"))
                inserted_before_commit.append(True)
            return identity
        with patch.object(c3.BaselineAnalysis, "artifact", deferred_failure):
            try:
                await service.analyze(T, cid, rid, gateway=gateway)
            except IntegrityError as exc:
                constraint = getattr(exc.orig.__cause__, "constraint_name", None)
                assert constraint in {"run_steps_parent_step_id_fk", "run_steps_parent_step_id_scope_fk"}, constraint
            else:
                raise AssertionError("deferred commit should fail")
        assert inserted_before_commit == [True]
        assert gateway.calls == 0 and not await artifacts(rid, "model_request")
        assert not await rows(select(c3.S).where(c3.S.c.run_id == rid, c3.S.c.kind == "model"))
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "unknown"

    async def test_c3_refusal_or_unoffered_function_is_not_analysis():
        for field, value in [("refusal", "synthetic refusal"),
                             ("function_call", {"name": "not_offered", "arguments": "{}"})]:
            cid, rid, _ = await fixture()
            def mutate(payload, field=field, value=value):
                payload["choices"][0]["message"][field] = value
            gateway = SyntheticGateway(mutate)
            out = await service.analyze(T, cid, rid, gateway=gateway)
            assert out["reason"] == "model_content_or_tool_protocol_invalid" and out["analysis"] is None
            assert (await artifacts(rid, "model_response"))[0]["content_json"]["payload"]["raw"] == gateway.last_payload

    async def test_c3_frozen_semantics_visible_before_followup():
        cid, rid, aids = await fixture(materials=[
            {"class_uid": 1007, "process": {"pid": 41, "cmd_line": "inventory --read-only"},
             "user": {"name": "operator-one"}, "device": {"hostname": "host-one"}},
            {"class_uid": 4001, "src_endpoint": {"ip": "192.0.2.9", "port": 40001},
             "dst_endpoint": {"ip": "198.51.100.9", "port": 443}, "network": {"protocol_name": "tcp"}}])
        async with service.transaction(T) as store:
            new_mid = uuid4()
            await store.db.execute(insert(m.AlertMaterials).values(id=new_mid, tenant_id=T, alert_id=aids[0],
                revision=2, ocsf_json={"process": {"cmd_line": "newer-unfrozen-command"}},
                detection={}, source_scope={}, retention={}, material_state="complete"))
            await store.db.execute(update(A).where(A.c.id == aids[0]).values(latest_material_id=new_mid))
        gateway = SyntheticGateway()
        result = await service.analyze(T, cid, rid, gateway=gateway)
        assert result["state"] == "completed", result
        request = (await artifacts(rid, "model_request"))[0]["content_json"]["payload"]
        data = model_data(gateway.last_body["messages"][1]["content"])
        direct = [item for item in data["items"] if item["role"] == "observation"]
        for value in ({"process_command_line": "inventory --read-only"}, {"dest_ip": "198.51.100.9"}, {"dst_port": 443}):
            assert value in [item["value"] for item in direct]
        assert "newer-unfrozen-command" not in gateway.last_body["messages"][1]["content"]
        context = await service.read_context(T, cid, rid)
        for item in direct:
            ref = request["source_map"][item["id"]]["ref"]
            assert ref["type"] == "alert_material" and ref["source_path"].startswith("$.ocsf_json.")
            assert c3.source_members(context, ref, {}) == item["alert_ids"]
            assert str(new_mid) != str(ref["id"])
        assert all(row["read_state"] == "read" for row in await rows(select(RM).where(RM.c.run_id == rid)))
        assert not await rows(select(c3.S).where(c3.S.c.run_id == rid, c3.S.c.stage_code == "C4.materials"))
        assert len(gateway.last_body["messages"][1]["content"].encode()) <= 8192
        assert len(json.dumps(gateway.last_body["messages"], ensure_ascii=False, separators=(",", ":")).encode()) <= 12288
        return {"visible_observation_count": len(direct), "frozen_materials_only": True, "model_substitute": True}

    checks = [test_c3_frozen_semantics_visible_before_followup,
        test_c3_same_run_artifacts_and_usage, test_c3_concurrent_replay_freeze_and_publication,
        test_c3_invalid_output_kept_without_adoption, test_c3_contract_rejects_scope_role_and_coverage_errors,
        test_c3_limits_and_missing_config, test_c3_prior_unknown_usage_blocks_dispatch,
        test_c3_partial_usage_and_truncated_response, test_c3_cancel_unknown_and_tenant_isolation,
        test_c3_guard_and_prior_analysis_citations, test_c3_model_adapter_uses_existing_guarded_transport,
        test_c3_request_commit_failure_does_not_dispatch, test_c3_refusal_or_unoffered_function_is_not_analysis]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 100)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- retain each original independent failure
            record(check.__name__, False, traceback.format_exc())
