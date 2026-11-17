"""Same-snapshot A/I result reads. No SQL, writes, resubmission or execution."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SUPPLY = ROOT / 'docs/operations/evidence/test-streaming-ai-20261115-01'
SAVED = '--verify-saved' in sys.argv


def save(name, data):
    with (OUT / name).open('x') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def get_all(urls, name):
    if SAVED:
        rows = json.loads((OUT / name).read_text())['receipts']
        assert [r['url'] for r in rows] == urls
    else:
        code = '''import json,urllib.request,urllib.error
from datetime import datetime,timezone
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for url in URLS:
    r={"method":"GET","url":url,"at":datetime.now(timezone.utc).isoformat(),"authorization_header":False}
    try:
        with opener.open(url,timeout=30) as response:r.update(status=response.status,body=json.load(response))
    except urllib.error.HTTPError as error:r.update(status=error.code,body=error.read().decode())
    except Exception as error:r.update(status=None,error=type(error).__name__)
    print(json.dumps(r,ensure_ascii=False),flush=True)
    if r["status"]!=200:break
'''.replace('URLS', repr(urls))
        result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
                                 'sting-infra21', 'python3', '-'], input=code, text=True,
                                capture_output=True, timeout=180)
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        save(name, {'ssh_exit': result.returncode, 'ssh_stderr': result.stderr, 'receipts': rows})
        assert result.returncode == 0, name
    assert len(rows) == len(urls) and all(r['status'] == 200 and r['method'] == 'GET' for r in rows), name
    return {r['url']: r['body'] for r in rows}


def norm(value):
    if isinstance(value, dict):
        return {k: norm(v) for k, v in value.items()}
    if isinstance(value, list):
        return [norm(v) for v in value]
    if isinstance(value, str) and 'T' in value:
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).isoformat()
        except ValueError:
            pass
    return value


def same_fields(public, saved):
    assert all(norm(v) == norm(saved[k]) for k, v in public.items() if k in saved), public.keys()


def main():
    mapping = json.loads((SUPPLY / 'actual-analysis-map-01.json').read_text())
    pg_file = SUPPLY / 'analysis-pg-01.json'
    assert mapping['status'] == 'passed' and mapping['source'] == 'real_saved_snapshot'
    assert hashlib.sha256(pg_file.read_bytes()).hexdigest() == mapping['snapshot_sha256']
    validation = json.loads((SUPPLY / 'analysis-validation-01.json').read_text())
    assert validation['status'] == 'passed' and validation['snapshot_sha256'] == mapping['snapshot_sha256']
    rows = json.loads(pg_file.read_text())['rows']
    policy = json.loads((ROOT / 'deploy/aisoc21/streaming-candidate-20261115-01/analysis/lifecycle.json').read_text())
    profile = json.loads((ROOT / 'deploy/http-service/streaming-20261115-01/profile.json').read_text())
    host = f"http://{profile['bind']}:{profile['port']}"
    base = host + '/api/v1/socai2'
    runs = mapping['runs']
    tasks = {r['id']: r for r in rows['analysis_tasks']}
    urls = []
    for task in tasks.values():
        urls.append(f"{base}/{task['subject_type']}s/{task['subject_id']}/analysis-tasks/{task['id']}")
    for run in runs:
        kind = 'alerts' if run['kind'] == 'alert_basic' else 'incidents'
        run['subject_url'] = f"{base}/{kind}/{run['subject_id']}"
        run['url'] = run['subject_url'] + '/analysis/runs/' + run['run_id']
        urls += [run['subject_url'], run['subject_url'] + '/analysis', run['url'], run['url'] + '/trace',
                 base + '/analysis-runs/' + run['run_id'] + '/steps',
                 base + '/analysis-runs/' + run['run_id'] + '/artifacts']
        if kind == 'incidents':
            urls.append(run['subject_url'] + '/analysis-tasks')
    urls = list(dict.fromkeys(urls))
    plan = {'batch_id': mapping['batch_id'], 'base_url': base, 'urls': urls,
            'supplied_evidence': {name: hashlib.sha256((SUPPLY / name).read_bytes()).hexdigest()
                for name in ('actual-analysis-map-01.json', 'analysis-pg-01.json', 'analysis-validation-01.json',
                             'quality-findings-01.json', 'usage-01.json')},
            'purpose': 'Only new analysis output/state/actual scope; reuse earlier ingress and config acceptance.'}
    if SAVED:
        assert json.loads((OUT / 'plan.json').read_text()) == plan
    else:
        save('plan.json', plan)
    got = get_all(urls, 'get-01.json')
    # Follow only real cursors. This finished batch fits one page per directory.
    pages = {url: [value] for url, value in got.items() if 'next_cursor' in value or 'next_before_run_id' in value}
    while True:
        next_urls = []
        owners = {}
        for url, values in pages.items():
            last = values[-1]
            field = 'cursor' if 'next_cursor' in last else 'before_run_id'
            cursor = last.get('next_' + field)
            if cursor is not None:
                follow = url + '?' + urlencode({field: cursor})
                assert follow not in got, 'repeated_cursor'
                next_urls.append(follow)
                owners[follow] = url
        if not next_urls:
            break
        more = get_all(next_urls, f'page-{len(got):03}.json')
        got.update(more)
        for url, value in more.items():
            pages[owners[url]].append(value)
    content_urls = []
    for run in runs:
        needed = {run['input_artifact_id'], run['policy_artifact_id']}
        for model in run['models']:
            needed.update([model['request_artifact_id'], model['response_artifact_id'], *model['original_artifact_ids']])
        needed.update(q['artifact_id'] for q in run['queries'])
        directory_url = base + '/analysis-runs/' + run['run_id'] + '/artifacts'
        directory = {a['id']: a for page in pages[directory_url] for a in page['items']}
        assert needed <= directory.keys(), 'missing_required_artifact'
        for identity in sorted(needed):
            url = host + directory[identity]['content_url']
            assert urlsplit(url).netloc == urlsplit(host).netloc and url.startswith(run['url'] + '/artifacts/')
            content_urls.append(url)
    got.update(get_all(list(dict.fromkeys(content_urls)), 'content-01.json'))
    checked = []
    for task in tasks.values():
        url = f"{base}/{task['subject_type']}s/{task['subject_id']}/analysis-tasks/{task['id']}"
        view = got[url]
        assert view['task_id'] == task['id'] and host + view['status_url'] == url
        assert view['status'] == task['state']
        same_fields(view, task)
        attempts = [r for r in rows['analysis_attempts'] if r['task_id'] == task['id']]
        assert len(view['attempts']) == len(attempts)
        for actual in view['attempts']:
            saved = next(r for r in attempts if r['attempt_no'] == actual['attempt_no'])
            same_fields(actual, saved)
            assert actual['run_id'] == saved['run_id']
            if actual['run_id']:
                assert host + actual['run_url'] in got
        if task['id'] in mapping['old_task_ids']:
            assert view['status'] == 'skipped' and view['reason_code'] == 'closed_before_start'
            assert view['attempts'] == [] and view['results'] == [] and view['latest_run_id'] is None
    for run in runs:
        rid = run['run_id']
        entry = got[run['url']]
        saved_run = next(r for r in rows['runs'] if r['id'] == rid)
        same_fields(entry['run'], saved_run)
        assert entry['run']['id'] == rid and entry['run']['state'] == 'completed'
        assert entry['run']['delivery_state'] == run['delivery_state']
        table = 'alert_assessments' if run['kind'] == 'alert_basic' else 'incident_diagnoses'
        result = next(r for r in rows[table] if r['source_run_id'] == rid)
        same_fields(entry['result'], result)
        assert entry['result']['id'] in run['result_ids'] and entry['result']['source_run_id'] == rid
        task = got[run['subject_url'] + '/analysis-tasks/' + run['task_id']]
        assert task['latest_run_id'] == rid and len(task['results']) == 1
        assert task['results'][0]['id'] == result['id'] and task['results'][0]['source_run_id'] == rid
        assert host + task['results'][0]['url'] == run['url']
        directory = got[run['subject_url'] + '/analysis']
        assert directory['current_pointer_id'] == result['id'] and directory['current'] == entry
        history = [item for page in pages[run['subject_url'] + '/analysis'] for item in page['entries']]
        assert len(history) == 1 and history[0] == entry and entry['is_current_pointer']
        trace = got[run['url'] + '/trace']
        assert trace['run']['id'] == rid
        for section, table_name in [('steps', 'run_steps'), ('artifacts', 'artifacts')]:
            url = host + trace[section + '_url']
            expected = [r for r in rows[table_name] if r['run_id'] == rid]
            items = [item for page in pages[url] for item in page['items']]
            assert {item['id'] for item in items} == {r['id'] for r in expected}
            assert len(items) == len(expected) == trace[section + '_total']
            for item in items:
                same_fields(item, next(r for r in expected if r['id'] == item['id']))
                if section == 'steps':
                    for ref in item['artifact_refs']:
                        original = next(r for r in rows['artifacts'] if r['id'] == ref['artifact_id'])
                        assert original['run_id'] == ref['run_id']
                        assert original.get('alert_id') == ref['subject_id'] or original.get('incident_id') == ref['subject_id']
        subject = got[run['subject_url']]
        if run['kind'] == 'alert_basic':
            assert subject['facts']['latest_triage_id'] == result['id']
            assert subject['triage']['source_run_id'] == rid
            assert entry['result']['rationale'] == '告'
            if entry['explanation']:
                explanation = next(r for r in rows['artifacts'] if r['id'] == entry['explanation']['artifact_id'])
                assert entry['explanation']['available'] and entry['explanation']['content'] == explanation['content_json']
        else:
            assert subject['facts']['latest_diagnosis_id'] == result['id'] and entry['result']['summary'] == 'A'
            assert norm(entry['input_selection']) == norm({**run['selection'], 'input_artifact_id': run['input_artifact_id']})
            coverage = entry['analysis_coverage']
            assert coverage['state'] == 'complete' and coverage['not_analyzed_count'] == 0
            assert set(coverage['covered_alert_ids']) == set(run['selection']['selected_alert_ids'])
            assert coverage['analyzed_count'] + coverage['unresolved_count'] == run['selection']['selected_count']
            page = got[run['subject_url'] + '/analysis-tasks']
            assert page['total'] == 1 and page['items'] == [task]
            state = next(r for r in rows['analysis_subject_state'] if r['subject_id'] == run['subject_id'])
            update = page['update_state']
            assert norm(update['next_check_at']) == norm(state['next_check_at'])
            assert norm(update['last_normal_completed_at']) == norm(state['last_normal_completed_at'])
            expected_expiry = datetime.fromisoformat(state['last_normal_completed_at']) + timedelta(seconds=policy['automatic_window_seconds'])
            assert norm(update['auto_expires_at']) == expected_expiry.isoformat()
            assert update['eligible'] and update['ineligible_reason'] is None
        checked.append({'run_id': rid, 'task_id': run['task_id'], 'result_id': result['id'],
                        'execution_state': 'completed', 'model_quality': 'NOT_PASSED'})
    for url in content_urls:
        content = got[url]
        saved = next(r for r in rows['artifacts'] if r['id'] == url.rsplit('/', 1)[-1])
        assert content['availability'] == 'available' and content['metadata']['id'] == saved['id']
        assert content['content_json'] == saved['content_json'] and content['content_text'] == saved['content_text']
        same_fields(content['metadata'], saved)
    quality = json.loads((SUPPLY / 'quality-findings-01.json').read_text())
    assert quality['status'] == 'NOT_PASSED'
    save('result.json', {'http_readback_passed': True, 'http_gets': len(got), 'all_status_200': True,
                         'authentication': 'none', 'runs': checked, 'old_closed_tasks_skipped': len(mapping['old_task_ids']),
                         'step_count': len(rows['run_steps']), 'run_artifact_metadata_count': sum(bool(a['run_id']) for a in rows['artifacts']),
                         'required_artifact_contents_read': len(set(content_urls)), 'source_queries_read': sum(len(r['queries']) for r in runs),
                         'incident_selected_and_covered': 3, 'lifecycle_window_seconds_readback': policy['automatic_window_seconds'],
                         'model_quality': 'NOT_PASSED', 'quality_evidence': str((SUPPLY / 'quality-findings-01.json').relative_to(ROOT)),
                         'business_writes': 0, 'direct_database_queries': 0, 'new_model_calls': 0,
                         'case_creation_or_execution': False, 'complete_change_accepted': False})
    print(json.dumps({'http_readback_passed': True, 'http_gets': len(got), 'runs': len(checked), 'model_quality': 'NOT_PASSED'}))


if __name__ == '__main__':
    main()
