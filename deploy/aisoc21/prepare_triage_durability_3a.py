"""Snapshot bounded durability inputs and mint only three expiring API keys."""
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
from prepare_triage_admission_3a import READERS, sha
from finish_model_triage_3a import METRICS

R = Path('/opt/sting-aisoc-socai2')
B = '3a-triage-durability-20261020'
E = R / 'evidence' / B
PARENT = 'sha256:dd64bd753333f1cf705225534b1d0a2430fa43ff38f06a1196f39c67b709e645'
EXPECTED = [57, 28, 77, 77, 21, 6, 18, 2, 5, 10, 12, 4, 6, 5]


def save(name, value):
    with (E / name).open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
    (E / name).chmod(0o600)


def main():
    os.umask(0o077)
    target = R / 'private/app-triage-durability-3a.json'
    assert not target.exists() and not E.exists(), 'Inspect partial prepare; no key or evidence overwrite'
    batch = SharedBatch(R)
    prior = json.loads((R / 'private/app-triage-admission-3a.json').read_text())
    receipt = json.loads((R / 'source/docs/operations/3a-triage-admission.json').read_text())
    runtime = {name: batch.inspect('socai2-' + name + '-1') for name in ['api', 'fusion', 'agents', 'actions']}
    assert runtime['agents']['Image'] == PARENT
    assert {name: item['Image'] for name, item in runtime.items()} == receipt['postconditions']['images']
    assert all(item['State'].get('Health', {}).get('Status') == 'healthy' for item in runtime.values())
    envs = {name: sorted(item['Config']['Env']) for name, item in runtime.items()}
    values = dict(entry.split('=', 1) for entry in envs['agents'] if '=' in entry)
    assert values['AISOC_AGENT_KAFKA_DISABLE'] == '1'
    E.mkdir(mode=0o700)
    save('environment-before.json', snapshot())
    materials = [('alerts', json.loads(batch.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM (" + MATERIAL_SQL + ') t;').stdout))]
    materials += [(table, rows(batch, table)) for table in TABLES]
    for (table, material), count in zip(materials, EXPECTED):
        assert len(material) == count, (table, len(material), count)
        save('prior-' + table + '.json', [hashlib.sha256(row['material'].encode()).hexdigest() for row in material])
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip() == '134'
    credentials = {}
    now = datetime.fromisoformat(batch.pg('SELECT now()::text;').stdout.strip())
    for stem, scope in READERS:
        path = R / ('private/app-' + stem + '-3a.json')
        keys = R / ('private/' + stem + '-3a/keys.json')
        old = json.loads(path.read_text()); metadata = {}
        for alias in ['reader_a', 'reader_b']:
            key = old['identities'][alias]
            current = json.loads(batch.pg('SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT id,tenant_id,is_active,scopes,expires_at FROM api_keys WHERE id=' + lit(key['key_id']) + ') t;').stdout)
            assert current['is_active'] and current['scopes'] == [scope]
            assert current['tenant_id'] == key['tenant_id']
            assert datetime.fromisoformat(current['expires_at']) > now
            metadata[alias] = current
        assert keys.stat().st_uid == keys.stat().st_gid == 10001 and keys.stat().st_mode & 0o777 == 0o600
        credentials[stem] = {'state_sha256': sha(path), 'keys_sha256': sha(keys), 'metadata': metadata}
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + B)
    identities = {}
    for name in ['a', 'b', 'denied']:
        old = prior['identities']['a' if name == 'denied' else name]
        identities[name] = {
            'tenant_id': old['tenant_id'], 'user_id': old['user_id'],
            'key_id': str(uuid.uuid5(namespace, 'key/' + name)), 'key': 'aisoc_' + secrets.token_hex(24),
            'scopes': ['settings:read'] if name == 'denied' else ['alerts:read', 'alerts:write', 'cases:read'],
            'expires_at': (now + timedelta(hours=3)).isoformat(),
        }
    for alias in ['a', 'b']:
        value = batch.pg('SET ROLE aisoc; SELECT enabled FROM aisoc_shadow_mode WHERE tenant_id=' + lit(identities[alias]['tenant_id']) + " AND alert_class='*';").stdout.strip()
        assert value == 't'
    state = {'batch': B, 'created_at': now.isoformat(), 'identities': identities,
             'images': {name: item['Image'] for name, item in runtime.items()},
             'old_image': PARENT, 'reader_credentials': credentials,
             'graph_config_sha256': sha(R / 'private/identity-graph-3a/config.json'),
             'limits': {'broker_publishes': 7, 'deliveries': 8, 'method_substitutions': 8,
                        'normal_ingress': 1, 'new_runs': 1, 'new_source_artifacts': 5, 'real_model_calls': 0},
             'scope_plan_sha256': sha(R / 'source/docs/operations/3a-triage-durability-plan.md'),
             'resident_worker_enabled': False}
    with target.open('x') as stream:
        json.dump(state, stream, indent=2)
    sql = 'SET ROLE aisoc; BEGIN; '
    for name, item in identities.items():
        fields = [lit(item[key]) for key in ['key_id', 'tenant_id', 'user_id']]
        fields += [lit('socai2-' + B + '-' + name), lit(item['key'][:12]),
                   lit(hashlib.sha256(item['key'].encode()).hexdigest()), lit(json.dumps(item['scopes'])) + '::jsonb', lit(item['expires_at'])]
        sql += 'INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES (' + ','.join(fields) + '); '
    batch.pg(sql + 'COMMIT;')
    values.update({key: value for entry in envs['fusion'] if '=' in entry for key, value in [entry.split('=', 1)] if key.startswith('KAFKA_')})
    values['AISOC_AGENT_RAISE_APPROVALS'] = '0'
    with (R / 'private/probe-triage-durability-3a.env').open('x') as stream:
        stream.write(''.join(key + '=' + value + '\n' for key, value in values.items()))
    save('reader-credentials-before.json', credentials)
    save('gateway-before.json', json.loads(subprocess.check_output(['docker', 'exec', 'socai2-litellm-1', 'python', '-c', METRICS])))
    save('runtime-baseline.json', {'images': state['images'], 'env_sha256': {name: hashlib.sha256(json.dumps(env).encode()).hexdigest() for name, env in envs.items()}})
    safe = {name: {key: value for key, value in item.items() if key != 'key'} for name, item in identities.items()}
    save('fixtures.json', {**{key: value for key, value in state.items() if key != 'identities'}, 'identities': safe})
    print(json.dumps({'batch': B, 'operation_keys': 3, 'new_readers': 0, 'old_reader_keys_preserved': 10, 'business_source_changes': 0, 'real_model_calls': 0}))


if __name__ == '__main__':
    main()
