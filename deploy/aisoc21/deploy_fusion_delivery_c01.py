"""C01 checkpointed build/deploy. Only Fusion can be recreated.

Run `build TEST_ATTEMPT`, then the independent infrastructure probe, then
`deploy`. A failure requires checkpoint inspection; phases cannot be replayed.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

from configure_triage_admission_3a import PARTS as PRIOR, compose, describe, env, inspect, observation, private_hashes, save

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
E = R / 'evidence/c01-fusion-delivery-20261020'
P = R / 'private/completion-c01'
PARTS = PRIOR + ['fusion-delivery-c01']
PARENT = 'sha256:9be177b961edd6bbc0951dbb92966aaccb53c81438f82e5677ede6ae47f2d07b'
IMAGE = 'socai2-fusion:delivery-c01-20261020'
CHANGED = {'services/fusion/app/' + p for p in ['workers/consumer.py', 'services/alert_sink.py', 'services/dlq.py', 'services/dlq_sink.py']}
ADDED = {'services/fusion/app/services/delivery_recovery.py'}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    return {str(p.relative_to(S)): sha(p) for p in sorted((S / 'services/fusion/app').rglob('*.py'))}


def protect_old_state(now, *, allow_fusion=False):
    old = read(E / 'before.json')
    assert now['environment']['volumes'] == old['environment']['volumes']
    assert set(now['environment']['containers']) == set(old['environment']['containers'])
    for name, value in old['environment']['containers'].items():
        if allow_fusion and name == 'socai2-fusion-1':
            continue
        assert now['environment']['containers'][name] == value, 'Other container changed: ' + name
    for key in ['budget', 'readers', 'policy_sha256', 'migrations', 'gateway']:
        assert now[key] == old[key], 'Frozen input changed: ' + key
    for table, hashes in old['materials'].items():
        assert set(hashes).issubset(now['materials'][table]), 'Old material changed: ' + table
    assert private_hashes() == read(E / 'private-input-hashes.json')


OFFSETS = '''import asyncio,json
from aiokafka import AIOKafkaConsumer,TopicPartition
from app.core.config import settings
from app.core.kafka_security import kafka_client_kwargs
async def main():
 c=AIOKafkaConsumer(bootstrap_servers=settings.kafka_bootstrap_servers,group_id=settings.kafka_consumer_group,enable_auto_commit=False,**kafka_client_kwargs());await c.start()
 try:
  ps=c.partitions_for_topic(settings.kafka_topic_alerts_raw)
  if ps is None:
   await c.topics();ps=c.partitions_for_topic(settings.kafka_topic_alerts_raw)
  assert ps
  tps=[TopicPartition(settings.kafka_topic_alerts_raw,p) for p in sorted(ps)];c.assign(tps);ends=await c.end_offsets(tps)
  rows=[{'partition':tp.partition,'committed':await c.committed(tp),'end':ends[tp]} for tp in tps]
  print(json.dumps({'topic':settings.kafka_topic_alerts_raw,'group':settings.kafka_consumer_group,'partitions':rows}))
 finally:await c.stop()
asyncio.run(main())'''


def raw_offsets():
    result = subprocess.run(['docker', 'exec', 'socai2-fusion-1', 'python', '-c', OFFSETS], capture_output=True, text=True)
    assert result.returncode == 0, 'Raw offset read failed; inspect privately'
    return json.loads(result.stdout.splitlines()[-1])


def build(attempt):
    assert (E / 'prepared.json').is_file() and not (E / 'build-started.json').exists()
    tests = read(E / f'tests-fusion-{attempt}.json')
    assert tests['exit_code'] == tests['failed'] == tests['errors'] == 0 and tests['passed'] > 0
    assert tests['source_unchanged'] and tests['test_inputs_unchanged']
    assert sources() == tests['tested_runtime_source_sha256']
    assert all(sha(S / p) == h for p, h in tests['test_input_sha256'].items())
    before = observation()
    protect_old_state(before)
    assert inspect('socai2-fusion-1')['Image'] == inspect('socai2-fusion:risk-score-3a-20261020')['Id'] == PARENT
    parent = read(E / 'parent-source.json')
    current = sources()
    assert set(current) - set(parent) == ADDED and not (set(parent) - set(current))
    assert {p for p in parent if parent[p] != current[p]} == CHANGED
    originals = E / 'parent-sources'
    originals.mkdir(mode=0o700)
    for p in sorted(CHANGED):
        destination = originals / p
        destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        source = '/app/app/' + p.removeprefix('services/fusion/app/')
        subprocess.run(['docker', 'cp', 'socai2-fusion-1:' + source, str(destination)], check=True, capture_output=True)
        destination.chmod(0o600)
        assert sha(destination) == parent[p]
    offsets = raw_offsets()
    assert all(v['committed'] == v['end'] for v in offsets['partitions']), 'Old raw backlog needs separate review'
    save(E, 'production-offsets-before.json', offsets)
    save(E, 'build-started.json', {'test_attempt': attempt, 'source_sha256': current,
         'parent': PARENT, 'only_changed': sorted(CHANGED), 'only_added': sorted(ADDED),
         'dockerfile_sha256': sha(S / 'deploy/aisoc21/build/Dockerfile.fusion-delivery-c01')})
    with (E / 'build-fusion.log').open('x') as output:
        result = subprocess.run(['docker', 'build', '--pull=false', '--network=none', '-f',
            'deploy/aisoc21/build/Dockerfile.fusion-delivery-c01', '-t', IMAGE, '.'], cwd=S, stdout=output, stderr=subprocess.STDOUT)
    (E / 'build-fusion.log').chmod(0o600)
    assert result.returncode == 0, 'Build failed; preserve checkpoint'
    built = inspect(IMAGE)['Id']
    assert len(PARTS) == 23
    configs = []
    for parts in [PRIOR, PARTS]:
        result = subprocess.run(compose(parts) + ['config', '--format', 'json'], capture_output=True, text=True)
        assert result.returncode == 0
        configs.append(json.loads(result.stdout))
    old, desired = configs
    expected = json.loads(json.dumps(old))
    expected['services']['fusion']['image'] = IMAGE
    assert expected == desired, 'Compose changed more than Fusion image'
    save(P, 'compose-before.json', old)
    save(P, 'compose-desired.json', desired)
    rollback = {'name': 'socai2', 'services': {'fusion': old['services']['fusion']},
                'networks': {key: {'name': value['name'], 'external': True} for key, value in old['networks'].items()}}
    assert not rollback['services']['fusion'].get('depends_on')
    save(P, 'rollback.fusion.json', rollback)
    cmd = ['docker', 'compose', '--project-directory', str(R), '-f', str(P / 'rollback.fusion.json')]
    assert subprocess.run(cmd + ['config', '--quiet'], capture_output=True).returncode == 0
    save(E, 'built-image.json', {'fusion': built, 'parent': PARENT, 'test_attempt': attempt,
         'source_sha256': current, 'source_count': len(current), 'compose_layers': len(PARTS),
         'layer_inputs': {f'deploy/aisoc21/compose.{part}.yml': sha(S / f'deploy/aisoc21/compose.{part}.yml') for part in PARTS},
         'rollback_private_path': str(P / 'rollback.fusion.json'), 'rollback_sha256': sha(P / 'rollback.fusion.json'),
         'dependencies_changed': False, 'runtime_services_changed': 0})
    print(json.dumps({'built': built, 'sources': len(current), 'runtime_changed': False, 'test_attempt': attempt}))


def deploy():
    built = read(E / 'built-image.json')
    assert not (E / 'deploy-started.json').exists()
    acceptance = read(E / 'probe/acceptance.json')
    assert acceptance['accepted'] is True and acceptance['real_models'] == 0
    assert acceptance['image_id'] == built['fusion'] and acceptance['source_sha256'] == built['source_sha256']
    boundary = read(E / 'boundaries/acceptance.json')
    assert boundary['accepted'] and boundary['real_models'] == 0
    assert boundary['image_id'] == built['fusion'] and boundary['source_sha256'] == built['source_sha256']
    audit = read(E / 'predeploy-independent-audit.json')
    assert audit['accepted'] and audit['image_id'] == built['fusion']
    assert sources() == built['source_sha256']
    assert all(sha(S / p) == h for p, h in built['layer_inputs'].items())
    assert inspect(IMAGE)['Id'] == built['fusion']
    protect_old_state(observation())
    old = read(P / 'fusion-container-before.json')
    assert describe(inspect('socai2-fusion-1')) == describe(old)
    offsets = raw_offsets()
    assert offsets == read(E / 'production-offsets-before.json')
    actual = json.loads(subprocess.check_output(compose(PARTS) + ['config', '--format', 'json']))
    assert actual == read(P / 'compose-desired.json')
    save(E, 'deploy-started.json', {'before': describe(old), 'command': compose(PARTS) + ['up', '-d', '--no-deps', '--pull', 'never', '--no-build', 'fusion']})
    with (E / 'compose-up.log').open('x') as output:
        result = subprocess.run(compose(PARTS) + ['up', '-d', '--no-deps', '--pull', 'never', '--no-build', 'fusion'], stdout=output, stderr=subprocess.STDOUT)
    (E / 'compose-up.log').chmod(0o600)
    assert result.returncode == 0, 'Inspect checkpoint; do not repeat deployment'
    for _ in range(50):
        now = inspect('socai2-fusion-1')
        if now['State'].get('Health', {}).get('Status') == 'healthy':
            break
        time.sleep(1)
    assert now['State']['Health']['Status'] == 'healthy' and now['Image'] == built['fusion'] and now['Id'] != old['Id']
    assert env(now) == env(old) and now['Mounts'] == old['Mounts'] and now['HostConfig'] == old['HostConfig']
    for k in ['User', 'Cmd', 'Entrypoint', 'WorkingDir', 'ExposedPorts', 'Healthcheck']:
        assert now['Config'].get(k) == old['Config'].get(k)
    code = "from pathlib import Path;import hashlib,json;print(json.dumps({'services/fusion/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}))"
    actual_source = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-fusion-1', 'python', '-c', code]))
    assert actual_source == built['source_sha256']
    protect_old_state(observation(), allow_fusion=True)
    assert raw_offsets() == offsets
    save(E, 'deployment.json', {'before': describe(old), 'after': describe(now), 'runtime_source_matches_tests': True,
         'source_count': len(actual_source), 'only_recreated': 'fusion', 'env_mounts_host_config_equal': True,
         'production_offsets_unchanged': True, 'worker_agents_disabled': True, 'dependencies_changed': False})
    print(json.dumps({'deployed': True, 'only_recreated': 'fusion', 'image': built['fusion'], 'sources': len(actual_source)}))


if __name__ == '__main__':
    os.umask(0o077)
    if len(sys.argv) == 3 and sys.argv[1] == 'build':
        build(sys.argv[2])
    elif sys.argv[1:] == ['deploy']:
        deploy()
    else:
        raise SystemExit('Usage: deploy_fusion_delivery_c01.py build TEST_ATTEMPT | deploy')
