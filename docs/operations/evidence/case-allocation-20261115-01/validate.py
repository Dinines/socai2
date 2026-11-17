"""Step 5 direct real-PG allocation/admission checks; no model or executor."""
import argparse
import asyncio
import json
import os
import sys
import traceback
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'services/api'))


def save(path, body):
    path.write_text(json.dumps(body, default=str, ensure_ascii=False, indent=2) + '\n')


async def main(args):
    from app.models import socai2 as m
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_store import StoreError
    from app.socai2.case_allocation_contracts import FollowIncident
    from app.socai2.case_contracts import AssociationRequest, CaseCreate, MemberChange, MoveMembers
    from app.socai2.case_service import CaseService
    from app.socai2.page_reader import PageReadService
    from sqlalchemy import insert, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out = Path(__file__).resolve().parent / args.batch
    out.mkdir(exist_ok=False)
    cfg = json.loads(Path(args.profile).read_text())
    assert cfg['processing_database'] == 'v12_upgrade_dev'
    os.environ['SOCAI2_ANALYSIS_TASKS_CONFIG_FILE'] = str(ROOT / 'deploy/local-investigation/analysis-tasks.json')
    os.environ['SOCAI2_CASE_ALLOCATION_CONFIG_FILE'] = str(ROOT / 'deploy/local-investigation/case-allocation.json')
    url = URL.create('postgresql+psycopg', username=cfg['admin'], password=Path(cfg['password_file']).read_text().strip(),
        host=cfg['host'], port=cfg['port'], database=cfg['processing_database'])
    admin = create_async_engine(url, hide_parameters=True, connect_args={'sslmode': 'disable'})
    engine = create_async_engine(url, hide_parameters=True, connect_args={'sslmode': 'disable', 'options': '-c role='+cfg['processor']})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, pages = CaseService(sessions), PageReadService(sessions)
    tasks = AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    tenant, actor_id, event = uuid4(), uuid4(), uuid4()
    actor = Actor(user_id=actor_id, name='Step 5 allocation fixture')
    alerts = [uuid4() for _ in range(450)]
    result = {'state': 'running', 'tenant_id': tenant, 'actor_id': actor_id, 'incident_id': event,
        'checks': [], 'model_calls': 0, 'case_execution_calls': 0, 'database': cfg['processing_database']}
    receipts = {}

    async def counts(cid):
        return (await cases.read_case(tenant, cid))['member_count']

    async def revision(cid):
        return (await cases.read_case(tenant, cid))['case'].scope_revision

    async def add(cid, ids=(), incidents=()):
        req = AssociationRequest(operation_key=uuid4(), expected_scope_revision=await revision(cid),
            alert_ids=list(ids), incident_ids=list(incidents))
        return req, await cases.associate(tenant, cid, req, actor=actor)

    async def expect_error(code, call):
        try:
            await call
        except StoreError as exc:
            assert exc.code == code, (code, exc.code)
        else:
            raise AssertionError('expected '+code)

    async def snapshot():
        async with cases.transaction(tenant, readonly=True) as store:
            return {table: (await store.db.execute(text('SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),\'[]\') FROM socai2.'+table+' t WHERE tenant_id=:tenant'),
                {'tenant':tenant})).scalar_one() for table in ('cases','case_alerts','case_incidents','case_alert_exclusions',
                    'incidents','analysis_tasks','analysis_subject_state','analysis_attempts','runs','activities','activity_targets')}

    try:
        async with admin.begin() as db:
            await db.execute(text("""INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
            VALUES(:id,'Step 5 allocation',:slug,'enterprise',true,'{}','{}',now(),now())"""), {'id':tenant,'slug':'case-alloc-'+str(tenant)})
            await db.execute(text("""INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
            VALUES(:id,:tenant,:email,:name,'!','soc_analyst',true,false,'{}',now(),now())"""),
                {'id':actor_id,'tenant':tenant,'email':str(actor_id)+'@example.invalid','name':'case-alloc-'+str(actor_id)})
        async with cases.transaction(tenant) as store:
            await store.db.execute(insert(m.Alerts), [{'id':aid,'tenant_id':tenant,'source_namespace':'case-allocation-fixture',
                'source_identity_key':str(aid),'title':'Synthetic allocation '+str(n)} for n,aid in enumerate(alerts)])
            await store.db.execute(insert(m.Incidents).values(id=event,tenant_id=tenant,source_namespace='case-allocation-fixture',
                source_incident_id=str(event),title='260-member synthetic event'))
            await store.db.execute(insert(m.IncidentAlerts), [{'id':uuid4(),'tenant_id':tenant,'incident_id':event,'alert_id':aid,'membership_source':'fusion','correlation_basis':{},'basis_version':'step5.fixture','source_operation_id':uuid4()}
                for aid in alerts[:260]])
        req99 = CaseCreate(operation_key=uuid4(), title='99 + 5', alert_ids=alerts[:99])
        first = await cases.create_case(tenant, req99, actor=actor)
        cid = first.primary_case_id
        req5, overflow = await add(cid, alerts[99:104])
        assert [await counts(x.case_id) for x in overflow.allocations] == [100, 4]
        assert sum(x.initial_task is not None for x in overflow.allocations) == 1
        receipts.update(first=first.model_dump(mode='json'), overflow=overflow.model_dump(mode='json'))
        result['checks'].append('99_plus_5_to_100_4_new_case_task_only')

        req_event = CaseCreate(operation_key=uuid4(), title='Event first chain', incident_ids=[event])
        chain = await cases.create_case(tenant, req_event, actor=actor)
        assert [await counts(x.case_id) for x in chain.allocations] == [100,100,60]
        assert len({x.initial_task.task_id for x in chain.allocations}) == 3
        independent = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(),title='Independent event chain',incident_ids=[event]), actor=actor)
        old_receiver = chain.receiving_case_id
        _, extended = await add(chain.primary_case_id, alerts[300:345])
        view = await pages.read(tenant,'incidents',event,'view')
        assert view.case_receiving.active_case_id == independent.receiving_case_id
        replay = await cases.create_case(tenant, req_event, actor=actor)
        assert replay == chain
        assert await cases.associate(tenant,cid,req5,actor=actor) == overflow
        assert (await pages.read(tenant,'incidents',event,'view')).case_receiving.active_case_id == independent.receiving_case_id
        receipts.update(event_chain=chain.model_dump(mode='json'), independent=independent.model_dump(mode='json'), extended=extended.model_dump(mode='json'))
        result['checks'].append('event_260_three_tasks_independent_receiver_replay_no_steal')

        root, receiver = independent.primary_case_id, independent.receiving_case_id
        detail = await cases.read_case(tenant,root)
        kept = [r['alert_id'] for r in detail['members']][1:]
        excluded = detail['members'][0]['alert_id']
        replaced = await cases.change_members(tenant,root,MemberChange(operation_key=uuid4(),expected_scope_revision=detail['case'].scope_revision,alert_ids=kept),actor=actor)
        follow = await cases.follow_incident(tenant,receiver,FollowIncident(operation_key=uuid4(),incident_id=event),actor=actor)
        assert follow.excluded_alert_ids == [excluded]
        assert excluded not in {a for x in follow.allocations for a in x.added_alert_ids+x.existing_alert_ids}
        async with cases.transaction(tenant) as store:
            await store.db.execute(insert(m.IncidentAlerts), [{'id':uuid4(),'tenant_id':tenant,'incident_id':event,'alert_id':aid,'membership_source':'fusion','correlation_basis':{},'basis_version':'step5.fixture','source_operation_id':uuid4()} for aid in alerts[260:263]])
        follow_new = await cases.follow_incident(tenant,receiver,FollowIncident(operation_key=uuid4(),incident_id=event),actor=actor)
        assert {a for x in follow_new.allocations for a in x.added_alert_ids} == set(alerts[260:263])
        _, restored = await add(root,[excluded])
        assert next(x for x in restored.allocations if x.case_id == receiver).added_alert_ids == [excluded]
        assert await counts(root) == 99
        replace_more = await cases.change_members(tenant,root,MemberChange(operation_key=uuid4(),expected_scope_revision=await revision(root),alert_ids=kept[:-1]+[alerts[400]]),actor=actor)
        assert await counts(root) == 98
        assert next(x for x in replace_more.allocation.allocations if x.case_id == receiver).added_alert_ids == [alerts[400]]
        receipts.update(replaced=replaced.model_dump(mode='json'), excluded_follow=follow.model_dump(mode='json'), follow_new=follow_new.model_dump(mode='json'), restored=restored.model_dump(mode='json'), replacement=replace_more.model_dump(mode='json'))
        result['checks'].append('exclusion_respected_follow_new_only_explicit_restore_replace_keeps_old_members')

        source = await cases.create_case(tenant,CaseCreate(operation_key=uuid4(),title='Move source',alert_ids=alerts[430:432]),actor=actor)
        move = await cases.move_members(tenant,source.primary_case_id,MoveMembers(operation_key=uuid4(),target_case_id=root,
            expected_source_scope_revision=await revision(source.primary_case_id),expected_target_scope_revision=await revision(root),alert_ids=[alerts[430]]),actor=actor)
        assert await counts(source.primary_case_id) == 1
        assert next(x for x in move.allocation.allocations if x.case_id == receiver).added_alert_ids == [alerts[430]]
        cleared = await cases.change_members(tenant,source.primary_case_id,MemberChange(operation_key=uuid4(),expected_scope_revision=await revision(source.primary_case_id),alert_ids=[]),actor=actor)
        assert await counts(source.primary_case_id) == 0 and not any(x.initial_task for x in cleared.allocation.allocations)
        receipts.update(move=move.model_dump(mode='json'),cleared=cleared.model_dump(mode='json'))
        result['checks'].append('move_actual_source_target_empty_replace_no_task')

        before = await snapshot()
        await expect_error('case_scope_revision_conflict', cases.associate(tenant,root,AssociationRequest(operation_key=uuid4(),expected_scope_revision=999999,alert_ids=[alerts[410]]),actor=actor))
        await expect_error('operation_key_conflict', cases.create_case(tenant,req_event.model_copy(update={'title':'different'}),actor=actor))
        await expect_error('member_alert_not_found', cases.associate(tenant,root,AssociationRequest(operation_key=uuid4(),expected_scope_revision=await revision(root),alert_ids=[alerts[410],uuid4()]),actor=actor))
        assert await snapshot() == before
        result['checks'].append('version_operation_missing_member_conflicts_atomic')

        relation = await cases.read_related_cases(tenant,chain.primary_case_id,limit=1)
        assert relation.items[0].primary_relation == 'continuation' and relation.next_cursor
        all_related = await cases.read_related_cases(tenant,chain.primary_case_id,limit=100)
        assert len({x.case_id for x in all_related.items}) == all_related.total
        assert any(x.relation_types == ['continuation','shared_incident'] for x in all_related.items)
        shared_only = await cases.create_case(tenant,CaseCreate(operation_key=uuid4(),title='Member-only intersection',alert_ids=[alerts[20]]),actor=actor)
        await expect_error('cursor_stale',cases.read_related_cases(tenant,chain.primary_case_id,limit=1,cursor=relation.next_cursor))
        unchanged = await snapshot()
        all_related = await cases.read_related_cases(tenant,chain.primary_case_id,limit=100)
        member_only = next(x for x in all_related.items if x.case_id == shared_only.primary_case_id)
        assert member_only.primary_relation == 'shared_incident' and member_only.shared_incidents[0].related_case_sources == ['member_alert']
        page = await pages.read(tenant,'incidents',event,'records',section='cases',limit=100,offset=0)
        assert sum(bool(x['is_active_receiver']) for x in page.items) == 1
        alert_page = await pages.read(tenant,'alerts',alerts[20],'records',section='cases',limit=100,offset=0)
        assert all('is_active_receiver' not in x for x in alert_page.items)
        detail = await cases.read_case(tenant,old_receiver)
        assert detail['case'].continuation.receiving_case_id == extended.receiving_case_id
        assert await snapshot() == unchanged
        receipts.update(related=all_related.model_dump(mode='json'),incident_cases=page.model_dump(mode='json'))
        result['checks'].append('relations_order_dedup_sources_cursor_readonly_alert_contract_unchanged')

        stopped = await tasks.submit(tenant,kind='case_investigation',subject_id=receiver,intent='check',source='user',operation_key=uuid4(),submitted_by=actor_id)
        async with tasks.transaction(tenant) as store:
            await store.db.execute(update(m.AnalysisTasks).where(m.AnalysisTasks.tenant_id==tenant,m.AnalysisTasks.id==stopped['task_id']).values(
                state='failed',ended_at=await store.now(),reason_code='synthetic_stopped_state_fixture',error_detail={'fixture':True,'no_model_or_executor':True}))
            await store.stop_subject(await store.task(stopped['task_id']),None,'automatic_attempts_stopped')
        assert (await pages.read(tenant,'incidents',event,'view')).case_receiving.can_receive_automatically
        # A fixture clock anchor tests the one-week boundary without waiting or mutating any Run.
        async with cases.transaction(tenant) as store:
            await store.db.execute(update(m.Cases).where(m.Cases.tenant_id==tenant,m.Cases.id==receiver).values(created_at=text("clock_timestamp()-interval '8 days'")))
        assert (await pages.read(tenant,'incidents',event,'view')).case_receiving.reason_code == 'auto_window_expired'
        assert await cases.follow_incident(tenant,receiver,FollowIncident(operation_key=uuid4(),incident_id=event),actor=actor) is None
        _, manual_expired = await add(root,[alerts[411]])
        assert next(x for x in manual_expired.allocations if x.case_id == receiver).added_alert_ids == [alerts[411]]
        receipts['manual_expired'] = manual_expired.model_dump(mode='json')
        result['checks'].append('analysis_stop_does_not_block_receiving_expired_auto_stops_manual_allowed')

        # Dedicated closed receiver; original main event remains expired for HTTP readback.
        closed = await cases.create_case(tenant,CaseCreate(operation_key=uuid4(),title='Closed receiver',alert_ids=[alerts[440]]),actor=actor)
        async with cases.transaction(tenant) as store:
            await store.db.execute(update(m.Cases).where(m.Cases.tenant_id==tenant,m.Cases.id==closed.primary_case_id).values(
                handling_status='resolved',resolved_at=await store.now(),resolved_by=actor_id,resolution_note='Synthetic closed receiver'))
        await expect_error('resolved_case_scope_policy_not_enabled',cases.associate(tenant,closed.primary_case_id,AssociationRequest(operation_key=uuid4(),expected_scope_revision=await revision(closed.primary_case_id),alert_ids=[alerts[441]]),actor=actor))
        result['checks'].append('closed_receiver_rejects_manual_allocation')
        exported = await snapshot()
        assert not exported['runs'] and not exported['analysis_attempts']
        initial = [t for t in exported['analysis_tasks'] if t['intent']=='initial']
        assert len(initial) == len(exported['cases'])
        for task in initial:
            assert task['state']=='accepted'
        result['synthetic_stopped_state_task_id'] = stopped['task_id']
        task = first.allocations[0].initial_task
        read_task = await tasks.read_task(tenant,'case',cid,task.task_id)
        save(out/'task.json',read_task)
        result.update(state='passed',counts={k:len(v) for k,v in exported.items()},http_sample={
            'case_99':cid,'case_overflow':overflow.receiving_case_id,'event_chain':chain.primary_case_id,
            'independent_root':root,'active_receiver':receiver,'closed_case':closed.primary_case_id,
            'task_id':task.task_id,'spare_alert_ids':alerts[420:430], 'alert_id':alerts[20]})
        save(out/'database.json',exported)
    except BaseException as exc:
        result.update(state='failed',error=type(exc).__name__,traceback=traceback.format_exc())
        raise
    finally:
        save(out/'receipts.json',receipts)
        save(out/'result.json',result)
        await engine.dispose()
        await admin.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',required=True)
    parser.add_argument('--batch',required=True)
    asyncio.run(main(parser.parse_args()))
