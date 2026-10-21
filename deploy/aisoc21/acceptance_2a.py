"""Real HTTP/Kafka/Fusion/PG/Redis2A diagnosis; no model or vendor calls.

One checkpoint per submission. Never auto-resubmit an unconfirmed request.
Only one verified, fixture-owned dedup cache key may be removed.
"""
import asyncio,hashlib,json,os,sys,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,"/app")
import asyncpg,httpx,redis.asyncio as redis
from aiokafka import AIOKafkaConsumer
from aiokafka.structs import TopicPartition
from app.core.kafka_security import kafka_client_kwargs
from app.schemas.fusion_alert import RawAlert
E=Path('/evidence');B=os.getenv('SOCAI2_TEST_BATCH','2a-20261020');RAW='socai2.alerts.raw';FUSED='socai2.alerts.fused'

def save(name,data):
    with (E/name).open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2,default=str);f.write('\n')
def decode(x):return json.loads(x) if isinstance(x,(str,bytes)) else x

async def main():
    assert not (E/'probe-started.json').exists(),'Inspect prior checkpoints; do not replay'
    ids=json.loads(Path('/private/app-2a.json').read_text())['identities'];save('probe-started.json',{'batch':B,'at':datetime.now(timezone.utc)})
    consumer=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=None,enable_auto_commit=False,**kafka_client_kwargs())
    db=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'))
    cache=redis.from_url(os.environ['REDIS_URL'],decode_responses=False)
    messages=[];checks=[];steps={}
    await consumer.start();parts=[TopicPartition(t,i) for t in [RAW,FUSED] for i in range(3)];consumer.assign(parts);await consumer.seek_to_end(*parts)
    initial=await consumer.end_offsets(parts)
    async def cache_incident(incident_id):
        data=await cache.get('aisoc:fusion:incident:'+str(incident_id));return decode(data) if data else None
    try:
      async with httpx.AsyncClient(base_url='http://api:8000',timeout=30,trust_env=False) as http:
        async def request(method,path,name=None,body=None,expected=200):
            r=await http.request(method,path,headers={'Authorization':'Bearer '+ids[name]['key']} if name else {},json=body)
            checks.append({'method':method,'path':path,'identity':name,'status':r.status_code,'expected':expected})
            assert r.status_code==expected,(path,r.status_code)
            return r
        now=datetime.now(timezone.utc)
        base={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/a1')),'source':'socai2-'+B,'title':'socai2 '+B+' execution finding','description':'Synthetic existing finding; no real host/vendor access','severity':'medium','src_ip':os.getenv('SOCAI2_TEST_SRC_IP','198.18.2.1'),'hostname':'socai2-2a-test-host','mitre_tactics':['execution'],'mitre_techniques':['T1059.001'],'event_time':now.isoformat(),'source_event_ids':[B+'-source-a1'],'external_id':B+'-finding-a1','connector_type':'migration-test','tags':[B],'raw_event':{'batch':B,'occurrence':'a1','synthetic':True}}
        def variant(label,**overrides):
            return {**base,'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/'+label)),'source_event_ids':[B+'-source-'+label],'external_id':B+'-finding-'+label,'raw_event':{'batch':B,'occurrence':label,'synthetic':True},**overrides}
        await request('POST','/api/v1/alert-ingress',body=base,expected=401)
        await request('POST','/api/v1/alert-ingress','a',{**base,'tenant_id':ids['b']['tenant_id']},403)
        assert initial==await consumer.end_offsets(parts)
        save('rejected-http.json',{'checks':checks.copy(),'no_broker_offset_change':True})
        async def submit(label,body,identity='a'):
            save(label+'-sending.json',{'input':body,'identity':identity,'operation':'One explicit submission, no retries'})
            ack=(await request('POST','/api/v1/alert-ingress',identity,body,202)).json();save(label+'-accepted.json',ack)
            raw=None;fused=None;observed=[]
            for _ in range(30):
                batches=await consumer.getmany(timeout_ms=1000)
                for tp,items in batches.items():
                    for msg in items:
                        value=decode(msg.value);alert=value.get('alert',value)
                        if B not in alert.get('tags',[]):continue
                        item={'topic':msg.topic,'partition':msg.partition,'offset':msg.offset,'sha256':hashlib.sha256(msg.value).hexdigest(),'value':value};messages.append(item);observed.append(item)
                        if msg.topic==RAW and (msg.partition,msg.offset)==(ack['message']['partition'],ack['message']['offset']):raw=item
                        if msg.topic==FUSED and value.get('tenant_id')==ids[identity]['tenant_id'] and body['id'] in alert.get('source_event_ids',[]):
                            assert fused is None,'Unexpected multiple fused results for current submission';fused=item
                if raw and fused:break
            assert raw and fused,'Unconfirmed processing: inspect retained broker receipt, do not replay'
            v=fused['value'];assert v['id']==ack['canonical_alert_id']==v['alert_row_id']
            detail=(await request('GET',ack['result_url'],identity)).json()
            row=await db.fetchrow('SELECT id,tenant_id,dedup_hash,event_time,raw_event,source_event_ids,external_id,first_seen,last_seen FROM alerts WHERE id=$1',uuid.UUID(v['id']))
            assert row and str(row['tenant_id'])==ids[identity]['tenant_id']
            model=RawAlert.model_validate({**body,'tenant_id':ids[identity]['tenant_id']})
            result={'input':body,'identity':identity,'receipt':ack,'raw_record':raw,'fused_record':fused,'pg_row':dict(row),'api_detail':detail,'fingerprint':model.fingerprint(),'correlation_key':model.correlation_key(),'incident_snapshot':await cache_incident(v.get('incident_id')) if v.get('incident_id') else None}
            save(label+'-result.json',result);steps[label]=result
            return result
        a1=await submit('01-original',base)
        if os.getenv('SOCAI2_PROBE_MODE')=='replay-fix':
            related=await submit('02-related',variant('related',title='socai2 '+B+' related signal',mitre_techniques=['T1105']))
            incident_before=related['incident_snapshot'];assert incident_before['alert_count']==2
            key='aisoc:fusion:dedup:'+a1['fingerprint'];value=await cache.get(key)
            assert value and value.decode()==a1['receipt']['canonical_alert_id'] and base['source']=='socai2-'+B
            save('cache-loss-before.json',{'key':key,'owned_tenant':ids['a']['tenant_id'],'incident_before':incident_before,'only_own_key_removed':True})
            assert await cache.unlink(key)==1
            replay=await submit('03-cache-miss-replay',base)
            incident_after=replay['incident_snapshot'];assert incident_after['id']==incident_before['id']
            assert incident_after['alert_count']==2 and incident_after['alert_ids']==incident_before['alert_ids']
            assert incident_after['last_seen']==incident_before['last_seen']
            assert replay['fused_record']['value']['persist_outcome']=='duplicate'
            assert decode(replay['pg_row']['source_event_ids'])==decode(a1['pg_row']['source_event_ids'])
            save('acceptance.json',{'batch':B,'status':'Replay member-count fix passed on real services','checks':checks,'submissions':3,'incident_before':incident_before,'incident_after':incident_after,'last_seen_unchanged':True,'pg_source_list_unchanged':True,'cache_loss_simulated':True,'persist_outcome':'duplicate','decision':replay['fused_record']['value']['fusion_decision'],'scope':'Membership/count/time idempotence only; independent occurrence identity unresolved; downstream risk replay accounting remains2B'})
            print(json.dumps({'submissions':3,'http_checks':len(checks),'distinct_incident_members':2,'incident_count':2,'status':'member replay fix passed'}));return
        replay=await submit('02-exact-replay',base)
        a2=await submit('03-distinct-occurrence',variant('a2',event_time=(now+timedelta(minutes=1)).isoformat()))
        a3=await submit('04-related-alert',variant('a3',title='socai2 '+B+' second execution signal',mitre_techniques=['T1105']))
        a4=await submit('05-other-entity',variant('a4',src_ip='198.18.2.2',hostname='socai2-2a-other-host'))
        # Change title as well as tactic: the original fingerprint omits tactics.
        a5=await submit('06-other-tactic',variant('a5',title='socai2 '+B+' credential finding',mitre_tactics=['credential-access'],mitre_techniques=['T1003']))
        b1=await submit('07-other-tenant',base,'b')
        await request('GET',a1['receipt']['result_url'],'b',expected=404);await request('GET',b1['receipt']['result_url'],'a',expected=404)
        oldincident=a3['incident_snapshot'];key='aisoc:fusion:dedup:'+a1['fingerprint'];value=await cache.get(key);ttl=await cache.ttl(key)
        assert value and value.decode()==a1['receipt']['canonical_alert_id'] and ttl>0
        assert base['source']=='socai2-'+B and a1['pg_row']['tenant_id']==uuid.UUID(ids['a']['tenant_id'])
        save('cache-loss-before.json',{'dedup_key':key,'owned_tenant':ids['a']['tenant_id'],'value':value.decode(),'ttl_before':ttl,'incident_before':oldincident,'only_own_key_removed':True})
        assert await cache.unlink(key)==1
        cached=await submit('08-replay-cache-miss',base)
        latest=await cache_incident(cached['fused_record']['value']['incident_id'])
        finalrows=await db.fetch('SELECT id,tenant_id,title,source_event_ids,event_time,external_id,raw_event FROM alerts WHERE tenant_id=ANY($1::uuid[]) ORDER BY tenant_id,id',[uuid.UUID(i['tenant_id']) for i in ids.values()])
        def value(s):return s['fused_record']['value']
        assert value(a1)['fusion_decision']=='new_incident' and value(a1)['persist_outcome']=='inserted'
        assert value(replay)['fusion_decision']=='duplicate' and value(replay)['persist_outcome']=='duplicate'
        assert decode(replay['pg_row']['source_event_ids'])==decode(a1['pg_row']['source_event_ids'])
        assert value(a2)['fusion_decision']=='duplicate' and a2['receipt']['canonical_alert_id']==a1['receipt']['canonical_alert_id']
        assert a2['input']['source_event_ids'][0] in decode(a2['pg_row']['source_event_ids'])
        assert decode(a2['pg_row']['raw_event'])==decode(a1['pg_row']['raw_event'])
        assert value(a3)['incident_id']==value(a1)['incident_id'] and value(a3)['fusion_decision']=='correlated'
        assert a3['incident_snapshot']['alert_count']==2
        assert value(a4)['incident_id']!=value(a1)['incident_id'] and value(a5)['incident_id']!=value(a1)['incident_id']
        assert value(b1)['incident_id']!=value(a1)['incident_id'] and b1['receipt']['canonical_alert_id']!=a1['receipt']['canonical_alert_id']
        assert len(finalrows)==5
        findings=[{'id':'2A-01','severity':'blocking','actual':'Distinct source occurrence shares canonical alert; PG keeps first event_time/raw_event/external_id, later source IDs only','inputs':['01-original','03-distinct-occurrence'],'desired':'Trace occurrence identity, time and material independently while allowing grouped view'}, {'id':'2A-02','severity':'blocking','actual':'After one owned dedup key removed, exact replay increments Redis incident before PG confirms duplicate','inputs':['04-related-alert','08-replay-cache-miss'],'desired':'Same canonical alert replay does not increase incident membership/count'}]
        assert value(cached)['persist_outcome']=='duplicate' and value(cached)['fusion_decision']=='correlated'
        assert latest['alert_count']==3 and len(set(latest['alert_ids']))==2
        save('acceptance.json',{'batch':B,'status':'Diagnosis completed;2A business acceptance blocked by reproduced defects','checks':checks,'steps':list(steps),'final_pg_rows':[dict(r) for r in finalrows],'incident_after_cache_miss':latest,'findings':findings,'normal_scope_boundaries_passed':True,'no_model_or_vendor_calls_requested':True,'business_source_or_runtime_config_changed':False,'cache_loss_simulated_not_natural_ttl_expiry':True,'new_source_occurrence_payload_retained_in_raw_and_fused_broker_evidence':True})
        print(json.dumps({'submissions':len(steps),'http_checks':len(checks),'pg_rows':len(finalrows),'blocking_findings':len(findings),'status':'2A blocked, diagnostic evidence retained'}))
    finally:
        await db.close();await cache.aclose();await consumer.stop()
if __name__=='__main__':
    try:asyncio.run(asyncio.wait_for(main(),240))
    except Exception as e:
        save('probe-failed.json',{'error_type':type(e).__name__,'instruction':'Inspect checkpoints, never replay unknown submissions'});raise
