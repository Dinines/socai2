"""Seed isolated read-only skill fixtures; no authoring or backtest is claimed."""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib, json, os, secrets, subprocess, uuid

from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from finish_model_triage_3a import METRICS

R = Path('/opt/sting-aisoc-socai2')
B = '3a-tenant-skill-20261020'
E = R / ('evidence/' + B)
KEYS_DIR = R / 'private/tenant-skill-3a'
KEYS_PATH = '/run/secrets/tenant-skill/keys.json'
TABLES = ['investigation_runs', 'investigation_events', 'investigation_artifacts',
          'aisoc_run_costs', 'aisoc_shadow_mode', 'aisoc_shadow_decisions',
          'aisoc_business_context_rule_sets', 'aisoc_context_statements',
          'aisoc_tenant_skills', 'aisoc_tenant_skill_versions', 'aisoc_replay_evaluations']


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
    state_path = R / 'private/app-tenant-skill-3a.json'
    assert not state_path.exists() and not KEYS_DIR.exists(), 'No fixture reseed or credential overwrite'
    E.mkdir(exist_ok=True, mode=0o700)
    E.chmod(0o700)
    b = SharedBatch(R)
    org_state_path = R / 'private/app-org-memory-3a.json'
    org_state = json.loads(org_state_path.read_text())
    assert org_state['batch'] == '3a-org-memory-20261020'
    org_keys_path = R / 'private/org-memory-3a/keys.json'
    original_credentials = {'org_memory_state_sha256': hashlib.sha256(org_state_path.read_bytes()).hexdigest(),
                            'org_memory_keys_sha256': hashlib.sha256(org_keys_path.read_bytes()).hexdigest()}
    save('environment-before.json', snapshot())
    materials = [('alerts', json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM (" + MATERIAL_SQL + ") t;").stdout))]
    materials += [(table, rows(b, table)) for table in TABLES]
    for name, data in materials:
        if name in ['aisoc_tenant_skills', 'aisoc_tenant_skill_versions', 'aisoc_replay_evaluations']:
            assert not data, 'Inspect pre-existing skill/replay materials before fixture insertion: ' + name
        save('prior-' + name + '.json', [hashlib.sha256(row['material'].encode()).hexdigest() for row in data])
    save('prior-org-memory-credentials.json', original_credentials)

    runtime = {name: inspect('socai2-' + name + '-1') for name in ['api', 'fusion', 'agents', 'actions']}
    envs = {name: sorted(item['Config']['Env']) for name, item in runtime.items()}
    env_path = R / 'private/runtime-env-before-tenant-skill-3a.json'
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
        tenant_name = name[-1] if name.startswith('reader_') else ('a' if name == 'denied' else name)
        original = org_state['identities'][tenant_name]
        reader = name.startswith('reader_')
        item = {'tenant_id': original['tenant_id'],
                'user_id': str(uuid.uuid5(namespace, 'user_id/' + name)) if reader else original['user_id'],
                'key_id': str(uuid.uuid5(namespace, 'key_id/' + name)),
                'key': 'aisoc_' + secrets.token_hex(24),
                'scopes': ['settings:read'] if reader else (['alerts:read'] if name == 'denied' else ['alerts:read', 'alerts:write', 'cases:read', 'settings:read']),
                'role': 'viewer' if reader else original['role'],
                'expires_at': (created_at + (timedelta(days=30) if reader else timedelta(hours=3))).isoformat(),
                'purpose': 'resident tenant skill reader' if reader else 'bounded acceptance operation'}
        identities[name] = item

    fixture_evaluations = {name: {kind: str(uuid.uuid5(namespace, 'evaluation/' + name + '/' + kind))
                                   for kind in ['baseline', 'candidate']} for name in ['a', 'b']}
    definitions = [
        ('a_rule', 'a', 'skill-a-rule', 2, 'active', {'rule_ids': ['R-SKILL-A']}, False),
        ('a_source', 'a', 'skill-a-source', 1, 'active', {'sources': ['socai2-' + B]}, False),
        ('a_tech', 'a', 'skill-a-tech', 1, 'active', {'techniques': ['T1059']}, False),
        ('a_tie_a', 'a', 'skill-a-tie-a', 1, 'active', {'keywords': ['tie-marker']}, False),
        ('a_tie_b', 'a', 'skill-a-tie-b', 1, 'active', {'keywords': ['tie-marker']}, False),
        ('a_expired', 'a', 'skill-a-expired', 1, 'active', {'rule_ids': ['R-SKILL-A']}, True),
        ('a_retired', 'a', 'skill-a-retired', 1, 'retired', {'rule_ids': ['R-SKILL-A']}, False),
        ('b_expired', 'b', 'skill-b-expired', 1, 'active', {'rule_ids': ['R-SKILL-A']}, True),
    ]
    skills = {}
    for alias, tenant, skill_id, version, status, match, expired in definitions:
        expires_at = (created_at + timedelta(days=-1 if expired else 1)).isoformat()
        body = {'id': skill_id, 'name': 'Probe-only ' + skill_id, 'owner': 'probe-only',
                'expires_at': expires_at, 'match': match,
                'plan': ['Review current authentication and process evidence.', 'Verify account activity against the backup-job owner.'],
                'expected_pivots': ['authentication_activity', 'process_activity'], 'min_pivots': 2,
                'guidance': 'Require current authentication, process and backup-job evidence before classifying this account activity.',
                'verdict_guidance': 'An expected account name alone does not establish authorization.',
                'required_evidence': ['Current activity timestamp', 'Current process tree', 'Verified backup-job ownership']}
        skills[alias] = {'row_id': str(uuid.uuid5(namespace, 'skill/' + alias)),
                         'tenant_id': identities[tenant]['tenant_id'], 'skill_id': skill_id,
                         'version': version, 'status': status, 'expires_at': expires_at, 'body': body}
    state = {'batch': B, 'identities': identities, 'skills': skills, 'fixture_evaluations': fixture_evaluations,
             'reader_keys_file': str(KEYS_DIR / 'keys.json'), 'reader_container_path': KEYS_PATH,
             'created_at': created_at.isoformat(), 'reused_org_memory_test_tenants': True,
             'synthetic_preactivated_read_fixtures_not_authoring_backtest_activation_acceptance': True,
             'replay_fixture_status': 'failed', 'original_org_memory_credentials': original_credentials}
    with state_path.open('x') as f:
        json.dump(state, f, indent=2)
    state_path.chmod(0o600)

    for name, item in identities.items():
        sql = 'SET ROLE aisoc; BEGIN; '
        if name.startswith('reader_'):
            sql += f"INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{item['user_id']}','{item['tenant_id']}','{B}-{name}@test.invalid','socai2-tenant-skill-{name}','!disabled-api-only','viewer',true); "
        sql += f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{item['key_id']}','{item['tenant_id']}','{item['user_id']}','socai2-{B}-{name}','{item['key'][:12]}','{hashlib.sha256(item['key'].encode()).hexdigest()}',{lit(json.dumps(item['scopes']))}::jsonb,{lit(item['expires_at'])}); COMMIT;"
        b.pg(sql)
    for tenant in ['a', 'b']:
        item = identities[tenant]
        sql = f"SET ROLE aisoc; BEGIN; SELECT set_config('app.current_tenant_id','{item['tenant_id']}',true); "
        for kind, evaluation_id in fixture_evaluations[tenant].items():
            method = {'probe_only': True, 'not_actual_backtest': True, 'batch': B, 'fixture': kind}
            sql += ("INSERT INTO aisoc_replay_evaluations(id,tenant_id,status,error,connector_id,vendor,window_start,window_end,train_fraction,bootstrap_seed,bootstrap_resamples,headline_accuracy,score,method,requested_by) VALUES ("
                    f"'{evaluation_id}','{item['tenant_id']}','failed','PROBE_ONLY foreign-key fixture; no replay executed',{lit(B)},'fixture',{lit((created_at - timedelta(days=1)).isoformat())},{lit(created_at.isoformat())},0.7,0,1,NULL,NULL,{lit(json.dumps(method))}::jsonb,'{item['user_id']}'); ")
        for alias, skill in skills.items():
            if skill['tenant_id'] != item['tenant_id']:
                continue
            baseline, candidate = [fixture_evaluations[tenant][kind] for kind in ['baseline', 'candidate']]
            body = skill['body']
            source_yaml = '# PROBE_ONLY synthetic preactivated read fixture; no authoring or replay executed\n' + json.dumps(body, ensure_ascii=False)
            sql += ("INSERT INTO aisoc_tenant_skills(id,tenant_id,skill_id,version,status,name,owner,expires_at,body,source_yaml,backtest_evaluation_id,backtest_baseline_id,backtest_version,activated_at,activated_by,created_by) VALUES ("
                    f"'{skill['row_id']}','{item['tenant_id']}',{lit(skill['skill_id'])},{skill['version']},{lit(skill['status'])},{lit(body['name'])},'probe-only',{lit(skill['expires_at'])},{lit(json.dumps(body))}::jsonb,{lit(source_yaml)},'{candidate}','{baseline}',{skill['version']},{lit(created_at.isoformat())},'{item['user_id']}','{item['user_id']}'); ")
            for version in range(1, skill['version'] + 1):
                history = dict(body)
                if alias == 'a_rule' and version == 1:
                    history['guidance'] = 'Prior synthetic version; not current'
                history_source = '# PROBE_ONLY synthetic version snapshot\n' + json.dumps(history, ensure_ascii=False)
                history_id = str(uuid.uuid5(namespace, 'version/' + alias + '/' + str(version)))
                sql += ("INSERT INTO aisoc_tenant_skill_versions(id,tenant_id,skill_row_id,skill_id,version,name,owner,expires_at,body,source_yaml,backtest_evaluation_id,backtest_baseline_id,authored_at,activated_at,activated_by,retired_at) VALUES ("
                        f"'{history_id}','{item['tenant_id']}','{skill['row_id']}',{lit(skill['skill_id'])},{version},{lit(history['name'])},'probe-only',{lit(skill['expires_at'])},{lit(json.dumps(history))}::jsonb,{lit(history_source)},'{candidate}','{baseline}',{lit(created_at.isoformat())},{lit(created_at.isoformat())},'{item['user_id']}'," + (lit(created_at.isoformat()) if skill['status'] == 'retired' else 'NULL') + "); ")
        b.pg(sql + 'COMMIT;')

    assert len(rows(b, 'aisoc_tenant_skills')) == 8
    assert len(rows(b, 'aisoc_tenant_skill_versions')) == 9
    assert len(rows(b, 'aisoc_replay_evaluations')) == 4
    replay_fixtures = json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT id,status,error,headline_accuracy,score,report_markdown,method FROM aisoc_replay_evaluations ORDER BY id) t;").stdout)
    assert all(row['status'] == 'failed' and row['error'] == 'PROBE_ONLY foreign-key fixture; no replay executed'
               and row['headline_accuracy'] is None and row['score'] is None and row['report_markdown'] is None
               and row['method']['probe_only'] is True and row['method']['not_actual_backtest'] is True
               for row in replay_fixtures)
    save('synthetic-replay-fk-fixtures.json', replay_fixtures)

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
    values.update(AISOC_AGENT_RAISE_APPROVALS='0', AISOC_TENANT_SKILLS_KEYS_FILE=KEYS_PATH)
    assert values.get('AISOC_AGENT_KAFKA_DISABLE') == '1', 'Keep resident worker disabled'
    assert values.get('AISOC_ORG_MEMORY_KEYS_FILE') == '/run/secrets/org-memory/keys.json'
    probe_env = R / 'private/probe-tenant-skill-3a.env'
    with probe_env.open('x') as f:
        f.write(''.join(key + '=' + value + '\n' for key, value in values.items()))
    probe_env.chmod(0o600)
    assert hashlib.sha256(org_state_path.read_bytes()).hexdigest() == original_credentials['org_memory_state_sha256']
    assert hashlib.sha256(org_keys_path.read_bytes()).hexdigest() == original_credentials['org_memory_keys_sha256']
    safe = {name: {key: value for key, value in item.items() if key != 'key'} for name, item in identities.items()}
    save('fixtures.json', {'batch': B, 'identities': safe, 'skills': skills, 'fixture_evaluations': fixture_evaluations,
                           'reused_org_memory_test_tenants': True,
                           'synthetic_preactivated_read_fixtures_not_authoring_backtest_activation_acceptance': True,
                           'replay_fixture_status': 'failed', 'original_org_memory_credentials_unchanged': True,
                           'reader_keys_file': {'container_path': KEYS_PATH, 'owner_uid': 10001, 'owner_gid': 10001,
                                                'directory_mode': '0700', 'file_mode': '0600', 'mapped_tenants': sorted(mapping)},
                           'operation_keys_revoke_at_finish': ['a', 'b', 'denied'],
                           'reader_keys_retained_until_expiry_or_controlled_rotation': ['reader_a', 'reader_b']})
    print(json.dumps({'reused_test_tenants': 2, 'new_tenants': 0, 'new_users': 2,
                      'operation_keys': 3, 'tenant_reader_keys': 2, 'synthetic_skill_heads': 8,
                      'synthetic_skill_versions': 9, 'failed_replay_fk_fixtures': 4,
                      'prior_materials_hashed': 12, 'resident_worker_enabled': False}))


if __name__ == '__main__':
    main()
