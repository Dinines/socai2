"""Actual API/PG production-method policy receipts; checkpointed modes."""
import asyncio,copy,hashlib,json,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
import asyncpg,httpx
sys.path.insert(0,'/app')
from app.investigator import ledger
from app.workers.business_context import BusinessContextApplier
from app.workers.fused_alert_consumer import FusedAlertTriageWorker,worker_enabled
E=Path('/evidence');B='3a-suppression-20261020';P='/api/v1/business-context/rules'
YAML='''rules:
  - id: authorized-maintenance
    when: {field: username, op: eq, value: socai2-3a-maint}
    then: {suppress: true}
'''
def save(n,x):
    with (E/n).open('x') as f:json.dump(x,f,indent=2,default=str)
async def main(mode):
    save(mode+'-started.json',{'at':datetime.now(timezone.utc)})
    ids=json.loads(Path('/private/state.json').read_text())['identities'];checks=[]
    db=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'))
    assert not worker_enabled()
    async with httpx.AsyncClient(base_url='http://api:8000',trust_env=False,timeout=25) as c:
      async def req(method,path,n='a',body=None,status=200):
        r=await c.request(method,path,headers={'Authorization':'Bearer '+ids[n]['key']} if n else {},json=body)
        checks.append({'method':method,'path':path,'identity':n,'status':r.status_code,'expected':status});(E/(mode+'-http-checks.json')).write_text(json.dumps(checks,indent=2));assert r.status_code==status,(r.status_code,r.text[:150]);return r.json()
      try:
        if mode=='before':
            rules=json.loads((E/'rules-before.json').read_text()) if (E/'rules-before.json').exists() else await req('POST',P,body={'enabled':True,'yaml':YAML})
            if not (E/'rules-before.json').exists():save('rules-before.json',rules)
            inputs={};alerts={}
            for n in ['a','b']:
                value={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/'+n)),'source':'socai2-'+B,'source_event_ids':[B+'-'+n],'title':'Authorized policy receipt fixture','severity':'low','hostname':'socai2-3a-host','username':'socai2-3a-maint','event_time':datetime.now(timezone.utc).isoformat(),'tags':[B],'raw_event':{'synthetic':True,'batch':B}}
                save('input-'+n+'-sending.json',value)
                ack=await req('POST','/api/v1/alert-ingress',n,value,202)
                save('input-'+n+'-ack.json',ack)
                for _ in range(80):
                    r=await c.get('/api/v1/alerts/'+ack['canonical_alert_id'],headers={'Authorization':'Bearer '+ids[n]['key']})
                    if r.status_code==200:break
                    assert r.status_code==404;await asyncio.sleep(.25)
                else:raise RuntimeError('Accepted outcome unknown; no resubmission')
                alerts[n]=r.json();inputs[n]={'id':ack['canonical_alert_id'],'alert_row_id':ack['canonical_alert_id'],'tenant_id':ids[n]['tenant_id'],'alert':{**value,'id':ack['canonical_alert_id'],'tenant_id':ids[n]['tenant_id']}}
            old=await FusedAlertTriageWorker(bootstrap_servers='',business_context=BusinessContextApplier()).triage(inputs['a'])
            assert old['suppressed'] and 'policy_receipt' not in old
            count=await db.fetchval('SELECT count(*) FROM investigation_runs WHERE tenant_id=$1',uuid.UUID(ids['a']['tenant_id']));assert count==0
            save('before-acceptance.json',{'rules':rules,'inputs':inputs,'alerts':alerts,'old_summary':old,'old_tenant_ledger_runs':count,'checks':checks});return
        old=json.loads((E/'before-acceptance.json').read_text());inputs=old['inputs'];applier=BusinessContextApplier();w=FusedAlertTriageWorker(bootstrap_servers='',business_context=applier)
        if mode=='restart':
            previous=json.loads((E/'after-acceptance.json').read_text());again=await w.triage(inputs['a'])
            assert again['policy_receipt']==previous['receipt']
            for label,run_id in previous['runs'].items():
                events=await req('GET',f'/api/v1/investigations/{run_id}/events');assert events['items'][0]['kind']=='policy_decision'
            save('restart-acceptance.json',{'receipt_preserved_after_restart':again['policy_receipt'],'checks':checks});return
        if mode=='complete':
            # Resume by reading the three already committed rows. Never rerun
            # the accepted ingress or the completed write phases after a schema
            # assertion failure in the final API-read checks.
            rows=await db.fetch("SELECT e.payload FROM investigation_events e WHERE tenant_id=$1 AND kind='policy_decision' ORDER BY created_at",uuid.UUID(ids['a']['tenant_id']))
            assert len(rows)==3
            receipts=[{**json.loads(x['payload']),'persisted':True} for x in rows]
            receipt=next(x for x in receipts if not x['shadow'] and x['business_context_policy'].get('policy_revision')!='f'*64)
            recovered=next(x for x in receipts if x['business_context_policy'].get('policy_revision')=='f'*64)
            shadow=next(x for x in receipts if x['shadow'])
            assert (await w.triage(inputs['a']))['policy_receipt']==receipt
            runs={'live':receipt['run_id'],'recovered_probe_only':recovered['run_id'],'shadow':shadow['run_id']}
            for name,rid in runs.items():
                detail=await req('GET',f'/api/v1/investigations/{rid}');events=await req('GET',f'/api/v1/investigations/{rid}/events')
                assert detail['status']=='completed' and detail['event_count']==1 and detail['total_tokens']==0
                assert events['items'][0]['kind']=='policy_decision' and 'verdict' not in events['items'][0]['payload']
            await req('GET',f"/api/v1/investigations/{receipt['run_id']}",'b',status=404)
            await req('GET',f"/api/v1/investigations/{receipt['run_id']}",'denied',status=403)
            await req('GET',f"/api/v1/investigations/{receipt['run_id']}",None,status=401)
            for n in ['a','b']:
                detail=await req('GET','/api/v1/alerts/'+inputs[n]['id'],n)
                for k in ['raw_event','severity','status','disposition','ai_score','ai_summary','priority']:assert detail.get(k)==old['alerts'][n].get(k)
            save('after-acceptance.json',{'receipt':receipt,'runs':runs,'shadow_receipt':shadow,'recovered_receipt_probe_only':recovered,'same_input_replays_before_initial_final_read_failure':9,'real_pg_write_error':'Policy receipt failed (DivisionByZeroError), asserted by primary after probe before API response-field failure','rollback_left_no_half_run_asserted_in_primary_probe':True,'same_pool_recovery_asserted_in_primary_probe':True,'same_key_changed_input_rejected_in_primary_probe':True,'other_tenant_normal_branch_reached_in_primary_probe':True,'read_completion_without_ingress_or_fault_candidate_replay':True,'alert_results_unchanged':True,'checks':checks})
            return
        assert mode=='after'
        first=await w.triage(inputs['a']);receipt=first['policy_receipt'];run=receipt['run_id'];assert receipt['persisted'] and not first['response_dispatched'] and 'verdict' not in first
        duplicate=await w.triage(inputs['a']);assert duplicate['policy_receipt']==receipt
        parallel=await asyncio.gather(*(w.triage(copy.deepcopy(inputs['a'])) for _ in range(8)));assert all(x['policy_receipt']==receipt for x in parallel)
        async def counts():return dict(await db.fetchrow('SELECT (SELECT count(*) FROM investigation_runs WHERE tenant_id=$1) runs,(SELECT count(*) FROM investigation_events WHERE tenant_id=$1) events',uuid.UUID(ids['a']['tenant_id'])))
        assert await counts()=={'runs':1,'events':1}
        # Real PG transaction error after run insertion, before event write.
        # Proxy is confined to this probe; shared DB and service configuration remain intact.
        from app.investigator import policy_decisions as pd
        pool=await ledger.get_pool();original=ledger.get_pool
        class Conn:
            def __init__(self,c):self.c=c
            def __getattr__(self,n):return getattr(self.c,n)
            async def execute(self,sql,*a):
                if 'INSERT INTO investigation_events' in sql:return await self.c.execute('SELECT 1/0')
                return await self.c.execute(sql,*a)
        class Acquire:
            async def __aenter__(self):self.cm=pool.acquire();return Conn(await self.cm.__aenter__())
            async def __aexit__(self,*a):return await self.cm.__aexit__(*a)
        class Pool:
            def acquire(self):return Acquire()
        async def failing_pool():return Pool()
        changed=copy.deepcopy(receipt['business_context_policy']);changed['policy_revision']='f'*64
        ledger.get_pool=failing_pool
        try:
            try:await pd.persist_policy_suppression(tenant_ref=ids['a']['tenant_id'],alert_id=inputs['a']['id'],raw_alert=inputs['a']['alert'],policy=changed,matched_rules=['authorized-maintenance'])
            except ledger.LedgerPersistError as e:failure=str(e)
            else:raise AssertionError('Write failure swallowed')
        finally:ledger.get_pool=original
        assert await counts()=={'runs':1,'events':1}
        recovered=await pd.persist_policy_suppression(tenant_ref=ids['a']['tenant_id'],alert_id=inputs['a']['id'],raw_alert=inputs['a']['alert'],policy=changed,matched_rules=['authorized-maintenance'])
        assert await counts()=={'runs':2,'events':2}
        altered=copy.deepcopy(inputs['a']);altered['alert']['title']='changed same-key input'
        try:await w.triage(altered)
        except ledger.LedgerPersistError:conflict=True
        else:raise AssertionError('Frozen input overwritten')
        assert await counts()=={'runs':2,'events':2}
        # Same entity in B has no rule: stop exactly upon entering normal model-config resolution.
        async def normal_branch(_):raise RuntimeError('probe-normal-branch')
        w._resolve_tenant_llm=normal_branch
        try:await w.triage(inputs['b'])
        except RuntimeError as e:assert str(e)=='probe-normal-branch'
        else:raise AssertionError('Other tenant incorrectly suppressed')
        # Live shadow observes the rule and writes a distinct receipt without alert updates.
        from app.workers.shadow_mode import ShadowModeTriageWriter,ShadowDecision
        from app.workers.triage_persistence import LiveTriageWriter
        sw=ShadowModeTriageWriter(LiveTriageWriter(),ShadowDecision(tenant_ref=ids['a']['tenant_id'],alert_class='unclassified',alert_id=inputs['a']['id']))
        shadow=await sw.persist_policy_suppression(tenant_ref=ids['a']['tenant_id'],alert_id=inputs['a']['id'],raw_alert=inputs['a']['alert'],policy=receipt['business_context_policy'],matched_rules=receipt['business_context_rules'])
        assert shadow['shadow'] and shadow['run_id']!=run
        # Cross-tenant reference cannot produce a receipt even if passed to the writer directly.
        try:await pd.persist_policy_suppression(tenant_ref=ids['b']['tenant_id'],alert_id=inputs['a']['id'],raw_alert={},policy=changed,matched_rules=['test'])
        except ledger.LedgerPersistError:pass
        else:raise AssertionError('Cross tenant reference written')
        runs={'live':run,'recovered':recovered['run_id'],'shadow':shadow['run_id']}
        for name,rid in runs.items():
            detail=await req('GET',f'/api/v1/investigations/{rid}');events=await req('GET',f'/api/v1/investigations/{rid}/events')
            assert detail['status']=='completed' and detail['total_tokens']==0 and detail['event_count']==1
            assert events['items'][0]['kind']=='policy_decision' and 'verdict' not in events['items'][0]['payload']
        await req('GET',f'/api/v1/investigations/{run}','b',status=404)
        await req('GET',f'/api/v1/investigations/{run}','denied',status=403)
        await req('GET',f'/api/v1/investigations/{run}',None,status=401)
        for n in ['a','b']:
            detail=await req('GET','/api/v1/alerts/'+inputs[n]['id'],n)
            for k in ['raw_event','severity','status','disposition','ai_score','ai_summary','priority']:assert detail.get(k)==old['alerts'][n].get(k),(k,detail.get(k),old['alerts'][n].get(k))
        save('after-acceptance.json',{'receipt':receipt,'runs':runs,'shadow_receipt':shadow,'recovered_receipt':recovered,'same_input_replays':9,'real_pg_write_error':failure,'rollback_left_no_half_run':True,'same_pool_recovered':True,'same_key_changed_input_rejected':conflict,'other_tenant_normal_branch_reached':True,'alert_results_unchanged':True,'checks':checks})
      finally:
        await db.close();await ledger.close_pool()
if __name__=='__main__':asyncio.run(main(sys.argv[1]))
