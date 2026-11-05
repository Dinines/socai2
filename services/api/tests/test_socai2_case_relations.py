"""Real restricted PG transactions and ASGI; synthetic data, no executors."""
import asyncio
import traceback
from datetime import timedelta
from unittest.mock import patch
from uuid import UUID, uuid4, uuid5

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import socai2_cases as api
from app.models import socai2 as m
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_store import CA, RM, A, BaselineStore, C, F, R, StoreError
from app.socai2.case_contracts import (
    AssociationRequest,
    CaseCreate,
    MemberChange,
    MoveMembers,
)
from app.socai2.case_service import CaseService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic-relations@example.invalid")
I, IA, CI = m.Incidents.__table__, m.IncidentAlerts.__table__, m.CaseIncidents.__table__


async def run_checks(engine, record, only=None):
    service = CaseService(async_sessionmaker(engine, expire_on_commit=False))

    async def rows(table, *clauses, tenant=T):
        async with service.transaction(tenant, readonly=True) as store:
            return [dict(r) for r in (await store.db.execute(select(table).where(*store.where(table, *clauses)))).mappings()]

    async def alert(namespace="relations-fixture", tenant=T):
        aid = uuid4()
        async with service.transaction(tenant) as store:
            await store.db.execute(insert(A).values(id=aid, tenant_id=tenant, title="synthetic relation alert",
                source_namespace=namespace, source_identity_key=str(aid)))
        return aid

    async def incident(aids, namespace="relations-fixture", tenant=T):
        iid = uuid4()
        async with service.transaction(tenant) as store:
            await store.db.execute(insert(I).values(id=iid, tenant_id=tenant, title="synthetic incident",
                source_namespace=namespace, source_incident_id=str(iid)))
            for aid in aids:
                await store.db.execute(insert(IA).values(id=uuid4(), tenant_id=tenant, incident_id=iid,
                    alert_id=aid, membership_source="fusion", correlation_basis={},
                    basis_version="synthetic.v1", source_operation_id=uuid4()))
        return iid

    async def create(aids=None, incident_ids=None):
        if aids is None and incident_ids is None:
            aids = [await alert()]
        return await service.create_case(T, CaseCreate(operation_key=uuid4(), title="synthetic relations Case",
            alert_ids=aids or [], incident_ids=incident_ids or []), actor=ACTOR)

    def association(revision=1, aids=(), incidents=()):
        return AssociationRequest(operation_key=uuid4(), expected_scope_revision=revision,
            alert_ids=list(aids), incident_ids=list(incidents))

    def moving(source, target, aids):
        return MoveMembers(operation_key=uuid4(), target_case_id=target.case_id,
            expected_source_scope_revision=source.scope_revision,
            expected_target_scope_revision=target.scope_revision, alert_ids=aids)

    async def fail(code, call):
        try:
            await call
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("operation unexpectedly succeeded")

    async def claim(created):
        async with service.transaction(T) as store:
            now = await store.now()
            return await store.claim(created.case_id, created.pending_run_id,
                Start(operation_key=uuid4(), expected_scope_revision=created.scope_revision,
                    window_start=now-timedelta(minutes=1), window_end=now), actor=ACTOR,
                executor_version="synthetic-relations.v1", limits=Limits(max_model_calls=4,
                    max_tool_calls=4, max_tokens=24000, max_rows_per_query=200,
                    deadline_at=now+timedelta(seconds=120), policy_version="synthetic.v1"))

    async def context(created):
        async with service.transaction(T, readonly=True) as store:
            return await store.read_context(created.case_id, created.pending_run_id)

    async def test_create_incident_union_and_link_only():
        a, b = await alert(), await alert()
        i = await incident([a, b])
        request = CaseCreate(operation_key=uuid4(), title="incident union", alert_ids=[a], incident_ids=[i])
        first, replay = await asyncio.gather(service.create_case(T, request, actor=ACTOR), service.create_case(T, request, actor=ACTOR))
        assert first == replay and set(first.added_alert_ids) == {a, b} and first.linked_incident_ids == [i]
        detail = await service.read_case(T, first.case_id)
        assert detail["case"].source_namespace == "relations-fixture"
        assert detail["linked_incident_count"] == 1 and detail["member_count"] == 2
        assert {row["alert_id"]: row["membership_source"] for row in detail["members"]} == {a: "manual", b: "incident_link"}
        another = await create([a, b])
        await claim(another)
        old_run = await rows(R, R.c.id == another.pending_run_id)
        linked = await service.associate(T, another.case_id, association(incidents=[i]), actor=ACTOR)
        assert not linked.changed and linked.pending_run_id is None and linked.linked_incident_ids == [i]
        assert await rows(R, R.c.id == another.pending_run_id) == old_run
        content = await context(another)
        assert not content.incidents[str(i)].linked_from_case

    async def test_association_replay_uses_original_incident_snapshot():
        a, b = await alert(), await alert()
        i, case = await incident([a]), await create([a])
        req = association(incidents=[i])
        first = await service.associate(T, case.case_id, req, actor=ACTOR)
        async with service.transaction(T) as store:
            await store.db.execute(insert(IA).values(id=uuid4(), tenant_id=T, incident_id=i, alert_id=b,
                membership_source="fusion", correlation_basis={}, basis_version="synthetic.v1", source_operation_id=uuid4()))
        assert await service.associate(T, case.case_id, req, actor=ACTOR) == first
        assert len(await rows(CA, CA.c.case_id == case.case_id)) == 1
        later = await service.associate(T, case.case_id, association(incidents=[i]), actor=ACTOR)
        assert later.added_alert_ids == [b] and later.linked_incident_ids == []
        assert later.pending_run_id == case.pending_run_id and later.scope_revision == 2
        duplicate = await service.associate(T, case.case_id, association(2, incidents=[i]), actor=ACTOR)
        assert not duplicate.changed and duplicate.scope_revision == 2

    async def test_invalid_selection_rolls_back_creation_and_association():
        a, bad = await alert(), await alert("other-scope")
        i, empty = await incident([a]), await incident([])
        foreign = await incident([], tenant=OTHER)
        for ids, code in [([i, uuid4()], "case_incident_not_found"), ([i, foreign], "case_incident_not_found"),
                          ([i, empty], "case_incident_members_unavailable")]:
            req = CaseCreate(operation_key=uuid4(), title="must rollback", incident_ids=ids)
            await fail(code, service.create_case(T, req, actor=ACTOR))
            cid = uuid5(T, "socai2.case.create:"+str(req.operation_key))
            assert not await rows(C, C.c.id == cid)
        case = await create([a])
        before = await service.read_case(T, case.case_id)
        await fail("case_source_namespace_mismatch", service.associate(T, case.case_id,
            association(aids=[bad], incidents=[i]), actor=ACTOR))
        assert await service.read_case(T, case.case_id) == before
        foreign_alert = await alert(tenant=OTHER)
        await fail("member_alert_not_found", service.associate(T, case.case_id,
            association(aids=[foreign_alert]), actor=ACTOR))

    async def test_move_preserves_active_scope_and_coalesces_next():
        a, b, c = await alert(), await alert(), await alert()
        i = await incident([a, b])
        source, target = await create(incident_ids=[i]), await create([c])
        frozen = await claim(source)
        original = await rows(F, F.c.id == frozen.input_artifact_id)
        original_context = await context(source)
        original_members = await rows(RM, RM.c.run_id == source.pending_run_id)
        req = moving(source, target, [a])
        out = await service.move_members(T, source.case_id, req, actor=ACTOR)
        assert out.source.pending_run_id != source.pending_run_id and out.target.pending_run_id == target.pending_run_id
        assert out.source.scope_revision == out.target.scope_revision == 2
        assert await service.move_members(T, source.case_id, req, actor=ACTOR) == out
        next_req = MoveMembers(operation_key=uuid4(), target_case_id=target.case_id,
            expected_source_scope_revision=2, expected_target_scope_revision=2, alert_ids=[b])
        second = await service.move_members(T, source.case_id, next_req, actor=ACTOR)
        assert second.source.pending_run_id == out.source.pending_run_id
        assert not await rows(CA, CA.c.case_id == source.case_id)
        assert await rows(F, F.c.id == frozen.input_artifact_id) == original
        assert await context(source) == original_context
        assert await rows(RM, RM.c.run_id == source.pending_run_id) == original_members
        assert len(await rows(CI, CI.c.case_id == source.case_id)) == 1 and not await rows(CI, CI.c.case_id == target.case_id)
        assert (await rows(R, R.c.id == source.pending_run_id))[0]["state"] == "running"
        assert (await rows(R, R.c.id == target.pending_run_id))[0]["state"] == "pending_update"
        assert all(r["membership_source"] == "move" for r in await rows(CA, CA.c.case_id == target.case_id, CA.c.alert_id.in_([a,b])))

    async def test_duplicate_target_and_empty_source_binding():
        a, bad = await alert(), await alert("different")
        source, target = await create([a]), await create([a])
        out = await service.move_members(T, source.case_id, moving(source, target, [a]), actor=ACTOR)
        assert not out.target.changed and out.target.scope_revision == 1 and out.added_to_target_alert_ids == []
        detail = await service.read_case(T, source.case_id)
        assert detail["baseline_records"][0]["start_eligibility"].reason == "empty_scope"
        assert detail["case"].source_namespace == "relations-fixture"
        await fail("case_source_namespace_mismatch", service.change_members(T, source.case_id,
            MemberChange(operation_key=uuid4(), expected_scope_revision=2, alert_ids=[bad]), actor=ACTOR))
        restored = await service.associate(T, source.case_id, association(2, aids=[a]), actor=ACTOR)
        assert restored.scope_revision == 3 and restored.pending_run_id == source.pending_run_id

    async def test_move_atomic_rollback_after_source_write():
        a = await alert()
        source, target = await create([a]), await create()
        before = [await service.read_case(T, cid) for cid in [source.case_id, target.case_id]]
        original = BaselineStore.replace_members
        async def injected(store, cid, *args, **kwargs):
            if cid == target.case_id:
                raise StoreError("synthetic_target_failure")
            return await original(store, cid, *args, **kwargs)
        with patch.object(BaselineStore, "replace_members", injected):
            await fail("synthetic_target_failure", service.move_members(T, source.case_id, moving(source, target, [a]), actor=ACTOR))
        assert [await service.read_case(T, cid) for cid in [source.case_id, target.case_id]] == before

    async def test_reverse_concurrent_moves_no_deadlock_or_lost_update():
        a, b = await alert(), await alert()
        left, right = await create([a]), await create([b])
        results = await asyncio.gather(service.move_members(T, left.case_id, moving(left, right, [a]), actor=ACTOR),
            service.move_members(T, right.case_id, moving(right, left, [b]), actor=ACTOR), return_exceptions=True)
        failures = [r for r in results if isinstance(r, StoreError)]
        assert len(failures) == 1 and failures[0].code == "case_scope_revision_conflict", results
        members = await rows(CA, CA.c.case_id.in_([left.case_id,right.case_id]))
        assert len(members) == 2 and {r["alert_id"] for r in members} == {a,b}
        assert len({r["case_id"] for r in members}) == 1

    async def test_move_competes_with_start_and_preserves_frozen_input():
        a = await alert()
        source, target = await create([a]), await create()
        results = await asyncio.gather(claim(source), service.move_members(T, source.case_id,
            moving(source, target, [a]), actor=ACTOR), return_exceptions=True)
        assert not isinstance(results[1], Exception), results
        if isinstance(results[0], StoreError):
            assert results[0].code == "baseline_scope_revision_conflict"
            assert len(await rows(R, R.c.case_id == source.case_id)) == 1
        else:
            assert results[0].state == "running"
            assert set((await context(source)).alerts) == {str(a)}
            assert len(await rows(R, R.c.case_id == source.case_id)) == 2

    async def test_source_binding_database_guard_and_legacy_unknown():
        case = await create()
        try:
            async with service.transaction(T) as store:
                await store.db.execute(update(C).where(C.c.id == case.case_id).values(source_namespace="other"))
        except DBAPIError:
            pass
        else:
            raise AssertionError("namespace binding was overwritten")
        cid, aid = uuid4(), await alert()
        async with service.transaction(T) as store:
            await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="unverified legacy", scope_revision=1))
        await fail("case_source_scope_unverified", service.associate(T, cid, association(aids=[aid]), actor=ACTOR))
        async with service.transaction(T, readonly=True) as store:
            count = (await store.db.execute(text("SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2'"))).scalar_one()
            assert count == 459

    async def test_http_relations_boundaries():
        principal = CurrentUser(USER, T, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
        app = FastAPI()
        app.include_router(api.router, prefix="/api/v1")
        async def user():
            return principal
        app.dependency_overrides[get_current_user] = user
        app.dependency_overrides[api.get_service] = lambda: service
        a, b = await alert(), await alert()
        source, target = await create([a]), await create([b])
        req = moving(source, target, [a])
        path = f"/api/v1/socai2/cases/{source.case_id}/members/move"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            bad = await client.post(path, json={**req.model_dump(mode="json"), "tenant_id": str(OTHER)})
            assert bad.status_code == 422
            principal = CurrentUser(USER, T, "viewer", ACTOR.name, scopes=["cases:read"])
            assert (await client.post(path, json=req.model_dump(mode="json"))).status_code == 403
            principal = CurrentUser(USER, T, "admin", ACTOR.name, scopes=["cases:read", "cases:write"])
            result = await client.post(path, json=req.model_dump(mode="json"))
            assert result.status_code == 200, result.text
            assert result.json()["source"]["scope_revision"] == 2
            associated = await client.post(f"/api/v1/socai2/cases/{source.case_id}/associations",
                json=association(2, aids=[a]).model_dump(mode="json"))
            assert associated.status_code == 200 and associated.json()["added_alert_ids"] == [str(a)]

    async def test_move_capacity_and_resolved_target_rollback():
        a = await alert()
        source, target = await create([a]), await create()
        # Seed the remaining current members in one SQL batch. The attempted
        # move must fail before it can refresh any target pending snapshot.
        extra = [uuid4() for _ in range(199)]
        async with service.transaction(T) as store:
            await store.db.execute(insert(A), [{"id": aid, "tenant_id": T, "title": "capacity fixture",
                "source_namespace": "relations-fixture", "source_identity_key": str(aid)} for aid in extra])
            await store.db.execute(insert(CA), [{"id": uuid4(), "tenant_id": T, "case_id": target.case_id,
                "alert_id": aid, "membership_source": "manual", "source_operation_id": uuid4()} for aid in extra])
        before = [await service.read_case(T, cid) for cid in [source.case_id, target.case_id]]
        await fail("case_member_limit_exceeded", service.move_members(T, source.case_id, moving(source, target, [a]), actor=ACTOR))
        assert [await service.read_case(T, cid) for cid in [source.case_id, target.case_id]] == before
        async with service.transaction(T) as store:
            await store.db.execute(update(C).where(C.c.id == target.case_id).values(handling_status="resolved",
                resolved_at=await store.now(), resolved_by=USER, resolution_note="synthetic closed"))
        await fail("resolved_case_scope_policy_not_enabled", service.move_members(T, source.case_id,
            moving(source, target, [a]), actor=ACTOR))
        assert await service.read_case(T, source.case_id) == before[0]

    async def test_uncommitted_move_is_not_visible_to_readers():
        a = await alert()
        source, target = await create([a]), await create()
        before = [await service.read_case(T, cid) for cid in [source.case_id, target.case_id]]
        reached, release = asyncio.Event(), asyncio.Event()
        original = BaselineStore.replace_members
        async def held(store, cid, *args, **kwargs):
            if cid == target.case_id:
                reached.set()
                await release.wait()
            return await original(store, cid, *args, **kwargs)
        with patch.object(BaselineStore, "replace_members", held):
            task = asyncio.create_task(service.move_members(T, source.case_id, moving(source, target, [a]), actor=ACTOR))
            try:
                await asyncio.wait_for(reached.wait(), 15)
                assert [await service.read_case(T, cid) for cid in [source.case_id, target.case_id]] == before
            finally:
                release.set()
                await task
        assert not await rows(CA, CA.c.case_id == source.case_id)
        assert len(await rows(CA, CA.c.case_id == target.case_id)) == 2

    checks = [test_create_incident_union_and_link_only, test_association_replay_uses_original_incident_snapshot,
        test_invalid_selection_rolls_back_creation_and_association, test_move_preserves_active_scope_and_coalesces_next,
        test_duplicate_target_and_empty_source_binding, test_move_atomic_rollback_after_source_write,
        test_reverse_concurrent_moves_no_deadlock_or_lost_update, test_move_competes_with_start_and_preserves_frozen_input,
        test_source_binding_database_guard_and_legacy_unknown, test_http_relations_boundaries,
        test_move_capacity_and_resolved_target_rollback, test_uncommitted_move_is_not_visible_to_readers]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 120)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- retain synthetic failures verbatim
            record(check.__name__, False, traceback.format_exc())
