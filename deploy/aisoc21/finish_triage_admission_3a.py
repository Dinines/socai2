"""Read-only result checks and revoke only this batch's three operation keys.

No service restart, reader rotation, source mutation or model call.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.error
import urllib.request

from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from prepare_identity_read_3a import TABLES, rows, lit
from prepare_triage_admission_3a import B, E, R, READERS, sha
from finish_model_triage_3a import METRICS


def read(name):
    return json.loads((E / name).read_text())


def save(name, value):
    with (E / name).open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
    (E / name).chmod(0o600)


def status(key):
    request = urllib.request.Request('http://127.0.0.1:18000/api/v1/alerts?limit=1', headers={'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def main():
    assert (E / 'verify-acceptance.json').is_file() and not (E / 'postconditions.json').exists()
    assert all((E / name).is_file() for name in ['broker-run-complete.json', 'broker-cold-repeat-complete.json', 'broker-restart-complete.json', 'broker-fallback-projection.json'])
    state = json.loads((R / 'private/app-triage-admission-3a.json').read_text())
    batch = SharedBatch(R)
    if (E / 'operation-key-lifecycle.json').exists():
        assert (E / 'finish-first-failure.json').exists(), 'Existing lifecycle needs an explicit recovery record'
        revoked = read('operation-key-lifecycle.json')['deactivated']
        assert all(status(item['key']) == revoked[name] == 401 for name, item in state['identities'].items())
        save('finish-recovery-key-check.json', {'statuses': revoked, 'key_updates_reexecuted': False})
    else:
        revoked = {}
        for name, item in state['identities'].items():
            batch.pg('SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id=' + lit(item['key_id']) + ' AND tenant_id=' + lit(item['tenant_id']) + ' AND name=' + lit('socai2-' + B + '-' + name) + ';')
            revoked[name] = status(item['key'])
            assert revoked[name] == 401
        save('operation-key-lifecycle.json', {'deactivated': revoked, 'reader_keys_rotated': 0})
    readers = {}
    for stem, scope in READERS:
        path = R / ('private/app-' + stem + '-3a.json')
        keys = R / ('private/' + stem + '-3a/keys.json')
        frozen = state['reader_credentials'][stem]
        assert sha(path) == frozen['state_sha256'] and sha(keys) == frozen['keys_sha256']
        metadata = {}
        original = json.loads(path.read_text())
        for alias in ['reader_a', 'reader_b']:
            key = original['identities'][alias]
            current = json.loads(batch.pg('SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT id,tenant_id,is_active,scopes,expires_at FROM api_keys WHERE id=' + lit(key['key_id']) + ') t;').stdout)
            assert current == frozen['tenants'][alias] and current['scopes'] == [scope]
            metadata[alias] = current
        readers[stem] = {'state_and_keys_hash_preserved': True, 'metadata': metadata}
    assert sha(R / 'private/identity-graph-3a/config.json') == state['graph_config_sha256']
    verified = read('verify-acceptance.json')['cases']
    accepted = read('run-acceptance.json')
    assert len(accepted['cases']) == len(verified) == accepted['model_attempts'] == 3
    costs, usage = {}, {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
    for name, item in verified.items():
        assert not item.get('not_completed')
        metadata = read(name + '-model-metadata.json')
        assert metadata['route'] == 'http://192.168.1.43:8000/v1' and metadata['finish_reason'] == 'stop'
        actual = metadata['usage_metadata']
        assert len(item['cost_rows']) == 1
        cost = item['cost_rows'][0]
        assert cost['call_count'] == cost['unpriced_call_count'] == 1
        # These counters describe dollar pricing, separately from measured
        # token usage. A local unpriced call has measured_call_count=0.
        assert cost['measured_call_count'] == cost['estimated_call_count'] == 0
        assert cost['total_prompt_tokens'] == actual['input_tokens'] and cost['total_completion_tokens'] == actual['output_tokens']
        assert item['run']['total_tokens'] == actual['total_tokens']
        costs[name] = cost
        for key in usage:
            usage[key] += actual[key]
    gateway = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-litellm-1', 'python', '-c', METRICS]))
    initial_gateway = read('gateway-before.json'); expected_gateway = dict(initial_gateway)
    expected_gateway['aisoc-triage'] += 3
    assert gateway == expected_gateway
    # All original rows remain exact. Probe observations separately explain
    # any new rows and any mutable fields of new probe-only Runs.
    counts = {}
    for table in ['alerts'] + TABLES:
        material = json.loads(batch.pg('SET ROLE aisoc; SELECT COALESCE(json_agg(t),\'[]\'::json) FROM (' + MATERIAL_SQL + ') t;').stdout) if table == 'alerts' else rows(batch, table)
        old = read('prior-' + table + '.json')
        now = [hashlib.sha256(row['material'].encode()).hexdigest() for row in material]
        assert not Counter(old) - Counter(now), table
        delta = len(now) - len(old)
        limits = {'alerts': (3, 3), 'investigation_runs': (3, 5), 'investigation_events': (6, 8),
                  'investigation_artifacts': (21, 31), 'aisoc_run_costs': (3, 3), 'aisoc_shadow_decisions': (3, 10)}
        lower, upper = limits.get(table, (0, 0))
        assert lower <= delta <= upper, (table, delta)
        counts[table] = {'old_preserved': len(old), 'added': delta, 'total': len(now)}
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip() == '134'
    before, after = read('environment-before.json'), snapshot()
    assert before == after, 'Existing containers and volumes must be unchanged'
    baseline = read('runtime-baseline.json')
    for name in ['api', 'fusion', 'agents', 'actions']:
        item = batch.inspect('socai2-' + name + '-1')
        assert item['Image'] == state['images'][name] and item['State'].get('Health', {}).get('Status') == 'healthy'
        assert hashlib.sha256(json.dumps(sorted(item['Config']['Env'])).encode()).hexdigest() == baseline['env_sha256'][name]
    assert sha(R / 'source/deploy/aisoc21/litellm.config.yaml') == baseline['gateway_config_sha256']
    broker_complete = {mode: read('broker-' + mode + '-complete.json') for mode in ['run', 'cold-repeat', 'restart']}
    assert all(item['actual_model_requests'] == 0 and item['source_unchanged'] for item in broker_complete.values())
    fallback = read('broker-fallback-projection.json')
    assert fallback['actual_model_requests'] == 0 and fallback['needs_review_condition_met']
    result = {'batch': B, 'images': state['images'], 'existing_containers_preserved': len(before['containers']),
              'volumes_preserved': len(before['volumes']), 'migrations_unchanged': 134,
              'runtime_code_env_images_and_prompt_changed': False, 'services_restarted': 0,
              'material_counts': counts, 'usage': {**usage, 'model_attempts': 3, 'successful_calls': 3, 'unpriced_calls': 3, 'cost': None},
              'cost_rows': costs, 'gateway_before': initial_gateway, 'gateway_after': gateway,
              'reader_keys_preserved': 10, 'reader_credentials': readers,
              'operation_keys_deactivated': revoked, 'input_sha256': state['input_sha256'],
              'broker_complete': broker_complete, 'resident_worker_enabled': False,
              'worker_admission_accepted': False, 'full_model_quality_accepted': False,
              'next': '3A-10 bounded worker reliability corrections before admission'}
    save('environment-after.json', after)
    save('postconditions.json', result)
    print(json.dumps({key: value for key, value in result.items() if key not in ['reader_credentials', 'broker_complete']}))


if __name__ == '__main__':
    main()
