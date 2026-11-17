"""Verify the already created replacement; account for Docker create/run defaults."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

v = json.load(sys.stdin)
c = v['candidate']
root = Path(c['root'])
key = 'AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS'


def run(args, body=None):
    result = subprocess.run(args, input=body, capture_output=True, text=True,
                            timeout=c['command_timeout_seconds'], check=False)
    if result.returncode:
        with (root/'private'/(v['batch_id']+'-input-guard-finish-error.txt')).open('x') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(result.stderr)
        raise RuntimeError('command_failed_private_detail_retained')
    return result.stdout


old, new = json.loads(run(['docker', 'inspect', c['container'], v['staged_container']]))
assert old['Id'] == v['previous_container_id'] and new['Id'] == v['created_container_id']
assert old['State']['Status'] == 'exited' and old['State']['ExitCode'] == 0
assert new['State']['Status'] == 'created' and old['Image'] == new['Image'] == c['image']
assert not any('analysis_dispatch_runtime' in row.get('Command', '') for row in
               (json.loads(line) for line in run(['docker', 'ps', '--no-trunc', '--format', '{{json .}}']).splitlines()))
old_env = dict(line.split('=', 1) for line in old['Config']['Env'])
new_env = dict(line.split('=', 1) for line in new['Config']['Env'])
assert new_env == {**old_env, key: str(v['prepared_bytes'])}
host_delta = {k: {'old': value, 'new': new['HostConfig'].get(k)} for k, value in old['HostConfig'].items()
              if new['HostConfig'].get(k) != value}
assert host_delta == {'OomKillDisable': {'old': None, 'new': False}}
ignored = {'Hostname', 'Env', 'AttachStdout', 'AttachStderr'}
assert {k: value for k, value in new['Config'].items() if k not in ignored} == {
    k: value for k, value in old['Config'].items() if k not in ignored}
assert all(old['Config'][k] is False and new['Config'][k] is True for k in ('AttachStdout', 'AttachStderr'))
mount_keys = ('Type', 'Source', 'Destination', 'RW', 'Propagation')
assert sorted(tuple(m[k] for k in mount_keys) for m in new['Mounts']) == sorted(
    tuple(m[k] for k in mount_keys) for m in old['Mounts'])
env_file = dict(line.split('=', 1) for line in Path(c['private_runtime_path']).read_text().splitlines() if line)
previous_env = dict(line.split('=', 1) for line in (
    root/'private'/(v['batch_id']+'-before-input-guard.env')).read_text().splitlines() if line)
assert env_file == {**previous_env, key: str(v['prepared_bytes'])}
assert json.loads((root/'analysis/config/deployment.json').read_text()) == c
for name, sha in v['runtime_files'].items():
    if name != 'deployment.json':
        assert hashlib.sha256((root/'analysis/config'/name).read_bytes()).hexdigest() == sha
probe = json.loads(run(['docker', 'run', '--rm', '-i', '--network', 'none', '--user', c['user'],
                        '--workdir', c['workdir'], '--env-file', c['private_runtime_path'],
                        '--volumes-from', new['Id'], '--entrypoint', 'python', c['image'], '-'], v['probe']).splitlines()[-1])
assert probe['policy_sha256'] == v['policy_sha256'] and probe['status'] == 'passed'
run(['docker', 'rename', old['Id'], v['retained_container']])
run(['docker', 'rename', new['Id'], c['container']])
current = json.loads(run(['docker', 'inspect', c['container']]))[0]
assert current['Id'] == new['Id'] and current['State']['Status'] == 'created' and not current['State']['Running']
print(json.dumps({'status': 'passed', 'observed_at': datetime.now(timezone.utc).isoformat(),
                  'current_container': c['container'], 'container_id': current['Id'], 'state': 'created',
                  'image_id': current['Image'], 'previous_container_id': old['Id'],
                  'retained_container': v['retained_container'], 'previous_state': 'exited',
                  'same_resources_mounts_command_and_other_environment': True,
                  'docker_create_defaults': {'OomKillDisable': host_delta['OomKillDisable'],
                                             'AttachStdout': {'old': False, 'new': True},
                                             'AttachStderr': {'old': False, 'new': True}},
                  'changed_environment_keys': [key], 'probe': probe,
                  'runtime_files': {name: hashlib.sha256((root/'analysis/config'/name).read_bytes()).hexdigest()
                                    for name in v['runtime_files']},
                  'model_calls': 0, 'database_queries': 0, 'dispatcher_started': False}, indent=2))
