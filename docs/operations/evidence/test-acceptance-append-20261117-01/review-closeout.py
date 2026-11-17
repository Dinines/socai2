"""Verify saved static/failed-batch/cleanup evidence; no running service access."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'docs/operations/evidence/acceptance-append-20261117-02'
OLD = ROOT / 'docs/operations/evidence/acceptance-append-20261117-01'
READ = {}


def raw(path):
    value = path.read_bytes()
    READ[str(path.relative_to(ROOT))] = hashlib.sha256(value).hexdigest()
    return value


def load(path):
    return json.loads(raw(path))


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert json.loads((HERE / name).read_text()) == value


def main():
    facts = load(SOURCE / 'final-records.json')
    static = load(SOURCE / 'static-verification.json')
    before = load(SOURCE / 'static-before.json')
    prior = ROOT / 'docs/operations/evidence/acceptance-case-continuation-20261117-01'
    prior_records = load(prior / 'static-before.json')['records']
    prior_new = load(prior / 'static-verification.json')['new_record']
    prior_records[prior_new['id']] = prior_new
    assert before['records'] == prior_records and len(prior_records) == 51
    site = ROOT / 'deliverables/investigation-validation-20261106/processing-audit'
    index = raw(site / 'index.html').decode()
    current = {r['id']: r for r in json.loads(re.search(r'<script type="application/json" id="audit-records">(.*?)</script>', index, re.S)[1])}
    assert len(current) == 53 and all(current[k] == v for k, v in prior_records.items())
    assert set(current) - set(prior_records) == {r['id'] for r in static['new_records']}
    for name, expected in before['pages'].items():
        assert hashlib.sha256(raw(site / name)).hexdigest() == expected
    historical_hashes = load(ROOT / 'docs/operations/evidence/test-acceptance-case-continuation-20261117-01/evidence-hashes-01.json')
    prior_files = {n: h for n, h in historical_hashes.items() if '/processing-audit/' in n and not n.endswith('/processing-audit/index.html')}
    for name, expected in prior_files.items():
        assert hashlib.sha256(raw(ROOT / name)).hexdigest() == expected
    assert len(prior_files) == 226
    assert static['source'] == 'static-export-02' and not static['live_21_viewer_release'] and static['browser_validation'] == 'not_performed'
    source_rows = {k: {r['id']: r for r in v} for k, v in facts.items() if isinstance(v, list)}
    for item in static['new_records']:
        assert current[item['id']] == item
        cid = item['scope_id']
        case_runs = {r['id'] for r in facts['runs'] if r['case_id'] == cid}
        assert len(case_runs) == 2
        page = raw(site / item['detail']).decode()
        assert all(rid in page for rid in case_runs)
        logs = load(site / item['logs']['manifest'])
        assert {r['id'] for r in logs['runs']} == case_runs
        export = SOURCE / static['source'] / 'cases' / cid / 'export'
        manifest = load(export / 'manifest.json')
        db_raw = raw(export / 'database.json')
        assert manifest['sources'] == [{'file': 'database.json', 'sha256': hashlib.sha256(db_raw).hexdigest()}]
        db = json.loads(db_raw)
        assert [c['id'] for c in db['cases']] == [cid]
        assert {r['id'] for r in db['results']} == {r['id'] for r in facts['results'] if r['case_id'] == cid}
        for table, rows in db.items():
            assert all(source_rows[table].get(r['id']) == r for r in rows), table
    cleanup = load(SOURCE / 'cleanup.json')
    assert cleanup['status'] == 'passed' and set(cleanup['stopped_processes']) == {'api', 'fusion', 'dispatcher'}
    assert cleanup['dedicated_model_forward_closed'] and cleanup['databases_and_evidence_retained'] and cleanup['no_deployment_to_21']
    assert cleanup['dependency_action'] == 'compose stop, no down/remove/volume deletion'
    old_state = load(OLD / 'prepared/runs/part1/state.json')
    assert old_state['status'] == 'incomplete' and old_state['error_code'] == 'http_status_503'
    assert old_state['sent'] == {'alerts': 1, 'context': 2}
    exchanges = [load(p) for p in (OLD / 'prepared/runs/part1/http').glob('*.json') if not p.name.endswith('.intent.json')]
    assert any(r.get('response', {}).get('status') == 503 for r in exchanges)
    old_rows = load(OLD / 'stopped-batch-records.json')
    assert not old_rows['cases'] and not old_rows['results'] and len(old_rows['runs']) == 2
    assert all(t['state'] == 'completed' for t in old_rows['analysis_tasks'])
    assert all(a['local_state'] == 'ended' for a in old_rows['analysis_attempts'])
    assert not ({r['id'] for r in old_rows['runs']} & {r['id'] for r in facts['runs']})
    old_index = load(OLD / 'model-io/index.json')
    assert old_index['source_snapshot_sha256'] == hashlib.sha256(raw(OLD / 'stopped-batch-records.json')).hexdigest()
    assert old_index['request_count'] == old_index['received_original_count'] == 2 and old_index['new_model_calls'] == 0
    old_artifacts = {r['id']: r for r in old_rows['artifacts']}
    old_tokens = 0
    for entry in old_index['requests']:
        for name, expected in entry['files'].items():
            assert hashlib.sha256(raw(OLD / 'model-io' / name)).hexdigest() == expected
        response = old_artifacts[entry['original_artifact_id']]['content_json']['raw']
        assert response['choices'][0]['finish_reason'] == entry['finish_reason'] == 'stop'
        assert response['usage'] == entry['usage']
        old_tokens += response['usage']['total_tokens']
    assert old_tokens == 4013
    old_summary, old_cleanup = load(OLD / 'closed-batch-summary.json'), load(OLD / 'stopped-processes.json')
    assert old_summary['status'] == 'original_incomplete_retained' and old_summary['pending_tasks'] == old_cleanup['pending_tasks'] == 0
    diagnostics = load(SOURCE / 'retained-diagnostics.json')
    citation = [r['details']['citation_review'] for r in diagnostics['artifacts']
                if r['schema_version'] == 'socai2.baseline-delivery.v2' and isinstance(r['details'].get('citation_review'), dict)]
    assert sorted(len(r['issues']) for r in citation) == [1, 1, 2, 5]
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == h for name, h in READ.items())
    save('closeout-evidence-hashes-04.json', READ)
    save('closeout-review-04.json', {
        'status': 'saved_closeout_evidence_passed', 'static_records': {'before': 51, 'after': 53, 'old_records_equal': True,
            'old_detail_hashes_checked': len(before['pages']), 'independently_prior_files_checked': len(prior_files),
            'new_cases': 2, 'case_runs_each': 2, 'export_rows_unchanged': True, 'browser_checked': False, 'released_to_21': False},
        'cleanup': {'saved_receipt_reviewed': True, 'current_processes_or_ports_not_probed': True,
            'reported_stopped': cleanup['stopped_processes'], 'data_and_evidence_retained': True, 'no_deployment_to_21': True},
        'failed_batch01': {'status': 'incomplete', 'error_code': 'http_status_503', 'sent': old_state['sent'],
            'cases': 0, 'results': 0, 'real_model_requests': 2, 'tokens': old_tokens, 'original_failure_retained': True},
        'actual_batch02_model_requests': 13, 'actual_batch02_tokens': 109995,
        'combined_actual_model_requests': 15, 'combined_actual_tokens': old_tokens + 109995,
        'C6_citation_issues_retained': 9, 'model_quality': 'not_fully_evaluated',
        'reviewer_business_connections': 0, 'reviewer_sends': 0, 'reviewer_models': 0,
        'evidence_files_hashed': len(READ), 'all_read_files_unchanged': True})
    print('closeout verified: static 51->53 and 226 prior files unchanged; old failure retained; 15 calls/114008 tokens total; 9 C6 issues deferred')


if __name__ == '__main__':
    main()
