"""3A-07 bounded disposition reads, transaction proof and one real model run.

Feedback rows are synthetic read fixtures, not analyst write/compilation
acceptance. Production SQL is exercised through an AST-extracted formatter;
its SAVEPOINT failure is not an HTTP or shared-database outage. A submitted
alert or started model call must never be blindly replayed.
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, '/app')
import httpx
from aiokafka import AIOKafkaConsumer, TopicPartition
from app.agents.auto_triage_agent import _build_alert_context
from app.context import dispositions as dispositions
from app.context import knowledge_base as kb
from app.context import organisation_memory as memory
from app.context import tenant_skills as skills
from app.core.kafka_security import kafka_client_kwargs
from app.investigator import ledger
from app.workers.fused_alert_consumer import FusedAlertTriageWorker, build_state, worker_enabled

E = Path('/evidence')
B = '3a-dispositions-20261020'
CONTEXT_PATH = '/api/v1/feedback/recent-dispositions'
API_SOURCE = Path('/api-feedback.py')


def save(name, value):
    with (E / name).open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
    (E / name).chmod(0o600)


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def instant(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def prompt_messages(content):
    value = json.loads(content)
    assert isinstance(value, list) and value
    return [str(message['content']) for message in value]


def feedback_ids(value, key='dispositions'):
    return [str(row['feedback_id']) for row in value[key]]


def production_sql():
    """Extract only the production literal and its pure formatter, no imports."""
    source = API_SOURCE.read_text()
    tree = ast.parse(source, filename=str(API_SOURCE))
    sql = formatter = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == '_RECENT_DISPOSITIONS_SQL' for target in node.targets):
                sql = ast.literal_eval(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == '_RECENT_DISPOSITIONS_SQL':
            sql = ast.literal_eval(node.value)
        elif isinstance(node, ast.FunctionDef) and node.name == 'recent_dispositions_sql':
            assert not node.decorator_list
            formatter = node
    assert isinstance(sql, str) and formatter is not None
    assert all(node.id in {'cutoff', '_RECENT_DISPOSITIONS_SQL', 'bool', 'str'}
               for node in ast.walk(formatter) if isinstance(node, ast.Name))
    assert all(isinstance(node.func, ast.Attribute) and node.func.attr == 'format'
               for node in ast.walk(formatter) if isinstance(node, ast.Call))
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.Await)) for node in ast.walk(formatter))
    namespace = {'__builtins__': {}, 'bool': bool, 'str': str, '_RECENT_DISPOSITIONS_SQL': sql}
    module = ast.fix_missing_locations(ast.Module(body=[formatter], type_ignores=[]))
    exec(compile(module, str(API_SOURCE), 'exec'), namespace)
    return namespace['recent_dispositions_sql'], sha(source)


def positional(sql, values):
    names = []
    def bind(match):
        name = match.group(1); assert name in values, name
        if name not in names: names.append(name)
        return '$' + str(names.index(name) + 1)
    return re.sub(r'(?<!:):([a-z_][a-z_0-9]*)', bind, sql), [values[name] for name in names]


async def main(mode):
    assert mode in {'before', 'after', 'verify', 'restart'}
    save(mode + '-started.json', {'at': datetime.now(timezone.utc), 'resident_worker_enabled': worker_enabled()})
    assert not worker_enabled()
    state = json.loads(Path('/private/state.json').read_text())
    assert state['batch'] == B
    ids, fixtures = state['identities'], state['feedback']
    tenant_a, tenant_b = ids['a']['tenant_id'], ids['b']['tenant_id']
    rule, entities, split = state['rule_id'], state['entities'], instant(state['split_at'])
    expected_order = [fixtures[alias]['id'] for alias in ['a_after_split', 'a_rule_old', 'a_entity_newer']]
    checks = []
    async with httpx.AsyncClient(base_url='http://api:8000', trust_env=False, timeout=25) as client:
        async def req(method, path, identity='a', *, params=None, body=None, status=200, headers=None):
            auth = {'Authorization': 'Bearer ' + ids[identity]['key']} if identity else {}
            response = await client.request(method, path, params=params, json=body, headers=auth if headers is None else headers)
            checks.append({'method': method, 'path': path, 'params': params, 'identity': identity,
                           'status': response.status_code, 'expected': status})
            log = E / (mode + '-http-checks.json')
            log.write_text(json.dumps(checks, indent=2, default=str)); log.chmod(0o600)
            assert response.status_code == status, (response.status_code, response.text[:150])
            return response.json() if response.content else None

        def parameters(tenant=None, *, query_rule=rule, query_entities=entities, cutoff=None, limit=5):
            value = [('rule_id', query_rule), ('limit', str(limit))]
            if tenant: value.append(('tenant_id', tenant))
            value.extend(('entities', entity) for entity in query_entities)
            if cutoff is not None: value.append(('as_of', cutoff.isoformat()))
            return value

        try:
            if mode == 'before':
                token = os.environ.get('AISOC_AGENTS_SERVICE_TOKEN', '').strip()
                assert token
                await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a), status=401)
                await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401,
                          headers={'X-AiSOC-Service-Token': token})
                dispositions.clear_cache()
                old = await dispositions.fetch_recent_dispositions(tenant_a, rule_id=rule, entities=entities)
                assert not old.decisions
                save('before-acceptance.json', {'checks': checks, 'old_bearer_actual_http_status': 401,
                                              'old_shared_header_actual_http_status': 401,
                                              'old_reader_state': old.as_state(), 'model_invoked': False, 'new_alerts_submitted': 0})
                return

            if mode in {'verify', 'restart'}:
                previous = json.loads((E / 'after-acceptance.json').read_text())
                model_id, probe_id = previous['result']['run_id'], previous['probe_run_id']
                async def read_run(run_id, event_count, artifact_count):
                    base = '/api/v1/investigations/' + run_id
                    run = await req('GET', base)
                    events = await req('GET', base + '/events')
                    artifacts = await req('GET', base + '/artifacts')
                    assert run['status'] == 'completed' and run['event_count'] == event_count
                    assert len(events['items']) == event_count and len(artifacts) == artifact_count
                    details = [await req('GET', base + '/artifacts/' + item['id']) for item in artifacts]
                    verdicts = [item for item in events['items'] if item['kind'] == 'triage_verdict']
                    receipts = [item for item in details if item['kind'] == 'recent_dispositions_read']
                    assert len(verdicts) == len(receipts) == 1
                    adopted = json.loads(receipts[0]['content'])
                    assert adopted == verdicts[0]['payload']['recent_dispositions_read']
                    for artifact in details:
                        blob = artifact['content'].encode()
                        assert artifact['event_id'] == verdicts[0]['id']
                        assert hashlib.sha256(blob).hexdigest() == artifact['sha256'] and len(blob) == artifact['size_bytes']
                    return run, events, artifacts, details, adopted
                run, events, artifacts, details, adopted = await read_run(model_id, 2, 6)
                probe_run, probe_events, probe_artifacts, probe_details, failed = await read_run(probe_id, 1, 1)
                pre = json.loads((E / 'model-before-persist.json').read_text())
                assert adopted == pre['recent_dispositions_read'] and adopted['status'] == 'success'
                assert feedback_ids(adopted, 'decisions') == expected_order
                assert sha(adopted['prompt_block']) == adopted['prompt_sha256']
                prompts = prompt_messages(next(item['content'] for item in details if item['kind'] == 'llm_prompt'))
                assert any(adopted['prompt_block'] in content for content in prompts)
                verdict = next(item for item in events['items'] if item['kind'] == 'triage_verdict')
                for kind in ['organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read']:
                    artifact = next(item for item in details if item['kind'] == kind)
                    assert json.loads(artifact['content']) == verdict['payload'][kind] == pre[kind]
                assert pre['organisation_memory_read']['status'] == 'success'
                assert pre['tenant_skill_read']['status'] == 'success' and pre['tenant_skill_read']['selection']['status'] == 'no_match'
                assert pre['knowledge_base_read']['status'] == 'no_match'
                assert failed == json.loads((E / 'actual-auth-failure-read.json').read_text())
                assert failed['status'] == 'unavailable' and failed['reason'] == 'auth_failed'
                assert not failed['decisions'] and not failed['prompt_block'] and probe_run['total_tokens'] == 0
                assert {item['kind'] for item in artifacts} == {'llm_prompt', 'llm_response', 'organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read', 'recent_dispositions_read'}
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

            a_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a))
            b_http = await req('GET', CONTEXT_PATH, 'reader_b', params=parameters(tenant_b))
            assert a_http['tenant_id'] == tenant_a and b_http['tenant_id'] == tenant_b
            assert feedback_ids(a_http) == expected_order and feedback_ids(b_http) == [fixtures['b_same_rule']['id']]
            assert [row['by_rule'] for row in a_http['dispositions']] == [True, True, False]
            assert all(row['by_entity'] for row in a_http['dispositions'])
            for response, tenant in [(a_http, tenant_a), (b_http, tenant_b)]:
                for row in response['dispositions']:
                    material = {'tenant_id': tenant, **{key: value for key, value in row.items() if key != 'row_source_sha256'}}
                    encoded = json.dumps(material, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                    assert sha(encoded) == row['row_source_sha256']
            assert instant(fixtures['a_entity_newer']['created_at']) > instant(fixtures['a_after_split']['created_at'])
            assert fixtures['a_unmatched']['id'] not in feedback_ids(a_http)
            inferred = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters())
            assert inferred == a_http
            await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_b), status=403)
            await req('GET', CONTEXT_PATH, 'denied', params=parameters(tenant_a), status=403)
            await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401)
            await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401,
                      headers={'Authorization': 'Bearer invalid-acceptance-credential'})
            await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401,
                      headers={'X-AiSOC-Service-Token': os.environ.get('AISOC_AGENTS_SERVICE_TOKEN', '')})
            frozen_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, cutoff=split))
            assert feedback_ids(frozen_http) == [fixtures['a_rule_old']['id']]
            assert frozen_http['excluded_after_cutoff'] == 2 and frozen_http['without_timestamp'] == 0
            all_excluded = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, cutoff=split - timedelta(days=2)))
            assert all_excluded['dispositions'] == [] and all_excluded['excluded_after_cutoff'] == 3
            no_match_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, query_rule='R-DISP-NO-MATCH', query_entities=[]))
            empty_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, query_rule='', query_entities=[]))
            assert no_match_http['dispositions'] == empty_http['dispositions'] == []
            fixture = json.loads(Path('/fixture.json').read_text()); base_alert = fixture['alert']
            forbidden = {**base_alert, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/forbidden-ingress')),
                         'source': 'socai2-' + B, 'source_event_ids': [B + '-forbidden'], 'event_time': datetime.now(timezone.utc).isoformat()}
            await req('POST', '/api/v1/alert-ingress', 'reader_a', body=forbidden, status=403)
            await req('POST', '/api/v1/feedback/alert-override', 'reader_a', status=403,
                      body={'alert_id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/forbidden-feedback')),
                            'original_verdict': 'true_positive', 'corrected_verdict': 'benign_true_positive',
                            'reason': 'Synthetic forbidden-write permission probe', 'reason_code': 'missing_context'})

            dispositions.clear_cache()
            live_a = (await dispositions.fetch_recent_dispositions(tenant_a, rule_id=rule, entities=entities)).as_read()
            cached_a = (await dispositions.fetch_recent_dispositions(tenant_a, rule_id=rule, entities=entities)).as_read()
            live_b = (await dispositions.fetch_recent_dispositions(tenant_b, rule_id=rule, entities=entities)).as_read()
            assert live_a['status'] == live_b['status'] == 'success'
            assert live_a['cache']['source'] == 'network' and cached_a['cache']['source'] == 'memory'
            assert feedback_ids(live_a, 'decisions') == expected_order
            assert feedback_ids(live_b, 'decisions') == [fixtures['b_same_rule']['id']]
            no_match = (await dispositions.fetch_recent_dispositions(tenant_a, rule_id='R-DISP-NO-MATCH')).as_read()
            empty = (await dispositions.fetch_recent_dispositions(tenant_a)).as_read()
            assert no_match['status'] == 'no_match' and empty['status'] == 'not_requested'
            assert not no_match['decisions'] and not empty['decisions']
            original_enabled = os.environ.get('AISOC_TRIAGE_DISPOSITIONS_ENABLED')
            try:
                os.environ['AISOC_TRIAGE_DISPOSITIONS_ENABLED'] = '0'
                disabled = (await dispositions.fetch_recent_dispositions(tenant_a, rule_id=rule, entities=entities)).as_read()
                assert disabled['status'] == 'disabled' and not disabled['decisions']
            finally:
                if original_enabled is None: os.environ.pop('AISOC_TRIAGE_DISPOSITIONS_ENABLED', None)
                else: os.environ['AISOC_TRIAGE_DISPOSITIONS_ENABLED'] = original_enabled
            original_keys_file = os.environ['AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE']
            with tempfile.TemporaryDirectory(prefix='dispositions-probe-') as temporary:
                path = Path(temporary) / 'keys.json'
                with path.open('x') as stream: json.dump({}, stream)
                path.chmod(0o600)
                try:
                    os.environ['AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE'] = str(path)
                    missing = (await dispositions.fetch_recent_dispositions(tenant_a, rule_id=rule, entities=entities)).as_read()
                    assert missing['status'] == 'unavailable' and missing['reason'] == 'not_configured' and not missing['decisions']
                    path.write_text(json.dumps({tenant_a: ids['reader_b']['key']}))
                    wrong_identity = (await dispositions.fetch_recent_dispositions(tenant_a, rule_id=rule, entities=entities)).as_read()
                    assert wrong_identity['status'] == 'unavailable' and wrong_identity['reason'] == 'auth_failed'
                    assert wrong_identity['http_status'] == 403 and not wrong_identity['decisions']
                finally: os.environ['AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE'] = original_keys_file

            pool = await ledger.get_pool(); assert pool is not None
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
            def probe_envelope(label):
                return {'tenant_id': tenant_a, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/selection/' + label)),
                        'alert': {**base_alert, 'source': 'socai2-' + B}}
            async def attach(envelope):
                investigation = build_state(envelope); assert investigation is not None
                await FusedAlertTriageWorker(bootstrap_servers='')._attach_recent_dispositions(investigation)
                return investigation

            original_ttl = dispositions._CACHE_TTL_S
            try:
                await reader_active(False)
                default_cached_revoked = (await dispositions.fetch_recent_dispositions(tenant_a, rule_id=rule, entities=entities)).as_read()
                assert default_cached_revoked['status'] == 'success' and default_cached_revoked['cache']['source'] == 'memory'
                dispositions._CACHE_TTL_S = 0
                revoked_refresh = (await dispositions.fetch_recent_dispositions(tenant_a, rule_id=rule, entities=entities)).as_read()
                assert revoked_refresh['status'] == 'unavailable' and revoked_refresh['reason'] == 'auth_failed'
                assert revoked_refresh['http_status'] == 401 and not revoked_refresh['decisions']
                assert revoked_refresh['cache']['freshness'] == 'expired'
                projection = await attach(probe_envelope('failure'))
                failed_prompt = _build_alert_context(projection, nonce='probe-only')
                auth_failure = deepcopy(projection.recent_dispositions_read)
                assert auth_failure['status'] == 'unavailable' and auth_failure['reason'] == 'auth_failed'
                assert not auth_failure['decisions'] and not auth_failure['prompt_block']
                assert 'status=unavailable' in failed_prompt and 'auth_failed' in failed_prompt
                assert fixtures['a_rule_old']['note'] not in failed_prompt
                save('actual-auth-failure-read.json', auth_failure)
                save('failure-prompt-projection.json', {'model_invoked': False, 'probe_only': True,
                                                       'read': auth_failure, 'context': failed_prompt,
                                                       'does_not_claim_model_saw_failure': True})
            finally:
                await reader_active(True); dispositions._CACHE_TTL_S = original_ttl
            dispositions.clear_cache()
            recovered = (await dispositions.fetch_recent_dispositions(tenant_a, rule_id=rule, entities=entities)).as_read()
            assert recovered['status'] == 'success' and recovered['cache']['source'] == 'network'
            original_url, original_timeout = dispositions._API_URL, dispositions._TIMEOUT_S
            try:
                dispositions._API_URL, dispositions._TIMEOUT_S = 'http://127.0.0.1:1', .5
                transport = (await dispositions.fetch_recent_dispositions(tenant_a, rule_id=rule, entities=entities)).as_read()
                assert transport['status'] == 'unavailable' and transport['reason'] == 'transport_error' and not transport['decisions']
            finally: dispositions._API_URL, dispositions._TIMEOUT_S = original_url, original_timeout
            from app.replay.shadow import ContextSnapshot, FrozenTriageContextReader
            frozen_reader = FrozenTriageContextReader(ContextSnapshot(split_at=split))
            frozen = (await frozen_reader.recent_dispositions(tenant_a, rule_id=rule, entities=entities)).as_read()
            assert frozen['status'] == 'success' and feedback_ids(frozen, 'decisions') == [fixtures['a_rule_old']['id']]
            assert instant(frozen['as_of']) == instant(frozen['requested_as_of']) == split
            assert frozen['excluded_after_cutoff'] == 2 and frozen['without_timestamp'] == 0
            method_note = frozen_reader.as_method_note()
            assert method_note['dispositions_frozen'] == 1 and method_note['dispositions_dropped_after_split'] == 2
            save('read-matrix.json', {'a_http': a_http, 'b_http': b_http, 'a_network': live_a, 'a_cached': cached_a,
                                      'b_network': live_b, 'no_match': no_match, 'empty_input': empty, 'disabled': disabled,
                                      'not_configured': missing, 'wrong_identity': wrong_identity,
                                      'default_cache_after_server_revocation': default_cached_revoked,
                                      'forced_ttl_zero_revoked_refresh': revoked_refresh, 'actual_revoked_key_worker': auth_failure,
                                      'recovery': recovered, 'transport_failure': transport, 'frozen': frozen,
                                      'frozen_method_note': method_note, 'frozen_http': frozen_http,
                                      'all_excluded_http': all_excluded, 'no_match_http': no_match_http, 'empty_http': empty_http,
                                      'created_cutoff_only_not_historical_note_reconstruction': True,
                                      'missing_time_echo_malformed_boundaries_unit_only': True,
                                      'controls_probe_process_only': True, 'model_calls': 0})

            formatter, api_source_hash = production_sql()
            sql, arguments = positional(formatter(cutoff=True), {'tenant_id': uuid.UUID(tenant_a), 'rule_id': rule,
                                                               'entities': entities, 'limit': 5, 'as_of': split})
            async def savepoint_probe(connection):
                pid = await connection.fetchval('SELECT pg_backend_pid()')
                before = [dict(row) for row in await connection.fetch(sql, *arguments)]
                try:
                    async with connection.transaction(): await connection.execute('SELECT 1/0')
                except Exception as error:
                    assert type(error).__name__ == 'DivisionByZeroError'
                    failure = {'exception': type(error).__name__, 'operation': 'SELECT 1/0', 'savepoint_rolled_back': True}
                else: raise AssertionError('Real PG error expected')
                after = [dict(row) for row in await connection.fetch(sql, *arguments)]
                assert before == after and await connection.fetchval('SELECT pg_backend_pid()') == pid
                assert [str(row['feedback_id']) for row in after if row['feedback_id'] is not None] == [fixtures['a_rule_old']['id']]
                assert after[0]['excluded_after_cutoff'] == 2
                return {'source_sha256': api_source_hash, 'sql_sha256': sha(formatter(cutoff=True)), 'source': str(API_SOURCE),
                        'production_formatter_and_statement_used': True, 'backend_pid': pid, 'failure': failure,
                        'before': before, 'after': after, 'same_session_recovered': True,
                        'http_or_shared_database_outage_injected': False, 'api_http_503_propagation_claimed': False}
            save('production-sql-savepoint.json', await scoped(tenant_a, savepoint_probe))

            probe_run_id = uuid.uuid5(uuid.NAMESPACE_URL, B + '/ledger-failure-probe')
            probe_kwargs = {'run_id': probe_run_id, 'alert_id': None, 'tenant_ref': tenant_a,
                            'alert_summary': 'Probe-only recent dispositions transaction recovery',
                            'raw_alert': {'batch': B, 'probe_only': True}, 'tier': 'probe_only',
                            'verdict': 'needs_review', 'confidence': 0.0,
                            'rationale': 'Probe-only transaction test; no model verdict or alert mutation.',
                            'shadow': True, 'recent_dispositions_read': auth_failure}
            async def probe_rows():
                async def read(connection):
                    counts = dict(await connection.fetchrow('SELECT (SELECT count(*) FROM investigation_runs WHERE id=$1) runs,(SELECT count(*) FROM investigation_events WHERE run_id=$1) events,(SELECT count(*) FROM investigation_artifacts WHERE run_id=$1) artifacts', probe_run_id))
                    events = [dict(row) for row in await connection.fetch('SELECT seq,kind,payload FROM investigation_events WHERE run_id=$1 ORDER BY seq', probe_run_id)]
                    artifacts = [dict(row) for row in await connection.fetch('SELECT id,kind,content,sha256,event_id FROM investigation_artifacts WHERE run_id=$1 ORDER BY created_at,id', probe_run_id)]
                    return {'counts': counts, 'events': events, 'artifacts': artifacts}
                return await scoped(tenant_a, read)
            assert (await probe_rows())['counts'] == {'runs': 0, 'events': 0, 'artifacts': 0}
            original_get_pool = ledger.get_pool; fault_hits = []
            class FaultConnection:
                def __init__(self, connection): self.connection = connection
                def __getattr__(self, name): return getattr(self.connection, name)
                async def execute(self, sql, *args):
                    if 'INSERT INTO investigation_artifacts' in sql and len(args) > 4 and args[4] == 'recent_dispositions_read':
                        fault_hits.append('recent_dispositions_read INSERT -> actual SELECT 1/0')
                        return await self.connection.execute('SELECT 1/0')
                    return await self.connection.execute(sql, *args)
            class FaultAcquire:
                async def __aenter__(self):
                    self.acquisition = pool.acquire(); return FaultConnection(await self.acquisition.__aenter__())
                async def __aexit__(self, *args): return await self.acquisition.__aexit__(*args)
            class FaultPool:
                def acquire(self): return FaultAcquire()
            async def failing_pool(): return FaultPool()
            save('ledger-fault-started.json', {'run_id': str(probe_run_id), 'probe_only': True, 'fault': 'actual SELECT 1/0 at recent disposition artifact insert'})
            ledger.get_pool = failing_pool
            try:
                try: await ledger.persist_auto_triage(**probe_kwargs)
                except ledger.LedgerPersistError as error: failure = {'exception': type(error).__name__, 'cause': type(error.__cause__).__name__}
                else: raise AssertionError('Actual PG error swallowed')
            finally: ledger.get_pool = original_get_pool
            assert fault_hits and failure['cause'] == 'DivisionByZeroError'
            rolled_back = await probe_rows(); assert rolled_back['counts'] == {'runs': 0, 'events': 0, 'artifacts': 0}
            assert await ledger.persist_auto_triage(**probe_kwargs)
            first_probe = await probe_rows(); assert first_probe['counts'] == {'runs': 1, 'events': 1, 'artifacts': 1}
            assert decoded(first_probe['events'][0]['payload'])['recent_dispositions_read'] == auth_failure
            assert first_probe['artifacts'][0]['kind'] == 'recent_dispositions_read'
            assert json.loads(first_probe['artifacts'][0]['content']) == auth_failure
            assert await ledger.persist_auto_triage(**probe_kwargs)
            repeated_probe = await probe_rows(); assert repeated_probe == first_probe
            save('ledger-failure-acceptance.json', {'probe_run_id': str(probe_run_id), 'probe_only': True, 'model_invoked': False,
                                                   'failure': failure, 'fault_hits': fault_hits, 'rolled_back': rolled_back,
                                                   'recovered': first_probe, 'same_run_retry': repeated_probe,
                                                   'cost_rows_expected': 0, 'actual_failed_read_persisted': True})

            topic = os.environ['KAFKA_TOPIC_ALERTS_FUSED']
            consumer = AIOKafkaConsumer(topic, bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                        **kafka_client_kwargs(), enable_auto_commit=False, group_id=None)
            await consumer.start()
            try:
                partitions = sorted(consumer.partitions_for_topic(topic) or []); assert partitions
                assigned = [TopicPartition(topic, partition) for partition in partitions]
                consumer.unsubscribe(); consumer.assign(assigned)
                starts = await consumer.end_offsets(assigned)
                for partition, offset in starts.items(): consumer.seek(partition, offset)
                save('fused-read-starts.json', [{'partition': partition.partition, 'offset': offset} for partition, offset in starts.items()])
                body = {**base_alert, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/model-alert')),
                        'source': 'socai2-' + B, 'source_event_ids': [str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/model-event'))],
                        'event_time': datetime.now(timezone.utc).isoformat(), 'tags': [B]}
                save('model-sending.json', body)
                ack = await req('POST', '/api/v1/alert-ingress', body=body, status=202); save('model-ack.json', ack)
                for _ in range(80):
                    response = await client.get('/api/v1/alerts/' + ack['canonical_alert_id'], headers={'Authorization': 'Bearer ' + ids['a']['key']})
                    if response.status_code == 200: break
                    assert response.status_code == 404
                    await asyncio.sleep(.25)
                else: raise AssertionError('Accepted ingress outcome unknown; inspect, never resubmit')
                alert = response.json(); save('model-stored-alert.json', alert)
                fused = coordinate = None
                for _ in range(100):
                    records = await consumer.getmany(timeout_ms=200, max_records=50)
                    for _, messages in records.items():
                        for message in messages:
                            candidate = json.loads(message.value)
                            if str(candidate.get('alert_row_id')) == ack['canonical_alert_id']:
                                assert fused is None and candidate['tenant_id'] == tenant_a
                                fused = candidate
                                coordinate = {'topic': topic, 'partition': message.partition, 'offset': message.offset,
                                              'sha256': hashlib.sha256(message.value).hexdigest()}
                    if fused is not None: break
                assert fused is not None, 'Missing fused result; do not resubmit'
                save('model-fused-envelope.json', fused); save('model-fused-coordinate.json', coordinate)
            finally:
                with contextlib.suppress(asyncio.CancelledError): await consumer.stop()

            # Preflight exact production prompt outside triage: a cap failure
            # must not create a fallback verdict, model call or extra input.
            from app.agents import auto_triage_agent as agent_module
            memory.clear_cache(); skills.clear_cache(); kb.clear_cache(); dispositions.clear_cache()
            budget_state = build_state(fused); assert budget_state is not None
            budget_state.organisation_memory_read = await memory.fetch_organisation_memory(tenant_a)
            budget_state.organisation_memory = list(budget_state.organisation_memory_read['statements'])
            worker = FusedAlertTriageWorker(bootstrap_servers='')
            await worker._attach_tenant_skill(budget_state); await worker._attach_runbooks(budget_state)
            await worker._attach_recent_dispositions(budget_state); await worker._attach_identity_context(budget_state)
            nonce = agent_module.make_nonce()
            context = _build_alert_context(budget_state, nonce=nonce)
            system = agent_module.prompt_text('triage.system') + '\n\n' + agent_module.system_rule(nonce)
            literal = json.dumps([{'role': 'system', 'content': system}, {'role': 'user', 'content': context}], sort_keys=True, default=str)
            assert budget_state.organisation_memory_read['status'] == 'success'
            assert budget_state.tenant_skill_read['status'] == 'success' and budget_state.tenant_skill_read['selection']['status'] == 'no_match'
            assert budget_state.knowledge_base_read['status'] == 'no_match'
            assert budget_state.recent_dispositions_read['status'] == 'success'
            assert feedback_ids(budget_state.recent_dispositions_read, 'decisions') == expected_order
            save('model-prompt-budget-preflight.json', {'literal_limit': 8000, 'literal_chars': len(literal), 'prompt_sha256': sha(literal),
                                                       'recent_dispositions_read': budget_state.recent_dispositions_read,
                                                       'organisation_memory_read': budget_state.organisation_memory_read,
                                                       'tenant_skill_read': budget_state.tenant_skill_read,
                                                       'knowledge_base_read': budget_state.knowledge_base_read,
                                                       'model_invoked': False, 'new_run_persisted': False})
            assert len(literal) <= 8000, 'Prompt literal would be truncated; stop before model, never re-ingress'
            memory.clear_cache(); skills.clear_cache(); kb.clear_cache(); dispositions.clear_cache()
            original_invoke = agent_module.safe_ainvoke
            async def observe(llm, messages, *args, **kwargs):
                save('model-sent-messages.json', [{'role': message.type, 'content': message.content} for message in messages])
                response = await original_invoke(llm, messages, *args, **kwargs)
                metadata = response.response_metadata or {}; headers = metadata.get('headers', {}) or {}
                save('model-metadata.json', {'usage_metadata': response.usage_metadata, 'finish_reason': metadata.get('finish_reason'),
                                             'route': headers.get('x-litellm-model-api-base'), 'model': metadata.get('model_name'),
                                             'response_content': response.content})
                return response
            class ObservedWorker(FusedAlertTriageWorker):
                async def _record(self, investigation, **kwargs):
                    actual = {key: asdict(value) if is_dataclass(value) else value for key, value in kwargs.items() if key != 'writer'}
                    save('model-before-persist.json', {'run_id': str(investigation.run_id), 'raw_alert': investigation.raw_alert,
                                                       'recent_dispositions_read': investigation.recent_dispositions_read,
                                                       'recent_dispositions': investigation.recent_dispositions,
                                                       'organisation_memory_read': investigation.organisation_memory_read,
                                                       'tenant_skill_read': investigation.tenant_skill_read,
                                                       'knowledge_base_read': investigation.knowledge_base_read,
                                                       'exchanges': investigation.llm_exchanges, 'verdict': investigation.verdict,
                                                       'tokens': kwargs.get('tokens', 0), 'tier': kwargs['tier'], 'findings': investigation.findings,
                                                       'model_used': investigation.model_used, 'actual_kwargs': actual,
                                                       'writer_class': type(kwargs['writer']).__name__})
                    await super()._record(investigation, **kwargs)
            agent_module.safe_ainvoke = observe
            try:
                save('model-call-started.json', {'coordinate': coordinate, 'source': 'actual Fusion envelope', 'no_replay_after_this_checkpoint': True})
                result = await ObservedWorker(bootstrap_servers='').triage(fused)
            finally: agent_module.safe_ainvoke = original_invoke
            save('model-worker-result.json', result)
            assert result['shadow'] and result['tier'] == 'llm'
            assert not result['response_dispatched'] and not result['approvals_raised'] and result['source_writeback'] is None
            pre = json.loads((E / 'model-before-persist.json').read_text())
            adopted = pre['recent_dispositions_read']
            messages = json.loads((E / 'model-sent-messages.json').read_text()); contents = [str(message['content']) for message in messages]
            assert adopted['status'] == 'success' and adopted['cache']['source'] == 'network'
            assert feedback_ids(adopted, 'decisions') == expected_order and adopted['adopted_count'] == 3
            assert adopted['prompt_block'] and sha(adopted['prompt_block']) == adopted['prompt_sha256']
            assert any(adopted['prompt_block'] in content for content in contents)
            assert len(adopted['prompt_block']) <= 3000
            for row in adopted['decisions']:
                assert len(row['note']) <= 240 and row['rendered_sha256'] == sha(row['rendered_text'])
                assert row['rendered_text'] in adopted['prompt_block']
                original = next(item for item in a_http['dispositions'] if item['feedback_id'] == row['feedback_id'])
                assert row['row_source_sha256'] == original['row_source_sha256']
            assert pre['organisation_memory_read']['status'] == 'success'
            assert pre['organisation_memory_read']['prompt_block']
            assert any(pre['organisation_memory_read']['prompt_block'] in content for content in contents)
            assert pre['tenant_skill_read']['status'] == 'success' and pre['tenant_skill_read']['selection']['status'] == 'no_match'
            assert pre['knowledge_base_read']['status'] == 'no_match'
            assert not pre['tenant_skill_read']['prompt_block'] and not pre['knowledge_base_read']['prompt_block']
            assert pre['exchanges'] and not pre['exchanges'][0]['prompt_truncated'] and not pre['exchanges'][0]['response_truncated']
            metadata = json.loads((E / 'model-metadata.json').read_text())
            rationale = agent_module._parse_llm_response(str(metadata['response_content']))['rationale']
            observation = {'rationale': rationale, 'verdict': result['verdict'],
                           'adopted_feedback_ids': feedback_ids(adopted, 'decisions'),
                           'exact_note_mentions': [{'feedback_id': row['feedback_id'], 'note': row['note'],
                                                    'exact_note_in_model_rationale': row['note'] in rationale} for row in adopted['decisions']],
                           'feedback_ids_mentioned': [row['feedback_id'] for row in adopted['decisions'] if row['feedback_id'] in rationale],
                           'causal_adoption_or_quality_not_claimed': True, 'no_required_verdict_or_mention': True, 'second_model_call': False}
            save('model-disposition-observation.json', observation)
            save('after-acceptance.json', {'alerts': {'model': alert}, 'result': result, 'probe_run_id': str(probe_run_id), 'checks': checks,
                                          'fused_coordinate': coordinate, 'fused_consumer_group': None, 'fused_reader_commits': False,
                                          'submitted_alerts': 1, 'model_calls': 1, 'actual_model_dispositions_read': adopted,
                                          'actual_model_memory_read': pre['organisation_memory_read'],
                                          'actual_model_skill_read': pre['tenant_skill_read'], 'actual_model_kb_read': pre['knowledge_base_read'],
                                          'model_observation': observation, 'failure_prompt_was_projection_only': True,
                                          'synthetic_feedback_rows_expected': 5, 'created_cutoff_only_not_historical_note_reconstruction': True,
                                          'synthetic_read_fixtures_not_analyst_write_compilation_or_quality_acceptance': True})
        finally:
            await ledger.close_pool()


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1]))
