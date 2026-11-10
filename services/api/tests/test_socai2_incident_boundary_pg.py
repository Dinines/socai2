"""Opt-in I integration on an existing isolated PG; all model/tool replies synthetic."""
import asyncio
import copy
import json
import traceback
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import runtime_policy
from app.socai2.baseline_context import reference
from app.socai2.page_reader import PageReadService
from app.socai2.stage_reader import StageReadService
from app.socai2.stage_result_contracts import ALERT_EXECUTOR_VERSION, AlertOutput
from app.socai2.stage_results import A, D, F, I, R, StageResultService, artifact
from jsonschema import Draft202012Validator
from socai2_test_model_view import synthetic_measure
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_socai2_incident_diagnosis_executor import Gateway as LegacyGateway
from test_socai2_incident_diagnosis_executor import validate_diagnosis_contract

ROOT = Path(__file__).resolve().parents[3]
TENANT = UUID(int=1)


@contextmanager
def policy(candidate=True):
    original = runtime_policy.active_policy
    name = "investigation-policy-incident-v1.toml" if candidate else "investigation-policy.toml"
    selected = runtime_policy.load_policy(ROOT / "deploy/local-investigation" / name)
    runtime_policy.active_policy = lambda: selected
    try:
        yield
    finally:
        runtime_policy.active_policy = original


class Gateway:
    provider, model = "synthetic", "synthetic-incident-boundary"

    def __init__(self, service, iid, *, bad_member=False, mode=None):
        self.service, self.iid, self.bad_member = service, iid, bad_member
        self.mode = mode
        self.calls, self.requests, self.responses = 0, [], []

    async def configure(self, *_):
        return True

    async def measure(self, body, stage):
        return await synthetic_measure(body, stage)

    async def complete(self, body, timeout):
        assert timeout > 0
        self.calls += 1
        self.requests.append(copy.deepcopy(body))
        # Read the committed request to exercise the exact alias/receipt map.
        async with self.service.transaction(TENANT, readonly=True) as store:
            request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.incident_id == self.iid, F.c.kind == "model_request")).order_by(F.c.captured_at.desc()).limit(1))).scalar_one()
        assert request["body"] == body
        sources = request["source_map"]
        members = request["incident_boundary"]["member_aliases"]
        selected = {aid: next(s for s, item in sources.items() if item["alert_ids"] == [aid]
                             and item["ref"]["role"] == "observation") for aid in members}
        receipts = [s for s, item in sources.items() if item["ref"]["role"] == "execution_receipt"]
        answer = {"diagnosis": {"summary": "Synthetic event summary.", "conclusion": "Synthetic unresolved assessment.",
                   "source_ids": [*selected.values(), *receipts], "limitations": []},
            "members": [{"alert_ref": alias, "state": "unresolved", "assessment": "Synthetic member requires confirmation.",
                         "source_ids": [selected[aid]], "limitations": []} for aid, alias in members.items()],
            "findings": [{"statement": "Synthetic event finding.", "state": "unresolved", "alert_refs": list(members.values()),
                         "source_ids": list(selected.values()), "limitations": []}],
            "open_questions": [{"text": "Synthetic authorization question.", "alert_refs": list(members.values()),
                                "source_ids": list(selected.values()), "evidence_requirements": ["Human confirmation."]}]}
        Draft202012Validator(body["response_format"]["json_schema"]["schema"]).validate(answer)
        if self.bad_member:
            answer["members"][1]["source_ids"] = answer["members"][0]["source_ids"]
        if self.mode == "all_invalid":
            for key in ("members", "findings", "open_questions"):
                for unit in answer[key]:
                    unit["source_ids"] = ["N1_S999999"]
        elif self.mode == "not_reviewed":
            answer["members"][1].update(state="not_reviewed", source_ids=[])
        elif self.mode == "business_name":
            answer["diagnosis"]["summary"] = "S3 存储桶配置记录需要业务复核。"
        elif self.mode == "timeout":
            raise TimeoutError("synthetic transport uncertainty")
        payload = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}],
                   "usage": {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200}}
        if self.mode == "malformed":
            payload["choices"][0]["message"]["content"] = "{invalid json"
        self.responses.append(copy.deepcopy(payload))
        return payload


async def run_checks(engine, record, only=None):
    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))
    reader = StageReadService(service.sessions)

    async def rows(table, condition):
        async with service.transaction(TENANT, readonly=True) as store:
            return [dict(r) for r in (await store.db.execute(select(table).where(*store.where(table, condition)))).mappings()]

    async def fixture(*, extra_raw=None):
        iid, aids, mids, queries = uuid4(), [uuid4(), uuid4()], [uuid4(), uuid4()], []
        async with service.transaction(TENANT) as store:
            now = await store.now()
            await store.db.execute(insert(I).values(id=iid, tenant_id=TENANT, source_namespace="synthetic.boundary",
                source_incident_id=str(iid), title="Synthetic boundary event", description="Stored event description.", handling_status="new"))
            for aid, mid in zip(aids, mids):
                await store.db.execute(insert(A).values(id=aid, tenant_id=TENANT, source_namespace="synthetic.boundary",
                    source_identity_key=str(aid), title="Synthetic member", description="Stored collector description.",
                    event_time=now, event_time_source="source", handling_status="new"))
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=TENANT, alert_id=aid, revision=1,
                    raw_text="Synthetic raw text.", raw_json={"process": {"pid": 42}, "email": {"id": "business-message", "size": 0}, **(extra_raw or {})},
                    detection={"rule_id": "synthetic"}, source_scope={}, retention={}, material_state="complete"))
                await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=TENANT, incident_id=iid, alert_id=aid,
                    membership_source="fusion", correlation_basis={"reason": "synthetic frozen membership"},
                    basis_version="synthetic", source_operation_id=uuid4()))
        for aid, mid in zip(aids, mids):
            claim = await service.begin(TENANT, "alert_basic", aid, uuid4(), producer=ALERT_EXECUTOR_VERSION, limits=None)
            async with service.transaction(TENANT) as store:
                run, _, _ = await service.locked(store, claim["run_id"])
                now, sid, fid = await store.now(), uuid4(), uuid4()
                await store.db.execute(insert(m.RunSteps).values(id=sid, tenant_id=TENANT, run_id=run["id"], seq=1,
                    kind="tool", stage_code="A", name="synthetic_receipt", state="running", started_at=now,
                    implementation_version=ALERT_EXECUTOR_VERSION))
                body = {"schema_version": ALERT_EXECUTOR_VERSION, "tool_name": "threat_intel", "state": "skipped",
                    "reason": "no_supported_frozen_objects", "returned_rows": None, "truncated": False, "rows": None,
                    "actual_args": {"scope": {"alert_ids": [str(aid)], "window_start": now.isoformat(), "window_end": now.isoformat()},
                                    "parameters": {"selectors": [], "source_scope": "tenant_only"}}, "limitations": []}
                await artifact(store, run, fid, "tool_response", body, now, [], step_id=sid, schema_version=ALERT_EXECUTOR_VERSION)
                await store.db.execute(update(m.RunSteps).where(m.RunSteps.id == sid).values(
                    output_artifact_id=fid, state="completed", ended_at=now))
                queries.append((aid, run["id"], fid))
            result = AlertOutput(verdict="needs_review", confidence=.4, score_state="available", rationale="Synthetic old analysis.",
                explanation="Synthetic explanation.", generation_method="template", recommendations=[], limitations=[],
                source_refs=[reference("alert_material", mid, "observation", "$.raw_json.process.pid")])
            await service.finish(TENANT, claim["run_id"], result)
        return iid, aids, mids, queries

    async def http_readback(iid, aids, mids, out, queries):
        from app.api.v1.endpoints import socai2_analysis as analysis
        from app.api.v1.endpoints import socai2_pages as pages
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        app = FastAPI()
        def dependency(value):
            def get():
                return value
            return get
        for module, instance in ((analysis, reader), (pages, PageReadService(service.sessions))):
            app.include_router(module.router)
            app.dependency_overrides[module.get_service] = dependency(instance)
            app.dependency_overrides[module.User.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=TENANT)
        paths = [f"/socai2/incidents/{iid}", f"/socai2/incidents/{iid}/analysis",
                 f"/socai2/incidents/{iid}/records/members", f"/socai2/incidents/{iid}/analysis/runs/{out['run_id']}/trace"]
        paths += [f"/socai2/alerts/{aid}" for aid in aids]
        paths += [f"/socai2/alerts/{aid}/materials/{mid}" for aid, mid in zip(aids, mids)]
        paths += [f"/socai2/alerts/{aid}/analysis/runs/{rid}/artifacts/{fid}" for aid, rid, fid in queries]
        responses = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            for path in paths:
                response = await client.get(path)
                assert response.status_code == 200, (path, response.text)
                responses.append(response.json())
        assert responses[0]["facts"]["description"] == "Stored event description."
        assert responses[1]["current"]["valid_for_current_input"]
        assert responses[1]["current"]["run"]["delivery_state"] == "complete"
        assert responses[1]["current"]["result"]["diagnosis"]["delivery_assessment"]["review_items"]["state"] == "required"
        assert len(responses[1]["current"]["result"]["diagnosis"]["findings"]) == 3
        assert responses[2]["total"] == 2
        for value in responses[4:6]:
            assert value["facts"]["description"] == "Stored collector description."
        for value in responses[-2:]:
            assert value["availability"] == "available" and value["content_json"]["returned_rows"] is None
        return len(paths)

    async def delivery_readback(iid, out, state, delivery):
        """Verify the existing HTTP entry, saved result and Run agree."""
        from app.api.v1.endpoints import socai2_analysis as api
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        app = FastAPI()
        app.include_router(api.router)
        app.dependency_overrides[api.get_service] = lambda: reader
        app.dependency_overrides[api.User.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=TENANT)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            response = await client.get(f"/socai2/incidents/{iid}/analysis/runs/{out['run_id']}")
        assert response.status_code == 200, response.text
        value = response.json()
        assert value["run"]["state"] == state and value["run"]["delivery_state"] == delivery
        stored = (await rows(D, D.c.id == out["diagnosis_id"]))[0]
        assert value["result"]["diagnosis"] == stored["diagnosis"]
        metadata = (stored["diagnosis"] or {}).get("delivery_assessment")
        if metadata is not None:
            validate_diagnosis_contract(stored["diagnosis"])
            assert metadata["state"] == delivery
        return value

    async def test_boundary_freeze_save_and_existing_gets():
        with policy():
            iid, aids, mids, queries = await fixture()
            before = [await rows(A, A.c.id == aid) for aid in aids]
            gateway = Gateway(service, iid)
            out = await service.execute_incident(TENANT, iid, uuid4(), gateway=gateway)
            assert out["state"] == "completed" and gateway.calls == 1
            frozen = (await rows(F, F.c.id == out["input_artifact_id"]))[0]["content_json"]
            assert sum(map(len, frozen["triage_queries"].values())) == 2
            arts = await rows(F, F.c.run_id == out["run_id"])
            request = next(a["content_json"] for a in arts if a["kind"] == "model_request")
            response = next(a["content_json"] for a in arts if a["kind"] == "model_response")
            assert request["body"] == gateway.requests[0] and response["raw"] == gateway.responses[0]
            assert set(request["incident_boundary"]["member_aliases"]) == set(map(str, aids))
            diagnosis = (await rows(D, D.c.id == out["diagnosis_id"]))[0]["diagnosis"]
            validate_diagnosis_contract(diagnosis)
            delivery = diagnosis["delivery_assessment"]
            assert delivery["state"] == "complete" and delivery["review_items"]["state"] == "required"
            assert set(delivery["member_coverage"]["analyzed_ids"]) == set(map(str, aids))
            publication = next(a["content_json"] for a in arts if a["kind"] == "source_snapshot")
            assert publication["delivery_assessment"] == delivery
            assert {r["id"] for r in diagnosis["source_refs"] if r["role"] == "execution_receipt"} == {str(q[2]) for q in queries}
            assert all(q["outcome"] == "not_queried" for q in diagnosis["program_facts"]["query_statuses"])
            assert await service.freshness(TENANT, out["run_id"])
            assert before == [await rows(A, A.c.id == aid) for aid in aids]
            gets = await http_readback(iid, aids, mids, out, queries)
            # Idempotent replay cannot dispatch a second request.
            existing = (await rows(R, R.c.id == out["run_id"]))[0]
            assert existing["delivery_state"] == "complete"
            assert all([(await rows(R, R.c.id == rid))[0]["delivery_state"] == "partial" for _, rid, _ in queries])
            replay = await service.execute_incident(TENANT, iid, UUID(existing["operation_key"]), gateway=gateway)
            assert replay["run_id"] == out["run_id"] and gateway.calls == 1
            return {"incident_id": str(iid), "run_id": str(out["run_id"]), "http_gets": gets,
                    "synthetic_model_calls": 1, "real_model_calls": 0, "frozen_query_receipts": 2}

    async def test_boundary_invalid_member_preserves_partial_and_previous():
        with policy():
            iid, _, _, _ = await fixture()
            good = await service.execute_incident(TENANT, iid, uuid4(), gateway=Gateway(service, iid))
            bad_gateway = Gateway(service, iid, bad_member=True)
            bad = await service.execute_incident(TENANT, iid, uuid4(), gateway=bad_gateway)
            assert bad["state"] == "failed" and bad_gateway.calls == 1
            assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] == good["diagnosis_id"]
            entry = await reader.read_entry(TENANT, "incident_diagnosis", iid, bad["run_id"])
            partial = entry.partial_analysis.content
            assert len(partial["retained_analysis"]["members"]) == 1
            assert partial["retained_analysis"]["conclusion"] is None
            value = await delivery_readback(iid, bad, "failed", "partial")
            delivery = value["result"]["diagnosis"]["delivery_assessment"]
            assert "invalid_response_units_excluded" in delivery["reasons"] and delivery["review_items"]["state"] == "required"
            return {"prior_run": str(good["run_id"]), "partial_run": str(bad["run_id"]), "valid_members_retained": 1, "http_gets": 1}

    async def test_boundary_empty_and_malformed_have_no_delivery():
        with policy():
            iid, _, _, _ = await fixture()
            good = await service.execute_incident(TENANT, iid, uuid4(), gateway=Gateway(service, iid))
            runs = {}
            for mode in ("all_invalid", "malformed"):
                gateway = Gateway(service, iid, mode=mode)
                out = await service.execute_incident(TENANT, iid, uuid4(), gateway=gateway)
                assert out["state"] == "failed" and gateway.calls == 1
                value = await delivery_readback(iid, out, "failed", "none")
                assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] == good["diagnosis_id"]
                arts = await rows(F, F.c.run_id == out["run_id"])
                response = next(a["content_json"] for a in arts if a["kind"] == "model_response")
                assert response["raw"] == gateway.responses[0]
                if mode == "all_invalid":
                    delivery = value["result"]["diagnosis"]["delivery_assessment"]
                    assert "no_valid_analysis_content" in delivery["reasons"]
                    assert delivery["review_items"]["state"] == "unknown"
                else:
                    assert value["result"]["diagnosis"] is None
                runs[mode + "_run"] = str(out["run_id"])
            return {**runs, "prior_run": str(good["run_id"]), "http_gets": 2, "real_model_calls": 0}

    async def test_boundary_explicit_not_reviewed_is_partial():
        with policy():
            iid, aids, _, _ = await fixture()
            out = await service.execute_incident(TENANT, iid, uuid4(), gateway=Gateway(service, iid, mode="not_reviewed"))
            value = await delivery_readback(iid, out, "completed", "partial")
            delivery = value["result"]["diagnosis"]["delivery_assessment"]
            assert delivery["reasons"] == ["member_analysis_not_completed"]
            assert len(delivery["member_coverage"]["not_reviewed_ids"]) == 1
            assert set(delivery["member_coverage"]["expected_ids"]) == set(map(str, aids))
            assert value["is_current_pointer"]  # Publication eligibility remains the existing rule.
            return {"run_id": str(out["run_id"]), "http_gets": 1, "real_model_calls": 0}

    async def test_boundary_unknown_keeps_prior_and_no_delivery():
        with policy():
            iid, _, _, _ = await fixture()
            good = await service.execute_incident(TENANT, iid, uuid4(), gateway=Gateway(service, iid))
            gateway, op = Gateway(service, iid, mode="timeout"), uuid4()
            try:
                await service.execute_incident(TENANT, iid, op, gateway=gateway)
            except TimeoutError:
                pass
            else:
                raise AssertionError("expected transport uncertainty")
            out = await service.execute_incident(TENANT, iid, op, gateway=gateway)
            value = await delivery_readback(iid, out, "unknown", "none")
            assert value["run"]["ended_at"] is None and gateway.calls == 1
            assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] == good["diagnosis_id"]
            return {"unknown_run": str(out["run_id"]), "prior_run": str(good["run_id"]), "http_gets": 1, "real_model_calls": 0}

    async def test_boundary_new_receipt_freshness_keeps_legacy_history():
        with policy(False):
            iid, _, _, queries = await fixture()
            old = await service.execute_incident(TENANT, iid, uuid4(), gateway=LegacyGateway())
            assert old["state"] == "completed"
        with policy():
            current = await service.execute_incident(TENANT, iid, uuid4(), gateway=Gateway(service, iid))
            assert current["state"] == "completed" and await service.freshness(TENANT, current["run_id"])
            assert await service.freshness(TENANT, old["run_id"])
            # An orphan artifact is not an executed tool receipt. Completed
            # original artifacts remain immutable, including in this test.
            async with service.transaction(TENANT) as store:
                fid = queries[0][2]
                row = await store.one(select(F).where(*store.where(F, F.c.id == fid)))
                body = copy.deepcopy(row["content_json"])
                body["reason"] = "synthetic_orphan_receipt"
                run = await store.one(select(R).where(*store.where(R, R.c.id == queries[0][1])))
                await artifact(store, run, uuid4(), "tool_response", body, await store.now(), [], schema_version=ALERT_EXECUTOR_VERSION)
            assert await service.freshness(TENANT, current["run_id"])
            assert await service.freshness(TENANT, old["run_id"])
            old_source = (await rows(F, F.c.id == old["input_artifact_id"]))[0]["content_json"]
            assert "query_receipts_version" not in old_source
            async with service.transaction(TENANT) as store:
                await store.db.execute(update(A).where(*store.where(A, A.c.id == queries[0][0])).values(
                    description="Synthetic changed source description."))
            assert not await service.freshness(TENANT, current["run_id"])
            assert not await service.freshness(TENANT, old["run_id"])
            page = await reader.read_page(TENANT, "incident_diagnosis", iid)
            assert page.current.freshness == "stale" and not page.current.valid_for_current_input
            old_entry = await reader.read_entry(TENANT, "incident_diagnosis", iid, old["run_id"])
            assert old_entry.freshness == "stale"
            assert (await rows(F, F.c.id == old["input_artifact_id"]))[0]["content_json"] == old_source
            return {"legacy_run": str(old["run_id"]), "candidate_run": str(current["run_id"]), "legacy_contract_preserved": True}

    async def test_boundary_field_reads_and_member_pagination_preserve_values():
        from app.api.v1.endpoints import socai2_analysis as analysis
        from app.api.v1.endpoints import socai2_pages as pages
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        with policy():
            iid, aids, mids, _ = await fixture(extra_raw={"cloud": {"mfa_enabled": False, "permissions_after": []}})
            before = [await rows(A, A.c.id.in_(aids)), await rows(m.AlertMaterials.__table__, m.AlertMaterials.id.in_(mids))]
            async with service.transaction(TENANT, readonly=True) as store:
                matches = (await store.db.execute(select(A.c.id).where(*store.where(A,
                    A.c.id.in_(aids), A.c.description.ilike("%collector description%"))))).scalars().all()
                assert set(matches) == set(aids)
            app = FastAPI()
            app.include_router(pages.router)
            app.include_router(analysis.router)
            page_reader = PageReadService(service.sessions)
            app.dependency_overrides[pages.get_service] = lambda: page_reader
            app.dependency_overrides[analysis.get_service] = lambda: reader
            for module in (pages, analysis):
                app.dependency_overrides[module.User.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=TENANT)
            gets = 0
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
                async def get(path, expected=200):
                    nonlocal gets
                    response = await client.get('/socai2/' + path)
                    assert response.status_code == expected, response.text
                    gets += 1
                    return response.json()
                empty = await get(f"incidents/{iid}/analysis")
                assert empty["current"] is None and empty["entries"] == []
                out = await service.execute_incident(TENANT, iid, uuid4(), gateway=Gateway(service, iid))
                current = await get(f"incidents/{iid}/analysis")
                assert current["current"]["run"]["id"] == str(out["run_id"])
                diagnosis = current["current"]["result"]["diagnosis"]
                assert {f["id"] for f in diagnosis["findings"] if f["id"].startswith("member:")} == {"member:" + str(aid) for aid in aids}
                first = await get(f"incidents/{iid}/records/members?limit=1")
                second = await get(f"incidents/{iid}/records/members?limit=1&offset={first['next_offset']}")
                assert first["total"] == second["total"] == 2 and second["next_offset"] is None
                assert {first["items"][0]["id"], second["items"][0]["id"]} == set(map(str, aids))
                for aid, mid in zip(aids, mids):
                    value = await get(f"alerts/{aid}")
                    assert value["facts"]["description"] == "Stored collector description."
                    content = await get(f"alerts/{aid}/materials/{mid}")
                    raw = content["content_json"]
                    assert content["content_text"] == "Synthetic raw text."
                    assert raw["raw_json"]["email"] == {"id": "business-message", "size": 0}
                    assert raw["raw_json"]["cloud"] == {"mfa_enabled": False, "permissions_after": []}
                    linked = await get(f"alerts/{aid}/records/incidents")
                    assert linked["items"][0]["id"] == str(iid)
                await get(f"alerts/{aids[0]}/materials/{mids[1]}", 404)
                await get(f"incidents/{uuid4()}", 404)
                for section in ("objects", "sources", "comments", "responses"):
                    value = await get(f"incidents/{iid}/records/{section}")
                    assert value["items"] == [] and value["total"] == 0 and value["next_offset"] is None
            after = [await rows(A, A.c.id.in_(aids)), await rows(m.AlertMaterials.__table__, m.AlertMaterials.id.in_(mids))]
            assert before == after
            request = next(a["content_json"] for a in await rows(F, F.c.run_id == out["run_id"]) if a["kind"] == "model_request")
            user = request["body"]["messages"][-1]["content"]
            assert "Stored collector description." in user and "business-message" in user
            assert "mfa_enabled" in user and "false" in user and "permissions_after" in user
            return {"run_id": str(out["run_id"]), "http_gets": gets, "original_rows_equal": True,
                    "description_sql_lookup": True, "text_search_http_parameter": False, "real_model_calls": 0}

    async def test_boundary_missing_material_and_unprocessed_empty_states():
        from app.socai2.incident_model_boundary import build
        from app.socai2.stage_result_contracts import INCIDENT_EXECUTOR_VERSION
        with policy():
            iid, aid = uuid4(), uuid4()
            async with service.transaction(TENANT) as store:
                await store.db.execute(insert(I).values(id=iid, tenant_id=TENANT, source_namespace="synthetic.empty",
                    source_incident_id=str(iid), title="Synthetic missing material event"))
                await store.db.execute(insert(A).values(id=aid, tenant_id=TENANT, source_namespace="synthetic.empty",
                    source_identity_key=str(aid), title="Synthetic missing material alert", description=None))
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=TENANT, incident_id=iid, alert_id=aid,
                    membership_source="fusion", correlation_basis={"reason": "synthetic fixed scope"},
                    basis_version="synthetic", source_operation_id=uuid4()))
            page = PageReadService(service.sessions)
            alert = await page.read(TENANT, "alerts", aid, "view")
            event = await reader.read_page(TENANT, "incident_diagnosis", iid)
            assert alert.material is None and alert.triage is None and alert.facts.description is None
            assert event.current is None and event.entries == []
            claim = await service.begin(TENANT, "incident_diagnosis", iid, uuid4(), producer=INCIDENT_EXECUTOR_VERSION, limits=None)
            source = (await rows(F, F.c.id == claim["input_artifact_id"]))[0]["content_json"]
            prepared = build(source, claim["input_artifact_id"], runtime_policy.active_policy().incident_io)[-1]
            member = prepared["data"]["members"][0]
            assert member["stored_material_state"] == "unavailable" and not member["triage_eligible"] and not member["queries_available"]
            assert all(s["ref"]["role"] != "execution_receipt" for s in prepared["source_map"].values())
            await service.stop(TENANT, claim["run_id"], state="cancelled", code="synthetic_input_read_check_only")
            assert (await rows(R, R.c.id == claim["run_id"]))[0]["delivery_state"] == "none"
            assert (await rows(I, I.c.id == iid))[0]["latest_diagnosis_id"] is None
            return {"run_id": str(claim["run_id"]), "real_model_calls": 0, "missing_preserved": True, "fake_query_receipts": 0}

    async def test_boundary_namespaced_citation_policy_saves_business_text():
        with policy():
            iid, aids, mids, queries = await fixture(extra_raw={"cloud": {"service": "S3", "configuration_changed": True}})
            gateway = Gateway(service, iid, mode="business_name")
            out = await service.execute_incident(TENANT, iid, uuid4(), gateway=gateway)
            assert out["state"] == "completed" and gateway.calls == 1
            entry = await reader.read_entry(TENANT, "incident_diagnosis", iid, out["run_id"])
            assert entry.run.delivery_state == "complete" and entry.result.summary == "S3 存储桶配置记录需要业务复核。"
            arts = await rows(F, F.c.run_id == out["run_id"])
            request = next(a["content_json"] for a in arts if a["kind"] == "model_request")
            response = next(a["content_json"] for a in arts if a["kind"] == "model_response")
            assert request["incident_boundary"]["output_validation"] == {"prose_alias_format": "namespaced_v1"}
            assert response["raw"] == gateway.responses[0]
            gets = await http_readback(iid, aids, mids, out, queries)
            return {"run_id": str(out["run_id"]), "http_gets": gets, "real_model_calls": 0,
                    "business_text_preserved": True, "delivery": "complete", "review": "required"}

    for name, check in list(locals().items()):
        if name.startswith("test_boundary_") and (not only or name in only):
            try:
                detail = await asyncio.wait_for(check(), 120)
                record(name, True, detail)
            except Exception:  # noqa: BLE001 -- keep each actual failure in the receipt
                record(name, False, traceback.format_exc())
