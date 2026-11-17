"""Independent offline review of actual append02; no clients or business execution."""
import copy
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'docs/operations/evidence/acceptance-append-20261117-02'
sys.path.insert(0, str(ROOT / 'tools/testdata'))
from acceptance_status import session_status
from acceptance_verify import verify_readback

READ = {}


def raw(path):
    value = path.read_bytes()
    READ[str(path.relative_to(ROOT))] = hashlib.sha256(value).hexdigest()
    return value


def load(path):
    return json.loads(raw(path))


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert json.loads((HERE / name).read_text()) == value


class SavedHttp:
    def __init__(self, directory):
        self.records, self.used = [], set()
        for path in sorted(directory.glob('*.json')):
            if path.name.endswith('.intent.json'):
                continue
            item = load(path)
            assert item['outcome'] == 'returned'
            request, response = item['request'], item['response']
            assert response['status'] in ({200} if request['method'] == 'GET' else {201, 202})
            body_file = response['body_file']
            assert Path(body_file).name == body_file
            body = raw(directory / body_file)
            assert hashlib.sha256(body).hexdigest() == response['sha256']
            assert json.loads(body) == response['body']
            if request['method'] == 'POST':
                intent = load(path.with_name(path.stem + '.intent.json'))
                assert intent['request'] == request
            else:
                assert request['method'] == 'GET'
            self.records.append((path, item))

    def request(self, method, path):
        assert method == 'GET'
        matches = [(p, r) for p, r in self.records if r['request']['method'] == method and r['request']['path'] == path]
        assert matches, path
        source, value = matches[-1]
        self.used.add(str(source.relative_to(SOURCE)))
        return copy.deepcopy(value['response']['body'])

    def pages(self, path, params=None):
        result, seen, cursor = [], set(), None
        while True:
            candidates = []
            for source, record in self.records:
                if record['request']['method'] != 'GET':
                    continue
                url = urlsplit(record['request']['path'])
                query = parse_qs(url.query)
                if url.path == path and query.get('cursor', [None])[0] == cursor and all(
                        query.get(k) == [str(v)] for k, v in (params or {}).items()):
                    candidates.append((source, record))
            assert candidates, (path, params, cursor)
            source, record = candidates[-1]
            self.used.add(str(source.relative_to(SOURCE)))
            page = record['response']['body']
            result.extend(copy.deepcopy(page['items']))
            cursor = page['next_cursor']
            if not cursor:
                assert len(result) == page['total']
                return result
            assert cursor not in seen
            seen.add(cursor)


def main():
    prepared = SOURCE / 'prepared'
    summary = load(SOURCE / 'final-validation.json')
    session = load(prepared / 'session.json')
    frozen = load(SOURCE / 'source-freeze-final.json')
    runtime = load(SOURCE / 'source-freeze-02.json')
    prior_review = load(HERE / 'reviewed-source-03.json')
    assert frozen['files'] == prior_review['files']
    for name, expected in frozen['files'].items():
        assert hashlib.sha256(raw(ROOT / name)).hexdigest() == expected
    changes = [p for p, h in runtime['files'].items() if frozen['files'][p] != h]
    assert set(changes) == {'tools/testdata/acceptance_append.py', 'tools/testdata/tests/test_acceptance_append.py'}
    first_hashes = load(SOURCE / 'first-part-sha256-before-append.json')
    first_dir = prepared / 'runs/part1'
    assert set(first_hashes) == {str(p.relative_to(first_dir)) for p in first_dir.rglob('*') if p.is_file()}
    for name, expected in first_hashes.items():
        assert hashlib.sha256(raw(first_dir / name)).hexdigest() == expected
    assert len(first_hashes) == 1037
    states, snapshots, readers, part_checks = [], [], [], []
    for part in ('part1', 'part2'):
        folder = prepared / 'runs' / part
        state, rows = load(folder / 'state.json'), load(folder / 'saved-records.json')
        states.append(state)
        snapshots.append(rows)
        assert state['execution_id'] == session['execution']['execution_id'] == summary['execution_id']
        assert state['session_sha256'] == hashlib.sha256(raw(prepared / 'session.json')).hexdigest()
        assert state['status'] == 'completed' and state['execution_issues'] == [] and rows['readonly'] is True
        rb = load(folder / 'readback.json')
        assert rb == state['readback'] and rb['status'] == 'passed' and not rb['missing_originals']
        plan = next(p for p in session['plan']['parts'] if p['id'] == part)
        assert state['sent'] == {'alerts': len(plan['files']['alerts']), 'context': len(plan['files']['context'])}
        for role in ('alerts', 'context'):
            for material in plan['files'][role]:
                receipt = load(folder / ('send-' + material.replace('/', '-')))
                assert receipt['status'] == 'accepted_only' and receipt['accepted'] == receipt['requested'] == 1
                assert receipt['not_attempted'] == 0 and receipt['cleanup_errors'] == []
                assert receipt['tenant_id'] == session['profile']['tenant_id']
                assert len(receipt['records']) == 1
                record = receipt['records'][0]
                assert record['wire_sha256'] == session['wire_sha256'][material]
                assert hashlib.sha256(raw(prepared / 'wire' / material)).hexdigest() == record['wire_sha256']
                assert record['state'] == 'accepted_not_processed' and record['message']['topic'] == receipt['topic']
        context = load(folder / 'context-readback.json')
        assert context['status'] == 'passed' and len(context['rows']) == len(plan['files']['context'])
        expected_context = {session['identities'][m]['event_id']: load(prepared / 'wire' / m)['ocsf_event']
                            for m in plan['files']['context']}
        for row in context['rows']:
            original = expected_context[row['event_id']]
            assert row['tenant_id'] == session['profile']['tenant_id']
            assert all(row['ocsf_json'].get(k) == v for k, v in original.items())
        stage_times = [(s['stage'], stamp(s['at'])) for s in state['steps']]
        assert all(a[1] <= b[1] for a, b in zip(stage_times, stage_times[1:]))
        new_ids = {session['identities'][m]['predicted_canonical_alert_id'] for m in plan['files']['alerts']}
        for aid in new_ids:
            task = next(t for t in rows['analysis_tasks'] if t['subject_type'] == 'alert' and t['subject_id'] == aid)
            assert task['state'] == 'completed' and stamp(task['submitted_at']) >= stamp(context['observed_at'])
            assert stamp(task['ended_at']) <= dict(stage_times)['alerts_publish_and_triage']
        http = SavedHttp(folder / 'http')
        readers.append(http)
        verified = verify_readback(http, rows)
        assert verified == rb
        posts = [r for _, r in http.records if r['request']['method'] == 'POST']
        assert len(posts) == 3
        expected_case_ids = {cid for ids in state['cases'].values() for cid in ids}
        if part == 'part2':
            assert all(r['request']['path'] != '/api/v1/socai2/cases' for r in posts)
            actual = {r['request']['path'].split('/')[5] for r in posts if r['request']['path'].endswith('/investigations')}
            assert actual == expected_case_ids
            assert all(r['request']['body']['mode'] == 'check' for r in posts)
        part_checks.append({'part': part, 'sent': state['sent'], 'http_gets': sum(r['request']['method'] == 'GET' for _, r in http.records),
                            'http_posts': len(posts), 'saved_http_used_for_readback': len(http.used), 'readback': 'passed'})
    first, final = snapshots
    immutable = ('alert_materials', 'alert_source_refs', 'analysis_tasks', 'analysis_attempts', 'runs', 'results',
                 'run_members', 'run_steps', 'artifacts', 'alert_assessments', 'incident_diagnoses')
    for table in immutable:
        current = {r['id']: r for r in final[table]}
        assert all(current.get(r['id']) == r for r in first[table]), table
    live = load(SOURCE / 'final-records.json')
    assert {k: live[k] for k in final} == final
    assert {k: len(v) for k, v in final.items() if isinstance(v, list)} == summary['counts']
    assert len(live['case_incidents']) == 1
    before_records = load(prepared / 'runs/part2/before-records.json')
    assert before_records == first
    assert states[0]['cases'] == states[1]['cases'] and states[0]['incidents'] == states[1]['incidents']
    for source in states[1]['previous_receipts']:
        assert hashlib.sha256(raw(prepared / source['path'])).hexdigest() == source['sha256']
    runs = {r['id']: r for r in final['runs']}
    results = {r['id']: r for r in final['results']}
    artifacts = {r['id']: r for r in final['artifacts']}
    case_checks = []
    for case in session['plan']['scenario']['cases']:
        cid, = states[0]['cases'][case['key']]
        old_run, = [r for r in first['runs'] if r['case_id'] == cid]
        new_run, = [r for r in final['runs'] if r['case_id'] == cid and r['id'] != old_run['id']]
        old_result, = [r for r in first['results'] if r['case_id'] == cid]
        new_result, = [r for r in final['results'] if r['case_id'] == cid and r['id'] != old_result['id']]
        old_members = {m['alert_id'] for m in first['run_members'] if m['run_id'] == old_run['id']}
        members = {m['alert_id'] for m in final['run_members'] if m['run_id'] == new_run['id']}
        current = {m['alert_id'] for m in final['case_alerts'] if m['case_id'] == cid}
        assert members == current and len(old_members) == 1
        assert members > old_members and len(members) == 2 if case['scope'] == 'incident' else members == old_members
        assert new_result['source_run_id'] == new_run['id'] and new_result['comparison_result_id'] == old_result['id']
        assert new_run['comparison_result_id'] == old_result['id']
        manifest = artifacts[new_run['input_artifact_id']]['content_json']
        assert manifest['comparison_context']['previous_run_id'] == old_run['id']
        assert manifest['comparison_context']['comparison_result_id'] == old_result['id']
        result_members = {m['alert_id'] for m in live['result_members'] if m['result_id'] == new_result['id']}
        assert result_members == members
        case_checks.append({'key': case['key'], 'case_id': cid, 'member_counts': [len(old_members), len(members)],
                            'run_ids': [old_run['id'], new_run['id']], 'result_ids': [old_result['id'], new_result['id']],
                            'comparison': 'same-case previous result', 'second_task_source': next(t['source'] for t in final['analysis_tasks']
                                if t['id'] == next(a['task_id'] for a in final['analysis_attempts'] if a['run_id'] == new_run['id']))})
    for result in final['results']:
        assert (result['validation_state'], result['conclusion_state'], result['delivery_state']) == ('accepted', 'uncertain', 'partial')
    task_map = {t['id']: t for t in final['analysis_tasks']}
    assert all(t['state'] in {'completed', 'skipped'} and t['ended_at'] for t in task_map.values())
    moments = []
    for attempt in final['analysis_attempts']:
        task = task_map[attempt['task_id']]
        assert (task['subject_type'], task['subject_id']) == (attempt['subject_type'], attempt['subject_id'])
        assert runs[attempt['run_id']][attempt['subject_type'] + '_id'] == attempt['subject_id']
        assert attempt['local_state'] == 'ended' and attempt['outcome'] == 'completed'
        moments += [(stamp(attempt['started_at']), 1), (stamp(attempt['local_ended_at']), -1)]
    active = peak = 0
    for _, delta in sorted(moments):
        active += delta
        peak = max(peak, active)
    assert active == 0 and peak == 1
    skipped, = [t for t in task_map.values() if t['state'] == 'skipped']
    assert skipped['reason_code'] == 'no_changes' and not any(a['task_id'] == skipped['id'] for a in final['analysis_attempts'])
    connection = load(SOURCE / 'post-implementation-readback/connection-binding.json')
    for part in ('part1', 'part2'):
        preflight = load(prepared / 'runs' / part / 'preflight.json')
        assert preflight['connection_sha256'] == connection['connection_sha256']
    assert set(connection['connection_sha256']) == {'http', 'kafka', 'postgres', 'lake'}
    assert connection['status'] == 'passed' and all(connection[k] == 0 for k in ('new_publications', 'new_business_writes', 'new_model_calls'))
    post_http = SavedHttp(SOURCE / 'post-implementation-readback/http')
    assert all(r['request']['method'] == 'GET' for _, r in post_http.records)
    index = load(SOURCE / 'model-io/index.json')
    assert index['source_snapshot_sha256'] == hashlib.sha256(raw(SOURCE / 'final-records.json')).hexdigest()
    assert index['new_model_calls'] == 0 and index['cost'] == 'unknown'
    request_ids, usage = set(), 0
    stages = Counter()
    for item in index['requests']:
        for name, expected in item['files'].items():
            assert hashlib.sha256(raw(SOURCE / 'model-io' / name)).hexdigest() == expected
        directory = SOURCE / 'model-io' / next(iter(item['files'])).split('/')[0]
        request_artifact = artifacts[item['request_artifact_id']]
        original_artifact = artifacts[item['original_artifact_id']]
        assert load(directory / 'request-artifact.json') == request_artifact
        assert load(directory / 'original-artifact.json') == original_artifact
        body, response = load(directory / 'request.json'), load(directory / 'response.json')
        assert body == request_artifact['content_json']['body']
        assert response == original_artifact['content_json']['raw']
        assert original_artifact['content_json']['request_artifact_id'] == item['request_artifact_id']
        assert request_artifact['run_id'] == original_artifact['run_id'] == item['run_id']
        assert item['request_artifact_id'] not in request_ids
        request_ids.add(item['request_artifact_id'])
        assert item['finish_reason'] == response['choices'][0]['finish_reason'] == 'stop'
        assert item['usage'] == response['usage'] and item['state'] == 'received_original'
        assert not item['input_observations']
        prompt = json.dumps(body, ensure_ascii=False)
        assert all(token not in prompt for token in ('tenant_uid', 'is_test', 'expected_verdict', summary['execution_id'], session['profile']['tenant_id']))
        usage += response['usage']['total_tokens']
        stages[item['stage']] += 1
    assert len(request_ids) == index['request_count'] == index['received_original_count'] == summary['model_requests'] == 13
    assert usage == summary['total_tokens'] == 109995 and index['usage_unknown_requests'] == 0
    diagnostics = load(SOURCE / 'retained-diagnostics.json')
    assert diagnostics['model_quality'] == summary['model_quality'] == 'not_fully_evaluated'
    for record in diagnostics['artifacts']:
        artifact = artifacts[record['artifact_id']]
        assert artifact['run_id'] == record['run_id']
        assert record['details'] == {k: artifact['content_json'][k] for k in record['details']}
    assert diagnostics['recorded_step_issues'] == states[1]['readback']['recorded_step_issues']
    after_first, last_status = load(SOURCE / 'status-after-part1.json'), load(SOURCE / 'status-final.json')
    assert after_first['state'] == 'waiting_append' and after_first['next_part'] == 'part2'
    observed = session_status(prepared)
    assert observed['state'] == last_status['state'] == 'all_parts_completed' and observed['next_part'] is None
    assert not observed['blocking_issues'] and not observed['live_state_verified'] and not any(observed['this_command'].values())
    assert observed['parts'] == last_status['parts'] and observed['sources'] == last_status['sources']
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == h for name, h in READ.items())
    save('actual-evidence-hashes-04.json', READ)
    result = {'scope': 'Independent offline review of actual local append02; closeout evidence tracked separately',
              'status': 'actual_two_part_case_save_readback_passed', 'execution_id': summary['execution_id'],
              'runtime_source': 'acceptance-append-20261117-02/source-freeze-02.json',
              'final_source': 'acceptance-append-20261117-02/source-freeze-final.json',
              'post_runtime_change': changes, 'runtime_and_later_guard_separated': True,
              'parts': part_checks, 'counts': summary['counts'], 'cases': case_checks,
              'old_part_files_unchanged': len(first_hashes), 'old_frozen_records_unchanged': True,
              'saved_vs_later_live_snapshot': 'identical for all shared tables',
              'actual_attempt_concurrency_peak': peak, 'active_attempts_at_end': active,
              'actual_model_calls': len(request_ids), 'actual_model_stages': dict(stages), 'actual_tokens': usage,
              'actual_finish_reasons': {'stop': 13}, 'model_quality': 'not_fully_evaluated', 'cost': 'unknown',
              'diagnostic_artifact_count': len(diagnostics['artifacts']),
              'recorded_step_issue_count': len(diagnostics['recorded_step_issues']),
              'current_configuration_binding': 'saved actual four-config digests identical; post-run live check saved',
              'reviewer_network_calls': 0, 'reviewer_business_writes': 0, 'reviewer_model_calls': 0,
              'evidence_files_hashed': len(READ), 'all_read_files_unchanged': True,
              'not_verified': ['21 deployment', '3c.3', '3d', 'task4', 'model prose quality', 'natural scheduling intervals']}
    save('actual-review-04.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'counts', 'cases', 'actual_model_calls', 'actual_tokens', 'evidence_files_hashed')}, ensure_ascii=False))


if __name__ == '__main__':
    with patch('socket.socket', side_effect=AssertionError('offline evidence review only')):
        main()
