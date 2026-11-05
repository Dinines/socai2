"""ASGI + restricted synthetic PG; authentication/model/lake are substitutes."""
import asyncio
import importlib.util
import json
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4, uuid5

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_cases as api
from app.models import socai2 as m
from app.socai2.baseline_contracts import Actor
from app.socai2.baseline_store import RES, A, C, F, R
from app.socai2.case_contracts import MemberChange
from app.socai2.case_reader import CaseReader, usage_totals
from app.socai2.case_service import CaseService
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker


def helper(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


execution = helper("test_socai2_baseline_executor")
T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic-http@example.invalid")
BASE = "/api/v1/socai2/cases"
S = m.RunSteps.__table__


async def run_checks(engine, record, only=None):
    class TestService(CaseService):
        gateway = None

        async def start_full(self, *args, **kwargs):
            kwargs.update(gateway=self.gateway or execution.PipelineGateway(), lake=execution.deep.AdaptiveLake())
            with patch("app.socai2.baseline_enrichment.sources.CONNECTED", frozenset()):
                return await super().start_full(*args, **kwargs)

    service = TestService(async_sessionmaker(engine, expire_on_commit=False))
    principal = CurrentUser(USER, T, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
    app = FastAPI()
    app.include_router(api.router, prefix="/api/v1")
    async def user():
        return principal
    app.dependency_overrides[get_current_user] = user
    app.dependency_overrides[api.get_service] = lambda: service
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local")

    async def request(method, path, *, code=200, **kwargs):
        response = await client.request(method, path, **kwargs)
        assert response.status_code == code, (response.status_code, response.text)
        return response.json()

    async def rows(query, tenant=T):
        async with service.transaction(tenant) as store:
            return [dict(r) for r in (await store.db.execute(query)).mappings()]

    async def alert(tenant=T):
        aid, mid, host = uuid4(), uuid4(), "synthetic-" + uuid4().hex
        async with service.transaction(tenant) as store:
            now = await store.now()
            await store.db.execute(insert(A).values(id=aid, tenant_id=tenant, title="synthetic HTTP alert",
                source_namespace="case-http-fixture", source_identity_key=str(aid)))
            await store.db.execute(insert(m.AlertMaterials.__table__).values(id=mid, tenant_id=tenant, alert_id=aid,
                revision=1, ocsf_json=execution.lake.original(host), detection={}, source_scope={}, material_state="complete", retention={}))
            await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
            await store.db.execute(insert(m.AlertObjects.__table__).values(id=uuid4(), tenant_id=tenant, alert_id=aid,
                material_id=mid, object_type="host", object_role="entity", object_key="host:" + host, namespace="fixture",
                raw_value=host, normalized_value=host, source_path="$.ocsf_json.device.name", attributes={}))
        return aid, mid, now

    async def create(aids=None):
        if aids is None:
            aid, _, _ = await alert()
            aids = [aid]
        body = {"operation_key": str(uuid4()), "title": "synthetic HTTP Case", "alert_ids": list(map(str, aids))}
        out = await request("POST", BASE, json=body)
        return out, body

    async def start_body(revision=1):
        async with service.transaction(T) as store:
            now = await store.now()
        return {"operation_key": str(uuid4()), "expected_scope_revision": revision,
            "window_start": (now - timedelta(minutes=5)).isoformat(), "window_end": (now + timedelta(minutes=5)).isoformat()}

    async def test_http_create_idempotency_pending_and_atomic_member_failure():
        aid, _, _ = await alert()
        body = {"operation_key": str(uuid4()), "title": "synthetic create once", "alert_ids": [str(aid)]}
        first, second = await asyncio.gather(request("POST", BASE, json=body), request("POST", BASE, json=body))
        assert first == second
        cid, rid = first["case_id"], first["pending_run_id"]
        detail = await request("GET", f"{BASE}/{cid}")
        assert detail["member_count"] == 1 and detail["case"]["created_by"] == str(USER)
        run = await request("GET", f"{BASE}/{cid}/runs/{rid}")
        assert run["run"]["state"] == "pending_update" and run["run"]["started_at"] is None
        assert run["run"]["trigger"] == "case_created" and run["run"]["purpose"] == "建立案件的初始分析"
        assert run["result_ids"] == [] and run["start_eligibility"]["can_start"]
        history = await request("GET", f"{BASE}/{cid}/history")
        assert len(history["items"]) == 1 and history["items"][0]["result"] is None
        assert (await request("POST", BASE, json={**body, "title": "changed"}, code=409))["detail"] == "operation_key_conflict"
        for bad in ({**body, "tenant_id": str(OTHER)}, {**body, "alert_ids": [str(aid), str(aid)]}, {**body, "title": "   "}):
            await request("POST", BASE, json=bad, code=422)
        foreign, _, _ = await alert(OTHER)
        failed = {**body, "operation_key": str(uuid4()), "alert_ids": [str(aid), str(foreign)]}
        assert (await request("POST", BASE, json=failed, code=404))["detail"] == "member_alert_not_found"
        derived = uuid5(T, "socai2.case.create:" + failed["operation_key"])
        assert not await rows(select(C).where(C.c.id == derived))
        change = {"operation_key": str(uuid4()), "expected_scope_revision": 1, "alert_ids": [str(foreign)]}
        await request("PUT", f"{BASE}/{cid}/members", json=change, code=404)
        assert (await request("GET", f"{BASE}/{cid}"))["case"]["scope_revision"] == 1
        assert len(await rows(select(R).where(R.c.case_id == UUID(cid)))) == 1

    async def test_http_full_delivery_reports_frozen_material_and_read_only():
        aid, mid, _ = await alert()
        out, _ = await create([aid])
        cid, rid = out["case_id"], out["pending_run_id"]
        service.gateway = execution.PipelineGateway(())
        start = await start_body()
        finished = await request("POST", f"{BASE}/{cid}/runs/{rid}/start", json=start)
        assert finished["run"]["state"] == "completed" and finished["usage"]["model_calls"] == 2
        assert finished["duration_seconds"] is not None and finished["elapsed_seconds"] is None
        assert finished["usage"]["unpriced_model_calls"] == 2 and finished["usage"]["total_tokens"] == 2000
        result_id = finished["result_ids"][0]
        result = await request("GET", f"{BASE}/{cid}/results/{result_id}")
        assert result["result"]["validation_state"] == "accepted" and result["result"]["delivery_state"] == "partial"
        assert result["delivery"]["detail"]["result_id"] == result_id
        paths = [result["result"]["report_artifact_id"], result["result"]["graph_artifact_id"],
            result["delivery"]["detail_artifact_id"], result["delivery"]["markdown_artifact_id"]]
        for artifact_id in paths:
            artifact = await request("GET", f"{BASE}/{cid}/runs/{rid}/artifacts/{artifact_id}")
            assert artifact["availability"] == "available"
        other_mid = uuid4()
        async with service.transaction(T) as store:
            await store.db.execute(insert(m.AlertMaterials.__table__).values(id=other_mid, tenant_id=T, alert_id=aid,
                revision=2, raw_text="new material after frozen run", detection={}, source_scope={}, material_state="complete", retention={}))
            await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=other_mid))
        old = await request("GET", f"{BASE}/{cid}/runs/{rid}/materials/{mid}")
        assert old["id"] == str(mid) and old["ocsf_json"]["process"]["pid"] == 4209
        await request("GET", f"{BASE}/{cid}/runs/{rid}/materials/{other_mid}", code=404)
        before = (await rows(select(C).where(C.c.id == UUID(cid))))[0]
        current = await request("GET", f"{BASE}/{cid}")
        assert current["current_assessment"]["covers_current_members"] is True
        assert (await request("GET", f"{BASE}/{cid}/history"))["items"][0]["result"]["id"] == result_id
        replay = await request("POST", f"{BASE}/{cid}/runs/{rid}/start", json=start)
        assert replay["result_ids"] == [result_id] and service.gateway.order == ["C3", "C6"]
        assert (await rows(select(C).where(C.c.id == UUID(cid))))[0] == before
        another, _ = await create()
        for suffix in (f"runs/{rid}", f"results/{result_id}", f"runs/{another['pending_run_id']}/artifacts/{paths[0]}"):
            await request("GET", f"{BASE}/{another['case_id']}/{suffix}", code=404)
        return {"case_id": cid, "run_id": rid, "result_id": result_id, "model_calls": 2}

    async def test_http_permissions_feature_flag_actor_and_tenant_isolation():
        nonlocal principal
        out, body = await create()
        original = principal
        try:
            principal = CurrentUser(USER, T, "viewer", ACTOR.name, scopes=["cases:read"])
            await request("GET", f"{BASE}/{out['case_id']}")
            await request("POST", BASE, json=body, code=403)
            await request("PUT", f"{BASE}/{out['case_id']}/members", json={"operation_key": str(uuid4()),
                "expected_scope_revision": 1, "alert_ids": []}, code=403)
            await request("POST", f"{BASE}/{out['case_id']}/runs/{out['pending_run_id']}/start", json=await start_body(), code=403)
            principal = CurrentUser(USER, OTHER, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
            await request("GET", f"{BASE}/{out['case_id']}", code=404)
            own, _, _ = await alert(OTHER)
            await request("POST", BASE, json={**body, "operation_key": str(uuid4()), "alert_ids": [str(own)]}, code=403)
            principal = original
            with patch.object(api.settings, "SOCAI2_CASE_API_ENABLED", False):
                del app.dependency_overrides[api.get_service]
                await request("GET", f"{BASE}/{out['case_id']}", code=503)
            async def unauthorized():
                raise HTTPException(401, "synthetic missing authentication")
            app.dependency_overrides[api.get_service] = lambda: service
            app.dependency_overrides[get_current_user] = unauthorized
            await request("GET", f"{BASE}/{out['case_id']}", code=401)
        finally:
            principal = original
            app.dependency_overrides[get_current_user] = user
            app.dependency_overrides[api.get_service] = lambda: service

    async def test_http_active_run_scope_coalesces_and_requires_manual_successor():
        out, body = await create()
        cid, rid = out["case_id"], out["pending_run_id"]
        entered, release = asyncio.Event(), asyncio.Event()
        async def pause():
            entered.set()
            await release.wait()
        service.gateway = execution.PipelineGateway((), hook=pause)
        start = await start_body()
        running = asyncio.create_task(request("POST", f"{BASE}/{cid}/runs/{rid}/start", json=start))
        try:
            await asyncio.wait_for(entered.wait(), 25)
            observed = await request("GET", f"{BASE}/{cid}/runs/{rid}")
            assert observed["run"]["state"] == "running" and observed["run"]["input_artifact_id"]
            assert observed["duration_seconds"] is None and observed["elapsed_seconds"] is not None
            second, _, _ = await alert()
            third, _, _ = await alert()
            members = body["alert_ids"] + [str(second)]
            pending = await request("PUT", f"{BASE}/{cid}/members", json={"operation_key": str(uuid4()),
                "expected_scope_revision": 1, "alert_ids": members})
            again = await request("PUT", f"{BASE}/{cid}/members", json={"operation_key": str(uuid4()),
                "expected_scope_revision": 2, "alert_ids": members + [str(third)]})
            assert pending["pending_run_id"] == again["pending_run_id"]
            next_id = again["pending_run_id"]
            await request("POST", f"{BASE}/{cid}/runs/{next_id}/start", json=await start_body(3), code=409)
            assert (await request("GET", f"{BASE}/{cid}/runs/{next_id}"))["start_eligibility"]["reason"] == "baseline_active"
        finally:
            release.set()
            finished = await running
        assert finished["input_member_count"] == 1 and finished["current_member_count"] == 3
        next_run = await request("GET", f"{BASE}/{cid}/runs/{next_id}")
        assert next_run["run"]["state"] == "pending_update" and next_run["steps"] == []
        assert next_run["start_eligibility"]["can_start"]
        assert (await request("GET", f"{BASE}/{cid}"))["current_assessment"] is None
        assert service.gateway.order == ["C3", "C6"]

    async def test_http_transport_failure_is_sanitized_and_unknown_remains_visible():
        out, _ = await create()
        cid, rid = out["case_id"], out["pending_run_id"]
        async def broken():
            raise RuntimeError("synthetic provider secret must not appear")
        service.gateway = execution.PipelineGateway(hook=broken)
        start = await start_body()
        response = await request("POST", f"{BASE}/{cid}/runs/{rid}/start", json=start, code=503)
        assert "provider secret" not in json.dumps(response)
        observed = await request("GET", f"{BASE}/{cid}/runs/{rid}")
        assert observed["run"]["state"] == "unknown" and not observed["start_eligibility"]["can_start"]
        assert observed["usage"]["total_tokens"] is None and observed["usage"]["unknown_token_calls"] == 1
        assert observed["result_ids"] == []
        replay = await request("POST", f"{BASE}/{cid}/runs/{rid}/start", json=start)
        assert replay["run"]["state"] == "unknown" and service.gateway.order == ["C3"]

    async def test_http_rejects_budget_injection_and_stale_scope_before_claim():
        out, _ = await create()
        path = f"{BASE}/{out['case_id']}/runs/{out['pending_run_id']}/start"
        body = await start_body()
        for changes in ({"limits": {"max_model_calls": 100}}, {"gateway": "other"}, {"tenant_id": str(OTHER)},
                {"window_start": "2026-11-01T01:00:00", "window_end": "2026-11-01T02:00:00"}):
            await request("POST", path, json={**body, **changes}, code=422)
        await request("POST", path, json={**body, "expected_scope_revision": 9}, code=409)
        run = await request("GET", f"{BASE}/{out['case_id']}/runs/{out['pending_run_id']}")
        assert run["run"]["state"] == "pending_update" and not run["artifacts"] and not run["steps"]

    async def test_read_snapshot_consistency_and_database_readonly():
        out, body = await create()
        cid, second = UUID(out["case_id"]), (await alert())[0]
        async with service.transaction(T, readonly=True) as store:
            reader, changed = CaseReader(store), False
            original = reader.rows
            async def interleave(query):
                nonlocal changed
                if not changed:
                    changed = True
                    await service.change_members(T, cid, MemberChange(operation_key=uuid4(), expected_scope_revision=1,
                        alert_ids=[UUID(body["alert_ids"][0]), second]), actor=ACTOR)
                return await original(query)
            reader.rows = interleave
            frozen = await reader.case(cid)
        assert frozen["case"].scope_revision == 1 and frozen["member_count"] == 1 and len(frozen["members"]) == 1
        assert (await request("GET", f"{BASE}/{cid}"))["case"]["scope_revision"] == 2
        try:
            async with service.transaction(T, readonly=True) as store:
                await store.db.execute(update(C).where(C.c.id == cid).values(title="must not write"))
        except DBAPIError as exc:
            assert getattr(exc.orig, "sqlstate", None) == "25006"
        else:
            raise AssertionError("GET transaction must be read only")

    async def test_usage_unknown_and_currency_groups_are_explicit():
        def step(usage):
            return {"kind": "model", "state": "completed", "usage": usage}
        reported = {"total_tokens": 30, "usage_state": "reported", "cost_state": "priced", "cost": 1.25,
            "currency": "USD", "price_version": "v1"}
        out = usage_totals([step(reported), step({**reported, "currency": "CNY"}), step(None),
            step({"usage_state": "partial", "total_tokens": 99999})], 5)
        assert out["known_total_tokens"] == 60 and out["total_tokens"] is None and out["unknown_token_calls"] == 3
        assert out["unpriced_model_calls"] == 3 and len(out["costs_by_currency_and_price_version"]) == 2
        assert {r["cost"] for r in out["costs_by_currency_and_price_version"]} == {"1.25"}

    async def test_history_saved_ai_only_stable_cursor_and_no_fake_result():
        out, _ = await create()
        cid, pending = UUID(out["case_id"]), UUID(out["pending_run_id"])
        async with service.transaction(T) as store:
            now = await store.now()
            pending_row = await store.one(select(R).where(R.c.id == pending))
            conversation, answer, run, unsaved, input_id, result_id = [uuid4() for _ in range(6)]
            await store.db.execute(insert(m.Conversations.__table__).values(id=conversation, tenant_id=T,
                case_id=cid, title="synthetic conversation", created_by=USER))
            for rid in (run, unsaved):
                actual_input = input_id if rid == run else uuid4()
                await store.db.execute(insert(R).values(id=rid, tenant_id=T, case_id=cid, kind="ai_question",
                    title="synthetic AI", purpose="synthetic question", trigger="question", state="completed",
                    scope_kind="whole_case", scope_revision=1, started_at=now, ended_at=now, requested_by=USER,
                    input_artifact_id=actual_input, executor_version="synthetic.ai.v1",
                    operation_key=str(uuid4()), request_hash="0" * 64))
                await store.save_input_artifact(cid, rid, actual_input, {"synthetic": True}, kind="input_snapshot",
                    schema="synthetic.ai.v1", captured_at=now, refs=[], actor_id=USER)
            await store.db.execute(insert(m.Messages.__table__).values(id=answer, tenant_id=T, case_id=cid,
                conversation_id=conversation, sequence=1, role="assistant", content="synthetic saved answer",
                state="completed", source_run_id=run, input_artifact_id=input_id, source_refs=[],
                client_request_key=str(uuid4()), answered_at=now))
            await store.db.execute(insert(RES).values(id=result_id, tenant_id=T, case_id=cid, kind="ai_saved",
                source_run_id=run, source_answer_id=answer, title="synthetic saved AI", purpose="synthetic question",
                conclusion=None, conclusion_state="unavailable", conclusion_origin="system", validation_state="system_only",
                closing_note="synthetic only", findings=[], questions=[], recommendations=[], change_kind="not_comparable",
                case_impact={"summary": None, "supported_changes": [], "cannot_generalize": [], "next_steps": [],
                    "affected_scope": {"kind": "whole_case", "alert_ids": [], "object_keys": [], "window_start": None,
                        "window_end": None, "limitations": []}}, input_artifact_id=input_id, delivery_state="partial",
                created_at=now, saved_at=pending_row["requested_at"], saved_by=USER, operation_key=str(uuid4())))
        first = await request("GET", f"{BASE}/{cid}/history", params={"limit": 1})
        assert first["next_cursor"]
        second = await request("GET", f"{BASE}/{cid}/history", params={"limit": 1, "cursor": first["next_cursor"]})
        assert second["next_cursor"] is None
        items = first["items"] + second["items"]
        assert {i["id"] for i in items} == {"run:" + str(pending), "result:" + str(result_id)}
        assert next(i for i in items if i["run"]["id"] == str(pending))["result"] is None
        result = await request("GET", f"{BASE}/{cid}/results/{result_id}")
        assert result["delivery"] is None
        assert result["source_answer"]["conversation_id"] == str(conversation)
        assert result["source_answer"]["id"] == str(answer)
        assert result["source_answer"]["input_artifact_id"] == str(input_id)
        await request("GET", f"{BASE}/{cid}/history", params={"cursor": "not base64!"}, code=422)
        await request("GET", f"{BASE}/{cid}/history", params={"limit": 101}, code=422)

    async def test_artifact_scope_integrity_and_external_reference_not_exposed():
        out, _ = await create()
        cid, rid = UUID(out["case_id"]), UUID(out["pending_run_id"])
        bad, external, large = uuid4(), uuid4(), uuid4()
        async with service.transaction(T) as store:
            now = await store.now()
            for identity, extra in ((bad, {"content_json": {"synthetic": True}, "size_bytes": 18}),
                    (external, {"blob_ref": "s3://synthetic-private-path", "size_bytes": 10}),
                    (large, {"content_text": "synthetic declared large", "size_bytes": 131073})):
                await store.db.execute(insert(F).values(id=identity, tenant_id=T, case_id=cid, run_id=rid,
                    kind="source_snapshot", schema_version="synthetic.read.v1", mime_type="application/json", sha256="0" * 64,
                    captured_at=now, material_state="complete", source_refs=[], retention={}, **extra))
        await request("GET", f"{BASE}/{cid}/runs/{rid}/artifacts/{bad}", code=409)
        loaded = await request("GET", f"{BASE}/{cid}/runs/{rid}/artifacts/{external}")
        assert loaded["availability"] == "external_content_not_loaded" and "private-path" not in json.dumps(loaded)
        assert (await request("GET", f"{BASE}/{cid}/runs/{rid}/artifacts/{large}"))["content_text"] is None

    async def test_run_last_record_uses_all_artifacts_when_directory_truncated():
        out, _ = await create()
        cid, rid = UUID(out["case_id"]), UUID(out["pending_run_id"])
        before = (await request("GET", f"{BASE}/{cid}"))["case"]
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(F), [{"id": uuid4(), "tenant_id": T, "case_id": cid, "run_id": rid,
                "kind": "source_snapshot", "schema_version": "synthetic.read.v1", "mime_type": "application/json",
                "content_json": {"synthetic": True}, "sha256": "0" * 64, "size_bytes": 18,
                "captured_at": now + timedelta(seconds=i), "material_state": "complete", "source_refs": [], "retention": {}}
                for i in range(201)])
        run = await request("GET", f"{BASE}/{cid}/runs/{rid}")
        assert run["artifacts_truncated"] and len(run["artifacts"]) == 200
        assert run["artifact_counts"]["source_snapshot"] == 201
        assert datetime.fromisoformat(run["last_recorded_at"]) == now + timedelta(seconds=200)
        assert run["duration_seconds"] is None and run["elapsed_seconds"] is None
        assert (await request("GET", f"{BASE}/{cid}"))["case"] == before

    checks = [test_http_create_idempotency_pending_and_atomic_member_failure,
        test_http_full_delivery_reports_frozen_material_and_read_only,
        test_http_permissions_feature_flag_actor_and_tenant_isolation,
        test_http_active_run_scope_coalesces_and_requires_manual_successor,
        test_http_transport_failure_is_sanitized_and_unknown_remains_visible,
        test_http_rejects_budget_injection_and_stale_scope_before_claim,
        test_read_snapshot_consistency_and_database_readonly,
        test_usage_unknown_and_currency_groups_are_explicit,
        test_history_saved_ai_only_stable_cursor_and_no_fake_result,
        test_artifact_scope_integrity_and_external_reference_not_exposed,
        test_run_last_record_uses_all_artifacts_when_directory_truncated]
    try:
        for check in checks:
            if only is not None and check.__name__ not in only:
                continue
            service.gateway = None
            try:
                detail = await asyncio.wait_for(check(), 240)
                record(check.__name__, True, detail)
            except Exception:  # noqa: BLE001 -- retain original synthetic failures
                record(check.__name__, False, traceback.format_exc())
    finally:
        await client.aclose()
