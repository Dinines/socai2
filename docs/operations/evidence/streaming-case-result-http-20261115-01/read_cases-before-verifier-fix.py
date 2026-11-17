"""Read only the two actual S01 Case Runs supplied by the test owner."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SUPPLY = ROOT / 'docs/operations/evidence/test-streaming-case-initial-20261115-01'
helper = OUT.parent / 'streaming-ai-http-20261115-01/read_analysis.py'
spec = importlib.util.spec_from_file_location('saved_http_reader', helper)
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)
io.OUT = OUT
io.SAVED = '--verify-saved' in sys.argv


def same(public, saved, label):
    for key, value in public.items():
        if key in saved:
            assert io.norm(value) == io.norm(saved[key]), f'{label}.{key}'


def main():
    pg = SUPPLY / 'case-pg-01.json'
    fingerprint = hashlib.sha256(pg.read_bytes()).hexdigest()
    assert fingerprint == 'a30c69fadd2241d96e393bd6be48591dca37231157e808660c0c09e7d1b5421e'
    validation = json.loads((SUPPLY / 'case-validation-01.json').read_text())
    assert validation['status'] == 'passed' and validation['snapshot_sha256'] == fingerprint
    mapping = json.loads((SUPPLY / 'actual-case-run-map-01.json').read_text())
    assert mapping['source'] == 'real_postgres_snapshot'
    cases = mapping['cases']
    rows = json.loads(pg.read_text())['rows']
    indexed = {table: {row['id']: row for row in rows[table]}
               for table in ('cases', 'runs', 'results', 'artifacts', 'analysis_tasks', 'case_assessments')}
    profile = json.loads((ROOT / 'deploy/http-service/streaming-20261115-01/profile.json').read_text())
    host = f"http://{profile['bind']}:{profile['port']}"
    base = host + '/api/v1/socai2'
    urls = []
    wanted = {}
    for case in cases:
        cid, rid = case['case_id'], case['run_id']
        case['url'] = f'{base}/cases/{cid}'
        case['run_url'] = case['url'] + '/runs/' + rid
        urls += [case['url'], case['url'] + '/analysis-tasks/' + case['task_id'],
                 case['run_url'], case['url'] + '/results/' + case['result_id'],
                 case['url'] + '/history', base + '/analysis-runs/' + rid + '/steps',
                 base + '/analysis-runs/' + rid + '/artifacts']
        needed = {case[key] for key in ('C1_artifact_id', 'input_artifact_id', 'report_artifact_id', 'graph_artifact_id')}
        for step in rows['run_steps']:
            if step['run_id'] != rid:
                continue
            if step['kind'] == 'model' or step['stage_code'] == 'C4.query' or step['name'] == 'knowledge':
                needed.update([step['input_artifact_id'], step['output_artifact_id']])
            if step['kind'] == 'stage' and step['stage_code'] in {'C2', 'C3', 'C4.routing', 'C6'}:
                needed.add(step['output_artifact_id'])
        for artifact in rows['artifacts']:
            body = artifact.get('content_json') or {}
            if artifact.get('run_id') == rid and (body.get('type') in {'model_original_response', 'delivery_report'}
                    or artifact.get('schema_version') == 'socai2.runtime-policy.v1'):
                needed.add(artifact['id'])
        assert needed <= set(case['artifact_ids'])
        wanted[rid] = sorted(needed)
    supplied = ('case-pg-01.json', 'actual-case-run-map-01.json', 'case-validation-01.json',
                'case-model-usage-01.json', 'case-log-queries-01.json')
    plan = {'purpose': 'Two completed S01 Case Runs: persisted result, exact scope, knowledge, C4, model originals and initial comparison.',
            'base_url': base, 'initial_get_urls': urls, 'required_artifact_ids': wanted,
            'supplied_sha256': {name: hashlib.sha256((SUPPLY / name).read_bytes()).hexdigest() for name in supplied},
            'http_helper_sha256': hashlib.sha256(helper.read_bytes()).hexdigest(),
            'business_writes': 0, 'database_queries': 0, 'new_model_calls': 0}
    if '--prepare' in sys.argv:
        io.save('plan.json', plan)
        print(json.dumps({'prepared': True, 'initial_gets': len(urls), 'artifact_gets': sum(map(len, wanted.values()))}))
        return
    assert json.loads((OUT / 'plan.json').read_text()) == plan
    got = io.get_all(urls, 'get-01.json')
    pages = {url: [body] for url, body in got.items() if 'next_cursor' in body}
    page_no = 0
    while True:
        follow = {url + '?' + urlencode({'cursor': bodies[-1]['next_cursor']}): url
                  for url, bodies in pages.items() if bodies[-1].get('next_cursor') is not None}
        if not follow:
            break
        assert not set(follow) & got.keys(), 'repeated_cursor'
        page_no += 1
        extra = io.get_all(list(follow), f'page-{page_no:02}.json')
        for url, body in extra.items():
            pages[follow[url]].append(body)
        got.update(extra)
    contents = {}
    for case in cases:
        rid = case['run_id']
        directory = {a['id']: a for page in pages[base + '/analysis-runs/' + rid + '/artifacts'] for a in page['items']}
        for aid in wanted[rid]:
            url = host + directory[aid]['content_url']
            assert urlsplit(url).netloc == urlsplit(host).netloc
            assert url == case['run_url'] + '/artifacts/' + aid
            contents[aid] = url
    got.update(io.get_all(list(contents.values()), 'content-01.json'))
    checked = []
    for case in cases:
        cid, rid = case['case_id'], case['run_id']
        members = set(case['member_ids'])
        detail, run = got[case['url']], got[case['run_url']]
        result = got[case['url'] + '/results/' + case['result_id']]
        task = got[case['url'] + '/analysis-tasks/' + case['task_id']]
        same(detail['case'], indexed['cases'][cid], 'case')
        assert {m['alert_id'] for m in detail['members']} == members
        assert detail['member_count'] == len(members) and not detail['members_truncated']
        assert detail['case']['current_assessment_id'] == case['assessment_id']
        same(detail['current_assessment']['value'], indexed['case_assessments'][case['assessment_id']], 'assessment')
        assert detail['baseline_records'] == []
        assert task['status'] == 'completed' and task['latest_run_id'] == rid and len(task['attempts']) == 1
        same(task, indexed['analysis_tasks'][case['task_id']], 'task')
        saved_attempt = next(a for a in rows['analysis_attempts'] if a['id'] == case['attempt_id'])
        same(task['attempts'][0], saved_attempt, 'attempt')
        assert host + task['attempts'][0]['run_url'] == case['run_url']
        assert [r['id'] for r in task['results']] == [case['result_id']]
        assert host + task['results'][0]['url'] == case['url'] + '/results/' + case['result_id']
        same(run['run'], indexed['runs'][rid], 'run')
        assert run['run']['state'] == 'completed' and run['result_ids'] == [case['result_id']]
        assert run['input_member_count'] == len(members) and {m['alert_id'] for m in run['members']} == members
        same(result['result'], indexed['results'][case['result_id']], 'result')
        same(result['run'], indexed['runs'][rid], 'result.run')
        assert result['member_count'] == len(members) and {m['alert_id'] for m in result['members']} == members
        for obj, key in ((run, 'run'), (result, 'result')):
            assert obj[key]['comparison_context'] == case['comparison_context']
            assert obj['previous_run_url'] is None and obj['comparison_result_url'] is None
        assert {result['result'][key] for key in ('validation_state', 'conclusion_state', 'delivery_state')} == {'accepted', 'uncertain', 'partial'}
        history = [i for page in pages[case['url'] + '/history'] for i in page['items']]
        assert len(history) == 1 and history[0]['run']['id'] == rid and history[0]['result']['id'] == case['result_id']
        for section, table in (('steps', 'run_steps'), ('artifacts', 'artifacts')):
            link = base + '/analysis-runs/' + rid + '/' + section
            assert host + run[section + '_url'] == link
            actual = [i for page in pages[link] for i in page['items']]
            expected = {r['id']: r for r in rows[table] if r.get('run_id') == rid}
            assert {r['id'] for r in actual} == set(expected) == set(case['step_ids' if section == 'steps' else 'artifact_ids'])
            assert len(actual) == run[section + '_total']
            for item in actual:
                same(item, expected[item['id']], section)
        for aid in wanted[rid]:
            read = got[contents[aid]]
            saved = indexed['artifacts'][aid]
            assert read['availability'] == 'available'
            same(read['artifact'], saved, 'artifact')
            assert read['content_json'] == saved['content_json'], 'json body differs:' + aid
            assert read['content_text'] == saved['content_text'], 'text body differs:' + aid
        c1 = got[contents[case['C1_artifact_id']]]['content_json']
        assert set(c1['scope']['alert_ids']) == members
        assert c1['update_context']['comparison_context'] == case['comparison_context']
        incident = next(iter(c1['incidents'].values()))
        scope = incident['diagnosis_scope']
        assert scope['input_selection']['selected_count'] == 3 and len(scope['analysis_coverage']['covered_alert_ids']) == 3
        assert set(scope['case_selected_alert_ids']) == set(scope['case_covered_alert_ids']) == members
        assert incident['linked_from_case'] is (len(members) == 3)
        if len(members) == 1:
            assert 'diagnosis_scope_extends_beyond_case' in incident['limitations']
        selected = [s for s in rows['run_steps'] if s['run_id'] == rid]
        knowledge_step = next(s for s in selected if s['name'] == 'knowledge')
        knowledge = got[contents[knowledge_step['output_artifact_id']]]['content_json']
        assert len(knowledge['rows']) == (4 if len(members) == 3 else 2)
        c4 = [s for s in selected if s['stage_code'] == 'C4.query']
        tools = []
        for step in c4:
            request = got[contents[step['input_artifact_id']]]['content_json']
            response = got[contents[step['output_artifact_id']]]['content_json']
            tools.append(request['tool_name'])
            assert response['tool_name'] == request['tool_name']
        assert sorted(tools) == sorted(case['C4_selected_tools'])
        checked.append({'case_id': cid, 'run_id': rid, 'result_id': case['result_id'], 'member_count': len(members),
                        'execution': 'completed', 'validation': 'accepted', 'conclusion': 'uncertain', 'delivery': 'partial',
                        'source_incident_coverage': 3, 'case_coverage_intersection': len(members),
                        'knowledge_rows': len(knowledge['rows']), 'C4_tools': tools, 'comparison': 'initial'})
    summary = {'status': 'passed', 'http_gets': len(got), 'business_writes': 0, 'database_queries': 0, 'new_model_calls': 0,
               'authentication': 'none', 'snapshot_sha256': fingerprint, 'cases': checked,
               'steps_read': sum(len(c['step_ids']) for c in cases), 'artifact_metadata_read': sum(len(c['artifact_ids']) for c in cases),
               'artifact_contents_read': len(contents), 'literal_content_matches_saved_snapshot': True,
               'model_quality_passed': False, 'complete_change_accepted': False}
    if io.SAVED and (OUT / 'result.json').exists():
        assert json.loads((OUT / 'result.json').read_text()) == summary
    else:
        io.save('result.json', summary)
    print(json.dumps({k:summary[k] for k in ('status', 'http_gets', 'steps_read', 'artifact_metadata_read', 'artifact_contents_read')}))


if __name__ == '__main__':
    main()
