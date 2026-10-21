"""Three neutral shadow samples on the current worker, never retrying a model.

Only the probe's constructed ChatOpenAI instances have retries=0/timeout=45.
Production source/defaults, prompt registry, source data and limits are untouched.
Inputs contain no rubric. Source provision and model mentions are observations,
not causal adoption or classification-quality assertions.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import re
import sys
import uuid
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, '/app')
import httpx
from aiokafka import AIOKafkaConsumer, TopicPartition
from app.agents import auto_triage_agent as agent
from app.context import dispositions, identity, knowledge_base, organisation_memory, tenant_skills
from app.core.kafka_security import kafka_client_kwargs
from app.investigator import ledger
from app.llm import contract
from app.workers.fused_alert_consumer import FusedAlertTriageWorker, build_state, worker_enabled

E = Path('/evidence')
B = '3a-triage-admission-20261020'
LIMIT = 8000
READ_KINDS = ('organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read',
              'recent_dispositions_read', 'identity_context_read')
READERS = (organisation_memory, tenant_skills, knowledge_base, dispositions, identity)
FORBIDDEN_KEYS = {'expected', 'expected_verdict', 'test_label', 'rubric', 'scoring_label', 'ground_truth'}


class ProbeStop(BaseException):
    """Stop an operator boundary without converting it to a production fallback."""


def save(name, value):
    with (E / name).open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write('\n')
    (E / name).chmod(0o600)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def check_blind(value):
    if isinstance(value, dict):
        assert not FORBIDDEN_KEYS.intersection(value), 'Scoring metadata is forbidden in model input'
        for item in value.values(): check_blind(item)
    elif isinstance(value, list):
        for item in value: check_blind(item)


def clear_readers():
    for reader in READERS: reader.clear_cache()


def safe_base(value):
    if not value: return None
    text = str(value); parsed = urlsplit(text)
    assert parsed.username is None and parsed.password is None and not parsed.query and not parsed.fragment
    return text


def sdk_settings(llm):
    result = {'model': getattr(llm, 'model_name', None) or getattr(llm, 'model', None),
              'base_url': safe_base(getattr(llm, 'openai_api_base', None) or getattr(llm, 'base_url', None)),
              'max_retries': getattr(llm, 'max_retries', None),
              'request_timeout': str(getattr(llm, 'request_timeout', None))}
    for key in ['root_client', 'root_async_client']:
        client = getattr(llm, key, None)
        result[key] = {'max_retries': getattr(client, 'max_retries', None),
                       'timeout': str(getattr(client, 'timeout', None))}
    return result


def candidate(case_id, item, tenant_id):
    assert set(item) == {'tenant', 'alert'} and isinstance(item['alert'], dict)
    body = deepcopy(item['alert']); check_blind(body)
    assert isinstance(body.get('id'), str) and str(uuid.UUID(body['id'])) == body['id']
    assert isinstance(body.get('source'), str) and body['source'].strip()
    assert isinstance(body.get('source_event_ids'), list) and body['source_event_ids']
    assert all(isinstance(value, str) and value.strip() for value in body['source_event_ids'])
    assert isinstance(body.get('event_time'), str)
    event_time = datetime.fromisoformat(body['event_time'].replace('Z', '+00:00'))
    assert event_time.tzinfo is not None
    return body, {'tenant_id': tenant_id, 'id': body['id'], 'alert_row_id': body['id'], 'alert': deepcopy(body)}


async def prompt_preflight(envelope, prefix):
    clear_readers()
    investigation = build_state(deepcopy(envelope)); assert investigation is not None
    worker = FusedAlertTriageWorker(bootstrap_servers='', max_attempts=1)
    tenant = str(investigation.tenant_id)
    investigation.organisation_memory_read = await organisation_memory.fetch_organisation_memory(tenant)
    investigation.organisation_memory = list(investigation.organisation_memory_read['statements'])
    await worker._attach_tenant_skill(investigation); await worker._attach_runbooks(investigation)
    await worker._attach_recent_dispositions(investigation); await worker._attach_identity_context(investigation)
    nonce = agent.make_nonce()
    context = agent._build_alert_context(investigation, nonce=nonce)
    system = agent.prompt_text('triage.system') + '\n\n' + agent.system_rule(nonce)
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': context}]
    literal = json.dumps(messages, sort_keys=True, default=str)
    check_blind(investigation.raw_alert)
    # The shallow production serializer can omit/cap nested fields. Verify the
    # supplied short evidence summary, rather than assuming its key survived.
    summary = (investigation.raw_alert.get('raw_event') or {}).get('evidence_summary')
    if isinstance(summary, str) and summary:
        assert summary in context, 'Evidence summary omitted or truncated in actual prompt projection'
    reads = {kind: deepcopy(getattr(investigation, kind)) for kind in READ_KINDS}
    for read in reads.values():
        block = read.get('prompt_block', '')
        assert sha(block) == read['prompt_sha256']
        if block: assert block in context
    report = {'messages': messages, 'literal_chars': len(literal), 'literal_limit': LIMIT,
              'literal_sha256': sha(literal), 'within_limit': len(literal) <= LIMIT,
              'nonce_length': len(nonce), 'raw_alert': investigation.raw_alert,
              'reads': reads, 'model_invoked': False, 'run_persisted': False,
              'cache_cleared_in_probe_process_only': True}
    save(prefix + '-prompt-preflight.json', report)
    if len(literal) > LIMIT: raise ProbeStop('Full prompt exceeds preserved cap; no model/input replay')
    return report


async def main(mode):
    assert mode in {'preflight', 'run', 'verify'} and not worker_enabled()
    save(mode + '-started.json', {'at': datetime.now(timezone.utc), 'resident_worker_enabled': False})
    state = json.loads(Path('/private/state.json').read_text())
    inputs_path = Path('/private/inputs.json'); inputs = json.loads(inputs_path.read_text())
    assert state['batch'] == inputs['batch'] == B
    assert state['input_sha256'] == hashlib.sha256(inputs_path.read_bytes()).hexdigest()
    cases = inputs['cases']; ids = state['identities']
    assert isinstance(cases, dict) and len(cases) == 3
    assert all(re.fullmatch(r'(?:p|case)[0-9]{2}', name) for name in cases)
    check_blind(cases)
    checks = []
    async with httpx.AsyncClient(base_url='http://api:8000', trust_env=False, timeout=25) as client:
        async def request(method, path, alias, *, body=None, expected=200):
            auth = {'Authorization': 'Bearer ' + ids[alias]['key']} if alias else {}
            response = await client.request(method, path, json=body, headers=auth)
            checks.append({'method': method, 'path': path, 'identity': alias,
                           'status': response.status_code, 'expected': expected})
            path_log = E / (mode + '-http-checks.json')
            path_log.write_text(json.dumps(checks, indent=2)); path_log.chmod(0o600)
            assert response.status_code == expected, (path, response.status_code, response.text[:100])
            return response.json() if response.content else None

        try:
            if mode == 'preflight':
                reports = {}
                for name, item in cases.items():
                    body, envelope = candidate(name, item, ids[item['tenant']]['tenant_id'])
                    report = await prompt_preflight(envelope, name + '-candidate')
                    default = agent.make_chat_model('triage', temperature=0.0, max_tokens=512, json_output=True)
                    sdk = sdk_settings(default)
                    save(name + '-sdk-default-preflight.json', sdk)
                    reports[name] = {'literal_chars': report['literal_chars'], 'sdk_default': sdk,
                                     'candidate_sha256': sha(json.dumps(body, sort_keys=True))}
                save('preflight-acceptance.json', {'cases': reports, 'input_sha256': hashlib.sha256(inputs_path.read_bytes()).hexdigest(),
                                                   'model_attempts': 0, 'ingress': 0, 'runtime_changed': False})
                return

            if mode == 'verify':
                outputs = {}
                for name, item in cases.items():
                    if not (E / (name + '-worker-result.json')).is_file():
                        outputs[name] = {'not_completed': True,
                                         'ack_exists': (E / (name + '-ack.json')).exists(),
                                         'model_started_exists': (E / (name + '-model-started.json')).exists()}
                        continue
                    result = json.loads((E / (name + '-worker-result.json')).read_text())
                    pre = json.loads((E / (name + '-before-persist.json')).read_text())
                    run_id, alias = result['run_id'], item['tenant']; base = '/api/v1/investigations/' + run_id
                    run = await request('GET', base, alias)
                    events = await request('GET', base + '/events', alias)
                    artifacts = await request('GET', base + '/artifacts', alias)
                    details = [await request('GET', base + '/artifacts/' + row['id'], alias) for row in artifacts]
                    verdicts = [row for row in events['items'] if row['kind'] == 'triage_verdict']; assert len(verdicts) == 1
                    verdict = verdicts[0]; exchange = pre['exchanges']
                    expected_kinds = set(READ_KINDS) | ({'llm_prompt', 'llm_response'} if exchange else set())
                    assert run['status'] == 'completed' and run['event_count'] == len(events['items']) == (2 if exchange else 1)
                    assert {row['kind'] for row in artifacts} == expected_kinds and len(artifacts) == len(expected_kinds)
                    for artifact in details:
                        raw = artifact['content'].encode()
                        assert artifact['event_id'] == verdict['id'] and artifact['sha256'] == hashlib.sha256(raw).hexdigest()
                        assert artifact['size_bytes'] == len(raw)
                    for kind in READ_KINDS:
                        blob = next(row for row in details if row['kind'] == kind)
                        assert json.loads(blob['content']) == verdict['payload'][kind] == pre['reads'][kind]
                    if exchange:
                        prompt = next(row['content'] for row in details if row['kind'] == 'llm_prompt')
                        response = next(row['content'] for row in details if row['kind'] == 'llm_response')
                        sent = json.loads((E / (name + '-sent-messages.json')).read_text())
                        assert json.loads(prompt) == sent and sha(prompt) == exchange[0]['input_hash']
                        assert sha(response) == exchange[0]['output_hash'] and len(prompt) <= LIMIT and len(response) <= LIMIT
                        calls = [row for row in events['items'] if row['kind'] == 'llm_call']; assert len(calls) == 1
                        for event in [calls[0], verdict]:
                            assert event['input_hash'] == exchange[0]['input_hash'] and event['output_hash'] == exchange[0]['output_hash']
                    stored = json.loads((E / (name + '-stored-alert.json')).read_text())
                    current = await request('GET', '/api/v1/alerts/' + stored['id'], alias)
                    for key in ['raw_event', 'severity', 'status', 'disposition', 'resolved_at', 'priority']:
                        assert current.get(key) == stored.get(key), (name, key)
                    pool = await ledger.get_pool(); assert pool is not None
                    async with pool.acquire() as connection:
                        async with connection.transaction():
                            await ledger._set_rls_context(connection, uuid.UUID(ids[alias]['tenant_id']))
                            costs = [dict(row) for row in await connection.fetch('SELECT run_id,total_prompt_tokens,total_completion_tokens,call_count,measured_call_count,estimated_call_count,unpriced_call_count FROM aisoc_run_costs WHERE run_id=$1', str(run_id))]
                    if costs:
                        assert len(costs) == 1
                        assert costs[0]['total_prompt_tokens'] + costs[0]['total_completion_tokens'] == run['total_tokens'] == pre['tokens']
                    elif pre['tokens']:
                        raise AssertionError('Measured tokens have no cost row')
                    usage = None
                    metadata_path = E / (name + '-model-metadata.json')
                    if metadata_path.exists():
                        usage = json.loads(metadata_path.read_text()).get('usage_metadata')
                        if isinstance(usage, dict) and type(usage.get('input_tokens')) is int and type(usage.get('output_tokens')) is int:
                            assert len(costs) == 1 and costs[0]['call_count'] == 1
                            assert costs[0]['total_prompt_tokens'] == usage['input_tokens']
                            assert costs[0]['total_completion_tokens'] == usage['output_tokens']
                    other = 'b' if alias == 'a' else 'a'
                    await request('GET', base, other, expected=404)
                    await request('GET', base, 'denied', expected=403)
                    await request('GET', base, None, expected=401)
                    outputs[name] = {'run': run, 'events': events, 'artifacts': artifacts, 'artifact_details': details,
                                     'cost_rows': costs, 'actual_usage_metadata': usage, 'manual_alert_state_preserved': True}
                save('verify-acceptance.json', {'cases': outputs, 'checks': checks, 'model_attempts': 0,
                                               'new_inputs': 0, 'classification_quality_not_asserted': True})
                return

            accepted = json.loads((E / 'preflight-acceptance.json').read_text())
            assert accepted['input_sha256'] == hashlib.sha256(inputs_path.read_bytes()).hexdigest()
            assert not list(E.glob('*-model-started.json'))
            assert all(not (E / (name + '-ack.json')).exists() and not (E / (name + '-sending.json')).exists() for name in cases)
            results = {}
            for name, item in cases.items():
                alias = item['tenant']; tenant = ids[alias]['tenant_id']
                body, _ = candidate(name, item, tenant)
                topic = os.environ['KAFKA_TOPIC_ALERTS_FUSED']
                consumer = AIOKafkaConsumer(topic, bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                            **kafka_client_kwargs(), enable_auto_commit=False, group_id=None)
                await consumer.start()
                try:
                    assigned = [TopicPartition(topic, partition) for partition in sorted(consumer.partitions_for_topic(topic) or [])]
                    assert assigned; consumer.unsubscribe(); consumer.assign(assigned)
                    starts = await consumer.end_offsets(assigned)
                    for partition, offset in starts.items(): consumer.seek(partition, offset)
                    save(name + '-fused-read-starts.json', [{'partition': key.partition, 'offset': value} for key, value in starts.items()])
                    save(name + '-sending.json', body)
                    ack = await request('POST', '/api/v1/alert-ingress', alias, body=body, expected=202)
                    save(name + '-ack.json', ack)
                    for _ in range(80):
                        response = await client.get('/api/v1/alerts/' + ack['canonical_alert_id'], headers={'Authorization': 'Bearer ' + ids[alias]['key']})
                        if response.status_code == 200: break
                        assert response.status_code == 404; await asyncio.sleep(.25)
                    else: raise ProbeStop('Accepted ingress unknown; read back, never resubmit')
                    stored = response.json(); save(name + '-stored-alert.json', stored)
                    fused = coordinate = None
                    for _ in range(100):
                        records = await consumer.getmany(timeout_ms=200, max_records=50)
                        for messages in records.values():
                            for message in messages:
                                value = json.loads(message.value)
                                if str(value.get('alert_row_id')) == ack['canonical_alert_id']:
                                    assert fused is None and value['tenant_id'] == tenant
                                    fused = value; coordinate = {'topic': topic, 'partition': message.partition,
                                                                  'offset': message.offset, 'sha256': hashlib.sha256(message.value).hexdigest()}
                        if fused is not None: break
                    if fused is None: raise ProbeStop('Fused result unknown; never resubmit')
                    check_blind(fused)
                    save(name + '-fused-envelope.json', fused); save(name + '-fused-coordinate.json', coordinate)
                finally:
                    with contextlib.suppress(asyncio.CancelledError): await consumer.stop()
                await prompt_preflight(fused, name + '-actual')
                clear_readers(); contract._RESPONSE_CACHE.clear()
                original_invoke, original_factory = agent.safe_ainvoke, agent.make_chat_model
                observed = {'factory_calls': 0, 'safe_calls': 0, 'exception': None}

                def factory(*args, **kwargs):
                    if observed['factory_calls']: raise ProbeStop('Unexpected second model construction')
                    observed['factory_calls'] += 1
                    default = original_factory(*args, **kwargs)
                    actual = original_factory(*args, **{**kwargs, 'max_retries': 0, 'request_timeout': 45})
                    before, after = sdk_settings(default), sdk_settings(actual)
                    assert after['max_retries'] == 0
                    assert float(after['request_timeout']) == 45
                    assert all(after[key]['max_retries'] in {0, None} for key in ['root_client', 'root_async_client'])
                    save(name + '-sdk-settings.json', {'default': before, 'probe': after,
                                                     'probe_instance_only': True, 'runtime_defaults_changed': False})
                    return actual

                async def invoke(llm, messages, *args, **kwargs):
                    checkpoint = E / (name + '-model-started.json')
                    if checkpoint.exists() or observed['safe_calls'] or len(list(E.glob('*-model-started.json'))) >= 3:
                        raise ProbeStop('Model attempt already started or batch quota consumed')
                    assert [message.type for message in messages] == ['system', 'human']
                    sent = [{'role': 'system' if message.type == 'system' else 'user', 'content': message.content} for message in messages]
                    literal = json.dumps(sent, sort_keys=True, default=str)
                    save(name + '-sent-messages.json', sent)
                    save(name + '-safe-call-budget.json', {'literal_chars': len(literal), 'literal_limit': LIMIT,
                                                         'literal_sha256': sha(literal), 'within_limit': len(literal) <= LIMIT})
                    if len(literal) > LIMIT: raise ProbeStop('Actual safe-call budget exceeded before model')
                    assert len(literal) <= LIMIT
                    save(name + '-model-started.json', {'at': datetime.now(timezone.utc), 'coordinate': coordinate,
                                                        'literal_sha256': sha(literal), 'attempt': 1,
                                                        'batch_attempt': len(list(E.glob('*-model-started.json'))) + 1,
                                                        'never_retry_unknown': True})
                    observed['safe_calls'] += 1
                    try:
                        response = await original_invoke(llm, messages, *args, **kwargs)
                    except Exception as error:
                        observed['exception'] = type(error).__name__
                        save(name + '-model-exception.json', {'type': type(error).__name__, 'delivery_or_usage': 'unknown',
                                                             'attempt_consumed': True, 'retry_allowed': False})
                        raise
                    metadata = response.response_metadata or {}; headers = metadata.get('headers', {}) or {}
                    save(name + '-model-metadata.json', {'usage_metadata': response.usage_metadata,
                                                         'token_usage': metadata.get('token_usage'),
                                                         'model_name': metadata.get('model_name'),
                                                         'resolved_model': headers.get('x-litellm-response-model') or metadata.get('model_name'),
                                                         'route': safe_base(headers.get('x-litellm-model-api-base')),
                                                         'finish_reason': metadata.get('finish_reason'),
                                                         'headers': {key: value for key, value in headers.items() if key.lower() in {
                                                             'x-litellm-call-id', 'x-litellm-model-id', 'x-litellm-model-api-base',
                                                             'x-litellm-response-cost', 'x-litellm-response-cost-original'}},
                                                         'response_content': response.content,
                                                         'upstream_weights_version': 'unknown'})
                    return response

                class ObservedWorker(FusedAlertTriageWorker):
                    async def _record(self, investigation, **kwargs):
                        save(name + '-before-persist.json', {'run_id': str(investigation.run_id),
                                                            'tenant_id': str(investigation.tenant_id),
                                                            'raw_alert': investigation.raw_alert,
                                                            'reads': {kind: getattr(investigation, kind) for kind in READ_KINDS},
                                                            'exchanges': investigation.llm_exchanges,
                                                            'verdict': investigation.verdict, 'confidence': investigation.confidence,
                                                            'findings': investigation.findings, 'model_used': investigation.model_used,
                                                            'tokens': kwargs.get('tokens', 0), 'tier': kwargs['tier'],
                                                            'cost': {key: asdict(value) if is_dataclass(value) else value for key, value in kwargs.items() if key == 'cost'},
                                                            'writer_class': type(kwargs['writer']).__name__})
                        original_writer = kwargs['writer']
                        class CaptureWriter:
                            async def persist_auto_triage(self, **fields):
                                save(name + '-ledger-input.json', fields)
                                return await original_writer.persist_auto_triage(**fields)
                        kwargs['writer'] = CaptureWriter()
                        await super()._record(investigation, **kwargs)

                agent.make_chat_model, agent.safe_ainvoke = factory, invoke
                try:
                    result = await ObservedWorker(bootstrap_servers='', max_attempts=1).triage(fused)
                finally: agent.make_chat_model, agent.safe_ainvoke = original_factory, original_invoke
                save(name + '-worker-result.json', result)
                assert result['shadow'] and not result['response_dispatched'] and not result['approvals_raised'] and result['source_writeback'] is None
                pre = json.loads((E / (name + '-before-persist.json')).read_text())
                actual_input = json.loads((E / (name + '-ledger-input.json')).read_text())
                assert all(pre['reads'][kind] == actual_input[kind] for kind in READ_KINDS)
                if pre['exchanges']:
                    sent = json.loads((E / (name + '-sent-messages.json')).read_text())
                    prompt = json.dumps(sent, sort_keys=True, default=str)
                    exchange = pre['exchanges'][0]
                    assert not exchange['prompt_truncated'] and not exchange['response_truncated']
                    assert exchange['prompt'] == prompt and exchange['input_hash'] == sha(prompt)
                    for read in pre['reads'].values():
                        block = read.get('prompt_block', '')
                        assert read['prompt_sha256'] == sha(block)
                        if block: assert any(block in message['content'] for message in sent)
                results[name] = {'result': result, 'observed': observed,
                                 'classification_not_asserted': True, 'coordinate': coordinate}
                save(name + '-acceptance.json', results[name])
                if observed['exception']:
                    save('run-halted.json', {'case': name, 'reason': 'model_result_or_delivery_unknown',
                                             'completed_cases': list(results), 'retry_allowed': False})
                    break
            save('run-acceptance.json', {'cases': results, 'checks': checks,
                                         'model_attempts': len(list(E.glob('*-model-started.json'))),
                                         'max_model_attempts': 3, 'per_case_limit': 1,
                                         'fused_reader_group': None, 'fused_reader_commits': False,
                                         'runtime_changed': False, 'classification_quality_not_asserted': True})
        finally:
            await ledger.close_pool()


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1]))
