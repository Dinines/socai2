"""Complete the candidate env; retain the stopped predecessor and create its replacement."""
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
private = root/'private'
key = 'AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS'


def run(args, body=None):
    result = subprocess.run(args, input=body, capture_output=True, text=True,
                            timeout=c['command_timeout_seconds'], check=False)
    if result.returncode:
        with (private/(v['batch_id']+'-input-guard-error.txt')).open('x') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(result.stderr)
        raise RuntimeError('command_failed_private_detail_retained')
    return result.stdout


old = json.loads(run(['docker', 'inspect', c['container']]))[0]
assert old['Id'] == v['previous_container_id'] and old['Image'] == c['image']
assert old['State']['Status'] == 'exited' and old['State']['ExitCode'] == 0
names = run(['docker', 'ps', '-a', '--format', '{{.Names}}']).splitlines()
assert v['staged_container'] not in names and v['retained_container'] not in names
assert not any('analysis_dispatch_runtime' in row.get('Command', '') for row in
               (json.loads(line) for line in run(['docker', 'ps', '--no-trunc', '--format', '{{json .}}']).splitlines()))
for name, sha in v['runtime_files'].items():
    assert hashlib.sha256((root/'analysis/config'/name).read_bytes()).hexdigest() == sha
base = json.loads((root/'analysis/docker-base.json').read_text())
assert base[:2] == ['docker', 'run']
assert base[base.index('--env-file')+1] == c['private_runtime_path']
deployment = root/'analysis/config/deployment.json'
previous = json.loads(deployment.read_text())
expected = json.loads(json.dumps(c))
assert expected['runtime_env'].pop(key) == str(v['prepared_bytes'])
assert previous == expected
env_path = Path(c['private_runtime_path'])
env_raw = env_path.read_bytes()
env = dict(line.split('=', 1) for line in env_raw.decode().splitlines() if line and not line.startswith('#'))
old_env = dict(line.split('=', 1) for line in old['Config']['Env'])
assert key not in env and key not in old_env
backup = private/(v['batch_id']+'-before-input-guard.env')
with backup.open('xb') as stream:
    os.fchmod(stream.fileno(), 0o600)
    stream.write(env_raw)
archive = root/'analysis/evidence'/v['batch_id']/'deployment.before-input-guard.json'
with archive.open('xb') as stream:
    stream.write(deployment.read_bytes())
env[key] = str(v['prepared_bytes'])
temporary = private/(v['batch_id']+'-input-guard.env')
with temporary.open('x') as stream:
    os.fchmod(stream.fileno(), 0o600)
    stream.write(''.join(k+'='+value+'\n' for k, value in sorted(env.items())))
os.replace(temporary, env_path)
deployment.write_text(json.dumps(c, indent=2)+'\n')
created = run(['docker', 'create', *base[2:], '--name', v['staged_container'], '--restart', 'no',
               '--entrypoint', 'python', c['image'], *old['Config']['Cmd']]).strip()
new = json.loads(run(['docker', 'inspect', created]))[0]
new_env = dict(line.split('=', 1) for line in new['Config']['Env'])
assert new_env == {**old_env, key: str(v['prepared_bytes'])}
assert new['HostConfig'] == old['HostConfig']
ignored = {'Hostname', 'Env'}
assert {k: value for k, value in new['Config'].items() if k not in ignored} == {
    k: value for k, value in old['Config'].items() if k not in ignored}
mount_keys = ('Type', 'Source', 'Destination', 'RW', 'Propagation')
mounts = lambda row: sorted(tuple(m[k] for k in mount_keys) for m in row['Mounts'])
assert mounts(new) == mounts(old)
probe = json.loads(run(['docker', 'run', '--rm', '-i', '--network', 'none', '--user', c['user'],
                        '--workdir', c['workdir'], '--env-file', c['private_runtime_path'],
                        '--volumes-from', created, '--entrypoint', 'python', c['image'], '-'], v['probe']).splitlines()[-1])
assert probe['policy_sha256'] == v['policy_sha256'] and probe['status'] == 'passed'
run(['docker', 'rename', old['Id'], v['retained_container']])
run(['docker', 'rename', created, c['container']])
current = json.loads(run(['docker', 'inspect', c['container']]))[0]
assert current['Id'] == created and current['State']['Status'] == 'created' and not current['State']['Running']
print(json.dumps({'status': 'passed', 'observed_at': datetime.now(timezone.utc).isoformat(),
                  'current_container': c['container'], 'container_id': created, 'state': 'created',
                  'image_id': current['Image'], 'previous_container_id': old['Id'],
                  'retained_container': v['retained_container'], 'previous_state': 'exited',
                  'same_host_config_mounts_command_and_other_environment': True,
                  'changed_environment_keys': [key], 'probe': probe,
                  'runtime_files': {name: hashlib.sha256((root/'analysis/config'/name).read_bytes()).hexdigest()
                                    for name in v['runtime_files']},
                  'model_calls': 0, 'database_queries': 0, 'dispatcher_started': False}, indent=2))
