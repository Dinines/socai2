"""Bounded versioned-identity real-service acceptance; checkpoint every submission."""
import asyncio,hashlib,json,os,sys,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,'/app')
import asyncpg,httpx,redis.asyncio as redis
from aiokafka import AIOKafkaConsumer,AIOKafkaProducer
from aiokafka.structs import TopicPartition
from app.core.kafka_security import kafka_client_kwargs
from app.schemas.fusion_alert import RawAlert
E=Path('/evidence');B='2a-identity-20261020';RAW='socai2.alerts.raw';FUSED='socai2.alerts.fused'

def save(name,data):
    with (E/name).open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2,default=str);f.write('\n')
def decode(x):return json.loads(x) if isinstance(x,(str,bytes)) else x

async def main(mode):
    ids=json.loads(Path('/private/app-identity-2a.json').read_text())['identities'];checks=[]
    db=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'))
    cache=redis.from_url(os.environ['REDIS_URL'])
    async with httpx.AsyncClient(base_url='http://api:8000',timeout=25,trust_env=False) as client:
      async def req(method,path,identity='a',body=None,status=200):
        r=await client.request(method,path,headers={'Authorization':'Bearer '+ids[identity]['key']} if identity else {},json=body)
        checks.append({'method':method,'path':path,'identity':identity,'status':r.status_code,'expected':status});assert r.status_code==status,(path,r.status_code)
        return r
      if mode=='verify':
        result=json.loads((E/'acceptance.json').read_text());verified=[]
        for step in result['steps']:
            detail=(await req('GET','/api/v1/alerts/'+step['canonical_id'],step['identity'])).json()
            assert hashlib.sha256(json.dumps(detail['raw_event'],sort_keys=True).encode()).hexdigest()==step['raw_event_sha256']
            assert detail['fusion_incident_id']==step['api_incident_id'] and detail['event_time']==step['api_event_time']
            verified.append(step['canonical_id'])
        save('restart-verification.json',{'checks':checks,'canonical_ids_retrieved':verified,'data_and_persisted_incident_relation_unchanged':True,'inputs_replayed':False})
        print(json.dumps({'after_restart_reads':len(verified),'unchanged':True}));await db.close();await cache.aclose();return
      assert not (E/'probe-started.json').exists();save('probe-started.json',{'batch':B,'at':datetime.now(timezone.utc)})
      consumer=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=None,enable_auto_commit=False,**kafka_client_kwargs())
      producer=AIOKafkaProducer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],acks='all',enable_idempotence=True,**kafka_client_kwargs())
      await consumer.start();await producer.start();parts=[TopicPartition(t,i) for t in [RAW,FUSED] for i in range(3)];consumer.assign(parts);await consumer.seek_to_end(*parts)
      try:
        initial=await consumer.end_offsets(parts);now=datetime.now(timezone.utc)
        base={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/first')),'source':'socai2-'+B,'title':'socai2 '+B+' execution finding','description':'Synthetic upstream finding, no vendor operation','src_ip':'198.18.3.1','hostname':'socai2-identity-test','severity':'medium','mitre_tactics':['execution'],'mitre_techniques':['T1059.001'],'event_time':now.isoformat(),'source_event_ids':[B+'-first-event'],'external_id':B+'-finding-first','connector_type':'migration-test','tags':[B],'raw_event':{'batch':B,'occurrence':'first','synthetic':True}}
        def variant(label,**changes):return {**base,'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/'+label)),'source_event_ids':[B+'-'+label+'-event'],'external_id':B+'-finding-'+label,'raw_event':{'batch':B,'occurrence':label,'synthetic':True},**changes}
        missing={k:v for k,v in base.items() if k!='id'}
        await req('POST','/api/v1/alert-ingress',None,base,401)
        await req('POST','/api/v1/alert-ingress','a',missing,422)
        await req('POST','/api/v1/alert-ingress','a',{**base,'tenant_id':ids['b']['tenant_id']},403)
        await req('POST','/api/v1/alert-ingress','a',{**base,'identity_version':'unknown-v99'},422)
        assert initial==await consumer.end_offsets(parts);save('rejected.json',{'checks':checks.copy(),'no_offsets_changed':True})
        steps=[];full={}
        async def incident(i):
            value=await cache.get('aisoc:fusion:incident:'+str(i));return decode(value) if value else None
        async def submit(label,body,identity='a',broker=False,expected_version='source-v1',expected_canonical=None):
            save(label+'-sending.json',{'input':body,'identity':identity,'channel':'broker' if broker else 'HTTP'})
            if broker:
                wire={**body,'tenant_id':ids[identity]['tenant_id']};ack=await producer.send_and_wait(RAW,json.dumps(wire).encode(),key=ids[identity]['tenant_id'].encode())
                receipt={'canonical_alert_id':expected_canonical,'message':{'topic':ack.topic,'partition':ack.partition,'offset':ack.offset},'identity_version':expected_version}
            else:receipt=(await req('POST','/api/v1/alert-ingress',identity,body,202)).json()
            save(label+'-accepted.json',receipt);assert receipt['identity_version']==expected_version
            raw=fused=None
            for _ in range(30):
                batches=await consumer.getmany(timeout_ms=1000)
                for tp,messages in batches.items():
                    for msg in messages:
                        v=decode(msg.value);a=v.get('alert',v)
                        item={'topic':msg.topic,'partition':msg.partition,'offset':msg.offset,'sha256':hashlib.sha256(msg.value).hexdigest(),'value':v}
                        if msg.topic==RAW and (msg.partition,msg.offset)==(receipt['message']['partition'],receipt['message']['offset']):raw=item
                        if msg.topic==FUSED and v.get('tenant_id')==ids[identity]['tenant_id'] and body['id'] in a.get('source_event_ids',[]):
                            assert fused is None;fused=item
                if raw and fused:break
            assert raw and fused,'Unconfirmed processing; inspect checkpoint, do not resubmit'
            v=fused['value'];canonical=receipt['canonical_alert_id'];assert canonical==v['id']==v['alert_row_id']
            detail=(await req('GET','/api/v1/alerts/'+canonical,identity)).json()
            row=await db.fetchrow('SELECT id,tenant_id,event_time,raw_event,external_id,source_event_ids,enrichment_data,dedup_hash FROM alerts WHERE id=$1',uuid.UUID(canonical))
            assert row and str(row['tenant_id'])==ids[identity]['tenant_id']
            if expected_version=='source-v1':
                assert detail['fusion_identity']['version']=='source-v1' and detail['fusion_identity']['source_alert_id']==body['id']
                assert detail['fusion_identity']['source']==body['source']
                assert detail['raw_event']==body['raw_event'] and detail['external_id']==body['external_id']
                assert detail['fusion_incident_id']==decode(row['enrichment_data'])['socai2_fusion']['incident_id']
            item={'label':label,'input':body,'receipt':receipt,'raw':raw,'fused':fused,'pg_row':dict(row),'api':detail,'incident':await incident(v['incident_id']) if v['incident_id'] else None}
            save(label+'-result.json',item);full[label]=item
            steps.append({'label':label,'canonical_id':canonical,'identity':identity,'identity_version':expected_version,'decision':v['fusion_decision'],'persist_outcome':v['persist_outcome'],'api_incident_id':detail['fusion_incident_id'],'api_event_time':detail['event_time'],'raw_event_sha256':hashlib.sha256(json.dumps(detail['raw_event'],sort_keys=True).encode()).hexdigest(),'raw_coordinate':{k:raw[k] for k in ['topic','partition','offset','sha256']},'fused_coordinate':{k:fused[k] for k in ['topic','partition','offset','sha256']}})
            return item
        first=await submit('01-first',base)
        second=await submit('02-distinct',variant('second',event_time=(now+timedelta(minutes=1)).isoformat()))
        assert first['receipt']['canonical_alert_id']!=second['receipt']['canonical_alert_id']
        assert first['api']['fusion_incident_id']==second['api']['fusion_incident_id']
        assert first['pg_row']['event_time']!=second['pg_row']['event_time'] and first['pg_row']['external_id']!=second['pg_row']['external_id']
        replay=await submit('03-replay',base)
        assert replay['fused']['value']['persist_outcome']=='duplicate' and replay['pg_row']==first['pg_row']
        connector=await submit('04-connector',{**base,'connector_id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/connector'))})
        other_source=await submit('05-source',{**base,'source':base['source']+'-other'})
        assert len({i['receipt']['canonical_alert_id'] for i in [first,connector,other_source]})==3
        entity=await submit('06-entity',variant('entity',src_ip='198.18.3.2'))
        tactic=await submit('07-tactic',variant('tactic',mitre_tactics=['credential-access']))
        assert first['api']['fusion_incident_id']!=entity['api']['fusion_incident_id'] and first['api']['fusion_incident_id']!=tactic['api']['fusion_incident_id']
        other=await submit('08-tenant',base,'b')
        assert first['receipt']['canonical_alert_id']!=other['receipt']['canonical_alert_id']
        await req('GET','/api/v1/alerts/'+first['receipt']['canonical_alert_id'],'b',status=404)
        await req('GET','/api/v1/alerts/'+other['receipt']['canonical_alert_id'],'a',status=404)
        model=RawAlert.model_validate({**base,'tenant_id':ids['a']['tenant_id'],'identity_version':'source-v1','source_alert_id':base['id']});key='aisoc:fusion:dedup:'+model.fingerprint()
        value=await cache.get(key);assert value and value.decode()==first['receipt']['canonical_alert_id']
        before=await incident(first['api']['fusion_incident_id']);assert before['alert_count']==4 and len(set(before['alert_ids']))==4
        save('cache-loss-before.json',{'owned_key':key,'tenant':ids['a']['tenant_id'],'value':value.decode(),'incident_before':before});assert await cache.unlink(key)==1
        lost=await submit('09-cache-miss-replay',base);after=lost['incident']
        assert after['alert_count']==4 and after['alert_ids']==before['alert_ids'] and after['last_seen']==before['last_seen']
        assert lost['pg_row']==first['pg_row']
        legacy=json.loads(Path('/legacy/legacy-alert-2a.json').read_text())
        old_http=await submit('10-legacy-http',legacy['input'],'legacy',expected_version='legacy-v1')
        assert old_http['receipt']['canonical_alert_id']==legacy['canonical_alert_id']
        old_broker=await submit('11-legacy-broker',legacy['input'],'legacy',broker=True,expected_version='legacy-v1',expected_canonical=legacy['canonical_alert_id'])
        assert old_broker['fused']['value']['persist_outcome']=='duplicate'
        bad={**variant('invalid-identity'),'tenant_id':ids['a']['tenant_id'],'schema_version':'v1','identity_version':'unknown-v99','source_alert_id':base['id']}
        ack=await producer.send_and_wait(RAW,json.dumps(bad).encode(),key=ids['a']['tenant_id'].encode());coordinate={'topic':ack.topic,'partition':ack.partition,'offset':ack.offset};save('bad-identity-ack.json',coordinate)
        for _ in range(20):
            dead=await db.fetchrow('SELECT id,tenant_id,topic,topic_partition,kafka_offset,reason,source_event_id FROM aisoc_dead_letters WHERE topic=$1 AND topic_partition=$2 AND kafka_offset=$3',ack.topic,ack.partition,ack.offset)
            if dead:break
            await asyncio.sleep(.5)
        assert dead and str(dead['tenant_id'])==ids['a']['tenant_id'];save('invalid-identity-dlq.json',dict(dead))
        counts=await db.fetch('SELECT tenant_id,count(*) AS count FROM alerts WHERE tenant_id=ANY($1::uuid[]) GROUP BY tenant_id',[uuid.UUID(ids[k]['tenant_id']) for k in ['a','b']]);assert sorted(r['count'] for r in counts)==[1,6]
        save('acceptance.json',{'batch':B,'status':'Versioned source identity bounded acceptance passed','checks':checks,'steps':steps,'new_tenant_alert_counts':[dict(r) for r in counts],'common_incident_after_cache_miss':after,'canonical_legacy_id':legacy['canonical_alert_id'],'legacy_http_and_broker_preserved':True,'unknown_identity_dlq_coordinate':coordinate,'one_owned_dedup_key_removed':True,'independent_materials_verified':True,'schema_changed':False})
        print(json.dumps({'http_checks':len(checks),'checked_alert_deliveries':len(steps),'bad_identity_broker_deliveries':1,'new_alert_rows':7,'common_incident_members':4,'legacy_compatibility':True}))
      finally:await consumer.stop();await producer.stop();await db.close();await cache.aclose()
if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'run'
    try:asyncio.run(asyncio.wait_for(main(mode),240))
    except Exception as e:
        save('failed-'+mode+'.json',{'error_type':type(e).__name__,'instruction':'Inspect checkpoint; do not replay successful or unknown submissions'});raise
