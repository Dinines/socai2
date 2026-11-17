"""W4 only: read the packaged candidate, restart once, preserve state and stop."""
import hashlib
import json
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

v = json.load(sys.stdin)
c, build = v['candidate'], v['build']
root = Path(c['root'])
prepared = json.loads((root/'evidence/prepare.json').read_text())
assert prepared['status'] == 'passed' and prepared['archive_sha256'] == v['archive_sha256']
package = root/build['release']
image = build['image']
out = root/'evidence'
responses = out/'responses'
responses.mkdir()


def command(args, *, include_stderr=False):
    result = subprocess.run(args, capture_output=True, text=True,
                            timeout=c['command_timeout_seconds'], check=False)
    assert result.returncode == 0, result.stderr[-1500:]
    return result.stdout + (result.stderr if include_stderr else '')


def inspect():
    return json.loads(command(['docker', 'inspect', c['container']]))[0]


def protected():
    return [{'name': r['Name'], 'id': r['Id'], 'image': r['Image'], 'state': r['State']['Status']}
            for r in json.loads(command(['docker', 'inspect', *v['protected_containers']]))]


def ledger_hashes():
    folder = root/'state/ledger'
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}


assert protected() == prepared['protected_after']
assert ledger_hashes() == v['ledger_hashes']
with socket.socket() as sock:
    sock.bind((c['bind_host'], c['bind_port']))
created = command(['docker', 'create', '--name', c['container'], '--restart', 'no', '--read-only',
    '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--network', c['network'],
    '--memory', c['memory'], '--pids-limit', str(c['pids_limit']), '--tmpfs', c['tmpfs'],
    '--publish', f"{c['bind_host']}:{c['bind_port']}:{c['container_port']}",
    '--mount', f"type=bind,src={root/'config'},dst={c['config_mount']},readonly",
    '--mount', f"type=bind,src={root/'state'},dst={c['ledger_mount']},readonly",
    prepared['image_id']]).strip()
assert inspect()['Id'] == created
requests = []
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(path, *, upstream=False):
    assert path.startswith('/') and (not upstream or path == '/openapi.json')
    base = c['upstream_base_url'] if upstream else f"http://{c['bind_host']}:{c['bind_port']}"
    with opener.open(base+path, timeout=c['http_timeout_seconds']) as response:
        body = response.read()
        name = f'{len(requests)+1:02}.body'
        (responses/name).write_bytes(body)
        requests.append({'path': path, 'source': 'dependency_contract' if upstream else 'test_service',
                         'status': response.status, 'body': 'responses/'+name,
                         'sha256': hashlib.sha256(body).hexdigest(),
                         'content_type': response.headers.get('Content-Type'),
                         'source_environment': response.headers.get('X-Investigation-Environment')})
        assert response.status == 200
        if path.startswith('/api/v1/socai2/'):
            assert requests[-1]['source_environment'] == c['environment_label']
        return body


def read(path, **kwargs):
    return json.loads(get(path, **kwargs))


def start():
    command(['docker', 'start', c['container']])
    deadline = time.monotonic()+c['startup_timeout_seconds']
    while time.monotonic() < deadline:
        assert inspect()['State']['Running']
        logs = command(['docker', 'logs', c['container']], include_stderr=True)
        starts = logs.count('Application startup complete.')
        stops = logs.count('Application shutdown complete.')
        if starts <= stops:
            time.sleep(0.2)
            continue
        try:
            with socket.create_connection((c['bind_host'], c['bind_port']), timeout=0.2):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError('candidate_start_timeout')


def stop():
    if inspect()['State']['Running']:
        command(['docker', 'stop', '--time', str(c['stop_timeout_seconds']), c['container']])
    return inspect()['State']['ExitCode']


case_summaries = []
exits = []
try:
    start()
    caps = read('/test-api/v1/capabilities')
    assert caps['service_version'] == caps['viewer_version'] == '0.4.0'
    assert caps['environment_label'] == c['environment_label'] and caps['read_only']
    assert caps['investigation_http']['get_operations'] == 55
    assert read('/openapi.json') == json.loads((package/'test-openapi.json').read_text())
    assert read('/openapi.json', upstream=True) == json.loads((package/'investigation-openapi.json').read_text())
    assert read('/viewer/config.json')['viewer_version'] == '0.4.0'
    for path, name in [('/viewer/', 'index.html'), ('/viewer/assets/viewer.js', 'viewer.js'),
                       ('/viewer/assets/viewer.css', 'viewer.css'), ('/viewer/assets/viewer_state.mjs', 'viewer_state.mjs')]:
        assert get(path) == (package/'services/investigation_test/web'/name).read_bytes()
    assert read('/test-api/v1/batches')['total'] == 2
    prefix = '/test-api/v1/batches/'+v['observation_batch']
    detail = get(prefix)
    assert json.loads(detail)['batch']['provenance'] == 'saved_evidence'
    assert len(read(prefix+'/cases')['items']) == 3
    assert len(read(prefix+'/operations')['items']) == 3
    assert len(read(prefix+'/quality-issues')['items']) == 2
    evidence = get(prefix+'/evidence/quality-summary?format=content')
    assert json.loads(evidence)['status'] == 'NOT_PASSED'
    read('/test-api/v1/batches/w2-live-s01-s04-20261115-01')
    mapping = v['mapping']
    base = '/api/v1/socai2'
    for cid, count, runs in [(mapping['event_case_id'], 4, 2), (mapping['control_case_id'], 1, 1)]:
        case = read(base+'/cases/'+cid)
        history = read(base+'/cases/'+cid+'/history')
        assert case['case']['id'] == cid and case['member_count'] == count
        assert len(history['items']) == runs and history.get('next_before_run_id') is None
        freshness = case['current_assessment']['input_freshness']
        assert freshness['state'] == ('current' if runs == 2 else 'stale')
        case_summaries.append({'case_id': cid, 'members': count, 'runs': runs, 'input_freshness': freshness})
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
            assert all(result[key] == value for key, value in run['result_states'].items())
            for key, field, container in [('previous_run_url', 'previous_run_id', 'run'),
                                          ('comparison_result_url', 'comparison_result_id', 'result')]:
                assert current[key].startswith(base+'/cases/'+run['subject_id']+'/')
                assert read(current[key])[container]['id'] == run['comparison_context'][field]
        steps = read(base+'/analysis-runs/'+run['run_id']+'/steps')
        assert len(steps['items']) == (2 if incident else 17)
        directory = base+'/analysis-runs/'+run['run_id']+'/artifacts'
        page, items = directory+'?limit=20', []
        while page:
            response = read(page)
            items.extend(response['items'])
            cursor = response.get('next_cursor')
            page = directory+'?'+urllib.parse.urlencode({'limit': 20, 'cursor': cursor}) if cursor else None
        original = v['originals']['I' if incident else 'C6']
        item = next(row for row in items if row['id'] == original['artifact_id'])
        assert item['content_url'].startswith(base+'/')
        body = read(item['content_url'])
        assert body['availability'] == 'available'
        raw = (json.dumps(body['content_json'], ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                          allow_nan=False).encode() if body['content_json'] is not None
               else (body['content_text'] or '').encode())
        assert hashlib.sha256(raw).hexdigest() == original['sha256']
    assert ledger_hashes() == v['ledger_hashes']
    exits.append(stop())
    start()
    assert read('/test-api/v1/capabilities') == caps
    assert get(prefix) == detail
    assert get(prefix+'/evidence/quality-summary?format=content') == evidence
finally:
    exits.append(stop())
    (out/'requests.json').write_text(json.dumps(requests, indent=2)+'\n')
    (out/'service.log').write_text(command(['docker', 'logs', c['container']], include_stderr=True))
assert c['stop_after_validation'] and ledger_hashes() == v['ledger_hashes']
assert protected() == prepared['protected_after']
row = inspect()
assert row['Image'] == prepared['image_id'] and not row['State']['Running']
assert all(not m['RW'] for m in row['Mounts'] if m['Type'] == 'bind')
assert row['HostConfig']['ReadonlyRootfs'] and row['HostConfig']['RestartPolicy']['Name'] == 'no'
for name, sha in prepared['configuration_hashes'].items():
    assert hashlib.sha256((root/'config'/name).read_bytes()).hexdigest() == sha
result = {'status': 'passed', 'observed_at': datetime.now(timezone.utc).isoformat(), 'container_id': created,
    'image_id': row['Image'], 'state': row['State']['Status'], 'exit_code': row['State']['ExitCode'],
    'service_version': caps['service_version'], 'viewer_version': caps['viewer_version'],
    'http_gets': len(requests), 'business_proxy_gets': sum(r['path'].startswith(base+'/') for r in requests),
    'dependency_contract_gets': sum(r['source'] == 'dependency_contract' for r in requests),
    'cases': case_summaries, 'originals_checked': v['originals'], 'server_exit_codes': exits,
    'ledger_files_unchanged': len(v['ledger_hashes']), 'configuration_hashes': prepared['configuration_hashes'],
    'mounts': [{'source': m['Source'], 'destination': m['Destination'], 'rw': m['RW']} for m in row['Mounts']],
    'command': row['Config']['Entrypoint']+row['Config']['Cmd'],
    'port_bindings': row['HostConfig']['PortBindings'], 'protected_services_unchanged': True,
    'new_model_calls': 0, 'business_writes': 0, 'direct_database_queries': 0, 'kafka_messages': 0,
    'formal_4177_switched': False, 'model_quality': 'NOT_PASSED', 'whole_change_accepted': False}
(out/'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
