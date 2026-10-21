"""Read-only C02 checkpoint verification after Docker reordered Binds.

Never invokes Compose up or replays deployment. The first assertion failure and
its original operator remain evidence; only Binds list order is normalized.
"""
import copy
import hashlib
import json
import os
import subprocess

from configure_triage_admission_3a import describe, env, inspect, observation, save
from deploy_triage_material_c02 import IMAGE, protected, sources
from prepare_completion_c02 import E, P


def read(path):
    return json.loads(path.read_text())


def main():
    os.umask(0o077)
    assert (E / 'deploy-started.json').is_file() and not (E / 'deployment.json').exists()
    failure = read(E / 'deployment-first-assertion-failure.json')
    assert failure['exit_code'] == 1 and failure['sorted_binds_equal']
    built = read(E / 'built-image.json')
    old = read(P / 'agents-container-before.json')
    now = inspect('socai2-agents-1')
    assert now['State']['Health']['Status'] == 'healthy'
    assert now['Image'] == built['agents'] == inspect(IMAGE)['Id'] and now['Id'] != old['Id']
    assert now['Config']['StopTimeout'] == 60
    assert env(now) == env(old) and now['Mounts'] == old['Mounts']
    before_host, after_host = copy.deepcopy(old['HostConfig']), copy.deepcopy(now['HostConfig'])
    assert before_host != after_host
    assert sorted(before_host['Binds']) == sorted(after_host['Binds'])
    before_host['Binds'] = sorted(before_host['Binds'])
    after_host['Binds'] = sorted(after_host['Binds'])
    assert before_host == after_host
    for key in ['User', 'Cmd', 'Entrypoint', 'WorkingDir', 'ExposedPorts', 'Healthcheck']:
        assert now['Config'].get(key) == old['Config'].get(key)
    code = "from pathlib import Path;import hashlib,json;print(json.dumps({'services/agents/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}))"
    runtime = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-agents-1', 'python', '-c', code]))
    assert runtime == sources() == built['source_sha256'] and len(runtime) == 184
    protected(observation(), changed_agents=True)
    result = {'before': describe(old), 'after': describe(now), 'only_recreated': 'agents',
              'image_id': built['agents'], 'source_count': len(runtime),
              'source_matches_tests_and_baked_probe': True, 'stop_grace_seconds': 60,
              'env_and_mounts_equal': True, 'host_config_equal_after_only_binds_order_normalization': True,
              'dependencies_changed': False, 'real_models': 0, 'new_business_rows': 0,
              'agents_worker_enabled': False, 'original_deploy_command_passed': False,
              'checkpoint_read_only_verification_passed': True, 'additional_recreates': 0,
              'original_failure_sha256': hashlib.sha256((E / 'deployment-first-assertion-failure.json').read_bytes()).hexdigest()}
    save(E, 'deployment.json', result)
    print(json.dumps({'checkpoint_verified': True, 'original_deploy_command_passed': False,
                      'only_original_recreate': 'agents', 'image': built['agents'], 'sources': len(runtime)}))


if __name__ == '__main__':
    main()
