"""Marked tenant memory and narrowly scoped credentials; resident worker stays off."""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib, json, os, secrets, subprocess, uuid

from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from finish_model_triage_3a import METRICS

R = Path('/opt/sting-aisoc-socai2')
B = '3a-org-memory-20261020'
E = R / ('evidence/' + B)
KEYS_DIR = R / 'private/org-memory-3a'
KEYS_PATH = '/run/secrets/org-memory/keys.json'
TABLES = ['investigation_runs', 'investigation_events', 'investigation_artifacts',
          'aisoc_run_costs', 'aisoc_shadow_mode', 'aisoc_shadow_decisions',
          'aisoc_business_context_rule_sets', 'aisoc_context_statements']


def rows(b, table):
    assert table in TABLES
    return json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(x),'[]'::json) FROM "
                           "(SELECT row_to_json(t)::text AS material FROM " + table +
                           " t ORDER BY row_to_json(t)::text) x;").stdout)


def save(name, data):
    path = E / name
    with path.open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    path.chmod(0o600)


def inspect(name):
    return json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]


def lit(value):
    return "'" + str(value).replace("'", "''") + "'"


def main():
    assert os.geteuid() == 0, 'Host infrastructure operator required for private ownership'
    os.umask(0o077)
    state_path = R / 'private/app-org-memory-3a.json'
    assert not state_path.exists() and not KEYS_DIR.exists(), 'No fixture reseed or credential overwrite'
    E.mkdir(exist_ok=True, mode=0o700)
    E.chmod(0o700)
    b = SharedBatch(R)
    save('environment-before.json', snapshot())
    materials = [('alerts', json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM (" + MATERIAL_SQL + ") t;").stdout))]
    materials += [(table, rows(b, table)) for table in TABLES]
    for name, data in materials:
        save('prior-' + name + '.json', [hashlib.sha256(row['material'].encode()).hexdigest() for row in data])

    runtime = {name: inspect('socai2-' + name + '-1') for name in ['api', 'fusion', 'agents', 'actions']}
    envs = {name: sorted(item['Config']['Env']) for name, item in runtime.items()}
    env_path = R / 'private/runtime-env-before-org-memory-3a.json'
    with env_path.open('x') as f:
        json.dump(envs, f, indent=2)
    env_path.chmod(0o600)
    save('env-before.json', {name: {'sha256': hashlib.sha256(json.dumps(values).encode()).hexdigest(),
                                   'image': runtime[name]['Image']} for name, values in envs.items()})
    save('gateway-before.json', json.loads(subprocess.check_output(['docker', 'exec', 'socai2-litellm-1', 'python', '-c', METRICS])))

    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + B)
    created_at = datetime.fromisoformat(b.pg('SELECT now()::text;').stdout.strip())
    identities = {}
    for name in ['a', 'b', 'denied', 'reader_a', 'reader_b']:
        item = {key: str(uuid.uuid5(namespace, key + '/' + name)) for key in ['tenant_id', 'user_id', 'key_id']}
        if name == 'denied':
            item.update({key: identities['a'][key] for key in ['tenant_id', 'user_id']})
        elif name.startswith('reader_'):
            item['tenant_id'] = identities[name[-1]]['tenant_id']
        reader = name.startswith('reader_')
        item.update(key='aisoc_' + secrets.token_hex(24),
                    scopes=['alerts:read'] if reader else (['settings:read'] if name == 'denied' else ['alerts:read', 'alerts:write', 'cases:read']),
                    role='viewer' if reader else 'soc_analyst',
                    expires_at=(created_at + (timedelta(days=30) if reader else timedelta(hours=3))).isoformat(),
                    purpose='resident tenant memory reader' if reader else 'bounded acceptance operation')
        identities[name] = item
    statement_ids = {name: str(uuid.uuid5(namespace, 'statement/' + name)) for name in ['a_valid', 'a_expired', 'b_expired']}
    statements = {
        'a_valid': {'tenant': 'a', 'statement': 'ORG-MEMORY-A-VALID: svc-backup on MEM-HOST runs expected nightly backups during the approved 02:00 UTC window; verify the current job.', 'scope_value': 'svc-backup', 'expires_at': (created_at + timedelta(days=1)).isoformat()},
        'a_expired': {'tenant': 'a', 'statement': 'ORG-MEMORY-A-EXPIRED: expired synthetic tenant-A maintenance statement.', 'scope_value': 'expiredA', 'expires_at': (created_at - timedelta(days=1)).isoformat()},
        'b_expired': {'tenant': 'b', 'statement': 'ORG-MEMORY-B-EXPIRED: expired synthetic tenant-B maintenance statement.', 'scope_value': 'expiredB', 'expires_at': (created_at - timedelta(days=1)).isoformat()},
    }
    state = {'batch': B, 'identities': identities, 'statement_ids': statement_ids, 'statements': statements,
             'reader_keys_file': str(KEYS_DIR / 'keys.json'), 'reader_container_path': KEYS_PATH,
             'created_at': created_at.isoformat(), 'synthetic_compiled_rows_not_analyst_compiler_execution': True}
    with state_path.open('x') as f:
        json.dump(state, f, indent=2)
    state_path.chmod(0o600)

    for name, item in identities.items():
        sql = 'SET ROLE aisoc; BEGIN; '
        if name in ['a', 'b']:
            sql += f"INSERT INTO tenants(id,name,slug) VALUES ('{item['tenant_id']}','socai2 {B} {name}','socai2-{B}-{name}'); "
        if name != 'denied':
            sql += f"INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{item['user_id']}','{item['tenant_id']}','{B}-{name}@test.invalid','socai2-org-memory-{name}','!disabled-api-only','{item['role']}',true); "
        sql += f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{item['key_id']}','{item['tenant_id']}','{item['user_id']}','socai2-{B}-{name}','{item['key'][:12]}','{hashlib.sha256(item['key'].encode()).hexdigest()}',{lit(json.dumps(item['scopes']))}::jsonb,{lit(item['expires_at'])}); COMMIT;"
        b.pg(sql)
    for name in ['a', 'b']:
        item = identities[name]
        b.pg(f"SET ROLE aisoc; BEGIN; SELECT set_config('app.current_tenant_id','{item['tenant_id']}',true); INSERT INTO aisoc_shadow_mode(tenant_id,alert_class,enabled,enabled_at,updated_by) VALUES ('{item['tenant_id']}','*',true,now(),'{item['user_id']}'); COMMIT;")
    for name, statement in statements.items():
        tenant = identities[statement['tenant']]['tenant_id']
        b.pg(f"SET ROLE aisoc; BEGIN; SELECT set_config('app.current_tenant_id','{tenant}',true); INSERT INTO aisoc_context_statements(id,tenant_id,statement,reason_code,scope,scope_value,observations,expires_at) VALUES ('{statement_ids[name]}','{tenant}',{lit(statement['statement'])},'expected_service_account','entity',{lit(statement['scope_value'])},2,{lit(statement['expires_at'])}); COMMIT;")

    KEYS_DIR.mkdir(mode=0o700)
    mapping = {identities[name]['tenant_id']: identities['reader_' + name]['key'] for name in ['a', 'b']}
    keys_file = KEYS_DIR / 'keys.json'
    with keys_file.open('x') as f:
        json.dump(mapping, f, indent=2)
    keys_file.chmod(0o600)
    os.chown(keys_file, 10001, 10001)
    os.chown(KEYS_DIR, 10001, 10001)
    KEYS_DIR.chmod(0o700)
    values = dict(value.split('=', 1) for value in runtime['agents']['Config']['Env'] if '=' in value)
    values.update({key: value for entry in runtime['fusion']['Config']['Env'] if '=' in entry
                   for key, value in [entry.split('=', 1)] if key.startswith('KAFKA_')})
    values.update(AISOC_AGENT_RAISE_APPROVALS='0', AISOC_ORG_MEMORY_KEYS_FILE=KEYS_PATH)
    assert values.get('AISOC_AGENT_KAFKA_DISABLE') == '1', 'Keep resident worker disabled'
    probe_env = R / 'private/probe-org-memory-3a.env'
    with probe_env.open('x') as f:
        f.write(''.join(key + '=' + value + '\n' for key, value in values.items()))
    probe_env.chmod(0o600)
    safe = {name: {key: value for key, value in item.items() if key != 'key'} for name, item in identities.items()}
    save('fixtures.json', {'batch': B, 'identities': safe, 'statement_ids': statement_ids, 'statements': statements,
                           'synthetic_compiled_rows_not_analyst_compiler_execution': True,
                           'reader_keys_file': {'container_path': KEYS_PATH, 'owner_uid': 10001, 'owner_gid': 10001,
                                                'directory_mode': '0700', 'file_mode': '0600', 'mapped_tenants': sorted(mapping)},
                           'operation_keys_revoke_at_finish': ['a', 'b', 'denied'],
                           'reader_keys_retained_until_expiry_or_controlled_rotation': ['reader_a', 'reader_b']})
    print(json.dumps({'tenants': 2, 'users': 4, 'operation_keys': 3, 'tenant_reader_keys': 2,
                      'synthetic_statements': 3, 'prior_materials_hashed': 9, 'resident_worker_enabled': False}))


if __name__ == '__main__':
    main()
