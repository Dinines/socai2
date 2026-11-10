"""I executor, real frozen-input SQL in existing synthetic PG, model substitute."""
import asyncio
import copy
import json
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4

import jsonschema
from app.models import socai2 as m
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_enrichment import S
from app.socai2.baseline_store import StoreError, encoded
from app.socai2.incident_diagnosis_contract import build, parse
from app.socai2.runtime_policy import draft_limit
from app.socai2.stage_reader import StageReadService
from app.socai2.stage_result_contracts import INCIDENT_EXECUTOR_VERSION, AlertOutput
from app.socai2.stage_results import AS, A, D, F, I, R, StageResultService
from socai2_test_model_view import model_data
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
LIMITS = Limits(max_model_calls=0, max_tokens=0, max_tool_calls=0, max_rows_per_query=0,
                deadline_at=None, policy_version="synthetic.storage")


def validate_diagnosis_contract(value):
    schema = json.loads((Path(__file__).resolve().parents[1] / "app/socai2/contracts.schema.json").read_text())
    jsonschema.validate(value, {"$defs": schema["$defs"], "$ref": "#/$defs/diagnosis"})


class Gateway:
    provider, model = "synthetic", "synthetic-incident-model"

    def __init__(self, transform=None, *, wait=False, configured=True):
        self.transform, self.configured = transform, configured
        self.calls, self.requests, self.responses = 0, [], []
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        if not wait:
            self.release.set()

    async def configure(self, *_):
        return self.configured

    async def measure(self, body, stage):
        from socai2_test_model_view import synthetic_measure
        return await synthetic_measure(body, stage)

    async def complete(self, body, timeout):
        assert timeout > 0
        self.calls += 1
        self.requests.append(copy.deepcopy(body))
        self.entered.set()
        await self.release.wait()
        data = model_data(body["messages"][1]["content"])
        by_member = {m["alert_id"]: [x["id"] for x in data["items"] if m["alert_id"] in x["alert_ids"]]
                     for m in data["members"]}
        ids = [v[0] for v in by_member.values() if v]
        answer = {"summary": "synthetic member aggregation", "conclusion": "synthetic relation remains unresolved",
            "evidence_ids": ids,
            "members": [{"alert_id": aid, "state": "unresolved" if values else "not_reviewed",
                "assessment": "synthetic authorization unresolved", "source_ids": values[:2], "limitations": ["synthetic"]}
                for aid, values in by_member.items()],
            "findings": [{"id": "F1", "statement": "synthetic shared background, causality unproven", "state": "inferred",
                "alert_ids": list(by_member), "source_ids": ids, "limitations": ["not causal proof"]}] if all(by_member.values()) else [],
            "open_questions": [{"text": "synthetic authorization question", "alert_ids": list(by_member),
                "source_ids": ids, "evidence_requirements": ["human confirmation"]}], "limitations": ["synthetic only"]}
        payload = {"id": "synthetic-incident-request", "choices": [{"finish_reason": "stop",
            "message": {"content": json.dumps(answer)}}], "usage": {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200}}
        if self.transform:
            payload = self.transform(payload, data)
        self.responses.append(copy.deepcopy(payload))
        return payload


async def run_checks(engine, record, only=None):
    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))
    reader = StageReadService(service.sessions)

    async def rows(table, condition):
        async with service.transaction(T, readonly=True) as s:
            return [dict(r) for r in (await s.db.execute(select(table).where(*s.where(table, condition)))).mappings()]

    async def fixture(n=2):
        iid, aids, mids = uuid4(), [uuid4() for _ in range(n)], [uuid4() for _ in range(n)]
        async with service.transaction(T) as s:
            await s.db.execute(insert(I).values(id=iid, tenant_id=T, source_namespace="synthetic.i",
                source_incident_id=str(iid), title="synthetic incident", handling_status="new"))
            now = await s.now()
            for aid, mid in zip(aids, mids):
                await s.db.execute(insert(A).values(id=aid, tenant_id=T, source_namespace="synthetic.i",
                    source_identity_key=str(aid), title="synthetic member", event_time=now, event_time_source="source",
                    handling_status="completed", disposition="benign"))
                await s.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=T, alert_id=aid, revision=1,
                    raw_json={"process": {"pid": 42, "argv": ["synthetic.exe"]}}, detection={"rule_id": "synthetic"},
                    source_scope={}, retention={}, material_state="complete"))
                await s.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
                await s.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=T, incident_id=iid, alert_id=aid,
                    membership_source="fusion", correlation_basis={"reason": "synthetic shared host"},
                    basis_version="synthetic", source_operation_id=uuid4()))
        for aid, mid in zip(aids, mids):
            claim = await service.begin(T, "alert_basic", aid, uuid4(), producer="synthetic.triage", limits=LIMITS)
            out = AlertOutput(verdict="needs_review", rationale="paired-triage-" + str(aid), confidence=.4,
                score_state="available", explanation="synthetic explanation", generation_method="template",
                source_refs=[{"type": "alert_material", "id": mid, "external": None, "source_path": "$.raw_json.process.pid",
                    "row_keys": [], "role": "observation"}], recommendations=[], limitations=["synthetic"])
            await service.finish(T, claim["run_id"], out)
        return iid, aids, mids

    async def test_incident_frozen_valid_triage_and_delivery():
        iid, aids, _ = await fixture()
        before = [await rows(A, A.c.id == aid) for aid in aids]
        gateway = Gateway()
        out = await service.execute_incident(T, iid, uuid4(), gateway=gateway)
        assert out["state"] == "completed" and gateway.calls == 1
        frozen = (await rows(F, F.c.id == out["input_artifact_id"]))[0]["content_json"]
        assert len(frozen["members"]) == 2 and all(v["usable"] and v["freshness"] == "current" for v in frozen["triage_validation"].values())
        data = model_data(gateway.requests[0]["messages"][1]["content"])
        assert {m["alert_id"] for m in data["members"]} == set(map(str, aids))
        assert all(m["triage_eligible"] and m["triage_visibility"] == "included" for m in data["members"])
        assert len([v for v in data["items"] if v["role"] == "prior_analysis"]) == 2
        artifacts = await rows(F, F.c.run_id == out["run_id"])
        request = next(r["content_json"] for r in artifacts if r["kind"] == "model_request")
        response = next(r["content_json"] for r in artifacts if r["kind"] == "model_response")
        assert request["body"] == gateway.requests[0] and response["raw"] == gateway.responses[0]
        assert response["usage"]["total_tokens"] == 200 and len(response["validated_members"]) == 2
        diagnosis = (await rows(D, D.c.id == out["diagnosis_id"]))[0]
        assert diagnosis["state"] == "completed" and len(diagnosis["diagnosis"]["findings"]) == 3
        assert diagnosis["open_questions"][0]["state"] == "open"
        assert diagnosis["diagnosis"]["program_facts"] == data["program_facts"]
        validate_diagnosis_contract(diagnosis["diagnosis"])
        assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] == out["diagnosis_id"]
        assert before == [await rows(A, A.c.id == aid) for aid in aids]
        steps = await rows(S, S.c.run_id == out["run_id"])
        assert len(steps) == 2 and {s["kind"] for s in steps} == {"stage", "model"} and all(s["state"] == "completed" for s in steps)
        assert await service.freshness(T, out["run_id"])
        assert (await reader.read_page(T, "incident_diagnosis", iid)).current.valid_for_current_input
        return {"run_id": str(out["run_id"]), "members": 2, "model_calls": 1, "external_queries": 0}

    async def test_incident_stale_legacy_triage_excluded():
        iid, aids, mids = await fixture(3)
        async with service.transaction(T) as s:
            await s.db.execute(update(A).where(A.c.id == aids[1]).values(description="new material context"))
            tid, now = uuid4(), await s.now()
            await s.db.execute(insert(AS).values(id=tid, tenant_id=T, alert_id=aids[2], input_material_id=mids[2], kind="triage",
                verdict="needs_review", rationale="legacy-triage-must-not-enter-model", score_state="not_provided", producer="legacy",
                actor={}, assessed_at=now, operation_key=str(tid)))
            await s.db.execute(update(A).where(A.c.id == aids[2]).values(latest_triage_id=tid))
        gateway = Gateway()
        out = await service.execute_incident(T, iid, uuid4(), gateway=gateway)
        assert out["state"] == "completed"
        frozen = (await rows(F, F.c.id == out["input_artifact_id"]))[0]["content_json"]
        status = frozen["triage_validation"]
        assert status[str(aids[0])]["usable"]
        assert status[str(aids[1])]["freshness"] == "stale" and not status[str(aids[1])]["usable"]
        assert status[str(aids[2])]["freshness"] == "unavailable" and not status[str(aids[2])]["usable"]
        prompt = gateway.requests[0]["messages"][1]["content"]
        assert "paired-triage-" + str(aids[0]) in prompt
        assert "paired-triage-" + str(aids[1]) not in prompt and "legacy-triage-must-not-enter-model" not in prompt
        assert any(m["triage"]["rationale"] == "legacy-triage-must-not-enter-model" for m in frozen["members"])

    async def test_incident_replay_and_membership_change():
        iid, aids, _ = await fixture()
        gateway, op = Gateway(wait=True), uuid4()
        task = asyncio.create_task(service.execute_incident(T, iid, op, gateway=gateway))
        try:
            await asyncio.wait_for(gateway.entered.wait(), 25)
            other = Gateway()
            replay = await service.execute_incident(T, iid, op, gateway=other)
            assert replay["state"] == "running" and not replay["newly_claimed"] and other.calls == 0
            async with service.transaction(T) as s:
                await s.one(select(I).where(I.c.id == iid).with_for_update())
                await s.db.execute(delete(m.IncidentAlerts).where(m.IncidentAlerts.incident_id == iid, m.IncidentAlerts.alert_id == aids[1]))
            gateway.release.set()
            out = await task
            assert out["state"] == "completed" and not await service.freshness(T, out["run_id"])
            assert (await rows(R, R.c.id == out["run_id"]))[0]["delivery_state"] == "complete"
            assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] is None
            replay = await service.execute_incident(T, iid, op, gateway=other)
            assert replay["run_id"] == out["run_id"] and other.calls == 0
            diagnosis = (await rows(D, D.c.id == out["diagnosis_id"]))[0]
            assert len([f for f in diagnosis["diagnosis"]["findings"] if f["id"].startswith("member:")]) == 2
            assert diagnosis["diagnosis"]["delivery_assessment"]["state"] == "complete"
        finally:
            gateway.release.set()
            await task

    async def test_incident_invalid_coverage_and_wrong_member():
        iid, _, _ = await fixture()
        good = await service.execute_incident(T, iid, uuid4(), gateway=Gateway())
        def change(mode):
            def transform(p, data):
                answer = json.loads(p["choices"][0]["message"]["content"])
                if mode == "missing":
                    answer["members"].pop()
                elif mode == "wrong_member":
                    answer["members"][0]["source_ids"] = answer["members"][1]["source_ids"]
                else:
                    p.pop("usage")
                p["choices"][0]["message"]["content"] = json.dumps(answer)
                return p
            return transform
        for mode in ("missing", "wrong_member", "usage"):
            gateway = Gateway(change(mode))
            out = await service.execute_incident(T, iid, uuid4(), gateway=gateway)
            assert out["state"] == "failed" and gateway.calls == 1
            diagnosis = (await rows(D, D.c.id == out["diagnosis_id"]))[0]
            assert diagnosis["state"] == "failed"
            if mode == "wrong_member":
                assert diagnosis["diagnosis"]["validation_state"] == "partial"
                assert diagnosis["diagnosis"]["conclusion"] is None
            else:
                assert diagnosis["diagnosis"] is None
            assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] == good["diagnosis_id"]
            artifacts = await rows(F, F.c.run_id == out["run_id"])
            response = next(r["content_json"] for r in artifacts if r["kind"] == "model_response")
            assert response["raw"] == gateway.responses[0] and response["validation_error"]
            if mode == "usage":
                assert response["usage"]["total_tokens"] is None

    async def test_incident_disabled_and_unknown_no_retry():
        iid, _, _ = await fixture()
        gateway = Gateway(configured=False)
        out = await service.execute_incident(T, iid, uuid4(), gateway=gateway)
        assert out["state"] == "failed" and gateway.calls == 0
        assert (await rows(D, D.c.id == out["diagnosis_id"]))[0]["state"] == "failed"
        def timeout(*_):
            raise TimeoutError("synthetic transport uncertainty")
        gateway, op = Gateway(timeout), uuid4()
        try:
            await service.execute_incident(T, iid, op, gateway=gateway)
        except TimeoutError:
            pass
        else:
            raise AssertionError("expected timeout")
        out = await service.execute_incident(T, iid, op, gateway=gateway)
        assert out["state"] == "unknown" and gateway.calls == 1
        assert (await rows(D, D.c.id == out["diagnosis_id"]))[0]["state"] == "unknown"

    async def test_incident_request_commit_before_dispatch():
        iid, _, _ = await fixture()
        class Failing(StageResultService):
            injected = False
            @asynccontextmanager
            async def transaction(self, tenant, **kwargs):
                async with super().transaction(tenant, **kwargs) as s:
                    yield s
                    if not kwargs.get("readonly") and not self.injected:
                        step = await s.one(select(S).join(R, R.c.id == S.c.run_id).where(
                            R.c.incident_id == iid, S.c.kind == "model", S.c.state == "running"))
                        if step:
                            self.injected = True
                            await s.db.execute(update(S).where(S.c.id == step["id"]).values(parent_step_id=uuid4()))
        failing, gateway, op = Failing(service.sessions), Gateway(), uuid4()
        try:
            await failing.execute_incident(T, iid, op, gateway=gateway)
        except DBAPIError:
            pass
        else:
            raise AssertionError("expected failed commit")
        out = await failing.execute_incident(T, iid, op, gateway=gateway)
        assert gateway.calls == 0 and out["state"] == "unknown"
        assert not [r for r in await rows(F, F.c.run_id == out["run_id"]) if r["kind"] == "model_request"]

    async def test_incident_publication_is_atomic():
        iid, _, _ = await fixture()
        class Failing(StageResultService):
            publishing = False
            async def finish(self, *args, **kwargs):
                self.publishing = True
                try:
                    return await super().finish(*args, **kwargs)
                finally:
                    self.publishing = False
            @asynccontextmanager
            async def transaction(self, tenant, **kwargs):
                async with super().transaction(tenant, **kwargs) as s:
                    yield s
                    if self.publishing:
                        await s.db.execute(update(I).where(I.c.id == iid).values(latest_diagnosis_id=uuid4()))
        failing, gateway, op = Failing(service.sessions), Gateway(), uuid4()
        try:
            await failing.execute_incident(T, iid, op, gateway=gateway)
        except DBAPIError:
            pass
        else:
            raise AssertionError("expected failed publication")
        out = await failing.execute_incident(T, iid, op, gateway=gateway)
        assert out["state"] == "unknown" and gateway.calls == 1
        diagnosis = (await rows(D, D.c.id == out["diagnosis_id"]))[0]
        assert (await rows(R, R.c.id == out["run_id"]))[0]["delivery_state"] == "none"
        assert diagnosis["state"] == "unknown" and diagnosis["diagnosis"] is None
        assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] is None
        assert len([r for r in await rows(F, F.c.run_id == out["run_id"]) if r["kind"] == "model_response"]) == 1

    async def test_incident_case_freshness_and_frozen_history():
        iid, aids, _ = await fixture()
        out = await service.execute_incident(T, iid, uuid4(), gateway=Gateway())
        async def freeze():
            cid = uuid4()
            actor = Actor(user_id=USER, name="synthetic I bridge")
            async with service.transaction(T) as s:
                await s.db.execute(insert(m.Cases).values(id=cid, tenant_id=T, title="synthetic incident bridge"))
            changed = await service.replace_members(T, cid, aids, expected_revision=0, actor=actor, operation_id=uuid4())
            rid = UUID(changed["pending_run_id"])
            async def nop(_):
                pass
            await service.start(T, cid, rid, Start(expected_scope_revision=1, operation_key=uuid4()),
                actor=actor, executor=nop, executor_version="synthetic.no-execution", limits=LIMITS)
            ctx = await service.read_context(T, cid, rid)
            async with service.transaction(T) as s:
                await s.mark_unknown(cid, rid)
            return cid, rid, ctx
        cid, rid, first = await freeze()
        assert first.incidents[str(iid)].diagnosis_usable and first.incidents[str(iid)].diagnosis_freshness == "current"
        async with service.transaction(T) as s:
            await s.db.execute(update(A).where(A.c.id == aids[0]).values(description="changed after I completion"))
        _, _, second = await freeze()
        assert not second.incidents[str(iid)].diagnosis_usable and second.incidents[str(iid)].diagnosis_freshness == "stale"
        assert (await service.read_context(T, cid, rid)).model_dump() == first.model_dump()
        assert not (await reader.read_entry(T, "incident_diagnosis", iid, out["run_id"])).valid_for_current_input

    async def test_incident_view_budget_roles_and_tenant():
        iid, _, _ = await fixture()
        claim = await service.begin(T, "incident_diagnosis", iid, uuid4(), producer=INCIDENT_EXECUTOR_VERSION, limits=None)
        frozen = (await rows(F, F.c.id == claim["input_artifact_id"]))[0]["content_json"]
        material = frozen["members"][0]["material"]
        material["raw_json"].update({"big": "x"*5000, "-----BEGIN PRIVATE KEY-----": "synthetic", "invalid.path": "synthetic"})
        messages, mapping, data = build(frozen, claim["input_artifact_id"])
        assert len(encoded(data)) <= draft_limit() and len(encoded(messages)) <= draft_limit()
        assert data["omissions"]["input_guard"] and data["omissions"]["field_size"] and data["omissions"]["unaddressable_source_path"]
        assert "PRIVATE KEY" not in str(messages)
        stub = Gateway()
        p = await stub.complete({"messages": messages}, 1)
        parse(p["choices"][0]["message"]["content"], mapping, data)
        huge = copy.deepcopy(frozen)
        huge["members"] = []
        for _ in range(200):
            member = copy.deepcopy(frozen["members"][0])
            member["alert"]["id"] = str(uuid4())
            huge["members"].append(member)
        try:
            build(huge, claim["input_artifact_id"])
        except StoreError as exc:
            assert exc.code == "incident_member_directory_too_large"
        else:
            raise AssertionError("silently reduced member scope")
        try:
            await service.execute_incident(OTHER, iid, uuid4(), gateway=Gateway())
        except StoreError as exc:
            assert exc.code == "stage_subject_not_found"
        else:
            raise AssertionError("cross tenant accepted")
        await service.stop(T, claim["run_id"], state="cancelled", code="synthetic_view_check_only")

    async def test_incident_invalid_arrays_and_prose_keep_raw_and_prior():
        iid, _, _ = await fixture()
        good = await service.execute_incident(T, iid, uuid4(), gateway=Gateway())
        def change(mode):
            def transform(payload, data):
                answer = json.loads(payload["choices"][0]["message"]["content"])
                if mode == "arrays":
                    answer["limitations"] = "source missing"
                    answer["members"][0]["limitations"] = None
                else:
                    sid = data["items"][0]["id"] if mode == "bound" else "S999"
                    answer["summary"] += f" ({sid})"
                payload["choices"][0]["message"]["content"] = json.dumps(answer)
                return payload
            return transform
        gateway = Gateway(change("bound"))
        good = await service.execute_incident(T, iid, uuid4(), gateway=gateway)
        assert good["state"] == "completed"
        warning = next(r["content_json"] for r in await rows(F, F.c.run_id == good["run_id"]) if r["kind"] == "model_response")
        assert warning["raw"] == gateway.responses[0] and any(d["severity"] == "warning" for d in warning["validation_diagnostics"])
        for mode, reason in (("arrays", "incident_answer_shape_invalid"),
                ("prose", "incident_answer_prose_source_unbound")):
            gateway = Gateway(change(mode))
            out = await service.execute_incident(T, iid, uuid4(), gateway=gateway)
            assert out["state"] == "failed" and out["stop_reason"] == reason
            assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] == good["diagnosis_id"]
            response = next(r["content_json"] for r in await rows(F, F.c.run_id == out["run_id"]) if r["kind"] == "model_response")
            assert response["raw"] == gateway.responses[0] and response["validation_error"] == reason

    async def test_incident_member_facts_precede_large_labels():
        iid, aids, _ = await fixture()
        fields = [{"class_uid": 1007, "process": {"pid": 123, "cmd_line": "inventory --local"},
            "user": {"name": "only-first-user"}}, {"class_uid": 4001,
            "src_endpoint": {"ip": "192.0.2.11", "port": 50111},
            "dst_endpoint": {"ip": "198.51.100.11", "port": 443}, "network": {"protocol_name": "tcp"}}]
        async with service.transaction(T) as s:
            for aid, value in zip(aids, fields):
                mid = uuid4()
                await s.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=T, alert_id=aid, revision=2,
                    ocsf_json={"metadata": {"notes": "unverified source annotation " * 150}, **value},
                    detection={}, source_scope={}, retention={}, material_state="complete"))
                await s.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        gateway = Gateway()
        out = await service.execute_incident(T, iid, uuid4(), gateway=gateway)
        assert out["state"] == "completed", out
        data = model_data(gateway.requests[0]["messages"][1]["content"])
        assert [item["alert_ids"] for item in data["items"][:2]] == [[str(aid)] for aid in sorted(aids)]
        by_path = {item["field"]: item for item in data["items"] if item["role"] == "observation"}
        assert by_path["$.ocsf_json.process.cmd_line"]["alert_ids"] == [str(aids[0])]
        assert by_path["$.ocsf_json.user.name"]["alert_ids"] == [str(aids[0])]
        assert by_path["$.ocsf_json.dst_endpoint.ip"]["value"] == "198.51.100.11"
        assert by_path["$.ocsf_json.dst_endpoint.port"]["alert_ids"] == [str(aids[1])]
        request = next(r["content_json"] for r in await rows(F, F.c.run_id == out["run_id"]) if r["kind"] == "model_request")
        assert len([x for x in request["input_omission_details"] if x["source"]["source_path"] == "$.ocsf_json.metadata.notes"]) == 2
        assert "omission_details" not in data and len(gateway.requests[0]["messages"][1]["content"].encode()) <= draft_limit()

    async def test_incident_provider_error_receipt_preserves_previous_diagnosis():
        from test_socai2_model_errors import FailingGateway, ModelCallError
        iid, _, _ = await fixture()
        await service.execute_incident(T, iid, uuid4(), gateway=Gateway())
        before = (await rows(I, I.c.id == iid))[0]
        gateway, op = FailingGateway(), uuid4()
        try:
            await service.execute_incident(T, iid, op, gateway=gateway)
        except ModelCallError:
            pass
        else:
            raise AssertionError("provider failure must not become a diagnosis")
        replay = await service.execute_incident(T, iid, op, gateway=gateway)
        assert replay["state"] == "unknown" and gateway.calls == 1
        response = next(r for r in await rows(F, F.c.run_id == replay["run_id"]) if r["kind"] == "model_response")
        payload = response["content_json"]
        assert payload["raw"] is None and payload["transport_error"]["fields"]["code"] == "upstream_error"
        step = next(s for s in await rows(S, S.c.run_id == replay["run_id"]) if s["kind"] == "model")
        assert step["state"] == "unknown" and step["output_artifact_id"] == response["id"]
        assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] == before["latest_diagnosis_id"]
        return {"safe_error_saved": True, "replay_calls": gateway.calls, "prior_diagnosis_preserved": True}

    async def test_incident_explicit_schema_rejection_is_failed_and_replay_does_not_dispatch():
        from unittest.mock import patch

        from app.socai2.model_errors import ModelCallError
        iid, _, _ = await fixture()
        gateway, op = Gateway(), uuid4()
        attempts = []
        async def reject_schema(*_):
            attempts.append(True)
            raise ModelCallError({"http_status": 400, "fields": {"code": "invalid_schema"}})
        with patch.object(gateway, "complete", reject_schema):
            out = await service.execute_incident(T, iid, op, gateway=gateway)
            replay = await service.execute_incident(T, iid, op, gateway=gateway)
        assert out["state"] == replay["state"] == "failed" and len(attempts) == 1
        assert all(s["state"] == "failed" and s["ended_at"] for s in await rows(S, S.c.run_id == out["run_id"]))
        diagnosis = (await rows(D, D.c.id == out["diagnosis_id"]))[0]
        assert diagnosis["state"] == "failed" and diagnosis["diagnosis"] is None

    async def test_incident_partial_review_preserves_independent_content_and_previous_diagnosis():
        iid, _, _ = await fixture()
        good = await service.execute_incident(T, iid, uuid4(), gateway=Gateway())
        def wrong_member(payload, data):
            raw = json.loads(payload["choices"][0]["message"]["content"])
            raw["members"][1]["source_ids"] = raw["members"][0]["source_ids"]
            payload["choices"][0]["message"]["content"] = json.dumps(raw)
            return payload
        gateway, op = Gateway(wrong_member), uuid4()
        out = await service.execute_incident(T, iid, op, gateway=gateway)
        assert out["state"] == "failed" and gateway.calls == 1
        assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] == good["diagnosis_id"]
        diagnosis = (await rows(D, D.c.id == out["diagnosis_id"]))[0]
        assert diagnosis["state"] == "failed" and diagnosis["summary"] is None
        assert diagnosis["diagnosis"]["validation_state"] == "partial" and diagnosis["diagnosis"]["conclusion"] is None
        assert len(diagnosis["diagnosis"]["findings"]) == 2 and len(diagnosis["open_questions"]) == 1
        validate_diagnosis_contract(diagnosis["diagnosis"])
        entry = await reader.read_entry(T, "incident_diagnosis", iid, out["run_id"])
        assert not entry.valid_for_current_input and not entry.is_current_pointer
        assert entry.partial_analysis.available and not entry.partial_analysis.content["conclusion_adoptable"]
        assert len(entry.partial_analysis.content["retained_analysis"]["members"]) == 1
        response = next(r["content_json"] for r in await rows(F, F.c.run_id == out["run_id"]) if r["kind"] == "model_response")
        assert response["raw"] == gateway.responses[0]
        await service.execute_incident(T, iid, op, gateway=gateway)
        assert gateway.calls == 1
        try:
            await reader.read_entry(OTHER, "incident_diagnosis", iid, out["run_id"])
            raise AssertionError("cross-tenant partial content exposed")
        except StoreError as exc:
            assert exc.status == 404
        return {"prior_run": str(good["run_id"]), "partial_run": str(out["run_id"]),
            "valid_members_retained": 1, "global_judgment_adopted": False, "raw_preserved": True}

    checks = [v for k, v in locals().copy().items() if k.startswith("test_incident_")]
    for check in checks:
        if only and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 150)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- preserve each actual failure
            record(check.__name__, False, traceback.format_exc())
