"""Actual ingress→Fusion envelope→worker prompt/null score; one real model call."""
import asyncio,contextlib,hashlib,json,os,sys,uuid
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'/app')
import httpx
from aiokafka import AIOKafkaConsumer,TopicPartition
from app.core.kafka_security import kafka_client_kwargs
from app.investigator import ledger
from app.workers.fused_alert_consumer import FusedAlertTriageWorker,build_state,worker_enabled
from app.agents.auto_triage_agent import _build_alert_context
E=Path('/evidence');B='3a-risk-20261020'
def save(n,x):
    with (E/n).open('x') as f:json.dump(x,f,indent=2,default=str)
async def main(mode):
    save(mode+'-started.json',{'at':datetime.now(timezone.utc)})
    ids=json.loads(Path('/private/state.json').read_text())['identities'];checks=[]
    async with httpx.AsyncClient(base_url='http://api:8000',trust_env=False,timeout=25) as c:
      async def req(method,path,n='a',body=None,status=200):
        r=await c.request(method,path,headers={'Authorization':'Bearer '+ids[n]['key']} if n else {},json=body)
        checks.append({'method':method,'path':path,'identity':n,'status':r.status_code,'expected':status});(E/(mode+'-http-checks.json')).write_text(json.dumps(checks,indent=2));assert r.status_code==status,(r.status_code,r.text[:150]);return r.json()
      try:
        assert not worker_enabled()
        if mode=='after':
            fixture=json.loads(Path('/fixture.json').read_text());topic=os.environ['KAFKA_TOPIC_ALERTS_FUSED']
            consumer=AIOKafkaConsumer(topic,bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],**kafka_client_kwargs(),enable_auto_commit=False,group_id=None)
            await consumer.start()
            try:
                partitions=sorted(consumer.partitions_for_topic(topic) or []);assert partitions
                tps=[TopicPartition(topic,p) for p in partitions];consumer.unsubscribe();consumer.assign(tps)
                starts=await consumer.end_offsets(tps)
                for tp,offset in starts.items():consumer.seek(tp,offset)
                save('fused-read-starts.json',[{'partition':tp.partition,'offset':offset} for tp,offset in starts.items()])
                pending={};alerts={};fused={};coords={}
                for index,(label,case) in enumerate(fixture['cases'].items()):
                    body={**fixture['alert'],**case['extra'],'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/sample-'+str(index))),'source':'socai2-'+B,'source_event_ids':[str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/event-'+str(index)))],'event_time':datetime.now(timezone.utc).isoformat(),'tags':[B]}
                    save(label+'-sending.json',body);ack=await req('POST','/api/v1/alert-ingress',body=body,status=202);save(label+'-ack.json',ack);pending[ack['canonical_alert_id']]=label
                    for _ in range(80):
                        r=await c.get('/api/v1/alerts/'+ack['canonical_alert_id'],headers={'Authorization':'Bearer '+ids['a']['key']})
                        if r.status_code==200:break
                        assert r.status_code==404;await asyncio.sleep(.25)
                    else:raise AssertionError('Accepted outcome unknown; inspect, no resubmission')
                    alerts[label]=r.json();save(label+'-stored-alert.json',alerts[label])
                for _ in range(100):
                    records=await consumer.getmany(timeout_ms=200,max_records=50)
                    for tp,messages in records.items():
                        for record in messages:
                            envelope=json.loads(record.value);label=pending.get(str(envelope.get('alert_row_id')))
                            if label:
                                assert envelope['tenant_id']==ids['a']['tenant_id']
                                assert label not in fused,'Unexpected second delivery in contract probe'
                                fused[label]=envelope;coords[label]={'topic':topic,'partition':record.partition,'offset':record.offset,'sha256':hashlib.sha256(record.value).hexdigest()};save(label+'-fused-envelope.json',envelope)
                    if len(fused)==4:break
                assert len(fused)==4,'Missing fused outcome; no resubmission'
            finally:
                with contextlib.suppress(asyncio.CancelledError):await consumer.stop()
            projection={}
            for label,case in fixture['cases'].items():
                envelope=fused[label];assert envelope['alert']['risk_score']==case['expected']
                state=build_state(envelope);assert state.raw_alert['risk_score']==case['expected']
                context=_build_alert_context(state,nonce='contract-preflight')
                text='not provided or unknown (not zero)' if case['expected'] is None else f"{case['expected']:g} (publisher supplied"
                assert 'Provided alert risk score: '+text in context and 'Risk Score (vendor)' not in context
                upstream=next(x for x in alerts[label]['confidence_rationale'] if x['factor']=='upstream_risk')
                assert ('not supplied' in upstream['value']) if case['expected'] is None else upstream['value']==f"{case['expected']:.2f}"
                projection[label]={'value':state.raw_alert['risk_score'],'context':context,'upstream_factor':upstream}
            save('presence-matrix.json',{'projections':projection,'coordinates':coords,'consumer_group':None,'commits':False,'submitted_alerts':4})
            # Probe invalid nonfinite payload before any publish; sample has new
            # unused UUID so it cannot be confused with an accepted input.
            invalid={**fixture['alert'],'id':str(uuid.uuid5(uuid.NAMESPACE_URL,B+'/invalid')),'source':'socai2-'+B,'source_event_ids':['invalid-nonfinite'],'event_time':datetime.now(timezone.utc).isoformat(),'risk_score':'NaN'}
            await req('POST','/api/v1/alert-ingress',body=invalid,status=422)
            from app.agents import auto_triage_agent as agent_module
            original=agent_module.safe_ainvoke
            async def observe(llm,messages,*a,**kw):
                result=await original(llm,messages,*a,**kw);meta=result.response_metadata or {};headers=meta.get('headers',{}) or {}
                save('model-metadata.json',{'usage_metadata':result.usage_metadata,'finish_reason':meta.get('finish_reason'),'route':headers.get('x-litellm-model-api-base'),'model':meta.get('model_name')});return result
            agent_module.safe_ainvoke=observe
            class Observed(FusedAlertTriageWorker):
                async def _record(self,state,**kw):
                    save('model-before-persist.json',{'run_id':str(state.run_id),'raw_alert':state.raw_alert,'exchanges':state.llm_exchanges,'verdict':state.verdict,'tokens':kw['tokens'],'tier':kw['tier'],'findings':state.findings,'model_used':state.model_used})
                    await super()._record(state,**kw)
            try:
                save('model-call-started.json',{'envelope_coordinate':coords['missing'],'source':'actual Fusion envelope, not reconstructed fixture'})
                result=await Observed(bootstrap_servers='').triage(fused['missing'])
            finally:agent_module.safe_ainvoke=original
            assert result['shadow'] and result['tier']=='llm' and not result['response_dispatched'] and not result['approvals_raised'] and result['source_writeback'] is None
            pre=json.loads((E/'model-before-persist.json').read_text());assert pre['raw_alert']['risk_score'] is None
            assert 'Provided alert risk score: not provided or unknown (not zero)' in pre['exchanges'][0]['prompt']
            save('model-worker-result.json',result)
            save('after-acceptance.json',{'alerts':alerts,'fused_coordinates':coords,'result':result,'checks':checks});return
        previous=json.loads((E/'after-acceptance.json').read_text());rid=previous['result']['run_id'];base='/api/v1/investigations/'+rid
        run=await req('GET',base);events=await req('GET',base+'/events');artifacts=await req('GET',base+'/artifacts')
        assert run['status']=='completed' and run['event_count']==2 and len(artifacts)==2
        assert {x['kind'] for x in events['items']}=={'triage_verdict','llm_call'}
        blobs=[await req('GET',base+'/artifacts/'+x['id']) for x in artifacts]
        for label,old in previous['alerts'].items():
            current=await req('GET','/api/v1/alerts/'+old['id'])
            for k in ['raw_event','severity','status','disposition','resolved_at','priority']:assert current.get(k)==old.get(k)
        if mode=='verify':
            await req('GET',base,'b',status=404);await req('GET',base,'denied',status=403);await req('GET',base,None,status=401)
        if mode=='restart':
            old=json.loads((E/'verify-acceptance.json').read_text());assert run==old['run'] and events==old['events'] and artifacts==old['artifacts'] and blobs==old['artifact_details']
        save(mode+'-acceptance.json',{'run':run,'events':events,'artifacts':artifacts,'artifact_details':blobs,'checks':checks,'model_invoked':False})
      finally:await ledger.close_pool()
if __name__=='__main__':asyncio.run(main(sys.argv[1]))
