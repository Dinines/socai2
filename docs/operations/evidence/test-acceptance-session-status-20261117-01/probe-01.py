"""Direct offline receipt-boundary checks; no changes to actual execution records."""
import hashlib
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/testdata'))
from acceptance_status import session_status


def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file()}


def main():
    source = ROOT / 'docs/operations/evidence/acceptance-singlepart-20261117-02'
    prior = {n: hashes(source / n) for n in ['prepared', 'runs']}
    frozen = json.loads((ROOT / 'docs/operations/evidence/acceptance-session-status-20261117-01/source-freeze-01.json').read_text())['files']
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in frozen.items())
    output = HERE / 'probe-01'
    output.mkdir(exist_ok=False)
    observations = []
    for variation in ['baseline', 'invalid_nested_steps', 'orphan_attempt_task', 'invalid_http_response_shape']:
        copy = output / variation
        shutil.copytree(source / 'prepared', copy)
        shutil.copytree(source / 'runs', copy / 'runs')
        modified = None
        if variation == 'invalid_nested_steps':
            modified = copy / 'runs/part1/state.json'
            value = json.loads(modified.read_text())
            value['steps'] = ['controlled-invalid-step']
        elif variation == 'orphan_attempt_task':
            modified = copy / 'runs/part1/saved-records.json'
            value = json.loads(modified.read_text())
            attempt = next(a for a in value['analysis_attempts'] if a['run_id'])
            attempt['task_id'] = '11111111-1111-4111-8111-111111111111'
            assert not any(t['id'] == attempt['task_id'] for t in value['analysis_tasks'])
        elif variation == 'invalid_http_response_shape':
            intent = next((copy / 'runs/part1/http').glob('*.intent.json'))
            modified = intent.with_name(intent.name.replace('.intent.json', '.json'))
            value = json.loads(modified.read_text())
            value['response'] = []
        if modified:
            modified.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        before = hashes(copy)
        try:
            with patch('socket.socket', side_effect=AssertionError('offline review only')):
                result = session_status(copy)
            observed = {'state': result['state'], 'next_part': result['next_part'],
                        'closure_verified': result['parts'][0]['closure_verified'],
                        'blocking_issues': result['blocking_issues']}
            (output / f'{variation}-status.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        except Exception as exc:
            observed = {'exception_type': type(exc).__name__, 'error': str(exc)}
        assert before == hashes(copy)
        observations.append({'variation': variation, 'modified': str(modified.relative_to(output)) if modified else None,
                             'expected': 'waiting_append' if variation == 'baseline' else 'needs_review_no_next', 'observed': observed})
    assert prior == {n: hashes(source / n) for n in prior}
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in frozen.items())
    report = {'scope': 'independent 3c.1 direct offline receipt boundary probes', 'source_sha256': frozen,
              'observations': observations, 'historical_records_unchanged': True,
              'implementation_changed': False, 'network_calls': 0, 'business_writes': 0, 'model_calls': 0}
    with (HERE / 'probe-results-01.json').open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(observations, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
