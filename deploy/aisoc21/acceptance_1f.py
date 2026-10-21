#!/usr/bin/env python3
"""Synthetic HTTP -> Kafka -> real Fusion -> PG -> HTTP evidence.

Run as a disposable API-image client on socai2's network, with runtime-only
Fusion env and CA. Test identities arrive on stdin, never command arguments.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import ssl
import sys
import uuid

sys.path.insert(0, '/app')

import asyncpg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import TopicPartition
import httpx

from app.core.kafka_security import kafka_client_kwargs

BATCH = '1f-20261020'
RAW, FUSED = 'socai2.alerts.raw', 'socai2.alerts.fused'
RESULT = Path('/output/acceptance.json')


def safe_row(row):
    if row is None:return None
    return {k:(str(v) if isinstance(v,(uuid.UUID,datetime)) else v) for k,v in dict(row).items()}


async def main(identities):
    evidence = {'batch':BATCH,'level':'Real HTTP, runtime PG role, Kafka and Fusion; synthetic inputs; no model/vendor',
                'http_checks':[], 'raw_messages':[], 'fused_messages':[]}
    RESULT.write_text(json.dumps({'batch':BATCH,'status':'started'})+'\n')
    transport = kafka_client_kwargs()
    consumer = AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                group_id=None, enable_auto_commit=False, **transport)
    await consumer.start()
    partitions = [TopicPartition(t,i) for t in (RAW,FUSED) for i in range(3)]
    consumer.assign(partitions)
    await consumer.seek_to_end(*partitions)
    starting = await consumer.end_offsets(partitions)
    producer = AIOKafkaProducer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                acks='all',enable_idempotence=True,**transport)
    await producer.start()
    db = await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'))
    try:
        evidence['postgres_runtime_transport'] = safe_row(await db.fetchrow(
            'SELECT current_user AS role, ssl, version, cipher FROM pg_stat_ssl WHERE pid=pg_backend_pid()'))
        assert evidence['postgres_runtime_transport']['role']=='aisoc_app' and evidence['postgres_runtime_transport']['ssl']
        async with httpx.AsyncClient(base_url='http://api:8000',timeout=35) as client:
            now=datetime.now(timezone.utc)
            def payload(label='a'):
                return {'id':str(uuid.uuid5(uuid.NAMESPACE_URL,'socai2/'+BATCH+'/'+label)),
                        'source':'socai2-migration-edr','title':'socai2 '+BATCH+' marked existing finding',
                        'description':'Synthetic existing alert for the migration baseline',
                        'severity':'high','hostname':'socai2-test-host','src_ip':'192.0.2.44',
                        'mitre_techniques':['T1059'],'event_time':now.isoformat(),
                        'source_event_ids':[BATCH+'-source-'+label],'external_id':BATCH+'-finding-'+label,
                        'connector_type':'migration-test','tags':[BATCH],
                        'raw_event':{'batch':BATCH,'occurrence':label,'synthetic':True}}
            async def request(method,path,identity=None,body=None,expected=None):
                headers={'Authorization':'Bearer '+identities[identity]['key']} if identity else {}
                response=await client.request(method,path,headers=headers,json=body)
                entry={'method':method,'path':path,'identity':identity,'status':response.status_code}
                evidence['http_checks'].append(entry)
                if expected is not None:
                    assert response.status_code==expected,(entry,response.text[:500])
                return response
            await request('POST','/api/v1/alert-ingress',body=payload(),expected=401)
            await request('POST','/api/v1/alert-ingress','readonly',payload(),403)
            await request('POST','/api/v1/alert-ingress','a',
                          {**payload(),'tenant_id':identities['b']['tenant_id']},403)
            await request('POST','/api/v1/alert-ingress','a',{**payload(),'schema_version':'v2'},422)
            await request('POST','/api/v1/alert-ingress','a',{**payload(),'source_event_ids':[]},422)
            await request('POST','/api/v1/alert-ingress','a',{**payload(),'unrecognised':1},422)
            rejected_end=await consumer.end_offsets(partitions)
            evidence['rejected_requests_did_not_publish']=starting==rejected_end
            assert evidence['rejected_requests_did_not_publish']
            async def fused_for(input_id):
                for _ in range(35):
                    batches=await consumer.getmany(timeout_ms=1000)
                    for tp,messages in batches.items():
                        for message in messages:
                            value=json.loads(message.value)
                            body=value.get('alert',value)
                            if BATCH not in body.get('tags',[]):continue
                            item={'topic':message.topic,'partition':message.partition,'offset':message.offset,
                                  'sha256':hashlib.sha256(message.value).hexdigest(),'value':value}
                            evidence['raw_messages' if message.topic==RAW else 'fused_messages'].append(item)
                    for item in evidence['fused_messages']:
                        if input_id in item['value'].get('alert',{}).get('source_event_ids',[]):return item
                raise RuntimeError('Timed out waiting for marked fused message')
            original=payload()
            accepted=(await request('POST','/api/v1/alert-ingress','a',original,202)).json()
            evidence['accepted']=accepted;evidence['input']=original
            first=await fused_for(original['id'])
            canonical=accepted['canonical_alert_id']
            assert first['value']['id']==canonical==first['value']['alert_row_id']
            assert first['value']['persist_outcome']=='inserted'
            assert first['value']['tenant_id']==identities['a']['tenant_id']
            detail=(await request('GET',accepted['result_url'],'a',expected=200)).json()
            assert detail['id']==canonical and detail['tenant_id']==identities['a']['tenant_id']
            assert detail['raw_event']['batch']==BATCH
            evidence['api_result']=detail
            await request('GET',accepted['result_url'],'b',expected=404)
            # Repeat the same input exactly: one canonical row, another decision.
            before_count=len(evidence['fused_messages'])
            repeat=(await request('POST','/api/v1/alert-ingress','a',original,202)).json()
            for _ in range(25):
                batches=await consumer.getmany(timeout_ms=1000)
                for tp,messages in batches.items():
                    for m in messages:
                        v=json.loads(m.value);body=v.get('alert',v)
                        if BATCH in body.get('tags',[]):
                            evidence['raw_messages' if m.topic==RAW else 'fused_messages'].append(
                                {'topic':m.topic,'partition':m.partition,'offset':m.offset,
                                 'sha256':hashlib.sha256(m.value).hexdigest(),'value':v})
                if len(evidence['fused_messages'])>before_count:break
            duplicate=evidence['fused_messages'][-1]['value']
            assert repeat['canonical_alert_id']==canonical and duplicate['fusion_decision']=='duplicate'
            assert duplicate['persist_outcome']=='duplicate'
            evidence['same_input_repeat']={'receipt':repeat,'decision':duplicate['fusion_decision']}
            distinct={**payload('a-second'),'event_time':(now+timedelta(seconds=60)).isoformat()}
            occurrence=(await request('POST','/api/v1/alert-ingress','a',distinct,202)).json()
            folded=await fused_for(distinct['id'])
            row=await db.fetchrow('SELECT id,tenant_id,source_event_ids,event_time,raw_event FROM alerts WHERE id=$1',uuid.UUID(canonical))
            sources=json.loads(row['source_event_ids'])
            assert distinct['source_event_ids'][0] in sources and distinct['id'] in sources
            evidence['distinct_occurrence']={'input':distinct,'receipt':occurrence,
                'decision':folded['value']['fusion_decision'],'same_canonical_id':occurrence['canonical_alert_id']==canonical,
                'new_source_ids_retained':True,'persistent_alert_row':safe_row(row),
                'limitation':'Original fingerprint excludes event time/finding ID; different occurrence folded to existing row. No independent occurrence guarantee.'}
            other=payload('b')
            other_accepted=(await request('POST','/api/v1/alert-ingress','b',other,202)).json()
            other_fused=await fused_for(other['id'])
            assert other_accepted['canonical_alert_id']!=canonical and other_fused['value']['persist_outcome']=='inserted'
            await request('GET',other_accepted['result_url'],'a',expected=404)
            await request('GET',other_accepted['result_url'],'b',expected=200)
            evidence['second_tenant']={'receipt':other_accepted,'separate_canonical_id':True}
            # Malformed broker envelope, independently of HTTP validation.
            bad={**payload('bad-stream'),'schema_version':'v999','tenant_id':identities['a']['tenant_id']}
            ack=await producer.send_and_wait(RAW,json.dumps(bad).encode(),key=identities['a']['tenant_id'].encode())
            evidence['bad_broker_schema_acknowledged']={'input_id':bad['id'],
                'topic':ack.topic,'partition':ack.partition,'offset':ack.offset}
            dead=None
            for _ in range(20):
                dead=await db.fetchrow('SELECT id,tenant_id,topic,reason,schema_version,source_event_id,topic_partition,kafka_offset '
                                      'FROM aisoc_dead_letters WHERE topic=$1 AND topic_partition=$2 AND kafka_offset=$3',
                                      ack.topic,ack.partition,ack.offset)
                if dead:break
                await asyncio.sleep(1)
            assert dead and dead['kafka_offset']==ack.offset and dead['topic_partition']==ack.partition
            evidence['bad_broker_schema']={'input_id':bad['id'],'broker_coordinate':
                {'topic':ack.topic,'partition':ack.partition,'offset':ack.offset},'durable_dead_letter':safe_row(dead)}
            counts=await db.fetch('SELECT tenant_id,count(*) AS count FROM alerts WHERE tenant_id=ANY($1::uuid[]) GROUP BY tenant_id',
                                  [uuid.UUID(identities[k]['tenant_id']) for k in ('a','b')])
            evidence['final_alert_counts']=[safe_row(r) for r in counts]
            assert sorted(r['count'] for r in counts)==[1,1]
            evidence['status']='primary chain and checked boundaries passed; original occurrence-folding limitation retained'
        RESULT.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':evidence['status'],'canonical_id':canonical,
                          'raw_messages_captured':len(evidence['raw_messages']),
                          'fused_messages_captured':len(evidence['fused_messages']),
                          'http_checks':len(evidence['http_checks']),'source_ids_preserved':True}))
    except Exception as exc:
        evidence['status']='failed';evidence['failure_type']=type(exc).__name__
        evidence['failure']=str(exc)[:800]
        RESULT.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
        raise
    finally:
        await db.close();await producer.stop();await consumer.stop()


async def complete_retained_probe():
    """Resolve only the failed DLQ lookup, retaining the first run unchanged."""
    original=Path('/output/acceptance-first-main-failed.json')
    evidence=json.loads(original.read_text())
    assert evidence['status']=='failed' and len(evidence['http_checks'])==14
    db=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'))
    c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=None,
                      enable_auto_commit=False,**kafka_client_kwargs())
    await c.start()
    try:
        bad_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'socai2/'+BATCH+'/bad-stream'))
        row=await db.fetchrow('SELECT id,tenant_id,topic,reason,schema_version,source_event_id,topic_partition,kafka_offset '
                             'FROM aisoc_dead_letters WHERE topic=$1 AND schema_version=$2 AND payload_excerpt LIKE $3 '
                             'ORDER BY occurred_at DESC LIMIT 1',RAW,'v999','%'+bad_id+'%')
        assert row is not None
        tp=TopicPartition(row['topic'],row['topic_partition']);c.assign([tp]);c.seek(tp,row['kafka_offset'])
        message=await asyncio.wait_for(c.getone(),15)
        value=json.loads(message.value)
        assert value['id']==bad_id and value['schema_version']=='v999'
        assert message.offset==row['kafka_offset'] and message.partition==row['topic_partition']
        evidence['bad_broker_schema']={'input_id':bad_id,'durable_dead_letter':safe_row(row),
            'verified_raw_record':{'topic':message.topic,'partition':message.partition,'offset':message.offset,
                                   'sha256':hashlib.sha256(message.value).hexdigest(),'value':value},
            'tenant_source_fields_unresolved_before_unknown_version_rejection':True}
        counts=await db.fetch('SELECT tenant_id,count(*) AS count FROM alerts WHERE tenant_id=ANY($1::uuid[]) GROUP BY tenant_id',
            [uuid.UUID(evidence[k]['receipt']['tenant_id']) for k in ('second_tenant',)] + [uuid.UUID(evidence['accepted']['tenant_id'])])
        assert sorted(r['count'] for r in counts)==[1,1]
        evidence['final_alert_counts']=[safe_row(r) for r in counts]
        evidence['first_run_retained']=original.name
        evidence['verification_correction']='Original probe looked up unresolved source_event_id. Targeted readback uses durable topic/partition/offset; no HTTP input or broker message replayed.'
        evidence.pop('failure',None);evidence.pop('failure_type',None)
        evidence['status']='primary chain and checked boundaries passed; original occurrence-folding limitation retained'
        RESULT.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':evidence['status'],'http_checks_retained':len(evidence['http_checks']),
                          'dlq_coordinate_verified':True,'tenant':row['tenant_id'],'no_inputs_replayed':True}))
    finally:
        await db.close();await c.stop()


if __name__=='__main__':
    if '--complete-retained' in sys.argv:
        asyncio.run(asyncio.wait_for(complete_retained_probe(),45))
    else:
        asyncio.run(asyncio.wait_for(main(json.load(sys.stdin)),180))
