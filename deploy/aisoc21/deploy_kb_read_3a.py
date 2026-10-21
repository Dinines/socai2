"""Add a dedicated KB-reader key directory; recreate API/Agents only on guarded cached parents."""
from pathlib import Path
import hashlib, json, subprocess, time

R = Path('/opt/sting-aisoc-socai2')
E = R / 'evidence/3a-kb-read-20261020'
BASE = {
    'api': 'sha256:645bbdb02e8864c8db5781913ea732f95605194e7d9f59839375c78ede14ec8b',
    'agents': 'sha256:27ca9899c2674e60714e02f71a431ee37ddae7b4d1cd417050b4396699704f70',
}
PARTS = ['services', 'embedding', 'gateway', 'investigation', 'correlation-2a', 'identity-2a',
         'risk-2b', 'policy-2b', 'ioc-2c', 'context-2c', 'suppression-3a', 'risk-score-3a', 'org-memory-3a', 'tenant-skill-3a', 'kb-read-3a']
KEY_VAR = 'AISOC_TRIAGE_KB_KEYS_FILE'
KEY_PATH = '/run/secrets/triage-kb/keys.json'
KEY_DIR = '/run/secrets/triage-kb'
HOST_KEY_DIR = R / 'private/kb-read-3a'


def inspect(name):
    return json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]


def env_values(item):
    return dict(value.split('=', 1) for value in item['Config']['Env'] if '=' in value)


def env_hash(values):
    return hashlib.sha256(json.dumps(sorted(key + '=' + value for key, value in values.items())).encode()).hexdigest()


def describe(item):
    return {'id': item['Id'], 'image': item['Image'], 'mounts': item['Mounts'],
            'env_sha256': env_hash(env_values(item)), 'started_at': item['State']['StartedAt'],
            'restart_count': item['RestartCount']}


def save(name, data):
    path = E / name
    with path.open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    path.chmod(0o600)


def main():
    assert not (E / 'deployment-before.json').exists(), 'Inspect any prior deployment; no blind replay'
    tests = json.loads((E / 'tests-acceptance.json').read_text())
    assert tests.get('failed') == 0
    for field in ['api_passed', 'agents_passed']:
        assert type(tests.get(field)) is int and tests[field] > 0, 'Required locked-image tests not accepted: ' + field
    tested_source = tests['tested_runtime_source_sha256']
    current_source = {str(path.relative_to(R / 'source')): hashlib.sha256(path.read_bytes()).hexdigest()
                      for service in BASE for path in (R / f'source/services/{service}/app').rglob('*.py')}
    assert current_source == tested_source, 'Runtime source differs from the accepted test input'
    state = json.loads((R / 'private/app-kb-read-3a.json').read_text())
    assert state['batch'] == '3a-kb-read-20261020'
    preserved_files = []
    for name, stem in [('org_memory', 'org-memory'), ('tenant_skill', 'tenant-skill')]:
        pair = state['original_reader_credentials'][name]
        for path, digest in [(R / ('private/app-' + stem + '-3a.json'), pair['state_sha256']),
                             (R / ('private/' + stem + '-3a/keys.json'), pair['keys_sha256'])]:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
            preserved_files.append((path, digest))
    org_state = json.loads((R / 'private/app-org-memory-3a.json').read_text())
    expected_tenants = sorted(state['identities'][name]['tenant_id'] for name in ['a', 'b'])
    assert expected_tenants == sorted(org_state['identities'][name]['tenant_id'] for name in ['a', 'b'])
    for name in ['reader_a', 'reader_b']:
        assert state['identities'][name]['scopes'] == ['knowledge_base:read']
    keys_file = HOST_KEY_DIR / 'keys.json'
    directory_stat, file_stat = HOST_KEY_DIR.stat(), keys_file.stat()
    assert directory_stat.st_uid == directory_stat.st_gid == file_stat.st_uid == file_stat.st_gid == 10001
    assert directory_stat.st_mode & 0o777 == 0o700 and file_stat.st_mode & 0o777 == 0o600
    mapping = json.loads(keys_file.read_text())
    assert mapping == {state['identities'][name]['tenant_id']: state['identities']['reader_' + name]['key'] for name in ['a', 'b']}
    before = {name: inspect('socai2-' + name + '-1') for name in ['api', 'agents', 'fusion', 'actions']}
    before_env = {name: env_values(item) for name, item in before.items()}
    assert KEY_VAR not in before_env['agents'], 'This layer has not been applied before'
    assert before_env['agents'].get('AISOC_AGENT_KAFKA_DISABLE') == '1'
    assert before_env['agents'].get('AISOC_ORG_MEMORY_KEYS_FILE') == '/run/secrets/org-memory/keys.json'
    assert before_env['agents'].get('AISOC_TENANT_SKILLS_KEYS_FILE') == '/run/secrets/tenant-skill/keys.json'
    for name, digest in BASE.items():
        assert before[name]['Image'] == digest
        assert inspect(f'socai2-{name}:tenant-skill-3a-20261020')['Id'] == digest, 'Cached parent changed'
    save('deployment-before.json', {name: describe(item) for name, item in before.items()})
    built = {}
    for name in BASE:
        subprocess.run(['docker', 'build', '--pull=false', '-f', f'deploy/aisoc21/build/Dockerfile.{name}-kb-read-3a',
                        '-t', f'socai2-{name}:kb-read-3a-20261020', '.'], cwd=R / 'source', check=True)
        built[name] = inspect(f'socai2-{name}:kb-read-3a-20261020')['Id']
    save('built-images.json', built)
    command = ['docker', 'compose', '--project-directory', str(R)]
    for part in PARTS:
        command += ['-f', str(R / f'source/deploy/aisoc21/compose.{part}.yml')]
    subprocess.run(command + ['config', '--quiet'], check=True)
    subprocess.run(command + ['up', '-d', '--no-deps', '--pull', 'never', *BASE], check=True, capture_output=True)
    after = {}
    for name in BASE:
        for _ in range(45):
            item = inspect('socai2-' + name + '-1')
            if item['State'].get('Health', {}).get('Status') == 'healthy':
                break
            time.sleep(1)
        else:
            raise RuntimeError('Unhealthy ' + name)
        assert item['Image'] == built[name]
        values = env_values(item)
        if name == 'agents':
            assert values.get(KEY_VAR) == KEY_PATH
            assert {key: value for key, value in values.items() if key != KEY_VAR} == before_env[name]
            mounts = {mount['Destination']: mount for mount in item['Mounts']}
            old_mounts = {mount['Destination']: mount for mount in before[name]['Mounts']}
            assert set(mounts) == set(old_mounts) | {KEY_DIR}
            assert {target: mount for target, mount in mounts.items() if target != KEY_DIR} == old_mounts
            secret_mount = mounts[KEY_DIR]
            assert secret_mount['Type'] == 'bind' and secret_mount['Source'] == str(HOST_KEY_DIR) and not secret_mount['RW']
            assert item['Config']['User'] == '10001:10001' and item['HostConfig']['ReadonlyRootfs']
        else:
            assert values == before_env[name] and item['Mounts'] == before[name]['Mounts']
        after[name] = {'id': item['Id'], 'image': item['Image'], 'healthy': True,
                       'env_sha256': env_hash(values)}
    for name in ['fusion', 'actions']:
        assert describe(inspect('socai2-' + name + '-1')) == describe(before[name]), 'Unrelated service changed: ' + name

    # Runs as the resident non-root user and proves real file readability.
    # Only permissions/count/hash leave the container; no credential values.
    proof_code = '''import hashlib,json,os,pathlib,sys
from app.context.organisation_memory import _credential
from app.workers.fused_alert_consumer import worker_enabled
p=pathlib.Path(os.environ['AISOC_TRIAGE_KB_KEYS_FILE']);info=p.stat();parent=p.parent.stat()
assert os.getuid()==10001 and info.st_uid==info.st_gid==parent.st_uid==parent.st_gid==10001
assert info.st_mode&0o777==0o600 and parent.st_mode&0o777==0o700
mapping=json.loads(p.read_text());expected=json.loads(sys.argv[1]);assert sorted(mapping)==expected
assert all(_credential(tenant,keys_file_env='AISOC_TRIAGE_KB_KEYS_FILE') for tenant in expected)
assert all(_credential(tenant) for tenant in expected)
assert all(_credential(tenant,keys_file_env='AISOC_TENANT_SKILLS_KEYS_FILE') for tenant in expected)
assert not worker_enabled()
print(json.dumps({'uid':os.getuid(),'directory_mode':'0700','file_mode':'0600','mapped_tenants':len(mapping),'file_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'resident_worker_enabled':False}))'''
    proof = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-agents-1', 'python', '-c', proof_code, json.dumps(expected_tenants)]))
    assert proof['file_sha256'] == hashlib.sha256(keys_file.read_bytes()).hexdigest()
    for path, digest in preserved_files:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    save('reader-credential-mount.json', proof)
    result = {'services': after, 'only_recreated_services': list(BASE), 'unchanged_services': ['fusion', 'actions'],
              'compose_layers': len(PARTS), 'api_env_and_mounts_unchanged': True,
              'agents_existing_env_and_mounts_preserved': True, 'agents_added_env_key': KEY_VAR,
              'agents_added_read_only_directory': {'source': str(HOST_KEY_DIR), 'target': KEY_DIR},
              'reader_credential_readable_as_runtime_user': True, 'resident_worker_enabled': False,
              'original_org_memory_credentials_env_and_mount_preserved': True,
              'original_tenant_skill_credentials_env_and_mount_preserved': True,
              'schema_or_dependencies_changed': False}
    save('deployment.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
