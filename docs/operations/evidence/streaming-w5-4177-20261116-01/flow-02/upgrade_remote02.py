"""Upgrade only the W5 read viewer; preserve previous container and all records."""
import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

v = json.load(sys.stdin)
c, build, baseline = v['profile'], v['build'], v['baseline']
image = build['image']
root = Path(c['deployment_root'])
package = Path(c['release_parent'])/build['release']
state = Path(c['state_root'])


def command(args, *, timeout=None):
    result = subprocess.run(args, capture_output=True, text=True,
                            timeout=timeout or c['command_timeout_seconds'], check=False)
    if result.returncode:
        raise RuntimeError(result.stderr[-1500:])
    return result.stdout, result.stderr


def read_command(args):
    return json.loads(command(args)[0])


def hashes(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}


def protected():
    names = [r['name'].lstrip('/') for r in baseline['containers']]
    return [{'name': r['Name'], 'id': r['Id'], 'image': r['Image'], 'state': r['State']['Status'],
             'restart': r['HostConfig']['RestartPolicy'], 'ports': r['HostConfig']['PortBindings']}
            for r in read_command(['docker', 'inspect', *names])]


assert protected() == baseline['containers']
assert hashes(Path(c['old_site'])) == baseline['old_site_files']
assert hashes(Path(c['state_source'])/'ledger') == baseline['w4_ledger_files']
assert not c['initial_state_import']
assert not any(p.exists() for p in [root, package])
assert hashes(state/'ledger') == v['current_ledger_hashes']
previous = read_command(['docker', 'inspect', c['previous_container']])[0]
assert previous['Id'] == v['previous']['container_id'] and previous['Image'] == v['previous']['image_id'] and previous['State']['Running']
assert c['container'] not in command(['docker', 'ps', '-a', '--format', '{{.Names}}'])[0].splitlines()
base = read_command(['docker', 'image', 'inspect', image['base_tag']])[0]
assert base['Id'] == image['base_id'] and base['Architecture'] == 'amd64' and base['Os'] == 'linux'
data = base64.b64decode(v['upload'], validate=True)
assert hashlib.sha256(data).hexdigest() == v['archive_sha256']
root.mkdir(parents=True)
out = root/'evidence'
out.mkdir()
(root/'release.tar.gz').write_bytes(data)
with tarfile.open(root/'release.tar.gz', 'r:gz') as archive:
    members = archive.getmembers()
    for member in members:
        name = Path(member.name)
        assert member.isfile() and not name.is_absolute() and '..' not in name.parts
        assert name.parts[0] == build['release']
    for member in members:
        target = Path(c['release_parent'])/member.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.extractfile(member).read())
config = root/'config'
config.mkdir()
service = json.loads((package/'config/service.example.json').read_text())
service.update(host=c['container_host'], port=c['container_port'], ledger_root=c['ledger_mount']+'/ledger',
               environment_label=c['environment_label'])
upstream = json.loads((package/'config/upstream.example.json').read_text())
upstream.update(base_url=c['upstream_base_url'], openapi_file=image['workdir']+'/investigation-openapi.json')
for name, value in [('service.json', service), ('upstream.json', upstream),
                    ('viewer.json', json.loads((package/'config/viewer.example.json').read_text()))]:
    (config/name).write_text(json.dumps(value, indent=2)+'\n')
log = command(['docker', 'build', '--pull=false', '--network=none', '--platform', image['platform'],
               '-t', image['tag'], str(package)], timeout=image['build_timeout_seconds'])
(out/'build.log').write_text(''.join(log))
loaded = read_command(['docker', 'image', 'inspect', image['tag']])[0]
probe = json.loads(command(['docker', 'run', '--rm', '--network', 'none', '--read-only',
    '--entrypoint', 'python', loaded['Id'], 'deploy/investigation-test/build.py', 'verify',
    '--directory', image['workdir']])[0].splitlines()[-1])
assert probe['service_version'] == v['service_version']
created = command(['docker', 'create', '--name', c['container'], '--restart', c['restart_policy'],
    '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--network', c['network'],
    '--memory', c['memory'], '--pids-limit', str(c['pids_limit']), '--tmpfs', c['tmpfs'],
    '--publish', f"{c['bind_host']}:{c['bind_port']}:{c['container_port']}",
    '--mount', f"type=bind,src={config},dst={c['config_mount']},readonly",
    '--mount', f"type=bind,src={state},dst={c['ledger_mount']},readonly", loaded['Id']])[0].strip()
(root/'runtime.json').write_text(json.dumps({k: val for k, val in v.items() if k not in ('upload', 'observation_files')}, indent=2)+'\n')
command(['docker', 'stop', '--time', str(c['stop_timeout_seconds']), c['previous_container']])
try:
    command(['docker', 'start', c['container']])
    deadline = time.monotonic()+c['startup_timeout_seconds']
    while time.monotonic() < deadline:
        row = read_command(['docker', 'inspect', c['container']])[0]
        assert row['Id'] == created and row['State']['Running']
        if 'Application startup complete.' in ''.join(command(['docker', 'logs', c['container']])):
            break
        time.sleep(0.2)
    else:
        raise RuntimeError('viewer_start_timeout')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://{c['bind_host']}:{c['bind_port']}/test-api/v1/capabilities",
                     timeout=c['http_timeout_seconds']) as response:
        raw = response.read()
        assert response.status == 200
        (out/'startup-capabilities.json').write_bytes(raw)
        caps = json.loads(raw)
    assert caps['service_version'] == caps['viewer_version'] == v['service_version'] and caps['read_only']
    assert caps['environment_label'] == c['environment_label']
except Exception:
    command(['docker', 'stop', '--time', str(c['stop_timeout_seconds']), c['container']])
    command(['docker', 'start', c['previous_container']])
    raise
assert protected() == baseline['containers']
assert hashes(Path(c['old_site'])) == baseline['old_site_files']
all_files = hashes(state/'ledger')
assert all(all_files.get(k)==value for k,value in baseline['w4_ledger_files'].items())
assert all_files == v['current_ledger_hashes']
assert read_command(['docker', 'inspect', c['previous_container']])[0]['State']['Status']=='exited'
assert row['Image'] == loaded['Id'] and row['HostConfig']['ReadonlyRootfs']
assert all(not m['RW'] for m in row['Mounts'] if m['Type'] == 'bind')
result = {'status': 'passed', 'observed_at': datetime.now(timezone.utc).isoformat(),
    'release': build['release'], 'archive_sha256': v['archive_sha256'],
    'image_id': loaded['Id'], 'base_image_id': base['Id'], 'image_package_check': probe,
    'container_id': created, 'container': c['container'], 'state': row['State']['Status'],
    'restart_policy': row['HostConfig']['RestartPolicy'], 'port_bindings': row['HostConfig']['PortBindings'],
    'mounts': row['Mounts'], 'command': row['Config']['Entrypoint']+row['Config']['Cmd'],
    'configuration_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in config.iterdir()},
    'ledger_files_preserved': len(v['current_ledger_hashes']), 'new_observation_files': 0, 'ledger_hashes': all_files, 'previous_viewer': {'name':c['previous_container'], 'id':previous['Id'], 'state':'exited'}, 'old_site_files_preserved': len(baseline['old_site_files']),
    'protected_services_unchanged': True, 'service_version': caps['service_version'],
    'startup_http_gets': 1, 'new_model_calls': 0, 'business_writes': 0, 'kafka_messages': 0,
    'whole_change_accepted': False}
(out/'deployment.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
