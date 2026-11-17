"""Replay review-01 inputs through the CLI; preserve original failures and receipts."""
import contextlib
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/testdata'))
from acceptance import main as cli_main


def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file()}


def main():
    source = ROOT / 'docs/operations/evidence/acceptance-singlepart-20261117-02'
    prior = {n: hashes(source / n) for n in ['prepared', 'runs']}
    old_probes = hashes(HERE / 'probe-01')
    frozen = json.loads((ROOT / 'docs/operations/evidence/acceptance-session-status-20261117-01/source-freeze-02.json').read_text())['files']
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in frozen.items())
    output = HERE / 'probe-02'
    output.mkdir(exist_ok=False)
    observations, socket_attempts, credential_reads = [], [], []
    expected_codes = {'baseline': set(), 'invalid_nested_steps': {'saved_closure_mismatch'},
                      'orphan_attempt_task': {'saved_execution_link_mismatch'},
                      'invalid_http_response_shape': {'http_write_unconfirmed'}}
    for variation, codes in expected_codes.items():
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
        assert before == hashes(HERE / 'probe-01' / variation), 'must replay identical review-01 inputs'
        connections = set(json.loads((copy / 'session.json').read_text())['profile']['connection_files'].values())
        old_open = Path.open

        def guarded_open(path, *args, **kwargs):
            if str(path) in connections:
                credential_reads.append(str(path))
                raise AssertionError('connection file read prohibited')
            return old_open(path, *args, **kwargs)

        def no_socket(*args, **kwargs):
            socket_attempts.append('socket')
            raise AssertionError('offline review only')

        report_path = output / f'{variation}-status.json'
        console = io.StringIO()
        with contextlib.redirect_stdout(console), patch('socket.socket', side_effect=no_socket), \
                patch.object(Path, 'open', guarded_open):
            exit_code = cli_main(['status', '--prepared', str(copy), '--report', str(report_path)])
        result = json.loads(report_path.read_text())
        printed = json.loads(console.getvalue())
        baseline = variation == 'baseline'
        assert exit_code == (0 if baseline else 3)
        assert result['state'] == printed['state'] == ('waiting_append' if baseline else 'needs_review')
        assert result['next_part'] == ('part2' if baseline else None)
        assert result['parts'][0]['closure_verified'] is baseline
        assert {issue['code'] for issue in result['blocking_issues']} == codes
        assert not result['live_state_verified'] and not any(result['this_command'].values())
        assert 'controlled-invalid-step' not in report_path.read_text()
        assert before == hashes(copy)
        observations.append({'variation': variation, 'same_inputs_as_review01': True,
                             'modified': str(modified.relative_to(output)) if modified else None,
                             'exit_code': exit_code, 'state': result['state'], 'next_part': result['next_part'],
                             'closure_verified': result['parts'][0]['closure_verified'],
                             'diagnostic_codes': sorted(codes), 'report_readback': 'passed',
                             'input_unchanged': True, 'exception': None})
    assert prior == {n: hashes(source / n) for n in prior}
    assert old_probes == hashes(HERE / 'probe-01')
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in frozen.items())
    assert not socket_attempts and not credential_reads
    assert 'acceptance_run' not in sys.modules and 'acceptance_clients' not in sys.modules
    report = {'scope': 'S1/S2 CLI replay of identical review-01 inputs', 'status': 'passed',
              'source_sha256': frozen, 'observations': observations,
              'historical_records_unchanged': True, 'review01_probes_unchanged': True,
              'implementation_changed': False, 'socket_attempts': len(socket_attempts),
              'credential_reads': len(credential_reads), 'network_calls': 0,
              'business_writes': 0, 'model_calls': 0, 'run_or_clients_imported': False}
    with (HERE / 'probe-results-02.json').open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(observations, ensure_ascii=False))


if __name__ == '__main__':
    main()
