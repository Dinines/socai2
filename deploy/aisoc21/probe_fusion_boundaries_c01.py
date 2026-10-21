"""C01 legacy, pre-snapshot crash-gap and durable-DLQ boundary probes.

Host21 only, after the candidate build and C01 offline tests:
  python probe_fusion_boundaries_c01.py run-all TEST_ATTEMPT
Each phase owns an exclusive checkpoint and a fresh UID10001 process. Never
repeat a failed phase automatically. All artifacts live under E/boundaries;
the gap group's retained offset0/end1 is an intentional unresolved result.

This reuses the main probe's encoding, hashes, evidence helpers, fixed source
and batch names. Its launch and real engine initialization follow the same
candidate-image/read-only-source/PG/Redis/SSL-Kafka contract; no model is used.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
import uuid

import probe_fusion_delivery_c01 as main_probe

sys.dont_write_bytecode = True
R, S, E, P = main_probe.R, main_probe.S, main_probe.E, main_probe.P
BATCH, SOURCE = main_probe.BATCH, main_probe.SOURCE
canonical, digest = main_probe.canonical, main_probe.digest
read, save, sha, sources = main_probe.read, main_probe.save, main_probe.sha, main_probe.sources
PHASES = ('init', 'legacy-first', 'legacy-replay', 'gap-seed', 'gap-hold', 'dlq-hold', 'dlq-recover', 'verify')
LIMITS = {'new_alert_rows': 1, 'raw_send_attempts': 4, 'fused_send_attempts': 2,
          'all_send_attempts': 6, 'worker_deliveries': 5, 'output_reads': 2,
          'deliveries_including_output_reads': 7, 'topics': 6, 'groups': 3,
          'real_models': 0, 'shared_service_restarts': 0, 'ddl': 0}


def resources():
    prefix = 'socai2.test.' + BATCH + '.boundaries'
    return {alias: {'raw': prefix + '.' + alias + '.raw',
                    'fused': prefix + '.' + alias + '.fused',
                    'group': prefix + '.' + alias + '.worker'} for alias in ('legacy', 'gap', 'dlq')}


def host_run(phase, test_attempt):
    assert phase in PHASES and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', test_attempt)
    tests = read(E / f'tests-fusion-{test_attempt}.json')
    assert tests['exit_code'] == 0 and tests['passed'] > 0 and not tests['failed'] and not tests['errors']
    assert tests['source_unchanged'] and tests['test_inputs_unchanged']
    current = sources(S)
    assert current == tests['tested_runtime_source_sha256']
    assert all(sha(S / name) == value for name, value in tests['test_input_sha256'].items())
    built = read(E / 'built-image.json')
    state = read(P / 'state.json')
    assert built['source_sha256'] == current and state['batch'] == BATCH
    amended = read(E / 'limits-amended.json')
    assert amended['broker_send_attempts_including_failed'] == amended['test_deliveries'] == 20
    assert amended['raw_send_attempts'] == amended['fused_send_attempts'] == 10
    boundary = E / 'boundaries'
    if phase == 'init':
        boundary.mkdir(mode=0o700)
        os.chown(boundary, 10001, 10001)
        save(boundary, 'contract.json', {
            'batch': BATCH, 'source': SOURCE, 'resources': resources(),
            'tenant_id': str(uuid.UUID(state['identities']['a']['tenant_id'])),
            'parent_image': state['parent_image'], 'candidate_image': built['fusion'],
            'runtime_source_sha256': current, 'operator_sha256': sha(__file__),
            'main_operator_sha256': sha(main_probe.__file__),
            'unit_test_record_sha256': sha(E / f'tests-fusion-{test_attempt}.json'),
            'amended_limits_sha256': sha(E / 'limits-amended.json'), 'limits': LIMITS,
        })
        os.chown(boundary / 'contract.json', 10001, 10001)
    contract = read(boundary / 'contract.json')
    assert contract['runtime_source_sha256'] == current and contract['candidate_image'] == built['fusion']
    assert contract['operator_sha256'] == sha(__file__)
    assert contract['main_operator_sha256'] == sha(main_probe.__file__)
    assert contract['unit_test_record_sha256'] == sha(E / f'tests-fusion-{test_attempt}.json')
    assert contract['amended_limits_sha256'] == sha(E / 'limits-amended.json')
    item = json.loads(subprocess.check_output(['docker', 'inspect', 'socai2-fusion-1']))[0]
    assert item['Image'] == contract['parent_image'] and 'socai2_default' in item['NetworkSettings']['Networks']
    candidate = json.loads(subprocess.check_output(['docker', 'image', 'inspect', built['fusion']]))[0]
    assert candidate['Id'] == contract['candidate_image']
    saved = read(P / 'fusion-container-before.json')
    certs = [m for m in saved['Mounts'] if m['Destination'] == '/run/certs/ca.crt']
    assert len(certs) == 1 and not certs[0]['RW'] and certs[0] in item['Mounts']
    save(E, 'boundaries-host-' + phase + '-started.json', {
        'phase': phase, 'operator_sha256': sha(__file__), 'candidate_image': built['fusion'],
        'contract_sha256': sha(boundary / 'contract.json'),
        'at': datetime.now(timezone.utc).isoformat(), 'never_automatically_replayed': True,
    })
    name = 'socai2-c01-boundaries-' + phase
    command = ['docker', 'run', '--rm', '--pull', 'never', '--name', name,
               '--user', '10001:10001', '--network', 'socai2_default', '--read-only',
               '--tmpfs', '/tmp:rw,nosuid,nodev,size=128m', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges:true', '--env-file', str(P / 'probe.env'),
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'PYTHONPATH=/app',
               '-e', 'C01_PROBE_IMAGE_ID=' + built['fusion'],
               '-v', str(S) + ':/source:ro', '-v', str(boundary) + ':/evidence',
               '-v', certs[0]['Source'] + ':/run/certs/ca.crt:ro',
               '-w', '/app', built['fusion'], 'python',
               '/source/deploy/aisoc21/probe_fusion_boundaries_c01.py', 'inside', phase]
    log = E / ('boundaries-host-' + phase + '.log')
    with log.open('xb') as output:
        try:
            result = subprocess.run(command, capture_output=True, timeout=100)
            output.write(result.stdout + result.stderr)
            code = result.returncode
        except subprocess.TimeoutExpired as exc:
            output.write((exc.stdout or b'') + (exc.stderr or b''))
            cleanup = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
            output.write(b'\nBoundary deadline; removed only this named probe container.\n')
            output.write(cleanup.stdout + cleanup.stderr)
            code = 124
    log.chmod(0o600)
    save(E, 'boundaries-host-' + phase + '-exit.json', {
        'phase': phase, 'exit_code': code, 'log_sha256': sha(log), 'source_unchanged': sources(S) == current,
    })
    assert code == 0 and sources(S) == current, 'Inspect boundary checkpoints; never blindly replay.'
    print(json.dumps({'phase': phase, 'exit_code': code, 'runtime_service_changed': False}))


async def inside(phase):
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    from aiokafka.structs import TopicPartition
    import redis.asyncio as redis_module
    import structlog
    from app.core.config import settings
    from app.core.kafka_security import kafka_client_kwargs
    from app.models.alert import RawAlert
    from app.services.alert_sink import AlertSink
    from app.services.correlator import Correlator
    from app.services.deduplicator import Deduplicator
    from app.services.delivery_recovery import DeliveryRecovery, make_snapshot
    from app.services.dlq_sink import PostgresDLQ
    from app.services.fusion_engine import FusionEngine
    from app.workers import consumer as worker_module

    def drop_log(_logger, _method, _event):
        raise structlog.DropEvent
    structlog.configure(processors=[drop_log])
    logging.disable(logging.CRITICAL)
    directory = Path('/evidence')
    contract = read(directory / 'contract.json')
    assert phase in PHASES and contract['batch'] == BATCH and contract['resources'] == resources()
    assert os.geteuid() == 10001 and os.environ['ENVIRONMENT'] == 'production'
    assert os.environ['C01_PROBE_IMAGE_ID'] == contract['candidate_image']
    assert sources(Path('/source')) == contract['runtime_source_sha256']
    image_source = {'services/fusion/app/' + str(p.relative_to('/app/app')): sha(p)
                    for p in sorted(Path('/app/app').rglob('*.py'))}
    assert image_source == contract['runtime_source_sha256']
    assert sha(__file__) == contract['operator_sha256']
    assert sha(main_probe.__file__) == contract['main_operator_sha256']
    assert int(urlsplit(settings.redis_url).path.strip('/')) == 9
    security = kafka_client_kwargs()
    assert security['security_protocol'] == 'SSL' and security['ssl_context'].check_hostname
    assert security['ssl_context'].verify_mode != 0
    save(directory, phase + '-started.json', {
        'phase': phase, 'pid': os.getpid(), 'uid': os.geteuid(),
        'candidate_image': contract['candidate_image'], 'at': datetime.now(timezone.utc).isoformat(),
        'runtime_source_sha256': digest(contract['runtime_source_sha256']), 'limits': LIMITS,
    })
    if phase != 'init':
        previous = PHASES[PHASES.index(phase) - 1]
        assert (directory / (previous + '-done.json')).is_file(), 'Previous phase not confirmed.'
    cfg = resources()
    tenant = uuid.UUID(contract['tenant_id'])
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + BATCH + '/boundaries')
    fixtures = {}
    for label in ('legacy', 'gap'):
        alert = RawAlert(
            tenant_id=tenant, identity_version='legacy-v1' if label == 'legacy' else 'source-v1',
            source_alert_id=uuid.uuid5(namespace, label) if label == 'gap' else None,
            source=SOURCE, title='C01 boundary ' + label,
            description='Synthetic original boundary body ' + label,
            severity='high', hostname='socai2-c01-boundary-' + label,
            username='socai2-c01-boundary-user-' + label,
            source_event_ids=[SOURCE + '-boundary-' + label], connector_type='socai2_c01_probe',
            external_id=SOURCE + '-boundary-' + label,
            raw_event={'synthetic': True, 'batch': BATCH, 'boundary': label}, tags=[SOURCE],
            created_at='2026-10-20T11:02:00Z', event_time='2026-10-20T11:01:00Z',
        )
        alert.id = alert.deterministic_id()
        fixtures[label] = alert
    replay = fixtures['legacy'].model_copy(deep=True)
    replay.description = 'Later changed body must not replace first material'
    replay.raw_event = {'synthetic': True, 'batch': BATCH, 'changed': True}
    replay.event_time = replay.event_time.replace(minute=9)
    replay.source_event_ids.append(SOURCE + '-boundary-legacy-later')
    assert replay.fingerprint() == fixtures['legacy'].fingerprint() and replay.deterministic_id() == fixtures['legacy'].id
    # A v1 envelope with an explicit tenant but no required alert title.
    # Deep RawAlert validation rejects it while retaining tenant lineage.
    poison = {'schema_version': 'v1', 'tenant_id': str(tenant), 'source': SOURCE, 'boundary': 'dlq'}
    values = {label: value.model_dump(mode='json') for label, value in fixtures.items()}
    values.update(legacy_replay=replay.model_dump(mode='json'), poison=poison)
    if phase == 'init':
        save(directory, 'inputs.json', values)
        save(directory, 'input-hashes.json', {key: digest(value) for key, value in values.items()})
    assert values == read(directory / 'inputs.json')
    assert {key: digest(value) for key, value in values.items()} == read(directory / 'input-hashes.json')
    bootstrap = settings.kafka_bootstrap_servers
    redis = redis_module.from_url(settings.redis_url, decode_responses=False)
    sink = AlertSink(settings.database_url)
    await sink.start()
    assert sink._pool is not None
    real_pool = sink._pool
    owned_stop = sink.stop

    async def started():
        assert sink._pool is real_pool

    async def unowned_stop():
        # The probe owns the real pool and still needs post-worker reads.
        pass

    sink.start, sink.stop = started, unowned_stop

    def event(kind, payload):
        previous = sorted(directory.glob('event-' + kind + '-*.json'))
        if kind == 'publish':
            assert len(previous) < LIMITS['all_send_attempts']
        elif kind == 'delivery':
            assert len(previous) < LIMITS['deliveries_including_output_reads']
        save(directory, 'event-' + kind + '-' + str(len(previous)) + '.json', {'phase': phase, 'pid': os.getpid(), **payload})

    async def material():
        async with real_pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                tls = dict(await conn.fetchrow('SELECT ssl, version, cipher FROM pg_stat_ssl WHERE pid=pg_backend_pid()'))
                assert tls['ssl']
                alert_rows = await conn.fetch('SELECT row_to_json(a)::text AS value FROM alerts a '
                    'WHERE tenant_id=$1 AND id=ANY($2::uuid[]) ORDER BY id', tenant, [v.id for v in fixtures.values()])
                dlq_rows = await conn.fetch('SELECT row_to_json(d)::text AS value FROM aisoc_dead_letters d '
                    'WHERE topic=$1 ORDER BY id', cfg['dlq']['raw'])
        rows = [json.loads(row['value']) for row in alert_rows]
        letters = [json.loads(row['value']) for row in dlq_rows]
        assert len(rows) <= 1 and all(row['id'] == str(fixtures['legacy'].id) for row in rows)
        assert len(letters) <= 1
        return {'pg_tls': tls, 'rows': rows, 'dead_letters': letters}

    async def position(alias):
        consumer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=cfg[alias]['group'], enable_auto_commit=False, **security)
        await consumer.start()
        try:
            tp, output = TopicPartition(cfg[alias]['raw'], 0), TopicPartition(cfg[alias]['fused'], 0)
            consumer.assign([tp])
            return {'committed': await consumer.committed(tp), 'raw_end': (await consumer.end_offsets([tp]))[tp],
                    'fused_end': (await consumer.end_offsets([output]))[output]}
        finally:
            await consumer.stop()

    async def publish(alias, label, expected):
        producer = AIOKafkaProducer(bootstrap_servers=bootstrap, value_serializer=canonical, **security)
        await producer.start()
        try:
            event('publish', {'kind': 'raw', 'label': label, 'topic': cfg[alias]['raw'], 'input_sha256': digest(values[label]), 'before_transport': True})
            ack = await producer.send_and_wait(cfg[alias]['raw'], partition=0, value=values[label])
            assert ack.partition == 0 and ack.offset == expected
            save(directory, 'raw-' + label + '-ack.json', {'topic': ack.topic, 'partition': ack.partition, 'offset': ack.offset,
                 'input_sha256': digest(values[label])})
        finally:
            await producer.stop()

    class SyntheticEnricher:
        async def enrich(self, alert):
            return {'ioc_lookup': {'status': 'not_requested', 'source': 'c01-synthetic-fixture'},
                    'c01_boundary': {'synthetic': True, 'marker': 'first-complete-material', 'retain': [1, 2, 3]}}

    class Engine(FusionEngine):
        async def process(self, alert):
            label = next(key for key, value in fixtures.items() if value.id == alert.id)
            assert (phase, label) in {('legacy-first', 'legacy'), ('gap-seed', 'gap')}, 'Recovery must not re-enter engine.'
            event('engine', {'label': label, 'production_engine': True, 'synthetic_enrichment_fixture': True,
                 'input_sha256': digest(alert.model_dump(mode='json'))})
            result = await super().process(alert)
            first = make_snapshot(result)
            if label == 'legacy':
                save(directory, 'first-result-legacy.json', first)
            else:
                save(directory, 'gap-completed-engine.json', {'incident_id': str(result.incident_id),
                     'result_sha256': first['sha256'], 'delivery_snapshot_saved': False, 'pg_insert_attempted': False})
            return result

    engine = Engine(Deduplicator(redis), Correlator(redis), enricher=SyntheticEnricher())

    async def run_worker(alias, expected_value, target, *, dlq_failure=False):
        settings.kafka_topic_alerts_raw, settings.kafka_topic_alerts_fused = cfg[alias]['raw'], cfg[alias]['fused']
        settings.kafka_consumer_group = cfg[alias]['group']
        settings.event_promotion_enabled = False
        completed = False

        class Consumer(AIOKafkaConsumer):
            async def __anext__(self):
                if completed:
                    raise StopAsyncIteration
                msg = await super().__anext__()
                assert msg.topic == cfg[alias]['raw'] and msg.partition == 0 and digest(msg.value) == digest(expected_value)
                event('delivery', {'kind': 'worker', 'alias': alias, 'topic': msg.topic,
                     'partition': msg.partition, 'offset': msg.offset, 'input_sha256': digest(msg.value)})
                return msg

            async def commit(self, offsets=None):
                nonlocal completed
                tp = TopicPartition(cfg[alias]['raw'], 0)
                assert offsets == {tp: target}
                event('commit', {'kind': 'intent', 'alias': alias, 'offset': target})
                await super().commit(offsets)
                assert await self.committed(tp) == target
                event('commit', {'kind': 'ack', 'alias': alias, 'offset': target})
                completed = True

        class Producer(AIOKafkaProducer):
            async def send_and_wait(self, topic, value=None, **kwargs):
                assert alias == 'legacy' and topic == cfg[alias]['fused'] and value['alert']['source'] == SOURCE
                event('publish', {'kind': 'fused', 'alias': alias, 'topic': topic, 'before_transport': True, 'body_sha256': digest(value)})
                ack = await super().send_and_wait(topic, value=value, **kwargs)
                event('fused_ack', {'topic': ack.topic, 'partition': ack.partition, 'offset': ack.offset, 'body_sha256': digest(value)})
                return ack

        dlq = PostgresDLQ((lambda: None) if dlq_failure else (lambda: real_pool))
        worker = worker_module.FusionWorker(engine, sink=sink, dlq=dlq)
        original_consumer, original_producer = worker_module.AIOKafkaConsumer, worker_module.AIOKafkaProducer
        worker_module.AIOKafkaConsumer, worker_module.AIOKafkaProducer = Consumer, Producer
        caught = None
        try:
            await asyncio.wait_for(worker.start(), 50)
        except Exception as exc:
            caught = type(exc).__name__
            save(directory, phase + '-worker-exception.json', {'exception_type': caught,
                 'attached_after_exit': worker.attached, 'no_exception_text_or_locals': True})
        finally:
            worker_module.AIOKafkaConsumer, worker_module.AIOKafkaProducer = original_consumer, original_producer
            await worker.stop()
        assert not worker.attached
        return caught

    try:
        assert await redis.ping()
        before = await material()
        save(directory, phase + '-before.json', before)
        if phase == 'init':
            assert not before['rows'] and not before['dead_letters']
            for value in fixtures.values():
                assert await redis.get(DeliveryRecovery.key(value)) is None
                assert (await engine._dedup.is_duplicate(value))[0] is False
            admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap, **security)
            await admin.start()
            try:
                topics = [value[key] for value in cfg.values() for key in ('raw', 'fused')]
                assert len(topics) == LIMITS['topics'] and not set(topics) & set(await admin.list_topics())
                await admin.create_topics([NewTopic(topic, 1, 1, topic_configs={'retention.ms': '604800000'}) for topic in topics])
            finally:
                await admin.close()
            for alias in cfg:
                consumer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=cfg[alias]['group'], enable_auto_commit=False, **security)
                await consumer.start()
                try:
                    tp = TopicPartition(cfg[alias]['raw'], 0)
                    consumer.assign([tp])
                    assert await consumer.committed(tp) is None and (await consumer.end_offsets([tp]))[tp] == 0
                    save(directory, 'group-' + alias + '-initializing.json', {'group': cfg[alias]['group'], 'offset': 0})
                    await consumer.commit({tp: 0})
                    assert await consumer.committed(tp) == 0
                finally:
                    await consumer.stop()
        elif phase == 'legacy-first':
            assert await position('legacy') == {'committed': 0, 'raw_end': 0, 'fused_end': 0}
            await publish('legacy', 'legacy', 0)
            assert await run_worker('legacy', values['legacy'], 1) is None
            assert await position('legacy') == {'committed': 1, 'raw_end': 1, 'fused_end': 1}
            lookup = await sink.lookup_delivery(fixtures['legacy'])
            assert lookup.snapshot == read(directory / 'first-result-legacy.json')
            assert lookup.alert_id == str(fixtures['legacy'].deterministic_id())
        elif phase == 'legacy-replay':
            await publish('legacy', 'legacy_replay', 1)
            assert await run_worker('legacy', values['legacy_replay'], 2) is None
            assert await position('legacy') == {'committed': 2, 'raw_end': 2, 'fused_end': 2}
            assert (await sink.lookup_delivery(replay)).snapshot == read(directory / 'first-result-legacy.json')
            original_row = read(directory / 'legacy-first-done.json')['material']['rows'][0]
            current_row = (await material())['rows'][0]
            assert {k: v for k, v in current_row.items() if k != 'source_event_ids'} == {k: v for k, v in original_row.items() if k != 'source_event_ids'}
            assert current_row['source_event_ids'] == replay.source_event_ids
        elif phase == 'gap-seed':
            assert not (await sink.lookup_delivery(fixtures['gap'])).exists
            assert (await engine._dedup.is_duplicate(fixtures['gap']))[0] is False
            await engine.process(fixtures['gap'])
            assert (await engine._dedup.is_duplicate(fixtures['gap']))[0] is True
            assert await redis.get(DeliveryRecovery.key(fixtures['gap'])) is None
            assert not (await sink.lookup_delivery(fixtures['gap'])).exists
        elif phase == 'gap-hold':
            assert (await engine._dedup.is_duplicate(fixtures['gap']))[0] is True, 'Seed TTL elapsed; do not republish/recompute.'
            assert await redis.get(DeliveryRecovery.key(fixtures['gap'])) is None
            await publish('gap', 'gap', 0)
            assert await run_worker('gap', values['gap'], 1) == 'DeliveryHold'
            assert await position('gap') == {'committed': 0, 'raw_end': 1, 'fused_end': 0}
            assert not (await sink.lookup_delivery(fixtures['gap'])).exists
            assert await redis.get(DeliveryRecovery.key(fixtures['gap'])) is None
        elif phase == 'dlq-hold':
            assert not before['dead_letters']
            await publish('dlq', 'poison', 0)
            save(directory, 'dlq-missing-provider-intent.json', {'fault': 'only dedicated PostgresDLQ provider returns None',
                 'real_pool_still_open': True, 'shared_postgres_stopped': False})
            assert await run_worker('dlq', poison, 1, dlq_failure=True) == 'DeliveryHold'
            assert await position('dlq') == {'committed': 0, 'raw_end': 1, 'fused_end': 0}
            assert not (await material())['dead_letters']
        elif phase == 'dlq-recover':
            assert await run_worker('dlq', poison, 1) is None
            assert await position('dlq') == {'committed': 1, 'raw_end': 1, 'fused_end': 0}
            letters = (await material())['dead_letters']
            assert len(letters) == 1
            letter = letters[0]
            assert letter['tenant_id'] == str(tenant) and letter['topic'] == cfg['dlq']['raw']
            assert letter['topic_partition'] == 0 and letter['kafka_offset'] == 0
            assert SOURCE in letter['payload_excerpt'] and letter['reason'].startswith('RawAlert validation failed:')
        elif phase == 'verify':
            positions = {alias: await position(alias) for alias in cfg}
            assert positions == {'legacy': {'committed': 2, 'raw_end': 2, 'fused_end': 2},
                                 'gap': {'committed': 0, 'raw_end': 1, 'fused_end': 0},
                                 'dlq': {'committed': 1, 'raw_end': 1, 'fused_end': 0}}
            first = read(directory / 'first-result-legacy.json')
            consumer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=None, enable_auto_commit=False, **security)
            await consumer.start()
            try:
                tp = TopicPartition(cfg['legacy']['fused'], 0)
                consumer.assign([tp]); consumer.seek(tp, 0)
                for offset in range(2):
                    msg = await asyncio.wait_for(consumer.getone(), 15)
                    body = json.loads(msg.value)
                    assert msg.offset == offset and msg.partition == 0
                    assert {k: v for k, v in body.items() if k not in ('alert_row_id', 'persist_outcome')} == first['fused']
                    assert body['persist_outcome'] == ('inserted' if offset == 0 else 'duplicate')
                    assert body['alert_row_id'] == str(fixtures['legacy'].id)
                    event('delivery', {'kind': 'fused_readback', 'alias': 'legacy', 'topic': msg.topic,
                         'partition': msg.partition, 'offset': msg.offset, 'wire_sha256': hashlib.sha256(msg.value).hexdigest()})
            finally:
                await consumer.stop()
            assert len(list(directory.glob('event-engine-*.json'))) == 2
            publish_events = [read(p) for p in directory.glob('event-publish-*.json')]
            delivery_events = [read(p) for p in directory.glob('event-delivery-*.json')]
            assert len(publish_events) == 6 and sum(e['kind'] == 'raw' for e in publish_events) == 4
            assert len(delivery_events) == 7 and sum(e['kind'] == 'worker' for e in delivery_events) == 5
            final = await material()
            assert len(final['rows']) == len(final['dead_letters']) == 1
            assert not (await sink.lookup_delivery(fixtures['gap'])).exists
            save(directory, 'acceptance.json', {
                'accepted': True, 'candidate_image': contract['candidate_image'],
                'image_id': contract['candidate_image'], 'source_sha256': contract['runtime_source_sha256'],
                'runtime_source_sha256': contract['runtime_source_sha256'], 'operator_sha256': sha(__file__),
                'legacy_original_uuid_and_full_first_snapshot_preserved': True,
                'gap_result': 'unknown held; offset0/end1 preserved; no repair invented',
                'dlq_missing_provider_is_a_probe_seam': True, 'dlq_pg_insert_and_exact_coordinates_confirmed': True,
                'positions': positions, 'new_alert_rows': 1, 'new_dead_letters': 1,
                'raw_send_attempts': 4, 'fused_send_attempts': 2, 'all_send_attempts': 6,
                'worker_deliveries': 5, 'output_reads': 2, 'deliveries_including_output_reads': 7,
                'topics': 6, 'groups': 3, 'real_models': 0, 'shared_restarts': 0, 'ddl': 0,
                'evidence_sha256': {p.name: sha(p) for p in sorted(directory.glob('*.json'))},
            })
        save(directory, phase + '-done.json', {'phase': phase, 'material': await material(),
             'positions': {alias: await position(alias) for alias in cfg},
             'real_models': 0, 'shared_restarts': 0, 'ddl': 0})
    finally:
        sink._pool = real_pool
        await owned_stop()
        await redis.aclose()


def main():
    os.umask(0o077)
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == 'run-all':
        for phase in PHASES:
            host_run(phase, args[1])
    elif len(args) == 3 and args[0] == 'run':
        host_run(args[1], args[2])
    elif len(args) == 2 and args[0] == 'inside':
        phase = args[1]
        try:
            asyncio.run(inside(phase))
        except BaseException as exc:
            failure = Path('/evidence') / (phase + '-failure.json')
            if not failure.exists():
                save(failure.parent, failure.name, {'phase': phase, 'exception_type': type(exc).__name__,
                     'outcome': 'inspect checkpoints; never blindly replay', 'no_exception_text_or_locals': True})
            print(json.dumps({'phase': phase, 'failed': True, 'exception_type': type(exc).__name__}))
            raise SystemExit(1) from None
    else:
        raise SystemExit('Usage: run-all TEST_ATTEMPT | run PHASE TEST_ATTEMPT')


if __name__ == '__main__':
    try:
        main()
    except AssertionError:
        print(json.dumps({'failed': True, 'reason': 'Guard failed; inspect retained checkpoints without replay.'}))
        raise SystemExit(1) from None
