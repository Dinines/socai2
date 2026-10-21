"""Checkpointed 3A-05 skill reads, selection provenance and one actual model run.

All authoring/version mutations below are labelled synthetic read fixtures,
with failed replay rows serving only foreign keys. They do not prove authoring,
activation, backtest quality or production observation. Accepted ingress and a
started model call are never automatically replayed.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, '/app')
import httpx
from aiokafka import AIOKafkaConsumer, TopicPartition
from app.agents.auto_triage_agent import _build_alert_context
from app.context import organisation_memory as memory
from app.context import tenant_skills as skills
from app.core.kafka_security import kafka_client_kwargs
from app.investigator import ledger
from app.workers.fused_alert_consumer import FusedAlertTriageWorker, build_state, worker_enabled

E = Path('/evidence')
B = '3a-tenant-skill-20261020'
CONTEXT_PATH = '/api/v1/tenant-skills/resolved/active'


def save(name, value):
    with (E / name).open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
    (E / name).chmod(0o600)


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


def skill_refs(read):
    return [f"{row['skill_id']}@v{row['version']}" for row in read['skills']]


async def main(mode, attempt=None):
    assert mode in {'before', 'after', 'verify', 'restart'}
    assert attempt is None or (mode == 'verify' and attempt == 'v2')
    probe_label = mode + ('-' + attempt if attempt else '')
    save(probe_label + '-started.json', {'at': datetime.now(timezone.utc), 'resident_worker_enabled': worker_enabled()})
    assert not worker_enabled()
    state = json.loads(Path('/private/state.json').read_text())
    assert state['batch'] == B
    ids, fixtures = state['identities'], state['skills']
    tenant_a, tenant_b = ids['a']['tenant_id'], ids['b']['tenant_id']
    checks = []
    async with httpx.AsyncClient(base_url='http://api:8000', trust_env=False, timeout=25) as client:
        async def req(method, path, identity='a', body=None, status=200, headers=None):
            auth = {'Authorization': 'Bearer ' + ids[identity]['key']} if identity else {}
            response = await client.request(method, path, headers=auth if headers is None else headers, json=body)
            checks.append({'method': method, 'path': path, 'identity': identity,
                           'status': response.status_code, 'expected': status})
            (E / (probe_label + '-http-checks.json')).write_text(json.dumps(checks, indent=2))
            (E / (probe_label + '-http-checks.json')).chmod(0o600)
            assert response.status_code == status, (response.status_code, response.text[:150])
            return response.json()

        try:
            if mode == 'before':
                token = os.environ.get('AISOC_AGENTS_SERVICE_TOKEN', '').strip()
                assert token, 'An existing shared token is needed only to reproduce the rejected old header'
                await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, 'reader_a', status=401)
                await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, None, status=401,
                          headers={'X-AiSOC-Service-Token': token})
                skills.clear_cache()
                old_rows = await skills.fetch_skills(tenant_a)
                assert old_rows == []
                save('before-acceptance.json', {'checks': checks, 'old_bearer_actual_http_status': 401,
                                              'old_shared_header_actual_http_status': 401,
                                              'old_reader_skills': old_rows,
                                              'model_invoked': False, 'new_alerts_submitted': 0})
                return

            if mode in {'verify', 'restart'}:
                previous = json.loads((E / 'after-acceptance.json').read_text())
                model_id, probe_id = previous['result']['run_id'], previous['probe_run_id']

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
                    receipt_artifacts = [item for item in details if item['kind'] == 'tenant_skill_read']
                    assert len(receipt_artifacts) == 1
                    receipt = json.loads(receipt_artifacts[0]['content'])
                    assert receipt == verdicts[0]['payload']['tenant_skill_read']
                    for artifact in details:
                        blob = artifact['content'].encode()
                        assert artifact['event_id'] == verdicts[0]['id']
                        assert hashlib.sha256(blob).hexdigest() == artifact['sha256']
                        assert len(blob) == artifact['size_bytes']
                    return run, events, artifacts, details, receipt

                run, events, artifacts, details, adopted = await read_run(model_id, 2, 4)
                probe_run, probe_events, probe_artifacts, probe_details, failed = await read_run(probe_id, 1, 1)
                assert {item['kind'] for item in events['items']} == {'llm_call', 'triage_verdict'}
                assert {item['kind'] for item in artifacts} == {'llm_prompt', 'llm_response', 'organisation_memory_read', 'tenant_skill_read'}
                before_persist = json.loads((E / 'model-before-persist.json').read_text())
                assert adopted == before_persist['tenant_skill_read']
                assert adopted['selection']['ref'] == fixtures['a_rule']['skill_id'] + '@v2'
                assert adopted['selection']['score'] == 20 and adopted['selection']['reasons'] == ['rule_id=R-SKILL-A']
                stored_messages = json.loads(next(item['content'] for item in details if item['kind'] == 'llm_prompt'))
                sent_messages = json.loads((E / 'model-sent-messages.json').read_text())
                assert [message['content'] for message in stored_messages] == [message['content'] for message in sent_messages]
                assert adopted['prompt_block'] in '\n'.join(message['content'] for message in stored_messages)
                org = next(item for item in details if item['kind'] == 'organisation_memory_read')
                verdict = next(item for item in events['items'] if item['kind'] == 'triage_verdict')
                assert json.loads(org['content']) == verdict['payload']['organisation_memory_read'] == before_persist['organisation_memory_read']
                assert failed == json.loads((E / 'actual-auth-failure-read.json').read_text())
                assert failed['status'] == 'unavailable' and failed['reason'] == 'auth_failed' and failed['skills'] == []
                assert failed['selection']['status'] == 'not_requested' and failed['prompt_block'] == ''
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

            initial_a = await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, 'reader_a')
            initial_b = await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_b, 'reader_b')
            assert initial_a['tenant_id'] == tenant_a and initial_b['tenant_id'] == tenant_b
            assert len(initial_a['skills']) == 5 and initial_b['skills'] == []
            assert {row['skill_id'] for row in initial_a['skills']} == {fixtures[key]['skill_id'] for key in ['a_rule', 'a_source', 'a_tech', 'a_tie_a', 'a_tie_b']}
            active_rule = next(row for row in initial_a['skills'] if row['skill_id'] == fixtures['a_rule']['skill_id'])
            assert active_rule['version'] == 2 and active_rule['body'] == fixtures['a_rule']['body']
            assert not any(marker in json.dumps(initial_a) for marker in ['skill-a-expired', 'skill-a-retired', 'Prior synthetic version; not current'])
            inferred_a = await req('GET', CONTEXT_PATH, 'reader_a')
            assert inferred_a == initial_a
            await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_b, 'reader_a', status=403)
            await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, 'denied', status=403)
            await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, None, status=401)
            await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, None, status=401,
                      headers={'Authorization': 'Bearer invalid-acceptance-credential'})
            await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, None, status=401,
                      headers={'X-AiSOC-Service-Token': os.environ.get('AISOC_AGENTS_SERVICE_TOKEN', '')})
            fixture = json.loads(Path('/fixture.json').read_text())
            base_alert = fixture['alert']
            forbidden = {**base_alert, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/forbidden-ingress')),
                         'source': 'socai2-' + B, 'source_event_ids': [B + '-forbidden'],
                         'event_time': datetime.now(timezone.utc).isoformat()}
            await req('POST', '/api/v1/alert-ingress', 'reader_a', body=forbidden, status=403)
            # JSON is valid YAML; this is a structurally valid authoring body.
            # Authorization must fail before any save or content parsing effects.
            await req('PUT', '/api/v1/tenant-skills', 'reader_a',
                      body={'source_yaml': json.dumps(fixtures['a_rule']['body'])}, status=403)

            skills.clear_cache()
            live_a = await skills.fetch_tenant_skills(tenant_a)
            cached_a = await skills.fetch_tenant_skills(tenant_a)
            live_b = await skills.fetch_tenant_skills(tenant_b)
            assert live_a['status'] == 'success' and live_a['cache']['source'] == 'network' and live_a['valid_count'] == 5
            assert cached_a['cache']['source'] == 'memory' and cached_a['skills'] == live_a['skills']
            assert live_b['status'] == 'no_match' and not live_b['skills']
            original_enabled = os.environ.get('AISOC_TENANT_SKILLS_ENABLED')
            try:
                os.environ['AISOC_TENANT_SKILLS_ENABLED'] = '0'
                disabled = await skills.fetch_tenant_skills(tenant_a)
                assert disabled['status'] == 'disabled' and not disabled['skills']
            finally:
                if original_enabled is None:
                    os.environ.pop('AISOC_TENANT_SKILLS_ENABLED', None)
                else:
                    os.environ['AISOC_TENANT_SKILLS_ENABLED'] = original_enabled
            original_keys_file = os.environ['AISOC_TENANT_SKILLS_KEYS_FILE']
            with tempfile.TemporaryDirectory(prefix='tenant-skill-probe-') as temporary:
                path = Path(temporary) / 'keys.json'
                with path.open('x') as stream:
                    json.dump({}, stream)
                path.chmod(0o600)
                try:
                    os.environ['AISOC_TENANT_SKILLS_KEYS_FILE'] = str(path)
                    missing = await skills.fetch_tenant_skills(tenant_a)
                    assert missing['status'] == 'unavailable' and missing['reason'] == 'not_configured' and not missing['skills']
                    path.write_text(json.dumps({tenant_a: ids['reader_b']['key']}))
                    wrong_identity = await skills.fetch_tenant_skills(tenant_a)
                    assert wrong_identity['status'] == 'unavailable' and wrong_identity['reason'] == 'auth_failed'
                    assert wrong_identity['http_status'] == 403 and not wrong_identity['skills']
                finally:
                    os.environ['AISOC_TENANT_SKILLS_KEYS_FILE'] = original_keys_file

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

            def selection_envelope(label, *, tenant=tenant_a, summary='Synthetic selection probe', rule=None, source='unrelated-source', techniques=None):
                return {'tenant_id': tenant, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/selection/' + label)),
                        'alert': {'title': summary, 'rule_id': rule, 'source': source,
                                  'mitre_techniques': techniques or [], 'severity': 'critical',
                                  'raw_event': {'probe_only': True, 'batch': B}}}

            async def attach(envelope):
                investigation = build_state(envelope)
                assert investigation is not None
                await FusedAlertTriageWorker(bootstrap_servers='')._attach_tenant_skill(investigation)
                return investigation

            original_ttl = skills._CACHE_TTL_S
            try:
                await reader_active(False)
                skills._CACHE_TTL_S = 0
                revoked_refresh = await skills.fetch_tenant_skills(tenant_a)
                assert revoked_refresh['status'] == 'unavailable' and revoked_refresh['reason'] == 'auth_failed'
                assert revoked_refresh['http_status'] == 401 and not revoked_refresh['skills']
                assert revoked_refresh['cache']['freshness'] == 'expired'
                projection = await attach(selection_envelope('failure', rule='R-SKILL-A'))
                auth_failure = projection.tenant_skill_read
                save('actual-auth-failure-read.json', auth_failure)
                assert auth_failure['status'] == 'unavailable' and auth_failure['reason'] == 'auth_failed'
                assert projection.tenant_skill is None and auth_failure['prompt_block'] == ''
                failed_prompt = _build_alert_context(projection, nonce='probe-only')
                assert 'status=unavailable' in failed_prompt and 'auth_failed' in failed_prompt
                assert 'Organisation skill skill-a-rule@' not in failed_prompt
                save('failure-prompt-projection.json', {'model_invoked': False, 'probe_only': True,
                                                       'read': auth_failure, 'context': failed_prompt,
                                                       'does_not_claim_model_saw_failure': True})
            finally:
                await reader_active(True)
                skills._CACHE_TTL_S = original_ttl
            skills.clear_cache()
            recovered = await skills.fetch_tenant_skills(tenant_a)
            assert recovered['status'] == 'success' and recovered['cache']['source'] == 'network'
            original_url, original_timeout = skills._API_URL, skills._TIMEOUT_S
            try:
                skills._API_URL, skills._TIMEOUT_S = 'http://127.0.0.1:1', .5
                transport = await skills.fetch_tenant_skills(tenant_a)
                assert transport['status'] == 'unavailable' and transport['reason'] == 'transport_error' and not transport['skills']
            finally:
                skills._API_URL, skills._TIMEOUT_S = original_url, original_timeout

            selection_matrix = {}
            selection_cases = [
                ('rule', {'rule': 'R-SKILL-A'}, 'a_rule', 20, ['rule_id=R-SKILL-A']),
                ('source', {'source': 'socai2-' + B}, 'a_source', 5, ['source=socai2-' + B]),
                ('technique', {'techniques': ['T1059.001']}, 'a_tech', 10, ['technique=T1059']),
                ('tie', {'summary': 'tie-marker selection probe'}, 'a_tie_a', 2, ['keywords=tie-marker']),
                ('no_match', {}, None, 0, []),
            ]
            for name, inputs, alias, score, reasons in selection_cases:
                envelope = selection_envelope(name, **inputs)
                investigation = await attach(envelope)
                read = investigation.tenant_skill_read
                assert read['status'] == 'success' and read['valid_count'] == 5
                assert read['selection']['score'] == score and read['selection']['reasons'] == reasons
                if alias is None:
                    assert read['selection']['status'] == 'no_match' and investigation.tenant_skill is None
                else:
                    assert read['selection']['ref'] == fixtures[alias]['skill_id'] + '@v' + str(fixtures[alias]['version'])
                    assert read['prompt_block'] == investigation.tenant_skill['triage_guidance']
                    assert hashlib.sha256(read['prompt_block'].encode()).hexdigest() == read['prompt_sha256']
                    assert read['prompt_block'] in _build_alert_context(investigation, nonce='probe-only')
                selection_matrix[name] = {'input': envelope, 'raw_alert': investigation.raw_alert,
                                          'read': read, 'tenant_skill': investigation.tenant_skill,
                                          'model_invoked': False, 'persisted': False}
            save('selection-matrix.json', selection_matrix)

            async def insert_read_fixture(alias, tenant_name, skill_id, match, guidance, lifetime_seconds):
                identity = ids[tenant_name]
                tenant = identity['tenant_id']
                head_id = uuid.uuid5(uuid.NAMESPACE_URL, B + '/head/' + alias)
                version_id = uuid.uuid5(uuid.NAMESPACE_URL, B + '/history/' + alias + '/1')
                baseline = uuid.UUID(state['fixture_evaluations'][tenant_name]['baseline'])
                candidate = uuid.UUID(state['fixture_evaluations'][tenant_name]['candidate'])
                async def insert(connection):
                    now = await connection.fetchval('SELECT now()')
                    expiry = now + timedelta(seconds=lifetime_seconds)
                    body = deepcopy(fixtures['a_rule']['body'])
                    body.update(id=skill_id, name='Probe-only ' + skill_id, expires_at=expiry.isoformat(),
                                match=match, guidance=guidance)
                    source = '# PROBE_ONLY read fixture; no replay or authoring executed\n' + json.dumps(body)
                    head = await connection.fetchrow(
                        "INSERT INTO aisoc_tenant_skills(id,tenant_id,skill_id,version,status,name,owner,expires_at,body,source_yaml,backtest_evaluation_id,backtest_baseline_id,backtest_version,activated_at,activated_by,created_by) VALUES ($1,$2,$3,1,'active',$4,'probe-only',$5,$6::jsonb,$7,$8,$9,1,$10,$11,$11) RETURNING id,tenant_id,skill_id,version,status,expires_at,activated_at,body",
                        head_id, uuid.UUID(tenant), skill_id, body['name'], expiry, json.dumps(body), source,
                        candidate, baseline, now, uuid.UUID(identity['user_id']))
                    await connection.execute(
                        "INSERT INTO aisoc_tenant_skill_versions(id,tenant_id,skill_row_id,skill_id,version,name,owner,expires_at,body,source_yaml,backtest_evaluation_id,backtest_baseline_id,authored_at,activated_at,activated_by) VALUES ($1,$2,$3,$4,1,$5,'probe-only',$6,$7::jsonb,$8,$9,$10,$11,$11,$12)",
                        version_id, uuid.UUID(tenant), head_id, skill_id, body['name'], expiry, json.dumps(body), source,
                        candidate, baseline, now, uuid.UUID(identity['user_id']))
                    return {'head': dict(head), 'history_id': str(version_id), 'probe_only': True,
                            'replay_executed': False, 'reused_failed_fk_scaffolds': True}
                return await scoped(tenant, insert)

            short_inserted = await insert_read_fixture('a-short', 'a', 'skill-a-short', {'rule_ids': ['R-SKILL-SHORT']},
                                                       'SHORT-SKILL: synthetic two-second change window; never lasting guidance.', 2)
            save('short-skill-inserted.json', short_inserted)
            skills.clear_cache()
            short_active = await skills.fetch_tenant_skills(tenant_a)
            assert short_active['valid_count'] == 6 and 'skill-a-short@v1' in skill_refs(short_active)
            short_selected = await attach(selection_envelope('short', rule='R-SKILL-SHORT'))
            assert short_selected.tenant_skill_read['selection']['ref'] == 'skill-a-short@v1'
            await asyncio.sleep(2.2)
            short_expired_cached = await skills.fetch_tenant_skills(tenant_a)
            assert short_expired_cached['valid_count'] == 5 and short_expired_cached['expired_count'] == 1
            assert short_expired_cached['cache']['source'] == 'memory' and 'skill-a-short@v1' not in skill_refs(short_expired_cached)
            short_unmatched = await attach(selection_envelope('short-expired', rule='R-SKILL-SHORT'))
            assert short_unmatched.tenant_skill_read['selection']['status'] == 'no_match' and short_unmatched.tenant_skill is None
            short_expired_api = await req('GET', CONTEXT_PATH + '?tenant_id=' + tenant_a, 'reader_a')
            assert 'skill-a-short' not in json.dumps(short_expired_api)
            b_inserted = await insert_read_fixture('b-valid', 'b', 'skill-b-valid', {'rule_ids': ['R-SKILL-A']},
                                                   'TENANT-B-SKILL: tenant B read fixture; never tenant A guidance.', 86400)
            skills.clear_cache()
            isolated_b = await skills.fetch_tenant_skills(tenant_b)
            final_a = await skills.fetch_tenant_skills(tenant_a)
            assert skill_refs(isolated_b) == ['skill-b-valid@v1'] and isolated_b['status'] == 'success'
            assert not any('skill-b-' in ref for ref in skill_refs(final_a)) and final_a['valid_count'] == 5
            b_selected = await attach(selection_envelope('tenant-b', tenant=tenant_b, rule='R-SKILL-A'))
            assert b_selected.tenant_skill_read['selection']['ref'] == 'skill-b-valid@v1'
            save('read-matrix.json', {'a_network': live_a, 'a_cached': cached_a, 'b_empty': live_b,
                                      'disabled': disabled, 'not_configured': missing, 'wrong_identity': wrong_identity,
                                      'actual_revoked_key_initial_refresh': revoked_refresh, 'actual_revoked_key_worker': auth_failure,
                                      'recovery': recovered, 'transport_failure': transport,
                                      'short_active': short_active, 'short_selected': short_selected.tenant_skill_read,
                                      'short_expired_cached': short_expired_cached,
                                      'short_after_expiry_selection': short_unmatched.tenant_skill_read,
                                      'short_expired_api': short_expired_api, 'b_valid_inserted': b_inserted,
                                      'b_isolated': isolated_b, 'b_selected': b_selected.tenant_skill_read, 'a_final': final_a,
                                      'controls_probe_process_only': True, 'model_calls': 0})

            probe_run_id = uuid.uuid5(uuid.NAMESPACE_URL, B + '/ledger-failure-probe')
            probe_kwargs = {'run_id': probe_run_id, 'alert_id': None, 'tenant_ref': tenant_a,
                            'alert_summary': 'Probe-only tenant skill transaction recovery',
                            'raw_alert': {'batch': B, 'probe_only': True}, 'tier': 'probe_only',
                            'verdict': 'needs_review', 'confidence': 0.0,
                            'rationale': 'Probe-only transaction test; no model verdict or alert mutation.',
                            'shadow': True, 'tenant_skill_read': auth_failure}

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
                def __init__(self, connection): self.connection = connection
                def __getattr__(self, name): return getattr(self.connection, name)
                async def execute(self, sql, *args):
                    if 'INSERT INTO investigation_artifacts' in sql and len(args) > 4 and args[4] == 'tenant_skill_read':
                        fault_hits.append('tenant_skill_read INSERT -> actual SELECT 1/0')
                        return await self.connection.execute('SELECT 1/0')
                    return await self.connection.execute(sql, *args)
            class FaultAcquire:
                async def __aenter__(self):
                    self.acquisition = pool.acquire()
                    return FaultConnection(await self.acquisition.__aenter__())
                async def __aexit__(self, *args): return await self.acquisition.__aexit__(*args)
            class FaultPool:
                def acquire(self): return FaultAcquire()
            async def failing_pool(): return FaultPool()
            save('ledger-fault-started.json', {'run_id': str(probe_run_id), 'probe_only': True,
                                              'fault': 'actual SELECT 1/0 at tenant skill artifact insert'})
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
            assert decoded(first_probe['events'][0]['payload'])['tenant_skill_read'] == auth_failure
            assert first_probe['artifacts'][0]['kind'] == 'tenant_skill_read'
            assert json.loads(first_probe['artifacts'][0]['content']) == auth_failure
            assert await ledger.persist_auto_triage(**probe_kwargs)
            repeated_probe = await probe_rows()
            assert repeated_probe == first_probe
            save('ledger-failure-acceptance.json', {'probe_run_id': str(probe_run_id), 'probe_only': True,
                                                   'model_invoked': False, 'failure': failure, 'fault_hits': fault_hits,
                                                   'rolled_back': rolled_back, 'recovered': first_probe,
                                                   'same_run_retry': repeated_probe, 'cost_rows_expected': 0,
                                                   'actual_failed_read_persisted': True})

            # Observe exactly the new Fusion message. No consumer group or
            # commits, substitute envelope, duplicate ingress or model retry.
            topic = os.environ['KAFKA_TOPIC_ALERTS_FUSED']
            consumer = AIOKafkaConsumer(topic, bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                        **kafka_client_kwargs(), enable_auto_commit=False, group_id=None)
            await consumer.start()
            try:
                partitions = sorted(consumer.partitions_for_topic(topic) or [])
                assert partitions
                assigned = [TopicPartition(topic, partition) for partition in partitions]
                consumer.unsubscribe(); consumer.assign(assigned)
                starts = await consumer.end_offsets(assigned)
                for partition, offset in starts.items(): consumer.seek(partition, offset)
                save('fused-read-starts.json', [{'partition': partition.partition, 'offset': offset} for partition, offset in starts.items()])
                body = {**base_alert, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/model-alert')),
                        'source': 'socai2-' + B, 'source_event_ids': [str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/model-event'))],
                        'event_time': datetime.now(timezone.utc).isoformat(), 'tags': [B]}
                save('model-sending.json', body)
                ack = await req('POST', '/api/v1/alert-ingress', body=body, status=202)
                save('model-ack.json', ack)
                for _ in range(80):
                    response = await client.get('/api/v1/alerts/' + ack['canonical_alert_id'], headers={'Authorization': 'Bearer ' + ids['a']['key']})
                    if response.status_code == 200: break
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
                    if fused is not None: break
                assert fused is not None, 'Missing fused result; do not resubmit'
                save('model-fused-envelope.json', fused)
            finally:
                with contextlib.suppress(asyncio.CancelledError): await consumer.stop()
            memory.clear_cache(); skills.clear_cache()
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
                                                       'tenant_skill_read': investigation.tenant_skill_read,
                                                       'tenant_skill': investigation.tenant_skill,
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
            assert result['verdict'] in {'true_positive', 'benign_true_positive', 'false_positive', 'benign', 'needs_review'}
            assert not result['response_dispatched'] and not result['approvals_raised'] and result['source_writeback'] is None
            before_persist = json.loads((E / 'model-before-persist.json').read_text())
            adopted = before_persist['tenant_skill_read']
            org_read = before_persist['organisation_memory_read']
            sent_messages = json.loads((E / 'model-sent-messages.json').read_text())
            actual_prompt = '\n'.join(str(message['content']) for message in sent_messages)
            assert adopted['status'] == 'success' and adopted['cache']['source'] == 'network'
            assert adopted['selection']['ref'] == fixtures['a_rule']['skill_id'] + '@v2'
            assert adopted['selection']['score'] == 20 and adopted['selection']['reasons'] == ['rule_id=R-SKILL-A']
            assert adopted['prompt_block'] == before_persist['tenant_skill']['triage_guidance']
            assert adopted['prompt_block'] in actual_prompt and 'skill-a-rule@v2' in actual_prompt
            assert org_read['status'] == 'success' and 'ORG-MEMORY-A-VALID' in org_read['prompt_block']
            assert org_read['prompt_block'] in actual_prompt
            assert not any(marker in actual_prompt for marker in ['skill-a-expired', 'skill-a-retired', 'skill-b-valid',
                                                                 'SHORT-SKILL', 'TENANT-B-SKILL', 'Prior synthetic version; not current'])
            assert hashlib.sha256(adopted['prompt_block'].encode()).hexdigest() == adopted['prompt_sha256']
            assert before_persist['exchanges'] and not before_persist['exchanges'][0]['prompt_truncated']
            assert not before_persist['exchanges'][0]['response_truncated']

            # Change only the newly seeded head after the actual verdict.
            # v1/v2 history and the verdict's v2 bytes must remain unchanged.
            async def rotate_new_head(connection):
                head_id = uuid.UUID(fixtures['a_rule']['row_id'])
                tenant = uuid.UUID(tenant_a)
                old_history = [dict(row) for row in await connection.fetch(
                    'SELECT version,row_to_json(t)::text material FROM aisoc_tenant_skill_versions t WHERE skill_row_id=$1 AND tenant_id=$2 ORDER BY version', head_id, tenant)]
                assert [row['version'] for row in old_history] == [1, 2]
                old_head = dict(await connection.fetchrow('SELECT * FROM aisoc_tenant_skills WHERE id=$1 AND tenant_id=$2', head_id, tenant))
                assert old_head['version'] == 2 and old_head['backtest_version'] == 2
                body = decoded(old_head['body'])
                body['guidance'] = 'REVISION-THREE-SKILL: distinct synthetic guidance authored after the observed v2 model run.'
                source = '# PROBE_ONLY post-verdict revision; no replay or authoring accepted\n' + json.dumps(body)
                updated = await connection.execute('UPDATE aisoc_tenant_skills SET version=3,backtest_version=3,body=$1::jsonb,source_yaml=$2,updated_at=now() WHERE id=$3 AND tenant_id=$4 AND version=2',
                                                   json.dumps(body), source, head_id, tenant)
                assert updated == 'UPDATE 1'
                now = await connection.fetchval('SELECT now()')
                await connection.execute(
                    'INSERT INTO aisoc_tenant_skill_versions(id,tenant_id,skill_row_id,skill_id,version,name,owner,expires_at,body,source_yaml,backtest_evaluation_id,backtest_baseline_id,authored_at,activated_at,activated_by) VALUES ($1,$2,$3,$4,3,$5,$6,$7,$8::jsonb,$9,$10,$11,$12,$12,$13)',
                    uuid.uuid5(uuid.NAMESPACE_URL, B + '/history/a-rule/3'), tenant, head_id, old_head['skill_id'],
                    old_head['name'], old_head['owner'], old_head['expires_at'], json.dumps(body), source,
                    old_head['backtest_evaluation_id'], old_head['backtest_baseline_id'], now, old_head['activated_by'])
                retained = [dict(row) for row in await connection.fetch(
                    'SELECT version,row_to_json(t)::text material FROM aisoc_tenant_skill_versions t WHERE skill_row_id=$1 AND tenant_id=$2 AND version<3 ORDER BY version', head_id, tenant)]
                assert retained == old_history
                current = dict(await connection.fetchrow('SELECT id,skill_id,version,backtest_version,body FROM aisoc_tenant_skills WHERE id=$1 AND tenant_id=$2', head_id, tenant))
                return {'current_head': current, 'history_v1_v2': old_history,
                        'history_v1_v2_sha256': [hashlib.sha256(item['material'].encode()).hexdigest() for item in old_history],
                        'history_v1_v2_unchanged': True, 'probe_only': True, 'replay_executed': False}
            rotation = await scoped(tenant_a, rotate_new_head)
            skills.clear_cache()
            v3_state = await attach(fused)
            v3_read = v3_state.tenant_skill_read
            assert v3_read['selection']['ref'] == 'skill-a-rule@v3' and 'REVISION-THREE-SKILL' in v3_read['prompt_block']
            async def persisted_skill(connection):
                run_id = uuid.UUID(before_persist['run_id'])
                event = dict(await connection.fetchrow("SELECT id,payload FROM investigation_events WHERE run_id=$1 AND kind='triage_verdict'", run_id))
                artifact = dict(await connection.fetchrow("SELECT event_id,kind,content,sha256 FROM investigation_artifacts WHERE run_id=$1 AND kind='tenant_skill_read'", run_id))
                assert decoded(event['payload'])['tenant_skill_read'] == adopted
                assert json.loads(artifact['content']) == adopted and artifact['event_id'] == event['id']
                assert 'REVISION-THREE-SKILL' not in artifact['content']
                return {'event_id': str(event['id']), 'artifact': artifact, 'v2_unchanged_after_head_v3': True}
            frozen_v2 = await scoped(tenant_a, persisted_skill)
            save('skill-version-rotation.json', {**rotation, 'current_v3_read': v3_read,
                                                  'original_model_v2_read': adopted, 'frozen_v2_after_head_change': frozen_v2,
                                                  'refresh_model_calls': 0, 'refresh_persisted': False,
                                                  'does_not_claim_deep_investigation_version_pinning': True})
            save('after-acceptance.json', {'alerts': {'model': alert}, 'result': result,
                                          'probe_run_id': str(probe_run_id), 'checks': checks,
                                          'fused_coordinate': coordinate, 'fused_consumer_group': None,
                                          'fused_reader_commits': False, 'submitted_alerts': 1,
                                          'model_calls': 1, 'failure_prompt_was_projection_only': True,
                                          'actual_model_skill_read': adopted, 'actual_model_memory_read': org_read,
                                          'short_skill_id': 'skill-a-short', 'b_valid_skill_id': 'skill-b-valid',
                                          'new_skill_head_version_after_model': 3,
                                          'synthetic_skill_heads_expected': 10, 'synthetic_skill_versions_expected': 12,
                                          'failed_replay_fk_scaffolds_expected': 4,
                                          'synthetic_read_fixtures_not_authoring_or_backtest_acceptance': True})
        finally:
            await ledger.close_pool()


if __name__ == '__main__':
    asyncio.run(main(*sys.argv[1:]))
