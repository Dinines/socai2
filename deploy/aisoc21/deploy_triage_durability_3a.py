"""Build the two-file correction on the exact cached parent; update only Agents."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

from prepare_triage_durability_3a import R, E, PARENT, save

PARTS = ['services', 'embedding', 'gateway', 'investigation', 'correlation-2a', 'identity-2a',
         'risk-2b', 'policy-2b', 'ioc-2c', 'context-2c', 'suppression-3a', 'risk-score-3a',
         'org-memory-3a', 'tenant-skill-3a', 'kb-read-3a', 'dispositions-3a', 'identity-read-3a',
         'triage-durability-3a']


def inspect(name):
    return json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]


def describe(item):
    return {'id': item['Id'], 'image': item['Image'], 'started_at': item['State']['StartedAt'],
            'restart_count': item['RestartCount'], 'mounts': item['Mounts'],
            'env_sha256': hashlib.sha256(json.dumps(sorted(item['Config']['Env'])).encode()).hexdigest()}


def main(mode='deploy'):
    assert mode in {'deploy', 'verify-existing'} and os.geteuid() == 0
    assert not (E / 'deployment.json').exists()
    assert (E / 'durability-before-complete.json').is_file(), 'Preserve before behavior before deploying'
    tests = json.loads((E / 'tests-acceptance.json').read_text())
    assert tests['failed'] == 0 and tests['agents_passed'] > 0
    source = {str(path.relative_to(R / 'source')): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in (R / 'source/services/agents/app').rglob('*.py')}
    assert source == tests['tested_runtime_source_sha256']
    for name, digest in tests['test_input_sha256'].items():
        assert hashlib.sha256((R / 'source' / name).read_bytes()).hexdigest() == digest
    state = json.loads((R / 'private/app-triage-durability-3a.json').read_text())
    image = 'socai2-agents:triage-durability-3a-20261020'
    command = ['docker', 'compose', '--project-directory', str(R)]
    assert len(PARTS) == 18
    for part in PARTS:
        command += ['-f', str(R / ('source/deploy/aisoc21/compose.' + part + '.yml'))]
    subprocess.run(command + ['config', '--quiet'], check=True, capture_output=True)
    if mode == 'deploy':
        assert not (E / 'deployment-before.json').exists()
        before = {name: inspect('socai2-' + name + '-1') for name in ['api', 'fusion', 'agents', 'actions']}
        assert {name: item['Image'] for name, item in before.items()} == state['images']
        assert before['agents']['Image'] == inspect('socai2-agents:identity-read-3a-20261020')['Id'] == PARENT
        values = dict(value.split('=', 1) for value in before['agents']['Config']['Env'] if '=' in value)
        assert values['AISOC_AGENT_KAFKA_DISABLE'] == '1'
        original = {name: describe(item) for name, item in before.items()}
        save('deployment-before.json', original)
        subprocess.run(['docker', 'build', '--pull=false', '-f', 'deploy/aisoc21/build/Dockerfile.agents-triage-durability-3a',
                        '-t', image, '.'], cwd=R / 'source', check=True)
        built = inspect(image)['Id']
        save('built-images.json', {'agents': built, 'parent': PARENT})
        subprocess.run(command + ['up', '-d', '--no-deps', '--pull', 'never', 'agents'], check=True, capture_output=True)
    else:
        assert (E / 'deployment-recovery-preconditions.json').is_file()
        original = json.loads((E / 'deployment-before.json').read_text())
        built = json.loads((E / 'built-images.json').read_text())['agents']
        assert inspect(image)['Id'] == built
    for _ in range(45):
        after = inspect('socai2-agents-1')
        if after['State'].get('Health', {}).get('Status') == 'healthy':
            break
        time.sleep(1)
    else:
        raise RuntimeError('Agents unhealthy; inspect checkpoints without blind recreation')
    assert after['Image'] == built and after['Id'] != original['agents']['id']
    assert describe(after)['env_sha256'] == original['agents']['env_sha256']
    assert {m['Destination']: m for m in after['Mounts']} == {m['Destination']: m for m in original['agents']['mounts']}
    assert after['Config']['User'] == '10001:10001' and after['HostConfig']['ReadonlyRootfs']
    for name in ['api', 'fusion', 'actions']:
        assert describe(inspect('socai2-' + name + '-1')) == original[name]
    code = "from pathlib import Path;import hashlib,json;print(json.dumps({'services/agents/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}))"
    actual = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-agents-1', 'python', '-c', code]))
    assert actual == source
    resident = '''import json,os
from app.context.organisation_memory import _credential
from app.workers.fused_alert_consumer import worker_enabled
assert os.getuid()==10001 and not worker_enabled()
variables=['AISOC_ORG_MEMORY_KEYS_FILE','AISOC_TENANT_SKILLS_KEYS_FILE','AISOC_TRIAGE_KB_KEYS_FILE','AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE','AISOC_TRIAGE_IDENTITY_KEYS_FILE']
tenants=json.loads(__import__('sys').argv[1])
assert all(_credential(tenant,keys_file_env=variable) for tenant in tenants for variable in variables)
print(json.dumps({'uid':os.getuid(),'reader_maps_readable':5,'mapped_tenants':len(tenants),'worker_enabled':False}))'''
    tenants = [state['identities'][name]['tenant_id'] for name in ['a', 'b']]
    proof = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-agents-1', 'python', '-c', resident, json.dumps(tenants)]))
    result = {'images': {'agents': built}, 'old_image': PARENT, 'services': {'agents': describe(after)},
              'only_recreated_services': ['agents'], 'compose_layers': 18,
              'env_and_mounts_preserved': True, 'runtime_source_hashes_match_tests': True,
              'dependencies_schema_or_prompts_changed': False, 'resident_reader_mount_check': proof,
              'resident_worker_enabled': False, 'verification_mode': mode,
              'rebuild_or_recreate_in_recovery': False}
    save('deployment.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main(*sys.argv[1:])
