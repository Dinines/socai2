"""Upload this frozen non-secret full-service release without switching services."""
import hashlib
import io
import json
import shlex
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E = Path(__file__).resolve().parent
CFG = ROOT / 'deploy/aisoc21/streaming-release-20261116-04'
c = json.loads((CFG / 'release.json').read_text())
h = json.loads((CFG / 'http-profile.json').read_text())
files = {}
for source, target in [
    (CFG, 'config'),
    (ROOT / '.local/http-release' / h['release'], 'http/releases/' + h['release']),
    (ROOT / c['swagger']['source_directory'], 'swagger/handoff'),
]:
    for path in sorted(source.rglob('*')):
        if path.is_file():
            assert not path.is_symlink()
            files[str(Path(target) / path.relative_to(source))] = path.read_bytes()
for name in ['prepare-viewer.py', 'cleanup-inventory.py']:
    files['scripts/' + name] = (E / name).read_bytes()
manifest = {name: hashlib.sha256(body).hexdigest() for name, body in sorted(files.items())}
files['stage-manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
buffer = io.BytesIO()
with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
    for name, body in sorted(files.items()):
        item = tarfile.TarInfo(name)
        item.size, item.mode = len(body), 0o644
        archive.addfile(item, io.BytesIO(body))
body = buffer.getvalue()
remote = '''
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
args = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', c['ssh_target'],
        shlex.join(['python3', '-c', remote, c['root'], hashlib.sha256(body).hexdigest()])]
result = subprocess.run(args, input=body, capture_output=True, timeout=120)
receipt = {'exit': result.returncode, 'stdout': result.stdout.decode(), 'stderr': result.stderr.decode()}
with (E / 'stage-release-01.json').open('x') as output:
    json.dump(receipt, output, indent=2)
print(json.dumps(receipt))
raise SystemExit(result.returncode)
