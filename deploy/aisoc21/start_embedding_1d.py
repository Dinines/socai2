"""Verify the copied model and exact local image, then start only embedding on 21."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT = Path('/opt/sting-aisoc-socai2')
IMAGE = 'sha256:265409e1d931028a8f7d5a32bcbafddd7bffbc6cc629d77efe9560adf692a5e7'


def main(reference_file):
    evidence = ROOT/'evidence/1d-20261020'
    reference = json.loads((evidence/reference_file).read_text())
    files = {}
    links = {}
    models = ROOT/'runtime-data/ollama-embedding/models'
    for p in sorted(models.rglob('*')):
        if p.is_symlink():
            assert p.resolve().is_relative_to(models.resolve())
            links['./'+p.relative_to(models).as_posix()] = str(p.readlink())
        if p.is_file():
            h = hashlib.sha256()
            with p.open('rb') as f:
                for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
            files['./'+p.relative_to(models).as_posix()] = h.hexdigest()
    assert links == reference.get('model_symlinks', {}), 'Model symlinks differ'
    assert files == reference['model_files'], 'Model files differ; no startup'
    image = json.loads(subprocess.check_output(['docker', 'image', 'inspect', IMAGE]))[0]
    assert image['Id'] == reference['image_id'] == IMAGE
    assert image['Architecture'] == 'amd64'
    compose = ROOT/'source/deploy/aisoc21/compose.embedding.yml'
    subprocess.run(['docker', 'compose', '--project-directory', str(ROOT), '-f', str(compose),
                    'up', '-d', '--no-deps', '--pull', 'never', 'ollama-embedding'], check=True)
    for _ in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:11435/api/version', timeout=3) as r:
                version = json.load(r)['version']
            break
        except OSError: time.sleep(1)
    else: raise RuntimeError('Embedding did not start')
    assert version == '0.40.6'
    with urllib.request.urlopen('http://127.0.0.1:11435/api/tags', timeout=5) as r:
        tags = json.load(r)
    x = json.loads(subprocess.check_output(['docker', 'inspect', 'socai2-ollama-embedding-1']))[0]
    assert not x['HostConfig']['DeviceRequests'] and not x['HostConfig']['Devices']
    assert x['HostConfig']['NanoCpus'] == 16*10**9
    assert x['HostConfig']['Memory'] == 32*1024**3
    assert x['HostConfig']['MemorySwap'] == 64*1024**3
    assert x['NetworkSettings']['Ports']['11434/tcp'] == [{'HostIp':'127.0.0.1','HostPort':'11435'}]
    data = {'image_id': IMAGE, 'source_image': reference['image_name'], 'api_version': version,
            'model_files': files, 'model_symlinks': links, 'all_model_files_equal_to_reference': True, 'tags': tags,
            'container_id': x['Id'], 'network_names': sorted(x['NetworkSettings']['Networks']),
            'ports': x['NetworkSettings']['Ports'], 'mounts': x['Mounts'],
            'device_requests': x['HostConfig']['DeviceRequests'], 'cpu_limit': 16,
            'memory_bytes': x['HostConfig']['Memory'],
            'cost': None, 'cost_source': 'unknown'}
    with (evidence/'embedding-runtime.json').open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    print(json.dumps(data))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', default='reference-model.json')
    args = parser.parse_args()
    assert Path(args.reference).name == args.reference
    main(args.reference)
