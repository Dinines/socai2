"""C01's two bounded real PG/Redis/SSL-Kafka recovery scenarios; no deployment.

On host21, after prepare_completion_c01.py and the cached unit suites:
  python probe_fusion_delivery_c01.py run-all TEST_ATTEMPT
Or use `run PHASE TEST_ATTEMPT` for each PHASE in PHASES, in order. Each worker
phase gets a fresh UID10001 container/process on the fixed candidate image;
its baked source and the read-only source both match the tested hashes. Existing checkpoints are never
replayed automatically: inspect a failed/unknown phase before any further work.

Only the INSERT seam receives an actual SELECT 1/0, and only B's dedicated
producer is deliberately stopped. The broker/PG/Redis services remain running.
Synthetic enrichment fixtures are identified as fixtures, not external intel.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
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

sys.dont_write_bytecode = True
R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
BATCH = 'c01-fusion-delivery-20261020'
E = R / 'evidence' / BATCH
P = R / 'private/completion-c01'
SOURCE = 'socai2-c01-20261020'
PHASES = ('init', 'fault-a', 'recover-a', 'replay-a', 'fault-b', 'drop-b-cache', 'recover-b', 'verify')
LIMITS = {'new_alert_rows': 3, 'publish_attempts': 9, 'raw_publish_attempts': 4,
          'fused_publish_attempts': 5, 'deliveries': 10, 'topics': 4,
          'groups': 2, 'real_models': 0, 'shared_service_restarts': 0, 'ddl': 0}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False, default=str).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(directory, name, value):
    with (directory / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, default=str)
        stream.write('\n')
    (directory / name).chmod(0o600)


def sources(root):
    base = root / 'services/fusion/app'
    return {str(p.relative_to(root)): sha(p) for p in sorted(base.rglob('*.py'))}


def runtime_sources():
    return {'services/fusion/app/' + str(p.relative_to('/app/app')): sha(p)
            for p in sorted(Path('/app/app').rglob('*.py'))}


def resources():
    prefix = 'socai2.test.' + BATCH
    return {alias: {'raw': prefix + '.' + alias + '.raw',
                    'fused': prefix + '.' + alias + '.fused',
                    'group': prefix + '.' + alias + '.worker'} for alias in ('a', 'b')}


def host_run(phase, test_attempt):
    """Docker reads private env; no private state or credentials enter evidence."""
    assert phase in PHASES and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', test_attempt)
    assert E.is_dir() and P.is_dir() and (P / 'probe.env').is_file()
    state = read(P / 'state.json')
    assert state['batch'] == BATCH
    tests = read(E / f'tests-fusion-{test_attempt}.json')
    assert tests['exit_code'] == 0 and tests['passed'] > 0
    assert not tests['failed'] and not tests['errors']
    assert tests['source_unchanged'] and tests['test_inputs_unchanged']
    current_source = sources(S)
    assert current_source == tests['tested_runtime_source_sha256']
    assert all(sha(S / name) == value for name, value in tests['test_input_sha256'].items())
    built = read(E / 'built-image.json')
    assert built['test_attempt'] == test_attempt and built['source_sha256'] == current_source
    assert built['parent'] == state['parent_image']
    item = json.loads(subprocess.check_output(['docker', 'inspect', 'socai2-fusion-1']))[0]
    assert item['Image'] == state['parent_image'], 'Resident service must remain unchanged during candidate probe.'
    networks = list(item['NetworkSettings']['Networks'])
    assert len(networks) == 1
    probe = E / 'probe'
    if phase == 'init':
        probe.mkdir(mode=0o700)
        os.chown(probe, 10001, 10001)
        contract = {'batch': BATCH, 'source': SOURCE, 'resources': resources(),
                    'tenants': {a: str(uuid.UUID(state['identities'][a]['tenant_id'])) for a in ('a', 'b')},
                    'parent_image': state['parent_image'], 'image_id': built['fusion'],
                    'network': networks[0], 'runtime_source_sha256': current_source,
                    'unit_test_record_sha256': sha(E / f'tests-fusion-{test_attempt}.json'),
                    'operator_sha256': sha(__file__), 'limits': LIMITS}
        assert contract['tenants']['a'] != contract['tenants']['b']
        save(probe, 'contract.json', contract)
        os.chown(probe / 'contract.json', 10001, 10001)
    contract = read(probe / 'contract.json')
    assert contract['runtime_source_sha256'] == current_source
    assert contract['operator_sha256'] == sha(__file__)
    assert contract['unit_test_record_sha256'] == sha(E / f'tests-fusion-{test_attempt}.json')
    assert contract['image_id'] == built['fusion'] and contract['network'] == networks[0]
    saved = read(P / 'fusion-container-before.json')
    certs = [m for m in saved['Mounts'] if m['Destination'] == '/run/certs/ca.crt']
    assert len(certs) == 1 and not certs[0]['RW']
    assert certs[0] in item['Mounts']
    save(E, 'probe-host-' + phase + '-started.json', {
        'phase': phase, 'operator_sha256': sha(__file__), 'image_id': built['fusion'],
        'contract_sha256': sha(probe / 'contract.json'),
        'at': datetime.now(timezone.utc).isoformat(), 'never_automatically_replayed': True})
    name = 'socai2-c01-probe-' + phase
    command = ['docker', 'run', '--rm', '--pull', 'never', '--name', name,
               '--user', '10001:10001', '--network', networks[0], '--read-only',
               '--tmpfs', '/tmp:rw,nosuid,nodev,size=128m', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges:true', '--env-file', str(P / 'probe.env'),
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'PYTHONPATH=/app',
               '-e', 'C01_PROBE_IMAGE_ID=' + built['fusion'],
               '-v', str(S) + ':/source:ro', '-v', str(probe) + ':/evidence',
               '-v', certs[0]['Source'] + ':/run/certs/ca.crt:ro',
               '-w', '/app', built['fusion'], 'python',
               '/source/deploy/aisoc21/probe_fusion_delivery_c01.py', 'inside', phase]
    log = E / ('probe-host-' + phase + '.log')
    with log.open('xb') as output:
        try:
            result = subprocess.run(command, capture_output=True, timeout=100)
            output.write(result.stdout + result.stderr)
            code = result.returncode
        except subprocess.TimeoutExpired as exc:
            output.write((exc.stdout or b'') + (exc.stderr or b''))
            output.write(b'\nProbe deadline; only this named probe container was removed.\n')
            try:
                cleanup = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
                output.write(cleanup.stdout + cleanup.stderr)
            except (OSError, subprocess.TimeoutExpired) as exc:
                output.write(('Cleanup unconfirmed: ' + type(exc).__name__ + '\n').encode())
            code = 124
    log.chmod(0o600)
    save(E, 'probe-host-' + phase + '-exit.json', {'phase': phase, 'exit_code': code,
         'log_sha256': sha(log), 'source_unchanged': sources(S) == current_source})
    assert code == 0, 'Probe did not finish; retain checkpoint, inspect, do not blindly rerun.'
    assert sources(S) == current_source
    if phase == 'verify':
        # Existing read-only observer: all prior materials, reservations,
        # reader identities, models, containers and volumes remain protected.
        sys.path.insert(0, str(S / 'deploy/aisoc21'))
        from configure_triage_admission_3a import observation
        before, after = read(E / 'before.json'), observation()
        assert before['environment'] == after['environment']
        for table, hashes in before['materials'].items():
            if table == 'alerts':
                assert len(after['materials'][table]) == len(hashes) + 3
                assert set(hashes) <= set(after['materials'][table])
            else:
                assert hashes == after['materials'][table]
        for field in ('budget', 'readers', 'policy_sha256', 'migrations', 'gateway'):
            assert before[field] == after[field], field
        save(E, 'probe-host-preservation.json', {'old_material_hashes_preserved': True,
             'new_alert_rows': 3, 'other_material_tables_equal': True,
             'budget_readers_policy_migrations_gateway_equal': True,
             'all_resident_containers_and_volumes_equal': True, 'real_models': 0,
             'shared_restarts': 0, 'ddl': 0, 'before_sha256': sha(E / 'before.json'),
             'after_observation_sha256': digest(after)})
        save(probe, 'acceptance.json', {'accepted': True, 'real_models': 0,
             'image_id': built['fusion'], 'source_sha256': built['source_sha256'],
             'probe_sha256': sha(__file__), 'main_scenarios_only': True,
             'verification_sha256': sha(probe / 'verify-done.json'),
             'preservation_sha256': sha(E / 'probe-host-preservation.json')})
        os.chown(probe / 'acceptance.json', 10001, 10001)
    print(json.dumps({'phase': phase, 'exit_code': code, 'business_service_changed': False}))


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
    from app.services.delivery_recovery import DeliveryHold, DeliveryRecovery, make_snapshot, restore_snapshot
    from app.services.fusion_engine import FusionEngine
    from app.workers import consumer as worker_module

    # Production loggers must not print credential-shaped exceptions or locals.
    def drop_log(_logger, _method, _event):
        raise structlog.DropEvent
    structlog.configure(processors=[drop_log])
    logging.disable(logging.CRITICAL)
    directory = Path('/evidence')
    contract = read(directory / 'contract.json')
    assert phase in PHASES and contract['batch'] == BATCH and contract['source'] == SOURCE
    assert os.geteuid() == 10001 and os.environ['ENVIRONMENT'] == 'production'
    assert os.environ['C01_PROBE_IMAGE_ID'] == contract['image_id']
    assert sources(Path('/source')) == contract['runtime_source_sha256']
    assert runtime_sources() == contract['runtime_source_sha256']
    assert sha(__file__) == contract['operator_sha256']
    assert int(urlsplit(settings.redis_url).path.strip('/')) == 9
    security = kafka_client_kwargs()
    assert security['security_protocol'] == 'SSL'
    assert security['ssl_context'].check_hostname
    assert security['ssl_context'].verify_mode != 0
    save(directory, phase + '-started.json', {'phase': phase, 'pid': os.getpid(),
         'at': datetime.now(timezone.utc).isoformat(), 'uid': os.geteuid(),
         'source_sha256': digest(contract['runtime_source_sha256']), 'limits': LIMITS})
    cfg = resources()
    assert contract['resources'] == cfg
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + BATCH)
    fixtures = {}
    for label, tenant_alias in (('a1', 'a'), ('a2', 'a'), ('b1', 'b')):
        raw = RawAlert(tenant_id=uuid.UUID(contract['tenants'][tenant_alias]),
             identity_version='source-v1', source_alert_id=uuid.uuid5(namespace, label),
             source=SOURCE, title='C01 isolated existing finding ' + label,
             description='Synthetic C01 body retained exactly for ' + label,
             severity='high', hostname='socai2-c01-host-' + tenant_alias,
             username='socai2-c01-user-' + tenant_alias, source_event_ids=[SOURCE + '-' + label],
             connector_type='socai2_c01_probe', external_id=SOURCE + '-' + label,
             raw_event={'synthetic': True, 'batch': BATCH, 'fixture': label},
             tags=[SOURCE], created_at='2026-10-20T11:02:00Z', event_time='2026-10-20T11:01:00Z')
        raw.id = raw.deterministic_id()
        fixtures[label] = raw
    values = {k: v.model_dump(mode='json') for k, v in fixtures.items()}
    if phase == 'init':
        save(directory, 'inputs.json', values)
        save(directory, 'input-hashes.json', {k: digest(v) for k, v in values.items()})
    assert values == read(directory / 'inputs.json')
    assert {k: digest(v) for k, v in values.items()} == read(directory / 'input-hashes.json')
    bootstrap = settings.kafka_bootstrap_servers
    redis = redis_module.from_url(settings.redis_url, decode_responses=False)
    sink = AlertSink(settings.database_url)
    await sink.start()
    assert sink._pool is not None
    real_pool = sink._pool

    def event(kind, payload):
        existing = sorted(directory.glob('event-' + kind + '-*.json'))
        if kind in ('publish', 'delivery'):
            assert len(existing) < LIMITS['publish_attempts' if kind == 'publish' else 'deliveries']
        if kind == 'publish':
            category = payload['kind']
            assert category in {'raw', 'fused'}
            assert sum(read(p)['kind'] == category for p in existing) < LIMITS[category + '_publish_attempts']
        name = 'event-' + kind + '-' + str(len(existing)) + '.json'
        save(directory, name, {'phase': phase, 'pid': os.getpid(), **payload})

    async def material():
        async with real_pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                tls = dict(await conn.fetchrow('SELECT ssl, version, cipher FROM pg_stat_ssl WHERE pid=pg_backend_pid()'))
                assert tls['ssl']
                rows = await conn.fetch('SELECT row_to_json(a)::text AS value FROM alerts a '
                     'WHERE id=ANY($1::uuid[]) AND tenant_id=ANY($2::uuid[]) ORDER BY id',
                     [a.id for a in fixtures.values()], [uuid.UUID(v) for v in contract['tenants'].values()])
        result = [json.loads(r['value']) for r in rows]
        assert len(result) <= 3 and all(r['connector_type'] == 'socai2_c01_probe' for r in result)
        return {'pg_tls': tls, 'rows': result}

    async def position(alias):
        c = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=cfg[alias]['group'],
                            enable_auto_commit=False, **security)
        await c.start()
        try:
            tp = TopicPartition(cfg[alias]['raw'], 0)
            c.assign([tp])
            raw_end = (await c.end_offsets([tp]))[tp]
            output = TopicPartition(cfg[alias]['fused'], 0)
            return {'committed': await c.committed(tp), 'raw_end': raw_end,
                    'fused_end': (await c.end_offsets([output]))[output]}
        finally:
            await c.stop()

    async def cache(label):
        key = DeliveryRecovery.key(fixtures[label])
        blob = await redis.get(key)
        if blob is None:
            return None
        restored = restore_snapshot(blob, fixtures[label])
        return {'key': key, 'ttl': await redis.ttl(key), 'snapshot': make_snapshot(restored)}

    async def check_previous(previous):
        assert (directory / (previous + '-done.json')).is_file(), 'Previous phase not confirmed; do not replay.'

    try:
        assert await redis.ping()
        before = await material()
        save(directory, phase + '-before.json', before)
        if phase == 'init':
            assert not before['rows']
            assert all([await cache(label) is None for label in fixtures])
            admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap, **security)
            await admin.start()
            try:
                topics = [v[k] for v in cfg.values() for k in ('raw', 'fused')]
                assert len(topics) == LIMITS['topics'] and not set(topics) & set(await admin.list_topics())
                await admin.create_topics([NewTopic(t, 1, 1, topic_configs={'retention.ms': '604800000'}) for t in topics])
            finally:
                await admin.close()
            for alias in ('a', 'b'):
                c = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=cfg[alias]['group'],
                                    enable_auto_commit=False, **security)
                await c.start()
                try:
                    tp = TopicPartition(cfg[alias]['raw'], 0)
                    c.assign([tp])
                    assert await c.committed(tp) is None and (await c.end_offsets([tp]))[tp] == 0
                    save(directory, 'group-' + alias + '-initializing.json', {'group': cfg[alias]['group'], 'offset': 0})
                    await c.commit({tp: 0})
                    assert await c.committed(tp) == 0
                    save(directory, 'group-' + alias + '-initialized.json', {'committed': 0})
                finally:
                    await c.stop()
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap, value_serializer=canonical, **security)
            await producer.start()
            try:
                for label in ('a1', 'a2', 'b1'):
                    alias = label[0]
                    event('publish', {'kind': 'raw', 'label': label, 'topic': cfg[alias]['raw'],
                                     'input_sha256': digest(values[label]), 'before_transport': True})
                    ack = await producer.send_and_wait(cfg[alias]['raw'], partition=0, value=values[label])
                    expected = 1 if label == 'a2' else 0
                    assert ack.partition == 0 and ack.offset == expected
                    save(directory, 'raw-' + label + '-ack.json', {'topic': ack.topic,
                         'partition': ack.partition, 'offset': ack.offset, 'input_sha256': digest(values[label])})
            finally:
                await producer.stop()
            save(directory, phase + '-done.json', {'positions': {a: await position(a) for a in cfg},
                 'new_alert_rows': 0, 'raw_publishes': 3, 'topics': 4, 'groups': 2})
            return

        previous = dict(zip(PHASES[1:], PHASES[:-1]))[phase]
        await check_previous(previous)
        if phase == 'drop-b-cache':
            current = await cache('b1')
            assert current is not None
            original = read(directory / 'first-result-b1.json')
            assert current['snapshot'] == original
            lookup = await sink.lookup_delivery(fixtures['b1'])
            assert lookup.exists and lookup.snapshot == original
            key = DeliveryRecovery.key(fixtures['b1'])
            save(directory, 'b1-cache-delete-intent.json', {'key': key, 'snapshot_sha256': original['sha256'],
                 'only_this_batch_single_key': True})
            removed = await redis.delete(key)
            assert removed == 1 and await redis.get(key) is None
            save(directory, phase + '-done.json', {'removed_keys': [key], 'removed_count': 1,
                 'pg_snapshot_unchanged': (await sink.lookup_delivery(fixtures['b1'])).snapshot == original})
            return

        if phase == 'verify':
            result = await material()
            assert len(result['rows']) == 3
            positions = {a: await position(a) for a in cfg}
            assert positions == {'a': {'committed': 3, 'raw_end': 3, 'fused_end': 3},
                                 'b': {'committed': 1, 'raw_end': 1, 'fused_end': 1}}
            seen = {}
            c = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=None, enable_auto_commit=False, **security)
            await c.start()
            try:
                for alias, total in (('a', 3), ('b', 1)):
                    tp = TopicPartition(cfg[alias]['fused'], 0)
                    c.assign([tp]); c.seek(tp, 0)
                    for expected in range(total):
                        msg = await asyncio.wait_for(c.getone(), 15)
                        body = json.loads(msg.value)
                        label = next(k for k, v in fixtures.items() if str(v.id) == body['id'])
                        assert msg.partition == 0 and msg.offset == expected
                        assert label == (('a1', 'a2', 'a1')[expected] if alias == 'a' else 'b1')
                        assert body['alert_row_id'] == body['id']
                        actual = {k: v for k, v in body.items() if k not in ('alert_row_id', 'persist_outcome')}
                        assert actual == read(directory / ('first-result-' + label + '.json'))['fused']
                        replayed = alias == 'a' and expected == 2
                        assert body['persist_outcome'] == ('duplicate' if label == 'b1' or replayed else 'inserted')
                        event('delivery', {'kind': 'fused_readback', 'label': label, 'topic': msg.topic,
                             'partition': msg.partition, 'offset': msg.offset, 'wire_sha256': hashlib.sha256(msg.value).hexdigest()})
                        seen.setdefault(label, []).append(body)
            finally:
                await c.stop()
            assert set(seen) == set(fixtures)
            for label, raw in fixtures.items():
                lookup = await sink.lookup_delivery(raw)
                first = read(directory / ('first-result-' + label + '.json'))
                assert lookup.exists and lookup.snapshot == first
                assert restore_snapshot(lookup.snapshot, raw).model_dump(mode='json') == first['fused']
            assert seen['a1'][0]['incident_id'] == seen['a2'][0]['incident_id']
            assert seen['b1'][0]['incident_id'] != seen['a1'][0]['incident_id']
            assert len(seen['a1']) == 2
            assert {k: v for k, v in seen['a1'][0].items() if k != 'persist_outcome'} == {
                k: v for k, v in seen['a1'][1].items() if k != 'persist_outcome'}
            assert len(list(directory.glob('event-engine-*.json'))) == 3
            assert len(list(directory.glob('event-publish-*.json'))) == 9  # Four raw, four acked fused, one stopped attempt.
            assert len(list(directory.glob('event-delivery-*.json'))) == 10  # Six worker, four independent output reads.
            save(directory, phase + '-done.json', {'positions': positions, 'material': result,
                 'actual_engine_calls': 3, 'raw_publish_attempts': 4, 'fused_publish_attempts': 5,
                 'all_publish_attempts': 9, 'raw_publishes_acked': 4, 'fused_publishes_acked': 4,
                 'failed_stopped_producer_attempts': 1, 'worker_deliveries': 6, 'output_reads': 4,
                 'all_original_fields_enrichments_and_incidents_equal': True,
                 'real_models': 0, 'shared_restarts': 0, 'ddl': 0,
                 'evidence_sha256': {p.name: sha(p) for p in sorted(directory.glob('*.json'))}})
            return

        alias = 'a' if phase.endswith('-a') else 'b'
        initial = await position(alias)
        start_offset = 2 if phase == 'replay-a' else 0
        assert initial['committed'] == start_offset and initial['fused_end'] == start_offset
        assert initial['raw_end'] == (2 if alias == 'a' else 1)
        replay_value = None
        if phase == 'replay-a':
            replay_value = dict(values['a1'])
            replay_value.update(title='Changed replay title, never the first result',
                 description='Changed replay body, never the first result',
                 event_time='2026-10-21T03:04:05Z',
                 raw_event={'synthetic': True, 'mutated': True,
                            'candidate_enrichment': {'replace_first': True}})
            replay = RawAlert.model_validate(replay_value)
            assert replay.deterministic_id() == fixtures['a1'].id
            assert replay.fingerprint() == fixtures['a1'].fingerprint()
            save(directory, 'a1-mutated-replay-input.json', {'body': replay_value,
                 'input_sha256': digest(replay_value), 'candidate_enrichment_used': False})
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap, value_serializer=canonical, **security)
            await producer.start()
            try:
                event('publish', {'kind': 'raw', 'label': 'a1-replay', 'topic': cfg['a']['raw'],
                     'input_sha256': digest(replay_value), 'before_transport': True})
                ack = await producer.send_and_wait(cfg['a']['raw'], partition=0, value=replay_value)
                assert ack.offset == 2 and ack.partition == 0
                save(directory, 'a1-mutated-replay-ack.json', {'offset': ack.offset,
                     'partition': ack.partition, 'topic': ack.topic, 'input_sha256': digest(replay_value)})
            finally:
                await producer.stop()
        if phase == 'recover-a':
            cached = await cache('a1')
            assert cached is not None and cached['ttl'] > 20, 'First-result TTL elapsed; hold, never recompute.'
            assert cached['snapshot'] == read(directory / 'first-result-a1.json')
            assert not (await sink.lookup_delivery(fixtures['a1'])).exists
        if phase == 'recover-b':
            assert await cache('b1') is None
            assert (await sink.lookup_delivery(fixtures['b1'])).snapshot == read(directory / 'first-result-b1.json')
        settings.kafka_topic_alerts_raw = cfg[alias]['raw']
        settings.kafka_topic_alerts_fused = cfg[alias]['fused']
        settings.kafka_consumer_group = cfg[alias]['group']
        settings.event_promotion_enabled = False
        allowed_engine = {'fault-a': {'a1'}, 'recover-a': {'a2'}, 'replay-a': set(),
                          'fault-b': {'b1'}, 'recover-b': set()}[phase]

        class SyntheticEnricher:
            async def enrich(self, alert):
                return {'ioc_lookup': {'status': 'not_requested', 'source': 'c01-synthetic-fixture'},
                        'c01_probe': {'synthetic': True, 'tenant_id': str(alert.tenant_id),
                                      'nested': [{'marker': 'first-full-enrichment'}, {'retain': [1, 2, 3]}]}}

        class Engine(FusionEngine):
            async def process(self, alert):
                label = next(k for k, v in fixtures.items() if v.id == alert.id)
                assert label in allowed_engine, 'Recovery must not re-enter engine for a completed first result.'
                event('engine', {'label': label, 'input_sha256': digest(alert.model_dump(mode='json')),
                     'actual_production_engine': True, 'synthetic_enrichment_fixture': True})
                result = await super().process(alert)
                save(directory, 'first-result-' + label + '.json', make_snapshot(result))
                return result

        class FaultConnection:
            def __init__(self, conn): self.conn = conn
            def __getattr__(self, name): return getattr(self.conn, name)
            async def fetchrow(self, sql, *args, **kwargs):
                if 'INSERT INTO alerts' in str(sql) and args and args[0] == fixtures['a1'].id:
                    save(directory, 'a1-real-sql-fault-intent.json', {'statement': 'SELECT 1/0',
                         'seam': 'only marked A1 alert INSERT', 'shared_pg_stopped': False})
                    try:
                        return await self.conn.fetchrow('SELECT 1/0')
                    except Exception as exc:
                        save(directory, 'a1-real-sql-fault-result.json', {'exception_type': type(exc).__name__,
                             'sqlstate': getattr(exc, 'sqlstate', None)})
                        raise
                return await self.conn.fetchrow(sql, *args, **kwargs)

        class FaultPool:
            @asynccontextmanager
            async def acquire(self):
                async with real_pool.acquire() as conn:
                    yield FaultConnection(conn)
            async def close(self):
                return None  # The owned real pool is closed separately below.

        if phase == 'fault-a': sink._pool = FaultPool()
        real_persist = sink.persist
        async def observed_persist(fused, **kwargs):
            outcome = await real_persist(fused, **kwargs)
            event('persist', {'alert_id': str(fused.id), 'outcome': outcome.outcome.value,
                 'durable': outcome.durable, 'snapshot_sha256': make_snapshot(fused)['sha256']})
            return outcome
        sink.persist = observed_persist
        # Keep the already SSL-checked production pool; Worker.start's repeated
        # start must not replace it and bypass the narrow A1 SQL fault seam.
        async def started():
            assert sink._pool is not None
        sink.start = started
        async def keep_pool_open():
            return None
        sink.stop = keep_pool_open
        committed_target = False
        target = 3 if phase == 'replay-a' else (2 if alias == 'a' else 1)
        class Consumer(AIOKafkaConsumer):
            async def __anext__(self):
                if committed_target:
                    raise StopAsyncIteration
                msg = await super().__anext__()
                assert msg.topic == cfg[alias]['raw'] and msg.partition == 0
                label = ('a1' if replay_value is not None and digest(msg.value) == digest(replay_value)
                         else next(k for k, v in values.items() if digest(v) == digest(msg.value)))
                assert label[0] == alias
                event('delivery', {'kind': 'worker', 'label': label, 'topic': msg.topic,
                     'partition': msg.partition, 'offset': msg.offset, 'input_sha256': digest(msg.value)})
                return msg
            async def commit(self, offsets=None):
                nonlocal committed_target
                assert offsets and set(offsets) == {TopicPartition(cfg[alias]['raw'], 0)}
                requested = next(iter(offsets.values()))
                assert isinstance(requested, int) and 0 < requested <= target
                event('commit', {'kind': 'intent', 'topic': cfg[alias]['raw'], 'partition': 0, 'offset': requested})
                await super().commit(offsets)
                actual = await self.committed(TopicPartition(cfg[alias]['raw'], 0))
                assert actual == requested
                event('commit', {'kind': 'ack', 'offset': actual})
                committed_target = actual == target

        class Producer(AIOKafkaProducer):
            async def start(self):
                await super().start()
                if phase == 'fault-b':
                    await self.stop()
                    save(directory, 'b1-real-producer-stopped.json', {'real_sdk_stop_awaited': True,
                         'only_this_probe_producer': True, 'shared_broker_stopped': False})
            async def send_and_wait(self, topic, value=None, **kwargs):
                assert topic == cfg[alias]['fused'] and value['alert']['source'] == SOURCE
                event('publish', {'kind': 'fused', 'topic': topic, 'body_sha256': digest(value),
                                 'before_transport': True, 'stopped_sdk': phase == 'fault-b'})
                ack = await super().send_and_wait(topic, value=value, **kwargs)
                event('fused_ack', {'topic': ack.topic, 'partition': ack.partition,
                     'offset': ack.offset, 'body_sha256': digest(value)})
                return ack

        engine = Engine(Deduplicator(redis), Correlator(redis), enricher=SyntheticEnricher())
        worker = worker_module.FusionWorker(engine, sink=sink)
        old_consumer, old_producer = worker_module.AIOKafkaConsumer, worker_module.AIOKafkaProducer
        worker_module.AIOKafkaConsumer, worker_module.AIOKafkaProducer = Consumer, Producer
        caught = None
        try:
            await asyncio.wait_for(worker.start(), 50)
        except Exception as exc:
            caught = type(exc).__name__
            save(directory, phase + '-worker-exception.json', {'exception_type': caught,
                 'attached_after_exit': worker.attached, 'no_exception_text_or_locals': True})
        finally:
            worker_module.AIOKafkaConsumer, worker_module.AIOKafkaProducer = old_consumer, old_producer
            await worker.stop()
            sink._pool = real_pool
        assert not worker.attached
        position_after = await position(alias)
        result = await material()
        if phase.startswith('fault-'):
            assert caught == ('DeliveryHold' if alias == 'a' else 'ProducerClosed')
            assert position_after['committed'] == 0 and position_after['fused_end'] == 0
            original = read(directory / ('first-result-' + alias + '1.json'))
            assert (await cache(alias + '1'))['snapshot'] == original
            lookup = await sink.lookup_delivery(fixtures[alias + '1'])
            assert lookup.exists == (alias == 'b')
            if alias == 'a':
                assert not (await sink.lookup_delivery(fixtures['a2'])).exists
                assert read(directory / 'a1-real-sql-fault-result.json')['sqlstate'] == '22012'
                assert [read(p)['label'] for p in sorted(directory.glob('event-delivery-*.json'))] == ['a1']
            else:
                assert lookup.snapshot == original
        else:
            assert caught is None and position_after['committed'] == target and position_after['fused_end'] == target
        if phase == 'replay-a':
            assert before == result, 'Replay must preserve the existing PG rows byte-for-byte.'
            assert (await sink.lookup_delivery(fixtures['a1'])).snapshot == read(directory / 'first-result-a1.json')
        save(directory, phase + '-done.json', {'position': position_after, 'material': result,
             'expected_worker_failure': phase.startswith('fault-'), 'worker_exception_type': caught,
             'source_unchanged': sources(Path('/source')) == contract['runtime_source_sha256'],
             'real_models': 0, 'shared_restarts': 0, 'ddl': 0})
    finally:
        await real_pool.close()
        sink._pool = None
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
