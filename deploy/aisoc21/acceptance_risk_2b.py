"""Checkpointed before/after HTTP risk replay probe; no model/vendor calls."""
import asyncio,hashlib,json,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,'/app')
import asyncpg,httpx,redis.asyncio as redis
from aiokafka import AIOKafkaConsumer
from aiokafka.structs import TopicPartition
from app.core.kafka_security import kafka_client_kwargs
from app.schemas.fusion_alert import RawAlert
E=Path(os.getenv('RISK_PROBE_EVIDENCE','/evidence'));B='2b-risk-20261020'
def save(n,v):
    with (E/n).open('x') as f:json.dump(v,f,indent=2,default=str)
async def main(mode):
    assert mode in ['before','after']
    save(mode+'-started.json',{'at':datetime.now(timezone.utc)})
    ids=json.loads(Path('/private/state.json').read_text())['identities'];tenant=ids['a']['tenant_id']
    cache=redis.from_url(os.environ['REDIS_URL']);db=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'))
    consumer=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=None,enable_auto_commit=False,**kafka_client_kwargs());await consumer.start()
    parts=[TopicPartition('socai2.alerts.fused',i) for i in range(3)];consumer.assign(parts);await consumer.seek_to_end(*parts)
    body={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/'+mode)),'source':'socai2-'+B,'source_event_ids':[B+'-'+mode+'-event'],'title':'Synthetic risk replay '+mode,'severity':'high','username':'socai2-risk-'+mode,'risk_score':0.5,'mitre_tactics':['execution'],'mitre_techniques':['T1059.001'],'event_time':datetime.now(timezone.utc).isoformat(),'tags':[B],'raw_event':{'batch':B,'mode':mode,'synthetic':True}}
    rkey='aisoc:fusion:rba:entity:'+tenant+':user:'+body['username'];checks=[]
    async with httpx.AsyncClient(base_url='http://api:8000',timeout=25,trust_env=False) as client:
      async def submit(label,identity='a'):
        save(mode+'-'+label+'-sending.json',{'input':body,'identity':identity})
        r=await client.post('/api/v1/alert-ingress',headers={'Authorization':'Bearer '+ids[identity]['key']},json=body)
        save(mode+'-'+label+'-http.json',{'status':r.status_code,'body':r.json()});assert r.status_code==202,r.status_code
        ack=r.json();save(mode+'-'+label+'-ack.json',ack)
        for _ in range(30):
            found=None
            for tp,messages in (await consumer.getmany(timeout_ms=1000)).items():
                for msg in messages:
                    v=json.loads(msg.value)
                    if v.get('tenant_id')==ids[identity]['tenant_id'] and v.get('id')==ack['canonical_alert_id']:
                        assert found is None;found={'topic':msg.topic,'partition':msg.partition,'offset':msg.offset,'sha256':hashlib.sha256(msg.value).hexdigest(),'value':v}
            if found:break
        else:raise RuntimeError('No confirmed fused record; do not replay unknown submission')
        detail=await client.get('/api/v1/alerts/'+ack['canonical_alert_id'],headers={'Authorization':'Bearer '+ids[identity]['key']});assert detail.status_code==200
        row=await db.fetchrow('SELECT id,tenant_id,event_time,raw_event,external_id,source_event_ids,enrichment_data,dedup_hash FROM alerts WHERE id=$1',uuid.UUID(ack['canonical_alert_id']))
        key=rkey if identity=='a' else rkey.replace(tenant,ids[identity]['tenant_id'])
        risk={k.decode():v.decode() for k,v in (await cache.hgetall(key)).items()};assert risk
        item={'receipt':ack,'fused':found,'api':detail.json(),'pg':dict(row),'risk':risk,'ttl':await cache.ttl(key)};save(mode+'-'+label+'-result.json',item);checks.append(item);return item
      try:
        first=await submit('first');assert int(first['risk']['alert_count'])==1 and float(first['risk']['score'])==30
        warm=await submit('warm');assert warm['risk']==first['risk'] and warm['pg']==first['pg']
        model=RawAlert.model_validate({**body,'tenant_id':tenant,'identity_version':'source-v1','source_alert_id':body['id']});dkey='aisoc:fusion:dedup:'+model.fingerprint()
        assert (await cache.get(dkey)).decode()==first['receipt']['canonical_alert_id'];save(mode+'-owned-key-removal.json',{'key':dkey,'value':first['receipt']['canonical_alert_id']});assert await cache.unlink(dkey)==1
        cold=await submit('cold');assert cold['pg']==first['pg'] and cold['api']['fusion_incident_id']==first['api']['fusion_incident_id']
        if mode=='before':assert int(cold['risk']['alert_count'])==2 and float(cold['risk']['score'])>59
        else:
            assert cold['risk']==first['risk'],'Replay changed risk'
            other=await submit('tenant-b','b');assert int(other['risk']['alert_count'])==1
            deny=await client.get('/api/v1/alerts/'+first['receipt']['canonical_alert_id'],headers={'Authorization':'Bearer '+ids['b']['key']});assert deny.status_code==404
        save(mode+'-acceptance.json',{'mode':mode,'inputs':len(checks),'first_score':first['risk']['score'],'cold_score':cold['risk']['score'],'first_count':first['risk']['alert_count'],'cold_count':cold['risk']['alert_count'],'material_unchanged':True,'canonical_id':first['receipt']['canonical_alert_id'],'source_uuid':body['id'],'tenant':tenant,'username':body['username'],'risk_key':rkey,'incident_id':first['api']['fusion_incident_id'],'expected_defect_reproduced':mode=='before','risk_replay_unchanged':cold['risk']==first['risk']})
        print(json.dumps({'mode':mode,'submissions':len(checks),'first_score':first['risk']['score'],'cold_score':cold['risk']['score'],'counts':[first['risk']['alert_count'],cold['risk']['alert_count']]}))
      finally:await consumer.stop();await cache.aclose();await db.close()
if __name__=='__main__':asyncio.run(asyncio.wait_for(main(sys.argv[1]),160))
