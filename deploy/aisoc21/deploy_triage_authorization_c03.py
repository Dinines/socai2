"""C03-02C-01 exact-parent build, offline candidate probe and Agents-only deployment."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

from configure_triage_admission_3a import compose, inspect, describe, env, observation, private_hashes, save
from deploy_triage_reasoning_c03 import PARTS as PRIOR
from prepare_triage_authorization_c03 import R, S, E, P, FILES, PARENT
LOCK = "services/agents/app/llm/prompts.lock.json"

PARTS = PRIOR + ['triage-authorization-c03']
IMAGE = 'socai2-agents:triage-authorization-c03-20261021'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    return {str(p.relative_to(S)): sha(p) for p in sorted((S / 'services/agents/app').rglob('*.py'))}


def protected(now, *, changed_agents=False):
    before = read(E / 'before.json')
    if changed_agents:
        now = json.loads(json.dumps(now))
        now['environment']['containers']['socai2-agents-1'] = before['environment']['containers']['socai2-agents-1']
    assert now == before, 'Environment or data drift; inspect without blindly replaying'
    assert private_hashes() == read(E / 'private-input-hashes.json')


def build(attempt):
    assert (E / 'prepared.json').is_file() and not (E / 'build-started.json').exists()
    prepared = read(E / 'prepared.json')
    tests = read(E / f'tests-agents-{attempt}.json')
    assert tests['exit_code'] == tests['failed'] == tests['errors'] == 0 and tests['passed'] == 88
    assert tests['source_unchanged'] and tests['test_inputs_unchanged']
    current = sources()
    assert tests['tested_runtime_source_sha256'] == current
    assert all(sha(S / p) == h for p, h in tests['test_input_sha256'].items())
    parent = prepared['full_parent_runtime_sources']
    assert set(current) == set(parent) and len(current) == 184
    assert {p for p in current if current[p] != parent[p]} == set(FILES) - {LOCK}
    assert inspect('socai2-agents-1')['Image'] == inspect('socai2-agents:triage-reasoning-c03-20261021')['Id'] == PARENT
    protected(observation())
    old = read(P / 'agents-container-before.json')
    assert old['Config']['StopTimeout'] == 60
    assert sha(S / LOCK) != prepared['parent_sources'][LOCK]
    assert len(PARTS) == 26
    configs = []
    for parts in [PRIOR, PARTS]:
        result = subprocess.run(compose(parts) + ['config', '--format', 'json'], capture_output=True, text=True)
        assert result.returncode == 0, 'Compose render failed'
        configs.append(json.loads(result.stdout))
    prior, desired = configs
    agent = desired['services']['agents']
    assert agent['stop_grace_period'] in ['60s', '1m0s']
    assert prior['services']['agents']['stop_grace_period'] == agent['stop_grace_period']
    expected = json.loads(json.dumps(prior))
    expected['services']['agents'].update(image=IMAGE, stop_grace_period=agent['stop_grace_period'])
    assert expected == desired, 'Unexpected Compose change'
    save(P, 'compose-before.json', prior)
    save(P, 'compose-desired.json', desired)
    rollback = {'name': 'socai2', 'services': {'agents': prior['services']['agents']},
                'networks': {k: {'name': v['name'], 'external': True} for k, v in prior['networks'].items()}}
    assert not rollback['services']['agents'].get('depends_on')
    save(P, 'rollback.agents.json', rollback)
    cmd = ['docker', 'compose', '--project-directory', str(R), '-f', str(P / 'rollback.agents.json')]
    assert subprocess.run(cmd + ['config', '--quiet'], capture_output=True).returncode == 0
    save(E, 'build-started.json', {'test_attempt': attempt, 'source_sha256': current, 'parent': PARENT,
         'dockerfile_sha256': sha(S / 'deploy/aisoc21/build/Dockerfile.agents-triage-authorization-c03')})
    with (E / 'build-agents.log').open('x') as output:
        result = subprocess.run(['docker', 'build', '--pull=false', '--network=none', '-f',
            'deploy/aisoc21/build/Dockerfile.agents-triage-authorization-c03', '-t', IMAGE, '.'], cwd=S, stdout=output, stderr=subprocess.STDOUT)
    (E / 'build-agents.log').chmod(0o600)
    assert result.returncode == 0, 'Inspect build checkpoint; do not replay'
    built = inspect(IMAGE)['Id']
    save(E, 'built-image.json', {'agents': built, 'parent': PARENT, 'test_attempt': attempt,
         'source_sha256': current, 'source_count': len(current), 'lock_sha256': sha(S / LOCK), 'compose_layers': 26,
         'source_layers': 23, 'stop_grace_seconds': 60,
         'layer_inputs': {f'deploy/aisoc21/compose.{p}.yml': sha(S / f'deploy/aisoc21/compose.{p}.yml') for p in PARTS},
         'rollback_private_path': str(P / 'rollback.agents.json'), 'rollback_sha256': sha(P / 'rollback.agents.json'),
         'dependencies_changed': False, 'runtime_services_changed': 0})
    print(json.dumps({'built': built, 'sources': len(current), 'runtime_changed': False, 'test_attempt': attempt}))


def deploy():
    built = read(E / 'built-image.json')
    assert not (E / 'deploy-started.json').exists()
    accepted = read(E / 'probe/acceptance.json')
    assert accepted['accepted'] and accepted['real_models'] == 0
    assert accepted['image_id'] == built['agents'] and accepted['source_sha256'] == built['source_sha256']
    audit = read(E / 'predeploy-independent-audit.json')
    assert audit['accepted'] and audit['image_id'] == built['agents']
    assert sources() == built['source_sha256'] and inspect(IMAGE)['Id'] == built['agents']
    assert sha(S / LOCK) == built['lock_sha256']
    assert all(sha(S / p) == h for p, h in built['layer_inputs'].items())
    protected(observation())
    old = read(P / 'agents-container-before.json')
    assert describe(inspect('socai2-agents-1')) == describe(old)
    actual = json.loads(subprocess.check_output(compose(PARTS) + ['config', '--format', 'json']))
    assert actual == read(P / 'compose-desired.json')
    save(E, 'deploy-started.json', {'before': describe(old), 'command': compose(PARTS) + ['up', '-d', '--no-deps', '--pull', 'never', '--no-build', 'agents']})
    with (E / 'compose-up.log').open('x') as output:
        result = subprocess.run(compose(PARTS) + ['up', '-d', '--no-deps', '--pull', 'never', '--no-build', 'agents'], stdout=output, stderr=subprocess.STDOUT)
    (E / 'compose-up.log').chmod(0o600)
    assert result.returncode == 0, 'Inspect checkpoint; do not repeat service recreation'
    for _ in range(50):
        now = inspect('socai2-agents-1')
        if now['State'].get('Health', {}).get('Status') == 'healthy':
            break
        time.sleep(1)
    assert now['State']['Health']['Status'] == 'healthy' and now['Image'] == built['agents'] and now['Id'] != old['Id']
    assert now['Config']['StopTimeout'] == 60
    assert env(now) == env(old)
    assert sorted(now['Mounts'], key=lambda m: m['Destination']) == sorted(old['Mounts'], key=lambda m: m['Destination'])
    host_before, host_after = json.loads(json.dumps(old['HostConfig'])), json.loads(json.dumps(now['HostConfig']))
    host_before['Binds'], host_after['Binds'] = sorted(host_before['Binds']), sorted(host_after['Binds'])
    assert host_before == host_after
    for key in ['User', 'Cmd', 'Entrypoint', 'WorkingDir', 'ExposedPorts', 'Healthcheck']:
        assert now['Config'].get(key) == old['Config'].get(key)
    code = "from pathlib import Path;import hashlib,json;print(json.dumps({'services/agents/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}))"
    runtime = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-agents-1', 'python', '-c', code]))
    assert runtime == built['source_sha256']
    actual_lock = subprocess.check_output(['docker', 'exec', 'socai2-agents-1', 'python', '-c', "from pathlib import Path;import hashlib;print(hashlib.sha256(Path('/app/app/llm/prompts.lock.json').read_bytes()).hexdigest())"], text=True).strip()
    assert actual_lock == built['lock_sha256']
    protected(observation(), changed_agents=True)
    save(E, 'deployment.json', {'before': describe(old), 'after': describe(now), 'only_recreated': 'agents',
         'image_id': built['agents'], 'source_count': len(runtime), 'source_matches_tests_and_baked_probe': True,
         'stop_grace_seconds': 60, 'env_mounts_host_config_semantically_equal': True, 'lock_sha256': actual_lock, 'dependencies_changed': False,
         'real_models': 0, 'new_business_rows': 0, 'agents_worker_enabled': False})
    print(json.dumps({'deployed': True, 'only_recreated': 'agents', 'image': built['agents'], 'sources': len(runtime), 'stop_grace_seconds': 60}))


def probe():
    built = read(E / 'built-image.json')
    assert sources() == built['source_sha256'] and inspect(IMAGE)['Id'] == built['agents']
    assert sha(S / LOCK) == built['lock_sha256']
    protected(observation())
    directory = E / 'probe'
    directory.mkdir(mode=0o700, exist_ok=False)
    os.chown(directory, 10001, 10001)
    operator = S / 'deploy/aisoc21/probe_triage_authorization_c03.py'
    contract = {'image_id': built['agents'], 'source_sha256': built['source_sha256'],
                'operator_sha256': sha(operator), 'lock_sha256': built['lock_sha256'],
                'unit_test_record_sha256': sha(E / f"tests-agents-{built['test_attempt']}.json"),
                'fixture_sha256': sha(E / 'probe-fixture.json')}
    assert contract['fixture_sha256'] == read(E / 'prepared.json')['probe_fixture_sha256']
    assert operator.is_file() and operator.stat().st_mode & 0o004, 'UID10001 operator must be readable before Docker'
    save(directory, 'contract.json', contract)
    os.chown(directory / 'contract.json', 10001, 10001)
    save(E, 'probe-started.json', {'image_id': built['agents'], 'operator_sha256': sha(operator),
         'network': 'none', 'private_mounts_or_env_files': False, 'synthetic_only': True})
    values = {'ENVIRONMENT': 'production', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': '/app',
              'C03_PROBE_IMAGE_ID': built['agents'], 'C03_PROBE_SYNTHETIC_ONLY': '1',
              'LLM_GATEWAY_URL': 'http://127.0.0.1.invalid/v1',
              'LITELLM_MASTER_KEY': 'synthetic-c03-no-credential',
              'AISOC_LLM_RESPONSE_CACHE': '0', 'AISOC_PSEUDONYMIZE_EGRESS': '0',
              'AISOC_AGENT_KAFKA_DISABLE': '1', 'OTEL_SDK_DISABLED': 'true',
              'DATABASE_DSN': '', 'DATABASE_URL': '', 'OPENAI_API_KEY': '', 'ANTHROPIC_API_KEY': '',
              'HTTP_PROXY': '', 'HTTPS_PROXY': '', 'ALL_PROXY': ''}
    name = 'socai2-c03-authorization-offline-probe'
    command = ['docker', 'run', '--rm', '--pull', 'never', '--name', name, '--network', 'none',
               '--user', '10001:10001', '--read-only', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges:true', '--tmpfs', '/tmp:rw,nosuid,nodev,size=64m']
    for key, value in values.items():
        command += ['-e', key + '=' + value]
    command += ['-v', str(S) + ':/source:ro', '-v', str(directory) + ':/evidence:rw',
                '-v', str(E / 'probe-fixture.json') + ':/fixtures/materials.json:ro', '-w', '/app',
                built['agents'], 'python', '/source/deploy/aisoc21/probe_triage_authorization_c03.py', 'inside']
    log = E / 'probe.log'
    with log.open('xb') as output:
        try:
            result = subprocess.run(command, capture_output=True, timeout=60)
            output.write(result.stdout + result.stderr)
            code = result.returncode
        except subprocess.TimeoutExpired as exc:
            output.write((exc.stdout or b'') + (exc.stderr or b''))
            cleanup = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
            output.write(b'\nDeadline: removed only the named C03-02C-01 offline probe container.\n')
            output.write(cleanup.stdout + cleanup.stderr)
            code = 124
    log.chmod(0o600)
    save(E, 'probe-exit.json', {'exit_code': code, 'log_sha256': sha(log),
         'source_unchanged': sources() == built['source_sha256'], 'private_mounts_or_env_files': False})
    assert code == 0, 'Inspect offline checkpoint; do not replay a prior result'
    accepted = read(directory / 'acceptance.json')
    assert accepted['accepted'] and accepted['real_models'] == 0 and accepted['synthetic_only']
    assert accepted['image_id'] == built['agents'] and accepted['source_sha256'] == built['source_sha256']
    assert accepted['fixture_sha256'] == contract['fixture_sha256'] and accepted['mock_http_requests'] == 4
    protected(observation())
    print(json.dumps({'offline_probe_accepted': True, 'candidate': built['agents'], 'mock_http_requests': 4,
                      'real_models': 0, 'new_business_rows': 0, 'network': 'none'}))


if __name__ == '__main__':
    os.umask(0o077)
    if len(sys.argv) == 3 and sys.argv[1] == 'build':
        build(sys.argv[2])
    elif sys.argv[1:] == ['deploy']:
        deploy()
    elif sys.argv[1:] == ['probe']:
        probe()
    else:
        raise SystemExit('Usage: deploy_triage_authorization_c03.py build TEST_ATTEMPT | probe | deploy')
