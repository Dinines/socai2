"""Case lifecycle guards and concurrent edits on an explicit isolated PG."""
import asyncio
import traceback
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.socai2.baseline_contracts import Actor
from app.socai2.baseline_store import C, R, StoreError
from app.socai2.case_management import manage_case, read_management
from app.socai2.case_management_contracts import CaseCloseRequest, CaseLifecycleRequest, CaseManagementUpdate
from app.socai2.case_service import CaseService
from app.socai2.case_contracts import CaseCreate

TENANT, USER = UUID(int=1), UUID(int=3)
ACTOR = Actor(user_id=USER, name='synthetic-case-management@example.invalid')


async def run_checks(engine, record, *, source_alert_id, only=None):
    service = CaseService(async_sessionmaker(engine, expire_on_commit=False))

    async def fixture(state=None):
        cid, rid, aid = uuid4(), uuid4(), uuid4()
        if state:
            created = await service.create_case(TENANT, CaseCreate(operation_key=uuid4(),
                title='synthetic management execution guard', alert_ids=[source_alert_id]), actor=ACTOR)
            cid, rid = created.case_id, created.pending_run_id
        async with service.transaction(TENANT) as store:
            if not state:
                await store.db.execute(insert(C).values(id=cid, tenant_id=TENANT,
                    title='synthetic management guard', created_by=USER))
            if state:
                await store.case(cid)
                now = await store.now()
                await store.save_input_artifact(cid, rid, aid, {'synthetic': True, 'executed': False},
                    kind='input_snapshot', schema='synthetic.management-test.v1', captured_at=now,
                    refs=[], actor_id=USER)
                await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
                    state='running', started_at=now, executor_version='synthetic-management-test',
                    input_artifact_id=aid, operation_key=str(uuid4()), request_hash='0'*64))
                if state == 'unknown':
                    await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(state=state))
        return cid

    async def expect(code, call):
        try:
            await call
        except StoreError as error:
            assert error.code == code, error.code
        else:
            raise AssertionError('expected '+code)

    async def active_and_unknown_block_closure():
        for state in ['running', 'unknown']:
            cid = await fixture(state)
            before = await read_management(service, TENANT, cid)
            assert not before.can_close and before.blocking_runs[0].state == state
            await expect('case_active_run_prevents_close', manage_case(service, TENANT, cid,
                CaseCloseRequest(operation_key=uuid4(), expected_row_version=before.case.row_version), ACTOR, action='case_closed'))
            assert await read_management(service, TENANT, cid) == before

    async def concurrent_edits_conflict_and_no_task_closure():
        cid = await fixture()
        changes = [CaseManagementUpdate(operation_key=uuid4(), expected_row_version=1, title=title)
                   for title in ['edit one', 'edit two']]
        results = await asyncio.gather(*(manage_case(service, TENANT, cid, change, ACTOR,
            action='case_management_updated') for change in changes), return_exceptions=True)
        assert sum(isinstance(r, StoreError) and r.code == 'case_row_version_conflict' for r in results) == 1
        current = await read_management(service, TENANT, cid)
        assert current.case.row_version == 2
        await expect('case_owner_not_in_tenant', manage_case(service, TENANT, cid,
            CaseManagementUpdate(operation_key=uuid4(), expected_row_version=2, owner_id=uuid4()),
            ACTOR, action='case_management_updated'))
        await expect('case_not_found', read_management(service, UUID(int=2), cid))
        unchanged = await manage_case(service, TENANT, cid,
            CaseManagementUpdate(operation_key=uuid4(), expected_row_version=2, title=current.case.title),
            ACTOR, action='case_management_updated')
        assert not unchanged.changed and unchanged.case.row_version == 2
        # No pending tasks: a reason is optional, as the confirmed rules require.
        request = CaseCloseRequest(operation_key=uuid4(), expected_row_version=2)
        closed = await manage_case(service, TENANT, cid, request, ACTOR, action='case_closed')
        await expect('operation_key_conflict', manage_case(service, TENANT, cid,
            request.model_copy(update={'reason': 'different intent'}), ACTOR, action='case_closed'))
        reopened = await manage_case(service, TENANT, cid,
            CaseLifecycleRequest(operation_key=uuid4(), expected_row_version=closed.case.row_version),
            ACTOR, action='case_reopened')
        assert reopened.case.handling_status == 'in_progress' and reopened.case.resolved_at is None
        async with service.transaction(TENANT, readonly=True) as store:
            assert not (await store.db.execute(select(R.c.id).where(*store.where(R, R.c.case_id == cid)))).all()

    for check in [active_and_unknown_block_closure, concurrent_edits_conflict_and_no_task_closure]:
        if only and check.__name__ not in only:
            continue
        try:
            await check()
            record(check.__name__, True)
        except Exception:
            record(check.__name__, False, traceback.format_exc())
