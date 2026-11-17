"""Read saved evidence only: Case continuation, failure retention and HTTP contract."""
import copy
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'docs/operations/evidence/acceptance-case-continuation-20261117-01'
OLD = ROOT / 'docs/operations/evidence/acceptance-singlepart-20261117-02'
EX = BASE / 'execution-03'
sys.path[:0] = [str(ROOT / 'tools/testdata'), str(ROOT / 'services/api')]
from acceptance_clients import Http
from acceptance_verify import verify_readback
from app.socai2.case_incident_material import freeze

SEEN = {}


def raw(path):
    body = path.read_bytes()
    SEEN[str(path.relative_to(ROOT))] = hashlib.sha256(body).hexdigest()
    return body


def read(path):
    return json.loads(raw(path))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def same(left, right):
    if isinstance(left, str) and isinstance(right, str):
        try:
            return datetime.fromisoformat(left.replace('Z', '+00:00')) == datetime.fromisoformat(right.replace('Z', '+00:00'))
        except ValueError:
            return left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def preserved(before, after, tables):
    for table in tables:
        current = {r['id']: r for r in after[table]}
        assert all(r['id'] in current and same(r, current[r['id']]) for r in before[table]), table


def main():
    source = read(EX / 'source-before.json')
    assert source == read(EX / 'source-after.json')
    assert all(hashlib.sha256(raw(ROOT / p)).hexdigest() == h for p, h in source.items())
    final, validation = read(BASE / 'final-validation.json'), read(EX / 'validation.json')
    pg, seed, original = read(EX / 'saved-records.json'), read(BASE / 'seed-snapshot.json'), read(BASE / 'source-records.json')
    oldpg = read(OLD / 'readback-02/saved-records.json')
    comparison, seedcheck = read(BASE / 'source-comparison.json'), read(BASE / 'seed-validation.json')
    assert len(comparison['unchanged_tables']) == 16
    assert sum(len(original[t]) for t in comparison['unchanged_tables']) == comparison['rows'] == 46
    preserved(oldpg, original, comparison['unchanged_tables'])
    assert same(read(BASE / 'source-export.json')['rows'], original)
    control = seedcheck['control_incident_id']
    for table in original:
        seeded = [r for r in seed[table] if table != 'incidents' or r['id'] != control]
        assert same(original[table], seeded), table
    assert len(seed['incidents']) == 2 and not seed['results'] and all(r['case_id'] is None for r in seed['runs'])
    assert seedcheck['counts_hashes'] == {t: {'count': len(v), 'sha256': digest(v)} for t, v in seed.items()}
    assert validation['readonly_before'] == validation['readonly_after'] == {
        t: {'count': len(v), 'sha256': digest(v)} for t, v in pg.items()}
    assert len(pg) == 26
    previous = read(BASE / 'execution-02/saved-records.json')
    before_run = read(BASE / 'driver-failure-final-records.json')
    for earlier in (seed, before_run, previous):
        preserved(earlier, pg, set(earlier) - {'cases', 'analysis_subject_state'})

    rid, tid, result_id = final['successful_run_id'], final['successful_task_id'], final['result_id']
    find = lambda table, identity: next(r for r in pg[table] if r['id'] == identity)
    run, task, result = find('runs', rid), find('analysis_tasks', tid), find('results', result_id)
    attempt = next(a for a in pg['analysis_attempts'] if a['task_id'] == tid)
    assert task['state'] == attempt['outcome'] == run['state'] == 'completed'
    assert attempt['run_id'] == result['source_run_id'] == rid and result['case_id'] == run['case_id'] == final['case_id']
    assert (result['validation_state'], result['conclusion_state'], result['delivery_state']) == ('accepted', 'uncertain', 'partial')
    assert result['change_kind'] == 'not_comparable' and result['comparison_result_id'] is None
    assert len(pg['results']) == 1 and len([s for s in pg['run_steps'] if s['run_id'] == rid]) == 17
    assert len([a for a in pg['artifacts'] if a['run_id'] == rid]) == 50
    assert {t: len(pg[t]) for t in final['saved_totals']} == final['saved_totals']
    failures = []
    for identity, outcome in [('56dcc7bb-c77d-4729-9f34-428b976067f2', 'failed'),
                              ('4e3df5da-499b-4592-b9bd-684e7b18e103', 'unknown'),
                              ('bc2f93fe-5f96-4096-8d35-a2dcc611c0d1', 'unknown')]:
        t = find('analysis_tasks', identity)
        a = next(a for a in pg['analysis_attempts'] if a['task_id'] == identity)
        assert t['state'] == 'failed' and a['outcome'] == outcome and a['local_state'] == 'ended'
        assert not any(r['source_run_id'] == a['run_id'] for r in pg['results'])
        failures.append({'task_id': identity, 'task_state': t['state'], 'reason_code': t['reason_code'],
                         'attempt_outcome': a['outcome'], 'run_id': a['run_id'],
                         'run_state': find('runs', a['run_id'])['state'] if a['run_id'] else None})

    http = []
    for path in sorted((EX / 'http').glob('*.json')):
        if path.name.endswith('.intent.json'):
            continue
        item = read(path)
        assert item['outcome'] == 'returned' and item['transport'] == 'ASGITransport'
        body = raw(path.parent / item['response']['body_file'])
        assert hashlib.sha256(body).hexdigest() == item['response']['sha256']
        assert json.loads(body) == item['response']['body']
        http.append(item)
    posts = [r for r in http if r['request']['method'] == 'POST']
    gets = [r for r in http if r['request']['method'] == 'GET']
    assert len(posts) == 1 and len(gets) == 168
    assert posts[0]['response']['status'] == 202 and posts[0]['response']['body']['task_id'] == tid
    assert posts[0]['request']['body']['mode'] == 'rerun'
    operations = [read(p / 'submission-intent.json')['body']['operation_key'] for p in [BASE, BASE / 'execution-02', EX]]
    assert len(set(operations)) == 3 and posts[0]['request']['body']['operation_key'] == operations[-1]

    class SavedHttp:
        pages = Http.pages

        def __init__(self):
            first_page = next(x['request']['path'] for x in gets if 'limit=' in x['request']['path'])
            self.config = SimpleNamespace(page_size=int(re.search(r'limit=(\d+)', first_page)[1]))
            self.sequence = 0

        def request(self, method, path):
            item = gets[self.sequence]
            assert method == 'GET' and path == item['request']['path'] and item['response']['status'] == 200
            self.sequence += 1
            return copy.deepcopy(item['response']['body'])

    reader = SavedHttp()
    with patch('socket.socket', side_effect=AssertionError('offline review only')):
        replay = verify_readback(reader, pg)
    assert reader.sequence == 168 and all(validation[k] == v for k, v in replay.items())
    result_bodies = [r['response']['body']['result'] for r in gets if isinstance(r['response']['body'], dict)
                     and isinstance(r['response']['body'].get('result'), dict)
                     and r['response']['body']['result']['id'] == result_id]
    assert result_bodies
    common_fields = set(result_bodies[0]) & set(result)
    assert all(all(same(body[k], result[k]) for k in common_fields) for body in result_bodies)

    artifacts = {a['id']: a for a in pg['artifacts']}
    context = next(a['content_json'] for a in pg['artifacts'] if a['run_id'] == rid and a['schema_version'] == 'socai2.baseline-context.v1')
    expected_alerts = {r['id'] for r in original['alerts']}
    assert set(context['alerts']) == expected_alerts and set(context['incidents']) == {r['id'] for r in original['incidents']}
    assert control not in context['incidents'] and all(r['incident_id'] != control for r in pg['case_incidents'])
    for iid, inc in context['incidents'].items():
        m = inc['analysis_material']
        candidate = {'run': find('runs', m['source_run_id']), 'task': find('analysis_tasks', m['task_id']),
                     'attempt': find('analysis_attempts', m['attempt_id']), 'input': artifacts[m['input']['id']],
                     'response': artifacts[m['response']['id']], 'receipt': artifacts[m['receipt_source']['id']],
                     'originals': [artifacts[r['id']] for r in m['originals']]}
        with patch('socket.socket', side_effect=AssertionError('offline review only')):
            restored, reasons = freeze(iid, candidate, sorted(expected_alerts))
        assert restored == m and not reasons
    manifest = artifacts[run['input_artifact_id']]['content_json']
    assert manifest['comparison_context'] == final['comparison_context']
    previous_id = manifest['comparison_context']['previous_run_id']
    assert find('runs', previous_id)['state'] == 'unknown' and not any(r['source_run_id'] == previous_id for r in pg['results'])

    queries = {a['content_json']['tool_name']: a['content_json'] for a in pg['artifacts']
               if a['run_id'] == rid and a['kind'] == 'tool_response'}
    authentication, network = queries['authentication_activity'], queries['network_connections']
    assert authentication['state'] == network['state'] == 'completed'
    assert len(authentication['rows']) == 2 and network['rows'] == []
    lake = read(OLD / 'runs/part1/context-readback.json')
    assert {r['event_id'] for r in authentication['rows']} == {r['event_id'] for r in lake['rows']}
    for row in authentication['rows']:
        saved = next(r for r in lake['rows'] if r['event_id'] == row['event_id'])
        assert json.loads(row['ocsf_json']) == saved['ocsf_json']

    index = read(EX / 'model-io/index.json')
    assert len(index['requests']) == 6
    calls, bodies = {}, {}
    for item in index['requests']:
        for name, checksum in item['files'].items():
            assert hashlib.sha256(raw(EX / 'model-io' / name)).hexdigest() == checksum
        folder = (EX / 'model-io' / next(iter(item['files']))).parent
        request, response = read(folder / 'request.json'), read(folder / 'response.json')
        ra, oa = read(folder / 'request-artifact.json'), read(folder / 'original-artifact.json')
        assert same(ra, artifacts[item['request_artifact_id']]) and same(oa, artifacts[item['original_artifact_id']])
        payload = ra['content_json'].get('payload', ra['content_json'])
        assert payload['body'] == request and oa['content_json']['raw'] == response
        assert item['usage'] == response['usage'] and item['finish_reason'] == response['choices'][0]['finish_reason'] == 'stop'
        if item['stage'] in {'C3', 'C6'}:
            messages = json.dumps(request['messages'], ensure_ascii=False)
            assert not any(m in messages for m in ['tenant_uid', 'batch_id', 'scenario_id', 'expected_verdict', BASE.name])
            calls.setdefault(item['run_id'], []).append(item['usage']['total_tokens'])
            bodies[(item['run_id'], item['stage'])] = response
    assert sorted(calls) == sorted([rid, previous_id]) and all(len(v) == 2 for v in calls.values())
    assert sum(calls[rid]) == 23539 and sum(calls[previous_id]) == 16059 and sum(map(sum, calls.values())) == 39598
    register = read(BASE / 'quality-register.json')
    detail = next(a['content_json'] for a in pg['artifacts'] if a['run_id'] == rid
                  and a['content_json'] and a['content_json'].get('type') == 'delivery_report')
    assert detail['citation_review']['issues'] == register['program_issues'] and len(register['program_issues']) == 5
    manual = register['manual_observations'][0]
    assert manual['model_claim'] in bodies[(rid, 'C6')]['choices'][0]['message']['content']
    history = find('run_steps', manual['actual_step_id'])
    assert history['state'] == 'skipped' and history['error']['code'] == manual['actual_reason']

    dispatch = read(EX / 'dispatcher-final.json')
    assert dispatch == {'active': 0, 'unconfirmed_receipts': 0, 'redis_running': 0, 'peak_active': 1}
    cleanup = read(BASE / 'cleanup.json')
    assert cleanup['dispatch_active'] == cleanup['redis_running'] == 0 and len(cleanup['released_forward_ports']) == 3
    services = read(BASE / 'services-after.json')['services']
    oldservices = read(OLD / 'services-before.json')
    assert {r['name']: r for r in oldservices.values()} == services
    fix = read(BASE / 'core-fix-scope.json')
    assert hashlib.sha256(raw(ROOT / fix['source'])).hexdigest() == fix['sha256']
    static_before, static_check = read(BASE / 'static-before.json'), read(BASE / 'static-verification.json')
    site = ROOT / 'deliverables/investigation-validation-20261106/processing-audit'
    html = raw(site / 'index.html').decode()
    current = {r['id']: r for r in json.loads(re.search(r'<script type="application/json" id="audit-records">(.*?)</script>', html, re.S)[1])}
    assert len(static_before['records']) == 50 and len(current) == 51
    assert all(current[k] == v for k, v in static_before['records'].items())
    assert current[static_check['new_record']['id']] == static_check['new_record']
    for name, checksum in static_before['page_hashes'].items():
        assert hashlib.sha256(raw(site / name)).hexdigest() == checksum
    for path, checksum in SEEN.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == checksum
    report = {'status': 'local_case_execution_save_readback_passed', 'scope': 'independent_saved_actual_evidence_review',
              'source_files': len(source), 'source_unchanged': True, 'core_fix_unchanged_from_previous_review': True,
              'source_rows': 46, 'source_comparison_tables': 16, 'case_id': final['case_id'], 'task_id': tid,
              'run_id': rid, 'result_id': result_id, 'task_state': 'completed', 'attempt_outcome': 'completed',
              'run_state': 'completed', 'validation_state': 'accepted', 'conclusion_state': 'uncertain', 'delivery_state': 'partial',
              'successful_run_steps': 17, 'successful_run_artifacts': 50, 'actual_saved_http_gets_replayed': 168,
              'actual_saved_http_post_receipts': 1, 'result_common_fields_compared': sorted(common_fields),
              'readonly_tables': 26, 'prior_rows_and_failure_artifacts_unchanged': True, 'retained_failures': failures,
              'comparison_context': manifest['comparison_context'], 'control_incident_excluded': True,
              'authentication_original_rows_equal': 2, 'network_rows': 0, 'new_model_calls_in_batch': 4,
              'new_tokens_in_batch': 39598, 'successful_run_model_calls': 2, 'successful_run_tokens': 23539,
              'copied_ai_calls_excluded': 2, 'finish_reasons': ['stop'] * 4, 'program_quality_issues': 5,
              'manual_quality_issues': 1, 'model_quality': 'NOT_PASSED; deferred; prose not fully evaluated',
              'dispatcher': dispatch, 'cleanup_evidence_reviewed': True, 'static_records': {'before': 50, 'after': 51, 'old_preserved': True},
              'active_21_service_identities_unchanged': True, 'actual_21_case_restored': False,
              'new_21_tcp_or_4177_verified': False, 'task3b_21_chain_complete': False,
              'task3c_complete': False, 'task3d_complete': False, 'task4_complete': False, 'change_complete': False,
              'reviewer_new_service_connections': 0, 'reviewer_new_business_writes': 0, 'reviewer_new_model_calls': 0,
              'review_limits': 'Saved real ASGI/PG/model/lake and cleanup receipts independently checked; no new service query or browser run.',
              'evidence_manifest': 'evidence-hashes-01.json'}
    with (HERE / 'evidence-hashes-01.json').open('x') as f:
        json.dump(SEEN, f, ensure_ascii=False, indent=2)
    with (HERE / 'independent-review-01.json').open('x') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print('Independent review passed for local C1 -> Case execution -> Result save/readback; original failures preserved; quality NOT_PASSED; 21 restoration pending.')


if __name__ == '__main__':
    main()
