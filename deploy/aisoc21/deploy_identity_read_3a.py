"""Add two dedicated read paths on guarded parents, preserving general graph disable."""
from pathlib import Path
import hashlib, json, os, subprocess, time

R = Path('/opt/sting-aisoc-socai2')
E = R / 'evidence/3a-identity-read-20261020'
BASE = {
    'api': 'sha256:41bae3dde2fdccb230622f30af99b6ef807469c930cb7b6aed1baf860eb7cd3d',
    'agents': 'sha256:90126c76cd8714fafef80c853fec595b0a6c7b702999bd7118e2cab564eae865',
}
PARTS = ['services', 'embedding', 'gateway', 'investigation', 'correlation-2a', 'identity-2a',
         'risk-2b', 'policy-2b', 'ioc-2c', 'context-2c', 'suppression-3a', 'risk-score-3a',
         'org-memory-3a', 'tenant-skill-3a', 'kb-read-3a', 'dispositions-3a', 'identity-read-3a']
ADDITIONS = {
    'api': {'env': 'AISOC_IDENTITY_GRAPH_CONFIG_FILE', 'file': '/run/secrets/identity-graph/config.json',
            'directory': '/run/secrets/identity-graph', 'host': R / 'private/identity-graph-3a'},
    'agents': {'env': 'AISOC_TRIAGE_IDENTITY_KEYS_FILE', 'file': '/run/secrets/triage-identity/keys.json',
               'directory': '/run/secrets/triage-identity', 'host': R / 'private/identity-read-3a'},
}
READERS = [('org_memory', 'org-memory'), ('tenant_skill', 'tenant-skill'),
           ('knowledge_base', 'kb-read'), ('recent_dispositions', 'dispositions')]
OLD_ENVS = {'AISOC_ORG_MEMORY_KEYS_FILE': '/run/secrets/org-memory/keys.json',
            'AISOC_TENANT_SKILLS_KEYS_FILE': '/run/secrets/tenant-skill/keys.json',
            'AISOC_TRIAGE_KB_KEYS_FILE': '/run/secrets/triage-kb/keys.json',
            'AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE': '/run/secrets/dispositions/keys.json'}


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
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
    path.chmod(0o600)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert os.geteuid() == 0
    assert not (E / 'deployment-before.json').exists(), 'Inspect prior deployment; no blind replay'
    tests = json.loads((E / 'tests-acceptance.json').read_text())
    assert tests.get('failed') == 0
    for field in ['api_passed', 'agents_passed']:
        assert type(tests.get(field)) is int and tests[field] > 0, 'Required locked-image tests not accepted: ' + field
    current_source = {str(path.relative_to(R / 'source')): sha(path)
                      for service in BASE for path in (R / f'source/services/{service}/app').rglob('*.py')}
    assert current_source == tests['tested_runtime_source_sha256'], 'Runtime differs from accepted test input'
    state = json.loads((R / 'private/app-identity-read-3a.json').read_text())
    assert state['batch'] == '3a-identity-read-20261020'
    assert sha(E / 'graph-fixtures.json') == state['graph_fixture_sha256']
    preserved_files = []
    for name, stem in READERS:
        pair = state['original_reader_credentials'][name]
        for path, digest in [(R / ('private/app-' + stem + '-3a.json'), pair['state_sha256']),
                             (R / ('private/' + stem + '-3a/keys.json'), pair['keys_sha256'])]:
            assert sha(path) == digest
            preserved_files.append((path, digest))
    org_state = json.loads((R / 'private/app-org-memory-3a.json').read_text())
    expected_tenants = sorted(state['identities'][name]['tenant_id'] for name in ['a', 'b'])
    assert expected_tenants == sorted(org_state['identities'][name]['tenant_id'] for name in ['a', 'b'])
    for name in ['reader_a', 'reader_b']:
        assert state['identities'][name]['scopes'] == ['graph:read']
    mount_digests = {}
    for name, config in ADDITIONS.items():
        file = config['host'] / Path(config['file']).name
        ds, fs = config['host'].stat(), file.stat()
        assert ds.st_uid == ds.st_gid == fs.st_uid == fs.st_gid == 10001
        assert ds.st_mode & 0o777 == 0o700 and fs.st_mode & 0o777 == 0o600
        mount_digests[name] = sha(file)
    assert mount_digests['api'] == state['graph_config_sha256']
    keys_file = ADDITIONS['agents']['host'] / 'keys.json'
    assert json.loads(keys_file.read_text()) == {
        state['identities'][name]['tenant_id']: state['identities']['reader_' + name]['key'] for name in ['a', 'b']}
    before = {name: inspect('socai2-' + name + '-1') for name in ['api', 'agents', 'fusion', 'actions']}
    before_env = {name: env_values(item) for name, item in before.items()}
    assert before_env['api'].get('AISOC_DISABLE_NEO4J', '').lower() == 'true'
    assert before_env['agents'].get('AISOC_AGENT_KAFKA_DISABLE') == '1'
    assert all(before_env['agents'].get(key) == value for key, value in OLD_ENVS.items())
    for name, digest in BASE.items():
        assert ADDITIONS[name]['env'] not in before_env[name], 'New layer already applied'
        assert ADDITIONS[name]['directory'] not in {mount['Destination'] for mount in before[name]['Mounts']}
        assert before[name]['Image'] == digest
        assert inspect(f'socai2-{name}:dispositions-3a-20261020')['Id'] == digest, 'Cached parent changed'
    save('deployment-before.json', {name: describe(item) for name, item in before.items()})
    built = {}
    for name in BASE:
        subprocess.run(['docker', 'build', '--pull=false', '-f', f'deploy/aisoc21/build/Dockerfile.{name}-identity-read-3a',
                        '-t', f'socai2-{name}:identity-read-3a-20261020', '.'], cwd=R / 'source', check=True)
        built[name] = inspect(f'socai2-{name}:identity-read-3a-20261020')['Id']
    save('built-images.json', built)
    command = ['docker', 'compose', '--project-directory', str(R)]
    for part in PARTS:
        command += ['-f', str(R / f'source/deploy/aisoc21/compose.{part}.yml')]
    assert len(PARTS) == 17
    subprocess.run(command + ['config', '--quiet'], check=True)
    subprocess.run(command + ['up', '-d', '--no-deps', '--pull', 'never', *BASE], check=True, capture_output=True)
    after = {}
    for name, config in ADDITIONS.items():
        for _ in range(45):
            item = inspect('socai2-' + name + '-1')
            if item['State'].get('Health', {}).get('Status') == 'healthy':
                break
            time.sleep(1)
        else:
            raise RuntimeError('Unhealthy ' + name)
        assert item['Image'] == built[name]
        values = env_values(item)
        assert values.get(config['env']) == config['file']
        assert {key: value for key, value in values.items() if key != config['env']} == before_env[name]
        mounts = {mount['Destination']: mount for mount in item['Mounts']}
        old_mounts = {mount['Destination']: mount for mount in before[name]['Mounts']}
        assert set(mounts) == set(old_mounts) | {config['directory']}
        assert {target: mount for target, mount in mounts.items() if target != config['directory']} == old_mounts
        addition = mounts[config['directory']]
        assert addition['Type'] == 'bind' and addition['Source'] == str(config['host']) and not addition['RW']
        assert item['Config']['User'] == '10001:10001' and item['HostConfig']['ReadonlyRootfs']
        after[name] = {'id': item['Id'], 'image': item['Image'], 'healthy': True, 'env_sha256': env_hash(values)}
    assert env_values(inspect('socai2-api-1')).get('AISOC_DISABLE_NEO4J', '').lower() == 'true'
    for name in ['fusion', 'actions']:
        assert describe(inspect('socai2-' + name + '-1')) == describe(before[name]), 'Unrelated service changed: ' + name
    # These fresh resident imports read private files but do not query graph/API or call a model.
    common = '''import hashlib,json,os,pathlib,sys
p=pathlib.Path(os.environ[sys.argv[1]]);info=p.stat();parent=p.parent.stat()
assert os.getuid()==10001 and info.st_uid==info.st_gid==parent.st_uid==parent.st_gid==10001
assert info.st_mode&0o777==0o600 and parent.st_mode&0o777==0o700
data=json.loads(p.read_text());assert isinstance(data,dict) and data
out={'uid':os.getuid(),'directory_mode':'0700','file_mode':'0600','file_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
'''
    agent_code = common + '''from app.context import identity
from app.context.organisation_memory import _credential
from app.workers.fused_alert_consumer import worker_enabled
expected=json.loads(sys.argv[2]);assert sorted(data)==expected
for variable in ['AISOC_TRIAGE_IDENTITY_KEYS_FILE','AISOC_ORG_MEMORY_KEYS_FILE','AISOC_TENANT_SKILLS_KEYS_FILE','AISOC_TRIAGE_KB_KEYS_FILE','AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE']:
 assert all(_credential(tenant,keys_file_env=variable) for tenant in expected)
assert not worker_enabled();out.update(mapped_tenants=len(data),resident_worker_enabled=False,identity_reader_fresh_import=True)
print('RESULT_JSON='+json.dumps(out))'''
    api_code = common + '''from app.db import neo4j
assert os.environ.get('AISOC_DISABLE_NEO4J','').lower()=='true'
assert getattr(neo4j,'_driver',None) is None
assert neo4j._identity_read_config()==data
out.update(general_graph_disabled=True,general_graph_driver_uninitialized=True,dedicated_config_validated=True,graph_connection_or_schema_called=False)
print('RESULT_JSON='+json.dumps(out))'''
    proofs = {}
    for name, code in [('agents', agent_code), ('api', api_code)]:
        output = subprocess.check_output(['docker', 'exec', 'socai2-' + name + '-1', 'python', '-c', code,
                                          ADDITIONS[name]['env'], json.dumps(expected_tenants)]).decode()
        marked = [line.removeprefix('RESULT_JSON=') for line in output.splitlines() if line.startswith('RESULT_JSON=')]
        assert len(marked) == 1
        proofs[name] = json.loads(marked[0])
        assert proofs[name]['file_sha256'] == mount_digests[name]
    for path, digest in preserved_files:
        assert sha(path) == digest
    assert sha(E / 'graph-fixtures.json') == state['graph_fixture_sha256']
    save('reader-credential-mount.json', proofs['agents'])
    save('identity-graph-config-mount.json', proofs['api'])
    result = {'services': after, 'only_recreated_services': list(BASE), 'unchanged_services': ['fusion', 'actions'],
              'compose_layers': len(PARTS), 'api_existing_env_and_mounts_preserved': True,
              'api_added_env_key': ADDITIONS['api']['env'],
              'api_added_read_only_directory': {'source': str(ADDITIONS['api']['host']), 'target': ADDITIONS['api']['directory']},
              'agents_existing_env_and_mounts_preserved': True, 'agents_added_env_key': ADDITIONS['agents']['env'],
              'agents_added_read_only_directory': {'source': str(ADDITIONS['agents']['host']), 'target': ADDITIONS['agents']['directory']},
              'private_files_readable_as_runtime_user': True, 'resident_worker_enabled': False,
              'general_graph_disabled': True, 'general_graph_initialization_or_schema_called': False,
              'original_four_reader_credentials_env_and_mounts_preserved': True,
              'graph_fixture_manifest_unchanged': True, 'schema_or_dependencies_changed': False}
    save('deployment.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
