"""Read this release's six saved runs and exact model/C1 originals through 4177."""
import hashlib
import json
import urllib.request
from pathlib import Path

here = Path(__file__).resolve().parent
repo = here.parents[3]
config = json.loads((repo / 'deploy/investigation-test/releases/workbench-4b-20261117-01/release.json').read_text())
original = here.parent / 'acceptance-fullflow-21-20261117-01/results/prepared'
snapshot = json.loads((original / 'runs/part2/saved-records.json').read_text())
report = json.loads((here / 'report-02/report.json').read_text())
saved = here / 'http-02'
saved.mkdir()
reads = []

def get(path):
    assert path.startswith('/api/v1/socai2/') or path in ['/test-api/v1/capabilities', '/viewer/config.json']
    with urllib.request.urlopen(config['local_entry'] + path, timeout=config['http_timeout_seconds']) as response:
        body = response.read()
        assert response.status == 200
    name = hashlib.sha256(path.encode()).hexdigest() + '.json'
    (saved / name).write_bytes(body)
    reads.append({'path': path, 'status': 200, 'file': 'http-02/' + name, 'sha256': hashlib.sha256(body).hexdigest()})
    return json.loads(body)

caps = get('/test-api/v1/capabilities')
assert caps['service_version'] == caps['viewer_version'] == config['version']
assert get('/viewer/config.json')['test_source_prefixes'] == config['test_source_prefixes']
old_runs = {r['id']: r for r in snapshot['runs']}
runs = []
for subject in report['subjects']:
    kind = subject['kind']
    for item in subject['rounds']:
        path = '/api/v1/socai2/' + {'case': 'cases', 'alert': 'alerts', 'incident': 'incidents'}[kind] + '/' + subject['id']
        path += ('/runs/' if kind == 'case' else '/analysis/runs/') + item['run_id']
        d = get(path)
        actual = d['run'] if kind == 'case' else get(path + '/trace')['run']
        assert actual['id'] == item['run_id'] and actual[kind + '_id'] == subject['id']
        for key in ['state', 'input_artifact_id']:
            assert actual[key] == old_runs[item['run_id']][key]
        if kind == 'case' and item['round'] == 2:
            assert actual['comparison_context']['previous_run_id'] == config['case_run_ids'][0]
            assert actual['comparison_context']['comparison_result_id'] == item['comparison_result_id']
        runs.append({'subject_type': kind, 'subject_id': subject['id'], 'run_id': actual['id'], 'state': actual['state']})
paths = {}
for path in (original / 'runs/part2/http').glob('*.json'):
    if path.name.endswith('.intent.json'):
        continue
    receipt = json.loads(path.read_text())
    body = receipt.get('response', {}).get('body')
    if isinstance(body, dict) and body.get('availability') == 'available':
        metadata = body.get('artifact') or body.get('metadata') or {}
        if metadata.get('id'):
            paths.setdefault(metadata['id'], receipt['request']['path'])
models = []
contexts = []
for artifact in snapshot['artifacts']:
    content = artifact.get('content_json')
    if not isinstance(content, dict):
        continue
    is_model = 'raw' in content
    is_context = artifact['schema_version'] == 'socai2.baseline-context.v1'
    if not (is_model or is_context):
        continue
    actual = get(paths[artifact['id']])
    assert actual['content_json'] == content and actual['content_text'] == artifact['content_text']
    if is_model:
        models.append({'artifact_id': artifact['id'], 'run_id': artifact['run_id'], 'unchanged': True})
    else:
        ids = content['scope']['alert_ids']
        sources = [content['alerts'][alert_id]['alert']['connector_type'] for alert_id in ids]
        assert all(any(source.startswith(prefix) for prefix in config['test_source_prefixes']) for source in sources)
        contexts.append({'run_id': artifact['run_id'], 'artifact_id': artifact['id'], 'frozen_alert_count': len(ids), 'sources': sources})
assert len(runs) == 6 and len(models) == 8 and sorted(c['frozen_alert_count'] for c in contexts) == [1, 2]
out = {'status': 'passed', 'runs': runs, 'model_originals': models, 'case_contexts': contexts,
       'http_gets': len(reads), 'reads': reads, 'business_posts': 0, 'model_calls': 0}
(here / 'live-http-verification.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': out['status'], 'runs': len(runs), 'originals': len(models), 'contexts': len(contexts), 'http_gets': len(reads)}))
