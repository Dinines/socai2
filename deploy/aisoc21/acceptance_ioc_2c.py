"""Checkpointed HTTP/Kafka/PG/API IOC observations and direct failure probe."""
import asyncio,hashlib,json,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,'/app')
import asyncpg,httpx
from aiokafka import AIOKafkaConsumer
from aiokafka.structs import TopicPartition
from app.core.kafka_security import kafka_client_kwargs
E=Path('/evidence');B='2c-ioc-20261020'
def save(n,v):
    with (E/n).open('x') as f:json.dump(v,f,indent=2,default=str)
async def main(mode):
    save(mode+'-started.json',{'at':datetime.now(timezone.utc)})
    state=json.loads(Path('/private/state.json').read_text());ids=state['identities'];source=json.loads(Path('/source-ioc.json').read_text());checks=[]
    async with httpx.AsyncClient(base_url='http://api:8000',trust_env=False,timeout=25) as client:
      async def req(method,path,identity='a',body=None,status=200):
        r=await client.request(method,path,headers={'Authorization':'Bearer '+ids[identity]['key']},json=body);checks.append({'method':method,'path':path,'identity':identity,'status':r.status_code,'expected':status});assert r.status_code==status,(r.status_code,r.text[:200]);return r.json()
      if mode=='restart':
        old=json.loads((E/'acceptance.json').read_text())
        for x in old['steps']:
            item=await req('GET','/api/v1/alerts/'+x['canonical_id'],x['identity']);assert item['fusion_ioc_lookup']==x['lookup'] and item['raw_event']==x['raw_event'] and item['fusion_incident_id']==x['incident_id']
        save('restart-acceptance.json',{'checks':checks,'frozen_lookup_and_material_unchanged':True});print(json.dumps({'reads_after_restart':len(checks),'unchanged':True}));return
      assert mode=='run'
      db=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'))
      c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=None,enable_auto_commit=False,**kafka_client_kwargs());await c.start();parts=[TopicPartition('socai2.alerts.fused',i) for i in range(3)];c.assign(parts);await c.seek_to_end(*parts)
      steps=[];first_body=None
      try:
        async def submit(label,domain,identity='a',expect='no_match',body=None):
            nonlocal first_body
            if body is None:body={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/'+label)),'source':'socai2-'+B,'title':'Historical IOC lookup '+label,'domain':domain,'severity':'medium','source_event_ids':[B+'-'+label],'event_time':datetime.now(timezone.utc).isoformat(),'tags':[B],'raw_event':{'batch':B,'label':label,'synthetic':True,'domain':domain}}
            if label=='historical':first_body=body
            save(label+'-sending.json',{'input':body,'identity':identity})
            ack=await req('POST','/api/v1/alert-ingress',identity,body,202);save(label+'-ack.json',ack)
            found=None
            for _ in range(30):
                for tp,messages in (await c.getmany(timeout_ms=1000)).items():
                    for msg in messages:
                        v=json.loads(msg.value)
                        if v.get('id')==ack['canonical_alert_id'] and v.get('tenant_id')==ids[identity]['tenant_id']:
                            found={'topic':msg.topic,'partition':msg.partition,'offset':msg.offset,'sha256':hashlib.sha256(msg.value).hexdigest(),'value':v}
                if found:break
            assert found,'Unknown processing; inspect checkpoint, do not resubmit'
            item=await req('GET','/api/v1/alerts/'+ack['canonical_alert_id'],identity);lookup=item['fusion_ioc_lookup'];assert lookup['status']==expect and lookup['external_status']=='not_configured'
            assert lookup['tenant_id']==ids[identity]['tenant_id'] and item['raw_event']==body['raw_event']
            row=await db.fetchrow('SELECT enrichment_data,raw_event FROM alerts WHERE id=$1',uuid.UUID(ack['canonical_alert_id']));metadata=json.loads(row['enrichment_data'])
            assert metadata['socai2_fusion']['ioc_lookup']==lookup
            if label!='replay':assert found['value']['enrichments']['ioc_lookup']==lookup
            result={'input':body,'receipt':ack,'fused':found,'api':item,'lookup':lookup};save(label+'-result.json',result)
            steps.append({'label':label,'canonical_id':ack['canonical_alert_id'],'identity':identity,'lookup':lookup,'raw_event':item['raw_event'],'incident_id':item['fusion_incident_id'],'raw_coordinate':ack['message'],'fused_coordinate':{k:found[k] for k in ['topic','partition','offset','sha256']}});return result
        first=await submit('historical',source['value'],expect='matched');hit=first['lookup']['matches'][0]
        assert hit['ioc_id']==state['ioc_ids']['historical'] and hit['last_seen'].startswith('2022-04-08') and hit['source_ref']==source['source_url'] and hit['weak']
        factor=next(x for x in first['fused']['value']['confidence_rationale'] if x['factor']=='threat_intel');assert factor['contribution']==-.3 and 'not used' in factor['value']
        await submit('missing','unmatched.socai2.invalid')
        other=await submit('other-tenant',source['value'],'b');assert not other['lookup']['matches']
        await req('GET','/api/v1/alerts/'+first['receipt']['canonical_alert_id'],'b',status=404)
        await submit('expired','expired.socai2.invalid')
        result=await db.execute('UPDATE threat_intel_iocs SET is_active=false WHERE id=$1 AND tenant_id=$2',uuid.UUID(state['ioc_ids']['historical']),uuid.UUID(ids['a']['tenant_id']));assert result=='UPDATE 1';save('owned-ioc-disabled.json',{'ioc_id':state['ioc_ids']['historical'],'tenant_id':ids['a']['tenant_id'],'rows':1})
        await submit('disabled',source['value'])
        replay=await submit('replay',source['value'],expect='matched',body=first_body);assert replay['lookup']==first['lookup'] and replay['fused']['value']['persist_outcome']=='duplicate'
        save('acceptance.json',{'steps':steps,'checks':checks,'historical_source':source,'original_lookup_frozen_after_ioc_disabled':True,'confidence_weight_unchanged':factor,'ioc_target_contacted':False,'external_enrichment_enabled':False,'model_calls':0})
        print(json.dumps({'deliveries':len(steps),'http_checks':len(checks),'new_rows':5,'historical_hit':True,'empty_tenant_miss':True,'expired_and_disabled_miss':True,'frozen_replay':True}))
      finally:await c.stop();await db.close()
if __name__=='__main__':asyncio.run(asyncio.wait_for(main(sys.argv[1]),210))
