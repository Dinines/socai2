"""Read the new I/Case rounds and their frozen comparison through candidate HTTP."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

folder = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('batch_http_reader', folder.parent/'streaming-ai-http-20261115-01/read_analysis.py')
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)
io.OUT, io.SAVED = folder, '--verify-saved' in sys.argv
config = json.loads((folder/'control-config.json').read_text())
mapping = json.loads((folder/'actual-map.json').read_text())
raw = (folder/'analysis-pg-01.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == mapping['snapshot_sha256']
rows = json.loads(raw)['rows']
index = {k: {r['id']: r for r in v} for k, v in rows.items() if k != 'analysis_subject_state'}
host = config['api_base_url']
base = host+'/api/v1/socai2'
event_case, control, iid = (mapping[k] for k in ('event_case_id', 'control_case_id', 'incident_id'))
urls = [base+'/incidents/'+iid+'/analysis']
for cid in (event_case, control):
    urls.extend([base+'/cases/'+cid, base+'/cases/'+cid+'/history', base+'/cases/'+cid+'/analysis-tasks'])
for task in mapping['tasks']:
    urls.append(f"{base}/{task['subject_type']}s/{task['subject_id']}/analysis-tasks/{task['id']}")
for run in mapping['runs']:
    prefix = 'incidents' if run['kind'] == 'incident_diagnosis' else 'cases'
    run['url'] = f"{base}/{prefix}/{run['subject_id']}"+('/analysis' if prefix == 'incidents' else '')+'/runs/'+run['run_id']
    urls.extend([run['url'], base+'/analysis-runs/'+run['run_id']+'/steps', base+'/analysis-runs/'+run['run_id']+'/artifacts'])
    if prefix == 'cases':
        urls.append(f"{base}/cases/{run['subject_id']}/results/{run['result_id']}")
got = io.get_all(list(dict.fromkeys(urls)), 'http-initial.json')
pages = {url: [body] for url, body in got.items() if any(k in body for k in ('next_cursor', 'next_before_run_id', 'next_offset'))}
page_number = 0
while True:
    follow = {}
    for url, bodies in pages.items():
        for key in ('cursor', 'before_run_id', 'offset'):
            if bodies[-1].get('next_'+key) is not None:
                follow[url+'?'+urlencode({key: bodies[-1]['next_'+key]})] = url
    if not follow:
        break
    assert not set(follow) & set(got)
    page_number += 1
    extra = io.get_all(list(follow), f'http-page-{page_number:02d}.json')
    for url, body in extra.items():
        pages[follow[url]].append(body)
    got.update(extra)
contents, comparison_urls = {}, []
for run in mapping['runs']:
    rid = run['run_id']
    detail = got[run['url']]
    io.same_fields(detail['run'], index['runs'][rid])
    for section, table in (('steps', 'run_steps'), ('artifacts', 'artifacts')):
        items = [item for page in pages[base+'/analysis-runs/'+rid+'/'+section] for item in page['items']]
        expected = {r['id']: r for r in rows[table] if r['run_id'] == rid}
        assert {item['id'] for item in items} == set(expected)
        for item in items:
            io.same_fields(item, expected[item['id']])
        if section == 'artifacts':
            directory = {item['id']: item for item in items}
    for aid in run['required_artifact_ids']:
        path = directory[aid]['content_url']
        assert path.startswith('/api/v1/socai2/')
        contents[aid] = host+path
    if run['kind'] == 'incident_diagnosis':
        io.same_fields(detail['result'], index['incident_diagnoses'][run['result_id']])
        assert detail['valid_for_current_input'] and detail['is_current_pointer']
        assert detail['input_selection']['selected_count'] == 4
    else:
        assert detail['input_member_count'] == 4
        assert detail['run']['comparison_context'] == run['comparison_context']
        comparison_urls.extend([host+detail['previous_run_url'], host+detail['comparison_result_url']])
        result = got[f"{base}/cases/{run['subject_id']}/results/{run['result_id']}"]
        io.same_fields(result['result'], index['results'][run['result_id']])
        assert result['result']['comparison_context'] == run['comparison_context']
more = list(dict.fromkeys([*contents.values(), *comparison_urls]))
more = [url for url in more if url not in got]
got.update(io.get_all(more, 'http-originals-and-comparison.json'))
for aid, url in contents.items():
    assert got[url]['availability'] == 'available'
    assert got[url]['content_json'] == index['artifacts'][aid]['content_json']
    assert got[url]['content_text'] == index['artifacts'][aid]['content_text']
for run in mapping['runs']:
    comp = run.get('comparison_context')
    if comp:
        detail = got[run['url']]
        prior = got[host+detail['previous_run_url']]
        result = got[host+detail['comparison_result_url']]
        assert prior['run']['id'] == comp['previous_run_id']
        assert result['result']['id'] == comp['comparison_result_id']
        io.same_fields(prior['run'], index['runs'][comp['previous_run_id']])
        io.same_fields(result['result'], index['results'][comp['comparison_result_id']])
for task in mapping['tasks']:
    url = f"{base}/{task['subject_type']}s/{task['subject_id']}/analysis-tasks/{task['id']}"
    view = got[url]
    assert view['status'] == task['state'] and view['task_id'] == task['id']
    if task['state'] == 'skipped':
        assert view['attempts'] == [] and view['latest_run_id'] is None
        assert view['reason_code'] == task['reason_code']
case_results = []
for cid in (event_case, control):
    url = base+'/cases/'+cid
    case = got[url]
    io.same_fields(case['case'], index['cases'][cid])
    member_ids = {m['alert_id'] for m in rows['case_alerts'] if m['case_id'] == cid}
    assert {m['alert_id'] for m in case['members']} == member_ids
    assert case['member_count'] == len(member_ids)
    history = [r for p in pages[url+'/history'] for r in p['items']]
    assert {r['run']['id'] for r in history} == {r['id'] for r in rows['runs'] if r['case_id'] == cid}
    case_results.append({'case_id': cid, 'members': case['member_count'], 'runs': len(history),
                         'assessment_freshness': case['current_assessment']['input_freshness']})
current = got[base+'/incidents/'+iid+'/analysis']
assert current['current_pointer_id'] == index['incidents'][iid]['latest_diagnosis_id']
assert current['current']['valid_for_current_input']
summary = {'status': 'passed', 'http_gets': len(got), 'all_http_200': True,
           'snapshot_sha256': mapping['snapshot_sha256'], 'original_contents_read': len(contents),
           'previous_run_and_result_links_read': len(comparison_urls), 'cases': case_results,
           'new_model_calls': 0, 'business_writes': 0, 'model_quality': 'NOT_PASSED', 'whole_change_accepted': False}
if not io.SAVED:
    io.save('http-validation.json', summary)
else:
    assert json.loads((folder/'http-validation.json').read_text()) == summary
print(json.dumps(summary, ensure_ascii=False, indent=2))
