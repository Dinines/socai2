"""Prepare five marked personal-opinion rows and dedicated disposition readers."""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib, json, os, secrets, subprocess, uuid

from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from finish_model_triage_3a import METRICS

R = Path('/opt/sting-aisoc-socai2')
B = '3a-dispositions-20261020'
E = R / ('evidence/' + B)
KEYS_DIR = R / 'private/dispositions-3a'
KEYS_PATH = '/run/secrets/dispositions/keys.json'
TABLES = ['investigation_runs', 'investigation_events', 'investigation_artifacts',
          'aisoc_run_costs', 'aisoc_shadow_mode', 'aisoc_shadow_decisions',
          'aisoc_business_context_rule_sets', 'aisoc_context_statements',
          'aisoc_tenant_skills', 'aisoc_tenant_skill_versions', 'aisoc_replay_evaluations',
          'aisoc_kb_documents', 'aisoc_analyst_feedback']


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
    state_path = R / 'private/app-dispositions-3a.json'
    assert not state_path.exists() and not KEYS_DIR.exists(), 'No fixture reseed or credential overwrite'
    E.mkdir(exist_ok=True, mode=0o700)
    E.chmod(0o700)
    batch = SharedBatch(R)
    previous = {}
    credential_hashes = {}
    for name, stem, directory in [('org_memory', 'org-memory', 'org-memory-3a'),
                                  ('tenant_skill', 'tenant-skill', 'tenant-skill-3a'),
                                  ('knowledge_base', 'kb-read', 'kb-read-3a')]:
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
        if name == 'aisoc_analyst_feedback':
            assert not data, 'Inspect unexpected pre-existing feedback rows before seeding'
        save('prior-' + name + '.json', [hashlib.sha256(row['material'].encode()).hexdigest() for row in data])
    schema = json.loads(batch.pg("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='aisoc_analyst_feedback' ORDER BY ordinal_position) t;").stdout)
    assert {row['column_name']: row['is_nullable'] for row in schema}['created_at'] == 'NO'
    assert 'updated_at' not in {row['column_name'] for row in schema}
    constraints = json.loads(batch.pg("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT conname,contype,pg_get_constraintdef(oid) definition FROM pg_constraint WHERE conrelid='public.aisoc_analyst_feedback'::regclass ORDER BY conname) t;").stdout)
    save('feedback-schema-before.json', {'table': 'aisoc_analyst_feedback', 'columns': schema,
                                   'constraints': constraints, 'fixture_alert_id_is_null': True,
                                   'history_or_database_immutability_claimed': False,
                                   'null_timestamp_fixture_seeded': False, 'schema_or_constraints_changed': False})

    runtime = {name: inspect('socai2-' + name + '-1') for name in ['api', 'fusion', 'agents', 'actions']}
    envs = {name: sorted(item['Config']['Env']) for name, item in runtime.items()}
    env_path = R / 'private/runtime-env-before-dispositions-3a.json'
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
            'scopes': ['alerts:read'] if reader else (['settings:read'] if name == 'denied' else
                       ['alerts:read', 'alerts:write', 'cases:read', 'settings:read', 'knowledge_base:read']),
            'role': 'viewer' if reader else original['role'],
            'expires_at': (now + (timedelta(days=30) if reader else timedelta(hours=3))).isoformat(),
            'purpose': 'resident tenant recent-disposition reader' if reader else 'bounded acceptance operation',
        }
    split = now - timedelta(days=1)
    early = now - timedelta(days=2)
    feedback = {}
    definitions = [
        ('a_rule_old', 'a', 'R-DISP-A', 'DISP-HOST-A', now - timedelta(days=2),
         'DISP-A-OLD: Personal opinion: prior access was authorized; verify current owner, time and authentication.'),
        ('a_after_split', 'a', 'R-DISP-A', 'DISP-HOST-A', now - timedelta(hours=12),
         'DISP-A-RECENT: Personal opinion: a prior exception was valid only for its approved window.'),
        ('a_entity_newer', 'a', 'R-DISP-OTHER', 'DISP-HOST-A', now - timedelta(hours=3),
         'DISP-A-ENTITY: Personal opinion: earlier account use was expected; verify current process and job ownership.'),
        ('a_unmatched', 'a', 'R-DISP-UNRELATED', 'DISP-UNRELATED-HOST', now - timedelta(days=2),
         'DISP-A-UNMATCHED: Unrelated synthetic personal opinion; should not match this rule or host.'),
        ('b_same_rule', 'b', 'R-DISP-A', 'DISP-HOST-B', now - timedelta(days=2),
         'DISP-B-ONLY: Tenant B personal opinion; never tenant A evidence.'),
    ]
    for alias, tenant, rule, entity, created, note in definitions:
        feedback[alias] = {
            'id': str(uuid.uuid5(namespace, 'feedback/' + alias)),
            'tenant_id': identities[tenant]['tenant_id'], 'alert_id': None,
            'ai_disposition': 'true_positive', 'analyst_disposition': 'benign_true_positive',
            'reason_code': 'expected_service_account', 'scope': 'entity', 'scope_value': entity,
            'analyst_id': 'probe-only ' + B + '/' + alias, 'note': note,
            'context': {'rule_id': rule, 'probe_only': True, 'batch': B,
                        'synthetic_personal_opinion_not_actual_analyst_feedback': True},
            'created_at': created.isoformat(),
        }
    state = {
        'batch': B, 'created_at': now.isoformat(), 'identities': identities, 'feedback': feedback,
        'rule_id': 'R-DISP-A', 'entities': ['disp-host-a', 'svc-review'],
        'split_at': split.isoformat(), 'cutoff': split.isoformat(),
        'reader_keys_file': str(KEYS_DIR / 'keys.json'), 'reader_container_path': KEYS_PATH,
        'reused_org_memory_tenant_skill_and_kb_test_tenants': True,
        'original_reader_credentials': credential_hashes,
        'no_timestamp_fixture': {'seeded': False, 'reason': 'created_at is NOT NULL; missing-time behavior is unit-only'},
        'synthetic_feedback_not_actual_analyst_write_compilation_or_closure': True,
        'historical_limit': 'Only created_at cutoff; no updated_at/version history or database-enforced note immutability. Current note text is not reconstructed at split.',
        'expected_retrieval': {'a_live_order': ['a_after_split', 'a_rule_old', 'a_entity_newer'],
                               'a_frozen_order': ['a_rule_old'], 'a_frozen_excluded_after_cutoff': 2,
                               'b_live_order': ['b_same_rule']},
    }
    with state_path.open('x') as stream:
        json.dump(state, stream, indent=2)
    state_path.chmod(0o600)
    for name, item in identities.items():
        sql = 'SET ROLE aisoc; BEGIN; '
        if name.startswith('reader_'):
            sql += f"INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{item['user_id']}','{item['tenant_id']}','{B}-{name}@test.invalid','socai2-dispositions-{name}','!disabled-api-only','viewer',true); "
        sql += f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{item['key_id']}','{item['tenant_id']}','{item['user_id']}','socai2-{B}-{name}','{item['key'][:12]}','{hashlib.sha256(item['key'].encode()).hexdigest()}',{lit(json.dumps(item['scopes']))}::jsonb,{lit(item['expires_at'])}); COMMIT;"
        batch.pg(sql)
    for row in feedback.values():
        values = [lit(row[key]) for key in ['id', 'tenant_id']]
        values += ['NULL']
        values += [lit(row[key]) for key in ['ai_disposition', 'analyst_disposition', 'reason_code', 'scope', 'scope_value', 'analyst_id', 'note']]
        values += [lit(json.dumps(row['context'])) + '::jsonb', lit(row['created_at'])]
        batch.pg("SET ROLE aisoc; BEGIN; SELECT set_config('app.current_tenant_id'," + lit(row['tenant_id']) + ",true); "
                 "INSERT INTO aisoc_analyst_feedback(id,tenant_id,alert_id,ai_disposition,analyst_disposition,reason_code,scope,scope_value,analyst_id,note,context,created_at) VALUES (" +
                 ','.join(values) + '); COMMIT;')
    assert len(rows(batch, 'aisoc_analyst_feedback')) == 5
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
    values.update(AISOC_AGENT_RAISE_APPROVALS='0', AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE=KEYS_PATH)
    assert values.get('AISOC_AGENT_KAFKA_DISABLE') == '1'
    assert values.get('AISOC_ORG_MEMORY_KEYS_FILE') == '/run/secrets/org-memory/keys.json'
    assert values.get('AISOC_TENANT_SKILLS_KEYS_FILE') == '/run/secrets/tenant-skill/keys.json'
    assert values.get('AISOC_TRIAGE_KB_KEYS_FILE') == '/run/secrets/triage-kb/keys.json'
    probe_env = R / 'private/probe-dispositions-3a.env'
    with probe_env.open('x') as stream:
        stream.write(''.join(key + '=' + value + '\n' for key, value in values.items()))
    probe_env.chmod(0o600)
    for name, stem, directory in [('org_memory', 'org-memory', 'org-memory-3a'),
                                  ('tenant_skill', 'tenant-skill', 'tenant-skill-3a'),
                                  ('knowledge_base', 'kb-read', 'kb-read-3a')]:
        assert hashlib.sha256((R / ('private/app-' + stem + '-3a.json')).read_bytes()).hexdigest() == credential_hashes[name]['state_sha256']
        assert hashlib.sha256((R / 'private' / directory / 'keys.json').read_bytes()).hexdigest() == credential_hashes[name]['keys_sha256']
    safe = {name: {key: value for key, value in item.items() if key != 'key'} for name, item in identities.items()}
    save('fixtures.json', {**{key: value for key, value in state.items() if key != 'identities'}, 'identities': safe,
                           'reader_keys_file': {'container_path': KEYS_PATH, 'owner_uid': 10001, 'owner_gid': 10001,
                                                'directory_mode': '0700', 'file_mode': '0600', 'mapped_tenants': sorted(mapping)},
                           'operation_keys_revoke_at_finish': ['a', 'b', 'denied'],
                           'reader_keys_retained_until_expiry_or_controlled_rotation': ['reader_a', 'reader_b']})
    print(json.dumps({'reused_test_tenants': 2, 'new_tenants': 0, 'new_users': 2,
                      'operation_keys': 3, 'tenant_reader_keys': 2, 'synthetic_feedback_rows': 5,
                      'null_timestamp_rows_seeded': 0, 'prior_materials_hashed': 14,
                      'resident_worker_enabled': False}))


if __name__ == '__main__':
    main()
