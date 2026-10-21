"""Bounded3A10-01 real Kafka/PG durability comparison, never a model probe.

Run prepare/before on the immutable3A08 Agents image, then after/restart/verify
on the fixed image. Seven independent topic/group/DLQ sets receive at most
seven new messages and eight deliveries. The sole normal result has actual
five-reader receipts, but its model-method result is an explicit substitute:
no prompt, response, tokens, cost, or real model request is fabricated.
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

sys.path.insert(0, '/app')

B = '3a-triage-durability-20261020'
E = Path('/evidence')
PRIVATE_STATE = Path('/private/state.json')
ALIASES = ('before-schema', 'before-no-pool', 'after-schema', 'after-missing-id',
           'after-unknown-tenant', 'after-no-pool', 'after-normal')
READS = ('organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read',
         'recent_dispositions_read', 'identity_context_read')
PREFIX = 'socai2.test.' + B + '.broker.'
ALLOWED_RUNTIME_CHANGES = {'services/agents/app/workers/fused_alert_consumer.py',
                           'services/agents/app/workers/triage_persistence.py'}
LIMITS = {'new_publishes': 7, 'deliveries': 8, 'model_method_substitutions': 8,
          'new_runs': 1, 'events': 1, 'artifacts': 5, 'cost_rows': 0,
          'real_model_requests': 0}


def save(name, value):
    with (E / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write('\n')
    (E / name).chmod(0o600)


def read(name):
    return json.loads((E / name).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, default=str).encode()).hexdigest()


def source_snapshot():
    app = Path('/app/app')
    assert app.is_dir()
    files = {'services/agents/app/' + str(path.relative_to(app)): sha(path)
             for path in app.rglob('*.py')}
    return {'files_sha256': files, 'aggregate_sha256': digest(files),
            'operator_sha256': sha(__file__),
            'reported_probe_image_id': os.getenv('AISOC_PROBE_IMAGE_ID', 'unknown')}


def fixtures(tenant_id):
    unknown = str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/unknown-tenant'))
    result = {}
    for alias in ALIASES:
        alert_id = str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/' + alias))
        tenant = unknown if alias == 'after-unknown-tenant' else tenant_id
        alert = {'id': alert_id, 'tenant_id': tenant, 'title': 'Broker durability observation',
                 'rule_id': 'R-DUR-' + alias.upper(), 'severity': 'medium',
                 'hostname': 'DUR-' + alias.upper(), 'username': 'svc-durability',
                 'source': B, 'source_event_ids': [B + '/' + alias], 'risk_score': None,
                 'raw_event': {'probe_only': True, 'batch': B, 'no_incident_claim': True},
                 'mitre_techniques': []}
        value = {'id': alert_id, 'alert_row_id': alert_id, 'tenant_id': tenant,
                 'incident_id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/incident/' + alias)),
                 'alert': alert, 'fusion_decision': 'new_incident', 'confidence_score': .1,
                 'narrative': 'Probe-only broker delivery; no incident or model assessment.'}
        if alias.endswith('schema'):
            value = {'probe_batch': B, 'unexpected_schema': True}
        elif alias == 'after-missing-id':
            for key in ('id', 'alert_row_id'): value.pop(key)
            value['alert'].pop('id')
        result[alias] = value
    return result


async def main(mode):
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, OffsetAndMetadata, TopicPartition
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    from app.agents import auto_triage_agent as agent
    from app.core.kafka_security import kafka_client_kwargs
    from app.investigator import ledger
    from app.workers import fused_alert_consumer as module

    assert mode in {'prepare', 'before', 'after', 'restart', 'verify'}
    os.umask(0o077)
    state = json.loads(PRIVATE_STATE.read_text(encoding='utf-8'))
    assert state['batch'] == B
    tenant = str(uuid.UUID(state['identities']['a']['tenant_id']))
    inputs = fixtures(tenant)
    normal = read('normal-fused-envelope.json')
    normal_alert = read('normal-stored-alert.json')
    normal_coordinate = read('normal-fused-coordinate.json')
    normal_id = str(uuid.UUID(normal['alert_row_id']))
    assert normal['tenant_id'] == normal['alert']['tenant_id'] == tenant
    assert normal['id'] == normal['alert']['id'] == normal_id == normal_alert['id']
    assert normal_alert['tenant_id'] == tenant
    assert normal['alert']['source'] == 'socai2-' + B
    assert normal_coordinate['topic'] == 'socai2.alerts.fused'
    inputs['after-normal'] = normal
    assert not module.worker_enabled(), 'Resident worker remains off; this operator constructs bounded workers only'
    assert not module._escalation_enabled() and not module._approvals_enabled()
    assert not module._memory_writeback_enabled(), 'No outcome-prior writes in this broker probe'
    assert not module.alert_trigger.deployment_enabled(), 'The actual production playbook deployment switch must remain off'
    bootstrap = os.environ['KAFKA_BOOTSTRAP_SERVERS']
    security = kafka_client_kwargs()
    topics = {alias: {'topic': PREFIX + alias, 'dlq': PREFIX + alias + '.dlq',
                      'group': PREFIX + alias + '.worker'} for alias in ALIASES}
    source = source_snapshot()
    started = 'durability-' + mode + '-started.json'
    assert not (E / started).exists(), 'Existing checkpoint requires inspection; never blindly replay input'
    if mode != 'prepare':
        config = read('durability-configuration.json')
        assert config['inputs_sha256'] == digest(inputs) and config['topics'] == topics
        assert read('broker-fixtures.json') == inputs
        assert config['normal_capture_sha256'] == {name: sha(E / name) for name in (
            'normal-fused-envelope.json', 'normal-fused-coordinate.json', 'normal-stored-alert.json')}
        old = config['old_image_source']
        assert source['operator_sha256'] == old['operator_sha256']
        if mode == 'before':
            assert source['files_sha256'] == old['files_sha256']
            assert source['reported_probe_image_id'] == state['images']['agents']
        else:
            changes = {name for name in set(source['files_sha256']) | set(old['files_sha256'])
                       if source['files_sha256'].get(name) != old['files_sha256'].get(name)}
            assert changes and changes <= ALLOWED_RUNTIME_CHANGES, changes
            tested = read('tests-acceptance.json')
            deployed = read('deployment.json')
            assert source['files_sha256'] == tested['tested_runtime_source_sha256']
            assert deployed['old_image'] == state['images']['agents']
            assert source['reported_probe_image_id'] == deployed['images']['agents']
            if mode != 'after':
                assert source['files_sha256'] == read('durability-after-complete.json')['source']['files_sha256']
    else:
        assert source['reported_probe_image_id'] == state['images']['agents']
    save(started, {'mode': mode, 'at': datetime.now(timezone.utc), 'source': source,
                   'inputs_sha256': digest(inputs), 'limits': LIMITS,
                   'resident_worker_enabled': False, 'actual_model_requests': 0})

    if mode == 'prepare':
        all_topics = [item[key] for item in topics.values() for key in ('topic', 'dlq')]
        assert len(set(all_topics)) == 14
        admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap,
                                    client_id='socai2-3a10-durability-admin', **security)
        await admin.start()
        try:
            existing = set(await admin.list_topics())
            assert not existing.intersection(all_topics), 'No existing topic, group or offset may be reset'
            await admin.create_topics([NewTopic(name, 1, 1, topic_configs={
                'cleanup.policy': 'delete', 'retention.ms': '604800000'}) for name in all_topics])
        finally:
            await admin.close()
        baseline = {}
        for alias, item in topics.items():
            observer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=item['group'],
                                        enable_auto_commit=False, **security)
            await observer.start()
            try:
                tp = TopicPartition(item['topic'], 0)
                observer.assign([tp])
                assert (await observer.end_offsets([tp]))[tp] == 0 and await observer.committed(tp) is None
                await observer.commit({tp: OffsetAndMetadata(0, 'new-empty-3a10-probe-baseline')})
                assert await observer.committed(tp) == 0
                baseline[alias] = {'end_offset': 0, 'committed': 0}
            finally:
                await observer.stop()
        save('broker-fixtures.json', inputs)
        save('durability-configuration.json', {'batch': B, 'topics': topics, 'baselines': baseline,
            'inputs_sha256': digest(inputs), 'old_image_source': source, 'limits': LIMITS,
            'normal_capture_sha256': {name: sha(E / name) for name in (
                'normal-fused-envelope.json', 'normal-fused-coordinate.json', 'normal-stored-alert.json')},
            'model_method_replacement': 'ProbeWorker._llm_triage, no transcript/usage/safe-call',
            'real_model_requests': 0, 'existing_3a09_topics_or_inputs_used': False})
        print(json.dumps({'mode': mode, 'new_topics': 14, 'new_groups': 7, 'published': 0}))
        return

    real_get_pool, real_persist, real_safe = ledger.get_pool, ledger.persist_auto_triage, agent.safe_ainvoke
    model_entries, delivery_entries, blocked, persist_returns, no_confirmation, dlq_acks = [], [], [], [], [], []
    active_phase = {'value': None}

    async def forbid_model(*args, **kwargs):
        blocked.append({'phase': active_phase['value'], 'safe_call_blocked': True})
        raise RuntimeError('This durability probe forbids real model requests')

    async def observe_persist(**fields):
        item = {'phase': active_phase['value'], 'run_id': str(fields['run_id'])}
        try:
            result = await real_persist(**fields)
        except Exception as exc:
            item['raised'] = type(exc).__name__
            item['cause'] = type(exc.__cause__).__name__ if exc.__cause__ else None
            persist_returns.append(item)
            raise
        item['returned'] = result
        persist_returns.append(item)
        return result

    ledger.persist_auto_triage, agent.safe_ainvoke = observe_persist, forbid_model

    async def material():
        pool = await real_get_pool()
        assert pool is not None
        async with pool.acquire() as connection:
            async with connection.transaction():
                await ledger._set_rls_context(connection, uuid.UUID(tenant))
                runs = await connection.fetch("SELECT row_to_json(t)::text AS material FROM (SELECT * FROM investigation_runs WHERE raw_alert->>'source'=$1 OR case_id=$2) t ORDER BY row_to_json(t)::text", B, normal_id)
                result = {'runs': [json.loads(row['material']) for row in runs]}
                run_ids = [uuid.UUID(row['id']) for row in result['runs']]
                for key, table, column, arguments in (
                    ('events', 'investigation_events', 'run_id', run_ids),
                    ('artifacts', 'investigation_artifacts', 'run_id', run_ids),
                    ('costs', 'aisoc_run_costs', 'run_id', [str(value) for value in run_ids]),
                ):
                    cast = 'text[]' if key == 'costs' else 'uuid[]'
                    rows = await connection.fetch('SELECT row_to_json(t)::text AS material FROM (SELECT * FROM ' + table +
                        ' WHERE ' + column + '=ANY($1::' + cast + ')) t ORDER BY row_to_json(t)::text', arguments)
                    result[key] = [json.loads(row['material']) for row in rows]
                rows = await connection.fetch('SELECT row_to_json(t)::text AS material FROM (SELECT * FROM aisoc_shadow_decisions WHERE source=$1 OR alert_id=$2) t ORDER BY row_to_json(t)::text', B, uuid.UUID(normal_id))
                result['shadow'] = [json.loads(row['material']) for row in rows]
        result['counts'] = {key: len(value) for key, value in result.items()}
        assert result['counts']['runs'] <= 1 and result['counts']['events'] <= 1
        assert result['counts']['artifacts'] <= 5 and result['counts']['costs'] == 0
        async with pool.acquire() as connection:
            async with connection.transaction():
                await ledger._set_rls_context(connection, uuid.UUID(tenant))
                row = await connection.fetchrow('SELECT row_to_json(t)::text AS material FROM (SELECT * FROM alerts WHERE id=$1 AND tenant_id=$2) t',
                                                 uuid.UUID(normal_id), uuid.UUID(tenant))
                assert row is not None, 'Normal delivery must refer to the actual ingressed canonical alert'
                result['normal_alert'] = json.loads(row['material'])
        return result

    class UnconfirmedProducer:
        async def send_and_wait(self, topic, value):
            no_confirmation.append({'phase': active_phase['value'], 'actual_send_attempted': False,
                                    'topic': topic, 'record_sha256': digest(value)})
            raise OSError('Probe provides no DLQ confirmation; actual broker remains healthy')

    class AcknowledgedProducer:
        def __init__(self, delegate, phase):
            self.delegate, self.phase = delegate, phase

        async def send_and_wait(self, topic, value):
            result = await self.delegate.send_and_wait(topic, value=value)
            acknowledgement = {'phase': self.phase, 'topic': result.topic,
                'partition': result.partition, 'offset': result.offset,
                'record_sha256': digest(value), 'broker_ack_monotonic': asyncio.get_running_loop().time()}
            save('durability-dlq-ack-' + self.phase + '.json', acknowledgement)
            dlq_acks.append(acknowledgement)
            return result

    class ProbeWorker(module.FusedAlertTriageWorker):
        def __init__(self, alias, phase, *, no_pool=False, fail_dlq=False):
            item = topics[alias]
            super().__init__(bootstrap_servers=bootstrap, topic=item['topic'], group_id=item['group'],
                             dlq_topic=item['dlq'], max_attempts=1, entity_concurrency=1)
            self.phase, self.no_pool, self.fail_dlq = phase, no_pool, fail_dlq
            self.results = []

        async def _process_with_retry(self, message):
            index = len(list(E.glob('durability-delivery-*.json')))
            assert index < LIMITS['deliveries']
            entry = {'phase': self.phase, 'input_sha256': digest(message), 'index': index}
            save('durability-delivery-' + str(index) + '.json', entry)
            delivery_entries.append(entry)
            active_phase['value'] = self.phase
            try:
                result = await super()._process_with_retry(message)
            except Exception as exc:
                save('durability-' + self.phase + '-process-result.json', {'raised': type(exc).__name__})
                raise
            save('durability-' + self.phase + '-process-result.json', {'returned': result})
            return result

        async def triage(self, message):
            result = await super().triage(message)
            self.results.append(result)
            return result

        async def _sink_for(self, investigation, fingerprint):
            sink = await super()._sink_for(investigation, fingerprint)
            if self.phase == 'after-unknown-tenant':
                # An absent tenant has no shadow-policy row. Do not invent one
                # or replace its real PG FK failure with a probe assertion.
                assert isinstance(sink, module.LiveTriageWriter)
            else:
                assert isinstance(sink, module.ShadowModeTriageWriter), 'Controlled test tenant must remain in shadow mode'
            return sink

        async def _llm_triage(self, investigation):
            index = len(list(E.glob('durability-model-substitute-*.json')))
            assert index < LIMITS['model_method_substitutions']
            entry = {'phase': self.phase, 'run_id': str(investigation.run_id), 'actual_model_request': False}
            save('durability-model-substitute-' + str(index) + '.json', entry)
            model_entries.append(entry)
            investigation.verdict, investigation.confidence = 'needs_review', 0.0
            investigation.model_used = 'probe:model-method-substitute:no-model'
            investigation.add_finding('Probe-only model method substitute; no actual model request or incident assessment.')
            investigation.confidence_basis = ['Broker durability observation only.']
            assert not investigation.llm_exchanges
            return investigation, 'probe_model_substitute'

        async def _record(self, investigation, **fields):
            save('durability-' + self.phase + '-before-persist.json', {
                'run_id': str(investigation.run_id), 'tier': fields['tier'], 'tokens': fields['tokens'],
                'llm_exchanges': investigation.llm_exchanges,
                **{kind: getattr(investigation, kind) for kind in READS}, 'actual_model_request': False})
            original = ledger.get_pool
            async def unavailable():
                return None
            if self.no_pool: ledger.get_pool = unavailable
            try:
                await super()._record(investigation, **fields)
            finally:
                ledger.get_pool = original

        async def _ensure_producer(self):
            if self.fail_dlq: return UnconfirmedProducer()
            actual = await super()._ensure_producer()
            return AcknowledgedProducer(actual, self.phase) if actual is not None else None

    async def observe(alias):
        observer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=topics[alias]['group'],
                                    enable_auto_commit=False, **security)
        await observer.start()
        tp = TopicPartition(topics[alias]['topic'], 0)
        observer.assign([tp])
        return observer, tp

    async def dlq(alias):
        observer = AIOKafkaConsumer(bootstrap_servers=bootstrap, group_id=None, enable_auto_commit=False, **security)
        await observer.start()
        try:
            tp = TopicPartition(topics[alias]['dlq'], 0)
            observer.assign([tp])
            end = (await observer.end_offsets([tp]))[tp]
            assert 0 <= end <= 1
            if end == 0: return {'end_offset': 0, 'messages': []}
            observer.seek(tp, 0)
            message = await asyncio.wait_for(observer.getone(), 10)
            return {'end_offset': end, 'messages': [{'offset': message.offset,
                    'sha256': hashlib.sha256(message.value).hexdigest(), 'body': json.loads(message.value)}]}
        finally:
            await observer.stop()

    async def launch(alias, phase, **faults):
        worker = ProbeWorker(alias, phase, **faults)
        task = asyncio.create_task(worker.start())
        for _ in range(150):
            if task.done(): await task
            if worker._consumer and worker._consumer.assignment(): return worker, task
            await asyncio.sleep(.1)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError): await task
        await worker.stop()
        raise AssertionError('Worker assignment unknown; inspect checkpoint before any recovery')

    async def halt(worker, task, *, persist_error=False):
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        except ledger.LedgerPersistError:
            assert persist_error
        await worker.stop()

    async def until_commit(observer, tp, expected, task):
        for _ in range(160):
            if task.done(): await task
            committed = await observer.committed(tp)
            if committed == expected: return committed
            await asyncio.sleep(.125)
        raise AssertionError('Offset outcome unknown; no input resubmission is authorised')

    producer = observer = worker = task = None

    async def publish(alias):
        assert len(list(E.glob('durability-ack-*.json'))) < LIMITS['new_publishes']
        save('durability-' + alias + '-sending.json', inputs[alias])
        sent = await producer.send_and_wait(topics[alias]['topic'], value=inputs[alias], partition=0)
        assert sent.partition == sent.offset == 0
        save('durability-ack-' + alias + '.json', {'topic': sent.topic, 'partition': sent.partition,
            'offset': sent.offset, 'input_sha256': digest(inputs[alias])})

    async def offsets():
        values = {}
        for alias in ALIASES:
            item, tp = await observe(alias)
            try:
                values[alias] = {'committed': await item.committed(tp),
                                'end_offset': (await item.end_offsets([tp]))[tp], 'dlq': await dlq(alias)}
            finally:
                await item.stop()
        return values

    try:
        if mode in {'before', 'after'}:
            if mode == 'after':
                read('durability-before-complete.json')
            initial = await material()
            assert not any(initial['counts'].values())
            save('durability-' + mode + '-pg-before.json', initial)
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap,
                                        value_serializer=lambda value: json.dumps(value).encode(), **security)
            await producer.start()
            aliases = ALIASES[:2] if mode == 'before' else ALIASES[2:]
            observations = {}
            for alias in aliases:
                observer, tp = await observe(alias)
                assert await observer.committed(tp) == 0 and (await observer.end_offsets([tp]))[tp] == 0
                no_pool = alias.endswith('no-pool')
                unconfirmed = alias == 'after-no-pool'
                worker, task = await launch(alias, alias, no_pool=no_pool, fail_dlq=unconfirmed)
                await publish(alias)
                if unconfirmed:
                    try: await asyncio.wait_for(asyncio.shield(task), 25)
                    except ledger.LedgerPersistError as exc: failure = type(exc).__name__
                    else: raise AssertionError('Unconfirmed DLQ did not retain the failed offset')
                    assert await observer.committed(tp) == 0
                    failed_pg, failed_dlq = await material(), await dlq(alias)
                    assert not any(failed_pg['counts'].values()) and not failed_dlq['messages']
                    await halt(worker, task, persist_error=True); worker = task = None
                    # Re-deliver the same broker message, keep no-pool injected,
                    # and restore only the DLQ producer confirmation.
                    worker, task = await launch(alias, alias + '-dlq-restored', no_pool=True)
                    await until_commit(observer, tp, 1, task)
                    confirmed = await dlq(alias)
                    assert len(confirmed['messages']) == 1
                    assert confirmed['messages'][0]['body']['failure_stage'] == 'persist'
                    assert confirmed['messages'][0]['body']['original'] == inputs[alias]
                    acknowledged = next(item for item in dlq_acks if item['phase'] == alias + '-dlq-restored')
                    assert acknowledged['broker_ack_monotonic'] <= asyncio.get_running_loop().time()
                    observations[alias] = {'failed_committed': 0, 'recovered_committed': 1,
                        'failure_type': failure, 'failed_pg': failed_pg, 'failed_dlq': failed_dlq,
                        'confirmed_dlq': confirmed, 'no_pool_still_injected': True,
                        'only_dlq_confirmation_restored': True, 'input_resubmitted': False,
                        'broker_ack_before_observed_commit': True,
                        'results': worker.results, 'pg': await material()}
                else:
                    await until_commit(observer, tp, 1, task)
                    confirmed = await dlq(alias)
                    current = await material()
                    observation = {'committed': 1, 'results': worker.results, 'dlq': confirmed, 'pg': current}
                    if mode == 'before':
                        assert not confirmed['messages'] and not any(current['counts'].values())
                        if alias == 'before-schema': assert worker.results == [None]
                        else: assert any(item.get('returned') is False for item in persist_returns)
                        observation['old_defect_reproduced'] = True
                    elif alias == 'after-normal':
                        assert not confirmed['messages']
                        assert current['counts'] == {'runs': 1, 'events': 1, 'artifacts': 5, 'costs': 0, 'shadow': 1}
                        assert len(worker.results) == 1 and worker.results[0]['tier'] == 'probe_model_substitute'
                        before = read('durability-after-normal-before-persist.json')
                        assert before['tokens'] == 0 and before['llm_exchanges'] == []
                        assert all(before[kind]['status'] in {'success', 'no_match'} for kind in READS)
                        assert {row['kind'] for row in current['artifacts']} == set(READS)
                        verdict = current['events'][0]
                        payload = verdict['payload']
                        if isinstance(payload, str): payload = json.loads(payload)
                        assert verdict['kind'] == 'triage_verdict'
                        assert current['runs'][0]['case_id'] == normal_id and current['runs'][0]['tenant_id'] == tenant
                        assert current['runs'][0]['raw_alert']['id'] == normal_id
                        for row in current['artifacts']:
                            assert json.loads(row['content']) == before[row['kind']] == payload[row['kind']]
                            assert row['event_id'] == verdict['id']
                            assert row['sha256'] == hashlib.sha256(row['content'].encode()).hexdigest()
                        assert not worker.results[0]['response_dispatched'] and not worker.results[0]['approvals_raised']
                        manual = ('status', 'disposition', 'resolved_at', 'priority', 'tags', 'snoozed_until', 'snoozed_by_id')
                        assert {key: initial['normal_alert'].get(key) for key in manual} == {
                            key: current['normal_alert'].get(key) for key in manual}
                        observation['five_actual_reader_artifacts_equal_payload_and_state'] = True
                        observation['model_method_substitute_not_real_model'] = True
                        observation['normal_alert_manual_columns_preserved'] = True
                        observation['normal_canonical_alert_id'] = normal_id
                    else:
                        assert len(confirmed['messages']) == 1 and not any(current['counts'].values())
                        body = confirmed['messages'][0]['body']
                        assert body['original'] == inputs[alias]
                        assert any(item['phase'] == alias for item in dlq_acks)
                        observation['broker_ack_before_observed_commit'] = True
                        if alias == 'after-unknown-tenant':
                            assert body['failure_stage'] == 'persist'
                            assert any(item['phase'] == alias and item.get('cause') == 'ForeignKeyViolationError'
                                       for item in persist_returns)
                            observation['actual_unknown_uuid_pg_fk_failure'] = True
                            phase_entries = [item for item in model_entries if item['phase'] == alias]
                            observation['model_method_before_unknown_tenant_pg_fk'] = {
                                'status': 'observed' if phase_entries else 'not_observed',
                                'entries': phase_entries,
                                'absence_is_not_proof_of_pre_model_tenant_existence_validation': True}
                        else:
                            assert body['failure_stage'] == 'schema' and body['attempts'] == 1
                            assert isinstance(body['error'], str) and body['error']
                            assert not worker.results
                            assert not any(item['phase'] == alias for item in model_entries)
                            assert not (E / ('durability-' + alias + '-before-persist.json')).exists()
                            observation['rejected_before_triage_model_reader_or_record'] = True
                    observations[alias] = observation
                await halt(worker, task); worker = task = None
                await observer.stop(); observer = None
            final = await material()
            save('durability-' + mode + '-observations.json', {'cases': observations,
                'model_method_substitutions': model_entries, 'deliveries': delivery_entries,
                'persist_returns': persist_returns, 'injected_no_confirmation': no_confirmation,
                'actual_dlq_acknowledgements': dlq_acks,
                'actual_model_requests': 0, 'final_pg': final,
                'worker_admission_accepted': False, 'cold_replay_or_cache_source_retention_fixed': False})
        elif mode == 'restart':
            read('durability-after-complete.json')
            before = await material()
            observer, tp = await observe('after-normal')
            assert await observer.committed(tp) == 1 and (await observer.end_offsets([tp]))[tp] == 1
            worker, task = await launch('after-normal', 'restart-idle')
            position = await worker._consumer.position(tp)
            assert position == 1
            await asyncio.sleep(1)
            if task.done(): await task
            assert not delivery_entries and not model_entries and before == await material()
            save('durability-restart-observations.json', {'committed': await observer.committed(tp),
                'position': position, 'deliveries': 0, 'model_method_substitutions': 0,
                'new_publishes': 0, 'pg_unchanged': True, 'bounded_idle_interval_seconds': 1,
                'not_rebalance_or_crash_or_long_running_acceptance': True})
            await halt(worker, task); worker = task = None
        else:
            read('durability-restart-complete.json')
            current, final_offsets = await material(), await offsets()
            assert current == read('durability-after-observations.json')['final_pg']
            for alias, value in final_offsets.items():
                assert value['committed'] == value['end_offset'] == 1
                dlq_count = 0 if alias in {'before-schema', 'before-no-pool', 'after-normal'} else 1
                assert len(value['dlq']['messages']) == dlq_count
            assert len(list(E.glob('durability-ack-*.json'))) == 7
            assert len(list(E.glob('durability-delivery-*.json'))) == 8
            assert len(list(E.glob('durability-model-substitute-*.json'))) <= 8
            save('durability-verify-observations.json', {'offsets': final_offsets, 'pg': current,
                'new_publishes': 0, 'new_deliveries': 0, 'actual_model_requests': 0,
                'worker_admission_accepted': False})
        assert not blocked, 'Unexpected safe-call was blocked; do not claim an unattempted model path'
        assert source_snapshot() == source
        save('durability-' + mode + '-complete.json', {'source': source,
            'source_unchanged_within_process': True, 'actual_model_requests': 0,
            'model_method_substitutions_this_process': len(model_entries),
            'deliveries_this_process': len(delivery_entries),
            'published_ack_files_so_far': len(list(E.glob('durability-ack-*.json'))),
            'worker_admission_accepted': False})
        print(json.dumps({'mode': mode, 'substitute_entries': len(model_entries),
            'deliveries': len(delivery_entries), 'actual_model_requests': 0, 'worker_admission_accepted': False}))
    finally:
        if worker is not None and task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, ledger.LedgerPersistError): await task
            await worker.stop()
        if observer is not None: await observer.stop()
        if producer is not None: await producer.stop()
        ledger.get_pool, ledger.persist_auto_triage, agent.safe_ainvoke = real_get_pool, real_persist, real_safe
        await ledger.close_pool()


if __name__ == '__main__':
    assert len(sys.argv) == 2
    asyncio.run(main(sys.argv[1].removeprefix('broker-')))
