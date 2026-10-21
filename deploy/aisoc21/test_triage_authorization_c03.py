"""C03-02C-01 cached-image, disconnected source-mounted tests; no build or deployment.

Run on 21 with one previously unused attempt name. Missing inputs are refused;
failed/interrupted attempts keep their exclusive reservation and evidence.
Only synthetic test credentials are permitted: no env-file/private mounts or
host environment forwarding are used. Real PG/Kafka/model evidence is not
claimed by these offline suites.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


R = Path('/opt/sting-aisoc-socai2')
SOURCE = R / 'source'
E = R / 'evidence/c03-triage-authorization-20261021'
IMAGE = 'socai2-agents-test:1g-20261020'
IMAGE_ID = 'sha256:017598b8433ddc452524ea0818e9e4cae467bf7d44a735695adda41d12ef0b10'
TIMEOUT_SECONDS = 300
TESTS = [
    'tests/porting/test_triage_reasoning_prompt_c03.py',
    'services/agents/tests/test_auto_triage_dispositions.py',
    'services/agents/tests/test_auto_triage_truncated_json.py',
    'services/agents/tests/test_auto_triage_ledger_records_the_prompt.py',
    'services/agents/tests/test_auto_triage_injection.py',
    'tests/porting/test_triage_request_3a.py',
    'tests/porting/test_triage_budget_3a.py',
]
SUPPORT_INPUTS = [
    'services/agents/pyproject.toml',
    'services/agents/tests/conftest.py',
    'services/agents/app/llm/prompts.lock.json',
    'tests/porting/test_triage_delivery_3a.py',
    'tests/porting/test_triage_recovery_3a.py',
    'tests/porting/reference/connectors/app/main.py',
    'tests/porting/reference/connectors/app/api/router.py',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    return {str(p.relative_to(SOURCE)): sha(p)
            for p in sorted((SOURCE / 'services/agents/app').rglob('*.py'))}


def inputs(names):
    return {name: sha(SOURCE / name) if (SOURCE / name).is_file() else None for name in names}


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    path.chmod(0o600)


def pytest_summary(output):
    """Parse only pytest's last result line, never application log messages.

    Retains the C02 final-summary parser fix: application log text such as
    ``attempt=1 error=`` must not count as pytest collection errors.
    This C03 runner never rewrites any prior attempt or C02 evidence.
    """
    plain = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', output)
    status = r'(?:passed|failed|errors?|skipped|deselected|xfailed|xpassed|warnings?)'
    pattern = (r'^\s*(?:=+\s*)?(\d+ ' + status + r'(?:,\s*\d+ ' + status + r')*)'
               r'\s+in\s+\d+(?:\.\d+)?s(?:\s+\([^\r\n]*\))?\s*(?:=+\s*)?$')
    lines = [line.strip() for line in plain.splitlines() if re.fullmatch(pattern, line)]
    line = lines[-1] if lines else ''
    result = {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0,
              'line': line, 'found': bool(lines)}
    if line:
        for number, label in re.findall(r'(\d+) (' + status + r')\b', line):
            name = 'errors' if label in {'error', 'errors'} else label
            if name in result:
                result[name] = int(number)
    return result


def main(attempt):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', attempt):
        raise SystemExit('Attempt must be 1-48 lowercase letters, digits or hyphens.')
    os.umask(0o077)
    names = TESTS + SUPPORT_INPUTS
    missing = [name for name in names if not (SOURCE / name).is_file()]
    if missing:
        raise SystemExit('Missing test inputs: ' + ', '.join(missing))
    before, test_inputs = sources(), inputs(names)
    if len(before) != 184:
        raise SystemExit('Expected the complete 184-file Agents application source.')
    if not (E / 'prepared.json').is_file():
        raise SystemExit('C03-02C-01 preparation/scope freeze is required before testing.')
    reservation = E / f'tests-agents-{attempt}.attempt'
    reservation.mkdir(mode=0o700)  # Exclusive; never reclaim a failed attempt.
    log, record_path = E / f'tests-agents-{attempt}.log', E / f'tests-agents-{attempt}.json'
    if log.exists() or record_path.exists():
        raise SystemExit('Attempt evidence exists; inspect it and choose a new name.')
    save(reservation / 'started.json', {
        'change': 'C03-02C-01', 'attempt': attempt,
        'started_at': datetime.now(timezone.utc).isoformat(),
        'runner_sha256': sha(Path(__file__)), 'cached_test_image': IMAGE,
        'expected_cached_test_image_id': IMAGE_ID,
        'test_input_sha256': test_inputs, 'tested_runtime_source_sha256': before,
    })
    image = subprocess.check_output([
        'docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}',
    ], text=True).strip()
    if image != IMAGE_ID:
        raise SystemExit('Cached image differs from the frozen C02 test image ID; no tests started.')
    container_name = 'socai2-c03-authorization-unit-' + attempt
    command = [
        'docker', 'run', '--rm', '--pull', 'never', '--name', container_name,
        '--network', 'none', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges:true',
        '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'ENVIRONMENT=production',
        '-e', 'AISOC_DEV_AUTH_BYPASS=false',
        '-e', 'DATABASE_DSN=', '-e', 'DATABASE_URL=',
        '-e', 'OPENAI_API_KEY=', '-e', 'LLM_API_KEY=', '-e', 'LITELLM_MASTER_KEY=',
        '-e', 'KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:1',
        '-e', 'REDIS_URL=redis://127.0.0.1:1/0',
        '-e', 'OTEL_SDK_DISABLED=true',
        '-e', 'PYTHONPATH=/source/services/agents',
        '-v', str(SOURCE) + ':/source:ro',
        '-v', str(SOURCE / 'tests/porting/reference/connectors') + ':/source/services/connectors:ro',
        '-w', '/source/services/agents', image,
        'python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        '--asyncio-mode=auto', '--tb=short',
    ] + ['/source/' + name for name in TESTS]
    timed_out = False
    with log.open('xb') as stream:
        try:
            result = subprocess.run(command, capture_output=True, timeout=TIMEOUT_SECONDS)
            content, exit_code = result.stdout + result.stderr, result.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            content = (exc.stdout or b'') + (exc.stderr or b'')
            content += b'\nC03-02C-01 test deadline; removing only the named test container.\n'
            try:
                cleanup = subprocess.run(['docker', 'rm', '-f', container_name],
                                         capture_output=True, timeout=30)
                content += cleanup.stdout + cleanup.stderr
            except (OSError, subprocess.TimeoutExpired) as cleanup_error:
                content += ('Cleanup unconfirmed: ' + type(cleanup_error).__name__ + '\n').encode()
            exit_code = 124
        except OSError as exc:
            content = ('C03-02C-01 test process could not start: ' + type(exc).__name__ + '\n').encode()
            exit_code = 127
        stream.write(content)
    log.chmod(0o600)
    output = content.decode('utf-8', errors='replace')
    stats = pytest_summary(output)

    record = {
        'service': 'agents', 'change': 'C03-02C-01', 'attempt': attempt,
        'exit_code': exit_code, 'passed': stats['passed'], 'failed': stats['failed'],
        'errors': stats['errors'], 'skipped': stats['skipped'],
        'pytest_summary': stats['line'], 'pytest_summary_found': stats['found'],
        'summary_parser': 'pytest-final-summary-line-v2',
        'timed_out': timed_out, 'timeout_seconds': TIMEOUT_SECONDS,
        'tests': TESTS, 'test_input_sha256': test_inputs,
        'tested_runtime_source_sha256': before, 'runtime_source_count': len(before),
        'log_sha256': sha(log), 'runner_sha256': sha(Path(__file__)),
        'cached_test_image': IMAGE, 'cached_test_image_id': image,
        'expected_cached_test_image_id': IMAGE_ID,
        'network': 'none', 'source_mount': 'read-only',
        'source_unchanged': sources() == before,
        'test_inputs_unchanged': inputs(names) == test_inputs,
        'private_mounts_or_env_files': False,
        'real_model_calls': 0, 'real_infrastructure_calls': 0,
        'new_business_rows': 0, 'broker_send_attempts': 0, 'broker_offset_commits': 0,
        'production_dependencies_changed': False,
    }
    save(record_path, record)
    summary = {key: value for key, value in record.items()
               if key not in {'tests', 'test_input_sha256', 'tested_runtime_source_sha256'}}
    summary['record_path'] = str(record_path)
    print(json.dumps(summary))
    if not (record['source_unchanged'] and record['test_inputs_unchanged']):
        raise SystemExit('Source/test inputs changed during the attempt; evidence retained.')
    if exit_code or not record['passed'] or record['failed'] or record['errors']:
        raise SystemExit('C03-02C-01 offline suites did not pass; failed attempt remains reserved.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python test_triage_reasoning_c03.py ATTEMPT')
    main(sys.argv[1])
