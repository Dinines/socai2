"""Retry the unchanged pinned acceptance build after a package-download timeout."""
import hashlib
import json
import subprocess
from pathlib import Path

c = CONFIG
root = Path(c['remote_root'])
package = root / 'package' / c['package_release']
manifest = json.loads((package / 'package-manifest.json').read_text())
assert hashlib.sha256((package / 'package-manifest.json').read_bytes()).hexdigest() == INPUT['manifest_sha256']
for name, record in manifest['files'].items():
    assert hashlib.sha256((package / name).read_bytes()).hexdigest() == record['sha256'], name
profile = json.loads((package / 'build-profile.json').read_text())
accept = json.loads((package / profile['acceptance_image']).read_text())
with (root / 'acceptance-build-retry-01.log').open('x') as log:
    result = subprocess.run(
        ['docker', 'build', '--pull=false', '--network=' + accept['build_network'],
         '--platform', c['platform'], '-f', 'Dockerfile.acceptance', '-t', c['acceptance_image'], '.'],
        cwd=package, text=True, stdout=log, stderr=subprocess.STDOUT,
        timeout=c['command_timeout_seconds'],
    )
assert result.returncode == 0, 'acceptance_image_retry_failed'
images = {}
for kind, tag in [('viewer', c['viewer_image']), ('acceptance', c['acceptance_image'])]:
    d = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag], text=True))[0]
    assert d['Architecture'] == 'amd64' and d['Os'] == 'linux'
    images[kind] = {'tag': tag, 'id': d['Id'], 'repo_digests': d['RepoDigests'],
                    'architecture': d['Architecture'], 'user': d['Config']['User']}
out = {'status': 'images_built_not_switched', 'package': str(package),
       'package_manifest_sha256': INPUT['manifest_sha256'], 'file_count': len(manifest['files']),
       'images': images, 'services_changed': False, 'acceptance_build_attempts': 2}
(root / 'images.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(out, ensure_ascii=False))
