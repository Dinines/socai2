"""Freeze the current baseline and provision three expiring probe identities.

No reader replacement, business-context seed, runtime change or model call.
The separate private grading rubric is deliberately not read by this operator.
"""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
import os
import secrets
import subprocess
import uuid

from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from prepare_identity_read_3a import TABLES, rows, lit
from finish_model_triage_3a import METRICS

R = Path('/opt/sting-aisoc-socai2')
B = '3a-triage-admission-20261020'
E = R / 'evidence' / B
READERS = [('org-memory', 'alerts:read'), ('tenant-skill', 'settings:read'),
           ('kb-read', 'knowledge_base:read'), ('dispositions', 'alerts:read'),
           ('identity-read', 'graph:read')]
EXPECTED = [54, 23, 69, 46, 18, 6, 13, 2, 5, 10, 12, 4, 6, 5]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    with (E / name).open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
    (E / name).chmod(0o600)


def main():
    os.umask(0o077)
    target = R / 'private/app-triage-admission-3a.json'
    assert not target.exists() and not E.exists(), 'Inspect partial state; never reseed or overwrite evidence'
    inputs_path = R / 'private/triage-admission-3a-inputs.json'
    inputs = json.loads(inputs_path.read_text())
    assert inputs['batch'] == B and len(inputs['cases']) == 3
    assert all(case['tenant'] in ['a', 'b'] for case in inputs['cases'].values())
    assert 'expected' not in inputs_path.read_text().lower()
    batch = SharedBatch(R)
    previous = json.loads((R / 'private/app-identity-read-3a.json').read_text())
    runtime = {name: batch.inspect('socai2-' + name + '-1') for name in ['api', 'fusion', 'agents', 'actions']}
    receipt = json.loads((R / 'source/docs/operations/3a-identity-read.json').read_text())
    for name in ['api', 'agents']:
        assert runtime[name]['Image'] == receipt['postconditions']['images'][name]
    envs = {name: sorted(item['Config']['Env']) for name, item in runtime.items()}
    values = dict(entry.split('=', 1) for entry in envs['agents'] if '=' in entry)
    assert values['AISOC_AGENT_KAFKA_DISABLE'] == '1'
    assert dict(entry.split('=', 1) for entry in envs['api'] if '=' in entry)['AISOC_DISABLE_NEO4J'].lower() == 'true'
    E.mkdir(mode=0o700)
    save('environment-before.json', snapshot())
    materials = [('alerts', json.loads(batch.pg('SET ROLE aisoc; SELECT COALESCE(json_agg(t),\'[]\'::json) FROM (' + MATERIAL_SQL + ') t;').stdout))]
    materials += [(table, rows(batch, table)) for table in TABLES]
    for (table, material), expected in zip(materials, EXPECTED):
        assert len(material) == expected, (table, len(material), expected)
        save('prior-' + table + '.json', [hashlib.sha256(row['material'].encode()).hexdigest() for row in material])
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip() == '134'
    readers = {}
    for stem, scope in READERS:
        state_path = R / ('private/app-' + stem + '-3a.json')
        keys_path = R / ('private/' + stem + '-3a/keys.json')
        state = json.loads(state_path.read_text())
        readers[stem] = {'state_sha256': sha(state_path), 'keys_sha256': sha(keys_path), 'tenants': {}}
        for name in ['reader_a', 'reader_b']:
            key = state['identities'][name]
            observed = json.loads(batch.pg('SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT id,tenant_id,is_active,scopes,expires_at FROM api_keys WHERE id=' + lit(key['key_id']) + ') t;').stdout)
            assert observed['is_active'] and observed['scopes'] == [scope]
            assert observed['tenant_id'] == key['tenant_id']
            readers[stem]['tenants'][name] = observed
        assert keys_path.stat().st_uid == keys_path.stat().st_gid == 10001
        assert keys_path.stat().st_mode & 0o777 == 0o600
    now = datetime.fromisoformat(batch.pg('SELECT now()::text;').stdout.strip())
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + B)
    identities = {}
    for name in ['a', 'b', 'denied']:
        old = previous['identities']['a' if name == 'denied' else name]
        identities[name] = {
            'tenant_id': old['tenant_id'], 'user_id': old['user_id'],
            'key_id': str(uuid.uuid5(namespace, 'key/' + name)),
            'key': 'aisoc_' + secrets.token_hex(24),
            'scopes': ['settings:read'] if name == 'denied' else ['alerts:read', 'alerts:write', 'cases:read', 'settings:read', 'knowledge_base:read', 'graph:read'],
            'expires_at': (now + timedelta(hours=3)).isoformat(),
        }
    state = {'batch': B, 'created_at': now.isoformat(), 'identities': identities,
             'input_sha256': sha(inputs_path), 'reader_credentials': readers,
             'images': {name: item['Image'] for name, item in runtime.items()},
             'graph_config_sha256': sha(R / 'private/identity-graph-3a/config.json'),
             'max_real_model_attempts': 3, 'max_attempts_per_case': 1,
             'probe_sdk_retries': 0, 'probe_sdk_timeout_seconds': 45,
             'resident_worker_enabled': False, 'business_sources_seeded': 0}
    with target.open('x') as stream:
        json.dump(state, stream, indent=2)
    sql = 'SET ROLE aisoc; BEGIN; '
    for name, key in identities.items():
        sql += "INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES (" + ','.join(lit(key[field]) for field in ['key_id', 'tenant_id', 'user_id']) + ',' + lit('socai2-' + B + '-' + name) + ',' + lit(key['key'][:12]) + ',' + lit(hashlib.sha256(key['key'].encode()).hexdigest()) + ',' + lit(json.dumps(key['scopes'])) + '::jsonb,' + lit(key['expires_at']) + '); '
    batch.pg(sql + 'COMMIT;')
    values.update({key: value for entry in envs['fusion'] if '=' in entry for key, value in [entry.split('=', 1)] if key.startswith('KAFKA_')})
    values['AISOC_AGENT_RAISE_APPROVALS'] = '0'
    with (R / 'private/probe-triage-admission-3a.env').open('x') as stream:
        stream.write(''.join(key + '=' + value + '\n' for key, value in values.items()))
    save('reader-credentials-before.json', readers)
    save('gateway-before.json', json.loads(subprocess.check_output(['docker', 'exec', 'socai2-litellm-1', 'python', '-c', METRICS])))
    save('runtime-baseline.json', {'images': state['images'], 'env_sha256': {name: hashlib.sha256(json.dumps(env).encode()).hexdigest() for name, env in envs.items()}, 'graph_config_sha256': state['graph_config_sha256'], 'gateway_config_sha256': sha(R / 'source/deploy/aisoc21/litellm.config.yaml')})
    safe = {name: {key: value for key, value in item.items() if key != 'key'} for name, item in identities.items()}
    save('fixtures.json', {**{key: value for key, value in state.items() if key != 'identities'}, 'identities': safe})
    print(json.dumps({'batch': B, 'operations_keys': 3, 'new_reader_keys': 0, 'existing_reader_keys_preserved': 10, 'business_sources_seeded': 0, 'real_model_attempt_limit': 3, 'runtime_changes': 0}))


if __name__ == '__main__':
    main()
