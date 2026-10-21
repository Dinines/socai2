"""Bounded graph-backed identity acceptance; one input/model, no graph SDK.

Graph fixtures, production-Cypher probes and actual configuration-removal
failure are prepared independently. This operator reads their evidence and
never initializes, migrates or writes the graph. Checkpoints forbid replay
of an accepted input or started model call.
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
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '/app')
import httpx
from aiokafka import AIOKafkaConsumer, TopicPartition
from app.agents.auto_triage_agent import _build_alert_context
from app.context import identity
from app.context import dispositions
from app.context import knowledge_base as kb
from app.context import organisation_memory as memory
from app.context import tenant_skills as skills
from app.core.kafka_security import kafka_client_kwargs
from app.investigator import ledger
from app.workers.fused_alert_consumer import FusedAlertTriageWorker, build_state, worker_enabled

E = Path('/evidence')
B = '3a-identity-read-20261020'
CONTEXT_PATH = '/api/v1/graph/identity-context'
READ_KINDS = ('organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read',
              'recent_dispositions_read', 'identity_context_read')
SOURCE_FIELDS = (
    'identity_id', 'identity_id_kind', 'employee_id', 'employee_id_kind', 'department_id', 'department_id_kind',
    'manager_id', 'manager_id_kind', 'account', 'provider', 'employee', 'title', 'is_active', 'employment_type',
    'start_date', 'end_date', 'imported_at', 'imported_at_status', 'imported_at_raw_sha256', 'department', 'manager',
    'manager_email', 'employee_linked', 'relationship_source',
)


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


def source_hash(tenant, row):
    material = {'tenant_id': tenant, **{field: row[field] for field in SOURCE_FIELDS}}
    return sha(json.dumps(material, sort_keys=True, separators=(',', ':'), ensure_ascii=False))


def identity_ids(read):
    return [row['identity_id'] for row in read['identities']]


def assert_no_material(read, *, reason=None):
    assert read['status'] == 'unavailable'
    if reason is not None:
        assert read['reason'] == reason
    assert read['adopted_count'] == 0 and not read['identities'] and not read['prompt_block']
    assert read['prompt_sha256'] == sha('')


async def main(mode):
    assert mode in {'before', 'after', 'verify', 'restart', 'resume-after-matrix'}
    assert not worker_enabled()
    save(mode + '-started.json', {'at': datetime.now(timezone.utc), 'resident_worker_enabled': False})
    state = json.loads(Path('/private/state.json').read_text())
    assert state['batch'] == B
    ids, graph = state['identities'], state['graph_fixture']
    tenant_a, tenant_b = ids['a']['tenant_id'], ids['b']['tenant_id']
    accounts, split = state['accounts'], instant(state['split_at'])
    assert graph['batch'] == B and graph['tenants'] == {'a': tenant_a, 'b': tenant_b}
    assert accounts == [graph['model_account']] == ['svc-identity-a']
    nodes = {row['alias']: row for row in graph['nodes']}

    def node_id(alias):
        return nodes[alias]['props']['id']

    def assert_model_row(row, tenant):
        for stem in ['identity', 'employee', 'department', 'manager']:
            assert row[stem + '_id'] == node_id(tenant + '-' + stem)
            assert row[stem + '_id_kind'] == 'business_id'
        assert row['account'] == accounts[0] and row['provider'] == 'synthetic-directory'
        assert row['is_active'] is (tenant == 'a') and row['employee_linked']
        assert row['imported_at_status'] == 'native' and row['imported_at']
        assert row['row_source_sha256'] == source_hash(graph['tenants'][tenant], row)

    checks = []
    prior_checks = []
    resume_metadata = None
    async with httpx.AsyncClient(base_url='http://api:8000', trust_env=False, timeout=25) as client:
        async def req(method, path, who='a', *, params=None, body=None, status=200, headers=None):
            auth = {'Authorization': 'Bearer ' + ids[who]['key']} if who else {}
            response = await client.request(method, path, params=params, json=body, headers=auth if headers is None else headers)
            checks.append({'method': method, 'path': path, 'params': params, 'identity': who,
                           'status': response.status_code, 'expected': status})
            log = E / (mode + '-http-checks.json')
            log.write_text(json.dumps(checks, indent=2, default=str)); log.chmod(0o600)
            assert response.status_code == status, (response.status_code, response.text[:150])
            return response.json() if response.content else None

        def parameters(tenant=None, *, query_accounts=accounts, cutoff=None, limit=5):
            value = [('limit', str(limit))]
            if tenant:
                value.append(('tenant_id', tenant))
            value.extend(('accounts', account) for account in query_accounts)
            if cutoff is not None:
                value.append(('as_of', cutoff.isoformat()))
            return value

        try:
            if mode == 'before':
                token = os.environ.get('AISOC_AGENTS_SERVICE_TOKEN', '').strip()
                assert token
                await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a), status=401)
                await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401,
                          headers={'X-AiSOC-Service-Token': token})
                identity.clear_cache()
                old = await identity.fetch_identity_context(tenant_a, accounts=accounts)
                assert not old.identities
                save('before-acceptance.json', {'checks': checks, 'old_bearer_actual_http_status': 401,
                                              'old_shared_header_actual_http_status': 401,
                                              'old_reader_state': old.as_state(), 'model_invoked': False,
                                              'new_alerts_submitted': 0})
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
                    receipts = [item for item in details if item['kind'] == 'identity_context_read']
                    assert len(verdicts) == len(receipts) == 1
                    read = json.loads(receipts[0]['content'])
                    assert read == verdicts[0]['payload']['identity_context_read']
                    for artifact in details:
                        blob = artifact['content'].encode()
                        assert artifact['event_id'] == verdicts[0]['id']
                        assert hashlib.sha256(blob).hexdigest() == artifact['sha256'] and len(blob) == artifact['size_bytes']
                    return run, events, artifacts, details, read

                run, events, artifacts, details, adopted = await read_run(model_id, 2, 7)
                probe_run, probe_events, probe_artifacts, probe_details, failed = await read_run(probe_id, 1, 1)
                pre = json.loads((E / 'model-before-persist.json').read_text())
                assert adopted == pre['identity_context_read'] and adopted['status'] == 'success'
                assert adopted['adopted_count'] == 1 and identity_ids(adopted) == [node_id('a-identity')]
                assert_model_row(adopted['identities'][0], 'a')
                assert sha(adopted['prompt_block']) == adopted['prompt_sha256']
                prompts = prompt_messages(next(row['content'] for row in details if row['kind'] == 'llm_prompt'))
                assert any(adopted['prompt_block'] in content for content in prompts)
                verdict = next(row for row in events['items'] if row['kind'] == 'triage_verdict')
                for kind in READ_KINDS:
                    artifact = next(row for row in details if row['kind'] == kind)
                    assert json.loads(artifact['content']) == verdict['payload'][kind] == pre[kind]
                assert pre['organisation_memory_read']['status'] == 'success'
                assert pre['tenant_skill_read']['status'] == 'success' and pre['tenant_skill_read']['selection']['status'] == 'no_match'
                assert pre['knowledge_base_read']['status'] == pre['recent_dispositions_read']['status'] == 'no_match'
                assert failed == json.loads((E / 'actual-graph-source-failure-read.json').read_text())
                assert_no_material(failed, reason='http_error')
                assert failed['http_status'] == 503 and failed['graph_source_reason'] == 'graph_not_configured'
                assert probe_run['total_tokens'] == 0
                assert {row['kind'] for row in artifacts} == set(READ_KINDS) | {'llm_prompt', 'llm_response'}
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

            assert not (E / 'model-sending.json').exists() and not (E / 'model-call-started.json').exists()
            pool = await ledger.get_pool(); assert pool is not None
            async def scoped(tenant, operation):
                async with pool.acquire() as connection:
                    async with connection.transaction():
                        await ledger._set_rls_context(connection, uuid.UUID(tenant))
                        return await operation(connection)

            if mode == 'resume-after-matrix':
                required = ['after-started.json', 'after-http-checks.json', 'read-state-matrix.json',
                            'actual-graph-source-failure-read.json', 'failure-prompt-projection.json',
                            'graph-config-restored.json']
                assert all((E / name).is_file() for name in required), 'Completed matrix/source-restore checkpoints required'
                assert not any((E / name).exists() for name in [
                    'ledger-fault-started.json', 'ledger-failure-acceptance.json', 'model-ack.json',
                    'model-fused-envelope.json', 'after-acceptance.json']), 'Inspect any later stage; no replay'
                matrix = json.loads((E / 'read-state-matrix.json').read_text())
                assert matrix['model_calls'] == 0 and matrix['no_neo4j_sdk_or_graph_mutation']
                assert matrix['recovery']['status'] == 'success' and matrix['recovery']['cache']['source'] == 'network'
                prior_checks = json.loads((E / 'after-http-checks.json').read_text())
                assert prior_checks and all(row['status'] == row['expected'] for row in prior_checks)
                assert not any(row['status'] == 202 for row in prior_checks)
                a_http = matrix['a_http']
                assert_model_row(a_http['identities'][0], 'a')
                source_failure = matrix['actual_graph_source_failure']
                assert source_failure == json.loads((E / 'actual-graph-source-failure-read.json').read_text())
                assert_no_material(source_failure, reason='http_error')
                assert source_failure['http_status'] == 503 and source_failure['graph_source_reason'] == 'graph_not_configured'
                base_alert = json.loads(Path('/fixture.json').read_text())['alert']
                resume_metadata = {'mode': mode, 'resumes_completed_matrix_without_reexecution': True,
                                   'old_http_checks': len(prior_checks), 'matrix_reexecuted': False,
                                   'key_mutations_reexecuted': False, 'ingress_before_resume': 0,
                                   'model_calls_before_resume': 0,
                                   'prior_checkpoint_sha256': {name: hashlib.sha256((E / name).read_bytes()).hexdigest() for name in required}}
                save('resume-after-matrix-preconditions.json', resume_metadata)
            else:
                a_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a))
                b_http = await req('GET', CONTEXT_PATH, 'reader_b', params=parameters(tenant_b))
                for payload, tenant in [(a_http, 'a'), (b_http, 'b')]:
                    assert payload['tenant_id'] == graph['tenants'][tenant] and payload['accounts'] == accounts
                    assert payload['source_status'] == 'success' and payload['source_reason'] is None
                    assert len(payload['identities']) == payload['candidate_count'] == payload['eligible_count'] == 1
                    assert payload['without_timestamp'] == 1 and payload['truncated_count'] == 0
                    assert_model_row(payload['identities'][0], tenant)
                assert await req('GET', CONTEXT_PATH, 'reader_a', params=parameters()) == a_http
                await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_b), status=403)
                await req('GET', CONTEXT_PATH, 'denied', params=parameters(tenant_a), status=403)
                await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401)
                await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401,
                          headers={'Authorization': 'Bearer invalid-acceptance-credential'})
                await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401,
                          headers={'X-AiSOC-Service-Token': os.environ.get('AISOC_AGENTS_SERVICE_TOKEN', '')})
                no_match_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, query_accounts=['identity-no-match']))
                empty_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, query_accounts=[]))
                assert no_match_http['source_status'] == empty_http['source_status'] == 'no_match'
                assert not no_match_http['identities'] and not empty_http['identities']
                unlinked = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, query_accounts=[graph['unlinked_account']]))
                assert len(unlinked['identities']) == 1
                unlinked_row = unlinked['identities'][0]
                assert unlinked_row['identity_id'] == node_id('a-unlinked') and not unlinked_row['employee_linked']
                assert all(unlinked_row[field] is None for field in ['employee_id', 'department_id', 'manager_id', 'is_active'])
                multi = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, query_accounts=[graph['multi_account']]))
                assert len(multi['identities']) == multi['candidate_count'] == 3
                assert {row['provider'] for row in multi['identities']} == {'synthetic-one', 'synthetic-two'}
                assert {row['employee_id'] for row in multi['identities']} == {node_id('a-multi-employee-' + suffix) for suffix in ['one', 'two', 'three']}
                cross = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, query_accounts=[graph['cross_account']]))
                assert len(cross['identities']) == 1 and cross['identities'][0]['identity_id'] == node_id('a-cross-identity')
                assert not cross['identities'][0]['employee_linked'] and cross['identities'][0]['employee_id'] is None
                for payload in [unlinked, multi, cross]:
                    for row in payload['identities']:
                        assert row['row_source_sha256'] == source_hash(tenant_a, row)
                        for stem in ['identity', 'employee', 'department', 'manager']:
                            assert row[stem + '_id'] is None or row[stem + '_id'] in {
                                item['props']['id'] for item in graph['nodes'] if item['props']['tenant_id'] == tenant_a}
                cutoff_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, query_accounts=[graph['cutoff_account']], cutoff=split, limit=1))
                assert len(cutoff_http['identities']) == 1 and cutoff_http['identities'][0]['employee_id'] == node_id('a-cutoff-90-early')
                assert instant(cutoff_http['as_of']) == split
                for key, expected in [('candidate_count', 7), ('eligible_count', 1), ('truncated_count', 0),
                                      ('excluded_after_cutoff', 3), ('excluded_unverifiable_import', 3),
                                      ('import_timestamp_missing', 1), ('without_timestamp', 1)]:
                    assert cutoff_http[key] == expected, key
                fixture = json.loads(Path('/fixture.json').read_text()); base_alert = fixture['alert']
                forbidden = {**base_alert, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/forbidden-ingress')),
                             'source': 'socai2-' + B, 'source_event_ids': [B + '-forbidden'],
                             'event_time': datetime.now(timezone.utc).isoformat()}
                await req('POST', '/api/v1/alert-ingress', 'reader_a', body=forbidden, status=403)
                await req('POST', '/api/v1/graph/context/import', 'reader_a', body={}, status=403)

                identity.clear_cache()
                live_a = (await identity.fetch_identity_context(tenant_a, accounts=accounts)).as_read()
                cached_a = (await identity.fetch_identity_context(tenant_a, accounts=accounts)).as_read()
                live_b = (await identity.fetch_identity_context(tenant_b, accounts=accounts)).as_read()
                assert identity._CACHE_TTL_S == 300 and live_a['cache']['ttl_seconds'] == 300
                assert live_a['status'] == live_b['status'] == 'success'
                assert live_a['cache']['source'] == 'network' and cached_a['cache']['source'] == 'memory'
                assert_model_row(live_a['identities'][0], 'a'); assert_model_row(live_b['identities'][0], 'b')
                no_match = (await identity.fetch_identity_context(tenant_a, accounts=['identity-no-match'])).as_read()
                empty = (await identity.fetch_identity_context(tenant_a, accounts=[])).as_read()
                assert no_match['status'] == 'no_match' and empty['status'] == 'not_requested' and empty['reason'] == 'empty_accounts'
                assert not no_match['identities'] and not empty['identities']
                original_enabled = os.environ.get('AISOC_TRIAGE_IDENTITY_ENABLED')
                try:
                    os.environ['AISOC_TRIAGE_IDENTITY_ENABLED'] = '0'
                    disabled = (await identity.fetch_identity_context(tenant_a, accounts=accounts)).as_read()
                    assert disabled['status'] == 'disabled' and not disabled['identities']
                finally:
                    if original_enabled is None: os.environ.pop('AISOC_TRIAGE_IDENTITY_ENABLED', None)
                    else: os.environ['AISOC_TRIAGE_IDENTITY_ENABLED'] = original_enabled
                original_keys_file = os.environ['AISOC_TRIAGE_IDENTITY_KEYS_FILE']
                with tempfile.TemporaryDirectory(prefix='identity-probe-') as temporary:
                    path = Path(temporary) / 'keys.json'
                    with path.open('x') as stream: json.dump({}, stream)
                    path.chmod(0o600)
                    try:
                        os.environ['AISOC_TRIAGE_IDENTITY_KEYS_FILE'] = str(path)
                        missing = (await identity.fetch_identity_context(tenant_a, accounts=accounts)).as_read()
                        assert_no_material(missing, reason='not_configured')
                        path.write_text(json.dumps({tenant_a: ids['reader_b']['key']}))
                        wrong_identity = (await identity.fetch_identity_context(tenant_a, accounts=accounts)).as_read()
                        assert_no_material(wrong_identity, reason='auth_failed')
                        assert wrong_identity['http_status'] == 403
                    finally: os.environ['AISOC_TRIAGE_IDENTITY_KEYS_FILE'] = original_keys_file

                async def reader_active(active):
                    async def update(connection):
                        result = await connection.execute('UPDATE api_keys SET is_active=$1 WHERE id=$2 AND tenant_id=$3',
                                                          active, uuid.UUID(ids['reader_a']['key_id']), uuid.UUID(tenant_a))
                        assert result == 'UPDATE 1'
                    await scoped(tenant_a, update)

                original_ttl = identity._CACHE_TTL_S
                try:
                    await reader_active(False)
                    default_cached_revoked = (await identity.fetch_identity_context(tenant_a, accounts=accounts)).as_read()
                    assert default_cached_revoked['status'] == 'success' and default_cached_revoked['cache']['source'] == 'memory'
                    identity._CACHE_TTL_S = 0
                    revoked_refresh = (await identity.fetch_identity_context(tenant_a, accounts=accounts)).as_read()
                    assert_no_material(revoked_refresh, reason='auth_failed')
                    assert revoked_refresh['http_status'] == 401 and revoked_refresh['cache']['freshness'] == 'expired'
                    projection = build_state({'tenant_id': tenant_a, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/auth-projection')),
                                              'alert': {**base_alert, 'source': 'socai2-' + B}})
                    assert projection is not None
                    await FusedAlertTriageWorker(bootstrap_servers='')._attach_identity_context(projection)
                    auth_failure = deepcopy(projection.identity_context_read)
                    assert_no_material(auth_failure, reason='auth_failed')
                    failed_prompt = _build_alert_context(projection, nonce='probe-only')
                    assert 'status=unavailable' in failed_prompt and 'auth_failed' in failed_prompt
                    assert 'Synthetic A account owner' not in failed_prompt
                    save('actual-auth-failure-read.json', auth_failure)
                    save('auth-failure-prompt-projection.json', {'model_invoked': False, 'probe_only': True,
                                                              'read': auth_failure, 'context': failed_prompt,
                                                              'does_not_claim_model_saw_failure': True})
                finally:
                    await reader_active(True); identity._CACHE_TTL_S = original_ttl
                identity.clear_cache()
                recovered = (await identity.fetch_identity_context(tenant_a, accounts=accounts)).as_read()
                assert recovered['status'] == 'success' and recovered['cache']['source'] == 'network'
                original_url, original_timeout = identity._API_URL, identity._TIMEOUT_S
                try:
                    identity._API_URL, identity._TIMEOUT_S = 'http://127.0.0.1:1', .5
                    transport = (await identity.fetch_identity_context(tenant_a, accounts=accounts)).as_read()
                    assert_no_material(transport, reason='transport_error')
                finally: identity._API_URL, identity._TIMEOUT_S = original_url, original_timeout
                from app.replay.shadow import ContextSnapshot, FrozenTriageContextReader
                frozen_reader = FrozenTriageContextReader(ContextSnapshot(split_at=split))
                frozen = (await frozen_reader.fetch_identity_context(tenant_a, accounts=[graph['cutoff_account']])).as_read()
                assert frozen['status'] == 'success' and frozen['adopted_count'] == 1
                assert frozen['identities'][0]['employee_id'] == node_id('a-cutoff-90-early')
                assert instant(frozen['as_of']) == instant(frozen['requested_as_of']) == split
                assert frozen['excluded_after_cutoff'] == frozen['excluded_unverifiable_import'] == 3
                assert frozen['candidate_count'] == 7 and frozen['eligible_count'] == 1
                assert frozen['without_timestamp'] == frozen['adopted_without_timestamp'] == 1
                assert frozen['import_cutoff_only'] and not frozen['business_history_verified']
                method_note = frozen_reader.as_method_note()
                assert method_note['identities_frozen'] == method_note['identities_without_timestamp'] == 1
                assert method_note['identities_dropped_after_split'] == method_note['identities_excluded_unverifiable_import'] == 3
                source_failure = json.loads((E / 'actual-graph-source-failure-read.json').read_text())
                assert_no_material(source_failure, reason='http_error')
                assert source_failure['tenant_id'] == tenant_a and source_failure['accounts'] == accounts
                assert source_failure['http_status'] == 503 and source_failure['graph_source_status'] == 'unavailable'
                assert source_failure['graph_source_reason'] == 'graph_not_configured'
                assert source_failure['candidate_count'] == source_failure['eligible_count'] == 0
                source_projection = json.loads((E / 'failure-prompt-projection.json').read_text())
                assert source_projection['read'] == source_failure and not source_projection['model_invoked']
                assert source_projection['probe_only'] and source_projection['does_not_claim_model_saw_failure']
                assert 'graph_not_configured' in source_projection['context']
                save('read-state-matrix.json', {'a_network': live_a, 'a_cached': cached_a, 'b_network': live_b,
                                              'no_match': no_match, 'empty_input': empty, 'disabled': disabled,
                                              'not_configured': missing, 'wrong_identity': wrong_identity,
                                              'default_cache_after_server_revocation': default_cached_revoked,
                                              'forced_ttl_zero_revoked_refresh': revoked_refresh,
                                              'actual_revoked_key_worker': auth_failure, 'recovery': recovered,
                                              'transport_failure': transport, 'actual_graph_source_failure': source_failure,
                                              'frozen': frozen, 'frozen_method_note': method_note,
                                              'a_http': a_http, 'b_http': b_http, 'cutoff_limit_one_http': cutoff_http,
                                              'unlinked_http': unlinked, 'multi_http': multi, 'cross_http': cross,
                                              'no_match_http': no_match_http, 'empty_http': empty_http,
                                              'import_cutoff_only_not_business_history': True,
                                              'malformed_echo_long_text_boundaries_unit_only': True,
                                              'no_neo4j_sdk_or_graph_mutation': True, 'model_calls': 0})

            probe_run_id = uuid.uuid5(uuid.NAMESPACE_URL, B + '/ledger-failure-probe')
            probe_kwargs = {'run_id': probe_run_id, 'alert_id': None, 'tenant_ref': tenant_a,
                            'alert_summary': 'Probe-only identity source failure transaction recovery',
                            'raw_alert': {'batch': B, 'probe_only': True}, 'tier': 'probe_only',
                            'verdict': 'needs_review', 'confidence': 0.0,
                            'rationale': 'Probe-only transaction test; no model verdict or alert mutation.',
                            'shadow': True, 'identity_context_read': source_failure}

            async def probe_rows():
                async def read(connection):
                    counts = dict(await connection.fetchrow('SELECT (SELECT count(*) FROM investigation_runs WHERE id=$1) runs,(SELECT count(*) FROM investigation_events WHERE run_id=$1) events,(SELECT count(*) FROM investigation_artifacts WHERE run_id=$1) artifacts', probe_run_id))
                    events = [dict(row) for row in await connection.fetch('SELECT seq,kind,payload FROM investigation_events WHERE run_id=$1 ORDER BY seq', probe_run_id)]
                    artifacts = [dict(row) for row in await connection.fetch('SELECT id,kind,content,sha256,event_id FROM investigation_artifacts WHERE run_id=$1 ORDER BY created_at,id', probe_run_id)]
                    costs = await connection.fetchval('SELECT count(*) FROM aisoc_run_costs WHERE run_id=$1', str(probe_run_id))
                    return {'counts': counts, 'events': events, 'artifacts': artifacts, 'cost_rows': costs}
                return await scoped(tenant_a, read)

            assert (await probe_rows())['counts'] == {'runs': 0, 'events': 0, 'artifacts': 0}
            original_get_pool = ledger.get_pool; fault_hits = []
            class FaultConnection:
                def __init__(self, connection): self.connection = connection
                def __getattr__(self, name): return getattr(self.connection, name)
                async def execute(self, sql, *args):
                    if 'INSERT INTO investigation_artifacts' in sql and len(args) > 4 and args[4] == 'identity_context_read':
                        fault_hits.append('identity_context_read INSERT -> actual SELECT 1/0')
                        return await self.connection.execute('SELECT 1/0')
                    return await self.connection.execute(sql, *args)
            class FaultAcquire:
                async def __aenter__(self):
                    self.acquisition = pool.acquire(); return FaultConnection(await self.acquisition.__aenter__())
                async def __aexit__(self, *args): return await self.acquisition.__aexit__(*args)
            class FaultPool:
                def acquire(self): return FaultAcquire()
            async def failing_pool(): return FaultPool()
            save('ledger-fault-started.json', {'run_id': str(probe_run_id), 'probe_only': True,
                                              'fault': 'actual SELECT 1/0 at identity context artifact insert'})
            ledger.get_pool = failing_pool
            try:
                try: await ledger.persist_auto_triage(**probe_kwargs)
                except ledger.LedgerPersistError as error:
                    failure = {'exception': type(error).__name__, 'cause': type(error.__cause__).__name__}
                else: raise AssertionError('Actual PG error swallowed')
            finally: ledger.get_pool = original_get_pool
            assert fault_hits and failure['cause'] == 'DivisionByZeroError'
            rolled_back = await probe_rows(); assert rolled_back['counts'] == {'runs': 0, 'events': 0, 'artifacts': 0}
            assert await ledger.persist_auto_triage(**probe_kwargs)
            first_probe = await probe_rows(); assert first_probe['counts'] == {'runs': 1, 'events': 1, 'artifacts': 1}
            assert first_probe['cost_rows'] == rolled_back['cost_rows'] == 0
            assert decoded(first_probe['events'][0]['payload'])['identity_context_read'] == source_failure
            assert first_probe['artifacts'][0]['kind'] == 'identity_context_read'
            assert json.loads(first_probe['artifacts'][0]['content']) == source_failure
            assert await ledger.persist_auto_triage(**probe_kwargs)
            repeated_probe = await probe_rows(); assert repeated_probe == first_probe
            save('ledger-failure-acceptance.json', {'probe_run_id': str(probe_run_id), 'probe_only': True,
                                                  'model_invoked': False, 'failure': failure, 'fault_hits': fault_hits,
                                                  'rolled_back': rolled_back, 'recovered': first_probe,
                                                  'same_run_retry': repeated_probe, 'cost_rows_expected': 0,
                                                  'actual_failed_read_persisted': True})

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
                assert body['rule_id'] == 'R-IDENTITY-A' and body['hostname'] == 'IDENTITY-HOST-A'
                assert body['username'] == accounts[0] and not body.get('mitre_techniques')
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

            from app.agents import auto_triage_agent as agent_module
            def clear_readers():
                for reader in [memory, skills, kb, dispositions, identity]: reader.clear_cache()
            clear_readers()
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
            assert budget_state.knowledge_base_read['status'] == budget_state.recent_dispositions_read['status'] == 'no_match'
            assert budget_state.identity_context_read['status'] == 'success' and budget_state.identity_context_read['adopted_count'] == 1
            assert_model_row(budget_state.identity_context_read['identities'][0], 'a')
            save('model-prompt-budget-preflight.json', {'literal_limit': 8000, 'literal_chars': len(literal),
                                                       'prompt_sha256': sha(literal), 'model_invoked': False,
                                                       'new_run_persisted': False,
                                                       **{kind: getattr(budget_state, kind) for kind in READ_KINDS}})
            assert len(literal) <= 8000, 'Prompt literal would be truncated; stop before model, never re-ingress'
            clear_readers()
            original_invoke = agent_module.safe_ainvoke
            async def observe(llm, messages, *args, **kwargs):
                save('model-sent-messages.json', [{'role': message.type, 'content': message.content} for message in messages])
                response = await original_invoke(llm, messages, *args, **kwargs)
                metadata = response.response_metadata or {}; headers = metadata.get('headers', {}) or {}
                save('model-metadata.json', {'usage_metadata': response.usage_metadata,
                                             'finish_reason': metadata.get('finish_reason'),
                                             'route': headers.get('x-litellm-model-api-base'),
                                             'model': metadata.get('model_name'),
                                             'resolved_model': headers.get('x-litellm-response-model') or metadata.get('model_name') or metadata.get('model'),
                                             'response_content': response.content})
                return response
            class ObservedWorker(FusedAlertTriageWorker):
                async def _record(self, investigation, **kwargs):
                    actual = {key: asdict(value) if is_dataclass(value) else value for key, value in kwargs.items() if key != 'writer'}
                    save('model-before-persist.json', {'run_id': str(investigation.run_id),
                                                       'raw_alert': investigation.raw_alert,
                                                       **{kind: getattr(investigation, kind) for kind in READ_KINDS},
                                                       'identity_context': investigation.identity_context,
                                                       'exchanges': investigation.llm_exchanges, 'verdict': investigation.verdict,
                                                       'tokens': kwargs.get('tokens', 0), 'tier': kwargs['tier'],
                                                       'findings': investigation.findings, 'model_used': investigation.model_used,
                                                       'actual_kwargs': actual, 'writer_class': type(kwargs['writer']).__name__})
                    original_writer = kwargs['writer']
                    class ObservedWriter:
                        async def persist_auto_triage(self, **arguments):
                            save('model-ledger-input.json', arguments)
                            return await original_writer.persist_auto_triage(**arguments)
                    kwargs['writer'] = ObservedWriter()
                    await super()._record(investigation, **kwargs)
            agent_module.safe_ainvoke = observe
            try:
                save('model-call-started.json', {'coordinate': coordinate, 'source': 'actual Fusion envelope',
                                                 'no_replay_after_this_checkpoint': True})
                result = await ObservedWorker(bootstrap_servers='').triage(fused)
            finally: agent_module.safe_ainvoke = original_invoke
            save('model-worker-result.json', result)
            assert result['shadow'] and result['tier'] == 'llm'
            assert not result['response_dispatched'] and not result['approvals_raised'] and result['source_writeback'] is None
            pre = json.loads((E / 'model-before-persist.json').read_text())
            adopted = pre['identity_context_read']
            messages = json.loads((E / 'model-sent-messages.json').read_text()); contents = [str(message['content']) for message in messages]
            assert adopted['status'] == 'success' and adopted['cache']['source'] == 'network'
            assert adopted['adopted_count'] == 1 and identity_ids(adopted) == [node_id('a-identity')]
            assert_model_row(adopted['identities'][0], 'a')
            assert adopted['prompt_block'] and sha(adopted['prompt_block']) == adopted['prompt_sha256']
            assert any(adopted['prompt_block'] in content for content in contents) and len(adopted['prompt_block']) <= 3000
            assert adopted['without_timestamp'] == adopted['adopted_without_timestamp'] == 1
            assert adopted['import_cutoff_only'] and not adopted['business_history_verified']
            persisted_input = json.loads((E / 'model-ledger-input.json').read_text())
            assert adopted == persisted_input['identity_context_read']
            assert pre['identity_context']['identities'] == adopted['identities']
            for row in adopted['identities']:
                assert row['rendered_sha256'] == sha(row['rendered_text']) and row['rendered_text'] in adopted['prompt_block']
                assert row['row_source_sha256'] == a_http['identities'][0]['row_source_sha256']
                for field, value in row['display_fields'].items():
                    assert row['adopted_field_sha256'][field] == sha(value)
                    assert row['raw_field_sha256'][field] == sha(str(row.get(field) or ''))
                    assert len(value) <= adopted['budget']['field_limits'][field]
            assert pre['organisation_memory_read']['status'] == 'success' and pre['organisation_memory_read']['prompt_block']
            assert any(pre['organisation_memory_read']['prompt_block'] in content for content in contents)
            assert pre['tenant_skill_read']['status'] == 'success' and pre['tenant_skill_read']['selection']['status'] == 'no_match'
            assert pre['knowledge_base_read']['status'] == pre['recent_dispositions_read']['status'] == 'no_match'
            assert all(not pre[kind]['prompt_block'] for kind in ['tenant_skill_read', 'knowledge_base_read', 'recent_dispositions_read'])
            assert pre['exchanges'] and not pre['exchanges'][0]['prompt_truncated'] and not pre['exchanges'][0]['response_truncated']
            metadata = json.loads((E / 'model-metadata.json').read_text())
            rationale = agent_module._parse_llm_response(str(metadata['response_content']))['rationale']
            observation = {'rationale': rationale, 'verdict': result['verdict'],
                           'adopted_identity_ids': identity_ids(adopted),
                           'source_ids_mentioned': [row[field] for row in adopted['identities']
                                                    for field in ['identity_id', 'employee_id', 'department_id', 'manager_id']
                                                    if row[field] and row[field] in rationale],
                           'exact_display_mentions': [{'identity_id': row['identity_id'], 'field': field, 'text': value,
                                                       'exact_text_in_model_rationale': value in rationale}
                                                      for row in adopted['identities'] for field, value in row['display_fields'].items() if value],
                           'causal_adoption_or_quality_not_claimed': True, 'no_required_verdict_or_mention': True,
                           'second_model_call': False}
            save('model-identity-observation.json', observation)
            save('after-acceptance.json', {'alerts': {'model': alert}, 'result': result,
                                          'probe_run_id': str(probe_run_id), 'checks': prior_checks + checks,
                                          'resume': resume_metadata, 'current_mode_http_checks': checks,
                                          'fused_coordinate': coordinate, 'fused_consumer_group': None,
                                          'fused_reader_commits': False, 'submitted_alerts': 1, 'model_calls': 1,
                                          'actual_model_identity_read': adopted,
                                          'actual_model_memory_read': pre['organisation_memory_read'],
                                          'actual_model_skill_read': pre['tenant_skill_read'],
                                          'actual_model_kb_read': pre['knowledge_base_read'],
                                          'actual_model_dispositions_read': pre['recent_dispositions_read'],
                                          'model_observation': observation, 'failure_prompt_was_projection_only': True,
                                          'synthetic_read_fixtures_not_hr_sync_or_history_quality': True,
                                          'import_cutoff_only_not_business_history': True,
                                          'no_neo4j_sdk_or_graph_mutation_by_this_operator': True})
        finally:
            await ledger.close_pool()


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1]))
