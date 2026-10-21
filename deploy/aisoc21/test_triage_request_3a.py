"""Bounded source-mounted tests on the unchanged cached dependency images."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

R = Path('/opt/sting-aisoc-socai2')
E = R / 'evidence/3a-triage-request-20261020'
SUITES = {
    'agents': ['test_llm_factory.py', 'test_llm_hot_path.py', 'test_llm_contract.py',
               'test_triage_structured_output.py', 'test_auto_triage_ledger_records_the_prompt.py',
               'test_fused_alert_worker.py'],
    'api': ['test_investigation_replay.py'],
}
NEW = {'agents': ['test_triage_request_3a.py', 'test_triage_recovery_3a.py', 'test_triage_durability_3a.py'],
       'api': ['test_triage_cursor_3a.py']}
IMAGES = {'agents': 'socai2-agents-test:1g-20261020', 'api': 'socai2-api-test:tenant-skill-3a-20261020'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources(service):
    return {str(p.relative_to(R / 'source')): sha(p) for p in (R / f'source/services/{service}/app').rglob('*.py')}


def main(service, attempt):
    assert service in SUITES and re.fullmatch(r'[a-z0-9-]+', attempt)
    before_fix = attempt == 'before'
    names = ([f'tests/porting/{NEW[service][0]}'] if before_fix else
             [f'services/{service}/tests/{n}' for n in SUITES[service]] + [f'tests/porting/{n}' for n in NEW[service]])
    paths = [R / 'source' / name for name in names]
    assert all(p.is_file() for p in paths), [str(p) for p in paths if not p.is_file()]
    log, record_path = E / f'tests-{service}-{attempt}.log', E / f'tests-{service}-{attempt}.json'
    assert not log.exists() and not record_path.exists()
    inputs = {n: sha(p) for n, p in zip(names, paths)}
    before = sources(service)
    image = subprocess.check_output(['docker', 'image', 'inspect', IMAGES[service], '--format', '{{.Id}}'], text=True).strip()
    command = ['docker', 'run', '--rm', '--network', 'none', '-e', 'PYTHONDONTWRITEBYTECODE=1',
               '-e', 'ENVIRONMENT=production', '-e', 'AISOC_DEV_AUTH_BYPASS=false', '-e', 'DATABASE_DSN=',
               '-e', 'DATABASE_URL=' + ('postgresql+asyncpg://unit:unit@127.0.0.1:1/unit' if service == 'api' else ''),
               '-e', f'PYTHONPATH=/source/services/{service}', '-v', str(R / 'source') + ':/source:ro',
               '-w', f'/source/services/{service}']
    if service == 'agents':
        command += ['-v', str(R / 'source/tests/porting/reference/connectors') + ':/source/services/connectors:ro']
    command += [image, 'python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--asyncio-mode=auto']
    command += ['/source/' + name for name in names]
    result = subprocess.run(command, capture_output=True, text=True)
    with log.open('x') as f:
        f.write(result.stdout + result.stderr)
    log.chmod(0o600)
    def count(label):
        matches = re.findall(r'(\d+) ' + label, result.stdout)
        return int(matches[-1]) if matches else 0
    record = {'service': service, 'attempt': attempt, 'exit_code': result.returncode,
              'passed': count('passed'), 'failed': count('failed'), 'errors': count('error'),
              'test_input_sha256': inputs, 'tested_runtime_source_sha256': before,
              'log_sha256': sha(log), 'cached_test_image_id': image, 'network': 'none',
              'source_unchanged': sources(service) == before,
              'test_inputs_unchanged': all(sha(R / 'source' / n) == h for n, h in inputs.items()),
              'real_model_calls': 0, 'production_dependencies_changed': False}
    with record_path.open('x') as f:
        json.dump(record, f, indent=2)
    record_path.chmod(0o600)
    print(json.dumps({k: v for k, v in record.items() if k not in ['test_input_sha256', 'tested_runtime_source_sha256']}))
    assert record['source_unchanged'] and record['test_inputs_unchanged']
    assert result.returncode != 0 and count('failed') > 0 if before_fix else result.returncode == 0 and count('passed') > 0


if __name__ == '__main__':
    main(*sys.argv[1:])
