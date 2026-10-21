"""Checkpointed 3A-04 HTTP/PG memory reads and one actual Fusion/model run.

Probe-only failure controls are confined to this process and marked fixtures.
No accepted ingress or started model call is automatically replayed.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import sys
import tempfile
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '/app')
import httpx
from aiokafka import AIOKafkaConsumer, TopicPartition
from app.agents.auto_triage_agent import _build_alert_context
from app.context import organisation_memory as memory
from app.core.kafka_security import kafka_client_kwargs
from app.investigator import ledger
from app.models.state import InvestigationState
from app.workers.fused_alert_consumer import FusedAlertTriageWorker, worker_enabled

E = Path('/evidence')
B = '3a-org-memory-20261020'
CONTEXT_PATH = '/api/v1/feedback/context-statements'


def save(name, value):
    with (E / name).open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
    (E / name).chmod(0o600)


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


def markers(value):
    return '\n'.join(row['statement'] for row in value['statements'])


async def main(mode):
    assert mode in {'before', 'after', 'verify', 'restart'}
    save(mode + '-started.json', {'at': datetime.now(timezone.utc), 'resident_worker_enabled': worker_enabled()})
    assert not worker_enabled()
    state = json.loads(Path('/private/state.json').read_text())
    assert state['batch'] == B
    ids = state['identities']
    tenant_a = ids['a']['tenant_id']
    tenant_b = ids['b']['tenant_id']
    checks = []
    async with httpx.AsyncClient(base_url='http://api:8000', trust_env=False, timeout=25) as client:
        async def req(method, path, identity='a', body=None, status=200, headers=None):
            auth = {'Authorization': 'Bearer ' + ids[identity]['key']} if identity else {}
            response = await client.request(method, path, headers=auth if headers is None else headers, json=body)
            checks.append({'method': method, 'path': path, 'identity': identity,
                           'status': response.status_code, 'expected': status})
            (E / (mode + '-http-checks.json')).write_text(json.dumps(checks, indent=2))
            assert response.status_code == status, (response.status_code, response.text[:150])
            return response.json()

        try:
            if mode == 'before':
                token = os.environ.get('AISOC_AGENTS_SERVICE_TOKEN', '').strip()
                assert token, 'Existing Agents shared token is required to reproduce its old request'
                await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, None, status=401,
                          headers={'X-AiSOC-Service-Token': token})
                own = await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, 'reader_a')
                denied = await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, 'denied')
                assert own['tenant_id'] == tenant_a and 'ORG-MEMORY-A-VALID' in json.dumps(own)
                assert denied['tenant_id'] == tenant_a
                memory.clear_cache()
                old_rows = await memory.fetch_statements(tenant_a)
                assert old_rows == []
                save('before-acceptance.json', {'checks': checks, 'reader_bearer_result': own,
                                              'old_missing_scope_result': denied,
                                              'old_reader_statements': old_rows,
                                              'old_shared_header_actual_http_status': 401,
                                              'model_invoked': False, 'new_alerts_submitted': 0})
                return

            if mode in {'verify', 'restart'}:
                previous = json.loads((E / 'after-acceptance.json').read_text())
                model_id = previous['result']['run_id']
                probe_id = previous['probe_run_id']

                async def read_run(run_id, events_expected, artifacts_expected):
                    base = '/api/v1/investigations/' + run_id
                    run = await req('GET', base)
                    events = await req('GET', base + '/events')
                    artifacts = await req('GET', base + '/artifacts')
                    assert run['status'] == 'completed' and run['event_count'] == events_expected
                    assert len(events['items']) == events_expected and len(artifacts) == artifacts_expected
                    details = [await req('GET', base + '/artifacts/' + item['id']) for item in artifacts]
                    verdicts = [item for item in events['items'] if item['kind'] == 'triage_verdict']
                    assert len(verdicts) == 1
                    memory_artifacts = [item for item in details if item['kind'] == 'organisation_memory_read']
                    assert len(memory_artifacts) == 1
                    content = json.loads(memory_artifacts[0]['content'])
                    assert content == verdicts[0]['payload']['organisation_memory_read']
                    assert memory_artifacts[0]['event_id'] == verdicts[0]['id']
                    blob = memory_artifacts[0]['content'].encode()
                    assert hashlib.sha256(blob).hexdigest() == memory_artifacts[0]['sha256']
                    assert len(blob) == memory_artifacts[0]['size_bytes']
                    return run, events, artifacts, details, content

                run, events, artifacts, details, adopted = await read_run(model_id, 2, 3)
                probe_run, probe_events, probe_artifacts, probe_details, failed = await read_run(probe_id, 1, 1)
                assert {item['kind'] for item in events['items']} == {'llm_call', 'triage_verdict'}
                assert {item['kind'] for item in artifacts} == {'llm_prompt', 'llm_response', 'organisation_memory_read'}
                assert adopted == json.loads((E / 'model-before-persist.json').read_text())['organisation_memory_read']
                assert failed == json.loads((E / 'actual-auth-failure-read.json').read_text())
                assert failed['status'] == 'unavailable' and failed['reason'] == 'auth_failed' and failed['adopted_count'] == 0
                assert probe_run['total_tokens'] == 0
                current = await req('GET', '/api/v1/alerts/' + previous['alerts']['model']['id'])
                for key in ['raw_event', 'severity', 'status', 'disposition', 'resolved_at', 'priority']:
                    assert current.get(key) == previous['alerts']['model'].get(key), key
                result = {'run': run, 'events': events, 'artifacts': artifacts, 'artifact_details': details,
                          'probe_run': probe_run, 'probe_events': probe_events, 'probe_artifacts': probe_artifacts,
                          'probe_artifact_details': probe_details, 'checks': checks,
                          'manual_alert_state_preserved': True, 'model_invoked': False, 'new_alerts_submitted': 0}
                if mode == 'verify':
                    await req('GET', '/api/v1/investigations/' + model_id, 'b', status=404)
                    await req('GET', '/api/v1/investigations/' + model_id, 'denied', status=403)
                    await req('GET', '/api/v1/investigations/' + model_id, None, status=401)
                    await req('GET', '/api/v1/investigations/' + probe_id, 'b', status=404)
                else:
                    earlier = json.loads((E / 'verify-acceptance.json').read_text())
                    for key in ['run', 'events', 'artifacts', 'artifact_details', 'probe_run', 'probe_events', 'probe_artifacts', 'probe_artifact_details']:
                        assert result[key] == earlier[key], key
                save(mode + '-acceptance.json', result)
                return

            # Public authentication and tenant intersections on the real API.
            initial_a = await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, 'reader_a')
            initial_b = await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_b, 'reader_b')
            assert initial_a['tenant_id'] == tenant_a and 'ORG-MEMORY-A-VALID' in json.dumps(initial_a)
            assert 'EXPIRED' not in json.dumps(initial_a) and initial_b['statements'] == []
            await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_b, 'reader_a', status=403)
            await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, 'denied', status=403)
            await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, None, status=401)
            await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, None, status=401,
                      headers={'Authorization': 'Bearer invalid-acceptance-credential'})
            await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, None, status=401,
                      headers={'X-AiSOC-Service-Token': os.environ.get('AISOC_AGENTS_SERVICE_TOKEN', '')})
            inferred_a = await req('GET', CONTEXT_PATH, 'reader_a')
            assert inferred_a == initial_a
            fixture = json.loads(Path('/fixture.json').read_text())
            base_alert = fixture['alert']
            forbidden = {**base_alert, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/forbidden-ingress')),
                         'source': 'socai2-' + B, 'source_event_ids': [B + '-forbidden'],
                         'event_time': datetime.now(timezone.utc).isoformat()}
            await req('POST', '/api/v1/alert-ingress', 'reader_a', body=forbidden, status=403)

            memory.clear_cache()
            live_a = await memory.fetch_organisation_memory(tenant_a)
            cached_a = await memory.fetch_organisation_memory(tenant_a)
            live_b = await memory.fetch_organisation_memory(tenant_b)
            assert live_a['status'] == 'success' and live_a['cache']['source'] == 'network'
            assert cached_a['cache']['source'] == 'memory' and cached_a['statements'] == live_a['statements']
            assert 'ORG-MEMORY-A-VALID' in markers(live_a) and 'EXPIRED' not in markers(live_a)
            assert live_b['status'] == 'no_match' and not live_b['statements']
            original_enabled = os.environ.get('AISOC_ORG_MEMORY_ENABLED')
            try:
                os.environ['AISOC_ORG_MEMORY_ENABLED'] = '0'
                disabled = await memory.fetch_organisation_memory(tenant_a)
                assert disabled['status'] == 'disabled' and not disabled['statements']
            finally:
                if original_enabled is None:
                    os.environ.pop('AISOC_ORG_MEMORY_ENABLED', None)
                else:
                    os.environ['AISOC_ORG_MEMORY_ENABLED'] = original_enabled
            original_keys_file = os.environ['AISOC_ORG_MEMORY_KEYS_FILE']
            with tempfile.TemporaryDirectory(prefix='org-memory-probe-') as temporary:
                path = Path(temporary) / 'keys.json'
                with path.open('x') as stream:
                    json.dump({}, stream)
                path.chmod(0o600)
                try:
                    os.environ['AISOC_ORG_MEMORY_KEYS_FILE'] = str(path)
                    missing = await memory.fetch_organisation_memory(tenant_a)
                    assert missing['status'] == 'unavailable' and missing['reason'] == 'not_configured' and not missing['statements']
                    path.write_text(json.dumps({tenant_a: ids['reader_b']['key']}))
                    wrong_identity = await memory.fetch_organisation_memory(tenant_a)
                    assert wrong_identity['status'] == 'unavailable' and wrong_identity['reason'] == 'auth_failed'
                    assert wrong_identity['http_status'] == 403 and not wrong_identity['statements']
                finally:
                    os.environ['AISOC_ORG_MEMORY_KEYS_FILE'] = original_keys_file

            pool = await ledger.get_pool()
            assert pool is not None

            async def scoped(tenant, operation):
                async with pool.acquire() as connection:
                    async with connection.transaction():
                        await ledger._set_rls_context(connection, uuid.UUID(tenant))
                        return await operation(connection)

            async def reader_active(active):
                async def update(connection):
                    result = await connection.execute('UPDATE api_keys SET is_active=$1 WHERE id=$2 AND tenant_id=$3',
                                                      active, uuid.UUID(ids['reader_a']['key_id']), uuid.UUID(tenant_a))
                    assert result == 'UPDATE 1'
                await scoped(tenant_a, update)

            # Revoke the actual reader fixture, then refresh its already cached
            # material. TTL change affects this process only, never the service.
            assert (await memory.fetch_organisation_memory(tenant_a))['cache']['source'] == 'memory'
            original_ttl = memory._CACHE_TTL_S
            try:
                await reader_active(False)
                memory._CACHE_TTL_S = 0
                auth_failure = await memory.fetch_organisation_memory(tenant_a)
                save('actual-auth-failure-read.json', auth_failure)
                assert auth_failure['status'] == 'unavailable' and auth_failure['reason'] == 'auth_failed'
                assert auth_failure['http_status'] == 401 and auth_failure['adopted_count'] == 0
                assert auth_failure['cache']['freshness'] == 'expired'
            finally:
                await reader_active(True)
                memory._CACHE_TTL_S = original_ttl
            memory.clear_cache()
            recovered = await memory.fetch_organisation_memory(tenant_a)
            assert recovered['status'] == 'success' and recovered['cache']['source'] == 'network'
            original_url, original_timeout = memory._API_URL, memory._TIMEOUT_S
            try:
                memory._API_URL, memory._TIMEOUT_S = 'http://127.0.0.1:1', .5
                transport = await memory.fetch_organisation_memory(tenant_a)
                assert transport['status'] == 'unavailable' and transport['reason'] == 'transport_error'
                assert transport['adopted_count'] == 0
            finally:
                memory._API_URL, memory._TIMEOUT_S = original_url, original_timeout
            projection = InvestigationState(tenant_id=uuid.UUID(tenant_a),
                                            incident_id=uuid.uuid5(uuid.NAMESPACE_URL, B + '/failure-projection'),
                                            raw_alert={'severity': 'critical', 'probe_only': True},
                                            organisation_memory_read=auth_failure)
            failed_prompt = _build_alert_context(projection, nonce='probe-only')
            assert 'status=unavailable' in failed_prompt and 'auth_failed' in failed_prompt
            assert 'ORG-MEMORY-A-VALID' not in failed_prompt
            save('failure-prompt-projection.json', {'model_invoked': False, 'probe_only': True,
                                                   'read': auth_failure, 'context': failed_prompt,
                                                   'does_not_claim_model_saw_failure': True})

            short_id = uuid.uuid5(uuid.NAMESPACE_URL, B + '/statement-short')
            async def insert_short(connection):
                row = await connection.fetchrow("INSERT INTO aisoc_context_statements(id,tenant_id,statement,reason_code,scope,scope_value,observations,expires_at) VALUES ($1,$2,'SHORT-ORG-MEMORY: synthetic two-second change window.','approved_pentest','entity','short-memory-window',3,now()+interval '2 seconds') RETURNING id,expires_at,created_at",
                                                short_id, uuid.UUID(tenant_a))
                return dict(row)
            short_row = await scoped(tenant_a, insert_short)
            save('short-statement-inserted.json', short_row)
            memory.clear_cache()
            short_active = await memory.fetch_organisation_memory(tenant_a)
            assert short_active['status'] == 'success' and 'SHORT-ORG-MEMORY' in markers(short_active)
            await asyncio.sleep(2.2)
            short_expired_cached = await memory.fetch_organisation_memory(tenant_a)
            assert 'SHORT-ORG-MEMORY' not in markers(short_expired_cached)
            assert short_expired_cached['expired_count'] >= 1 and short_expired_cached['cache']['source'] == 'memory'
            after_expiry_api = await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, 'reader_a')
            assert 'SHORT-ORG-MEMORY' not in json.dumps(after_expiry_api)
            b_id = uuid.uuid5(uuid.NAMESPACE_URL, B + '/statement-b-valid')
            async def insert_b(connection):
                row = await connection.fetchrow("INSERT INTO aisoc_context_statements(id,tenant_id,statement,reason_code,scope,scope_value,observations,expires_at) VALUES ($1,$2,'ORG-MEMORY-B-VALID: tenant B synthetic convention; never tenant A evidence.','expected_service_account','entity','tenant-B-only',2,now()+interval '1 day') RETURNING id,expires_at,created_at",
                                                b_id, uuid.UUID(tenant_b))
                return dict(row)
            b_row = await scoped(tenant_b, insert_b)
            memory.clear_cache()
            isolated_b = await memory.fetch_organisation_memory(tenant_b)
            final_a = await memory.fetch_organisation_memory(tenant_a)
            assert isolated_b['status'] == 'success' and 'ORG-MEMORY-B-VALID' in markers(isolated_b)
            assert 'ORG-MEMORY-A-' not in markers(isolated_b)
            assert 'ORG-MEMORY-B-' not in markers(final_a) and 'SHORT-ORG-MEMORY' not in markers(final_a)
            save('read-matrix.json', {'a_network': live_a, 'a_cached': cached_a, 'b_empty': live_b,
                                      'disabled': disabled, 'not_configured': missing, 'wrong_identity': wrong_identity,
                                      'actual_revoked_key': auth_failure, 'recovery': recovered, 'transport_failure': transport,
                                      'short_active': short_active, 'short_expired_cached': short_expired_cached,
                                      'short_expired_api': after_expiry_api, 'b_valid_inserted': b_row,
                                      'b_isolated': isolated_b, 'a_final': final_a,
                                      'controls_probe_process_only': True, 'model_calls': 0})

            # A real error on the same PG connection/transaction after the
            # verdict INSERT proves its memory artifact cannot commit alone.
            probe_run_id = uuid.uuid5(uuid.NAMESPACE_URL, B + '/ledger-failure-probe')
            probe_kwargs = {'run_id': probe_run_id, 'alert_id': None, 'tenant_ref': tenant_a,
                            'alert_summary': 'Probe-only organisation memory transaction recovery',
                            'raw_alert': {'batch': B, 'probe_only': True}, 'tier': 'probe_only',
                            'verdict': 'needs_review', 'confidence': 0.0,
                            'rationale': 'Probe-only transaction test; no model verdict or alert mutation.',
                            'shadow': True, 'organisation_memory_read': auth_failure}

            async def probe_rows():
                async def read(connection):
                    counts = dict(await connection.fetchrow('SELECT (SELECT count(*) FROM investigation_runs WHERE id=$1) runs,(SELECT count(*) FROM investigation_events WHERE run_id=$1) events,(SELECT count(*) FROM investigation_artifacts WHERE run_id=$1) artifacts', probe_run_id))
                    events = [dict(row) for row in await connection.fetch('SELECT seq,kind,payload FROM investigation_events WHERE run_id=$1 ORDER BY seq', probe_run_id)]
                    artifacts = [dict(row) for row in await connection.fetch('SELECT id,kind,content,sha256,event_id FROM investigation_artifacts WHERE run_id=$1 ORDER BY created_at,id', probe_run_id)]
                    return {'counts': counts, 'events': events, 'artifacts': artifacts}
                return await scoped(tenant_a, read)

            assert (await probe_rows())['counts'] == {'runs': 0, 'events': 0, 'artifacts': 0}
            original_get_pool = ledger.get_pool
            fault_hits = []
            class FaultConnection:
                def __init__(self, connection):
                    self.connection = connection
                def __getattr__(self, name):
                    return getattr(self.connection, name)
                async def execute(self, sql, *args):
                    if 'INSERT INTO investigation_artifacts' in sql and len(args) > 4 and args[4] == 'organisation_memory_read':
                        fault_hits.append('organisation_memory_read INSERT -> actual SELECT 1/0')
                        return await self.connection.execute('SELECT 1/0')
                    return await self.connection.execute(sql, *args)
            class FaultAcquire:
                async def __aenter__(self):
                    self.acquisition = pool.acquire()
                    return FaultConnection(await self.acquisition.__aenter__())
                async def __aexit__(self, *args):
                    return await self.acquisition.__aexit__(*args)
            class FaultPool:
                def acquire(self):
                    return FaultAcquire()
            async def failing_pool():
                return FaultPool()
            save('ledger-fault-started.json', {'run_id': str(probe_run_id), 'probe_only': True,
                                              'fault': 'actual SELECT 1/0 at memory artifact insert'})
            ledger.get_pool = failing_pool
            try:
                try:
                    await ledger.persist_auto_triage(**probe_kwargs)
                except ledger.LedgerPersistError as error:
                    failure = {'exception': type(error).__name__, 'cause': type(error.__cause__).__name__}
                else:
                    raise AssertionError('Actual PG error was swallowed')
            finally:
                ledger.get_pool = original_get_pool
            assert fault_hits and failure['cause'] == 'DivisionByZeroError'
            rolled_back = await probe_rows()
            assert rolled_back['counts'] == {'runs': 0, 'events': 0, 'artifacts': 0}
            assert await ledger.persist_auto_triage(**probe_kwargs)
            first_probe = await probe_rows()
            assert first_probe['counts'] == {'runs': 1, 'events': 1, 'artifacts': 1}
            assert decoded(first_probe['events'][0]['payload'])['organisation_memory_read'] == auth_failure
            assert json.loads(first_probe['artifacts'][0]['content']) == auth_failure
            assert await ledger.persist_auto_triage(**probe_kwargs)
            repeated_probe = await probe_rows()
            assert repeated_probe == first_probe
            save('ledger-failure-acceptance.json', {'probe_run_id': str(probe_run_id), 'probe_only': True,
                                                   'model_invoked': False, 'failure': failure, 'fault_hits': fault_hits,
                                                   'rolled_back': rolled_back, 'recovered': first_probe,
                                                   'same_run_retry': repeated_probe, 'cost_rows_expected': 0,
                                                   'actual_failed_read_persisted': True})

            # Capture the actual new Fusion envelope with no consumer group or
            # commits; do not construct a substitute envelope from the fixture.
            topic = os.environ['KAFKA_TOPIC_ALERTS_FUSED']
            consumer = AIOKafkaConsumer(topic, bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                        **kafka_client_kwargs(), enable_auto_commit=False, group_id=None)
            await consumer.start()
            try:
                partitions = sorted(consumer.partitions_for_topic(topic) or [])
                assert partitions
                assigned = [TopicPartition(topic, partition) for partition in partitions]
                consumer.unsubscribe()
                consumer.assign(assigned)
                starts = await consumer.end_offsets(assigned)
                for partition, offset in starts.items():
                    consumer.seek(partition, offset)
                save('fused-read-starts.json', [{'partition': partition.partition, 'offset': offset} for partition, offset in starts.items()])
                body = {**base_alert, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/model-alert')),
                        'source': 'socai2-' + B, 'source_event_ids': [str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/model-event'))],
                        'event_time': datetime.now(timezone.utc).isoformat(), 'tags': [B]}
                save('model-sending.json', body)
                ack = await req('POST', '/api/v1/alert-ingress', body=body, status=202)
                save('model-ack.json', ack)
                for _ in range(80):
                    response = await client.get('/api/v1/alerts/' + ack['canonical_alert_id'], headers={'Authorization': 'Bearer ' + ids['a']['key']})
                    if response.status_code == 200:
                        break
                    assert response.status_code == 404
                    await asyncio.sleep(.25)
                else:
                    raise AssertionError('Accepted ingress outcome unknown; inspect, never resubmit')
                alert = response.json()
                save('model-stored-alert.json', alert)
                fused = coordinate = None
                for _ in range(100):
                    records = await consumer.getmany(timeout_ms=200, max_records=50)
                    for _, messages in records.items():
                        for message in messages:
                            candidate = json.loads(message.value)
                            if str(candidate.get('alert_row_id')) == ack['canonical_alert_id']:
                                assert fused is None, 'Unexpected second delivery in bounded probe'
                                assert candidate['tenant_id'] == tenant_a
                                fused = candidate
                                coordinate = {'topic': topic, 'partition': message.partition, 'offset': message.offset,
                                              'sha256': hashlib.sha256(message.value).hexdigest()}
                    if fused is not None:
                        break
                assert fused is not None, 'Missing fused result; do not resubmit'
                save('model-fused-envelope.json', fused)
            finally:
                with contextlib.suppress(asyncio.CancelledError):
                    await consumer.stop()
            memory.clear_cache()
            from app.agents import auto_triage_agent as agent_module
            original_invoke = agent_module.safe_ainvoke
            async def observe(llm, messages, *args, **kwargs):
                save('model-sent-messages.json', [{'role': message.type, 'content': message.content} for message in messages])
                response = await original_invoke(llm, messages, *args, **kwargs)
                metadata = response.response_metadata or {}
                headers = metadata.get('headers', {}) or {}
                save('model-metadata.json', {'usage_metadata': response.usage_metadata,
                                             'finish_reason': metadata.get('finish_reason'),
                                             'route': headers.get('x-litellm-model-api-base'), 'model': metadata.get('model_name')})
                return response
            class ObservedWorker(FusedAlertTriageWorker):
                async def _record(self, investigation, **kwargs):
                    actual = {key: asdict(value) if is_dataclass(value) else value for key, value in kwargs.items() if key != 'writer'}
                    save('model-before-persist.json', {'run_id': str(investigation.run_id), 'raw_alert': investigation.raw_alert,
                                                       'organisation_memory_read': investigation.organisation_memory_read,
                                                       'exchanges': investigation.llm_exchanges, 'verdict': investigation.verdict,
                                                       'tokens': kwargs.get('tokens', 0), 'tier': kwargs['tier'],
                                                       'findings': investigation.findings, 'model_used': investigation.model_used,
                                                       'actual_kwargs': actual, 'writer_class': type(kwargs['writer']).__name__})
                    await super()._record(investigation, **kwargs)
            agent_module.safe_ainvoke = observe
            try:
                save('model-call-started.json', {'coordinate': coordinate, 'source': 'actual Fusion envelope',
                                                'no_replay_after_this_checkpoint': True})
                result = await ObservedWorker(bootstrap_servers='').triage(fused)
            finally:
                agent_module.safe_ainvoke = original_invoke
            save('model-worker-result.json', result)
            assert result['shadow'] and result['tier'] == 'llm'
            assert not result['response_dispatched'] and not result['approvals_raised'] and result['source_writeback'] is None
            before_persist = json.loads((E / 'model-before-persist.json').read_text())
            adopted = before_persist['organisation_memory_read']
            sent_messages = json.loads((E / 'model-sent-messages.json').read_text())
            actual_prompt = '\n'.join(str(message['content']) for message in sent_messages)
            assert adopted['status'] == 'success' and adopted['cache']['source'] == 'network'
            assert adopted['adopted_count'] == 1 and 'ORG-MEMORY-A-VALID' in markers(adopted)
            assert adopted['prompt_block'] in actual_prompt and 'status=success' in actual_prompt
            assert not any(marker in actual_prompt for marker in ['ORG-MEMORY-A-EXPIRED', 'ORG-MEMORY-B-', 'SHORT-ORG-MEMORY'])
            assert hashlib.sha256(adopted['prompt_block'].encode()).hexdigest() == adopted['prompt_sha256']
            assert before_persist['exchanges'] and not before_persist['exchanges'][0]['prompt_truncated']
            assert not before_persist['exchanges'][0]['response_truncated']
            save('after-acceptance.json', {'alerts': {'model': alert}, 'result': result,
                                          'probe_run_id': str(probe_run_id), 'checks': checks,
                                          'fused_coordinate': coordinate, 'fused_consumer_group': None,
                                          'fused_reader_commits': False, 'submitted_alerts': 1,
                                          'model_calls': 1, 'failure_prompt_was_projection_only': True,
                                          'actual_model_memory_read': adopted,
                                          'short_statement_id': str(short_id), 'b_valid_statement_id': str(b_id)})
        finally:
            await ledger.close_pool()


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1]))
