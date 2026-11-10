"""A executor on existing synthetic PG; real source SQL, substituted model."""
import asyncio
import copy
import json
import traceback
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import baseline_enrichment_sources as sources
from app.socai2.alert_basic_contract import build
from app.socai2.baseline_enrichment import S
from app.socai2.baseline_store import StoreError, encoded
from app.socai2.runtime_policy import draft_limit
from app.socai2.stage_results import AS, A, F, R, StageResultService
from socai2_test_model_view import model_data
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER = UUID(int=1), UUID(int=2)


class Gateway:
    provider, model = "synthetic", "synthetic-alert-model"

    def __init__(self, *, transform=None, wait=False, configured=True):
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
        ids = [item["id"] for item in data["items"]]
        answer = {"verdict": "needs_review", "confidence": .3,
            "rationale": "synthetic process record requires authorization verification",
            "explanation": "synthetic alert analysis; inventory and intelligence are background only",
            "evidence_ids": ids, "recommendations": [], "limitations": ["synthetic only; authorization unknown"], "decision_basis": None}
        payload = {"id": "synthetic-request", "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 60, "total_tokens": 160}}
        if self.transform:
            payload = self.transform(payload)
        self.responses.append(copy.deepcopy(payload))
        return payload


async def run_checks(engine, record, only=None):
    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))

    async def rows(table, condition, tenant=T):
        async with service.transaction(tenant, readonly=True) as store:
            return [dict(r) for r in (await store.db.execute(select(table).where(*store.where(table, condition)))).mappings()]

    async def fixture(*, when=True, background=True):
        aid, mid, host = uuid4(), uuid4(), "synthetic-a-" + uuid4().hex
        async with service.transaction(T) as s:
            now = await s.now()
            for tenant, lag in ((T, 1), (OTHER, 1), (T, 30)):
                history, material = uuid4(), uuid4()
                async with service.transaction(tenant) as history_store:
                    await history_store.db.execute(insert(A).values(id=history, tenant_id=tenant, source_namespace="synthetic.a",
                        source_identity_key=str(history), title="synthetic historical alert",
                        event_time=now-timedelta(hours=lag), event_time_source="source"))
                    await history_store.db.execute(insert(m.AlertMaterials).values(id=material, tenant_id=tenant, alert_id=history,
                        revision=1, raw_json={"process": {"pid": 9}}, detection={}, source_scope={}, retention={}, material_state="complete"))
                    await history_store.db.execute(update(A).where(A.c.id == history).values(latest_material_id=material))
                    await history_store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant, alert_id=history, material_id=material,
                        object_type="host", object_role="entity", object_key="host:"+host, namespace="synthetic.a",
                        raw_value=host, normalized_value=host, source_path="$.raw_json.host", attributes={}))
            await s.db.execute(insert(A).values(id=aid, tenant_id=T, source_namespace="synthetic.a", source_identity_key=str(aid),
                title="synthetic process alert", event_time=now if when else None, event_time_source="source" if when else "unknown",
                handling_status="completed", disposition="benign"))
            await s.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=T, alert_id=aid, revision=1,
                raw_json={"process": {"pid": 42, "argv": ["app.exe", "synthetic"]}},
                detection={"rule_id": "synthetic-rule"}, source_scope={}, retention={}, material_state="complete"))
            await s.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
            for typ, value, role in (("host", host, "entity"), ("domain", host+".invalid", "ioc")):
                await s.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=T, alert_id=aid, material_id=mid,
                    object_type=typ, object_role=role, object_key=typ+":"+value, namespace="synthetic.a",
                    raw_value=value, normalized_value=value, source_path="$.raw_json.host", attributes={}))
            if background:
                for tenant in (T, OTHER):
                    await s.db.execute(text("""INSERT INTO public.assets(id,tenant_id,name,asset_type,tags,updated_at)
                        VALUES(:id,:tenant,:host,'server',ARRAY['synthetic'],:now)"""),
                        {"id": uuid4(), "tenant": tenant, "host": host, "now": now})
                    await s.db.execute(text("""INSERT INTO public.threat_intel_iocs
                        (id,tenant_id,ioc_type,value,confidence,source,is_active,false_positive,updated_at)
                        VALUES(:id,:tenant,'domain',:value,80,'synthetic',true,false,:now)"""),
                        {"id": uuid4(), "tenant": tenant, "value": host+".invalid", "now": now})
        return aid, mid

    async def test_alert_actual_sources_model_and_paired_output():
        aid, mid = await fixture()
        gateway = Gateway()
        out = await service.execute_alert(T, aid, uuid4(), gateway=gateway)
        assert out["state"] == "completed" and gateway.calls == 1
        artifacts = await rows(F, F.c.run_id == out["run_id"])
        tools = {r["content_json"]["tool_name"]: r["content_json"] for r in artifacts if r["kind"] == "tool_response"}
        assert {name: p["returned_rows"] for name, p in tools.items()} == {"assets": 1, "history": 1, "threat_intel": 1}
        assert all(p["state"] == "completed" for p in tools.values())
        request = next(r for r in artifacts if r["kind"] == "model_request")
        assert request["content_json"]["body"] == gateway.requests[0]
        response = next(r for r in artifacts if r["kind"] == "model_response")
        assert response["content_json"]["raw"] == gateway.responses[0]
        assert response["content_json"]["usage"]["total_tokens"] == 160
        alert = (await rows(A, A.c.id == aid))[0]
        assessment = (await rows(AS, AS.c.id == alert["latest_triage_id"]))[0]
        assert assessment["input_material_id"] == mid and float(assessment["confidence"]) == .3
        assert alert["handling_status"] == "completed" and alert["disposition"] == "benign"
        explanation = (await rows(F, F.c.id == alert["latest_explanation_id"]))[0]["content_json"]
        assert explanation["generation_method"] == "model" and explanation["source_refs"]
        assert any(r["source_path"].endswith("argv.0") for r in explanation["source_refs"])
        steps = await rows(S, S.c.run_id == out["run_id"])
        assert len(steps) == 5 and all(s["state"] == "completed" for s in steps)
        assert all(s["usage"] is None for s in steps if s["kind"] != "model")
        assert await service.freshness(T, out["run_id"])
        return {"run_id": str(out["run_id"]), "tool_rows": {k: v["returned_rows"] for k, v in tools.items()}, "model_calls": 1}

    async def test_alert_claim_replay_and_concurrent_no_redispatch():
        aid, _ = await fixture()
        op, gateway = uuid4(), Gateway(wait=True)
        task = asyncio.create_task(service.execute_alert(T, aid, op, gateway=gateway))
        try:
            await asyncio.wait_for(gateway.entered.wait(), 10)
            other = Gateway()
            replay = await service.execute_alert(T, aid, op, gateway=other)
            assert replay["state"] == "running" and not replay["newly_claimed"] and other.calls == 0
            gateway.release.set()
            done = await task
            replay = await service.execute_alert(T, aid, op, gateway=other)
            assert replay["run_id"] == done["run_id"] and replay["state"] == "completed" and other.calls == 0
            assert len(await rows(S, S.c.run_id == done["run_id"])) == 5
        finally:
            gateway.release.set()
            await task

    async def test_alert_changed_input_stays_history():
        aid, mid = await fixture()
        gateway = Gateway(wait=True)
        task = asyncio.create_task(service.execute_alert(T, aid, uuid4(), gateway=gateway))
        try:
            await asyncio.wait_for(gateway.entered.wait(), 10)
            async with service.transaction(T) as s:
                new = uuid4()
                await s.db.execute(insert(m.AlertMaterials).values(id=new, tenant_id=T, alert_id=aid, revision=2,
                    raw_json={"process": {"pid": 99}}, detection={}, source_scope={}, retention={}, material_state="complete"))
                await s.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=new))
            gateway.release.set()
            out = await task
            assert out["state"] == "completed"
            assert (await rows(A, A.c.id == aid))[0]["latest_triage_id"] is None
            result = (await rows(AS, AS.c.source_run_id == out["run_id"]))[0]
            assert result["input_material_id"] == mid and not await service.freshness(T, out["run_id"])
        finally:
            gateway.release.set()
            await task

    async def test_alert_missing_sources_and_empty_are_distinct():
        aid, _ = await fixture(when=False, background=False)
        async def query(service, tenant, name, args):
            if name == "assets":
                class Unavailable(Exception):
                    sqlstate = "42501"
                raise DBAPIError("synthetic", {}, Unavailable(), False)
            return await sources.query(service, tenant, name, args)
        gateway = Gateway()
        out = await service.execute_alert(T, aid, uuid4(), gateway=gateway, query=query)
        artifacts = await rows(F, F.c.run_id == out["run_id"])
        tools = {r["content_json"]["tool_name"]: r["content_json"] for r in artifacts if r["kind"] == "tool_response"}
        assert tools["assets"]["state"] == "failed" and tools["assets"]["returned_rows"] is None
        assert tools["history"]["state"] == "skipped" and tools["history"]["reason"] == "history_window_not_defined"
        assert tools["threat_intel"]["state"] == "completed" and tools["threat_intel"]["returned_rows"] == 0
        assert out["state"] == "completed"
        input_facts = model_data(gateway.requests[0]["messages"][1]["content"])["program_facts"]
        explanation = next(r["content_json"] for r in artifacts if r["kind"] == "alert_explanation")
        assert explanation["program_facts"] == input_facts
        query_facts = {x["source"]: x for x in input_facts["query_statuses"]}
        assert {name: x["outcome"] for name, x in query_facts.items()} == {
            "assets": "failed", "history": "not_queried", "threat_intel": "empty"}
        by_id = {str(r["id"]): r for r in artifacts}
        for name, value in query_facts.items():
            assert by_id[value["receipt"]["id"]]["content_json"] == tools[name]

    async def test_alert_invalid_output_preserves_raw_and_prior_pointer():
        aid, _ = await fixture()
        prior = await service.execute_alert(T, aid, uuid4(), gateway=Gateway())
        old = (await rows(A, A.c.id == aid))[0]["latest_triage_id"]
        def bad_source(p):
            answer = json.loads(p["choices"][0]["message"]["content"])
            answer["evidence_ids"] = ["S99999"]
            p["choices"][0]["message"]["content"] = json.dumps(answer)
            return p
        def missing_usage(p):
            p.pop("usage")
            return p
        def truncated(p):
            p["choices"][0]["finish_reason"] = "length"
            return p
        for transform in (bad_source, missing_usage, truncated):
            gateway = Gateway(transform=transform)
            out = await service.execute_alert(T, aid, uuid4(), gateway=gateway)
            assert out["state"] == "failed" and gateway.calls == 1
            artifacts = await rows(F, F.c.run_id == out["run_id"])
            response = next(r["content_json"] for r in artifacts if r["kind"] == "model_response")
            assert response["raw"] == gateway.responses[0] and response["validation_error"]
            if transform == missing_usage:
                assert response["usage"]["total_tokens"] is None and response["usage"]["usage_state"] == "unavailable"
            assert not await rows(AS, AS.c.source_run_id == out["run_id"])
            assert (await rows(A, A.c.id == aid))[0]["latest_triage_id"] == old
        assert prior["state"] == "completed"

    async def test_alert_unknown_transport_is_not_retried():
        aid, _ = await fixture()
        def uncertain(_):
            raise TimeoutError("synthetic transport uncertainty")
        gateway, op = Gateway(transform=uncertain), uuid4()
        try:
            await service.execute_alert(T, aid, op, gateway=gateway)
        except TimeoutError:
            pass
        else:
            raise AssertionError("expected uncertain transport")
        out = await service.execute_alert(T, aid, op, gateway=gateway)
        assert out["state"] == "unknown" and gateway.calls == 1 and not out["newly_claimed"]
        assert not await rows(AS, AS.c.source_run_id == out["run_id"])

    async def test_alert_request_commit_before_dispatch():
        aid, _ = await fixture()
        class Failing(StageResultService):
            injected = False
            @asynccontextmanager
            async def transaction(self, tenant, **kwargs):
                async with super().transaction(tenant, **kwargs) as s:
                    yield s
                    if not kwargs.get("readonly") and not self.injected:
                        model = await s.one(select(S).join(R, R.c.id == S.c.run_id).where(
                            R.c.alert_id == aid, S.c.kind == "model", S.c.state == "running"))
                        if model:
                            self.injected = True
                            await s.db.execute(update(S).where(S.c.id == model["id"]).values(parent_step_id=uuid4()))
        failing, gateway, op = Failing(service.sessions), Gateway(), uuid4()
        try:
            await failing.execute_alert(T, aid, op, gateway=gateway)
        except DBAPIError:
            pass
        else:
            raise AssertionError("expected commit failure")
        out = await failing.execute_alert(T, aid, op, gateway=gateway)
        assert out["state"] == "unknown" and gateway.calls == 0
        assert not [r for r in await rows(F, F.c.run_id == out["run_id"]) if r["kind"] == "model_request"]

    async def test_alert_publication_rollback_keeps_response():
        aid, _ = await fixture()
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
                        await s.db.execute(update(A).where(A.c.id == aid).values(latest_explanation_id=uuid4()))
        failing, gateway, op = Failing(service.sessions), Gateway(), uuid4()
        try:
            await failing.execute_alert(T, aid, op, gateway=gateway)
        except DBAPIError:
            pass
        else:
            raise AssertionError("expected publication failure")
        out = await failing.execute_alert(T, aid, op, gateway=gateway)
        assert out["state"] == "unknown" and gateway.calls == 1
        artifacts = await rows(F, F.c.run_id == out["run_id"])
        assert len([r for r in artifacts if r["kind"] == "model_response"]) == 1
        assert not await rows(AS, AS.c.source_run_id == out["run_id"])
        assert (await rows(A, A.c.id == aid))[0]["latest_triage_id"] is None

    async def test_alert_model_disabled_and_view_omissions():
        aid, _ = await fixture()
        gateway = Gateway(configured=False)
        out = await service.execute_alert(T, aid, uuid4(), gateway=gateway)
        assert out["state"] == "failed" and out["stop_reason"] == "model_not_configured" and gateway.calls == 0
        frozen = (await rows(F, F.c.id == out["input_artifact_id"]))[0]["content_json"]
        frozen["members"][0]["material"]["raw_json"]["oversize"] = "x"*5000
        frozen["members"][0]["material"]["raw_json"]["control"] = "-----BEGIN PRIVATE KEY-----"
        frozen["members"][0]["material"]["raw_json"]["-----BEGIN PRIVATE KEY-----"] = "synthetic path"
        frozen["members"][0]["material"]["raw_json"]["unaddressable.path"] = "synthetic value"
        messages, mapping, data = build(frozen, out["input_artifact_id"], [])
        assert data["omissions"]["field_size"] >= 1 and data["omissions"]["input_guard"] >= 2
        assert data["omissions"]["unaddressable_source_path"] == 1
        assert "PRIVATE KEY" not in str(messages)
        assert len(encoded(data)) <= draft_limit() and len(encoded(messages)) <= draft_limit()
        assert mapping and all("oversize" not in x["ref"]["source_path"] for x in mapping.values())
        try:
            await service.execute_alert(OTHER, aid, uuid4(), gateway=Gateway())
        except StoreError as exc:
            assert exc.code == "stage_subject_not_found"
        else:
            raise AssertionError("cross tenant allowed")

    async def test_alert_metadata_roles_and_prose_rejection_persisted():
        aid, mid = uuid4(), uuid4()
        async with service.transaction(T) as s:
            await s.db.execute(insert(A).values(id=aid, tenant_id=T, source_namespace="synthetic.roles",
                source_identity_key=str(aid), title="source declarations", event_time_source="unknown"))
            await s.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=T, alert_id=aid,
                revision=1, raw_json={"raw_event": {"original_vendor": "DeclaredMaker", "custom_note": "Test record",
                    "process": {"pid": 42}, "user": {"name": "S1"}}},
                detection={}, source_scope={}, retention={}, material_state="complete"))
            await s.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        gateway = Gateway()
        good = await service.execute_alert(T, aid, uuid4(), gateway=gateway)
        assert good["state"] == "completed"
        data = model_data(gateway.requests[0]["messages"][1]["content"])
        items = {v["field"]:v for v in data["items"]}
        for name in ("original_vendor", "custom_note"):
            assert items["$.raw_json.raw_event."+name]["role"] == "source_label"
        assert items["$.raw_json.raw_event.process.pid"]["role"] == "observation"
        saved_alert = (await rows(A, A.c.id == aid))[0]
        latest = saved_alert["latest_triage_id"]
        explanation = (await rows(F, F.c.id == saved_alert["latest_explanation_id"]))[0]["content_json"]
        assert explanation["source_refs"] and all(r["role"] == "source_label" for r in explanation["source_refs"]
            if r["source_path"].endswith(("original_vendor", "custom_note")))
        def leak(payload):
            answer = json.loads(payload["choices"][0]["message"]["content"])
            sid = items["$.raw_json.raw_event.process.pid"]["id"]
            answer["explanation"] = f"According to ({sid}), authorization is unknown."
            payload["choices"][0]["message"]["content"] = json.dumps(answer)
            return payload
        warning_gateway = Gateway(transform=leak)
        warning = await service.execute_alert(T, aid, uuid4(), gateway=warning_gateway)
        assert warning["state"] == "completed"
        response = next(r["content_json"] for r in await rows(F, F.c.run_id == warning["run_id"]) if r["kind"] == "model_response")
        assert response["raw"] == warning_gateway.responses[0] and response["validation_error"] is None
        assert any(d["severity"] == "warning" for d in response["validation_diagnostics"])
        latest = (await rows(A, A.c.id == aid))[0]["latest_triage_id"]
        def unbound(payload):
            value = json.loads(payload["choices"][0]["message"]["content"])
            value["explanation"] = "According to S999, authorization is unknown."
            payload["choices"][0]["message"]["content"] = json.dumps(value)
            return payload
        bad_gateway = Gateway(transform=unbound)
        bad = await service.execute_alert(T, aid, uuid4(), gateway=bad_gateway)
        assert bad["state"] == "failed" and bad["stop_reason"] == "alert_answer_prose_source_unbound"
        assert (await rows(A, A.c.id == aid))[0]["latest_triage_id"] == latest
        response = next(r["content_json"] for r in await rows(F, F.c.run_id == bad["run_id"]) if r["kind"] == "model_response")
        assert response["raw"] == bad_gateway.responses[0] and response["usage"]["total_tokens"] == 160

    async def test_alert_behavior_projection_precedes_metadata():
        aid, _ = await fixture(background=False)
        mid = uuid4()
        async with service.transaction(T) as s:
            await s.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=T, alert_id=aid, revision=2,
                ocsf_json={"metadata": {"notes": "retained provenance " * 170}, "class_uid": 1007,
                    "process": {"pid": 123, "cmd_line": "inventory --local"}, "user": {"name": "operator-two"}},
                raw_json={"raw_event": {"original_vendor": "VendorClaim", "custom_note": "self-declared authorization"}},
                detection={}, source_scope={}, retention={}, material_state="complete"))
            await s.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        gateway = Gateway()
        out = await service.execute_alert(T, aid, uuid4(), gateway=gateway)
        assert out["state"] == "completed", out
        data = model_data(gateway.requests[0]["messages"][1]["content"])
        items = {x["field"]: x for x in data["items"]}
        assert items["$.ocsf_json.process.cmd_line"]["value"] == "inventory --local"
        assert items["$.ocsf_json.user.name"]["value"] == "operator-two"
        assert data["items"][0]["role"] == "observation"
        assert items["$.raw_json.raw_event.original_vendor"]["value"] == "VendorClaim"
        assert items["$.raw_json.raw_event.custom_note"]["role"] == "source_label"
        request = next(r["content_json"] for r in await rows(F, F.c.run_id == out["run_id"]) if r["kind"] == "model_request")
        assert items["$.ocsf_json.metadata.notes"]["value"] == "retained provenance " * 170
        assert not any(x["source"]["source_path"] == "$.ocsf_json.metadata.notes"
                       for x in request["input_omission_details"])
        assert "omission_details" not in data and len(gateway.requests[0]["messages"][1]["content"].encode()) <= draft_limit()

    async def test_alert_separate_judgment_basis_rejects_labels_without_publication():
        aid, _ = await fixture(background=False)
        good = await service.execute_alert(T, aid, uuid4(), gateway=Gateway())
        assert good["state"] == "completed"
        previous = (await rows(A, A.c.id == aid))[0]["latest_triage_id"]
        gateway = Gateway()
        def label_basis(payload):
            data = model_data(gateway.requests[-1]["messages"][1]["content"])
            label = next(i["id"] for i in data["items"] if i["role"] == "source_label")
            value = json.loads(payload["choices"][0]["message"]["content"])
            value.update(verdict="benign", decision_basis={"kind": "authorized_or_expected_behavior",
                "claim": "Source description says normal", "source_ids": [label]})
            payload["choices"][0]["message"]["content"] = json.dumps(value)
            return payload
        gateway.transform = label_basis
        out = await service.execute_alert(T, aid, uuid4(), gateway=gateway)
        assert out["state"] == "failed" and out["stop_reason"] == "alert_decision_basis_not_direct"
        artifacts = await rows(F, F.c.run_id == out["run_id"])
        response = next(r["content_json"] for r in artifacts if r["kind"] == "model_response")
        request = next(r["content_json"] for r in artifacts if r["kind"] == "model_request")
        assert response["raw"] == gateway.responses[0] and request["schema_profile"] == "standard"
        assert all(s.startswith("N") for s in request["source_map"])
        assert not await rows(AS, AS.c.source_run_id == out["run_id"])
        assert (await rows(A, A.c.id == aid))[0]["latest_triage_id"] == previous
        return {"raw_preserved": True, "prior_pointer_preserved": True, "decision_basis_rejected": True}

    async def test_alert_provider_error_receipt_preserves_previous_judgment():
        from test_socai2_model_errors import FailingGateway, ModelCallError
        aid, _ = await fixture(background=False)
        await service.execute_alert(T, aid, uuid4(), gateway=Gateway())
        before = (await rows(A, A.c.id == aid))[0]
        gateway, op = FailingGateway(), uuid4()
        try:
            await service.execute_alert(T, aid, op, gateway=gateway)
        except ModelCallError:
            pass
        else:
            raise AssertionError("provider failure must not become an answer")
        replay = await service.execute_alert(T, aid, op, gateway=gateway)
        assert replay["state"] == "unknown" and gateway.calls == 1
        artifacts = await rows(F, F.c.run_id == replay["run_id"])
        response = next(r for r in artifacts if r["kind"] == "model_response")
        payload = response["content_json"]
        assert payload["raw"] is None and payload["transport_error"]["http_status"] == 400
        assert payload["usage"]["total_tokens"] is None
        step = next(s for s in await rows(S, S.c.run_id == replay["run_id"]) if s["kind"] == "model")
        assert step["state"] == "unknown" and step["output_artifact_id"] == response["id"]
        after = (await rows(A, A.c.id == aid))[0]
        assert all(after[k] == before[k] for k in ("latest_triage_id", "latest_explanation_id", "disposition"))
        return {"safe_error_saved": True, "replay_calls": gateway.calls, "prior_judgment_preserved": True}

    async def test_alert_deepseek_wire_saved_after_union_expansion():
        from test_socai2_deepseek_union_schema import DeepSeekWireGateway
        aid, _ = await fixture(background=False)
        gateway = DeepSeekWireGateway(Gateway())
        out = await service.execute_alert(T, aid, uuid4(), gateway=gateway)
        assert out["state"] == "completed" and len(gateway.requests) == 1
        artifacts = await rows(F, F.c.run_id == out["run_id"])
        request = next(a["content_json"] for a in artifacts if a["kind"] == "model_request")
        assert request["body"] == gateway.requests[0]
        branches = request["body"]["text"]["format"]["schema"]["anyOf"]
        assert len(branches) == 4 and branches[0]["properties"]["decision_basis"] == {"type": "null"}
        branch = branches[1]["properties"]["decision_basis"]
        assert branch["type"] == "object" and branch["additionalProperties"] is False and "$ref" not in branch
        response = next(a["content_json"] for a in artifacts if a["kind"] == "model_response")
        assert response["raw"] == gateway.responses[0] and response["usage"]["usage_state"] == "reported"
        return {"expanded_request_saved_exactly": True, "raw_response_saved_exactly": True, "model_substitute": True}

    async def test_alert_explicit_schema_rejection_is_failed_and_replay_does_not_dispatch():
        from unittest.mock import patch

        from app.socai2.model_errors import ModelCallError
        aid, _ = await fixture(background=False)
        gateway, op = Gateway(), uuid4()
        attempts = []
        async def reject_schema(*_):
            attempts.append(True)
            raise ModelCallError({"http_status": 400, "fields": {"code": "invalid_schema"}})
        with patch.object(gateway, "complete", reject_schema):
            out = await service.execute_alert(T, aid, op, gateway=gateway)
            replay = await service.execute_alert(T, aid, op, gateway=gateway)
        assert out["state"] == replay["state"] == "failed" and len(attempts) == 1
        steps = await rows(S, S.c.run_id == out["run_id"])
        model = next(s for s in steps if s["kind"] == "model")
        assert model["state"] == "failed" and model["ended_at"] and model["usage"]["total_tokens"] is None
        assert not any(s["state"] in {"running", "planned", "unknown"} for s in steps)
        assert (await rows(A, A.c.id == aid))[0]["latest_triage_id"] is None

    async def test_alert_partial_review_keeps_advice_and_never_adopts_bad_judgment():
        from app.socai2.stage_reader import StageReadService
        reader = StageReadService(service.sessions)
        aid, _ = await fixture(background=False)
        good = await service.execute_alert(T, aid, uuid4(), gateway=Gateway())
        prior = (await rows(A, A.c.id == aid))[0]["latest_triage_id"]
        def broken(core):
            def transform(payload):
                raw = json.loads(payload["choices"][0]["message"]["content"])
                sid = raw["evidence_ids"][0]
                raw["recommendations"] = [{"reason": "independent valid advice", "source_ids": [sid]},
                    {"reason": "invalid advice", "source_ids": ["N99_S999"]}]
                if core:
                    raw["evidence_ids"] = ["N99_S999"]
                payload["choices"][0]["message"]["content"] = json.dumps(raw)
                return payload
            return transform
        gateway, op = Gateway(transform=broken(True)), uuid4()
        failed = await service.execute_alert(T, aid, op, gateway=gateway)
        assert failed["state"] == "failed" and gateway.calls == 1
        assert (await rows(A, A.c.id == aid))[0]["latest_triage_id"] == prior
        entry = await reader.read_entry(T, "alert_basic", aid, failed["run_id"])
        assert not entry.valid_for_current_input and entry.result is None
        assert entry.partial_analysis.available
        kept = entry.partial_analysis.content["retained_analysis"]
        assert kept["assessment"] is None and len(kept["recommendations"]) == 1
        response = next(r["content_json"] for r in await rows(F, F.c.run_id == failed["run_id"]) if r["kind"] == "model_response")
        assert response["raw"] == gateway.responses[0]
        await service.execute_alert(T, aid, op, gateway=gateway)
        assert gateway.calls == 1
        gateway = Gateway(transform=broken(False))
        partial = await service.execute_alert(T, aid, uuid4(), gateway=gateway)
        assert partial["state"] == "completed" and gateway.calls == 1
        entry = await reader.read_entry(T, "alert_basic", aid, partial["run_id"])
        assert entry.valid_for_current_input and entry.result.verdict == "needs_review"
        assert len(entry.result.recommendations) == 1 and entry.partial_analysis.content["conclusion_adoptable"]
        assert entry.explanation.content["program_facts"] == model_data(gateway.requests[0]["messages"][1]["content"])["program_facts"]
        from pathlib import Path

        import jsonschema
        schema = json.loads((Path(__file__).resolve().parents[1] / "app/socai2/contracts.schema.json").read_text())
        jsonschema.validate(entry.explanation.content, {"$defs": schema["$defs"], "$ref": "#/$defs/alert_explanation"})
        return {"prior_run": str(good["run_id"]), "failed_run": str(failed["run_id"]),
            "partial_run": str(partial["run_id"]), "failed_judgment_adopted": False, "raw_preserved": True}

    checks = [v for k, v in locals().copy().items() if k.startswith("test_alert_")]
    for check in checks:
        if only and check.__name__ not in only:
            continue
        try:
            # A multi-run check needs more wall time than one 120s Run; this
            # harness limit does not change the persisted executor allowance.
            detail = await asyncio.wait_for(check(), 150)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- retain each actual failure
            record(check.__name__, False, traceback.format_exc())
