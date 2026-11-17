"""Install only the new W4 candidate package/state and build its cached-base image."""
import base64
import hashlib
import json
import os
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

v = json.load(sys.stdin)
c, build = v['candidate'], v['build']
root = Path(c['root'])
assert root.parent == Path('/opt/sting-aisoc-socai2/candidates') and not root.exists()
image = build['image']


def command(args, *, timeout=None, body=None):
    result = subprocess.run(args, input=body, capture_output=True, text=True,
                            timeout=timeout or c['command_timeout_seconds'], check=False)
    if result.returncode:
        raise RuntimeError(result.stderr[-1500:])
    return result.stdout


def protected():
    names = v['protected_containers']
    rows = json.loads(command(['docker', 'inspect', *names]))
    return [{'name': r['Name'], 'id': r['Id'], 'image': r['Image'], 'state': r['State']['Status']}
            for r in rows]


before = protected()
base = json.loads(command(['docker', 'image', 'inspect', image['base_tag']]))[0]
assert base['Id'] == image['base_id'] and base['Architecture'] == 'amd64' and base['Os'] == 'linux'
assert c['container'] not in command(['docker', 'ps', '-a', '--format', '{{.Names}}']).splitlines()
root.mkdir()
(root/'evidence').mkdir()
for name, item in v['uploads'].items():
    assert name in {'release.tar.gz', 'state.tar.gz'}
    data = base64.b64decode(item['base64'], validate=True)
    assert hashlib.sha256(data).hexdigest() == item['sha256']
    (root/name).write_bytes(data)
    with tarfile.open(root/name, 'r:gz') as archive:
        for member in archive.getmembers():
            assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            assert member.name.split('/')[0] == (build['release'] if name == 'release.tar.gz' else 'state')
            target = root/member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
package = root/build['release']
uid, gid = map(int, image['user'].split(':'))
for path in [root/'state', *(root/'state').rglob('*')]:
    os.chown(path, uid, gid)
actual = {p.relative_to(root/'state/ledger').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (root/'state/ledger').rglob('*') if p.is_file()}
assert actual == v['ledger_hashes']
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
args = ['docker', 'build', '--pull=false', '--network=none', '--platform', image['platform'],
        '-t', image['tag'], str(package)]
log = command(args, timeout=image['build_timeout_seconds'])
(root/'evidence/build.log').write_text(log)
loaded = json.loads(command(['docker', 'image', 'inspect', image['tag']]))[0]
probe = json.loads(command(['docker', 'run', '--rm', '--network', 'none', '--read-only',
    '--entrypoint', 'python', loaded['Id'], 'deploy/investigation-test/build.py', 'verify',
    '--directory', image['workdir']]).splitlines()[-1])
assert probe['service_version'] == '0.4.0' and protected() == before
result = {'status': 'passed', 'observed_at': datetime.now(timezone.utc).isoformat(),
          'release': build['release'], 'archive_sha256': v['uploads']['release.tar.gz']['sha256'],
          'state_sha256': v['uploads']['state.tar.gz']['sha256'], 'image_id': loaded['Id'],
          'image_tag': image['tag'], 'base_image_id': base['Id'], 'platform': image['platform'],
          'image_package_check': probe, 'ledger_files': len(actual), 'protected_before': before,
          'protected_after': protected(), 'configuration_hashes': {
              p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in config.iterdir()},
          'model_calls': 0, 'business_writes': 0, 'dispatcher_started': False,
          'test_service_started': False}
(root/'runtime.json').write_text(json.dumps({k: value for k, value in v.items() if k != 'uploads'}, indent=2)+'\n')
(root/'evidence/prepare.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
