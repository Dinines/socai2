"""Four bounded real worker messages; explicit offset0 baseline and shadow DB policy."""
import asyncio,contextlib,hashlib,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'/app')
from aiokafka import AIOKafkaConsumer,AIOKafkaProducer,TopicPartition,OffsetAndMetadata
from app.core.kafka_security import kafka_client_kwargs
from app.investigator import ledger
from app.workers.business_context import BusinessContextApplier
from app.workers import fused_alert_consumer as module
E=Path('/evidence');TOPIC=os.getenv('SOCAI2_PROBE_TOPIC','socai2.test.3a-model-triage-20261020');GROUP=TOPIC+'.worker'
assert TOPIC in {'socai2.test.3a-model-triage-20261020','socai2.test.3a-model-blind-20261020'}
def save(n,x):
    with (E/n).open('x') as f:json.dump(x,f,indent=2,default=str)
async def main(mode):
    save('broker-'+mode+'-started.json',{'at':datetime.now(timezone.utc)})
    bootstrap=os.environ['KAFKA_BOOTSTRAP_SERVERS'];kw=kafka_client_kwargs();tp=TopicPartition(TOPIC,0)
    observer=AIOKafkaConsumer(bootstrap_servers=bootstrap,**kw,enable_auto_commit=False,group_id=GROUP)
    await observer.start();module._COMMIT_WINDOW_SECONDS=0
    inputs=json.loads((E/'setup-acceptance.json').read_text())['inputs'];total=len(inputs);results={};coordinates=[]
    from app.agents.auto_triage_agent import _build_alert_context
    fixture=json.loads(Path('/fixture.json').read_text())
    if mode=='run':
        projection={}
        for label,value in inputs.items():
            context=_build_alert_context(module.build_state(value),nonce='preflight-only')
            summary=fixture['samples'][label]['raw_event']['evidence_summary']
            assert summary in context,(label,'Fixture evidence summary omitted from actual prompt projection')
            projection[label]={'evidence_summary_present':True,'context_sha256':hashlib.sha256(context.encode()).hexdigest(),'context_chars':len(context)}
        save('prompt-preflight.json',projection)
    class ObservedWorker(module.FusedAlertTriageWorker):
        async def _record(self,state,**fields):
            label=self.label
            save(label+'-before-persist.json',{'run_id':str(state.run_id),'tenant_id':str(state.tenant_id),'raw_alert':state.raw_alert,'summary':state.alert_summary,'verdict':state.verdict,'confidence':state.confidence,'findings':state.findings,'basis':state.confidence_basis,'exchanges':state.llm_exchanges,'cost':fields['cost'].to_dict() if hasattr(fields['cost'],'to_dict') else module._cost_payload(fields['cost'],fields['tokens']),'tokens':fields['tokens'],'tier':fields['tier'],'model_used':state.model_used})
            await super()._record(state,**fields)
        async def triage(self,message):
            label=message['test_label'];self.label=label
            assert label not in results,'Unexpected replay: stop before another model call'
            original=os.environ.get('OPENAI_BASE_URL')
            if label=='model_failure':os.environ['OPENAI_BASE_URL']='http://127.0.0.1:9/v1'
            save(label+'-worker-entered.json',{'model_destination':'closed_local_port' if label=='model_failure' else 'existing_gateway','resident_worker_enabled':module.worker_enabled()})
            try:result=await super().triage(message)
            finally:
                if original is None:os.environ.pop('OPENAI_BASE_URL',None)
                else:os.environ['OPENAI_BASE_URL']=original
            assert result['shadow'],'Configured test tenant must remain in shadow'
            results[label]=result;save(label+'-worker-result.json',result);return result
    worker=ObservedWorker(bootstrap_servers=bootstrap,topic=TOPIC,group_id=GROUP,dlq_topic=TOPIC+'.dlq',max_attempts=1,business_context=BusinessContextApplier())
    from app.agents import auto_triage_agent as agent_module
    original_invoke=agent_module.safe_ainvoke
    async def observe_invoke(llm,messages,*args,**kwargs):
        # Observe the real return value; never supply a response or change usage.
        value=await original_invoke(llm,messages,*args,**kwargs)
        metadata=getattr(value,'response_metadata',{}) or {}
        headers=metadata.get('headers',{}) or {}
        save(worker.label+'-model-response-metadata.json',{'usage_metadata':getattr(value,'usage_metadata',None),'token_usage':metadata.get('token_usage'),'model_name':metadata.get('model_name'),'finish_reason':metadata.get('finish_reason'),'headers':{k:v for k,v in headers.items() if k.lower() in ['x-litellm-call-id','x-litellm-model-id','x-litellm-model-api-base','x-litellm-response-cost','x-litellm-response-cost-original']}})
        return value
    agent_module.safe_ainvoke=observe_invoke
    task=None;producer=None
    try:
        if mode=='run':
            assert (await observer.end_offsets([tp]))[tp]==0 and await observer.committed(tp) is None
            observer.assign([tp]);await observer.commit({tp:OffsetAndMetadata(0,'socai2-explicit-empty-topic-baseline')})
            save('group-baseline.json',{'committed':await observer.committed(tp),'topic_empty':True})
        else:assert mode=='restart' and await observer.committed(tp)==total
        task=asyncio.create_task(worker.start())
        for _ in range(100):
            if task.done():await task
            if worker._consumer and worker._consumer.assignment():break
            await asyncio.sleep(.1)
        else:raise AssertionError('No assignment')
        if mode=='restart':
            # No re-submission: query assigned position and wait a bounded interval.
            assert await worker._consumer.position(tp)==total
            await asyncio.sleep(2);assert not results and await observer.committed(tp)==total
            save('broker-restart-acceptance.json',{'committed':total,'assigned_position':total,'new_inputs':0,'processed':0,'resident_worker_enabled':module.worker_enabled()});return
        producer=AIOKafkaProducer(bootstrap_servers=bootstrap,**kw,value_serializer=lambda x:json.dumps(x).encode());await producer.start()
        for index,(label,value) in enumerate(inputs.items()):
            # A commit barrier before the next message keeps failure-endpoint
            # override local to the last sample, without concurrent env races.
            save(label+'-broker-sending.json',value);sent=await producer.send_and_wait(TOPIC,value=value)
            assert sent.offset==index;coordinate={'label':label,'partition':sent.partition,'offset':sent.offset};coordinates.append(coordinate);save(label+'-broker-ack.json',coordinate)
            for _ in range(240):
                if task.done():await task
                offset=await observer.committed(tp)
                if offset==index+1:break
                await asyncio.sleep(.25)
            else:raise AssertionError('Outcome unknown; inspect, never resubmit')
            assert label in results,'DLQ or missing durable result'
            save(label+'-committed.json',{'position':offset,'run_id':results[label]['run_id']})
        save('broker-acceptance.json',{'topic':TOPIC,'group':GROUP,'coordinates':coordinates,'results':results,'committed':total,'resident_worker_enabled':module.worker_enabled()})
    finally:
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):await task
            await worker.stop()
        if producer:await producer.stop()
        agent_module.safe_ainvoke=original_invoke
        await observer.stop();await ledger.close_pool()
if __name__=='__main__':asyncio.run(main(sys.argv[1]))
