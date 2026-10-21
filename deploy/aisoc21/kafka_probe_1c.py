#!/usr/bin/env python3
"""Real locked-aiokafka probe, run in a disposable cached Python container.

Only the dedicated smoke topic receives synthetic data. This is transport and
offset evidence, not a Fusion/Agents integration test.
"""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.structs import OffsetAndMetadata, TopicPartition

ROOT = Path('/work')
sys.path.insert(0, str(ROOT / 'source/deploy/aisoc21/kafka-source'))
from kafka_security import KafkaTransportError, kafka_client_kwargs

BOOTSTRAP = '192.168.1.21:9092'
BATCH = '1c-20261020'
TOPIC = 'socai2.verify.' + BATCH
GROUP = TOPIC + '.reader'
PROJECT_TOPICS = {'socai2.alerts.raw': 3, 'socai2.alerts.fused': 3,
                  'socai2.alerts.fused.dlq': 1}
EVIDENCE = ROOT / 'evidence' / BATCH


def value(number):
    return json.dumps({'batch': BATCH, 'kind': 'infrastructure-probe',
                       'sequence': number, 'text': '告警传输标记样本'},
                      sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def record(message):
    return {'topic': message.topic, 'partition': message.partition, 'offset': message.offset,
            'key': message.key.decode() if message.key else None,
            'sha256': hashlib.sha256(message.value).hexdigest(),
            'payload': json.loads(message.value)}


def coordinate(metadata):
    return {'topic': metadata.topic, 'partition': metadata.partition, 'offset': metadata.offset}


def save(name, data):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def transport_probe():
    # Do not bypass the original protected-environment refusal.
    os.environ.pop('AISOC_ALLOW_CLEARTEXT_KAFKA', None)
    os.environ['KAFKA_SECURITY_PROTOCOL'] = 'PLAINTEXT'
    refused = False
    try:
        kafka_client_kwargs(environment='production')
    except KafkaTransportError:
        refused = True
    assert refused, 'Upstream production cleartext refusal must remain effective'
    return {'production_cleartext_refused': refused,
            'test_transport': kafka_client_kwargs(environment='development')}


async def producer():
    p = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP, client_id='socai2-1c-probe-producer',
                         acks='all', enable_idempotence=True,
                         **kafka_client_kwargs(environment='development'))
    await p.start()
    return p


async def consumer(group=GROUP):
    c = AIOKafkaConsumer(TOPIC, bootstrap_servers=BOOTSTRAP,
                         client_id='socai2-1c-probe-consumer', group_id=group,
                         enable_auto_commit=False, auto_offset_reset='earliest',
                         **kafka_client_kwargs(environment='development'))
    await c.start()
    return c


async def main(mode):
    transport = transport_probe()
    admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP, client_id='socai2-1c-probe-admin',
                               **kafka_client_kwargs(environment='development'))
    await admin.start()
    try:
        if mode == 'before':
            if (EVIDENCE / 'client-before.json').exists():
                raise RuntimeError('Existing receipt retained; inspect before rerunning a write probe')
            existing = set(await admin.list_topics())
            assert not existing.intersection({TOPIC, *PROJECT_TOPICS}), 'Project topic already exists'
            topics = [NewTopic(name, partitions, 1,
                               topic_configs={'cleanup.policy': 'delete', 'min.insync.replicas': '1',
                                              'retention.ms': '86400000' if name == TOPIC else '604800000'})
                      for name, partitions in {**PROJECT_TOPICS, TOPIC: 1}.items()]
            await admin.create_topics(topics)
            p = await producer()
            try:
                brokers = [{'node_id': b.nodeId, 'host': b.host, 'port': b.port}
                           for b in p.client.cluster.brokers()]
                assert brokers and all(b['host'] == '192.168.1.21' and b['port'] == 9092 for b in brokers)
                sent = [coordinate(await p.send_and_wait(TOPIC, value(i), key=b'socai2-1c', partition=0))
                        for i in (1, 2)]
                assert [m['offset'] for m in sent] == [0, 1]
            finally:
                await p.stop()
            c = await consumer()
            try:
                first = await asyncio.wait_for(c.getone(), 25)
                assert first.value == value(1) and first.offset == sent[0]['offset']
                tp = TopicPartition(TOPIC, 0)
                await c.commit({tp: OffsetAndMetadata(first.offset + 1, '')})
                committed = await c.committed(tp)
                assert committed == 1
            finally:
                await c.stop()
            result = {'mode': mode, 'python': platform.python_version(),
                      'packages': {n: importlib.metadata.version(n) for n in ('aiokafka','async-timeout','packaging')},
                      'bootstrap': BOOTSTRAP, 'advertised_brokers': brokers, 'transport': transport,
                      'project_topics_created': PROJECT_TOPICS, 'smoke_topic': TOPIC, 'group': GROUP,
                      'input_payloads': [json.loads(value(i)) for i in (1, 2)],
                      'producer_acks': 'all', 'producer_idempotence': True,
                      'producer_acknowledged_coordinates': sent, 'first_consumer_record': record(first),
                      'committed_next_offset': committed, 'second_record_deliberately_uncommitted': True}
            save('client-before.json', result)
        else:
            before = json.loads((EVIDENCE / 'client-before.json').read_text())
            c = await consumer()
            try:
                second = await asyncio.wait_for(c.getone(), 30)
                assert second.value == value(2) and second.offset == 1
                tp = TopicPartition(TOPIC, 0)
                await c.commit({tp: OffsetAndMetadata(second.offset + 1, '')})
                p = await producer()
                try:
                    third_ack = coordinate(await p.send_and_wait(TOPIC, value(3), key=b'socai2-1c', partition=0))
                finally:
                    await p.stop()
                third = await asyncio.wait_for(c.getone(), 15)
                assert third.value == value(3) and third.offset == third_ack['offset'] == 2
                await c.commit({tp: OffsetAndMetadata(third.offset + 1, '')})
                committed = await c.committed(tp)
                assert committed == 3
            finally:
                await c.stop()
            replay = await consumer(group=None)
            try:
                records = [await asyncio.wait_for(replay.getone(), 15) for _ in range(3)]
                assert [r.value for r in records] == [value(i) for i in (1, 2, 3)]
                assert [r.offset for r in records] == [0, 1, 2]
            finally:
                await replay.stop()
            result = {'mode': mode, 'bootstrap': BOOTSTRAP, 'transport': transport,
                      'committed_before_restart': before['committed_next_offset'],
                      'first_record_on_fresh_group_session': record(second),
                      'first_record_not_redelivered_to_committed_group': True,
                      'new_write_acknowledged_after_restart': third_ack,
                      'new_write_consumed_after_restart': record(third),
                      'committed_next_offset': committed,
                      'independent_replay_from_earliest': [record(r) for r in records],
                      'all_payload_hashes_and_coordinates_match': True}
            save('client-after.json', result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        await admin.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('before', 'after'))
    args = parser.parse_args()
    asyncio.run(asyncio.wait_for(main(args.mode), 120))
