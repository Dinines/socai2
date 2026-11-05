"""A/I read + C1 freshness checks on isolated PG; no model/external calls."""
import asyncio
import traceback
from unittest.mock import patch
from uuid import UUID, uuid4, uuid5

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_analysis as api
from app.models import socai2 as m
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_model_view import candidates
from app.socai2.stage_read_contracts import StagePage
from app.socai2.stage_reader import StageReader, StageReadService
from app.socai2.stage_result_contracts import AlertOutput, IncidentOutput
from app.socai2.stage_results import AS, A, F, I, StageResultService
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
LIMITS = Limits(max_model_calls=0, max_tokens=0, max_tool_calls=0, max_rows_per_query=0,
    deadline_at=None, policy_version="synthetic.read-only")


async def run_checks(engine, record, only=None):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    writer, reader = StageResultService(sessions), StageReadService(sessions)
    principal = CurrentUser(USER, T, "analyst", "synthetic@example.invalid", scopes=["alerts:read"])
    app = FastAPI()
    app.include_router(api.router, prefix="/api/v1")
    async def user():
        return principal
    app.dependency_overrides[get_current_user] = user
    app.dependency_overrides[api.get_service] = lambda: reader
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local")

    async def get(path, status=200):
        r = await client.get("/api/v1/socai2/" + path)
        assert r.status_code == status, (r.status_code, r.text)
        return r.json()

    async def fixture():
        aid, iid, mid = uuid4(), uuid4(), uuid4()
        async with writer.transaction(T) as s:
            await s.db.execute(insert(A).values(id=aid, tenant_id=T, title="synthetic read alert", source_namespace="stage-read",
                source_identity_key=str(aid)))
            await material(s, aid, mid, 1)
            await s.db.execute(insert(I).values(id=iid, tenant_id=T, title="synthetic read incident",
                source_namespace="stage-read", source_incident_id=str(iid)))
            await s.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=T, alert_id=aid, incident_id=iid,
                membership_source="fusion", correlation_basis={}, basis_version="synthetic", source_operation_id=uuid4()))
        return aid, iid, mid

    async def material(s, aid, mid, revision):
        await s.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=T, alert_id=aid, revision=revision,
            raw_json={"pid": 42, "sentinel": "do-not-include-raw-in-C1-freshness"}, detection={}, source_scope={},
            material_state="complete", retention={}))
        await s.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))

    async def begin(kind, identity):
        return await writer.begin(T, kind, identity, uuid4(), producer="synthetic.reader.v1", limits=LIMITS)

    async def finish(kind, claim, mid):
        ref = {"type": "alert_material", "id": mid, "external": None, "source_path": "$.raw_json.pid", "row_keys": [], "role": "observation"}
        out = AlertOutput(verdict="needs_review", rationale="synthetic rationale", score_state="not_computed", confidence=None,
            explanation="synthetic explanation", generation_method="template", source_refs=[ref], recommendations=[], limitations=[]) if kind == "alert_basic" else IncidentOutput(
            summary="synthetic diagnosis", conclusion="synthetic unresolved", findings=[], source_refs=[ref], open_questions=[], limitations=[])
        return await writer.finish(T, claim["run_id"], out)

    async def freeze(aid):
        cid = uuid4()
        actor = Actor(user_id=USER, name="synthetic")
        async with writer.transaction(T) as s:
            await s.db.execute(insert(m.Cases).values(id=cid, tenant_id=T, title="synthetic freshness Case"))
        receipt = await writer.replace_members(T, cid, [aid], expected_revision=0, actor=actor, operation_id=uuid4())
        rid = UUID(receipt["pending_run_id"])
        async def nop(_):
            return None
        await writer.start(T, cid, rid, Start(operation_key=uuid4(), expected_scope_revision=1), actor=actor,
            executor=nop, executor_version="synthetic.no-execution", limits=LIMITS)
        ctx = await writer.read_context(T, cid, rid)
        async with writer.transaction(T) as s:
            await s.mark_unknown(cid, rid)
        return cid, rid, ctx

    async def test_read_current_results_and_explain():
        aid, iid, mid = await fixture()
        ac = await begin("alert_basic", aid); await finish("alert_basic", ac, mid)
        ic = await begin("incident_diagnosis", iid); await finish("incident_diagnosis", ic, mid)
        for path in [f"alerts/{aid}/analysis", f"incidents/{iid}/analysis"]:
            page = await get(path)
            StagePage.model_validate(page)
            assert page["current"]["valid_for_current_input"] and page["current"]["freshness"] == "current"
            assert "request_hash" not in str(page) and "do-not-include-raw-in-C1-freshness" not in str(page)
        detail = await get(f"alerts/{aid}/analysis/runs/{ac['run_id']}")
        assert detail["explanation"]["available"] and detail["result"]["confidence"] is None
        assert detail["result"]["score_state"] == "not_computed"

    async def test_c1_current_then_stale_and_historical_freeze():
        aid, iid, mid = await fixture()
        ac = await begin("alert_basic", aid); await finish("alert_basic", ac, mid)
        ic = await begin("incident_diagnosis", iid); await finish("incident_diagnosis", ic, mid)
        cid, rid, old = await freeze(aid)
        assert old.alerts[str(aid)].triage_usable and old.incidents[str(iid)].diagnosis_usable
        assert old.incidents[str(iid)].diagnosis_freshness == "current"
        assert "do-not-include-raw-in-C1-freshness" not in old.model_dump_json()
        async with writer.transaction(T) as s:
            await material(s, aid, uuid4(), 2)
        _, _, new = await freeze(aid)
        assert not new.alerts[str(aid)].triage_usable and new.alerts[str(aid)].triage_freshness == "stale"
        assert not new.incidents[str(iid)].diagnosis_usable and new.incidents[str(iid)].diagnosis_freshness == "stale"
        paths = [x["ref"]["source_path"] for x in candidates(new, uuid4(), [])]
        assert f"$.alerts.{aid}.triage" not in paths and f"$.incidents.{iid}.diagnosis" not in paths
        assert (await writer.read_context(T, cid, rid)).model_dump() == old.model_dump()
        page = await get(f"incidents/{iid}/analysis")
        assert page["current"]["is_current_pointer"] and not page["current"]["valid_for_current_input"]

    async def test_read_unknown_failed_history_and_pagination():
        aid, iid, mid = await fixture()
        first = await begin("incident_diagnosis", iid); await finish("incident_diagnosis", first, mid)
        second = await begin("incident_diagnosis", iid)
        await writer.stop(T, second["run_id"], state="failed", code="synthetic_fail")
        third = await begin("incident_diagnosis", iid)
        await writer.stop(T, third["run_id"], state="unknown", code="synthetic_unknown")
        base = f"incidents/{iid}/analysis?limit=1"
        pages, cursor = [], None
        for _ in range(3):
            page = await get(base + (f"&before_run_id={cursor}" if cursor else ""))
            pages += page["entries"]
            assert page["current"]["run"]["id"] == str(first["run_id"])
            cursor = page["next_before_run_id"]
        assert cursor is None and [e["run"]["state"] for e in pages] == ["unknown", "failed", "completed"]
        assert pages[0]["result"]["diagnosis"] is None and pages[1]["result"]["error_code"] == "synthetic_fail"
        await get(f"alerts/{aid}/analysis?before_run_id={third['run_id']}", 404)

    async def test_read_tenant_subject_permission_and_disabled():
        nonlocal principal
        aid, iid, mid = await fixture(); ac = await begin("alert_basic", aid); await finish("alert_basic", ac, mid)
        await get(f"incidents/{iid}/analysis/runs/{ac['run_id']}", 404)
        principal = CurrentUser(USER, OTHER, "analyst", "synthetic@example.invalid", scopes=["alerts:read"])
        await get(f"alerts/{aid}/analysis", 404)
        principal = CurrentUser(USER, T, "analyst", "synthetic@example.invalid", scopes=[])
        await get(f"alerts/{aid}/analysis", 403)
        principal = CurrentUser(USER, T, "analyst", "synthetic@example.invalid", scopes=["alerts:read"])
        with patch.object(api.settings, "SOCAI2_ANALYSIS_READ_ENABLED", False):
            try:
                api.get_service()
            except HTTPException as exc:
                assert exc.status_code == 503
            else:
                raise AssertionError("disabled surface opened")

    async def test_read_repeatable_snapshot_and_no_writes():
        aid, _, mid = await fixture(); ac = await begin("alert_basic", aid); await finish("alert_basic", ac, mid)
        async with reader.transaction(T, readonly=True) as s:
            view = StageReader(s, "alert_basic", aid)
            first = await view.page()
            async with writer.transaction(T) as other:
                await material(other, aid, uuid4(), 2)
            assert (await view.page()).model_dump() == first.model_dump()
        assert not (await reader.read_page(T, "alert_basic", aid)).current.valid_for_current_input
        try:
            async with reader.transaction(T, readonly=True) as s:
                await s.db.execute(update(A).where(A.c.id == aid).values(title="forbidden"))
        except DBAPIError as exc:
            assert exc.orig.sqlstate == "25006"
        else:
            raise AssertionError("read transaction allowed write")

    async def test_read_unlinked_legacy_result_is_not_current_valid():
        aid, _, mid = await fixture()
        async with writer.transaction(T) as s:
            now, tid = await s.now(), uuid4()
            await s.db.execute(insert(AS).values(id=tid, tenant_id=T, alert_id=aid, input_material_id=mid,
                kind="triage", verdict="needs_review", rationale="synthetic legacy", score_state="not_provided", producer="legacy",
                actor={}, assessed_at=now, operation_key=str(tid)))
            await s.db.execute(update(A).where(A.c.id == aid).values(latest_triage_id=tid))
        page = await get(f"alerts/{aid}/analysis")
        assert page["current_pointer_id"] == str(tid) and page["current"] is None
        assert page["current_unavailable_reason"] == "current_pointer_without_verifiable_run"
        _, _, ctx = await freeze(aid)
        assert ctx.alerts[str(aid)].triage and not ctx.alerts[str(aid)].triage_usable

    async def test_read_explanation_integrity_rejected():
        aid, _, mid = await fixture(); claim = await begin("alert_basic", aid)
        async with writer.transaction(T) as s:
            tid, now = uuid4(), await s.now()
            await s.db.execute(insert(AS).values(id=tid, tenant_id=T, alert_id=aid, input_material_id=mid,
                source_run_id=claim["run_id"], kind="triage", verdict="needs_review", score_state="not_provided", producer="synthetic",
                actor={}, assessed_at=now, operation_key=str(tid)))
            await s.db.execute(insert(F).values(id=uuid5(claim["run_id"], "explanation"), tenant_id=T, alert_id=aid,
                run_id=claim["run_id"], kind="alert_explanation", schema_version="synthetic.corrupt", content_json={"body": "wrong hash"},
                mime_type="application/json", sha256="0"*64, size_bytes=1, captured_at=now, material_state="complete", source_refs=[], retention={}))
        result = await get(f"alerts/{aid}/analysis/runs/{claim['run_id']}")
        assert result["explanation"]["reason"] == "content_integrity_mismatch" and result["explanation"]["content"] is None

    checks = [v for k, v in locals().copy().items() if k.startswith(("test_read_", "test_c1_current"))]
    try:
        for check in checks:
            if only and check.__name__ not in only:
                continue
            try:
                detail = await asyncio.wait_for(check(), 50)
                record(check.__name__, True, detail)
            except Exception:  # noqa: BLE001 -- preserve original failures
                record(check.__name__, False, traceback.format_exc())
    finally:
        await client.aclose()
