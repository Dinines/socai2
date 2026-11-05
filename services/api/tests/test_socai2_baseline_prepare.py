"""Explicit user preparation refreshes current facts only when later claimed."""
import asyncio
import traceback
from datetime import timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_cases as api
from app.socai2.baseline_contracts import Actor, Limits, Publication, Scope, Start
from app.socai2.baseline_store import A, C, R, StoreError
from app.socai2.case_contracts import CaseCreate, MemberChange, PrepareBaseline
from app.socai2.human_task_contracts import TaskCreate
from app.socai2.human_task_service import HumanTaskService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

TENANT, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic-prepare@example.invalid")


async def run_checks(engine, record, only=None):
    service = HumanTaskService(async_sessionmaker(engine, expire_on_commit=False))

    async def rows(table, *clauses):
        async with service.transaction(TENANT, readonly=True) as store:
            return [dict(r) for r in (await store.db.execute(select(table).where(*store.where(table, *clauses)))).mappings()]

    async def fixture():
        aid = uuid4()
        async with service.transaction(TENANT) as store:
            await store.db.execute(insert(A).values(id=aid, tenant_id=TENANT, title="synthetic prepare alert",
                source_namespace="prepare-fixture", source_identity_key=str(aid)))
        case = await service.create_case(TENANT, CaseCreate(operation_key=uuid4(), title="synthetic prepare Case",
            alert_ids=[aid]), actor=ACTOR)
        return case, aid

    def request(revision=1):
        return PrepareBaseline(operation_key=uuid4(), expected_scope_revision=revision)

    async def prepare(case, req=None):
        return await service.prepare_baseline(TENANT, case.case_id, req or request(), actor=ACTOR)

    async def claim(case, rid=None, revision=1):
        async with service.transaction(TENANT) as store:
            now = await store.now()
            return await store.claim(case.case_id, rid or case.pending_run_id,
                Start(operation_key=uuid4(), expected_scope_revision=revision, window_start=now-timedelta(minutes=1), window_end=now),
                actor=ACTOR, executor_version="synthetic.prepare.v1", limits=Limits(max_model_calls=4, max_tool_calls=4,
                    max_tokens=24000, max_rows_per_query=200, deadline_at=now+timedelta(seconds=120), policy_version="synthetic.v1"))

    async def context(case, rid=None):
        return await service.read_context(TENANT, case.case_id, rid or case.pending_run_id)

    async def complete(case, aid):
        scope = Scope(kind="whole_case", alert_ids=[aid], object_keys=[], window_start=None, window_end=None, limitations=[])
        return await service.publish(TENANT, case.case_id, case.pending_run_id, Publication(operation_key=uuid4(),
            terminal_state="completed", stop_reason="synthetic_handoff", title="synthetic completed result", conclusion=None,
            conclusion_state="unavailable", conclusion_origin="system", validation_state="system_only", closing_note="synthetic",
            findings=[], questions=[], recommendations=[], change_kind="initial", change_summary=None,
            case_impact={"summary":None,"supported_changes":[],"cannot_generalize":[],"affected_scope":scope,"next_steps":[]},
            delivery_state="partial", members=[{"alert_id":aid,"read_state":"missing","assessment_state":"unresolved",
                "conclusion_covered":False,"assessment":None,"limitations":"synthetic","evidence_refs":[]}]))

    async def reject(code, call):
        try:
            await call
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected rejection")

    async def test_prepare_reuses_pending_and_replays_original_receipt():
        case, _ = await fixture()
        before = await rows(C, C.c.id == case.case_id)
        req = request()
        first, duplicate = await asyncio.gather(prepare(case, req), prepare(case, req))
        assert first == duplicate and not first.created and first.pending_run_id == case.pending_run_id
        assert await rows(C, C.c.id == case.case_id) == before
        await claim(case)
        assert await prepare(case, req) == first
        assert len(await rows(R, R.c.case_id == case.case_id)) == 1
        await reject("operation_key_conflict", prepare(case, req.model_copy(update={"expected_scope_revision":2})))

    async def test_prepare_after_completion_consumes_human_feedback_at_claim():
        case, aid = await fixture()
        await claim(case)
        original = await context(case)
        await complete(case, aid)
        human = await service.write(TENANT, case.case_id, TaskCreate(operation_key=uuid4(), expected_scope_revision=1,
            title="confirm maintenance", state="completed", result_text="Synthetic approved maintenance for this alert.",
            result_scope=Scope(kind="selected_alerts", alert_ids=[aid], object_keys=[], window_start=None, window_end=None, limitations=[])), actor=ACTOR)
        assert len(await rows(R, R.c.case_id == case.case_id)) == 1
        first, second = await asyncio.gather(prepare(case), prepare(case))
        assert first.pending_run_id == second.pending_run_id and first.created != second.created
        pending = (await rows(R, R.c.id == first.pending_run_id))[0]
        assert pending["state"] == "pending_update" and pending["trigger"] == "manual" and pending["scope_revision"] == 1
        assert pending["started_at"] is pending["input_artifact_id"] is None
        await claim(case, first.pending_run_id)
        current = await context(case, first.pending_run_id)
        assert current.tasks[str(human.task.id)].usable_feedback
        assert current.tasks[str(human.task.id)].revision["id"] == str(human.task.current_revision_id)
        assert await context(case) == original and not original.tasks

    async def test_prepare_during_active_requires_manual_successor():
        case, aid = await fixture()
        await claim(case)
        before = await context(case)
        pending = await prepare(case)
        assert pending.created and pending.pending_run_id != case.pending_run_id
        await reject("baseline_already_active", claim(case, pending.pending_run_id))
        await complete(case, aid)
        assert (await rows(R, R.c.id == pending.pending_run_id))[0]["state"] == "pending_update"
        assert await context(case) == before
        await claim(case, pending.pending_run_id)
        assert len(await rows(R, R.c.case_id == case.case_id, R.c.state == "running")) == 1

    async def test_prepare_stale_empty_and_resolved_case():
        case, aid = await fixture()
        await reject("case_scope_revision_conflict", prepare(case, request(2)))
        await service.change_members(TENANT, case.case_id, MemberChange(operation_key=uuid4(), expected_scope_revision=1,
            alert_ids=[]), actor=ACTOR)
        await reject("baseline_scope_empty", prepare(case, request(2)))
        await service.change_members(TENANT, case.case_id, MemberChange(operation_key=uuid4(), expected_scope_revision=2,
            alert_ids=[aid]), actor=ACTOR)
        reused = await prepare(case, request(3))
        assert not reused.created and reused.pending_run_id == case.pending_run_id and reused.scope_revision == 3
        async with service.transaction(TENANT) as store:
            await store.db.execute(update(C).where(C.c.id == case.case_id).values(handling_status="resolved",
                resolved_at=await store.now(), resolved_by=USER, resolution_note="synthetic resolved"))
        await reject("resolved_case_start_policy_not_enabled", prepare(case, request(3)))
        assert len(await rows(R, R.c.case_id == case.case_id)) == 1

    async def test_prepare_http_permissions_and_no_execution():
        case, _ = await fixture()
        principal = CurrentUser(USER, TENANT, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
        app = FastAPI()
        app.include_router(api.router, prefix="/api/v1")
        async def user():
            return principal
        app.dependency_overrides[get_current_user] = user
        app.dependency_overrides[api.get_service] = lambda: service
        path = f"/api/v1/socai2/cases/{case.case_id}/baseline/prepare"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            body = request().model_dump(mode="json")
            assert (await client.post(path, json={**body,"max_model_calls":99})).status_code == 422
            principal = CurrentUser(USER, TENANT, "viewer", ACTOR.name, scopes=["cases:read"])
            assert (await client.post(path, json=body)).status_code == 403
            principal = CurrentUser(USER, TENANT, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
            response = await client.post(path, json=body)
            assert response.status_code == 200, response.text
            assert not response.json()["created"] and response.json()["pending_run_id"] == str(case.pending_run_id)
            assert (await rows(R, R.c.id == case.pending_run_id))[0]["state"] == "pending_update"
            principal = CurrentUser(USER, OTHER, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
            assert (await client.post(path, json=body)).status_code == 403
            app.dependency_overrides.pop(api.get_service)
            with patch.object(api.settings, "SOCAI2_CASE_API_ENABLED", False):
                assert (await client.post(path, json=body)).status_code == 503

    checks = [test_prepare_reuses_pending_and_replays_original_receipt,
        test_prepare_after_completion_consumes_human_feedback_at_claim, test_prepare_during_active_requires_manual_successor,
        test_prepare_stale_empty_and_resolved_case, test_prepare_http_permissions_and_no_execution]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 120)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- retain original synthetic failure
            record(check.__name__, False, traceback.format_exc())
