"""Host21 batch 1D: snapshot, narrowly raise Qdrant nofile, verify restored points.

Requires vector_probe before receipt. Keeps original image, volume, API key,
listeners, and all other service sections. Never tears down the Compose stack.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT = Path('/opt/sting-aisoc-socai2')
EVIDENCE = ROOT / 'evidence/1d-20261020'
PRIVATE = ROOT / 'private/vector-1d'
CONTAINER = 'sting-infra21-qdrant-1'


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError('Command failed: ' + args[0])
    return result.stdout


def inspect(name):
    return json.loads(run(['docker', 'inspect', name]))[0]


def key():
    return dict(v.split('=', 1) for v in inspect(CONTAINER)['Config']['Env'])['QDRANT__SERVICE__API_KEY']


def collections():
    request = urllib.request.Request('http://192.168.1.21:6333/collections', headers={'api-key': key()})
    return json.load(urllib.request.urlopen(request, timeout=10))['result']


def inventory():
    ids = run(['docker', 'ps', '-aq']).split()
    data = json.loads(run(['docker', 'inspect', *ids]))
    return {x['Name'].lstrip('/'): {'id': x['Id'], 'image': x['Image'],
             'started_at': x['State']['StartedAt'], 'status': x['State']['Status'],
             'restart_count': x['RestartCount'], 'mounts': x['Mounts']} for x in data}


def details():
    x = inspect(CONTAINER)
    line = next(v for v in Path(f"/proc/{x['State']['Pid']}/limits").read_text().splitlines()
                if v.startswith('Max open files'))
    return {'id': x['Id'], 'image': x['Image'], 'mounts': x['Mounts'],
            'ports': x['NetworkSettings']['Ports'], 'ulimits': x['HostConfig']['Ulimits'],
            'process_nofile_line': line, 'collections': collections()}


def write(name, data):
    with (EVIDENCE/name).open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def main(action):
    if action == 'snapshot':
        EVIDENCE.mkdir(parents=True, mode=0o700)
        PRIVATE.mkdir(mode=0o700)
        write('environment-before.json', {'containers': inventory(), 'qdrant': details(),
                                         'volumes': run(['docker', 'volume', 'ls', '-q']).split()})
        return
    if action == 'prepare-client':
        manifest = ROOT/'runtime-data/ollama-embedding/models/manifests/registry.ollama.ai/library/qwen3-embedding/0.6b'
        fingerprint = hashlib.sha256(manifest.read_bytes()).hexdigest()
        env = ROOT/'private/vector-1d.env'
        with env.open('x') as f:
            f.write('QDRANT_URL=http://192.168.1.21:6333\nQDRANT_API_KEY=' + key() + '\n'
                    'EMBEDDING_MANIFEST_SHA256=' + fingerprint + '\n'
                    'EMBEDDING_SERVICE_NAME=dependency-probe-1d\nEMBEDDING_RECORD_DIR=/evidence/calls\n')
        env.chmod(0o600)
        probe = EVIDENCE/'probe'
        probe.mkdir(mode=0o750)
        (probe/'calls').mkdir(mode=0o750)
        for p in (probe, probe/'calls'):
            run(['chown', '10001:10001', str(p)])
        return
    if action == 'restart':
        assert (EVIDENCE/'probe/before.json').exists(), 'Require actual point write/read first'
        before = details()
        assert before['process_nofile_line'].split()[3] == '1024', 'Review changed current limit'
        compose = Path('/opt/sting-aisoc-infra/compose.yml')
        old = compose.read_text()
        backup = PRIVATE/'compose-before.yml'
        with backup.open('x') as f: f.write(old)
        backup.chmod(0o600)
        start, end = old.index('  qdrant:\n'), old.index('\n  neo4j:')
        section = old[start:end]
        assert 'ulimits:' not in section
        new = old[:start] + section + '\n    ulimits:\n      nofile:\n        soft: 65536\n        hard: 65536\n' + old[end:]
        compose.write_text(new)
        command = ['docker', 'compose', '--project-directory', str(compose.parent), '-f', str(compose)]
        try: run(command + ['config', '--quiet'])
        except Exception:
            compose.write_text(old)
            raise
        write('restart-before.json', before)
        run(command + ['up', '-d', '--no-deps', '--pull', 'never', 'qdrant'])
        for _ in range(30):
            try:
                after = details()
                break
            except (OSError, ValueError): time.sleep(1)
        else: raise RuntimeError('Qdrant did not recover; private backup retained')
        for name in ('image', 'mounts', 'ports', 'collections'):
            assert before[name] == after[name], name
        assert after['process_nofile_line'].split()[3:5] == ['65536', '65536']
        write('restart-after.json', after)
        return
    assert action == 'verify'
    before = json.loads((EVIDENCE/'environment-before.json').read_text())
    after = {'containers': inventory(), 'qdrant': details(),
             'volumes': run(['docker', 'volume', 'ls', '-q']).split()}
    write('environment-after.json', after)
    existing = before['containers']
    for name, old in existing.items():
        if name != CONTAINER:
            assert after['containers'][name] == old, 'Other service changed: ' + name
    assert before['volumes'] == after['volumes']
    assert before['qdrant']['collections'] == after['qdrant']['collections']
    write('environment-summary.json', {'other_existing_containers_unchanged': len(existing)-1,
          'new_containers': sorted(set(after['containers']) - set(existing)),
          'same_existing_volume_names': True, 'existing_volumes': len(after['volumes']),
          'same_original_qdrant_image_mounts_ports': True,
          'collections_before_and_after': after['qdrant']['collections'],
          'process_nofile_line': after['qdrant']['process_nofile_line']})
    print(json.dumps(json.loads((EVIDENCE/'environment-summary.json').read_text())))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('snapshot', 'prepare-client', 'restart', 'verify'))
    args = p.parse_args()
    try: main(args.action)
    except Exception as exc:
        print(json.dumps({'success': False, 'action': args.action, 'error_type': type(exc).__name__}))
        raise SystemExit(1)
