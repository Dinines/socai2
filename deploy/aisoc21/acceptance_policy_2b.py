"""Real authenticated policy API/PG and direct production-method consumption.

The automatic Kafka consumer remains off; no model/vendor call is made.
"""
import asyncio,hashlib,json,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,'/app')
import asyncpg,httpx
from app.workers.business_context import BusinessContextApplier
from app.workers import business_context as bc
from app.workers.fused_alert_consumer import FusedAlertTriageWorker
E=Path('/evidence');B='2b-policy-20261020';P='/api/v1/business-context/rules'
def save(n,v):
    with (E/n).open('x') as f:json.dump(v,f,indent=2,default=str)
def yaml_version(v):
    return f'''rules:
  - id: policy-routing
    priority: 5
    when: {{field: hostname, op: eq, value: socai2-policy-host}}
    then: {{set_severity: {'high' if v==1 else 'critical'}, route_to: {'cloud' if v==1 else 'identity'}, tag: policy-v{v}}}
  - id: policy-maintenance
    priority: 10
    when: {{field: username, op: eq, value: socai2-policy-maint}}
    then: {{suppress: true}}
'''
async def main(mode):
    save(mode+'-started.json',{'mode':mode,'at':datetime.now(timezone.utc)})
    ids=json.loads(Path('/private/state.json').read_text())['identities'];checks=[]
    async with httpx.AsyncClient(base_url='http://api:8000',timeout=25,trust_env=False) as client:
      async def req(method,path,identity='a',body=None,status=200):
        r=await client.request(method,path,headers={'Authorization':'Bearer '+ids[identity]['key']} if identity else {},json=body)
        checks.append({'method':method,'path':path,'identity':identity,'status':r.status_code,'expected':status});assert r.status_code==status,(r.status_code,r.text[:300]);return r.json()
      if mode=='before':
        a=await req('GET',P);b=await req('GET',P)
        assert b['version']>a['version'] and 'policy_revision' not in a
        save('before-acceptance.json',{'repeated_get_versions':[a['version'],b['version']],'stable_content_revision_absent':True,'checks':checks});print(json.dumps({'versions':[a['version'],b['version']],'stable_revision_absent':True}));return
      if mode=='restart':
        old=json.loads((E/'after-acceptance.json').read_text());rules=await req('GET',P)
        assert rules['policy_revision']==old['v1']['policy_revision']
        consumed=await BusinessContextApplier().apply_for_tenant(ids['a']['tenant_id'],old['normal_input'])
        assert consumed.provenance['policy_revision']==rules['policy_revision'] and consumed.alert==old['v1_output']
        for label,item in old['alerts'].items():
            detail=await req('GET','/api/v1/alerts/'+item['canonical_id'],item['identity'])
            assert detail['raw_event']==item['api']['raw_event'] and detail['fusion_incident_id']==item['api']['fusion_incident_id'] and detail['severity']=='low'
        save('restart-acceptance.json',{'checks':checks,'rule_revision_and_original_alerts_preserved':True,'fresh_applier_revision':consumed.provenance,'same_normal_output':True});print(json.dumps({'restart_checks':len(checks),'unchanged':True}));return
      assert mode=='after'
      db=await asyncpg.connect((os.environ.get('DATABASE_DSN') or os.environ['DATABASE_URL']).replace('postgresql+asyncpg://','postgresql://'))
      try:
        await req('GET',P,identity=None,status=401)
        await req('POST',P,'read_a',{'yaml':yaml_version(1)},403)
        await req('POST',P,'a',{'yaml':'rules: [invalid]'},422)
        a0=await req('GET',P);b0=await req('GET',P,'b');assert a0['yaml']==b0['yaml']==''
        v1=await req('POST',P,'a',{'yaml':yaml_version(1)});same=await req('GET',P)
        assert same['policy_revision']==v1['policy_revision']==bc.policy_revision(yaml_version(1),True)
        assert same['version']>v1['version']
        rows=await db.fetch('SELECT tenant_id,yaml_text,enabled,updated_at FROM aisoc_business_context_rule_sets WHERE tenant_id=ANY($1::uuid[])',[uuid.UUID(ids[n]['tenant_id']) for n in ['a','b']]);assert len(rows)==1 and str(rows[0]['tenant_id'])==ids['a']['tenant_id'] and rows[0]['yaml_text']==yaml_version(1)
        save('policy-v1.json',{'api':v1,'pg_rows':[dict(r) for r in rows]})
        alerts={}
        for label,identity,username in [('normal','a','socai2-policy-user'),('maintenance','a','socai2-policy-maint'),('other','b','socai2-policy-user')]:
            raw={'batch':B,'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/'+label)),'source':'socai2-'+B,'title':'Synthetic policy '+label,'hostname':'socai2-policy-host','username':username,'severity':'low'}
            body={k:v for k,v in raw.items() if k!='batch'};body.update(raw_event=raw,source_event_ids=[B+'-'+label],event_time=datetime.now(timezone.utc).isoformat(),tags=[B])
            save('alert-'+label+'-sending.json',{'input':body,'identity':identity})
            ack=await req('POST','/api/v1/alert-ingress',identity,body,202);save('alert-'+label+'-ack.json',ack)
            for _ in range(40):
                r=await client.get('/api/v1/alerts/'+ack['canonical_alert_id'],headers={'Authorization':'Bearer '+ids[identity]['key']})
                if r.status_code==200:break
                assert r.status_code==404;await asyncio.sleep(.25)
            else:raise RuntimeError('Alert accepted but material not confirmed; do not resubmit')
            detail=r.json();assert detail['raw_event']==raw and detail['severity']=='low'
            item={'identity':identity,'canonical_id':ack['canonical_alert_id'],'api':detail,'receipt':ack};alerts[label]=item;save('alert-'+label+'-result.json',item)
        def message(label):
            item=alerts[label];tenant=ids[item['identity']]['tenant_id']
            return {'tenant_id':tenant,'id':item['canonical_id'],'incident_id':item['api']['fusion_incident_id'],'alert':{**item['api']['raw_event'],'id':item['canonical_id'],'tenant_id':tenant}}
        applier=BusinessContextApplier();a=ids['a']['tenant_id'];b=ids['b']['tenant_id'];normal=message('normal')['alert']
        first=await applier.apply_for_tenant(a,normal);assert first.alert['severity']=='high' and first.alert['route_to']=='cloud' and first.provenance['policy_revision']==v1['policy_revision']
        worker=FusedAlertTriageWorker(bootstrap_servers='',business_context=applier)
        suppressed=await worker.triage(message('maintenance'));assert suppressed['suppressed'] and suppressed['business_context_policy']['policy_revision']==v1['policy_revision'] and not suppressed['response_dispatched']
        other=await applier.apply_for_tenant(b,message('other')['alert']);assert not other.changed and other.provenance['load_status']=='empty'
        v2=await req('POST',P,'a',{'yaml':yaml_version(2)});assert v2['policy_revision']!=v1['policy_revision']
        cached=await applier.apply_for_tenant(a,normal);assert cached.alert==first.alert and cached.provenance['load_status']=='cache' and cached.provenance['policy_revision']==v1['policy_revision']
        save('policy-cache-before-expiry.json',{'saved_api':v2,'actually_applied':cached.provenance,'output':cached.alert,'cache_ttl_seconds':30,'waiting_actual_ttl':True})
        await asyncio.sleep(30.5)
        second=await applier.apply_for_tenant(a,normal);assert second.alert['severity']=='critical' and second.alert['route_to']=='identity' and second.provenance['policy_revision']==v2['policy_revision']
        restore=await req('POST',P,'a',{'yaml':yaml_version(1)});assert restore['policy_revision']==v1['policy_revision'] and restore['updated_at']!=v1['updated_at']
        # A new process/applier adopts restored policy immediately; existing workers retain their bounded TTL.
        fresh=BusinessContextApplier();restored=await fresh.apply_for_tenant(a,normal)
        assert restored.alert==first.alert and restored.provenance['policy_revision']==v1['policy_revision']
        assert first.alert['severity']=='high' and second.alert['severity']=='critical'
        # Only this probe process points to a closed loopback port. Shared PG stays up.
        olddsn=os.environ.get('DATABASE_DSN');os.environ['DATABASE_DSN']='postgresql://nobody@127.0.0.1:1/nope'
        try:
            stamp,rules=fresh._tenant_rules[a];fresh._tenant_rules[a]=(0,rules)
            stale=await fresh.apply_for_tenant(a,normal);cold=await BusinessContextApplier().apply_for_tenant(a,normal)
            assert stale.alert==first.alert and stale.provenance['load_status']=='stale_cache'
            assert stale.provenance['policy_revision']==v1['policy_revision']
            assert cold.provenance['load_status']=='unavailable' and cold.provenance['policy_revision'] is None and not cold.changed
        finally:
            if olddsn is None:os.environ.pop('DATABASE_DSN',None)
            else:os.environ['DATABASE_DSN']=olddsn
        b1=await req('GET',P,'b');assert b1['yaml']==b0['yaml'] and b1['policy_revision']==b0['policy_revision']
        save('after-acceptance.json',{'checks':checks,'v1':v1,'v2':v2,'restored':restore,'alerts':alerts,'normal_input':normal,'v1_output':first.alert,'v2_output':second.alert,'v1_actual':first.provenance,'v2_actual':second.provenance,'cached_v1_while_api_v2':cached.provenance,'restored_actual':restored.provenance,'stale_on_dependency_failure':stale.provenance,'cold_dependency_failure':cold.provenance,'suppression_actual_worker_summary':suppressed,'other_tenant':other.provenance,'direct_worker_method_only':True,'automatic_kafka_worker_started':False,'model_calls':0,'previous_results_not_rewritten':True})
        print(json.dumps({'http_checks':len(checks),'ingress_alerts':3,'real_pg_policy_read':True,'actual_ttl_observed':True,'worker_suppression':True,'versions_match':True,'model_calls':0}))
      finally:await db.close()
if __name__=='__main__':asyncio.run(asyncio.wait_for(main(sys.argv[1]),220))
