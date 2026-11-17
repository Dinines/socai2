"""Two frozen S01 Case operations, separately submitted and immediately read back."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def save(name, data):
    with (OUT / name).open('x') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def request(items, name):
    assert not (OUT / name).exists(), 'Inspect existing receipt; do not automatically repeat a write.'
    code = '''import json,urllib.request,urllib.error
from datetime import datetime,timezone
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for item in REQUESTS:
    result={"request":item,"at":datetime.now(timezone.utc).isoformat(),"authorization_header":False}
    req=urllib.request.Request(item["url"],method=item["method"],data=json.dumps(item["body"]).encode() if "body" in item else None,headers={"Content-Type":"application/json"})
    try:
        with opener.open(req,timeout=30) as response:result.update(status=response.status,body=json.load(response))
    except urllib.error.HTTPError as error:result.update(status=error.code,body=error.read().decode())
    except Exception as error:result.update(status=None,error=type(error).__name__,outcome="unknown")
    print(json.dumps(result,ensure_ascii=False),flush=True)
    if result["status"] not in [200,201]:break
'''.replace('REQUESTS', repr(items))
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
                             'sting-infra21', 'python3', '-'], input=code, text=True,
                            capture_output=True, timeout=120)
    receipts = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    save(name, {'ssh_exit': result.returncode, 'ssh_stderr': result.stderr, 'receipts': receipts})
    assert result.returncode == 0 and len(receipts) == len(items), name
    assert all(r['status'] == (201 if r['request']['method'] == 'POST' else 200) for r in receipts), name
    return {r['request']['url']: r['body'] for r in receipts}


def main():
    label = sys.argv[1]
    assert label in {'whole_incident', 'single_alert_a01', 'receiver'}
    prepared = json.loads((OUT / 'preparation-01.json').read_text())
    assert hashlib.sha256((OUT / 'requests.json').read_bytes()).hexdigest() == prepared['request_file_sha256']
    plan = json.loads((OUT / 'requests.json').read_text())
    requests = {r['label']: r for r in plan['requests']}
    source = ROOT / 'docs/operations/evidence/test-streaming-case-initial-20261115-01/source-acceptance-01.json'
    ready = ROOT / 'docs/operations/evidence/streaming-case-20261115-01/prepare-02.json'
    assert json.loads(source.read_text())['status'] == 'passed'
    assert json.loads(ready.read_text())['status'] == 'passed'
    if label == 'whole_incident':
        save('readiness-references.json', {'source_acceptance': str(source.relative_to(ROOT)),
             'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
             'case_prepare': str(ready.relative_to(ROOT)), 'case_prepare_sha256': hashlib.sha256(ready.read_bytes()).hexdigest(),
             'coordination': 'Investigation owner confirmed Case source ready, scheduler stopped, proceed in frozen order.'})
    else:
        assert json.loads((OUT / 'verification-whole_incident.json').read_text())['passed']
    first = requests['whole_incident']
    host = urlsplit(first['url']).scheme + '://' + urlsplit(first['url']).netloc
    if label == 'receiver':
        whole = json.loads((OUT / 'verification-whole_incident.json').read_text())
        single = json.loads((OUT / 'verification-single_alert_a01.json').read_text())
        assert single['passed'] and whole['case_id'] != single['case_id']
        incident_id = first['expected_explicit_incident_ids'][0]
        url = first['url'].removesuffix('/cases') + '/incidents/' + incident_id
        view = request([{'method': 'GET', 'url': url}], 'receiver-read-01.json')[url]
        save('receiver-observation.json', {'incident_id': incident_id, 'expected_case_id': whole['case_id'],
                                          'case_receiving': view['case_receiving']})
        print(json.dumps({'case_receiving': view['case_receiving']}, ensure_ascii=False))
        return
    item = requests[label]
    receipt = request([{k: item[k] for k in ('method', 'url', 'body')}], f'post-{label}.json')[item['url']]
    assert receipt['operation_key'] == item['body']['operation_key'] and receipt['requested_case_id'] is None
    assert receipt['changed'] and receipt['excluded_alert_ids'] == [] and len(receipt['allocations']) == 1
    allocation = receipt['allocations'][0]
    cid = allocation['case_id']
    assert receipt['primary_case_id'] == receipt['continuation_root_case_id'] == receipt['receiving_case_id'] == cid
    assert allocation['created'] and allocation['changed'] and allocation['previous_case_id'] is None
    assert sorted(allocation['added_alert_ids']) == sorted(item['expected_alert_ids']) and allocation['existing_alert_ids'] == []
    assert allocation['linked_incident_ids'] == item['expected_explicit_incident_ids']
    assert receipt['incident_receivers'] == [{'incident_id': iid, 'active_case_id': cid} for iid in item['expected_explicit_incident_ids']]
    initial = allocation['initial_task']
    assert initial['status'] == 'accepted' and initial['subject_type'] == 'case' and initial['subject_id'] == cid
    case_url, task_url = host + allocation['case_url'], host + initial['status_url']
    assert case_url == item['url'] + '/' + cid and task_url.startswith(case_url + '/analysis-tasks/')
    views = request([{'method': 'GET', 'url': case_url}, {'method': 'GET', 'url': task_url}], f'read-{label}.json')
    case, task = views[case_url], views[task_url]
    assert case['case']['id'] == cid and case['case']['scope_revision'] == allocation['scope_revision']
    assert case['case']['title'] == item['body']['title']
    assert case['member_count'] == len(item['expected_alert_ids']) and not case['members_truncated']
    assert sorted(m['alert_id'] for m in case['members']) == sorted(item['expected_alert_ids'])
    assert case['linked_incident_count'] == len(item['expected_explicit_incident_ids']) and not case['linked_incidents_truncated']
    assert sorted(i['incident_id'] for i in case['linked_incidents']) == sorted(item['expected_explicit_incident_ids'])
    assert case['current_assessment'] is None and case['case']['current_assessment_id'] is None and case['baseline_records'] == []
    assert case['case']['continuation'] == {'root_case_id': cid, 'previous_case_id': None, 'receiving_case_id': cid}
    assert task['task_id'] == initial['task_id'] and task['subject_id'] == cid and task['subject_type'] == 'case'
    assert task['status'] == 'accepted' and task['source'] == 'case_create' and task['intent'] == 'initial'
    assert task['attempts'] == [] and task['results'] == [] and task['latest_run_id'] is None and task['started_at'] is None
    verified = {'passed': True, 'label': label, 'case_id': cid, 'task_id': initial['task_id'],
                'scope_revision': allocation['scope_revision'], 'alert_ids': item['expected_alert_ids'],
                'explicit_incident_ids': item['expected_explicit_incident_ids'], 'operation_key': receipt['operation_key'],
                'task_status': task['status'], 'case_url': case_url, 'task_url': task_url,
                'attempts': 0, 'run_id': None, 'results': 0, 'http_post_count': 1, 'http_get_count': 2,
                'model_or_dispatch_started': False}
    save(f'verification-{label}.json', verified)
    print(json.dumps(verified, ensure_ascii=False))


if __name__ == '__main__':
    main()
