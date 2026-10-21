"""Bounded broker diagnostics on unchanged production worker/PG code.

The broker cases replace only the _llm_triage method, explicitly returning
probe_model_substitute with no model transcript, usage or request. Persistence
and DLQ fault proxies are named separately. Observed defects are recorded,
never converted into worker admission. The fallback mode uses the original
_llm_triage catch with a controlled run_auto_triage error and a capture sink.
"""
from pathlib import Path
from datetime import datetime, timezone
import asyncio
import contextlib
import hashlib
import json
import os
import sys
import uuid

# The operator is mounted as /probe.py, while the cached Agents image keeps
# the production package under /app/app. Match the application entry point's
# import root without modifying or copying any runtime source.
sys.path.insert(0, '/app')

B = '3a-triage-admission-20261020'
E = Path('/evidence')
INPUTS = Path('/private/broker-inputs.json')
ALIASES = ('schema', 'ledger-false', 'repeat', 'pg-recovery', 'pg-dlq')
PREFIX = 'socai2.test.' + B + '.broker.'
READS = ('organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read',
         'recent_dispositions_read', 'identity_context_read')


def save(name, value):
    with (E / name).open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write('\n')
    (E / name).chmod(0o600)


def read(name):
    return json.loads((E / name).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def source_snapshot():
    app = Path('/app/app')
    assert app.is_dir()
    files = {'services/agents/app/' + str(path.relative_to(app)): sha(path) for path in app.rglob('*.py')}
    return {'runtime_source_sha256': files, 'operator_sha256': sha(__file__),
            'runtime_source_aggregate_sha256': digest(files)}


async def main(mode):
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, OffsetAndMetadata, TopicPartition
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    from app.agents import auto_triage_agent as agent
    from app.core.kafka_security import kafka_client_kwargs
    from app.investigator import ledger
    from app.workers import fused_alert_consumer as module

    assert mode in {'prepare', 'run', 'cold-repeat', 'restart', 'fallback'}
    os.umask(0o077)
    fixture = json.loads(INPUTS.read_text())
    state = json.loads(Path('/private/state.json').read_text())
    assert fixture['batch'] == state['batch'] == B
    assert fixture['tenant_id'] == state['identities']['a']['tenant_id']
    assert set(fixture['inputs']) == {'repeat', 'ledger_false', 'pg_recovery', 'pg_dlq'}
    assert fixture['max_new_publishes'] == 7 and fixture['max_deliveries'] == 8
    assert fixture['max_broker_model_method_substitutions'] == 6 and fixture['max_fallback_model_method_substitutions'] == 1
    assert fixture['max_total_method_substitutions'] == 7 and fixture['max_real_model_requests'] == 0
    assert not module.worker_enabled() and os.getenv('AISOC_AGENT_RAISE_APPROVALS') == '0'
    assert not module._escalation_enabled(), 'Automatic investigation graph must remain off'
    bootstrap = os.environ['KAFKA_BOOTSTRAP_SERVERS']
    security = kafka_client_kwargs()
    topics = {alias: {'topic': PREFIX + alias, 'dlq': PREFIX + alias + '.dlq',
                      'group': PREFIX + alias + '.worker'} for alias in ALIASES}
    frozen_source = source_snapshot()
    started = 'broker-' + mode + '-started.json'
    assert not (E / started).exists(), 'Inspect existing checkpoints; no blind input/model-method replay'
    if mode != 'prepare':
        config = read('broker-configuration.json')
        assert config['input_sha256'] == sha(INPUTS) and config['source'] == frozen_source
    save(started, {'mode': mode, 'at': datetime.now(timezone.utc), 'source': frozen_source,
                   'input_sha256': sha(INPUTS), 'resident_worker_enabled': False,
                   'max_real_model_requests': 0, 'no_blind_replay': True})

    if mode == 'prepare':
        all_topics = [value[key] for value in topics.values() for key in ('topic', 'dlq')]
        assert len(set(all_topics)) == 10
        admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap, client_id='socai2-3a09-broker-admin', **security)
        await admin.start()
        try:
            existing = set(await admin.list_topics())
            assert not existing.intersection(all_topics), 'No existing topic or group may be reset'
            await admin.create_topics([NewTopic(name, 1, 1, topic_configs={'cleanup.policy': 'delete', 'retention.ms': '604800000'})
                                       for name in all_topics])
        finally:
            await admin.close()
        baselines = {}
        for alias, item in topics.items():
            consumer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=item['group'], enable_auto_commit=False, **security)
            await consumer.start()
            try:
                tp = TopicPartition(item['topic'], 0)
                consumer.assign([tp])
                assert (await consumer.end_offsets([tp]))[tp] == 0 and await consumer.committed(tp) is None
                await consumer.commit({tp: OffsetAndMetadata(0, 'socai2-new-empty-bounded-baseline')})
                assert await consumer.committed(tp) == 0
                baselines[alias] = {'topic_empty': True, 'committed': 0, 'partitions': 1}
            finally:
                await consumer.stop()
        save('broker-inputs-raw.json', fixture)
        save('broker-configuration.json', {'batch': B, 'topics': topics, 'baselines': baselines,
             'input_sha256': sha(INPUTS), 'source': frozen_source, 'production_runtime_changed': False,
             'limits': {key: value for key, value in fixture.items() if key.startswith('max_')},
             'broker_model_replacement': 'Subclass _llm_triage; probe_model_substitute; no safe-call, response or tokens',
             'fallback_replacement': 'Original _llm_triage catches controlled AutoTriageError from run_auto_triage; capture writer',
             'independent_of_three_real_model_cases': True})
        print(json.dumps({'mode': mode, 'new_topics': 10, 'new_groups': 5, 'baseline': 0, 'published': 0}))
        return

    real_get_pool, real_persist = ledger.get_pool, ledger.persist_auto_triage
    model_entries, delivery_entries, blocked_model_requests = [], [], []
    persist_returns, pg_fault_hits, dlq_fault_hits = [], [], []

    async def no_real_model(*args, **kwargs):
        blocked_model_requests.append({'unexpected_safe_call': True})
        raise RuntimeError('Broker diagnostic forbids any actual model request')

    original_safe_call = agent.safe_ainvoke
    agent.safe_ainvoke = no_real_model
    tenant = uuid.UUID(fixture['tenant_id'])

    async def material(value):
        investigation = module.build_state(value)
        pool = await real_get_pool()
        assert pool is not None
        async with pool.acquire() as connection:
            async with connection.transaction():
                await ledger._set_rls_context(connection, tenant)
                output = {}
                for key, table, predicate, argument in [
                    ('runs', 'investigation_runs', 'id=$1', investigation.run_id),
                    ('events', 'investigation_events', 'run_id=$1', investigation.run_id),
                    ('artifacts', 'investigation_artifacts', 'run_id=$1', investigation.run_id),
                    ('costs', 'aisoc_run_costs', 'run_id=$1', str(investigation.run_id)),
                    ('shadow', 'aisoc_shadow_decisions', 'alert_id=$1', uuid.UUID(value['alert_row_id'])),
                ]:
                    # The telemetry table uses TEXT keys and has no id column;
                    # the ledger/shadow tables use UUID tenant IDs. Sort the
                    # complete projection rather than assuming a shared PK.
                    tenant_argument = str(tenant) if key == 'costs' else tenant
                    rows = await connection.fetch('SELECT row_to_json(t)::text AS material FROM (SELECT * FROM ' + table +
                                                  ' WHERE ' + predicate + ' AND tenant_id=$2) t ORDER BY row_to_json(t)::text',
                                                  argument, tenant_argument)
                    output[key] = [json.loads(row['material']) for row in rows]
        output['counts'] = {key: len(rows) for key, rows in output.items()}
        return output

    async def bounded_materials():
        values = {name: await material(value) for name, value in fixture['inputs'].items()}
        assert sum(value['counts']['runs'] for value in values.values()) <= 2
        assert sum(value['counts']['artifacts'] for value in values.values()) <= 10
        assert sum(value['counts']['costs'] for value in values.values()) == 0
        return values

    class FaultConnection:
        def __init__(self, connection, phase):
            self.connection, self.phase = connection, phase

        def __getattr__(self, name):
            return getattr(self.connection, name)

        async def execute(self, statement, *args, **kwargs):
            if 'INSERT INTO investigation_artifacts' in str(statement) and len(args) > 4 and args[4] == 'identity_context_read':
                pg_fault_hits.append({'phase': self.phase, 'operation': 'identity artifact INSERT replaced by actual SELECT 1/0'})
                return await self.connection.execute('SELECT 1/0')
            return await self.connection.execute(statement, *args, **kwargs)

    class FaultAcquire:
        def __init__(self, pool, phase):
            self.context, self.phase = pool.acquire(), phase

        async def __aenter__(self):
            return FaultConnection(await self.context.__aenter__(), self.phase)

        async def __aexit__(self, *args):
            return await self.context.__aexit__(*args)

    class FaultPool:
        def __init__(self, pool, phase):
            self.pool, self.phase = pool, phase

        def acquire(self):
            return FaultAcquire(self.pool, self.phase)

    class UnconfirmedProducer:
        async def send_and_wait(self, topic, value):
            dlq_fault_hits.append({'topic': topic, 'actual_send_attempted': False})
            raise OSError('Probe proxy deliberately provides no DLQ confirmation; broker remains healthy')

    async def observe_persist(**fields):
        result = await real_persist(**fields)
        persist_returns.append({'run_id': str(fields['run_id']), 'returned': result})
        return result

    ledger.persist_auto_triage = observe_persist

    class ProbeWorker(module.FusedAlertTriageWorker):
        def __init__(self, alias, phase, *, persistence_fault=None, fail_dlq=False):
            item = topics[alias]
            super().__init__(bootstrap_servers=bootstrap, topic=item['topic'], group_id=item['group'],
                             dlq_topic=item['dlq'], max_attempts=1, entity_concurrency=1)
            self.phase, self.persistence_fault, self.fail_dlq = phase, persistence_fault, fail_dlq
            self.results = []

        async def _sink_for(self, investigation, fingerprint):
            sink = await super()._sink_for(investigation, fingerprint)
            assert isinstance(sink, module.ShadowModeTriageWriter), 'Existing test tenant must actually be in shadow mode'
            return sink

        async def triage(self, message):
            assert len(list(E.glob('broker-*-delivery-*.json'))) < 8
            delivery_entries.append({'phase': self.phase, 'input_sha256': digest(message)})
            assert len(delivery_entries) <= 8
            save('broker-' + self.phase + '-delivery-' + str(len(self.results)) + '.json', delivery_entries[-1])
            result = await super().triage(message)
            self.results.append(result)
            return result

        async def _llm_triage(self, investigation):
            existing = list(E.glob('broker-model-substitute-*.json'))
            assert len(existing) < 6
            model_entries.append({'phase': self.phase, 'run_id': str(investigation.run_id), 'actual_model_request': False})
            assert len(model_entries) <= 6
            save('broker-model-substitute-' + str(len(existing)) + '.json', model_entries[-1])
            investigation.verdict, investigation.confidence = 'needs_review', 0.0
            investigation.model_used = 'probe:model-method-substitute:no-model'
            investigation.add_finding('Broker-only model method substitute; no actual model request or incident assessment.')
            investigation.confidence_basis = ['Probe-only delivery observation; no actual model verdict.']
            return investigation, 'probe_model_substitute'

        async def _record(self, investigation, **fields):
            save('broker-' + self.phase + '-before-persist-' + str(len(self.results)) + '.json', {
                'run_id': str(investigation.run_id), 'tier': fields['tier'], 'tokens': fields['tokens'],
                'llm_exchanges': investigation.llm_exchanges,
                **{kind: getattr(investigation, kind) for kind in READS},
                'actual_model_request': False})
            original = ledger.get_pool
            async def unavailable():
                return None
            async def faulting():
                return FaultPool(await real_get_pool(), self.phase)
            if self.persistence_fault == 'false':
                ledger.get_pool = unavailable
            elif self.persistence_fault == 'pg':
                ledger.get_pool = faulting
            try:
                await super()._record(investigation, **fields)
            finally:
                ledger.get_pool = original

        async def _ensure_producer(self):
            if self.fail_dlq:
                return UnconfirmedProducer()
            return await super()._ensure_producer()

    producer = observer = None
    worker = task = None

    async def observe(alias):
        item = topics[alias]
        consumer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=item['group'], enable_auto_commit=False, **security)
        await consumer.start()
        tp = TopicPartition(item['topic'], 0)
        consumer.assign([tp])
        return consumer, tp

    async def launch(alias, phase, **faults):
        worker = ProbeWorker(alias, phase, **faults)
        task = asyncio.create_task(worker.start())
        for _ in range(150):
            if task.done():
                await task
            if worker._consumer and worker._consumer.assignment():
                return worker, task
            await asyncio.sleep(.1)
        raise AssertionError('No bounded worker assignment; inspect checkpoint before any retry')

    async def halt(worker, task, *, expected_persist_error=False):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except ledger.LedgerPersistError:
            assert expected_persist_error
        await worker.stop()

    async def until_commit(consumer, tp, expected, task):
        for _ in range(160):
            if task.done():
                await task
            committed = await consumer.committed(tp)
            if committed == expected:
                return committed
            await asyncio.sleep(.125)
        raise AssertionError('Commit outcome unknown; do not resubmit an input')

    async def publish(alias, value, expected):
        assert len(list(E.glob('broker-*-ack-*.json'))) < 7
        save('broker-' + alias + '-sending-' + str(expected) + '.json', value)
        sent = await producer.send_and_wait(topics[alias]['topic'], value=value, partition=0)
        assert sent.partition == 0 and sent.offset == expected
        coordinate = {'topic': sent.topic, 'partition': sent.partition, 'offset': sent.offset, 'input_sha256': digest(value)}
        save('broker-' + alias + '-ack-' + str(expected) + '.json', coordinate)
        return coordinate

    async def dlq(alias):
        consumer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=None, enable_auto_commit=False, **security)
        await consumer.start()
        try:
            tp = TopicPartition(topics[alias]['dlq'], 0)
            consumer.assign([tp])
            end = (await consumer.end_offsets([tp]))[tp]
            assert 0 <= end <= 1
            if not end:
                return {'messages': [], 'end_offset': 0}
            consumer.seek(tp, 0)
            message = await asyncio.wait_for(consumer.getone(), 10)
            return {'messages': [{'offset': message.offset, 'sha256': hashlib.sha256(message.value).hexdigest(),
                                  'body': json.loads(message.value)}], 'end_offset': end}
        finally:
            await consumer.stop()

    try:
        if mode == 'fallback':
            from app.replay.shadow import ShadowTriageWriter
            payload = fixture['fallback']
            before = await material(payload)
            original_run = module.run_auto_triage
            entries, captured = [], []
            class CaptureWriter(ShadowTriageWriter):
                async def persist_auto_triage(self, **fields):
                    captured.append(fields)
                    await super().persist_auto_triage(**fields)
            capture = CaptureWriter()
            class FallbackWorker(module.FusedAlertTriageWorker):
                async def _sink_for(self, investigation, fingerprint):
                    return capture
            async def controlled_failure(investigation):
                entries.append({'run_id': str(investigation.run_id), 'actual_model_request': False})
                assert len(entries) <= 1
                raise agent.AutoTriageError('Probe-only model method error; not an observed43 outage')
            module.run_auto_triage = controlled_failure
            try:
                result = await FallbackWorker(bootstrap_servers='', writer=capture).triage(payload)
            finally:
                module.run_auto_triage = original_run
            after = await material(payload)
            assert before == after and not any(after['counts'].values())
            assert len(captured) == 1 and captured[0]['raw_alert']['risk_score'] is None
            assert result['tier'] == 'deterministic' and not result['response_dispatched'] and not result['approvals_raised']
            assert len(entries) == 1 and not blocked_model_requests
            assert frozen_source == source_snapshot()
            save('broker-fallback-projection.json', {'result': result, 'captured_persist_fields': captured,
                 'model_method_substitutions': entries, 'actual_model_requests': 0,
                 'production_llm_triage_catch_used': True, 'model_failure_injected_not43outage': True,
                 'capture_writer_not_actual_ledger_verdict': True, 'pg_before': before, 'pg_after': after,
                 'writes_declined_by_capture_writer': dict(capture.calls),
                 'needs_review_condition_met': result['verdict'] == 'needs_review', 'new_broker_messages': 0})
            save('broker-fallback-complete.json', {'source_unchanged': True, 'actual_model_requests': 0,
                 'model_method_substitutions_this_process': len(entries), 'deliveries_this_process': 0,
                 'published_ack_files_so_far': len(list(E.glob('broker-*-ack-*.json'))),
                 'worker_admission_accepted': False})
            print(json.dumps({'mode': mode, 'substitute_entries': 1, 'actual_model_requests': 0, 'persisted_runs': 0,
                              'tier': result['tier'], 'verdict': result['verdict']}))
            return

        fingerprints = {name: module.get_governor().evidence_fingerprint(fixture['tenant_id'], module.build_state(value).raw_alert)
                        for name, value in fixture['inputs'].items()}
        assert len(set(fingerprints.values())) == 4
        if mode == 'run':
            initial_materials = await bounded_materials()
            assert not any(any(value['counts'].values()) for value in initial_materials.values())
            save('broker-pg-before.json', initial_materials)
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap, value_serializer=lambda value: json.dumps(value).encode(), **security)
            await producer.start()
            phases = {}
            # Schema failure is observed honestly: the current worker returns
            # None and may commit without a durable verdict or DLQ.
            observer, tp = await observe('schema')
            worker, task = await launch('schema', 'schema')
            await publish('schema', {}, 0)
            await until_commit(observer, tp, 1, task)
            phases['schema'] = {'committed': 1, 'triage_results': worker.results, 'dlq': await dlq('schema'),
                                'unprocessable_committed_without_dlq': worker.results == [None] and not (await dlq('schema'))['messages']}
            await halt(worker, task); worker = task = None
            await observer.stop(); observer = None

            observer, tp = await observe('ledger-false')
            worker, task = await launch('ledger-false', 'ledger-false', persistence_fault='false')
            await publish('ledger-false', fixture['inputs']['ledger_false'], 0)
            await until_commit(observer, tp, 1, task)
            after_false = await material(fixture['inputs']['ledger_false'])
            phases['ledger_false'] = {'committed': 1, 'pg': after_false, 'triage_results': worker.results,
                                     'persist_returns': list(persist_returns), 'dlq': await dlq('ledger-false'),
                                     'false_ledger_result_committed': not after_false['counts']['runs'] and any(item['returned'] is False for item in persist_returns),
                                     'pool_none_injected_only_during_record': True, 'shared_pg_outage': False}
            await halt(worker, task); worker = task = None
            await observer.stop(); observer = None

            observer, tp = await observe('repeat')
            worker, task = await launch('repeat', 'repeat')
            await publish('repeat', fixture['inputs']['repeat'], 0)
            await until_commit(observer, tp, 1, task)
            first = await material(fixture['inputs']['repeat'])
            first_calls = len(model_entries)
            await publish('repeat', fixture['inputs']['repeat'], 1)
            await until_commit(observer, tp, 2, task)
            warm = await material(fixture['inputs']['repeat'])
            assert first['counts']['runs'] == warm['counts']['runs'] == 1
            assert first['events'] == warm['events'] and first['artifacts'] == warm['artifacts']
            phases['repeat_warm'] = {'committed': 2, 'first': first, 'after': warm,
                                    'model_method_substitutions_after_repeat': len(model_entries) - first_calls,
                                    'results': worker.results, 'first_write_products_preserved': True,
                                    'generic_run_row_changed': first['runs'] != warm['runs'],
                                    'shadow_decision_changed': first['shadow'] != warm['shadow']}
            await halt(worker, task); worker = task = None
            await observer.stop(); observer = None

            observer, tp = await observe('pg-recovery')
            worker, task = await launch('pg-recovery', 'pg-recovery-failed', persistence_fault='pg', fail_dlq=True)
            await publish('pg-recovery', fixture['inputs']['pg_recovery'], 0)
            try:
                await asyncio.wait_for(task, 25)
            except ledger.LedgerPersistError as error:
                failure_type = type(error).__name__
            else:
                raise AssertionError('No-confirmation durability fault did not stop the bounded worker')
            assert await observer.committed(tp) == 0
            rolled_back = await material(fixture['inputs']['pg_recovery'])
            assert not any(rolled_back['counts'].values())
            assert not (await dlq('pg-recovery'))['messages']
            await halt(worker, task, expected_persist_error=True); worker = task = None
            calls_before_recovery = len(model_entries)
            worker, task = await launch('pg-recovery', 'pg-recovery-restored')
            await until_commit(observer, tp, 1, task)
            recovered = await material(fixture['inputs']['pg_recovery'])
            assert recovered['counts']['runs'] == 1 and recovered['counts']['events'] == 1 and recovered['counts']['artifacts'] == 5
            phases['pg_recovery'] = {'failed_committed': 0, 'recovered_committed': 1, 'failure_type': failure_type,
                                     'rolled_back': rolled_back, 'recovered': recovered,
                                     'no_input_resubmitted': True, 'recovered_results': worker.results,
                                     'model_method_substitutions_during_warm_recovery': len(model_entries) - calls_before_recovery,
                                     'cached_retry_source_receipts': [row for row in recovered['artifacts']],
                                     'dlq_failure_is_injected_proxy_not_broker_outage': True}
            await halt(worker, task); worker = task = None
            await observer.stop(); observer = None

            observer, tp = await observe('pg-dlq')
            worker, task = await launch('pg-dlq', 'pg-dlq', persistence_fault='pg')
            await publish('pg-dlq', fixture['inputs']['pg_dlq'], 0)
            await until_commit(observer, tp, 1, task)
            confirmed = await dlq('pg-dlq')
            assert len(confirmed['messages']) == 1
            body = confirmed['messages'][0]['body']
            assert body['failure_stage'] == 'persist' and body['alert_id'] == fixture['inputs']['pg_dlq']['alert_row_id']
            failed_pg = await material(fixture['inputs']['pg_dlq'])
            assert not any(failed_pg['counts'].values())
            phases['pg_confirmed_dlq'] = {'committed': 1, 'dlq': confirmed, 'pg': failed_pg, 'broker_ack_before_commit': True}
            await halt(worker, task); worker = task = None
            await observer.stop(); observer = None
            save('broker-run-observations.json', {'phases': phases, 'model_method_substitutions': model_entries,
                'deliveries': delivery_entries, 'actual_model_requests': 0, 'persist_returns': persist_returns,
                'actual_pg_fault_hits': pg_fault_hits, 'injected_dlq_no_confirmation_hits': dlq_fault_hits,
                'final_pg': await bounded_materials(), 'worker_admission_accepted': False,
                'substitute_is_not_model_chain_quality_proof': True, 'fingerprints': fingerprints})

        elif mode == 'cold-repeat':
            previous = read('broker-run-observations.json')['phases']['repeat_warm']['after']
            before = await material(fixture['inputs']['repeat'])
            assert before == previous
            assert not module.get_governor()._cache, 'Cold mode must use a fresh process, not a cleared old cache'
            observer, tp = await observe('repeat')
            assert await observer.committed(tp) == 2 and (await observer.end_offsets([tp]))[tp] == 2
            worker, task = await launch('repeat', 'repeat-cold')
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap, value_serializer=lambda value: json.dumps(value).encode(), **security)
            await producer.start()
            await publish('repeat', fixture['inputs']['repeat'], 2)
            await until_commit(observer, tp, 3, task)
            after = await material(fixture['inputs']['repeat'])
            assert before['events'] == after['events'] and before['artifacts'] == after['artifacts']
            save('broker-cold-repeat-observations.json', {'committed_before': 2, 'committed_after': 3,
                 'before': before, 'after': after, 'results': worker.results, 'model_method_substitutions': model_entries,
                 'completed_run_did_not_prevent_model_method_reentry': bool(model_entries),
                 'first_write_products_preserved': True, 'generic_run_row_changed': before['runs'] != after['runs'],
                 'actual_model_requests': 0, 'worker_admission_accepted': False})
            await halt(worker, task); worker = task = None

        elif mode == 'restart':
            read('broker-cold-repeat-observations.json')
            before = await bounded_materials()
            observer, tp = await observe('repeat')
            assert await observer.committed(tp) == 3 and (await observer.end_offsets([tp]))[tp] == 3
            worker, task = await launch('repeat', 'restart-idle')
            position = await worker._consumer.position(tp)
            assert position == 3
            await asyncio.sleep(1)
            if task.done():
                await task
            assert not delivery_entries and not model_entries and await observer.committed(tp) == 3
            assert before == await bounded_materials()
            save('broker-restart-observations.json', {'committed': 3, 'position': position, 'new_publishes': 0,
                 'deliveries': 0, 'model_method_substitutions': 0, 'actual_model_requests': 0,
                 'bounded_idle_interval_seconds': 1, 'pg_unchanged': True,
                 'not_rebalance_or_crash_or_long_running_acceptance': True})
            await halt(worker, task); worker = task = None
        assert not blocked_model_requests, 'Unexpected safe-call blocked; inspect instead of claiming no attempt'
        assert frozen_source == source_snapshot()
        save('broker-' + mode + '-complete.json', {'source_unchanged': True, 'actual_model_requests': 0,
             'model_method_substitutions_this_process': len(model_entries), 'deliveries_this_process': len(delivery_entries),
             'published_ack_files_so_far': len(list(E.glob('broker-*-ack-*.json'))), 'worker_admission_accepted': False})
        print(json.dumps({'mode': mode, 'substitute_entries': len(model_entries), 'deliveries': len(delivery_entries),
                          'actual_model_requests': 0, 'worker_admission_accepted': False}))
    finally:
        if task is not None and worker is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, ledger.LedgerPersistError):
                await task
            await worker.stop()
        if observer is not None:
            await observer.stop()
        if producer is not None:
            await producer.stop()
        ledger.get_pool, ledger.persist_auto_triage = real_get_pool, real_persist
        agent.safe_ainvoke = original_safe_call
        await ledger.close_pool()


if __name__ == '__main__':
    assert len(sys.argv) == 2
    asyncio.run(main(sys.argv[1].removeprefix('broker-')))
