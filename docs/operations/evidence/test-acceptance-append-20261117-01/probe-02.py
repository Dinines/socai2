"""Offline append-result boundary probe; all actual history remains unchanged."""
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/testdata'))
from acceptance_append import AppendRun


def load(path):
    value = json.loads(path.read_text())
    return value.get('value', value)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    origin = ROOT / 'docs/operations/evidence/streaming-fullflow-20261116-02'
    paths = [origin / 'first-round-snapshot.json', origin / 'final-pg.json']
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    before, after = [load(p)['rows'] for p in paths]
    for rows in (before, after):
        rows['incident_members'] = copy.deepcopy(rows['incident_alerts'])
    whole = next(c['id'] for c in after['cases']
                 if sum(r['case_id'] == c['id'] for r in after['runs']) == 2)
    fixed = next(c['id'] for c in after['cases'] if c['id'] != whole)
    anchor = next(r['alert_id'] for r in before['case_alerts'] if r['case_id'] == fixed)
    case_plan = [{'key': key, 'scope': scope, 'alert_refs': ['part1/alerts/001.json'],
                  'create_after_part': 'part1', 'check_after_parts': ['part2']}
                 for key, scope in [('whole', 'incident'), ('fixed', 'alerts')]]
    session = {'identities': {'part1/alerts/001.json': {'predicted_canonical_alert_id': anchor}},
               'plan': {'scenario': {'cases': case_plan}}}
    first_ids = {r['id'] for r in before['runs']}
    new_case_runs = {r['id'] for r in after['runs'] if r['case_id'] == whole and r['id'] not in first_ids}
    assert len(new_case_runs) == 1
    output = HERE / 'probe-02'
    output.mkdir(exist_ok=False)
    observations = []
    for variation in ('baseline_saved_two_rounds', 'expanded_case_without_new_run'):
        rows = copy.deepcopy(after)
        if variation == 'expanded_case_without_new_run':
            removed_attempts = [a for a in rows['analysis_attempts'] if a['run_id'] in new_case_runs]
            removed_tasks = {a['task_id'] for a in removed_attempts}
            rows['runs'] = [r for r in rows['runs'] if r['id'] not in new_case_runs]
            rows['analysis_attempts'] = [a for a in rows['analysis_attempts'] if a['run_id'] not in new_case_runs]
            rows['analysis_tasks'] = [t for t in rows['analysis_tasks'] if t['id'] not in removed_tasks]
            rows['results'] = [r for r in rows['results'] if r['source_run_id'] not in new_case_runs]
            for table in ('run_members', 'run_steps', 'artifacts'):
                rows[table] = [r for r in rows[table] if r['run_id'] not in new_case_runs]
        folder = output / variation
        folder.mkdir()
        runner = AppendRun.__new__(AppendRun)
        runner.previous = {'rows': copy.deepcopy(before)}
        runner.session = session
        runner.part = {'id': 'part2'}
        runner.state = {'cases': {'whole': [whole], 'fixed': [fixed]}}
        runner.output = folder
        # Test only the saved-result validator. Freeze/preflight gates are tested separately.
        runner.frozen = lambda: None
        input_hash = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
        with patch('socket.socket', side_effect=AssertionError('offline probe only')):
            issues = runner.validate_saved(rows)
        assert input_hash == hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
        receipt = load(folder / 'append-readback.json')
        observed = next(c for c in receipt['cases'] if c['key'] == 'whole')
        observations.append({'variation': variation, 'validator_status': receipt['status'],
                             'returned_execution_issues': issues,
                             'before_members': len([r for r in before['case_alerts'] if r['case_id'] == whole]),
                             'after_members': len(observed['current_member_ids']),
                             'new_run_ids': observed['new_run_ids'], 'new_result_ids': observed['new_result_ids'],
                             'old_result_still_present': any(r['case_id'] == whole for r in rows['results']),
                             'execution_state': observed['execution_state'], 'input_sha256': input_hash})
    assert hashes == {str(p.relative_to(ROOT)): digest(p) for p in paths}
    result = {'scope': 'validate_saved only, controlled in-memory graph variation; not a business execution',
              'source_files': hashes, 'observations': observations, 'historical_files_unchanged': True,
              'network_calls': 0, 'kafka_sends': 0, 'model_calls': 0}
    with (HERE / 'probe-results-02.json').open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(observations, ensure_ascii=False))


if __name__ == '__main__':
    main()
