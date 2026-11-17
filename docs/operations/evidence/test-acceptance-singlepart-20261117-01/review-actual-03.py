"""Independently check saved actual execution 02 and isolated C1 repair evidence."""
import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'docs/operations/evidence/acceptance-singlepart-20261117-02'
sys.path[:0] = [str(ROOT / 'tools/testdata'), str(ROOT / 'services/api')]
from acceptance_clients import Http
from acceptance_run import event_milliseconds
from acceptance_verify import verify_readback
from alert_scenarios import json_bytes
from app.socai2.case_incident_material import freeze, source_sql

SEEN = {}


def raw(path):
    body = path.read_bytes()
    SEEN[str(path.relative_to(ROOT))] = hashlib.sha256(body).hexdigest()
    return body


def read(path):
    return json.loads(raw(path))


def receipts(folder):
    values = []
    for path in sorted(folder.glob('*.json')):
        if path.name.endswith('.intent.json'):
            continue
        item = read(path)
        assert item['outcome'] == 'returned'
        response = item['response']
        body = raw(folder / response['body_file'])
        assert hashlib.sha256(body).hexdigest() == response['sha256']
        assert json.loads(body) == response['body']
        values.append(item)
    return values


def main():
    final_source = read(BASE / 'source-final.json')
    for path, digest in final_source.items():
        assert hashlib.sha256(raw(ROOT / path)).hexdigest() == digest
    state = read(BASE / 'runs/part1/state.json')
    session = read(BASE / 'prepared/session.json')
    pg = read(BASE / 'readback-02/saved-records.json')
    assert pg == read(BASE / 'runs/part1/saved-records.json')
    receipt = read(BASE / 'readback-02/readback.json')
    pg_digest = hashlib.sha256(json_bytes(pg)).hexdigest()
    assert receipt['scoped_pg_before_sha256'] == receipt['scoped_pg_after_sha256'] == pg_digest
    assert receipt['scoped_pg_readonly'] and pg['readonly']
    assert state['session_sha256'] == hashlib.sha256(raw(BASE / 'prepared/session.json')).hexdigest()
    assert state['status'] == 'completed_with_issues' and state['sent'] == {'alerts': 1, 'context': 2}
    assert state['other_parts'] == {'part2': 'not_executed'}
    ids, part = session['identities'], session['plan']['parts'][0]
    assert part['id'] == 'part1' and part['counts'] == {'alerts': 1, 'context': 2}
    preflight = read(BASE / 'runs/part1/preflight.json')
    for kind, digest in preflight['connection_sha256'].items():
        assert hashlib.sha256(raw(BASE / f'config/{kind}.json')).hexdigest() == digest
    assert preflight['matching_historical_members'] == preflight['new_alerts'] == preflight['new_context'] == 0
    assert preflight['readonly'] and preflight['fusion']['status'] == 'ready'
    assert preflight['database'] == receipt['database']
    sends = []
    for role in ['context', 'alerts']:
        for name in part['files'][role]:
            send = read(BASE / 'runs/part1' / ('send-' + name.replace('/', '-')))
            assert send['status'] == 'accepted_only' and send['accepted'] == 1 and send['not_attempted'] == 0
            assert not send['cleanup_errors'] and send['tenant_id'] == session['profile']['tenant_id']
            assert send['records'][0]['wire_sha256'] == hashlib.sha256(raw(BASE / 'prepared/wire' / name)).hexdigest()
            sends.append(send['records'][0]['message'])
    lake = read(BASE / 'runs/part1/context-readback.json')
    contexts = {ids[name]['event_id']: read(BASE / 'prepared/wire' / name)['ocsf_event'] for name in part['files']['context']}
    assert {r['event_id'] for r in lake['rows']} == set(contexts) and len(lake['rows']) == 2
    for row in lake['rows']:
        wire = contexts[row['event_id']]
        assert row['tenant_id'] == session['profile']['tenant_id']
        assert row['class_uid'] == wire['class_uid'] and row['event_time_ms'] == event_milliseconds(wire['time'])
        assert all(row['ocsf_json'].get(k) == v for k, v in wire.items())
    alert_path = part['files']['alerts'][0]
    wire = read(BASE / 'prepared/wire' / alert_path)
    alert, material = pg['alerts'][0], pg['alert_materials'][0]
    assert len(pg['alerts']) == len(pg['alert_materials']) == len(pg['incidents']) == len(pg['cases']) == 1
    assert alert['id'] == ids[alert_path]['predicted_canonical_alert_id'] and alert['source_alert_id'] == wire['id']
    assert material['id'] == alert['latest_material_id'] and material['raw_json']['raw_event'] == wire['raw_event']
    assert material['raw_json']['source_event_ids'] == wire['source_event_ids']
    assert {r['source_event_id'] for r in pg['alert_source_refs'] if r['relation_kind'] == 'source_event'} == set(wire['source_event_ids'])

    http = receipts(BASE / 'readback-02/http')
    assert len(http) == receipt['http_get_count'] == 37

    class SavedHttp:
        pages = Http.pages

        def __init__(self):
            self.config = SimpleNamespace(page_size=read(BASE / 'config/http.json')['page_size'])
            self.sequence = 0

        def request(self, method, path):
            item = http[self.sequence]
            assert method == item['request']['method'] == 'GET' and path == item['request']['path']
            assert item['response']['status'] == 200
            self.sequence += 1
            return copy.deepcopy(item['response']['body'])

    reader = SavedHttp()
    with patch('socket.socket', side_effect=AssertionError('saved evidence only')):
        replay = verify_readback(reader, pg)
    assert reader.sequence == 37 and all(receipt[k] == v for k, v in replay.items())
    original_http = receipts(BASE / 'runs/part1/http')
    posts = [r for r in original_http if r['request']['method'] == 'POST']
    assert len(posts) == 2 and sorted(r['response']['status'] for r in posts) == [201, 202]
    for item in posts:
        assert item['request']['path'].endswith(('/diagnose', '/cases'))
    tasks = pg['analysis_tasks']
    case_task = next(t for t in tasks if t['subject_type'] == 'case')
    case_attempt = next(a for a in pg['analysis_attempts'] if a['task_id'] == case_task['id'])
    assert case_task['state'] == 'failed' and case_attempt['error_stage'] == 'input'
    assert case_attempt['error_detail'] == {'exception_type': 'DBAPIError'} and case_attempt['run_id'] is None
    assert not pg['results'] and not any(r['case_id'] is not None for r in pg['runs'])
    assert len(pg['runs']) == 2 and all(r['state'] == 'completed' for r in pg['runs'])
    check = next(t for t in tasks if t['intent'] == 'check')
    assert check['state'] == 'skipped' and check['reason_code'] == 'no_changes'
    assert not any(a['task_id'] == check['id'] for a in pg['analysis_attempts'])
    assert len(pg['alert_assessments']) == len(pg['incident_diagnoses']) == 1

    model_index = read(BASE / 'model-io/index.json')
    assert model_index['source_snapshot_sha256'] == pg_digest
    assert len(model_index['requests']) == model_index['received_original_count'] == 2
    artifacts = {a['id']: a for a in pg['artifacts']}
    total_tokens = 0
    forbidden = ['tenant_uid', 'batch_id', 'scenario_id', 'expected_verdict', state['execution_id']]
    for item in model_index['requests']:
        for name, digest in item['files'].items():
            assert hashlib.sha256(raw(BASE / 'model-io' / name)).hexdigest() == digest
        folder = (BASE / 'model-io' / next(iter(item['files']))).parent
        request, original = read(folder / 'request-artifact.json'), read(folder / 'original-artifact.json')
        assert request == artifacts[item['request_artifact_id']] and original == artifacts[item['original_artifact_id']]
        body, response = read(folder / 'request.json'), read(folder / 'response.json')
        assert request['content_json']['body'] == body and original['content_json']['raw'] == response
        assert response['choices'][0]['finish_reason'] == item['finish_reason'] == 'stop'
        assert response['usage'] == item['usage']
        total_tokens += item['usage']['total_tokens']
        model_text = json.dumps(body['messages'], ensure_ascii=False)
        assert not any(marker in model_text for marker in forbidden)
    assert total_tokens == 4068

    c1 = read(BASE / 'c1-readonly-02.json')
    source = raw(ROOT / 'services/api/app/socai2/case_incident_material.py').decode()
    assert hashlib.sha256(source.encode()).hexdigest() == c1['candidate_sha256']
    old = source.replace("    # SOURCE_SQL has its own `incidents i`; using i.id there would select every\n    # tenant incident. Bind the outer task's subject through a distinct alias.\n", '')
    old = old.replace('replace(":id", "case_material_task.subject_id")', 'replace(":id", "i.id")').replace('case_material_task', 't')
    assert hashlib.sha256(old.encode()).hexdigest() == c1['deployed_source_sha256']
    assert 'i.id=case_material_task.subject_id' in source_sql() and 'i.id=i.id' not in source_sql()
    historical = read(ROOT / 'docs/operations/evidence/streaming-fullflow-20261116-02/final-pg.json')['rows']
    fixed, failed = [], []
    for item in c1['checks']:
        if item['version'] == 'deployed':
            assert item['status'] == 'failed' and item['sqlstate'] == '21000'
            failed.append(item['case_id'])
            continue
        assert item['version'] == 'fixed_isolated_readonly' and item['status'] == 'passed' and item['readonly']
        context = item['context']
        records = pg if item['case_id'] == pg['cases'][0]['id'] else historical
        expected = {r['alert_id'] for r in records['case_alerts'] if r['case_id'] == item['case_id']}
        assert set(context['alerts']) == set(context['scope']['alert_ids']) == set(item['alert_ids']) == expected
        assert context['case']['tenant_id'] == session['profile']['tenant_id'] and len(context['incidents']) == 1
        for iid, inc in context['incidents'].items():
            material = inc['analysis_material']
            rid = material['source_run_id']
            find = lambda name, identity: next(r for r in records[name] if r['id'] == identity)
            candidate = {'run': find('runs', rid), 'task': find('analysis_tasks', material['task_id']),
                         'attempt': find('analysis_attempts', material['attempt_id']),
                         'input': find('artifacts', material['input']['id']), 'response': find('artifacts', material['response']['id']),
                         'receipt': find('artifacts', material['receipt_source']['id']),
                         'originals': [find('artifacts', ref['id']) for ref in material['originals']]}
            assert candidate['input']['content_json']['parent']['id'] == iid
            assert candidate['run']['incident_id'] == material['incident_id'] == iid
            with patch('socket.socket', side_effect=AssertionError('saved evidence only')):
                recomputed, reasons = freeze(iid, candidate, sorted(expected))
            assert recomputed == material and not reasons
            assert set(material['case_selected_alert_ids']) == expected
        fixed.append({'case_id': item['case_id'], 'alert_ids': sorted(expected), 'sources': item['incidents']})
    assert len(fixed) == len(failed) == 2 and set(failed) == {r['case_id'] for r in fixed}
    assert sorted(len(r['alert_ids']) for r in fixed) == [1, 4]
    assert not set(fixed[0]['alert_ids']) & set(fixed[1]['alert_ids'])
    assert c1['new_business_writes'] == c1['new_model_calls'] == 0
    assert not c1['active_service_changed'] and not c1['case_run_created']
    assert read(BASE / 'services-before.json') == read(BASE / 'services-after.json')['services']
    for path, digest in SEEN.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    report = {'scope': 'saved_actual_02_and_isolated_C1_fix_independent_review', 'status': 'partial_pass_case_blocked',
              'execution_id': state['execution_id'], 'source_binding': str((BASE / 'source-final.json').relative_to(ROOT)),
              'kafka_ack_messages': sends, 'context_lake_records': 2, 'alerts': 1, 'incident_diagnoses': 1,
              'http_readback': {'actual_saved_gets_replayed': 37, 'steps': 7, 'artifacts': 21, 'pg_digest_unchanged': pg_digest},
              'incident_check': 'no_changes_no_attempt_no_run', 'actual_model_requests': 2,
              'finish_reasons': ['stop', 'stop'], 'total_tokens': total_tokens, 'model_quality': 'not_fully_evaluated',
              'input_marker_scan': {'markers': forbidden, 'matches': 0},
              'case': {'created': True, 'task_id': case_task['id'], 'state': 'failed', 'error_stage': 'input',
                       'error_type': 'DBAPIError', 'runs': 0, 'results': 0, 'recovered': False},
              'C1_fix': {'source_review': 'minimal_alias_fix_matches_deployed_source_on_reversal',
                         'saved_real_readonly_evidence': 'accepted', 'old_SQL_failed_cases': failed, 'fixed_cases': fixed,
                         'fresh_independent_database_execution': False, 'deployed': False},
              'new_reviewer_service_connections': 0, 'new_reviewer_business_writes': 0, 'new_reviewer_model_calls': 0,
              'part2': 'not_executed', 'task3b_complete': False, 'task3_complete': False,
              'evidence_hashes': 'review-evidence-03.json', 'local_checks': 'local-checks-03.json'}
    with (HERE / 'review-evidence-03.json').open('x') as f:
        json.dump(SEEN, f, ensure_ascii=False, indent=2)
    with (HERE / 'independent-review-03.json').open('x') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print('Independent saved-evidence review: context/A/I and 37 GETs pass; C1 isolated read-only fix accepted; Case still failed, 0 Run/Result, 3b incomplete.')


if __name__ == '__main__':
    main()
