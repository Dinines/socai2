"""Prepare six marked lexical KB fixtures and dedicated tenant read keys."""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib, json, os, secrets, subprocess, uuid

from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from finish_model_triage_3a import METRICS

R = Path('/opt/sting-aisoc-socai2')
B = '3a-kb-read-20261020'
E = R / ('evidence/' + B)
KEYS_DIR = R / 'private/kb-read-3a'
KEYS_PATH = '/run/secrets/triage-kb/keys.json'
TABLES = ['investigation_runs', 'investigation_events', 'investigation_artifacts',
          'aisoc_run_costs', 'aisoc_shadow_mode', 'aisoc_shadow_decisions',
          'aisoc_business_context_rule_sets', 'aisoc_context_statements',
          'aisoc_tenant_skills', 'aisoc_tenant_skill_versions', 'aisoc_replay_evaluations',
          'aisoc_kb_documents']


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


def main():
    assert os.geteuid() == 0
    os.umask(0o077)
    state_path = R / 'private/app-kb-read-3a.json'
    assert not state_path.exists() and not KEYS_DIR.exists(), 'No fixture reseed or credential overwrite'
    E.mkdir(exist_ok=True, mode=0o700)
    E.chmod(0o700)
    batch = SharedBatch(R)
    previous = {}
    credential_hashes = {}
    for name, stem, directory in [('org_memory', 'org-memory', 'org-memory-3a'),
                                  ('tenant_skill', 'tenant-skill', 'tenant-skill-3a')]:
        path = R / ('private/app-' + stem + '-3a.json')
        previous[name] = json.loads(path.read_text())
        assert previous[name]['batch'] == '3a-' + stem + '-20261020'
        credential_hashes[name] = {'state_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                   'keys_sha256': hashlib.sha256((R / 'private' / directory / 'keys.json').read_bytes()).hexdigest()}
        save('prior-' + stem + '-credentials.json', credential_hashes[name])
    save('prior-reader-credentials.json', credential_hashes)
    save('environment-before.json', snapshot())
    materials = [('alerts', json.loads(batch.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM (" + MATERIAL_SQL + ") t;").stdout))]
    materials += [(table, rows(batch, table)) for table in TABLES]
    for name, data in materials:
        save('prior-' + name + '.json', [hashlib.sha256(row['material'].encode()).hexdigest() for row in data])
    schema = json.loads(batch.pg("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='aisoc_kb_documents' ORDER BY ordinal_position) t;").stdout)
    assert {row['column_name']: row['is_nullable'] for row in schema}['created_at'] == 'NO'
    assert {row['column_name']: row['is_nullable'] for row in schema}['updated_at'] == 'NO'
    save('kb-schema-before.json', {'table': 'aisoc_kb_documents', 'columns': schema,
                                   'null_timestamp_fixture_seeded': False, 'schema_or_constraints_changed': False})

    runtime = {name: inspect('socai2-' + name + '-1') for name in ['api', 'fusion', 'agents', 'actions']}
    envs = {name: sorted(item['Config']['Env']) for name, item in runtime.items()}
    env_path = R / 'private/runtime-env-before-kb-read-3a.json'
    with env_path.open('x') as stream:
        json.dump(envs, stream, indent=2)
    env_path.chmod(0o600)
    save('env-before.json', {name: {'sha256': hashlib.sha256(json.dumps(values).encode()).hexdigest(),
                                   'image': runtime[name]['Image']} for name, values in envs.items()})
    save('gateway-before.json', json.loads(subprocess.check_output(['docker', 'exec', 'socai2-litellm-1', 'python', '-c', METRICS])))
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + B)
    now = datetime.fromisoformat(batch.pg('SELECT now()::text;').stdout.strip())
    identities = {}
    for name in ['a', 'b', 'denied', 'reader_a', 'reader_b']:
        tenant_name = name[-1] if name.startswith('reader_') else ('a' if name == 'denied' else name)
        original = previous['org_memory']['identities'][tenant_name]
        reader = name.startswith('reader_')
        identities[name] = {
            'tenant_id': original['tenant_id'],
            'user_id': str(uuid.uuid5(namespace, 'user_id/' + name)) if reader else original['user_id'],
            'key_id': str(uuid.uuid5(namespace, 'key_id/' + name)), 'key': 'aisoc_' + secrets.token_hex(24),
            'scopes': ['knowledge_base:read'] if reader else (['alerts:read'] if name == 'denied' else
                       ['alerts:read', 'alerts:write', 'cases:read', 'settings:read', 'knowledge_base:read']),
            'role': 'viewer' if reader else original['role'],
            'expires_at': (now + (timedelta(days=30) if reader else timedelta(hours=3))).isoformat(),
            'purpose': 'resident tenant KB retrieval reader' if reader else 'bounded acceptance operation',
        }
    split = now - timedelta(days=1)
    early = now - timedelta(days=2)
    documents = {}
    for alias, tenant_name, kind, created, updated, marker in [
        ('a_runbook', 'a', 'runbook', early, early, 'KB-A-RUNBOOK'),
        ('b_runbook', 'b', 'runbook', early, early, 'KB-B-RUNBOOK'),
        ('a_policy', 'a', 'policy', early, early, 'KB-A-POLICY'),
        ('a_wiki', 'a', 'wiki', early, early, 'KB-A-WIKI'),
        ('a_updated_after', 'a', 'runbook', early, now, 'KB-A-UPDATED-AFTER'),
        ('a_created_after', 'a', 'runbook', now + timedelta(days=1), now + timedelta(days=1), 'KB-A-CREATED-AFTER'),
    ]:
        content = ('Backup account evidence R-SKILL-A. ' + marker + '. '
                   'Synthetic retrieval fixture only; this is not an actual tenant SOP. '
                   'Collect the current authentication timestamp and process tree. '
                   'Verify backup-job ownership before deciding whether this account activity is authorized. '
                   'Record missing evidence and request human review when ownership cannot be established.')
        documents[alias] = {
            'id': str(uuid.uuid5(namespace, 'document/' + alias)),
            'tenant_id': identities[tenant_name]['tenant_id'],
            'title': 'Probe-only backup account evidence ' + alias, 'doc_kind': kind,
            'source_url': 'https://example.invalid/synthetic/' + B + '/' + alias,
            'content': content, 'content_sha256': hashlib.sha256(content.encode()).hexdigest(),
            'tags': ['probe-only', B], 'chunk_index': 0, 'chunk_total': 1,
            'created_at': created.isoformat(), 'updated_at': updated.isoformat(), 'created_by': 'probe-only ' + B,
        }
    state = {
        'batch': B, 'created_at': now.isoformat(), 'identities': identities, 'documents': documents,
        'query': 'Backup account evidence R-SKILL-A', 'split_at': split.isoformat(), 'cutoff': split.isoformat(),
        'reader_keys_file': str(KEYS_DIR / 'keys.json'), 'reader_container_path': KEYS_PATH,
        'reused_org_memory_and_tenant_skill_test_tenants': True,
        'original_reader_credentials': credential_hashes,
        'no_timestamp_fixture': {'seeded': False, 'reason': 'created_at and updated_at are NOT NULL; missing-time behavior is unit-only'},
        'synthetic_documents_not_actual_tenant_sop': True,
        'expected_retrieval': {'a_live': {'chunks': 3, 'excluded_after_cutoff': 0, 'excluded_after_update': 0, 'excluded_after_cutoff_total': 0},
                               'a_frozen': {'chunks': 1, 'excluded_after_cutoff': 1, 'excluded_after_update': 1, 'excluded_after_cutoff_total': 2},
                               'b_live': {'chunks': 1}, 'b_frozen': {'chunks': 1}},
    }
    with state_path.open('x') as stream:
        json.dump(state, stream, indent=2)
    state_path.chmod(0o600)
    for name, item in identities.items():
        sql = 'SET ROLE aisoc; BEGIN; '
        if name.startswith('reader_'):
            sql += f"INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{item['user_id']}','{item['tenant_id']}','{B}-{name}@test.invalid','socai2-kb-read-{name}','!disabled-api-only','viewer',true); "
        sql += f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{item['key_id']}','{item['tenant_id']}','{item['user_id']}','socai2-{B}-{name}','{item['key'][:12]}','{hashlib.sha256(item['key'].encode()).hexdigest()}',{lit(json.dumps(item['scopes']))}::jsonb,{lit(item['expires_at'])}); COMMIT;"
        batch.pg(sql)
    for document in documents.values():
        tags = 'ARRAY[' + ','.join(lit(tag) for tag in document['tags']) + ']::text[]'
        batch.pg("SET ROLE aisoc; BEGIN; SELECT set_config('app.current_tenant_id'," + lit(document['tenant_id']) + ",true); "
                 "INSERT INTO aisoc_kb_documents(id,tenant_id,title,source_url,doc_kind,content,chunk_index,chunk_total,tags,created_at,updated_at,created_by) VALUES (" +
                 ','.join([lit(document[key]) for key in ['id', 'tenant_id', 'title', 'source_url', 'doc_kind', 'content']]) +
                 ',0,1,' + tags + ',' + ','.join(lit(document[key]) for key in ['created_at', 'updated_at', 'created_by']) + '); COMMIT;')
    assert len(rows(batch, 'aisoc_kb_documents')) == len(dict(materials)['aisoc_kb_documents']) + 6
    KEYS_DIR.mkdir(mode=0o700)
    mapping = {identities[name]['tenant_id']: identities['reader_' + name]['key'] for name in ['a', 'b']}
    keys_file = KEYS_DIR / 'keys.json'
    with keys_file.open('x') as stream:
        json.dump(mapping, stream, indent=2)
    keys_file.chmod(0o600)
    os.chown(keys_file, 10001, 10001)
    os.chown(KEYS_DIR, 10001, 10001)
    KEYS_DIR.chmod(0o700)
    values = dict(value.split('=', 1) for value in runtime['agents']['Config']['Env'] if '=' in value)
    values.update({key: value for entry in runtime['fusion']['Config']['Env'] if '=' in entry
                   for key, value in [entry.split('=', 1)] if key.startswith('KAFKA_')})
    values.update(AISOC_AGENT_RAISE_APPROVALS='0', AISOC_TRIAGE_KB_KEYS_FILE=KEYS_PATH)
    assert values.get('AISOC_AGENT_KAFKA_DISABLE') == '1'
    assert values.get('AISOC_ORG_MEMORY_KEYS_FILE') == '/run/secrets/org-memory/keys.json'
    assert values.get('AISOC_TENANT_SKILLS_KEYS_FILE') == '/run/secrets/tenant-skill/keys.json'
    probe_env = R / 'private/probe-kb-read-3a.env'
    with probe_env.open('x') as stream:
        stream.write(''.join(key + '=' + value + '\n' for key, value in values.items()))
    probe_env.chmod(0o600)
    for name, stem, directory in [('org_memory', 'org-memory', 'org-memory-3a'),
                                  ('tenant_skill', 'tenant-skill', 'tenant-skill-3a')]:
        assert hashlib.sha256((R / ('private/app-' + stem + '-3a.json')).read_bytes()).hexdigest() == credential_hashes[name]['state_sha256']
        assert hashlib.sha256((R / 'private' / directory / 'keys.json').read_bytes()).hexdigest() == credential_hashes[name]['keys_sha256']
    safe = {name: {key: value for key, value in item.items() if key != 'key'} for name, item in identities.items()}
    save('fixtures.json', {**{key: value for key, value in state.items() if key != 'identities'}, 'identities': safe,
                           'reader_keys_file': {'container_path': KEYS_PATH, 'owner_uid': 10001, 'owner_gid': 10001,
                                                'directory_mode': '0700', 'file_mode': '0600', 'mapped_tenants': sorted(mapping)},
                           'operation_keys_revoke_at_finish': ['a', 'b', 'denied'],
                           'reader_keys_retained_until_expiry_or_controlled_rotation': ['reader_a', 'reader_b']})
    print(json.dumps({'reused_test_tenants': 2, 'new_tenants': 0, 'new_users': 2,
                      'operation_keys': 3, 'tenant_reader_keys': 2, 'synthetic_kb_rows': 6,
                      'null_timestamp_rows_seeded': 0, 'prior_materials_hashed': 13,
                      'resident_worker_enabled': False}))


if __name__ == '__main__':
    main()
