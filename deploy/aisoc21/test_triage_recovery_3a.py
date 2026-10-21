"""Run only persistence/message-validation tests on the cached Agents test image."""
from pathlib import Path
import hashlib, json, re, subprocess, sys

R = Path('/opt/sting-aisoc-socai2')
E = R / 'evidence/3a-triage-recovery-20261020'
SUITES = ['test_fused_alert_worker.py', 'test_replay_leakage.py',
          'test_replay_shadow_no_writes.py', 'test_ledger_tenant.py',
          'test_auto_triage_ledger_records_the_prompt.py',
          'test_outcome_memory.py', 'test_business_context_hotpath.py',
          'test_repeat_suppression_closes_the_loop.py']
NEW = ['test_triage_durability_3a.py', 'test_triage_delivery_3a.py', 'test_triage_recovery_3a.py']
IMAGE = 'socai2-agents-test:1g-20261020'
PARENT_IMAGE = 'socai2-agents:triage-durability-3a-20261020'
PARENT_ID = 'sha256:24071dd2817c34cc7108f38ae931cee43a831c3c5f01f49a65812fb87f51aea1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    return {str(path.relative_to(R / 'source')): digest(path)
            for path in (R / 'source/services/agents/app').rglob('*.py')}


def image_id(reference):
    return subprocess.check_output(['docker', 'image', 'inspect', reference, '--format', '{{.Id}}']).decode().strip()


def main(service, attempt):
    assert service == 'agents' and re.fullmatch(r'[a-z0-9-]+', attempt)
    E.mkdir(exist_ok=True, mode=0o700)
    E.chmod(0o700)
    log = E / f'tests-triage-recovery-3a-agents-{attempt}.log'
    record_path = E / f'tests-agents-{attempt}.json'
    assert not log.exists() and not record_path.exists(), 'Retain prior attempt; use a new label'
    assert image_id(PARENT_IMAGE) == PARENT_ID, 'Cached runtime parent changed; inspect before testing/building'
    test_image_id = image_id(IMAGE)
    files = ['/source/services/agents/tests/' + name for name in SUITES]
    files += ['/source/tests/porting/' + name for name in NEW]
    host_paths = [R / path.removeprefix('/') for path in files]
    assert all(path.is_file() for path in host_paths), 'Finish the bounded test inputs before starting'
    test_inputs = {str(path.relative_to(R / 'source')): digest(path) for path in host_paths}
    command = ['docker', 'run', '--rm', '--network', 'none',
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'ENVIRONMENT=production',
               '-e', 'AISOC_DEV_AUTH_BYPASS=false', '-e', 'DATABASE_URL=', '-e', 'DATABASE_DSN=',
               '-e', 'PYTHONPATH=/source/services/agents',
               '-v', str(R / 'source') + ':/source:ro',
               '-v', str(R / 'source/tests/porting/reference/connectors') + ':/source/services/connectors:ro',
               '-w', '/source/services/agents', test_image_id,
               'python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--asyncio-mode=auto', *files]
    before = source_hashes()
    result = subprocess.run(command, text=True, capture_output=True)
    with log.open('x') as stream:
        stream.write(result.stdout + result.stderr)
    log.chmod(0o600)
    matches = re.findall(r'(\d+) passed', result.stdout)
    passed = int(matches[-1]) if matches else 0
    unchanged = source_hashes() == before
    test_unchanged = all(digest(path) == test_inputs[str(path.relative_to(R / 'source'))] for path in host_paths)
    assert image_id(PARENT_IMAGE) == PARENT_ID
    record = {'service': service, 'attempt': attempt, 'passed': passed,
              'exit_code': result.returncode, 'suites': SUITES, 'new_tests': NEW,
              'log_sha256': digest(log), 'network': 'none',
              'auth_or_model_or_database_doubles_in_unit_tests': True,
              'tested_runtime_source_sha256': before, 'runtime_source_unchanged_during_tests': unchanged,
              'test_input_sha256': test_inputs, 'test_inputs_unchanged_during_tests': test_unchanged,
              'cached_test_image': IMAGE, 'cached_test_image_id': test_image_id,
              'runtime_parent_image': PARENT_IMAGE, 'runtime_parent_image_id': PARENT_ID,
              'production_dependencies_changed': False, 'remote_or_real_model_test': False}
    with record_path.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    record_path.chmod(0o600)
    print(json.dumps({key: value for key, value in record.items() if key not in ['tested_runtime_source_sha256', 'test_input_sha256']}))
    assert result.returncode == 0 and passed > 0 and unchanged and test_unchanged


if __name__ == '__main__':
    main(*sys.argv[1:])
