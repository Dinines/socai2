"""Bounded real SSL Kafka worker, private test topic/group; no resident enable."""
import asyncio,contextlib,hashlib,json,os,sys,copy
from pathlib import Path
sys.path.insert(0,'/app')
from aiokafka import AIOKafkaProducer,AIOKafkaConsumer,TopicPartition
from app.investigator import ledger
from app.core.kafka_security import kafka_client_kwargs
from app.workers.business_context import BusinessContextApplier
from app.workers import fused_alert_consumer as module
E=Path('/evidence');TOPIC='socai2.test.3a-suppression-20261020';GROUP=TOPIC+'.worker'
async def main():
    assert not (E/'broker-started.json').exists(),'Inspect existing broker attempt; no input replay'
    (E/'broker-started.json').write_text(json.dumps({'topic':TOPIC,'group':GROUP}))
    value=json.loads((E/'before-acceptance.json').read_text())['inputs']['a'];bootstrap=os.environ['KAFKA_BOOTSTRAP_SERVERS']
    kw=kafka_client_kwargs();module._COMMIT_WINDOW_SECONDS=0
    producer=AIOKafkaProducer(bootstrap_servers=bootstrap,**kw,value_serializer=lambda x:json.dumps(x).encode())
    observer=AIOKafkaConsumer(bootstrap_servers=bootstrap,**kw,enable_auto_commit=False,group_id=GROUP)
    await producer.start();await observer.start();tp=TopicPartition(TOPIC,0);phases=[]
    def worker():return module.FusedAlertTriageWorker(bootstrap_servers=bootstrap,topic=TOPIC,group_id=GROUP,dlq_topic=TOPIC+'.dlq',max_attempts=1,business_context=BusinessContextApplier())
    async def launch(w):
        task=asyncio.create_task(w.start())
        for _ in range(100):
            if task.done():return w,task
            if w._consumer and w._consumer.assignment():return w,task
            await asyncio.sleep(.1)
        raise AssertionError('Test subscription not assigned')
    async def committed(target):
        for _ in range(100):
            offset=await observer.committed(tp)
            if offset==target:return offset
            await asyncio.sleep(.1)
        raise AssertionError('Committed position not reached')
    async def halt(w,t):
        t.cancel()
        with contextlib.suppress(asyncio.CancelledError):await t
        await w.stop()
    try:
        w,t=await launch(worker());sent=await producer.send_and_wait(TOPIC,value=value);assert sent.offset==0
        await committed(1);await halt(w,t);phases.append({'phase':'durable_receipt','input_offset':0,'committed':1})
        # Same group already has a baseline commit, so crash/restart cannot
        # skip this failed input via auto_offset_reset=latest on a fresh group.
        original=ledger.get_pool
        async def no_pool():return None
        ledger.get_pool=no_pool
        w=worker();w._ensure_producer=no_pool
        try:
            w,t=await launch(w);sent=await producer.send_and_wait(TOPIC,value=value);assert sent.offset==1
            try:await asyncio.wait_for(t,15)
            except ledger.LedgerPersistError as error:failure=str(error)
            else:raise AssertionError('Undurable input did not stop worker')
            assert await observer.committed(tp)==1
            await w.stop()
        finally:ledger.get_pool=original
        phases.append({'phase':'no_receipt_and_no_dlq','input_offset':1,'committed':1,'error':failure,'stopped':True})
        w,t=await launch(worker());await committed(2);await halt(w,t)
        phases.append({'phase':'recovery_without_resubmission','input_offset':1,'committed':2})
        # Same-key changed material is not overwritten; real DLQ broker ack
        # is required before advancing past this poison input.
        w,t=await launch(worker());bad=copy.deepcopy(value);bad['alert']['title']='3A same-key conflict'
        sent=await producer.send_and_wait(TOPIC,value=bad);assert sent.offset==2
        await committed(3);await halt(w,t)
        dlq=AIOKafkaConsumer(bootstrap_servers=bootstrap,**kw,enable_auto_commit=False,group_id=None)
        await dlq.start()
        try:
            dtp=TopicPartition(TOPIC+'.dlq',0);dlq.assign([dtp]);dlq.seek(dtp,0)
            message=await asyncio.wait_for(dlq.getone(),10);body=json.loads(message.value)
            assert body['failure_stage']=='persist' and body['alert_id']==value['id']
            phases.append({'phase':'confirmed_dlq','input_offset':2,'committed':3,'dlq_offset':message.offset,'dlq_sha256':hashlib.sha256(message.value).hexdigest(),'failure_stage':body['failure_stage']})
        finally:await dlq.stop()
        (E/'broker-acceptance.json').write_text(json.dumps({'topic':TOPIC,'group':GROUP,'phases':phases,'new_input_messages':3,'dlq_messages':1,'resident_worker_enabled':module.worker_enabled()},indent=2))
        assert not module.worker_enabled()
        print(json.dumps({'bounded_worker_phases':len(phases),'input_messages':3,'committed':3,'resident_worker_enabled':False}))
    finally:
        await producer.stop();await observer.stop();await ledger.close_pool()
if __name__=='__main__':asyncio.run(main())
