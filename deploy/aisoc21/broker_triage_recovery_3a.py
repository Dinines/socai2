"""Bounded real Kafka/PG delivery recovery; three captured inputs, no model.

prepare runs on the old image. All worker children are fresh OS processes on
one tested/deployed image. A method substitute never fabricates an exchange,
usage or cost. Exclusive checkpoints forbid blind publication or call replay.
"""
from __future__ import annotations

import asyncio
import contextlib
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, '/app')
E = Path('/evidence')
B = '3a-triage-recovery-20261020'
READS = ('organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read',
         'recent_dispositions_read', 'identity_context_read')
PREFIX = 'socai2.test.' + B + '.broker.'
LIMITS = {'publishes': 8, 'deliveries': 12, 'methods': 6, 'runs': 3,
          'source_artifacts': 10, 'real_model_requests': 0, 'cost_rows': 0}
ALLOWED = {'services/agents/app/workers/fused_alert_consumer.py',
           'services/agents/app/workers/triage_persistence.py',
           'services/agents/app/workers/triage_delivery.py',
           'services/agents/app/investigator/ledger.py'}


class ProbeBoundary(BaseException):
    """An operator tripwire must not become a production fallback."""


def save(name, value):
    with (E / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write('\n')
    (E / name).chmod(0o600)


def read(name):
    return json.loads((E / name).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, default=str).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_snapshot():
    files = {'services/agents/app/' + str(p.relative_to('/app/app')): sha(p)
             for p in Path('/app/app').rglob('*.py')}
    return {'files_sha256': files, 'aggregate_sha256': digest(files),
            'operator_sha256': sha(__file__), 'pid': os.getpid(),
            'reported_probe_image_id': os.environ.get('AISOC_PROBE_IMAGE_ID', 'unknown')}


def resources():
    result = {name: {'topic': PREFIX + name, 'dlq': PREFIX + name + '.dlq',
                     'group': PREFIX + name + '.worker'} for name in ('warm', 'concurrent', 'unknown')}
    result['warm']['cold_group'] = PREFIX + 'warm.cold'
    result['concurrent']['second_group'] = PREFIX + 'concurrent.second'
    return result


def load():
    state = json.loads(Path('/private/state.json').read_text())
    assert state['batch'] == B
    inputs = read('inputs.json')
    assert set(inputs) == {'warm', 'concurrent', 'unknown'}
    tenant = str(uuid.UUID(state['identities']['a']['tenant_id']))
    canonical = []
    for value in inputs.values():
        alert_id = str(uuid.UUID(value['alert_row_id']))
        assert value['id'] == value['alert']['id'] == alert_id
        assert value['tenant_id'] == value['alert']['tenant_id'] == tenant
        assert value['alert']['source'] == 'socai2-' + B
        canonical.append(alert_id)
    assert len(set(canonical)) == 3
    return state, inputs, tenant


def guard(state, inputs, *, old=False):
    source = source_snapshot()
    if old:
        assert source['reported_probe_image_id'] == state['images']['agents']
    else:
        config = read('recovery-configuration.json')
        assert config['inputs_sha256'] == digest(inputs)
        assert config['inputs_file_sha256'] == sha(E / 'inputs.json')
        assert config['resources'] == resources()
        assert config['old_source']['operator_sha256'] == source['operator_sha256']
        before = config['old_source']['files_sha256']
        changes = {k for k in set(before) | set(source['files_sha256'])
                   if before.get(k) != source['files_sha256'].get(k)}
        assert changes and changes <= ALLOWED, changes
        tests, deployed = read('tests-acceptance.json'), read('deployment.json')
        assert tests['tested_runtime_source_sha256'] == source['files_sha256']
        assert deployed['old_image'] == state['images']['agents']
        assert source['reported_probe_image_id'] == deployed['images']['agents']
    return source


async def wait_file(name, seconds=45):
    deadline = asyncio.get_running_loop().time() + seconds
    while not (E / name).exists():
        assert asyncio.get_running_loop().time() < deadline, 'Barrier outcome unknown; do not replay'
        await asyncio.sleep(.1)
    return read(name)


async def child(role):
    log = E / ('recovery-child-' + role + '.log')
    assert not log.exists(), 'Retain prior child attempt; no automatic rerun'
    with log.open('xb') as stream:
        process = await asyncio.create_subprocess_exec(sys.executable, __file__, 'child', role,
                                                       stdout=stream, stderr=asyncio.subprocess.STDOUT)
    log.chmod(0o600)
    save('recovery-child-' + role + '-spawned.json', {'pid': process.pid, 'parent_pid': os.getpid()})
    return process


async def join(process, role, expected=0):
    try:
        code = await asyncio.wait_for(process.wait(), 65)
    except BaseException:
        if process.returncode is None:
            process.kill()
            await process.wait()
        raise
    save('recovery-child-' + role + '-exit.json', {'pid': process.pid, 'exit_code': code, 'expected': expected})
    assert code == expected, ('Child stopped; inspect evidence without rerun', role, code)


async def main(mode, role=None):
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, OffsetAndMetadata, TopicPartition
    from app.core.kafka_security import kafka_client_kwargs
    from app.investigator import ledger
    from app.workers import fused_alert_consumer as module
    from app.agents import auto_triage_agent as agent

    os.umask(0o077)
    assert mode in {'prepare', 'all', 'main', 'warm', 'concurrent', 'unknown', 'verify', 'child'}
    state, inputs, tenant_text = load()
    tenant = uuid.UUID(tenant_text)
    topic_map, security = resources(), kafka_client_kwargs()
    assert security['security_protocol'] in {'SSL', 'SASL_SSL'}
    bootstrap = os.environ['KAFKA_BOOTSTRAP_SERVERS']
    assert not module.worker_enabled() and not module._escalation_enabled() and not module._approvals_enabled()
    assert not module._memory_writeback_enabled() and not module.alert_trigger.deployment_enabled()
    source = guard(state, inputs, old=mode == 'prepare')
    label = role if mode == 'child' else mode
    save('recovery-' + label + '-started.json', {'mode': mode, 'role': role, 'pid': os.getpid(),
        'at': datetime.now(timezone.utc), 'source': source, 'inputs_sha256': digest(inputs),
        'limits': LIMITS, 'real_model_requests': 0, 'resident_worker_enabled': False})

    if mode == 'prepare':
        from aiokafka.admin import AIOKafkaAdminClient, NewTopic
        names = [v[k] for v in topic_map.values() for k in ('topic', 'dlq')]
        assert len(set(names)) == 6
        admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap, **security)
        await admin.start()
        try:
            assert not set(names).intersection(await admin.list_topics()), 'Never reset existing topics/groups'
            await admin.create_topics([NewTopic(n, 1, 1, topic_configs={'retention.ms': '604800000'}) for n in names])
        finally:
            await admin.close()
        groups = []
        for key, value in topic_map.items():
            for group in [value['group']] + [value[k] for k in ('cold_group', 'second_group') if k in value]:
                consumer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=group,
                                            enable_auto_commit=False, **security)
                await consumer.start()
                try:
                    tp = TopicPartition(value['topic'], 0); consumer.assign([tp])
                    assert (await consumer.end_offsets([tp]))[tp] == 0 and await consumer.committed(tp) is None
                    await consumer.commit({tp: OffsetAndMetadata(0, 'new-empty-3a10-recovery-baseline')})
                    groups.append({'alias': key, 'group': group, 'committed': await consumer.committed(tp)})
                    assert groups[-1]['committed'] == 0
                finally:
                    await consumer.stop()
        assert len(groups) == 5
        save('recovery-configuration.json', {'batch': B, 'resources': topic_map, 'groups': groups,
             'inputs_sha256': digest(inputs), 'inputs_file_sha256': sha(E / 'inputs.json'),
             'old_source': source, 'limits': LIMITS, 'real_model_requests': 0})
        return

    # Import only after deployment; prepare works on the frozen old image.
    from app.workers import triage_delivery as delivery
    real_pool, real_persist, real_safe = ledger.get_pool, ledger.persist_auto_triage, agent.safe_ainvoke
    effects = {'methods': [], 'deliveries': [], 'faults': [], 'dlq_acks': [], 'tripwires': [], 'persist': [], 'delivery_calls': []}
    flags = {'fault': False, 'fail_dlq': False, 'tripwire': False}

    def event(kind, value):
        existing = list(E.glob('recovery-' + label + '-' + kind + '-*.json'))
        item = {'role': label, 'pid': os.getpid(), **value}
        save('recovery-' + label + '-' + kind + '-' + str(len(existing)) + '.json', item)
        effects[kind].append(item)
        return item

    async def forbid_model(*args, **kwargs):
        event('tripwires', {'name': 'safe_ainvoke'})
        raise ProbeBoundary('No actual model is authorized in this probe')
    agent.safe_ainvoke = forbid_model

    real_lookup, real_claim = delivery.lookup, delivery.claim
    async def delivery_call(operation, callback, **kwargs):
        assert set(kwargs) == {'run_id', 'tenant_id', 'alert_id', 'workflow_version'}
        assert isinstance(kwargs['run_id'], uuid.UUID) and isinstance(kwargs['tenant_id'], uuid.UUID)
        item = {'operation': operation, 'arguments': kwargs}
        try:
            result = await callback(**kwargs)
        except Exception as exc:
            event('delivery_calls', {**item, 'raised': type(exc).__name__, 'reason': str(exc)})
            raise
        event('delivery_calls', {**item, 'result': result})
        return result
    async def lookup(**kwargs): return await delivery_call('lookup', real_lookup, **kwargs)
    async def claim(**kwargs): return await delivery_call('claim', real_claim, **kwargs)
    delivery.lookup, delivery.claim = lookup, claim

    async def material(value, *, enforce_bounds=True):
        investigation = module.build_state(value); assert investigation is not None
        pool = await real_pool(); assert pool is not None
        result = {}
        async with pool.acquire() as conn:
            async with conn.transaction():
                await ledger._set_rls_context(conn, tenant)
                for key, table, predicate, arg in (
                    ('runs', 'investigation_runs', 'id=$1', investigation.run_id),
                    ('events', 'investigation_events', 'run_id=$1', investigation.run_id),
                    ('artifacts', 'investigation_artifacts', 'run_id=$1', investigation.run_id),
                    ('costs', 'aisoc_run_costs', 'run_id=$1', str(investigation.run_id)),
                    ('shadow', 'aisoc_shadow_decisions', 'alert_id=$1', uuid.UUID(value['alert_row_id'])),
                    ('alerts', 'alerts', 'id=$1', uuid.UUID(value['alert_row_id'])),
                ):
                    scoped = tenant_text if key == 'costs' else tenant
                    rows = await conn.fetch('SELECT row_to_json(t)::text AS material FROM (SELECT * FROM ' + table +
                         ' WHERE ' + predicate + ' AND tenant_id=$2) t ORDER BY row_to_json(t)::text', arg, scoped)
                    result[key] = [json.loads(row['material']) for row in rows]
        result['counts'] = {k: len(v) for k, v in result.items()}
        if enforce_bounds:
            assert result['counts']['runs'] <= 1 and result['counts']['artifacts'] <= 5 and not result['costs']
        return result

    async def bounded():
        values = {k: await material(v) for k, v in inputs.items()}
        assert sum(v['counts']['runs'] for v in values.values()) <= LIMITS['runs']
        assert sum(v['counts']['artifacts'] for v in values.values()) <= LIMITS['source_artifacts']
        return values

    class FaultConnection:
        def __init__(self, conn): self.conn = conn
        def __getattr__(self, name): return getattr(self.conn, name)
        async def execute(self, sql, *args, **kwargs):
            if flags['fault'] and 'INSERT INTO investigation_artifacts' in str(sql) and len(args) > 4 and args[4] == 'identity_context_read':
                event('faults', {'operation': 'actual SELECT1/0 in production artifact transaction'})
                return await self.conn.execute('SELECT 1/0')
            return await self.conn.execute(sql, *args, **kwargs)
    class FaultAcquire:
        def __init__(self, pool): self.ctx = pool.acquire()
        async def __aenter__(self): return FaultConnection(await self.ctx.__aenter__())
        async def __aexit__(self, *args): return await self.ctx.__aexit__(*args)
    class FaultPool:
        def __init__(self, pool): self.pool = pool
        def acquire(self): return FaultAcquire(self.pool)

    async def observe_persist(**fields):
        event('persist', {'fields': deepcopy(fields), 'fields_sha256': digest(fields)})
        original = ledger.get_pool
        async def pool(): return FaultPool(await real_pool())
        if flags['fault']: ledger.get_pool = pool
        try: return await real_persist(**fields)
        finally: ledger.get_pool = original
    ledger.persist_auto_triage = observe_persist

    class GuardReader:
        def __init__(self, original): self.original = original
        def __getattr__(self, name):
            async def call(*args, **kwargs):
                if flags['tripwire']:
                    event('tripwires', {'name': 'reader.' + name})
                    raise ProbeBoundary('A recovered result must not re-read context')
                return await getattr(self.original, name)(*args, **kwargs)
            return call
    class GuardBusiness:
        def __init__(self, original): self.original = original
        async def apply_for_tenant(self, *args, **kwargs):
            if flags['tripwire']:
                event('tripwires', {'name': 'business_context'})
                raise ProbeBoundary('A recovered result must precede current policy')
            return await self.original.apply_for_tenant(*args, **kwargs)

    class FailedDLQ:
        async def send_and_wait(self, topic, value):
            save('recovery-warm-unconfirmed-dlq.json', {'topic': topic, 'value': value, 'actual_send_attempted': False})
            raise OSError('Probe supplies no DLQ confirmation; broker stays healthy')
    class AckDLQ:
        def __init__(self, original): self.original = original
        async def send_and_wait(self, topic, value):
            sent = await self.original.send_and_wait(topic, value=value)
            event('dlq_acks', {'topic': sent.topic, 'partition': sent.partition, 'offset': sent.offset,
                               'body': value, 'broker_ack_monotonic': asyncio.get_running_loop().time()})
            return sent

    class Worker(module.FusedAlertTriageWorker):
        def __init__(self, alias, group):
            cfg = topic_map[alias]
            super().__init__(bootstrap_servers=bootstrap, topic=cfg['topic'], group_id=group,
                             dlq_topic=cfg['dlq'], max_attempts=1, entity_concurrency=1)
            self.alias, self.results = alias, []
            self._reader = GuardReader(self._reader)
            if self._business_context is not None: self._business_context = GuardBusiness(self._business_context)
        async def _process_with_retry(self, message):
            assert len(list(E.glob('recovery-*-deliveries-*.json'))) < LIMITS['deliveries']
            event('deliveries', {'input_sha256': digest(message)})
            result = await super()._process_with_retry(message)
            self.results.append({'returned': result})
            return result
        async def triage(self, message):
            result = await super().triage(message)
            save('recovery-' + label + '-result-' + str(len(self.results)) + '.json', result)
            return result
        async def _llm_triage(self, investigation):
            if flags['tripwire']:
                event('tripwires', {'name': 'model_method'})
                raise ProbeBoundary('Recovery must never enter a new model method')
            assert len(list(E.glob('recovery-*-methods-*.json'))) < LIMITS['methods']
            snapshot = await material(inputs[self.alias])
            assert snapshot['counts']['runs'] == 1
            assert any(row['seq'] == -1 and row['kind'] == 'triage_started' for row in snapshot['events'])
            event('methods', {'run_id': str(investigation.run_id), 'actual_model_request': False,
                              'started_visible_before_method': snapshot})
            if label == 'unknown-crash':
                save('recovery-unknown-crash-intent.json', {'pid': os.getpid(), 'started_committed': True,
                                                          'method_entry_not_real_request': True, 'exit_code': 23})
                os._exit(23)
            if label == 'concurrent-a':
                save('recovery-concurrent-a-holding.json', {'pid': os.getpid(), 'run_id': str(investigation.run_id)})
                await wait_file('recovery-concurrent-release.json')
            investigation.verdict, investigation.confidence = 'needs_review', 0.0
            investigation.model_used = 'probe:model-method-substitute:no-model'
            investigation.add_finding('Delivery recovery method substitute; no actual model or quality assessment.')
            investigation.confidence_basis = ['Probe-only persistence observation.']
            assert not investigation.llm_exchanges
            return investigation, 'probe_model_substitute'
        async def _ensure_producer(self):
            if flags['fail_dlq']: return FailedDLQ()
            original = await super()._ensure_producer()
            return AckDLQ(original) if original is not None else None

    async def observer(alias, group):
        consumer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=group, enable_auto_commit=False, **security)
        await consumer.start(); tp = TopicPartition(topic_map[alias]['topic'], 0); consumer.assign([tp])
        return consumer, tp
    async def launch(worker):
        task = asyncio.create_task(worker.start())
        for _ in range(200):
            if task.done(): await task
            if worker._consumer and worker._consumer.assignment(): return task
            await asyncio.sleep(.1)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError): await task
        raise ProbeBoundary('Assignment unknown; never republish')
    async def stop(worker, task, *, failed=False):
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        except ledger.LedgerPersistError: assert failed
        await worker.stop()
    async def until(consumer, tp, expected, task):
        for _ in range(240):
            if task.done(): await task
            if await consumer.committed(tp) == expected: return
            await asyncio.sleep(.125)
        raise ProbeBoundary('Offset outcome unknown; never republish')
    async def publish(alias):
        assert len(list(E.glob('recovery-publish-*-ack.json'))) < LIMITS['publishes']
        save('recovery-publish-' + alias + '-sending.json', inputs[alias])
        producer = AIOKafkaProducer(bootstrap_servers=bootstrap, value_serializer=lambda v: json.dumps(v).encode(), **security)
        await producer.start()
        try:
            sent = await producer.send_and_wait(topic_map[alias]['topic'], value=inputs[alias], partition=0)
            assert sent.partition == sent.offset == 0
            save('recovery-publish-' + alias + '-ack.json', {'topic': sent.topic, 'partition': 0, 'offset': 0,
                                                            'input_sha256': digest(inputs[alias])})
        finally: await producer.stop()
    async def dlq(alias):
        consumer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=None, enable_auto_commit=False, **security)
        await consumer.start()
        try:
            tp = TopicPartition(topic_map[alias]['dlq'], 0); consumer.assign([tp])
            end = (await consumer.end_offsets([tp]))[tp]; assert end in {0, 1}
            if not end: return {'end_offset': 0, 'messages': []}
            consumer.seek(tp, 0); msg = await asyncio.wait_for(consumer.getone(), 10)
            return {'end_offset': end, 'messages': [{'offset': msg.offset, 'body': json.loads(msg.value),
                                                    'sha256': hashlib.sha256(msg.value).hexdigest()}]}
        finally: await consumer.stop()

    original_governor = module.get_governor
    def governor():
        if flags['tripwire']:
            event('tripwires', {'name': 'governor'})
            raise ProbeBoundary('Recovery must precede the current governor cache')
        return original_governor()
    module.get_governor = governor
    try:
        if mode == 'child':
            assert role in {'warm-cold', 'concurrent-a', 'concurrent-b', 'unknown-crash', 'unknown-resume'}
            alias = 'warm' if role == 'warm-cold' else ('concurrent' if role.startswith('concurrent') else 'unknown')
            cfg = topic_map[alias]
            group = cfg.get('cold_group') if role == 'warm-cold' else (cfg.get('second_group') if role == 'concurrent-b' else cfg['group'])
            flags['tripwire'] = role in {'warm-cold', 'concurrent-b', 'unknown-resume'}
            initial = await material(inputs[alias])
            worker = Worker(alias, group); consumer, tp = await observer(alias, group); task = None
            try:
                task = await launch(worker)
                save('recovery-' + role + '-ready.json', {'pid': os.getpid(), 'group': group})
                await until(consumer, tp, 1, task)
                final = await material(inputs[alias])
                if role == 'warm-cold': assert final == initial
                if flags['tripwire']: assert not effects['methods'] and not effects['persist'] and not effects['tripwires']
                if role in {'concurrent-b', 'unknown-resume'}:
                    result = await dlq(alias); assert len(result['messages']) == 1
                    assert result['messages'][0]['body']['original'] == inputs[alias]
                    assert not any(row['kind'] == 'triage_verdict' for row in final['events'])
                else: result = await dlq(alias)
                save('recovery-' + role + '-complete.json', {'before': initial, 'after': final, 'effects': effects,
                    'dlq': result, 'committed': await consumer.committed(tp), 'actual_model_requests': 0})
            finally:
                if task is not None: await stop(worker, task)
                await consumer.stop()
        elif mode == 'warm':
            cfg = topic_map['warm']; worker = Worker('warm', cfg['group'])
            consumer, tp = await observer('warm', cfg['group']); task = None
            try:
                initial = await material(inputs['warm']); assert not initial['runs'] and not initial['events'] and not initial['artifacts']
                flags.update(fault=True, fail_dlq=True)
                task = await launch(worker); await publish('warm')
                try: await asyncio.wait_for(asyncio.shield(task), 30)
                except ledger.LedgerPersistError: pass
                else: raise ProbeBoundary('Expected actual persist error and unconfirmed DLQ')
                assert await consumer.committed(tp) == 0
                rolled = await material(inputs['warm'])
                assert len(rolled['runs']) == 1 and rolled['runs'][0]['status'] == 'running'
                assert len(rolled['events']) == 1 and rolled['events'][0]['seq'] == -1
                assert not rolled['artifacts'] and not rolled['costs'] and len(effects['faults']) == 1
                unconfirmed = await dlq('warm'); assert not unconfirmed['messages']
                save('recovery-warm-rollback.json', {'pg': rolled, 'offset': 0, 'dlq': unconfirmed,
                     'only_claim_survives': True, 'model_method_substitute_count': len(effects['methods'])})
                await stop(worker, task, failed=True); task = None
                flags.update(fault=False, fail_dlq=False, tripwire=True)
                task = await launch(worker); await until(consumer, tp, 1, task)
                final = await material(inputs['warm'])
                assert len(effects['methods']) == 1 and len(effects['persist']) == 2 and not effects['tripwires']
                assert effects['persist'][0]['fields_sha256'] == effects['persist'][1]['fields_sha256']
                assert len(final['runs']) == 1 and final['runs'][0]['status'] == 'completed'
                verdicts = [v for v in final['events'] if v['kind'] == 'triage_verdict']; assert len(verdicts) == 1
                assert len(final['artifacts']) == 5 and not final['costs']
                fields = effects['persist'][0]['fields']
                assert all(fields[k]['status'] in {'success', 'no_match'} for k in READS)
                for row in final['artifacts']:
                    assert row['kind'] in READS and json.loads(row['content']) == fields[row['kind']] == verdicts[0]['payload'][row['kind']]
                    assert row['event_id'] == verdicts[0]['id'] and row['sha256'] == hashlib.sha256(row['content'].encode()).hexdigest()
                assert fields['tokens'] == 0 and fields['llm_exchanges'] == []
                manual = ('status', 'disposition', 'resolved_at', 'priority', 'tags', 'snoozed_until', 'snoozed_by_id')
                assert {k: initial['alerts'][0].get(k) for k in manual} == {k: final['alerts'][0].get(k) for k in manual}
                save('recovery-warm-complete.json', {'initial': initial, 'rolled_back': rolled, 'recovered': final,
                     'effects': effects, 'same_worker_pid': os.getpid(), 'same_worker_instance': True,
                     'committed': 1, 'model_or_reader_reentered_on_recovery': False, 'actual_model_requests': 0})
            finally:
                if task is not None: await stop(worker, task)
                await consumer.stop()
            process = await child('warm-cold'); await join(process, 'warm-cold')
        elif mode == 'concurrent':
            initial = await material(inputs['concurrent'])
            assert not initial['runs'] and not initial['events'] and not initial['artifacts']
            first = await child('concurrent-a')
            second = None
            try:
                await wait_file('recovery-concurrent-a-ready.json'); await publish('concurrent')
                holding = await wait_file('recovery-concurrent-a-holding.json')
                second = await child('concurrent-b'); await join(second, 'concurrent-b')
                assert holding['pid'] != second.pid
                save('recovery-concurrent-release.json', {'after_second_process_exit': True, 'first_pid': first.pid, 'second_pid': second.pid})
                await join(first, 'concurrent-a')
            finally:
                for process in (first, second):
                    if process is not None and process.returncode is None:
                        process.kill()
                        await process.wait()
            a, b = read('recovery-concurrent-a-complete.json'), read('recovery-concurrent-b-complete.json')
            assert len(a['effects']['methods']) == 1 and not b['effects']['methods']
            final = await material(inputs['concurrent'])
            assert final['runs'][0]['status'] == 'completed' and len(final['artifacts']) == 5
            manual = ('status', 'disposition', 'resolved_at', 'priority', 'tags', 'snoozed_until', 'snoozed_by_id')
            assert {k: initial['alerts'][0].get(k) for k in manual} == {k: final['alerts'][0].get(k) for k in manual}
            save('recovery-concurrent-complete.json', {'initial': initial, 'first': a, 'second': b, 'final': final,
                 'distinct_os_pids': [first.pid, second.pid], 'actual_overlap_holding_then_second': True,
                 'method_entries': 1, 'actual_model_requests': 0})
        elif mode == 'unknown':
            process = await child('unknown-crash')
            await wait_file('recovery-unknown-crash-ready.json'); await publish('unknown')
            await join(process, 'unknown-crash', expected=23)
            cfg = topic_map['unknown']; consumer, tp = await observer('unknown', cfg['group'])
            try: assert await consumer.committed(tp) == 0
            finally: await consumer.stop()
            before = await material(inputs['unknown'])
            assert before['runs'][0]['status'] == 'running' and len(before['events']) == 1 and before['events'][0]['seq'] == -1
            assert not before['artifacts']
            process = await child('unknown-resume'); await join(process, 'unknown-resume')
            final = await material(inputs['unknown']); assert final == before
            save('recovery-unknown-complete.json', {'before_resume': before, 'after_resume': final,
                 'crash_exit': 23, 'resume': read('recovery-unknown-resume-complete.json'),
                 'no_automatic_model_recalculation': True, 'actual_model_requests': 0})
        elif mode in {'all', 'main'}:
            for phase in ('warm', 'concurrent', 'unknown', 'verify'):
                process = await child_mode(phase)
                await join(process, 'mode-' + phase)
            save('recovery-all-complete.json', {'phases': ['warm', 'concurrent', 'unknown', 'verify'], 'actual_model_requests': 0})
        else:
            for name in ('warm', 'concurrent', 'unknown'): read('recovery-' + name + '-complete.json')
            values = await bounded()
            assert values['warm'] == read('recovery-warm-complete.json')['recovered']
            assert values['concurrent'] == read('recovery-concurrent-complete.json')['final']
            assert values['unknown'] == read('recovery-unknown-complete.json')['after_resume']
            counts = {key: len(list(E.glob(pattern))) for key, pattern in {
                'publishes': 'recovery-publish-*-ack.json', 'deliveries': 'recovery-*-deliveries-*.json',
                'methods': 'recovery-*-methods-*.json'}.items()}
            assert counts == {'publishes': 3, 'deliveries': 7, 'methods': 3}, counts
            assert not list(E.glob('recovery-*-tripwires-*.json'))

            # The production lookup uses the real pool and SQL. Only its Run
            # SELECT is replaced by a real server-side division error; the
            # shared PG service and other sessions remain healthy.
            identity = module.build_state(inputs['warm'])
            arguments = module.FusedAlertTriageWorker._delivery_fields(identity)
            expected = await delivery.lookup(**arguments)
            assert expected['reused_persisted'] and expected['recovery_format'] == 'summary_v1'
            class QueryFaultConnection(FaultConnection):
                async def fetchrow(self, sql, *args, **kwargs):
                    if str(sql).strip() == delivery._RUN_SQL.strip():
                        event('faults', {'operation': 'actual SELECT1/0 replacing production Run lookup'})
                        return await self.conn.fetchrow('SELECT 1/0')
                    return await self.conn.fetchrow(sql, *args, **kwargs)
            class QueryFaultAcquire(FaultAcquire):
                async def __aenter__(self): return QueryFaultConnection(await self.ctx.__aenter__())
            class QueryFaultPool(FaultPool):
                def acquire(self): return QueryFaultAcquire(self.pool)
            async def query_fault_pool(): return QueryFaultPool(await real_pool())
            ledger.get_pool = query_fault_pool
            try:
                try: await delivery.lookup(**arguments)
                except ledger.LedgerPersistError as exc:
                    assert type(exc.__cause__).__name__ == 'DivisionByZeroError'
                    query_failure = {'type': type(exc).__name__, 'cause': type(exc.__cause__).__name__}
                else: raise ProbeBoundary('PG read failure must not become a missing Run')
            finally: ledger.get_pool = real_pool
            assert await delivery.lookup(**arguments) == expected
            cross = {**arguments, 'tenant_id': uuid.UUID(state['identities']['b']['tenant_id'])}
            try: await delivery.claim(**cross)
            except ledger.LedgerPersistError as exc: cross_failure = {'type': type(exc).__name__, 'reason': str(exc)}
            else: raise ProbeBoundary('Cross-tenant canonical identity must not authorize a claim')
            assert await bounded() == values
            save('recovery-lookup-failure-acceptance.json', {'before': expected, 'query_failure': query_failure,
                 'after': expected, 'cross_tenant': cross_failure, 'pg_materials_unchanged': True,
                 'actual_shared_pg_outage': False, 'model_or_worker_invoked': False})

            legacy_request = read('legacy-lookup-request.json')
            assert set(legacy_request) == {'run_id', 'tenant_id', 'alert_id', 'workflow_version'}
            assert legacy_request['tenant_id'] == tenant_text
            legacy_args = {**legacy_request, 'run_id': uuid.UUID(legacy_request['run_id']),
                           'tenant_id': uuid.UUID(legacy_request['tenant_id'])}
            value = {'tenant_id': tenant_text, 'alert_row_id': legacy_request['alert_id'],
                     'alert': {'id': legacy_request['alert_id'], 'tenant_id': tenant_text}}
            assert module.build_state(value).run_id == legacy_args['run_id']
            legacy_before = await material(value, enforce_bounds=False)
            recovered = await delivery.lookup(**legacy_args)
            assert recovered['recovery_format'] == 'legacy_first_verdict' and recovered['reused_persisted']
            assert recovered['cost']['tokens'] > 0 and recovered['cost']['tokens'] == legacy_before['runs'][0]['total_tokens']
            assert recovered['legacy_missing_fields'] and recovered['effect_status'] == 'not_replayed'
            assert recovered['incident_id'] is None and recovered['shadow'] is None and recovered['cost']['resolved_models'] is None
            assert await material(value, enforce_bounds=False) == legacy_before
            save('recovery-legacy-lookup-acceptance.json', {'arguments': legacy_request, 'result': recovered,
                 'before': legacy_before, 'old_material_unchanged': True, 'actual_new_model_requests': 0,
                 'worker_or_broker_replay_invoked': False, 'does_not_invent_missing_legacy_fields': True})
            save('recovery-verify-complete.json', {'materials': values, 'counts': counts, 'limits': LIMITS,
                 'source': source, 'actual_model_requests': 0, 'legacy_lookup_and_read_fault_proof': True,
                 'full_worker_admission_accepted': False})
        assert source_snapshot() == source
    finally:
        ledger.get_pool, ledger.persist_auto_triage, agent.safe_ainvoke = real_pool, real_persist, real_safe
        delivery.lookup, delivery.claim = real_lookup, real_claim
        module.get_governor = original_governor
        await ledger.close_pool()


async def child_mode(mode):
    log = E / ('recovery-mode-' + mode + '.log')
    assert not log.exists()
    with log.open('xb') as stream:
        process = await asyncio.create_subprocess_exec(sys.executable, __file__, mode,
                                                       stdout=stream, stderr=asyncio.subprocess.STDOUT)
    log.chmod(0o600)
    return process


if __name__ == '__main__':
    assert len(sys.argv) in {2, 3}
    asyncio.run(main(*sys.argv[1:]))
