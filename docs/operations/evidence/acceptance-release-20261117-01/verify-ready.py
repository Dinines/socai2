"""Read back the five live services, their frozen sources, and the cleaned empty state."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

c = json.load(sys.stdin)
root = Path(c['root'])
h = json.loads((root / 'config/http-profile.json').read_text())
images = json.loads((root / 'config/images.json').read_text())
cleanup = json.loads((root / 'cleanup-zero.json').read_text())


def run(args, body=None):
    result = subprocess.run(args, input=body, capture_output=True, timeout=55)
    assert not result.returncode, 'verification_command_failed:' + args[0]
    return result.stdout


def inspect(name):
    return json.loads(run(['docker', 'inspect', name]))[0]


def get(url):
    with urlopen(url, timeout=10) as response:
        assert response.status == 200
        return json.load(response)


checks = {}
for kind, name in [('processing', c['analysis']['name']), ('fusion', c['fusion']['name']),
                   ('http', h['container']), ('swagger', c['swagger']['container']), ('viewer', c['viewer']['name'])]:
    value = inspect(name)
    assert value['State']['Running'] and value['RestartCount'] == 0
    assert value['Image'] == images['processing' if kind == 'fusion' else kind]
    checks[kind] = {'name': name, 'id': value['Id'], 'image': value['Image'],
                    'running': True, 'restart_count': 0, 'started_at': value['State']['StartedAt']}
for name in c['must_remain_stopped']:
    assert not inspect(name)['State']['Running'], 'old_service_active:' + name

verification = 'import hashlib,json,sys;from pathlib import Path;expected=json.load(sys.stdin);actual={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in expected};assert actual==expected,"runtime_source_mismatch";print(json.dumps({"verified_files":len(actual),"digest":hashlib.sha256(json.dumps(actual,sort_keys=True).encode()).hexdigest()}))'
transport = json.loads((root / 'config/transport.json').read_text())
manifest = json.loads((root / 'releases' / transport['processing_release'] / 'manifest.json').read_text())
expected = {('/app/' + name if name.startswith('app/') else '/opt/processor/' + name): record['sha256']
            for name, record in manifest['files'].items() if name not in {'Dockerfile', 'build_processing_image.py'}}
expected['/run/analysis/investigation-policy.toml'] = manifest['policy_sha256']
sources = {'processing': json.loads(run(['docker', 'exec', '-i', c['analysis']['name'], 'python', '-c', verification], json.dumps(expected).encode()))}
expected = {'/app/' + target: h['expected_source_hashes'][source] for source, target in h['patches'].items()}
sources['http'] = json.loads(run(['docker', 'exec', '-i', h['container'], 'python', '-c', verification], json.dumps(expected).encode()))
key_profiles = {name: record['sha256'] for name, record in manifest['files'].items()
                if name in {'app/socai2/alert-input-v1.json', 'app/socai2/incident-input-v1.json',
                            'app/socai2/case-input-v1.json', 'app/socai2/baseline_context.schema.json'}}

base = c['viewer']['upstream']
ready = get(base + '/readyz')
raw = get(base + '/openapi.json')
assert raw['info']['version'] == h['release']
empty = {}
for subject in ['alerts', 'incidents', 'cases']:
    value = get(base + '/api/v1/socai2/' + subject)
    assert value['items'] == [], 'business_store_not_empty:' + subject
    empty[subject] = value
viewer = 'http://' + c['viewer']['bind'] + ':' + str(c['viewer']['port'])
capabilities = get(viewer + '/test-api/v1/capabilities')
assert capabilities['environment_label'] == c['release']
batches = get(viewer + '/test-api/v1/batches')
assert batches['items'] == [], 'old_ledger_still_visible'

d = c['database']
sql = """BEGIN READ ONLY;
SELECT json_build_object('tables',(SELECT count(*) FROM information_schema.tables WHERE table_schema='socai2' AND table_type='BASE TABLE'),
 'columns',(SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2'),
 'tasks',(SELECT count(*) FROM socai2.analysis_tasks), 'attempts',(SELECT count(*) FROM socai2.analysis_attempts),
 'runs',(SELECT count(*) FROM socai2.runs), 'results',(SELECT count(*) FROM socai2.results));COMMIT;"""
database = json.loads(run(['docker', 'exec', '-i', d['container'], 'psql', '-wXAtq', '-v', 'ON_ERROR_STOP=1', '-U', d['admin'], '-d', d['name']], sql.encode()))
assert database == {'tables': 32, 'columns': 521, 'tasks': 0, 'attempts': 0, 'runs': 0, 'results': 0}
result = {'status': 'ready_for_new_full_flow', 'release': c['release'], 'database': d['name'],
          'database_state': database, 'images': images, 'services': checks, 'runtime_sources': sources,
          'runtime_input_profiles': key_profiles, 'policy_sha256': manifest['policy_sha256'],
          'old_execution_services_stopped': True, 'http_readiness': ready, 'http_empty_reads': empty,
          'http_version': raw['info']['version'], 'operations': h['expected_operations'],
          'viewer_capabilities': capabilities, 'viewer_empty_batches': batches,
          'cleanup_zero': {'backup_root': cleanup['backup_root'], 'preserved_tables_unchanged': cleanup['preserved_tables_unchanged']},
          'prior_runtime_root': c['prior_runtime_root'], 'model_calls': 0, 'business_posts': 0}
with (root / 'deployment-ready.json').open('x') as output:
    json.dump(result, output, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
