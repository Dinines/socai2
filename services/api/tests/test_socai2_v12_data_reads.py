"""Actual PostgreSQL and HTTP checks for stored sources and Case activities."""
import asyncio
import traceback
from uuid import UUID, uuid4

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_cases, socai2_pages
from app.models import socai2 as m
from app.socai2.baseline_contracts import Actor
from app.socai2.baseline_store import digest, encoded
from app.socai2.case_service import CaseService
from app.socai2.page_reader import PageReadService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)


async def run_checks(engine, record, only=None):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, pages = CaseService(sessions), PageReadService(sessions)
    app = FastAPI()
    # Both orders have distinct source-artifact paths; case routes are not
    # accidentally captured by an alerts/incidents-only parameter validator.
    app.include_router(socai2_pages.router, prefix="/api/v1")
    app.include_router(socai2_cases.router, prefix="/api/v1")
    principal = CurrentUser(USER, T, "analyst", "synthetic@test.invalid", scopes=["alerts:read", "cases:read"])
    app.dependency_overrides[get_current_user] = lambda: principal
    app.dependency_overrides[socai2_cases.get_service] = lambda: cases
    app.dependency_overrides[socai2_pages.get_service] = lambda: pages

    async def fixture():
        cid, iid, aid, other = (uuid4() for _ in range(4))
        async with cases.transaction(T) as s:
            await s.db.execute(insert(m.Cases).values(id=cid, tenant_id=T, title="synthetic read case", created_by=USER))
            await s.db.execute(insert(m.Incidents).values(id=iid, tenant_id=T, title="synthetic read incident",
                source_namespace="v12-read", source_incident_id=str(iid)))
            for identity in (aid, other):
                await s.db.execute(insert(m.Alerts).values(id=identity, tenant_id=T, title="synthetic read alert",
                    source_namespace="v12-read", source_identity_key=str(identity)))
            await s.replace_members(cid, {aid}, expected_revision=0, actor=Actor(user_id=USER, name="synthetic"), operation_id=uuid4())
            await s.db.execute(insert(m.CaseIncidents).values(id=uuid4(), tenant_id=T, case_id=cid,
                incident_id=iid, linked_by=USER, source_operation_id=uuid4()))
        return cid, iid, aid, other

    async def save_source(s, key, parent, value, *, state="complete", size_override=None):
        identity, raw = uuid4(), encoded(value)
        await s.db.execute(insert(m.Artifacts).values(id=identity, tenant_id=T, **{key: parent},
            run_id=None, kind="source_snapshot", schema_version="synthetic.source.v1", content_json=value,
            mime_type="application/json", sha256=digest(value), size_bytes=len(raw) if size_override is None else size_override, captured_at=await s.now(),
            material_state=state, source_refs=[], retention={"truncated": state != "complete"}))
        return identity

    async def get(client, path, status=200):
        response = await client.get("/api/v1/socai2/" + path)
        assert response.status_code == status, (response.status_code, response.text)
        return response.json()

    async def test_v12_non_run_sources_are_bound_to_subject_version_and_hash():
        cid, iid, aid, other = await fixture()
        async with cases.transaction(T) as s:
            alert_source = await save_source(s, "alert_id", aid, {"version": 1, "original": "exact alert source"})
            incident_source = await save_source(s, "incident_id", iid, {"version": 2, "original": "exact incident source"})
            case_source = await save_source(s, "case_id", cid, {"version": 3, "original": "retained case source"}, state="truncated")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            directory = await get(client, f"alerts/{aid}/records/source_artifacts")
            assert directory["total"] == 1 and directory["items"][0]["id"] == str(alert_source)
            assert "content_json" not in directory["items"][0]
            body = await get(client, f"alerts/{aid}/artifacts/{alert_source}")
            assert body["availability"] == "available" and body["content_json"]["version"] == 1
            assert (await get(client, f"incidents/{iid}/artifacts/{incident_source}"))["content_json"]["version"] == 2
            assert (await get(client, f"cases/{cid}/artifacts/{case_source}"))["availability"] == "retained_truncated"
            await get(client, f"alerts/{other}/artifacts/{alert_source}", 404)
            await get(client, f"cases/{cid}/artifacts/{alert_source}", 404)
            async with cases.transaction(T) as s:
                invalid = await save_source(s, "alert_id", aid, {"invalid_size_fixture": True}, size_override=1)
            body = await get(client, f"alerts/{aid}/artifacts/{invalid}")
            assert body["availability"] == "content_integrity_mismatch" and body["content_json"] is None
            principal.tenant_id = OTHER
            try:
                await get(client, f"cases/{cid}/artifacts/{case_source}", 404)
                await get(client, f"alerts/{aid}/artifacts/{alert_source}", 404)
            finally:
                principal.tenant_id = T
        return {"non_run_sources": 3, "wrong_parent_and_tenant_rejected": True, "hash_size_enforced": True}

    async def test_v12_case_activities_include_members_once_and_get_never_writes():
        cid, iid, aid, other = await fixture()
        ids = [uuid4() for _ in range(4)]
        async with cases.transaction(T) as s:
            for identity, field, parent in zip(ids,
                    ("subject_case_id", "subject_alert_id", "subject_incident_id", "subject_alert_id"),
                    (cid, aid, iid, other), strict=True):
                await s.db.execute(insert(m.Activities).values(id=identity, tenant_id=T, operation_id=uuid4(),
                    actor={"type": "system", "name": "synthetic"}, action="synthetic_test", summary="synthetic",
                    detail={}, **{field: parent}))
            # This is already a matching subject; matching the target too must
            # not duplicate it in the list or count.
            await s.db.execute(insert(m.ActivityTargets).values(id=uuid4(), tenant_id=T,
                activity_id=ids[0], alert_id=aid, result_state="succeeded"))
        async with cases.transaction(T, readonly=True) as s:
            before = (await s.db.execute(select(func.count()).select_from(m.Activities))).scalar_one()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            page = await get(client, f"cases/{cid}/activities")
            listed = [v["id"] for v in page["items"]]
            assert all(str(v) in listed for v in ids[:3]) and str(ids[3]) not in listed
            assert len(listed) == len(set(listed)) == page["total"]
            first = await get(client, f"cases/{cid}/activities?limit=1")
            second = await get(client, f"cases/{cid}/activities?limit=1&offset={first['next_offset']}")
            assert first["total"] == second["total"] and first["items"][0]["id"] != second["items"][0]["id"]
            principal.tenant_id = OTHER
            try:
                await get(client, f"cases/{cid}/activities", 404)
            finally:
                principal.tenant_id = T
        async with cases.transaction(T, readonly=True) as s:
            after = (await s.db.execute(select(func.count()).select_from(m.Activities))).scalar_one()
        assert before == after
        return {"matched_subjects": 3, "duplicate_activity_count": 0, "get_writes": 0}

    for check in (test_v12_non_run_sources_are_bound_to_subject_version_and_hash,
                  test_v12_case_activities_include_members_once_and_get_never_writes):
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 60)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- preserve original test failure
            record(check.__name__, False, traceback.format_exc())
