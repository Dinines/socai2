"""Verify API delivery/restart, revoke this batch's keys and check preservation."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request

from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from prepare_identity_read_3a import TABLES, rows, lit
from prepare_triage_admission_3a import READERS, sha
from prepare_triage_durability_3a import R, E, B, save
from finish_model_triage_3a import METRICS
from deploy_triage_durability_3a import inspect, describe


def read(name):
    return json.loads((E / name).read_text())


def main():
    assert not (E / 'finish-started.json').exists(), 'Inspect any existing restart/cleanup checkpoint'
    assert (E / 'durability-verify-complete.json').is_file()
    save('finish-started.json', {'batch': B, 'no_model_or_ingress': True})
    state = json.loads((R / 'private/app-triage-durability-3a.json').read_text())
    ids = state['identities']; checks = []
    run_id = read('durability-after-observations.json')['cases']['after-normal']['results'][0]['run_id']
    normal = read('normal-stored-alert.json'); base = '/api/v1/investigations/' + run_id

    def request(path, who='a', expected=200):
        headers = {'Authorization': 'Bearer ' + ids[who]['key']} if who else {}
        req = urllib.request.Request('http://127.0.0.1:18000' + path, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                code, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            code, body = error.code, error.read()
        checks.append({'path': path, 'identity': who, 'status': code, 'expected': expected})
        assert code == expected, (path, code, expected)
        return json.loads(body) if body else None

    def delivery():
        run = request(base); events = request(base + '/events'); artifacts = request(base + '/artifacts')
        details = [request(base + '/artifacts/' + item['id']) for item in artifacts]
        assert run['status'] == 'completed' and run['total_tokens'] == 0
        assert run['event_count'] == len(events['items']) == 1 and len(artifacts) == 5
        verdict = events['items'][0]; assert verdict['kind'] == 'triage_verdict'
        before = read('durability-after-normal-before-persist.json')
        kinds = {'organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read', 'recent_dispositions_read', 'identity_context_read'}
        assert {item['kind'] for item in artifacts} == kinds
        for item in details:
            content = item['content'].encode()
            assert hashlib.sha256(content).hexdigest() == item['sha256'] and len(content) == item['size_bytes']
            assert item['event_id'] == verdict['id']
            assert json.loads(item['content']) == verdict['payload'][item['kind']] == before[item['kind']]
        alert = request('/api/v1/alerts/' + normal['id'])
        for key in ['raw_event', 'severity', 'status', 'disposition', 'resolved_at', 'priority', 'tags']:
            assert alert.get(key) == normal.get(key), key
        return {'run': run, 'events': events, 'artifacts': artifacts, 'artifact_details': details, 'alert': alert}

    first = delivery()
    request(base, 'b', 404); request(base, 'denied', 403); request(base, None, 401)
    save('api-before-restart.json', first)
    agent = inspect('socai2-agents-1')
    save('restart-before.json', describe(agent))
    subprocess.run(['docker', 'restart', 'socai2-agents-1'], check=True, capture_output=True)
    for _ in range(45):
        current = inspect('socai2-agents-1')
        if current['State'].get('Health', {}).get('Status') == 'healthy':
            break
        time.sleep(1)
    else:
        raise RuntimeError('Agents unhealthy after targeted restart; no blind repeat')
    assert current['Id'] == agent['Id'] and current['Image'] == agent['Image']
    assert describe(current)['env_sha256'] == describe(agent)['env_sha256'] and current['Mounts'] == agent['Mounts']
    code = "import os,json;from app.workers.fused_alert_consumer import worker_enabled,_broker_schema_error;from app.workers.triage_persistence import LiveTriageWriter;assert os.getuid()==10001 and not worker_enabled() and _broker_schema_error({})=='alert_not_object_or_empty';print(json.dumps({'uid':os.getuid(),'worker_enabled':False,'strict_broker_import_after_restart':True}))"
    resident = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-agents-1', 'python', '-c', code]))
    second = delivery(); assert second == first
    save('api-after-restart.json', second)
    save('restart-after.json', {'runtime': describe(current), 'resident': resident, 'same_api_delivery': True})

    # Verify the fields added to the actual broker DLQ, independently of the
    # method substitutes used only to avoid model calls.
    observations = read('durability-after-observations.json')['cases']
    fixtures = read('broker-fixtures.json'); dlq_projection = {}
    for alias in ['after-schema', 'after-missing-id', 'after-unknown-tenant', 'after-no-pool']:
        case = observations[alias]; messages = case['confirmed_dlq']['messages'] if alias == 'after-no-pool' else case['dlq']['messages']
        assert len(messages) == 1; body = messages[0]['body']; original = fixtures[alias]
        assert body['original'] == original
        if alias == 'after-schema':
            assert body['tenant_id'] is None and body['canonical_alert_id'] is None and body['source'] is None
        else:
            assert body['tenant_id'] == original['tenant_id'] and body['source'] == original['alert']['source']
            assert body['source_event_ids'] == original['alert']['source_event_ids']
            assert body['canonical_alert_id'] == (None if alias == 'after-missing-id' else original['alert_row_id'])
        dlq_projection[alias] = {key: body[key] for key in ['tenant_id', 'canonical_alert_id', 'source', 'source_event_ids', 'failure_stage', 'attempts']}
    save('dlq-projection-verification.json', {'actual_broker_fields': dlq_projection, 'unknown_is_not_default_tenant': True})

    batch = SharedBatch(R); revoked = {}
    for name, item in ids.items():
        batch.pg('SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id=' + lit(item['key_id']) + ' AND tenant_id=' + lit(item['tenant_id']) + ' AND name=' + lit('socai2-' + B + '-' + name) + ';')
        request(base, name, 401); revoked[name] = 401
    save('key-lifecycle.json', {'operation_keys_deactivated': revoked, 'reader_keys_rotated': 0})
    readers = {}
    for stem, scope in READERS:
        path = R / ('private/app-' + stem + '-3a.json'); keyfile = R / ('private/' + stem + '-3a/keys.json')
        frozen = state['reader_credentials'][stem]
        assert sha(path) == frozen['state_sha256'] and sha(keyfile) == frozen['keys_sha256']
        old = json.loads(path.read_text()); metadata = {}
        for alias in ['reader_a', 'reader_b']:
            item = old['identities'][alias]
            value = json.loads(batch.pg('SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT id,tenant_id,is_active,scopes,expires_at FROM api_keys WHERE id=' + lit(item['key_id']) + ') t;').stdout)
            assert value == frozen['metadata'][alias] and value['scopes'] == [scope]
            metadata[alias] = value
        readers[stem] = {'original_hashes_preserved': True, 'metadata': metadata}
    assert sha(R / 'private/identity-graph-3a/config.json') == state['graph_config_sha256']
    counts = {}; deltas = {'alerts': 1, 'investigation_runs': 1, 'investigation_events': 1, 'investigation_artifacts': 5, 'aisoc_shadow_decisions': 1}
    for table in ['alerts'] + TABLES:
        material = json.loads(batch.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM (" + MATERIAL_SQL + ') t;').stdout) if table == 'alerts' else rows(batch, table)
        old = read('prior-' + table + '.json'); actual = [hashlib.sha256(row['material'].encode()).hexdigest() for row in material]
        assert not Counter(old) - Counter(actual), table
        assert len(actual) == len(old) + deltas.get(table, 0), (table, len(actual), len(old))
        counts[table] = {'old_preserved': len(old), 'added': deltas.get(table, 0), 'total': len(actual)}
    gateway = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-litellm-1', 'python', '-c', METRICS]))
    assert gateway == read('gateway-before.json')
    start, end = read('environment-before.json'), snapshot()
    assert set(start['containers']) == set(end['containers']) and start['volumes'] == end['volumes']
    for name, item in start['containers'].items():
        if name != 'socai2-agents-1':
            assert end['containers'][name] == item, name
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip() == '134'
    assert describe(current)['env_sha256'] == read('runtime-baseline.json')['env_sha256']['agents']
    save('finish-http-checks.json', checks)
    save('environment-after.json', end)
    post = {'batch': B, 'material_counts': counts, 'images': {name: inspect('socai2-' + name + '-1')['Image'] for name in ['api', 'fusion', 'agents', 'actions']},
            'only_updated_and_restarted': ['agents'], 'other_containers_preserved': 35, 'containers_total': 36,
            'volumes_preserved': 18, 'migrations_preserved': 134,
            'gateway_before': read('gateway-before.json'), 'gateway_after': gateway,
            'real_model_calls': 0, 'model_tokens': 0, 'new_cost_rows': 0, 'new_reader_keys': 0,
            'reader_keys_preserved': 10, 'reader_credentials': readers, 'operation_keys_deactivated': revoked,
            'compose_layers': 18, 'unit_tests_passed': read('tests-acceptance.json')['passed'],
            'http_explicit_count': len(read('normal-http-checks.json')) + len(checks),
            'resident_worker_enabled': False, 'bounded_3a_10_01_accepted': True,
            'full_worker_admission_accepted': False, 'cold_replay_or_cache_source_retention_fixed': False,
            'model_quality_retested': False, 'next': '3A-10-02 durable prior results and source preservation; SDK budgets remain later'}
    save('postconditions.json', post)
    print(json.dumps({key: value for key, value in post.items() if key != 'reader_credentials'}))


if __name__ == '__main__':
    main()
