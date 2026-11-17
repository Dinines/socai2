"""Read the authorized 4177 entry once; retain each response and source identity."""
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

p = Path(__file__).resolve().parent
v = json.loads((p/'runtime.json').read_text())
c = v['profile']
previous = p.parent/'streaming-w4-package-20261116-01'
reference = json.loads((previous/'remote-runtime.json').read_text())
mapping = reference['mapping']
package = Path(json.loads((p/'build-01.json').read_text())['archive']).parent/v['build']['release']
output = p/'http-responses'
output.mkdir()
requests = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def get(path, status=200):
    assert path.startswith('/') and not path.startswith('//')
    try:
        response = opener.open(c['local_entry']+path, timeout=c['http_timeout_seconds'])
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read()
        filename = f'{len(requests)+1:02}.body'
        (output/filename).write_bytes(body)
        headers = dict(response.headers)
        requests.append({'path': path, 'status': response.status, 'body': 'http-responses/'+filename,
                         'sha256': hashlib.sha256(body).hexdigest(), 'headers': headers})
        (p/'http-requests.json').write_text(json.dumps(requests, indent=2)+'\n')
        assert response.status == status, (path, response.status)
        if path.startswith('/api/v1/socai2/'):
            assert response.headers.get('X-Investigation-Environment') == c['environment_label']
        if status == 307:
            assert response.headers['Location'] == '/viewer/'
            assert response.headers['Cache-Control'] == 'no-store'
        return body


def read(path):
    return json.loads(get(path))


for path in ['/', '/index.html']:
    get(path, 307)
assert get('/viewer/') == (package/'services/investigation_test/web/index.html').read_bytes()
assert read('/viewer/config.json')['viewer_version'] == v['service_version']
caps = read('/test-api/v1/capabilities')
assert caps['service_version'] == caps['viewer_version'] == v['service_version'] and caps['read_only']
assert caps['environment_label'] == c['environment_label'] and caps['investigation_http']['get_operations'] == 55
assert read('/openapi.json') == json.loads((package/'test-openapi.json').read_text())
assert read('/test-api/v1/batches')['total'] == 2
prefix = '/test-api/v1/batches/'+reference['observation_batch']
assert read(prefix)['batch']['provenance'] == 'saved_evidence'
assert read('/test-api/v1/batches/w2-live-s01-s04-20261115-01')['batch']['execution_state'] == 'failed'
assert read(prefix+'/evidence/quality-summary?format=content')['status'] == 'NOT_PASSED'
base = '/api/v1/socai2'
cases = []
for cid, members, rounds in [(mapping['event_case_id'], 4, 2), (mapping['control_case_id'], 1, 1)]:
    case = read(base+'/cases/'+cid)
    history = read(base+'/cases/'+cid+'/history')
    assert case['case']['id'] == cid and case['member_count'] == members
    assert len(history['items']) == rounds and history.get('next_before_run_id') is None
    freshness = case['current_assessment']['input_freshness']
    assert freshness['state'] == ('current' if rounds == 2 else 'stale')
    cases.append({'id': cid, 'members': members, 'runs': rounds, 'freshness': freshness})
for run in mapping['runs']:
    incident = run['kind'] == 'incident_diagnosis'
    path = base+'/incidents/'+run['subject_id']+'/analysis' if incident else base+'/cases/'+run['subject_id']
    current = read(path+'/runs/'+run['run_id'])
    assert current['run']['id'] == run['run_id'] and current['run']['state'] == 'completed'
    if incident:
        assert current['result']['id'] == run['result_id']
        assert current['input_selection']['selected_count'] == 4 and current['valid_for_current_input']
    else:
        assert current['input_member_count'] == 4 and current['run']['comparison_context'] == run['comparison_context']
        result = read(path+'/results/'+run['result_id'])['result']
        assert all(result[key] == val for key, val in run['result_states'].items())
        for key, field, container in [('previous_run_url', 'previous_run_id', 'run'),
                                      ('comparison_result_url', 'comparison_result_id', 'result')]:
            assert current[key].startswith(base+'/cases/'+run['subject_id']+'/')
            assert read(current[key])[container]['id'] == run['comparison_context'][field]
old_requests = json.loads((previous/'remote/evidence/requests.json').read_text())
for original in reference['originals'].values():
    request = next(r for r in old_requests if original['artifact_id'] in r['path'])
    body = read(request['path'])
    assert body['availability'] == 'available'
    raw = (json.dumps(body['content_json'], ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode() if body['content_json'] is not None
           else (body['content_text'] or '').encode())
    assert hashlib.sha256(raw).hexdigest() == original['sha256']
receipt = {'status': 'passed', 'observed_at': datetime.now(timezone.utc).isoformat(),
           'entry': c['local_entry'], 'service_version': caps['service_version'],
           'http_gets': len(requests), 'http_307': 2, 'http_200': len(requests)-2,
           'business_proxy_gets': sum(r['path'].startswith(base+'/') for r in requests),
           'cases': cases, 'originals_checked': reference['originals'],
           'current_case_result_states': mapping['runs'][1]['result_states'],
           'quality': 'NOT_PASSED', 'business_writes': 0, 'model_calls': 0}
(p/'http-validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(receipt, ensure_ascii=False, indent=2))
