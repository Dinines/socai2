"""Real alert ingress and read-only current-context observations, checkpointed."""
import asyncio,json,os,sys,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
import asyncpg,httpx
E=Path('/evidence');B='2c-context-20261020'
def save(n,v):
    with (E/n).open('x') as f:json.dump(v,f,indent=2,default=str)
async def main(mode):
    save(mode+'-started.json',{'at':datetime.now(timezone.utc)})
    state=json.loads(Path('/private/state.json').read_text());ids=state['identities'];records=state['records'];checks=[]
    db=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'))
    async with httpx.AsyncClient(base_url='http://api:8000',trust_env=False,timeout=25) as c:
      async def req(method,path,identity='a',body=None,status=200):
        r=await c.request(method,path,headers={'Authorization':'Bearer '+ids[identity]['key']} if identity else {},json=body)
        checks.append({'method':method,'path':path,'identity':identity,'status':r.status_code,'expected':status});assert r.status_code==status,(r.status_code,r.text[:250]);return r.json()
      try:
        if mode=='before':
            now=datetime.now(timezone.utc);alerts={}
            for label,identity,offset,host,user in [('history','a',-3600,'socai2-context-host','SVC-Context'),('current','a',0,'socai2-context-host','SVC-Context'),('future','a',3600,'socai2-context-host','SVC-Context'),('missing','a',0,'socai2-context-missing','svc-missing'),('other','b',0,'socai2-context-host','SVC-Context'),('linked','a',0,'socai2-linked-alias',None)]:
                body={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/'+label)),'source':'socai2-'+B,'title':'Synthetic context '+label,'hostname':host,'username':user,'severity':'medium','event_time':(now+timedelta(seconds=offset)).isoformat(),'source_event_ids':[B+'-'+label],'tags':[B],'raw_event':{'batch':B,'label':label,'synthetic':True}}
                save('alert-'+label+'-sending.json',body);ack=await req('POST','/api/v1/alert-ingress',identity,body,202);save('alert-'+label+'-ack.json',ack)
                for _ in range(40):
                    r=await c.get('/api/v1/alerts/'+ack['canonical_alert_id'],headers={'Authorization':'Bearer '+ids[identity]['key']})
                    if r.status_code==200:break
                    assert r.status_code==404;await asyncio.sleep(.25)
                else:raise RuntimeError('Unknown accepted processing; inspect, no resubmission')
                item=r.json();alerts[label]={'id':ack['canonical_alert_id'],'identity':identity,'api':item,'receipt':ack};save('alert-'+label+'-result.json',alerts[label])
            tenant=ids['a']['tenant_id'];await db.execute("SELECT set_config('app.current_tenant_id',$1,false)",tenant)
            count=await db.execute('INSERT INTO alert_asset_correlations(id,tenant_id,alert_id,asset_id,match_field,confidence) VALUES ($1,$2,$3,$4,$5,1)',uuid.UUID(records['link']),uuid.UUID(tenant),uuid.UUID(alerts['linked']['id']),uuid.UUID(records['asset_a']),'synthetic-explicit-link');assert count=='INSERT 0 1'
            await req('GET','/api/v1/alerts/'+alerts['current']['id']+'/processing-context',status=404)
            save('before-acceptance.json',{'alerts':alerts,'context_route_absent':True,'checks':checks,'explicit_test_link_created':True});print(json.dumps({'accepted_alerts':6,'context_route_status_before':404}));return
        old=json.loads((E/'before-acceptance.json').read_text());alerts=old['alerts']
        async def context(label,identity=None,status=200):
            return await req('GET','/api/v1/alerts/'+alerts[label]['id']+'/processing-context',identity or alerts[label]['identity'],status=status)
        if mode=='restart':
            previous=json.loads((E/'after-acceptance.json').read_text());verified=[]
            for label,prior in previous['final_views'].items():
                current=await context(label);current.pop('queried_at');prior={k:v for k,v in prior.items() if k!='queried_at'};assert current==prior
                detail=await req('GET','/api/v1/alerts/'+alerts[label]['id'],alerts[label]['identity']);assert detail['raw_event']==alerts[label]['api']['raw_event'] and detail['severity']=='medium' and detail['priority']==50
                verified.append(label)
            save('restart-acceptance.json',{'checks':checks,'context_and_alert_material_preserved':verified,'new_inputs_submitted':False});print(json.dumps({'restart_contexts':len(verified),'http_checks':len(checks)}));return
        assert mode=='after'
        await context('current',identity='b',status=404);await context('current',identity='denied',status=403)
        await req('GET','/api/v1/alerts/'+alerts['current']['id']+'/processing-context',identity=None,status=401)
        first=await context('current');other=await context('other');missing=await context('missing');linked=await context('linked')
        assert first['priority']['score']==706 and not first['partial']
        assert first['dimensions']['identities']['rows'][0]['id']==records['identity_a']
        assert first['dimensions']['assets']['rows'][0]['id']==records['asset_a']
        assert first['dimensions']['assets']['rows'][0]['owner_email'] is None
        assert [r['id'] for r in first['dimensions']['vulnerabilities']['rows']]==[records['vuln_open']]
        assert [r['id'] for r in first['dimensions']['alert_history']['rows']]==[alerts['history']['id']]
        assert other['priority']['score']==280 and other['dimensions']['assets']['rows'][0]['id']==records['asset_b']
        assert other['dimensions']['alert_history']['rows']==[]
        assert missing['priority']['score']==350 and not missing['priority']['material_complete'] and missing['dimensions']['assets']['status']=='no_match'
        assert linked['priority']['score']==523 and linked['dimensions']['assets']['rows'][0]['id']==records['asset_a']
        assert linked['dimensions']['identities']['status']=='not_requested'
        # Only this fixture changes, demonstrating a CURRENT view instead of rewriting frozen alerts.
        tenant=ids['a']['tenant_id'];await db.execute("SELECT set_config('app.current_tenant_id',$1,false)",tenant)
        result=await db.execute("UPDATE assets SET criticality='low' WHERE id=$1 AND tenant_id=$2",uuid.UUID(records['asset_a']),uuid.UUID(tenant));assert result=='UPDATE 1'
        changed=await context('current');assert changed['priority']['score']==435 and first['priority']['score']==706
        unchanged_b=await context('other');assert unchanged_b['priority']==other['priority']
        final={'current':changed,'other':unchanged_b,'missing':missing,'linked':await context('linked')}
        for label in final:
            item=await req('GET','/api/v1/alerts/'+alerts[label]['id'],alerts[label]['identity']);assert item['raw_event']==alerts[label]['api']['raw_event'] and item['severity']=='medium' and item['priority']==50
        save('after-acceptance.json',{'checks':checks,'initial_view':first,'initial_other':other,'initial_linked':linked,'final_views':final,'changed_current':changed,'original_alert_materials_unchanged':True,'same_account_host_other_tenant_isolated':True,'historical_future_excluded':True,'closed_vulnerability_excluded':True,'no_queue_sort_or_stored_priority_change':True,'material_source_is_synthetic':True,'model_calls':0})
        print(json.dumps({'http_checks':len(checks),'initial_score':706,'new_context_score':435,'other_tenant_score':280,'stored_priority_unchanged':50,'history_before_alert_only':True}))
      finally:await db.close()
if __name__=='__main__':asyncio.run(asyncio.wait_for(main(sys.argv[1]),200))
