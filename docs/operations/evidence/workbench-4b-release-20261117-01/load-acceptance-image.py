"""Load the unchanged-recipe image built with the existing local dependency cache."""
import hashlib
import json
import subprocess
from pathlib import Path

c = CONFIG
root = Path(c['remote_root'])
archive = root / 'incoming' / Path(INPUT['archive']).name
with archive.open('rb') as source:
    digest = hashlib.sha256()
    for block in iter(lambda: source.read(1048576), b''):
        digest.update(block)
assert digest.hexdigest() == INPUT['sha256']
r = subprocess.run(['docker', 'image', 'load', '-i', str(archive)], text=True, capture_output=True,
                   timeout=c['command_timeout_seconds'])
assert r.returncode == 0, r.stderr[-800:]
images = {}
for kind, tag in [('viewer', c['viewer_image']), ('acceptance', c['acceptance_image'])]:
    d = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag], text=True))[0]
    assert d['Architecture'] == 'amd64' and d['Os'] == 'linux'
    if kind == 'acceptance':
        assert d['Id'] == INPUT['image_id']
    images[kind] = {'tag': tag, 'id': d['Id'], 'repo_digests': d['RepoDigests'],
                    'architecture': d['Architecture'], 'user': d['Config']['User']}
package = root / 'package' / c['package_release']
manifest = json.loads((package / 'package-manifest.json').read_text())
assert hashlib.sha256((package / 'package-manifest.json').read_bytes()).hexdigest() == INPUT['package_manifest_sha256']
out = {'status': 'images_built_not_switched', 'package': str(package),
       'package_manifest_sha256': INPUT['package_manifest_sha256'], 'file_count': len(manifest['files']),
       'images': images, 'services_changed': False, 'acceptance_build_host': 'local_cached_dependencies',
       'acceptance_archive_sha256': INPUT['sha256'], 'failed_remote_acceptance_builds': 2}
(root / 'images.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(out, ensure_ascii=False))
