"""Final documentation-only image revision: packaged Compose and stored report."""
import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(config_path):
    config = json.loads(config_path.read_text())
    output = Path(config['output'])
    output.mkdir(exist_ok=False)
    private = output/'empty-config'
    private.mkdir()
    results = output/'results'
    results.mkdir()
    environment = config['environment'] | {'ACCEPTANCE_CONFIG_DIR': str(private),
                                           'ACCEPTANCE_RESULTS_DIR': str(results)}
    selected = output/'run.env'
    selected.write_text(''.join(f'{k}={v}\n' for k, v in environment.items()))
    prefix = ['docker', 'compose', '--env-file', str(selected), '-f', config['compose'],
              'run', '--rm', '-T', 'acceptance']
    original = Path(environment['ACCEPTANCE_MATERIALS_DIR'])
    before = {str(p.relative_to(original)): sha(p) for p in sorted(original.rglob('*')) if p.is_file()}
    receipts = []
    for args in ([], ['report', '--prepared', '/materials', '--output', '/results/report'],
                 ['session', '--prepared', '/materials', '--output', '/results/console']):
        result = subprocess.run([*prefix, *args], input='', capture_output=True, text=True, timeout=config['timeout_seconds'])
        receipts.append({'command': [*prefix, *args], 'exit_code': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr})
        assert result.returncode == 0
    report = json.loads((results/'report/report.json').read_text())
    prior = json.loads(Path(config['reference_report']).read_text())
    assert {k: v for k, v in report.items() if k != 'observed_at'} == {
        k: v for k, v in prior.items() if k != 'observed_at'}
    manifest = json.loads((results/'report/manifest.json').read_text())
    for item in manifest['files']:
        assert sha(results/'report'/item['path']) == item['sha256']
    end = json.loads((results/'console/end.json').read_text())
    assert end['reason'] == 'eof' and end['execution_attempts'] == 0 and end['all_parts_completed']
    assert {str(p.relative_to(original)): sha(p) for p in sorted(original.rglob('*')) if p.is_file()} == before
    value = {'status': 'passed', 'receipts': receipts, 'source_files_preserved': len(before),
             'report_files_readback': len(manifest['files']), 'counts': report['counts'],
             'model_requests': report['models']['request_count'], 'tokens': report['models']['usage']['total_tokens'],
             'quality_issues': report['quality']['issue_count'], 'step_issues': len(report['step_issues']),
             'network': environment['ACCEPTANCE_NETWORK'], 'business_actions': 0, 'new_model_calls': 0}
    (output/'validation.json').write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    print({k: v for k, v in value.items() if k != 'receipts'})


if __name__ == '__main__':
    import sys
    verify(Path(sys.argv[1]))
