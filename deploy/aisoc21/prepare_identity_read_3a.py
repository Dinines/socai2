"""Prepare only API identities and private mounts; graph fixtures are managed separately."""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib, json, os, secrets, subprocess, uuid

from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from finish_model_triage_3a import METRICS

R = Path('/opt/sting-aisoc-socai2')
B = '3a-identity-read-20261020'
E = R / ('evidence/' + B)
KEYS_DIR = R / 'private/identity-read-3a'
KEYS_PATH = '/run/secrets/triage-identity/keys.json'
GRAPH_DIR = R / 'private/identity-graph-3a'
GRAPH_PATH = '/run/secrets/identity-graph/config.json'
TABLES = ['investigation_runs', 'investigation_events', 'investigation_artifacts',
          'aisoc_run_costs', 'aisoc_shadow_mode', 'aisoc_shadow_decisions',
          'aisoc_business_context_rule_sets', 'aisoc_context_statements',
          'aisoc_tenant_skills', 'aisoc_tenant_skill_versions', 'aisoc_replay_evaluations',
          'aisoc_kb_documents', 'aisoc_analyst_feedback']
BASELINE = dict(zip(['alerts'] + TABLES, [53, 21, 66, 38, 17, 6, 12, 2, 5, 10, 12, 4, 6, 5]))
EXPECTED_DELTAS = dict(zip(['alerts'] + TABLES, [1, 2, 3, 8, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0]))
READERS = [('org_memory', 'org-memory', 'alerts:read'),
           ('tenant_skill', 'tenant-skill', 'settings:read'),
           ('knowledge_base', 'kb-read', 'knowledge_base:read'),
           ('recent_dispositions', 'dispositions', 'alerts:read')]


def rows(batch, table):
    assert table in TABLES
    return json.loads(batch.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(x),'[]'::json) FROM "
                               "(SELECT row_to_json(t)::text AS material FROM " + table +
                               " t ORDER BY row_to_json(t)::text) x;").stdout)


def save(name, data):
    path = E / name
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
    path.chmod(0o600)


def inspect(name):
    return json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]


def lit(value):
    return "'" + str(value).replace("'", "''") + "'"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_file(directory, name):
    path = directory / name
    ds, fs = directory.stat(), path.stat()
    assert ds.st_uid == ds.st_gid == fs.st_uid == fs.st_gid == 10001
    assert ds.st_mode & 0o777 == 0o700 and fs.st_mode & 0o777 == 0o600
    return path


def main():
    assert os.geteuid() == 0
    os.umask(0o077)
    state_path = R / 'private/app-identity-read-3a.json'
    assert not state_path.exists() and not KEYS_DIR.exists(), 'Inspect any partial prepare; no reseed or credential overwrite'
    E.mkdir(exist_ok=True, mode=0o700)
    E.chmod(0o700)
    graph_fixture_path = E / 'graph-fixtures.json'
    graph_fixture = json.loads(graph_fixture_path.read_text())
    assert isinstance(graph_fixture, dict) and graph_fixture['batch'] == B
    assert graph_fixture['model_account'] == 'svc-identity-a'
    split = datetime.fromisoformat(graph_fixture['split_at'])
    assert split.tzinfo is not None and split.utcoffset() == timedelta(0), 'Root-managed graph split must be aware UTC'
    assert graph_fixture['node_count'] == len(graph_fixture['nodes']) == 27
    assert graph_fixture['relationship_count'] == len(graph_fixture['edges']) == 22
    graph_seed = json.loads((E / 'graph-seed-result.json').read_text())
    assert graph_seed['schema_unchanged'] and graph_seed['only_marked_synthetic_objects_added']
    assert graph_seed['nodes'] == graph_fixture['node_count']
    assert graph_seed['relationships'] == graph_fixture['relationship_count']
    graph_config = private_file(GRAPH_DIR, 'config.json')
    config_fields = json.loads(graph_config.read_text())
    assert isinstance(config_fields, dict) and set(config_fields) == {'uri', 'username', 'password', 'database'}
    assert all(isinstance(value, str) and value.strip() for value in config_fields.values())
    assert config_fields['database'] == 'neo4j'
    batch = SharedBatch(R)
    previous, credential_hashes, reader_metadata = {}, {}, {}
    for name, stem, scope in READERS:
        path = R / ('private/app-' + stem + '-3a.json')
        keys = R / ('private/' + stem + '-3a/keys.json')
        previous[name] = json.loads(path.read_text())
        assert previous[name]['batch'] == '3a-' + stem + '-20261020'
        credential_hashes[name] = {'state_sha256': sha(path), 'keys_sha256': sha(keys)}
        reader_metadata[name] = {}
        for alias in ['reader_a', 'reader_b']:
            item = previous[name]['identities'][alias]
            observed = json.loads(batch.pg("SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT id,tenant_id,is_active,scopes,expires_at FROM api_keys WHERE id=" + lit(item['key_id']) + ") t;").stdout)
            assert observed['is_active'] and observed['scopes'] == [scope]
            assert observed['tenant_id'] == item['tenant_id']
            reader_metadata[name][alias] = observed
        save('prior-' + stem + '-credentials.json', credential_hashes[name])
    assert graph_fixture['tenants'] == {
        name: previous['org_memory']['identities'][name]['tenant_id'] for name in ['a', 'b']}
    save('prior-reader-credentials.json', credential_hashes)
    save('prior-reader-metadata.json', reader_metadata)
    save('environment-before.json', snapshot())
    materials = [('alerts', json.loads(batch.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM (" + MATERIAL_SQL + ") t;").stdout))]
    materials += [(table, rows(batch, table)) for table in TABLES]
    for name, data in materials:
        assert len(data) == BASELINE[name], (name, len(data), BASELINE[name])
        save('prior-' + name + '.json', [hashlib.sha256(row['material'].encode()).hexdigest() for row in data])
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip() == '134'
    runtime = {name: inspect('socai2-' + name + '-1') for name in ['api', 'fusion', 'agents', 'actions']}
    envs = {name: sorted(item['Config']['Env']) for name, item in runtime.items()}
    api_env = dict(value.split('=', 1) for value in envs['api'] if '=' in value)
    assert api_env.get('AISOC_DISABLE_NEO4J', '').lower() == 'true'
    assert 'AISOC_IDENTITY_GRAPH_CONFIG_FILE' not in api_env
    values = dict(value.split('=', 1) for value in envs['agents'] if '=' in value)
    assert 'AISOC_TRIAGE_IDENTITY_KEYS_FILE' not in values
    required = {'AISOC_ORG_MEMORY_KEYS_FILE': '/run/secrets/org-memory/keys.json',
                'AISOC_TENANT_SKILLS_KEYS_FILE': '/run/secrets/tenant-skill/keys.json',
                'AISOC_TRIAGE_KB_KEYS_FILE': '/run/secrets/triage-kb/keys.json',
                'AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE': '/run/secrets/dispositions/keys.json'}
    assert all(values.get(key) == value for key, value in required.items())
    assert values.get('AISOC_AGENT_KAFKA_DISABLE') == '1'
    env_path = R / 'private/runtime-env-before-identity-read-3a.json'
    with env_path.open('x') as stream:
        json.dump(envs, stream, indent=2)
    env_path.chmod(0o600)
    save('env-before.json', {name: {'sha256': hashlib.sha256(json.dumps(items).encode()).hexdigest(), 'image': runtime[name]['Image']} for name, items in envs.items()})
    save('gateway-before.json', json.loads(subprocess.check_output(['docker', 'exec', 'socai2-litellm-1', 'python', '-c', METRICS])))
    now = datetime.fromisoformat(batch.pg('SELECT now()::text;').stdout.strip())
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + B)
    identities = {}
    for name in ['a', 'b', 'denied', 'reader_a', 'reader_b']:
        tenant_name = name[-1] if name.startswith('reader_') else ('a' if name == 'denied' else name)
        original = previous['org_memory']['identities'][tenant_name]
        reader = name.startswith('reader_')
        identities[name] = {
            'tenant_id': original['tenant_id'],
            'user_id': str(uuid.uuid5(namespace, 'user_id/' + name)) if reader else original['user_id'],
            'key_id': str(uuid.uuid5(namespace, 'key_id/' + name)), 'key': 'aisoc_' + secrets.token_hex(24),
            'scopes': ['graph:read'] if reader else (['settings:read'] if name == 'denied' else
                       ['alerts:read', 'alerts:write', 'cases:read', 'settings:read', 'knowledge_base:read', 'graph:read']),
            'role': 'viewer' if reader else original['role'],
            'expires_at': (now + (timedelta(days=30) if reader else timedelta(hours=3))).isoformat(),
            'purpose': 'resident tenant identity-context reader' if reader else 'bounded acceptance operation',
        }
    # Reuse the existing A/B shadow rows without touching their frozen material.
    for alias in ['a', 'b']:
        tenant = identities[alias]['tenant_id']
        existing = json.loads(batch.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT alert_class,enabled FROM aisoc_shadow_mode WHERE tenant_id=" + lit(tenant) + ") t;").stdout)
        assert any(row['alert_class'] == '*' and row['enabled'] for row in existing), 'Existing test tenant must remain shadow-only'
    state = {
        'batch': B, 'created_at': now.isoformat(), 'identities': identities,
        'account': 'svc-identity-a', 'accounts': ['svc-identity-a'],
        'rule_id': 'R-IDENTITY-A', 'entities': ['identity-host-a', 'svc-identity-a'],
        'model_host': 'IDENTITY-HOST-A', 'model_mitre': [],
        'split_at': split.isoformat(), 'cutoff': split.isoformat(),
        'graph_fixture': graph_fixture, 'graph_fixture_sha256': sha(graph_fixture_path),
        'graph_config_file': str(graph_config), 'graph_container_path': GRAPH_PATH,
        'graph_config_sha256': sha(graph_config),
        'reader_keys_file': str(KEYS_DIR / 'keys.json'), 'reader_container_path': KEYS_PATH,
        'reused_original_four_reader_test_tenants': True,
        'original_reader_credentials': credential_hashes,
        'expected_material_deltas': EXPECTED_DELTAS,
        'no_pg_business_fixture_seeded': True, 'existing_shadow_configuration_preserved': True,
        'history_limit': 'Employee import stamp is not HR effective time or a history/version of the whole identity path.',
        'graph_access_limit': 'Application READ_ACCESS path; shared Community credentials are not a database-enforced read-only tenant role.',
    }
    with state_path.open('x') as stream:
        json.dump(state, stream, indent=2)
    state_path.chmod(0o600)
    sql = 'SET ROLE aisoc; BEGIN; '
    for name, item in identities.items():
        if name.startswith('reader_'):
            sql += f"INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{item['user_id']}','{item['tenant_id']}','{B}-{name}@test.invalid','socai2-identity-read-{name}','!disabled-api-only','viewer',true); "
        sql += f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{item['key_id']}','{item['tenant_id']}','{item['user_id']}','socai2-{B}-{name}','{item['key'][:12]}','{hashlib.sha256(item['key'].encode()).hexdigest()}',{lit(json.dumps(item['scopes']))}::jsonb,{lit(item['expires_at'])}); "
    batch.pg(sql + 'COMMIT;')
    KEYS_DIR.mkdir(mode=0o700)
    mapping = {identities[name]['tenant_id']: identities['reader_' + name]['key'] for name in ['a', 'b']}
    keys_file = KEYS_DIR / 'keys.json'
    with keys_file.open('x') as stream:
        json.dump(mapping, stream, indent=2)
    keys_file.chmod(0o600)
    os.chown(keys_file, 10001, 10001)
    os.chown(KEYS_DIR, 10001, 10001)
    KEYS_DIR.chmod(0o700)
    values.update({key: value for entry in runtime['fusion']['Config']['Env'] if '=' in entry
                   for key, value in [entry.split('=', 1)] if key.startswith('KAFKA_')})
    values.update(AISOC_AGENT_RAISE_APPROVALS='0', AISOC_TRIAGE_IDENTITY_KEYS_FILE=KEYS_PATH)
    probe_env = R / 'private/probe-identity-read-3a.env'
    with probe_env.open('x') as stream:
        stream.write(''.join(key + '=' + value + '\n' for key, value in values.items()))
    probe_env.chmod(0o600)
    for name, stem, _ in READERS:
        assert sha(R / ('private/app-' + stem + '-3a.json')) == credential_hashes[name]['state_sha256']
        assert sha(R / ('private/' + stem + '-3a/keys.json')) == credential_hashes[name]['keys_sha256']
    assert sha(graph_config) == state['graph_config_sha256'] and sha(graph_fixture_path) == state['graph_fixture_sha256']
    safe = {name: {key: value for key, value in item.items() if key != 'key'} for name, item in identities.items()}
    save('fixtures.json', {**{key: value for key, value in state.items() if key != 'identities'}, 'identities': safe,
                          'reader_keys_file': {'container_path': KEYS_PATH, 'owner_uid': 10001, 'owner_gid': 10001,
                                               'directory_mode': '0700', 'file_mode': '0600', 'mapped_tenants': sorted(mapping)},
                          'operation_keys_revoke_at_finish': ['a', 'b', 'denied'],
                          'reader_keys_retained_until_expiry_or_controlled_rotation': ['reader_a', 'reader_b']})
    print(json.dumps({'reused_test_tenants': 2, 'new_tenants': 0, 'new_users': 2,
                      'operation_keys': 3, 'tenant_reader_keys': 2, 'pg_business_fixtures': 0,
                      'graph_written_by_this_operator': False, 'prior_materials_hashed': 14,
                      'old_reader_keys_preserved': 8, 'resident_worker_enabled': False}))


if __name__ == '__main__':
    main()
