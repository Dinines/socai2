"""Run C01's bounded offline suites against the unchanged cached test image.

Invoke on 21 with one new attempt name. Every attempt is reserved exclusively;
neither a failed run nor an interrupted run can overwrite previous evidence.
This runner does not build images, access live dependencies, or deploy services.
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
E = R / 'evidence/c01-fusion-delivery-20261020'
IMAGE = 'socai2-fusion-test:2a-20261020'
TIMEOUT_SECONDS = 300
TESTS = [
    'tests/porting/test_fusion_delivery_recovery.py',
    'services/fusion/tests/test_alert_sink.py',
    'services/fusion/tests/test_alert_sink_batch.py',
    'services/fusion/tests/test_alert_sink_issue_1244.py',
    'services/fusion/tests/test_dlq_sink.py',
    'services/fusion/tests/test_consumer_dlq.py',
    'services/fusion/tests/test_dlq.py',
    'tests/porting/test_source_identity.py',
    'tests/porting/test_source_identity_sink.py',
]
SUPPORT_INPUTS = [
    'services/fusion/pyproject.toml',
    'services/fusion/tests/conftest.py',
    'tests/porting/fixtures/legacy-alert-2a.json',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    return {
        str(path.relative_to(SOURCE)): sha(path)
        for path in sorted((SOURCE / 'services/fusion/app').rglob('*.py'))
    }


def input_hashes(names):
    return {
        name: sha(SOURCE / name) if (SOURCE / name).is_file() else None
        for name in names
    }


def write_json_exclusive(path, value):
    with path.open('x', encoding='utf-8') as output:
        json.dump(value, output, indent=2)
        output.write('\n')
    path.chmod(0o600)


def main(attempt):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', attempt):
        raise SystemExit('Attempt must be 1-48 lowercase letters, digits or hyphens.')
    os.umask(0o077)
    names = TESTS + SUPPORT_INPUTS
    missing = [name for name in names if not (SOURCE / name).is_file()]
    if missing:
        raise SystemExit('Missing test inputs: ' + ', '.join(missing))
    before = sources()
    if not before:
        raise SystemExit('No Fusion runtime Python source files found.')
    inputs = input_hashes(names)
    E.mkdir(mode=0o700, parents=True, exist_ok=True)
    reservation = E / f'tests-fusion-{attempt}.attempt'
    reservation.mkdir(mode=0o700)  # Exclusive even if a prior run crashed.
    log = E / f'tests-fusion-{attempt}.log'
    record_path = E / f'tests-fusion-{attempt}.json'
    if log.exists() or record_path.exists():
        raise SystemExit('Attempt evidence already exists; choose a new attempt.')
    write_json_exclusive(reservation / 'started.json', {
        'attempt': attempt,
        'started_at': datetime.now(timezone.utc).isoformat(),
        'runner_sha256': sha(Path(__file__)),
        'cached_test_image': IMAGE,
        'test_input_sha256': inputs,
        'tested_runtime_source_sha256': before,
    })
    image = subprocess.check_output([
        'docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}',
    ], text=True).strip()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise SystemExit('Cached test image did not resolve to a fixed image ID.')
    container_name = f'socai2-c01-unit-{attempt}'
    command = [
        'docker', 'run', '--rm', '--pull', 'never', '--name', container_name,
        '--network', 'none', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges:true',
        '-e', 'PYTHONDONTWRITEBYTECODE=1',
        '-e', 'ENVIRONMENT=production',
        '-e', 'AISOC_DEV_AUTH_BYPASS=false',
        '-e', 'DATABASE_DSN=', '-e', 'DATABASE_URL=',
        '-e', 'KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:1',
        '-e', 'REDIS_URL=redis://127.0.0.1:1/0',
        '-e', 'OTEL_SDK_DISABLED=true',
        '-e', 'PYTHONPATH=/source/services/fusion',
        '-v', str(SOURCE) + ':/source:ro',
        '-w', '/source/services/fusion',
        image, 'python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        '--asyncio-mode=auto',
    ] + ['/source/' + name for name in TESTS]
    timed_out = False
    with log.open('xb') as output:
        try:
            result = subprocess.run(command, capture_output=True, timeout=TIMEOUT_SECONDS)
            content = result.stdout + result.stderr
            exit_code = result.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            content = (exc.stdout or b'') + (exc.stderr or b'')
            content += b'\nC01 runner timeout; removing only this named test container.\n'
            try:
                cleanup = subprocess.run(
                    ['docker', 'rm', '-f', container_name], capture_output=True, timeout=30,
                )
                content += cleanup.stdout + cleanup.stderr
            except (OSError, subprocess.TimeoutExpired) as cleanup_error:
                content += f'Test container cleanup failed: {type(cleanup_error).__name__}\n'.encode()
            exit_code = 124
        except OSError as exc:
            content = f'C01 test process could not start: {type(exc).__name__}\n'.encode()
            exit_code = 127
        output.write(content)
    log.chmod(0o600)
    text = content.decode('utf-8', errors='replace')

    def count(label):
        matches = re.findall(r'(\d+) ' + label + r'\b', text)
        return int(matches[-1]) if matches else 0

    record = {
        'service': 'fusion', 'change': 'C01', 'attempt': attempt,
        'exit_code': exit_code,
        'passed': count('passed'), 'failed': count('failed'),
        'errors': count('errors?'), 'skipped': count('skipped'),
        'timed_out': timed_out, 'timeout_seconds': TIMEOUT_SECONDS,
        'tests': TESTS, 'test_input_sha256': inputs,
        'tested_runtime_source_sha256': before,
        'log_sha256': sha(log), 'runner_sha256': sha(Path(__file__)),
        'cached_test_image': IMAGE, 'cached_test_image_id': image,
        'network': 'none', 'source_mount': 'read-only',
        'source_unchanged': sources() == before,
        'test_inputs_unchanged': input_hashes(names) == inputs,
        'real_model_calls': 0, 'real_infrastructure_calls': 0,
        'production_dependencies_changed': False,
    }
    write_json_exclusive(record_path, record)
    summary = {
        key: value for key, value in record.items()
        if key not in {'tests', 'test_input_sha256', 'tested_runtime_source_sha256'}
    }
    summary['record_path'] = str(record_path)
    print(json.dumps(summary))
    if not (record['source_unchanged'] and record['test_inputs_unchanged']):
        raise SystemExit('Source or test inputs changed during this attempt.')
    if exit_code != 0 or record['passed'] == 0 or record['failed'] or record['errors']:
        raise SystemExit('C01 offline tests did not pass; evidence has been retained.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python test_fusion_delivery_c01.py ATTEMPT')
    main(sys.argv[1])
