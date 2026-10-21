"""Run this KB batch and directly affected original tests on cached images."""
from pathlib import Path
import hashlib, json, re, subprocess, sys

R = Path('/opt/sting-aisoc-socai2')
E = R / 'evidence/3a-kb-read-20261020'
SUITES = {
    'agents': ['test_triage_knowledge_base.py', 'test_replay_leakage.py',
               'test_auto_triage_ledger_records_the_prompt.py', 'test_ledger_tenant.py',
               'test_fused_alert_worker.py'],
    'api': ['test_kb_triage_retrieval_route.py',
            'test_platform_route_permissions.py::TestWiring::test_kb_query_governs_reading_the_library',
            'test_platform_route_permissions.py::TestWiring::test_the_library_is_not_readable_by_a_machine_key_role',
            'test_platform_route_permissions.py::TestWiring::test_the_rest_of_the_knowledge_base_is_gated',
            'test_platform_route_permissions.py::TestUnentitledCallersAreRefused::test_a_viewer_cannot_erase_a_runbook_for_the_whole_tenant',
            'test_compliance_phishing_kb_tenant_isolation.py::TestKnowledgeBaseTenantIsolation'],
}
NEW = {
    'agents': ['test_kb_read_agents.py', 'test_kb_read_ledger.py',
               'test_org_memory_agents.py', 'test_org_memory_ledger.py',
               'test_tenant_skill_agents.py', 'test_tenant_skill_ledger.py'],
    'api': ['test_kb_read_api.py'],
}
IMAGES = {'agents': 'socai2-agents-test:1g-20261020',
          'api': 'socai2-api-test:tenant-skill-3a-20261020'}


def source_hashes(service):
    return {str(path.relative_to(R / 'source')): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (R / f'source/services/{service}/app').rglob('*.py')}


def main(service, attempt):
    assert service in SUITES and re.fullmatch(r'[a-z0-9-]+', attempt)
    E.mkdir(exist_ok=True, mode=0o700)
    E.chmod(0o700)
    log = E / f'tests-kb-read-3a-{service}-{attempt}.log'
    record_path = E / f'tests-{service}-{attempt}.json'
    assert not log.exists() and not record_path.exists(), 'Retain previous attempt; use a new label'
    files = [f'/source/services/{service}/tests/' + name for name in SUITES[service]]
    files += ['/source/tests/porting/' + name for name in NEW[service]]
    command = ['docker', 'run', '--rm', '--network', 'none',
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'ENVIRONMENT=production',
               '-e', 'AISOC_DEV_AUTH_BYPASS=false',
               '-e', ('DATABASE_URL=postgresql+asyncpg://unit:unit@127.0.0.1:1/unit' if service == 'api' else 'DATABASE_URL='),
               '-e', 'DATABASE_DSN=', '-e', f'PYTHONPATH=/source/services/{service}',
               '-v', str(R / 'source') + ':/source:ro', '-w', f'/source/services/{service}']
    if service == 'agents':
        command += ['-v', str(R / 'source/tests/porting/reference/connectors') + ':/source/services/connectors:ro']
    command += [IMAGES[service], 'python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--asyncio-mode=auto', *files]
    before = source_hashes(service)
    result = subprocess.run(command, text=True, capture_output=True)
    log.write_text(result.stdout + result.stderr)
    log.chmod(0o600)
    matches = re.findall(r'(\d+) passed', result.stdout)
    passed = int(matches[-1]) if matches else 0
    unchanged = source_hashes(service) == before
    record = {'service': service, 'attempt': attempt, 'passed': passed,
              'exit_code': result.returncode, 'suites': SUITES[service], 'new_tests': NEW[service],
              'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(), 'network': 'none',
              'auth_or_model_or_database_doubles_in_unit_tests': True,
              'tested_runtime_source_sha256': before, 'runtime_source_unchanged_during_tests': unchanged,
              'cached_test_image': IMAGES[service], 'production_dependencies_changed': False}
    record_path.write_text(json.dumps(record, indent=2) + '\n')
    record_path.chmod(0o600)
    print(json.dumps({key: value for key, value in record.items() if key != 'tested_runtime_source_sha256'}))
    assert result.returncode == 0 and unchanged


if __name__ == '__main__':
    main(*sys.argv[1:])
