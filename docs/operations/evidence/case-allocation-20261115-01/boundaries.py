"""Additional direct capacity/receiver boundaries in a separate synthetic tenant."""
import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

from validate import ROOT, save


async def main():
    from app.models import socai2 as m
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_store import StoreError
    from app.socai2.case_allocation_contracts import FollowIncident
    from app.socai2.case_contracts import AssociationRequest, CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.page_reader import PageReadService
    from sqlalchemy import insert, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    here = Path(__file__).resolve().parent
    out = here / 'boundaries-01'
    out.mkdir(exist_ok=False)
    profile = ROOT / '.local/case-allocation-validation/capacity-two.json'
    save(profile, {'case': {'max_alerts':2},'source_page_size':1,'default_limit':2,'max_limit':100})
    os.environ['SOCAI2_CASE_ALLOCATION_CONFIG_FILE'] = str(profile)
    os.environ['SOCAI2_ANALYSIS_TASKS_CONFIG_FILE'] = str(ROOT/'deploy/local-investigation/analysis-tasks.json')
    cfg = json.loads((ROOT/'.local/v1.2-reader-validation/config-dev.json').read_text())
    assert cfg['processing_database']=='v12_upgrade_dev'
    url=URL.create('postgresql+psycopg',username=cfg['admin'],password=Path(cfg['password_file']).read_text().strip(),host=cfg['host'],port=cfg['port'],database=cfg['processing_database'])
    admin=create_async_engine(url,hide_parameters=True,connect_args={'sslmode':'disable'})
    engine=create_async_engine(url,hide_parameters=True,connect_args={'sslmode':'disable','options':'-c role='+cfg['processor']})
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    service,pages=CaseService(sessions),PageReadService(sessions)
    tenant,actor_id,event,empty_event=uuid4(),uuid4(),uuid4(),uuid4()
    alerts=[uuid4() for _ in range(12)]
    actor=Actor(user_id=actor_id,name='Step5 capacity/receiver')
    result={'state':'running','tenant_id':tenant,'checks':[],'model_calls':0}
    async def link(ids):
        async with service.transaction(tenant) as store:
            await store.db.execute(insert(m.IncidentAlerts),[{'id':uuid4(),'tenant_id':tenant,'incident_id':event,'alert_id':aid,
                'membership_source':'fusion','correlation_basis':{},'basis_version':'fixture','source_operation_id':uuid4()} for aid in ids])
    async def count():
        async with service.transaction(tenant,readonly=True) as store:
            return {t.name:(await store.db.execute(select(t).where(t.c.tenant_id==tenant))).mappings().all() for t in
                [m.Cases.__table__,m.CaseAlerts.__table__,m.CaseIncidents.__table__,m.AnalysisTasks.__table__]}
    try:
        async with admin.begin() as db:
            await db.execute(text("INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at) VALUES(:t,'Step5 boundaries',:slug,'enterprise',true,'{}','{}',now(),now())"),{'t':tenant,'slug':'step5-'+str(tenant)})
            await db.execute(text("INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at) VALUES(:a,:t,:email,:name,'!','soc_analyst',true,false,'{}',now(),now())"),{'a':actor_id,'t':tenant,'email':str(actor_id)+'@example.invalid','name':str(actor_id)})
        async with service.transaction(tenant) as store:
            await store.db.execute(insert(m.Alerts),[{'id':aid,'tenant_id':tenant,'source_namespace':'boundary' if n<11 else 'other','source_identity_key':str(aid),'title':'Synthetic capacity'} for n,aid in enumerate(alerts)])
            await store.db.execute(insert(m.Incidents),[{'id':iid,'tenant_id':tenant,'source_namespace':'boundary','source_incident_id':str(iid),'title':'Synthetic receiver'} for iid in [event,empty_event]])
        assert (await pages.read(tenant,'incidents',empty_event,'view')).case_receiving.reason_code=='no_target'
        await link(alerts[:1])
        first=await service.create_case(tenant,CaseCreate(operation_key=uuid4(),title='Tiny configured capacity',incident_ids=[event]),actor=actor)
        await link(alerts[1:4])
        followed=await service.follow_incident(tenant,first.receiving_case_id,FollowIncident(operation_key=uuid4(),incident_id=event),actor=actor)
        assert len(followed.allocations)==2 and [len(a.added_alert_ids) for a in followed.allocations]==[1,2]
        assert followed.receiving_case_id!=first.receiving_case_id
        assert (await pages.read(tenant,'incidents',event,'view')).case_receiving.active_case_id==followed.receiving_case_id
        result['checks'].append('configured_two_capacity_auto_follow_transfers_receiver')
        async with service.transaction(tenant) as store:
            await store.db.execute(update(m.Cases).where(m.Cases.tenant_id==tenant,m.Cases.id==first.primary_case_id).values(handling_status='resolved',resolved_at=await store.now(),resolved_by=actor_id,resolution_note='Old case only'))
        await link(alerts[4:5])
        latest=await service.follow_incident(tenant,followed.receiving_case_id,FollowIncident(operation_key=uuid4(),incident_id=event),actor=actor)
        assert latest.receiving_case_id!=followed.receiving_case_id
        result['checks'].append('closed_old_case_does_not_close_receiver_or_block_continuation')
        # Two producers target different Cases of the same chain, sharing one remaining slot.
        receiver=latest.receiving_case_id
        requests=[]
        for cid,aid in [(followed.receiving_case_id,alerts[5]),(receiver,alerts[6])]:
            detail=await service.read_case(tenant,cid)
            requests.append((cid,AssociationRequest(operation_key=uuid4(),expected_scope_revision=detail['case'].scope_revision,alert_ids=[aid])))
        outcomes=await asyncio.gather(*(service.associate(tenant,cid,req,actor=actor) for cid,req in requests),return_exceptions=True)
        # If the receiver-specific revision races, rejection is correct; retry only that user's stale revision.
        for n,value in enumerate(outcomes):
            if isinstance(value,StoreError):
                assert value.code=='case_scope_revision_conflict'
                cid,req=requests[n]
                detail=await service.read_case(tenant,cid)
                outcomes[n]=await service.associate(tenant,cid,req.model_copy(update={'expected_scope_revision':detail['case'].scope_revision}),actor=actor)
            elif isinstance(value,Exception):
                raise value
        snapshot=await count()
        assert len(snapshot['cases'])==4 and len(snapshot['case_alerts'])==7
        assert all(sum(a['case_id']==c['id'] for a in snapshot['case_alerts'])<=2 for c in snapshot['cases'])
        assert len(snapshot['analysis_tasks'])==4
        result['checks'].append('two_producers_serialize_capacity_no_overfill_one_task_per_new_case')
        active=(await pages.read(tenant,'incidents',event,'view')).case_receiving.active_case_id
        detail=await service.read_case(tenant,active)
        before=await count()
        try:
            await service.associate(tenant,active,AssociationRequest(operation_key=uuid4(),expected_scope_revision=detail['case'].scope_revision,alert_ids=[alerts[7],alerts[11]]),actor=actor)
        except StoreError as exc:
            assert exc.code=='case_source_namespace_mismatch'
        else:
            raise AssertionError('namespace accepted')
        assert await count()==before
        async with service.transaction(tenant) as store:
            await store.db.execute(update(m.Cases).where(m.Cases.tenant_id==tenant,m.Cases.id==active).values(handling_status='resolved',resolved_at=await store.now(),resolved_by=actor_id,resolution_note='Current receiver closed'))
        await link(alerts[7:8])
        before=await count()
        assert (await pages.read(tenant,'incidents',event,'view')).case_receiving.reason_code=='closed'
        assert await service.follow_incident(tenant,active,FollowIncident(operation_key=uuid4(),incident_id=event),actor=actor) is None
        assert await count()==before
        result['checks'].append('namespace_conflict_atomic_closed_receiver_no_follow_or_new_case')
        save(out/'receipts.json',{'first':first.model_dump(mode='json'),'followed':followed.model_dump(mode='json'),'latest':latest.model_dump(mode='json')})
        result.update(state='passed',case_count=4,task_count=4)
    finally:
        save(out/'result.json',result)
        await engine.dispose(); await admin.dispose()


if __name__=='__main__':
    asyncio.run(main())
