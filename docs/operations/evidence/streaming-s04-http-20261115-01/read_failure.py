"""Read the actual S04 failed update without starting or repairing a task."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SUPPLY = OUT.parent / 'test-streaming-s04-20261115-01'
helper = OUT.parent / 'streaming-ai-http-20261115-01/read_analysis.py'
spec = importlib.util.spec_from_file_location('saved_http_reader', helper)
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)
io.OUT, io.SAVED = OUT, '--verify-saved' in sys.argv


def same(public, saved, label):
    for key, value in public.items():
        if key in saved:
            assert io.norm(value) == io.norm(saved[key]), f'{label}.{key}'


def main():
    preparing = '--prepare' in sys.argv
    if preparing:
        # Verbatim received map: the test owner may later append validation status.
        for name, source in [('supplied-analysis-map-01.json', SUPPLY / 'actual-analysis-map-01.json'),
                             ('supplied-ingress-map-01.json', SUPPLY / 'readback/identity-map.json')]:
            with (OUT / name).open('xb') as stream:
                stream.write(source.read_bytes())
    mapping = json.loads((OUT / 'supplied-analysis-map-01.json').read_text())
    ingress = json.loads((OUT / 'supplied-ingress-map-01.json').read_text())
    pg = SUPPLY / 'analysis-pg-01.json'
    fingerprint = hashlib.sha256(pg.read_bytes()).hexdigest()
    assert fingerprint == mapping['snapshot_sha256'] == '0af1dc0ae2b9b709070459c1d74e669d31a375a36514322dd25276d5ee8e4af3'
    assert mapping['source'] == 'one_real_saved_snapshot' and mapping['new_case_runs'] == 0
    rows = json.loads(pg.read_text())['rows']
    indexed = {table: {r['id']: r for r in rows[table]} for table in
               ('runs', 'artifacts', 'alerts', 'alert_materials', 'cases', 'case_assessments', 'results', 'incidents')}
    profile = json.loads((ROOT / 'deploy/http-service/streaming-20261115-01/profile.json').read_text())
    host = f"http://{profile['bind']}:{profile['port']}"
    base = host + '/api/v1/socai2'
    alert = ingress['A04']
    aurl, iurl = base + '/alerts/' + alert['alert_id'], base + '/incidents/' + alert['incident_id']
    urls = [aurl, aurl + '/materials/' + alert['material_id'], aurl + '/records/sources',
            aurl + '/records/source_artifacts', aurl + '/artifacts/' + alert['artifact_id'],
            aurl + '/records/incidents', iurl, iurl + '/records/members', iurl + '/analysis', iurl + '/analysis-tasks']
    for task in mapping['tasks']:
        urls.append(f"{base}/{task['subject_type']}s/{task['subject_id']}/analysis-tasks/{task['id']}")
    needed = {}
    for run in mapping['runs']:
        prefix = 'alerts' if run['kind'] == 'alert_basic' else 'incidents'
        run['url'] = f"{base}/{prefix}/{run['subject_id']}/analysis/runs/{run['run_id']}"
        urls += [run['url'], run['url'] + '/trace', base + '/analysis-runs/' + run['run_id'] + '/steps',
                 base + '/analysis-runs/' + run['run_id'] + '/artifacts']
        ids = {run['input_artifact_id'], run['policy_artifact_id']}
        for model in run['models']:
            ids.update([model['request_artifact_id'], model['response_artifact_id'], *model['original_artifact_ids']])
        ids.update(a['id'] for a in rows['artifacts'] if a.get('run_id') == run['run_id'] and a['kind'] == 'tool_response')
        needed[run['run_id']] = sorted(ids)
    for case in mapping['baseline_cases']:
        case['url'] = base + '/cases/' + case['case_id']
        urls += [case['url'], case['url'] + '/history', case['url'] + '/analysis-tasks', case['url'] + '/runs/' + case['run_id']]
    plan = {'source': str(SUPPLY.relative_to(ROOT)), 'snapshot_sha256': fingerprint,
            'supplied_map_sha256': hashlib.sha256((OUT / 'supplied-analysis-map-01.json').read_bytes()).hexdigest(),
            'initial_get_urls': urls, 'required_artifact_ids': needed,
            'purpose': 'Actual failure and preserved history; not successful Case follow-up validation',
            'writes': 0, 'database_queries': 0, 'new_model_calls': 0}
    if preparing:
        io.save('plan.json', plan)
        print(json.dumps({'prepared': True, 'initial_gets': len(urls), 'new_run_content_gets': sum(map(len, needed.values()))}))
        return
    assert json.loads((OUT / 'plan.json').read_text()) == plan
    got = io.get_all(urls, 'get-01.json')
    pages = {url: [body] for url, body in got.items() if any(k in body for k in ('next_cursor', 'next_before_run_id', 'next_offset'))}
    page_no = 0
    while True:
        follow = {}
        for url, bodies in pages.items():
            last = bodies[-1]
            for key in ('cursor', 'before_run_id', 'offset'):
                if last.get('next_' + key) is not None:
                    follow[url + '?' + urlencode({key: last['next_' + key]})] = url
        if not follow:
            break
        assert not set(follow) & got.keys(), 'repeated_cursor'
        page_no += 1
        extra = io.get_all(list(follow), f'page-{page_no:02}.json')
        for url, body in extra.items():
            pages[follow[url]].append(body)
        got.update(extra)
    contents = {}
    for run in mapping['runs']:
        directory = {a['id']: a for page in pages[base + '/analysis-runs/' + run['run_id'] + '/artifacts'] for a in page['items']}
        for aid in needed[run['run_id']]:
            url = host + directory[aid]['content_url']
            assert url == run['url'] + '/artifacts/' + aid
            contents[aid] = url
    got.update(io.get_all(list(contents.values()), 'content-01.json'))
    same(got[aurl]['facts'], indexed['alerts'][alert['alert_id']], 'alert')
    material = indexed['alert_materials'][alert['material_id']]
    body = got[aurl + '/materials/' + alert['material_id']]
    assert body['content_json'] == {k: material[k] for k in ('raw_json', 'ocsf_json', 'enrichment')}
    assert body['content_text'] == material['raw_text']
    refs = got[aurl + '/records/sources']
    assert refs['total'] == 1 and refs['items'][0]['source_event_id'] == alert['source_event_id']
    same(refs['items'][0], next(r for r in rows['alert_source_refs'] if r['alert_id'] == alert['alert_id']), 'source')
    artifacts = got[aurl + '/records/source_artifacts']
    assert artifacts['total'] == 1 and artifacts['items'][0]['id'] == alert['artifact_id']
    assert got[aurl + '/artifacts/' + alert['artifact_id']]['content_json'] == indexed['artifacts'][alert['artifact_id']]['content_json']
    assert [r['id'] for r in got[aurl + '/records/incidents']['items']] == [alert['incident_id']]
    same(got[iurl]['facts'], indexed['incidents'][alert['incident_id']], 'incident')
    members = [i for page in pages[iurl + '/records/members'] for i in page['items']]
    assert {m['id'] for m in members} == set(ingress['incident_members']) and len(members) == 4
    assert got[iurl]['derived']['member_count'] == 4
    for task in mapping['tasks']:
        url = f"{base}/{task['subject_type']}s/{task['subject_id']}/analysis-tasks/{task['id']}"
        view = got[url]
        assert view['task_id'] == task['id'] and view['status'] == task['state']
        assert host + view['status_url'] == url
        same(view, task, 'task')
        expected = [a for a in mapping['attempts'] if a['task_id'] == task['id']]
        assert len(view['attempts']) == len(expected)
        for actual, saved in zip(view['attempts'], expected):
            same(actual, saved, 'attempt')
            assert host + actual['run_url'] in got
        if task['state'] == 'skipped':
            assert view['reason_code'] == 'automatic_attempts_stopped'
            assert view['latest_run_id'] is None and view['attempts'] == [] and view['results'] == []
        else:
            assert view['latest_run_id'] == expected[0]['run_id']
            assert all(host + r['url'] in got for r in view['results'])
        assert view['retry_count'] == 0 and view['next_retry_at'] is None
    for run in mapping['runs']:
        rid = run['run_id']
        entry, trace = got[run['url']], got[run['url'] + '/trace']
        same(entry['run'], indexed['runs'][rid], 'run')
        assert entry['run']['state'] == run['state']
        table = 'alert_assessments' if run['kind'] == 'alert_basic' else 'incident_diagnoses'
        saved = next(r for r in rows[table] if r['source_run_id'] == rid)
        same(entry['result'], saved, 'analysis_result')
        assert entry['result']['id'] in run['result_ids']
        for section, table in (('steps', 'run_steps'), ('artifacts', 'artifacts')):
            url = base + '/analysis-runs/' + rid + '/' + section
            items = [item for page in pages[url] for item in page['items']]
            expected = {r['id']: r for r in rows[table] if r.get('run_id') == rid}
            assert {i['id'] for i in items} == set(expected)
            assert len(items) == pages[url][0]['total'] == trace[section + '_total']
            assert host + trace[section + '_url'] == url
            for item in items:
                same(item, expected[item['id']], section)
        if run['kind'] == 'incident_diagnosis':
            assert entry['result']['state'] == 'failed' and entry['result']['error_code'] == 'model_response_not_complete'
            assert all(entry['result'][k] is None for k in ('summary', 'diagnosis', 'generated_at'))
            assert entry['valid_for_current_input'] is False and entry['is_current_pointer'] is False
            assert entry['input_selection']['selected_count'] == 4
            assert entry['analysis_coverage']['state'] == 'unknown'
        else:
            assert entry['valid_for_current_input'] is True and entry['is_current_pointer'] is True
    for aid, url in contents.items():
        read, saved = got[url], indexed['artifacts'][aid]
        assert read['availability'] == 'available'
        same(read['metadata'], saved, 'artifact')
        assert read['content_json'] == saved['content_json'] and read['content_text'] == saved['content_text'], aid
    page = got[iurl + '/analysis']
    assert page['current_pointer_id'] == mapping['I_latest_pointer']
    assert page['current']['result']['id'] == mapping['I_latest_pointer']
    assert page['current']['freshness'] == 'stale' and page['current']['valid_for_current_input'] is False
    assert {entry['run']['id'] for p in pages[iurl + '/analysis'] for entry in p['entries']} == {
        r['id'] for r in rows['runs'] if r['kind'] == 'incident_diagnosis'}
    state = next(s for s in rows['analysis_subject_state'] if s['subject_id'] == alert['incident_id'])
    task_page = got[iurl + '/analysis-tasks']
    assert task_page['update_state']['eligible'] is False
    assert task_page['update_state']['ineligible_reason'] == state['automatic_stop_reason']
    assert {t['task_id'] for p in pages[iurl + '/analysis-tasks'] for t in p['items']} == {
        t['id'] for t in rows['analysis_tasks'] if t['subject_id'] == alert['incident_id']}
    case_checks = []
    for case in mapping['baseline_cases']:
        cid, rid, url = case['case_id'], case['run_id'], case['url']
        detail, run = got[url], got[url + '/runs/' + rid]
        same(detail['case'], indexed['cases'][cid], 'case')
        assert {m['alert_id'] for m in detail['members']} == set(case['member_ids'])
        assert detail['member_count'] == len(case['member_ids']) and detail['baseline_records'] == []
        assert detail['case']['current_assessment_id'] == case['assessment_id']
        same(detail['current_assessment']['value'], indexed['case_assessments'][case['assessment_id']], 'assessment')
        history = [i for p in pages[url + '/history'] for i in p['items']]
        assert len(history) == 1 and history[0]['run']['id'] == rid and history[0]['result']['id'] == case['result_id']
        same(history[0]['result'], indexed['results'][case['result_id']], 'old_result')
        tasks = [i for p in pages[url + '/analysis-tasks'] for i in p['items']]
        assert len(tasks) == 1 and tasks[0]['task_id'] == case['task_id'] and tasks[0]['latest_run_id'] == rid
        assert run['run']['comparison_context'] == case['comparison_context']
        assert run['previous_run_url'] is None and run['comparison_result_url'] is None
        assert run['input_member_count'] == len(case['member_ids'])
        case_checks.append({'case_id': cid, 'member_count': detail['member_count'], 'run_count': len(history),
                            'new_run_count': 0, 'initial_comparison_preserved': True,
                            'current_assessment_freshness': detail['current_assessment']['input_freshness']})
    summary = {'http_failure_readback_passed': True, 'http_gets': len(got), 'all_status_200': True,
               'snapshot_sha256': fingerprint, 'authentication': 'none', 'new_tasks_read': len(mapping['tasks']),
               'new_run_steps_read': sum(len(r['step_ids']) for r in mapping['runs']),
               'new_run_artifact_metadata_read': sum(len(r['artifact_ids']) for r in mapping['runs']),
               'new_run_contents_read': len(contents), 'incident_members': 4, 'new_alert_completed': True,
               'incident_failed': 'model_response_not_complete', 'incident_old_pointer_preserved_but_stale': True,
               'stopped_checks_without_run': 3, 'cases': case_checks, 'new_case_runs': 0,
               'S04_successful_update_accepted': False, 'whole_change_accepted': False,
               'business_writes': 0, 'database_queries': 0, 'new_model_calls': 0}
    if io.SAVED and (OUT / 'result.json').exists():
        assert json.loads((OUT / 'result.json').read_text()) == summary
    else:
        io.save('result.json', summary)
    print(json.dumps({k: summary[k] for k in ('http_failure_readback_passed', 'http_gets', 'new_tasks_read', 'new_run_contents_read', 'new_case_runs')}))


if __name__ == '__main__':
    main()
