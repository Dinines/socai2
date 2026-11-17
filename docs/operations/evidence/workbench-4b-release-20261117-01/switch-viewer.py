"""Replace only 4177 after immutable image and offline-report verification."""
import hashlib
import json
import subprocess
import time
import urllib.request
from pathlib import Path

c = CONFIG
root = Path(c['remote_root'])
baseline = INPUT
verified = json.loads((root / 'images-and-report-verified.json').read_text())
assert verified['status'] == 'passed_images_and_offline_report'
images = json.loads((root / 'images.json').read_text())
package = Path(images['package'])

def run(args):
    r = subprocess.run(args, text=True, capture_output=True, timeout=c['command_timeout_seconds'])
    if r.returncode:
        raise RuntimeError(args[0] + ':' + str(r.returncode) + ':' + r.stderr[-800:])
    return r.stdout

def inspect(name):
    d = json.loads(run(['docker', 'inspect', name]))[0]
    return {'id': d['Id'], 'image': d['Image'], 'running': d['State']['Running'],
            'started_at': d['State']['StartedAt'], 'restart_count': d['RestartCount'],
            'mounts': d['Mounts'], 'ports': d['NetworkSettings']['Ports']}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def core_unchanged():
    core = {name: inspect(name) for name in c['core_containers']}
    for name, d in core.items():
        assert d['running']
        for key in ['id', 'image', 'started_at', 'restart_count']:
            assert d[key] == baseline['core'][name][key], (name, key)
    return core

assert inspect(c['old_container'])['id'] == c['old_id']
assert inspect(c['old_container'])['running']
assert c['container'] not in run(['docker', 'ps', '-a', '--format', '{{.Names}}']).splitlines()
core_unchanged()
config = root / 'viewer-config'
config.mkdir()
old_config = Path(c['old_config'])
old_hashes = {}
for name in ['service.json', 'upstream.json', 'viewer.json', 'investigation-openapi.json']:
    old_hashes[name] = sha(old_config / name)
    (config / name).write_bytes((old_config / name).read_bytes())
viewer = json.loads((config / 'viewer.json').read_text())
viewer['test_source_prefixes'] = c['test_source_prefixes']
(config / 'viewer.json').write_text(json.dumps(viewer, ensure_ascii=False, indent=2) + '\n')
service = json.loads((config / 'service.json').read_text())
upstream = json.loads((config / 'upstream.json').read_text())
assert service['host'] == c['container_host'] and service['port'] == c['container_port']
assert service['environment_label'] == upstream['environment_label'] == c['environment_label']
assert upstream['base_url'] == c['upstream_base_url']
assert sha(config / 'investigation-openapi.json') == upstream['openapi_sha256']
contract = json.loads((config / 'investigation-openapi.json').read_text())
operations = sum(method in {'get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace'}
                 for path in contract['paths'].values() for method in path)
assert operations == 80
assert json.loads(run(['docker', 'image', 'inspect', c['viewer_image']]))[0]['Id'] == images['images']['viewer']['id']
run(['docker', 'stop', '-t', str(c['stop_timeout_seconds']), c['old_container']])
args = ['docker', 'run', '-d', '--name', c['container'], '--restart', c['restart'],
        '--network', c['network'], '--user', c['user'], '--read-only', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges:true', '--memory', c['memory'], '--pids-limit',
        str(c['pids_limit']), '--tmpfs', c['tmpfs'], '-p',
        f"{c['bind_host']}:{c['bind_port']}:{c['container_port']}",
        '--mount', f"type=bind,src={config},dst={c['config_mount']},readonly",
        '--mount', f"type=bind,src={c['state_root']},dst={c['ledger_mount']},readonly",
        '--entrypoint', 'python', c['viewer_image'], '-m', 'investigation_test', 'serve',
        '--config', c['config_mount'] + '/service.json',
        '--upstream-config', c['config_mount'] + '/upstream.json',
        '--viewer-config', c['config_mount'] + '/viewer.json']
try:
    container_id = run(args).strip()
    deadline = time.monotonic() + c['startup_timeout_seconds']
    while True:
        try:
            with urllib.request.urlopen(c['local_entry'] + '/test-api/v1/capabilities', timeout=c['http_timeout_seconds']) as response:
                capabilities = json.load(response)
            assert capabilities['service_version'] == capabilities['viewer_version'] == c['version']
            break
        except Exception:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.5)
    assert capabilities['environment_label'] == c['environment_label']
    assert capabilities['investigation_http']['contract_sha256'] == upstream['openapi_sha256']
    responses = {}
    for name, path in [('viewer-config.json', '/viewer/config.json'), ('index.html', '/viewer/'),
                       ('viewer.js', '/viewer/assets/viewer.js'), ('viewer_links.mjs', '/viewer/assets/viewer_links.mjs'),
                       ('test_sources.mjs', '/viewer/assets/test_sources.mjs'),
                       ('case.json', '/api/v1/socai2/cases/' + c['case_id'])]:
        with urllib.request.urlopen(c['local_entry'] + path, timeout=c['http_timeout_seconds']) as response:
            body = response.read()
            responses[name] = {'status': response.status, 'sha256': hashlib.sha256(body).hexdigest()}
        if name in ['index.html', 'viewer.js', 'viewer_links.mjs', 'test_sources.mjs']:
            assert body == (package / 'services/investigation_test/web' / name).read_bytes(), name
        if name == 'viewer-config.json':
            assert json.loads(body)['test_source_prefixes'] == c['test_source_prefixes']
        if name == 'case.json':
            assert json.loads(body) == baseline['http']['case']['data']
    current = inspect(c['container'])
    assert current['id'] == container_id and current['running']
    assert current['image'] == images['images']['viewer']['id']
    assert all(not item['RW'] for item in current['mounts'])
    ledger = {str(p.relative_to(c['state_root'])): sha(p) for p in Path(c['state_root']).rglob('*') if p.is_file()}
    assert ledger == baseline['ledger_sha256']
    assert old_hashes == {name: sha(old_config / name) for name in old_hashes}
    out = {'status': 'passed_4177_r8_readback', 'container': current, 'old_stopped': not inspect(c['old_container'])['running'],
           'core': core_unchanged(), 'ledger_sha256': ledger, 'capabilities': capabilities,
           'configuration': {'service': service, 'upstream': upstream, 'viewer': viewer},
           'config_sha256': {p.name: sha(p) for p in config.iterdir()}, 'old_config_sha256': old_hashes,
           'operations': operations, 'http': responses, 'business_writes': 0, 'model_calls': 0}
    (root / 'deployment-ready.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(out, ensure_ascii=False))
except Exception as exc:
    subprocess.run(['docker', 'stop', '-t', str(c['stop_timeout_seconds']), c['container']], capture_output=True)
    restored = run(['docker', 'start', c['old_container']]).strip()
    failure = {'status': 'new_viewer_failed_old_restored', 'error': str(exc), 'restored': restored}
    (root / 'deployment-failed.json').write_text(json.dumps(failure, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(failure, ensure_ascii=False))
    raise
