"""Upload this frozen full-service package; no active service switch."""
import hashlib
import io
import json
import shlex
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def main(config_dir):
    c = json.loads((config_dir / 'release.json').read_text())
    p = json.loads((config_dir / 'package-config.json').read_text())
    h = json.loads((config_dir / 'http-profile.json').read_text())
    transport = json.loads((config_dir / 'transport.json').read_text())
    evidence = ROOT / p['evidence']
    files = {}
    for source, target in [
        (config_dir, 'config'),
        (ROOT / '.local/http-release' / h['release'], 'http/releases/' + h['release']),
        (ROOT / p['test_package'], 'viewer/package'),
        (ROOT / c['swagger']['source_directory'], 'swagger/handoff'),
    ]:
        for path in sorted(source.rglob('*')):
            if path.is_file():
                assert not path.is_symlink()
                files[str(Path(target) / path.relative_to(source))] = path.read_bytes()
    for path in sorted(evidence.glob('*.py')):
        files['scripts/' + path.name] = path.read_bytes()
    files['swagger/compose.yml'] = (ROOT / 'deploy/api-docs/compose.yml').read_bytes()
    s = c['swagger']
    env = {'SWAGGER_IMAGE': s['image'], 'DOCS_PLATFORM': s['platform'], 'DOCS_BIND': s['bind'],
           'DOCS_PORT': s['port'], 'DOCS_CONTAINER_PORT': s['container_port'],
           'DOCS_CONTENT': c['root'] + '/swagger/handoff'}
    files['swagger/runtime.env'] = ('\n'.join(str(k) + '=' + str(v) for k, v in env.items()) + '\n').encode()
    manifest = {n: hashlib.sha256(b).hexdigest() for n, b in sorted(files.items())}
    files['stage-manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for name, body in sorted(files.items()):
            item = tarfile.TarInfo(name)
            item.size, item.mode = len(body), 0o644
            archive.addfile(item, io.BytesIO(body))
    body = buffer.getvalue()
    remote = r'''
import hashlib,io,json,sys,tarfile
from pathlib import Path
root=Path(sys.argv[1]); raw=sys.stdin.buffer.read()
assert hashlib.sha256(raw).hexdigest()==sys.argv[2]
assert not root.exists(), 'release_root_already_exists'
root.mkdir(parents=True); (root/'releases').mkdir()
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
 for item in archive.getmembers():
  name=Path(item.name)
  assert item.isfile() and not name.is_absolute() and '..' not in name.parts
  path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb') as output:output.write(archive.extractfile(item).read())
manifest=json.loads((root/'stage-manifest.json').read_text())
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
print(json.dumps({'root':str(root),'files':len(manifest),'archive_sha256':sys.argv[2],'services_changed':False}))
'''
    t = transport['transport']
    args = [t['ssh_binary'], '-T', '-o', 'BatchMode=yes', '-o',
            'ConnectTimeout=' + str(t['connect_timeout_seconds']), t['ssh_target'],
            shlex.join([t['remote_python'], '-c', remote, c['root'], hashlib.sha256(body).hexdigest()])]
    result = subprocess.run(args, input=body, capture_output=True, timeout=transport['command_timeout_seconds'])
    receipt = {'exit': result.returncode, 'stdout': result.stdout.decode(), 'stderr': result.stderr.decode()}
    with (evidence / 'stage-release-01.json').open('x') as output:
        json.dump(receipt, output, indent=2)
    print(json.dumps(receipt))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
