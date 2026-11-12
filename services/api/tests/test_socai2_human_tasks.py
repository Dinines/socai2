"""Restricted synthetic PostgreSQL + ASGI checks for versioned manual work."""
import asyncio
import traceback
from datetime import timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_tasks as api
from app.socai2 import baseline_context as c1
from app.socai2.baseline_contracts import Actor, Limits, Publication, Scope, Start
from app.socai2.baseline_model_view import candidates
from app.socai2.baseline_store import A, BaselineStore, C, R, StoreError
from app.socai2.case_contracts import CaseCreate, MemberChange
from app.socai2.human_task_contracts import TaskCreate, TaskEdit
from app.socai2.human_task_service import HumanTaskService, T, V
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import insert, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

TENANT, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic-human@example.invalid")


async def run_checks(engine, record, only=None):
    service = HumanTaskService(async_sessionmaker(engine, expire_on_commit=False))

    async def rows(table, *clauses):
        async with service.transaction(TENANT, readonly=True) as store:
            return [dict(r) for r in (await store.db.execute(select(table).where(*store.where(table, *clauses)))).mappings()]

    async def fixture():
        aids = [uuid4(), uuid4()]
        async with service.transaction(TENANT) as store:
            await store.db.execute(insert(A), [{"id": aid, "tenant_id": TENANT, "title": "synthetic human alert",
                "source_namespace": "human-fixture", "source_identity_key": str(aid)} for aid in aids])
        case = await service.create_case(TENANT, CaseCreate(operation_key=uuid4(), title="synthetic task Case", alert_ids=aids), actor=ACTOR)
        return case, aids

    def scope(aids):
        return Scope(kind="selected_alerts", alert_ids=aids, object_keys=[], window_start=None, window_end=None, limitations=[])

    def create_request(aids, **kw):
        return TaskCreate(operation_key=uuid4(), expected_scope_revision=1, title="confirm change authorization",
            **{"state": "completed", "result_text": "Synthetic operator confirms maintenance only for selected alerts.",
               "result_scope": scope(aids), **kw})

    def edit_request(task, **kw):
        fields = task.current.model_dump(exclude={"id", "case_id", "task_id", "revision", "completed_at", "completed_by", "changed_at", "changed_by"})
        fields["source_refs"] = [{"type": r.type, "id": r.id} for r in task.current.source_refs]
        return TaskEdit(**{**fields, "operation_key": uuid4(), "expected_scope_revision": 1,
            "expected_row_version": task.row_version, **kw})

    async def reject(code, call):
        try:
            await call
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("operation unexpectedly succeeded")

    async def write(cid, request, tid=None):
        return await service.write(TENANT, cid, request, actor=ACTOR, task_id=tid)

    async def capture(case, revision=1, claim=False):
        async with service.transaction(TENANT) as store:
            now = await store.now()
            request = Start(operation_key=uuid4(), expected_scope_revision=revision, window_start=now-timedelta(minutes=1), window_end=now)
            if claim:
                await store.claim(case.case_id, case.pending_run_id, request, actor=ACTOR, executor_version="synthetic.human.v1",
                    limits=Limits(max_model_calls=4, max_tool_calls=4, max_tokens=24000, max_rows_per_query=200,
                        deadline_at=now+timedelta(seconds=120), policy_version="synthetic.v1"))
                return await store.read_context(case.case_id, case.pending_run_id)
            return await c1.capture(store.db, TENANT, case.case_id, request)

    async def test_human_create_idempotent_without_machine_effects():
        case, aids = await fixture()
        before_run = await rows(R, R.c.case_id == case.case_id)
        request = create_request(aids, assignee_id=USER)
        first, replay = await asyncio.gather(write(case.case_id, request), write(case.case_id, request))
        assert first == replay and first.task.current.completed_by == USER
        assert first.task.current.completed_at == first.task.current.changed_at
        assert len(await rows(T, T.c.case_id == case.case_id)) == len(await rows(V, V.c.case_id == case.case_id)) == 1
        assert await rows(R, R.c.case_id == case.case_id) == before_run
        cas = (await rows(C, C.c.id == case.case_id))[0]
        assert cas["scope_revision"] == 1 and cas["handling_status"] == "new" and cas["current_assessment_id"] is None
        await reject("operation_key_conflict", write(case.case_id, request.model_copy(update={"title": "different"})))

    async def test_human_metadata_edits_and_feedback_reattest():
        case, aids = await fixture()
        first = (await write(case.case_id, create_request(aids))).task
        second = (await write(case.case_id, edit_request(first, title="clarified title"), first.id)).task
        assert second.current.revision == 2 and second.current.completed_at == first.current.completed_at
        assert second.current.changed_at > first.current.changed_at and second.current.completed_by == first.current.completed_by
        third = (await write(case.case_id, edit_request(second, result_text="Synthetic correction: only approved local activity."), first.id)).task
        assert third.current.completed_at > second.current.completed_at and third.current.changed_by == USER
        no_op = await write(case.case_id, edit_request(third), first.id)
        assert not no_op.changed and no_op.task == third
        old = await service.read_revision(TENANT, case.case_id, first.id, first.current_revision_id)
        assert old == first.current

    async def test_human_all_states_and_completion_validation():
        case, aids = await fixture()
        first = (await write(case.case_id, create_request(aids, state="not_started", result_text=None, result_scope=None))).task
        assert first.current.completed_at is None
        second = (await write(case.case_id, edit_request(first, state="cancelled"), first.id)).task
        third = (await write(case.case_id, edit_request(second, state="in_progress"), first.id)).task
        fourth = (await write(case.case_id, edit_request(third, state="completed", result_text="confirmed", result_scope=scope(aids)), first.id)).task
        reopened = (await write(case.case_id, edit_request(fourth, state="in_progress"), first.id)).task
        assert reopened.current.completed_at is reopened.current.completed_by is None
        assert fourth.current.completed_at is not None
        for kw in [{"result_text": " "}, {"result_scope": None}]:
            try:
                create_request(aids, **kw)
            except ValidationError:
                pass
            else:
                raise AssertionError("invalid completion accepted")

    async def test_human_frozen_context_and_moved_member_feedback():
        case, aids = await fixture()
        first = (await write(case.case_id, create_request(aids))).task
        frozen = await capture(case, claim=True)
        assert frozen.tasks[str(first.id)].usable_feedback
        await service.change_members(TENANT, case.case_id, MemberChange(operation_key=uuid4(), expected_scope_revision=1,
            alert_ids=aids[:1]), actor=ACTOR)
        edited = (await write(case.case_id, edit_request(first, title="metadata after member removal", expected_scope_revision=2), first.id)).task
        assert edited.current.result_scope == first.current.result_scope and edited.current.completed_at == first.current.completed_at
        current = await capture(case, revision=2)
        assert not current.tasks[str(first.id)].usable_feedback
        assert "feedback_scope_extends_beyond_case" in current.tasks[str(first.id)].limitations
        assert all(str(first.id) not in item["ref"]["source_path"] for item in candidates(current, uuid4(), []))
        async with service.transaction(TENANT, readonly=True) as store:
            assert await store.read_context(case.case_id, case.pending_run_id) == frozen
        await reject("task_scope_outside_current_case", write(case.case_id, edit_request(edited,
            expected_scope_revision=2, result_text="changed feedback"), first.id))

    async def test_human_scope_reference_assignee_and_origin_guards():
        case, aids = await fixture()
        other, other_aids = await fixture()
        for request, code in [
            (create_request([other_aids[0]]), "task_scope_outside_current_case"),
            (create_request(aids, assignee_id=uuid4()), "task_assignee_not_in_tenant"),
            (create_request(aids, origin_result_id=uuid4()), "task_origin_result_not_found"),
            (create_request(aids, source_refs=[{"type":"artifact", "id":uuid4()}]), "task_source_reference_not_found"),
            (create_request(aids, result_scope=scope(aids).model_copy(update={"object_keys":["unknown-object"]})), "task_objects_outside_current_scope"),
            (create_request(aids[:1], result_scope=scope(aids[:1]).model_copy(update={"kind":"whole_case"})), "task_whole_case_scope_incomplete")]:
            await reject(code, write(case.case_id, request))
        assert not await rows(T, T.c.case_id == case.case_id)
        foreign_task = (await write(other.case_id, create_request(other_aids))).task
        await reject("task_source_reference_outside_case", write(case.case_id, create_request(aids,
            source_refs=[{"type":"task_revision","id":foreign_task.current_revision_id}])))
        await reject("case_not_found", service.read(OTHER, case.case_id, foreign_task.id))

    async def test_human_concurrent_edit_replay_and_scope_conflict():
        case, aids = await fixture()
        first = (await write(case.case_id, create_request(aids))).task
        req = edit_request(first, title="first writer")
        results = await asyncio.gather(write(case.case_id, req, first.id), write(case.case_id,
            edit_request(first, title="competing writer"), first.id), return_exceptions=True)
        errors = [r for r in results if isinstance(r, StoreError)]
        assert len(errors) == 1 and errors[0].code == "task_row_version_conflict"
        winner = next(r for r in results if not isinstance(r, Exception))
        assert winner.task.row_version == 2 and len(await rows(V, V.c.task_id == first.id)) == 2
        await reject("case_scope_revision_conflict", write(case.case_id, edit_request(winner.task, expected_scope_revision=2), first.id))

    async def test_human_commit_failure_rolls_back_revision_and_pointer():
        case, aids = await fixture()
        first = (await write(case.case_id, create_request(aids))).task
        previous = BaselineStore.event
        async def fail_commit(store, *args, **kw):
            await previous(store, *args, **kw)
            await store.db.execute(update(T).where(T.c.id == first.id).values(current_revision_id=uuid4()))
        with patch.object(BaselineStore, "event", fail_commit):
            try:
                await write(case.case_id, edit_request(first, title="must rollback"), first.id)
            except DBAPIError:
                pass
            else:
                raise AssertionError("deferred FK commit unexpectedly succeeded")
        assert await service.read(TENANT, case.case_id, first.id) == first
        assert len(await rows(V, V.c.task_id == first.id)) == 1

    async def test_human_revision_database_immutability_and_pagination():
        case, aids = await fixture()
        task = (await write(case.case_id, create_request(aids))).task
        original = task
        for i in range(3):
            task = (await write(case.case_id, edit_request(task, title=f"revision {i}"), task.id)).task
        try:
            async with service.transaction(TENANT) as store:
                await store.db.execute(update(V).where(V.c.id == original.current_revision_id).values(result_text="rewrite"))
        except DBAPIError:
            pass
        else:
            raise AssertionError("old task revision mutated")
        first = await service.revisions(TENANT, case.case_id, task.id, limit=2)
        second = await service.revisions(TENANT, case.case_id, task.id, limit=2, offset=2)
        assert first.total == second.total == 4 and first.next_offset == 2 and second.next_offset is None
        assert [r.revision for r in first.items+second.items] == [4,3,2,1]
        assert (await service.list(TENANT, case.case_id))["total"] == 1

    async def test_human_origin_and_internal_reference():
        case, aids = await fixture()
        await capture(case, claim=True)
        scoped = scope(aids)
        publication = Publication(operation_key=uuid4(), terminal_state="completed", stop_reason="synthetic",
            title="synthetic source result", conclusion=None, conclusion_state="unavailable", conclusion_origin="system",
            validation_state="system_only", closing_note="synthetic handoff", findings=[], questions=[], recommendations=[],
            change_kind="initial", change_summary=None, case_impact={"summary":None,"supported_changes":[],
                "cannot_generalize":[],"affected_scope":scoped,"next_steps":[]}, delivery_state="partial",
            members=[{"alert_id":aid,"read_state":"missing","assessment_state":"unresolved","conclusion_covered":False,
                "assessment":None,"limitations":"synthetic","evidence_refs":[]} for aid in aids])
        out = await service.publish(TENANT, case.case_id, case.pending_run_id, publication)
        rid = UUID(str(out["result_id"]))
        task = (await write(case.case_id, create_request(aids, origin_result_id=rid,
            source_refs=[{"type":"result","id":rid}]))).task
        assert task.origin_result_id == rid and task.current.source_refs[0].role == "prior_analysis"
        await reject("task_origin_finding_not_found", write(case.case_id, create_request(aids,
            origin_result_id=rid, origin_finding_id="not-in-result")))

    async def test_human_http_permissions_and_read_only():
        case, aids = await fixture()
        principal = CurrentUser(USER, TENANT, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
        app = FastAPI()
        app.include_router(api.router, prefix="/api/v1")
        async def user():
            return principal
        app.dependency_overrides[get_current_user] = user
        app.dependency_overrides[api.get_service] = lambda: service
        path = f"/api/v1/socai2/cases/{case.case_id}/tasks"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            body = create_request(aids).model_dump(mode="json")
            assert (await client.post(path, json={**body,"completed_by":str(USER)})).status_code == 422
            principal = CurrentUser(USER, TENANT, "viewer", ACTOR.name, scopes=["cases:read"])
            assert (await client.post(path, json=body)).status_code == 403
            principal = CurrentUser(USER, TENANT, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
            response = await client.post(path, json=body)
            assert response.status_code == 200, response.text
            task = response.json()["task"]
            before = await rows(C, C.c.id == case.case_id)
            for url in [path, path+"/"+task["id"], path+"/"+task["id"]+"/revisions",
                path+"/"+task["id"]+"/revisions/"+task["current_revision_id"]]:
                assert (await client.get(url)).status_code == 200
            assert await rows(C, C.c.id == case.case_id) == before
            principal = CurrentUser(USER, OTHER, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
            assert (await client.get(path)).status_code == 404
            principal = CurrentUser(USER, TENANT, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
            app.dependency_overrides.pop(api.get_service)
            with patch.object(api.settings, "SOCAI2_CASE_API_ENABLED", False), \
                 patch.object(api.settings, "SOCAI2_PAGE_READ_ENABLED", False):
                assert (await client.get(path)).status_code == 503

    checks = [test_human_create_idempotent_without_machine_effects, test_human_metadata_edits_and_feedback_reattest,
        test_human_all_states_and_completion_validation, test_human_frozen_context_and_moved_member_feedback,
        test_human_scope_reference_assignee_and_origin_guards, test_human_concurrent_edit_replay_and_scope_conflict,
        test_human_commit_failure_rolls_back_revision_and_pointer, test_human_revision_database_immutability_and_pagination,
        test_human_origin_and_internal_reference, test_human_http_permissions_and_read_only]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 120)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- preserve original synthetic failures
            record(check.__name__, False, traceback.format_exc())
