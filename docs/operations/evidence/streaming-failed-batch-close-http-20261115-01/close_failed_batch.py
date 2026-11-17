"""One-shot existing HTTP management of the four explicitly assigned failed subjects."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'docs/operations/evidence/test-streaming-s01-ingress-20261115-01/readback/alerts-pg.json'
PROFILE = ROOT / 'deploy/http-service/streaming-20261115-01/profile.json'
REASON = '验收批来源范围失败，停止后续分析'


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def http(requests, filename):
    code = '''import json, urllib.request, urllib.error
from datetime import datetime, timezone
requests = json.loads(PAYLOAD)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for item in requests:
    result = {"request": item, "at": datetime.now(timezone.utc).isoformat()}
    payload = json.dumps(item["body"]).encode() if "body" in item else None
    req = urllib.request.Request(item["url"], data=payload, method=item["method"], headers={"Content-Type":"application/json"})
    try:
        with opener.open(req, timeout=30) as response:
            result.update(status=response.status, body=json.load(response))
    except urllib.error.HTTPError as error:
        result.update(status=error.code, body=error.read().decode())
    except Exception as error:
        result.update(status=None, error=type(error).__name__, outcome="unknown")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if result["status"] != 200: break
'''.replace('PAYLOAD', repr(json.dumps(requests, ensure_ascii=False)))
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
                             'sting-infra21', 'python3', '-'], input=code,
                            text=True, capture_output=True, timeout=180)
    receipts = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    save(filename, {'ssh_exit': result.returncode, 'ssh_stderr': result.stderr, 'receipts': receipts})
    assert result.returncode == 0 and len(receipts) == len(requests), filename
    assert all(item['status'] == 200 for item in receipts), filename
    return {item['request']['url']: item['body'] for item in receipts}


def main():
    assert not (OUT / 'plan.json').exists(), 'Already attempted: inspect receipts, never blindly repeat mutations.'
    source = json.loads(SOURCE.read_text())
    profile = json.loads(PROFILE.read_text())
    base = f"http://{profile['bind']}:{profile['port']}/api/v1/socai2"
    subjects = []
    for kind in ('alerts', 'incidents'):
        for row in source['rows'][kind]:
            tasks = [t for t in source['rows']['analysis_tasks'] if t['subject_id'] == row['id']]
            assert len(tasks) == 1 and tasks[0]['state'] == 'accepted' and tasks[0]['started_at'] is None
            subjects.append({'kind': kind, 'id': row['id'], 'task_id': tasks[0]['id'],
                             'source_identity': {k: v for k, v in row.items() if k in
                                                 ('source_namespace', 'source_alert_id', 'source_incident_id')},
                             'operation_key': str(uuid4())})
    assert len(subjects) == 4 and len(source['rows']['alerts']) == 3
    save('plan.json', {'at': datetime.now(timezone.utc).isoformat(), 'base_url': base,
                      'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                      'profile_sha256': hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
                      'reason': REASON, 'subjects': subjects})
    requests = []
    for s in subjects:
        s['url'] = f"{base}/{s['kind']}/{s['id']}"
        paths = ['', '/analysis-tasks'] + (['/records/sources'] if s['kind'] == 'alerts' else [])
        requests.extend({'method': 'GET', 'url': s['url'] + p} for p in paths)
    before = http(requests, 'before.json')
    for s in subjects:
        facts = before[s['url']]['facts']
        assert facts['id'] == s['id'] and facts['handling_status'] == 'new'
        assert all(facts[k] == v for k, v in s['source_identity'].items())
        tasks = before[s['url'] + '/analysis-tasks']['items']
        assert len(tasks) == 1 and tasks[0]['task_id'] == s['task_id']
        t = tasks[0]
        assert t['status'] == 'accepted' and t['started_at'] is None and not t['attempts'] and not t['results']
        assert t['latest_run_id'] is None
        s['body'] = {'operation_key': s['operation_key'], 'expected_row_version': facts['row_version'],
                     'handling_status': 'completed' if s['kind'] == 'alerts' else 'resolved', 'reason': REASON}
        if s['kind'] == 'incidents':
            s['body']['resolution_note'] = REASON
    save('requests.json', subjects)
    writes = {}
    for i, s in enumerate(subjects, 1):
        url = s['url'] + '/management'
        writes[s['url']] = http([{'method': 'PATCH', 'url': url, 'body': s['body']}], f'patch-{i:02}.json')[url]
    after = http(requests, 'after.json')
    activities = http([{'method': 'GET', 'url': s['url'] + '/records/activities'} for s in subjects], 'activities.json')
    checked = []
    for s in subjects:
        url = s['url']
        prior, saved = before[url], after[url]
        b, a = prior['facts'], saved['facts']
        receipt = writes[url]
        assert receipt['changed'] is True and receipt['feedback_id'] is None and receipt['facts'] == a
        assert a['handling_status'] == s['body']['handling_status'] and a['row_version'] == b['row_version'] + 1
        changed = {k for k in a if a[k] != b[k]}
        allowed = {'handling_status', 'row_version', 'business_updated_at'}
        allowed |= {'closed_at', 'closed_by'} if s['kind'] == 'alerts' else {'resolved_at', 'resolved_by', 'resolution_note'}
        assert changed <= allowed, changed
        assert all(prior.get(k) == saved.get(k) for k in ('material', 'triage', 'feedback'))
        assert before[url + '/analysis-tasks']['items'] == after[url + '/analysis-tasks']['items']
        if s['kind'] == 'alerts':
            assert before[url + '/records/sources']['items'] == after[url + '/records/sources']['items']
        else:
            assert a['resolution_note'] == REASON
        act = [a for a in activities[url + '/records/activities']['items'] if a['id'] == receipt['activity_id']]
        assert len(act) == 1 and act[0]['detail']['reason'] == REASON
        checked.append({'kind': s['kind'], 'id': s['id'], 'changed_fields': sorted(changed),
                        'task_id': s['task_id'], 'task_status': 'accepted', 'activity_id': receipt['activity_id']})
    save('result.json', {'passed': True, 'subjects': checked, 'http_calls': 30,
                         'mutation_count': 4, 'authentication': 'none', 'originals_and_analysis_pointers_unchanged': True,
                         'model_dispatch_started': False, 'closed_before_start_executed': False,
                         'boundary': 'Only failed batch management verified; new ingress and complete real chain remain pending.'})
    print(json.dumps({'passed': True, 'closed_alerts': 3, 'resolved_incidents': 1, 'accepted_unstarted_tasks': 4}))


if __name__ == '__main__':
    main()
