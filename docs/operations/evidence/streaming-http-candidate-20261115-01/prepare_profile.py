"""Prepare this batch's public profile only. Does not provision or start anything."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location('release', ROOT/'deploy/http-service/manage.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
out = ROOT/'deploy/http-service/streaming-20261115-01'
out.mkdir(exist_ok=True)
identity = json.loads((ROOT/'deploy/aisoc21/streaming-candidate-20261115-01/identity.json').read_text())
context = {k: identity[k] for k in ('tenant_id', 'actor_id', 'actor_name')}
(out/'context.json').write_text(json.dumps(context, indent=2)+'\n')
complete = {'services/api/app': 'app', 'services/api/investigation_http': 'investigation_http'}
patches = {str(p.relative_to(ROOT)): str(Path(target)/p.relative_to(ROOT/source))
           for source, target in complete.items() for p in release.package_sources(ROOT/source)}
patches.update({
    'deploy/http-service/run-records.json': 'config/run-records.json',
    'deploy/local-investigation/analysis-tasks.json': 'config/analysis-tasks.json',
    'deploy/local-investigation/case-allocation.json': 'config/case-allocation.json',
    'deploy/local-investigation/investigation-policy-case-v1.toml': 'config/investigation-policy.toml',
    'deploy/http-service/streaming-20261115-01/context.json': 'config/context.json',
    'docs/operations/evidence/case-update-http-20261115-01/candidate-openapi.json': 'contract/openapi.json',
    'services/api/pyproject.toml': 'pyproject.toml', 'services/api/poetry.lock': 'poetry.lock',
})
core_manifest = ROOT/'.local/processing-release/processing-20261115-r1/manifest.json'
core = json.loads(core_manifest.read_text())
shared = {src: core['files'][dst]['sha256'] for src, dst in patches.items()
          if dst.startswith('app/') and dst in core['files']}
assert all(release.sha(ROOT/src) == h for src, h in shared.items()), 'core_source_differs'
freeze = json.loads((ROOT/'docs/operations/evidence/execution-contract-fix-20261115-01/http-source-freeze.json').read_text())
assert all(release.sha(ROOT/src) == h for src, h in freeze['http_package_source'].items()), 'HTTP_source_differs'
env = {
    'ENVIRONMENT': 'test', 'DEBUG': 'false', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': '/app',
    'SOCAI2_CASE_API_ENABLED': 'true', 'SOCAI2_PAGE_READ_ENABLED': 'true',
    'SOCAI2_ANALYSIS_READ_ENABLED': 'true', 'SOCAI2_STAGE_EXECUTION_ENABLED': 'false',
    'AISOC_STARTUP_SCHEMA_MIGRATIONS': 'false', 'AISOC_DEV_AUTH_BYPASS': 'false',
    'SOCAI2_HTTP_CONTEXT_FILE': '/app/config/context.json',
    'SOCAI2_RUN_RECORDS_CONFIG_FILE': '/app/config/run-records.json',
    'SOCAI2_ANALYSIS_TASKS_CONFIG_FILE': '/app/config/analysis-tasks.json',
    'SOCAI2_CASE_ALLOCATION_CONFIG_FILE': '/app/config/case-allocation.json',
    'SOCAI2_INVESTIGATION_POLICY': '/app/config/investigation-policy.toml',
    'DATABASE_POOL_SIZE': '5', 'DATABASE_MAX_OVERFLOW': '5', 'DATABASE_POOL_RECYCLE_SECONDS': '300',
    'PGSSLROOTCERT': '/run/certs/ca.crt',
    'AISOC_CORS_ORIGINS': 'http://192.168.1.21:18480,http://127.0.0.1:18081',
}
for key, name in {
    'MANAGEMENT': 'subject_management.json', 'EXPORT': 'list_export.json',
    'EXPLORATION': 'exploration-query.json', 'EXPLORATION_STATE': 'exploration-state.json',
    'ALERT_REVIEW': 'alert-review-query.json', 'ALERT_HOST': 'alert-host-query.json',
}.items():
    env['SOCAI2_'+key+'_CONFIG_FILE'] = '/app/app/socai2/'+name
cfg = {
    'version': 'socai2.http-service.v1', 'release': 'streaming-http-20261115-r1',
    'root': identity['root']+'/http', 'reference_container': 'socai2-http-api',
    'base_image': 'sha256:d60231607c5eef22a7f4c9edc570f27d4856a441fbef3ea713ac6fab2475425e',
    'base_tag': 'socai2-http-base:streaming-d60231607c5e', 'buildkit': False,
    'image': 'socai2-http-api:streaming-http-20261115-r1',
    'container': identity['http']['container'], 'project': identity['http']['project'],
    'platform': identity['platform'], 'network': identity['network'],
    'bind': identity['http']['host'], 'port': identity['http']['port'], 'container_port': 8000,
    'database': identity['postgres']['database'], 'database_host': identity['postgres']['host'],
    'database_port': identity['postgres']['port'], 'entry': 'investigation_http.main:app',
    'memory': '2g', 'tmpfs': '/tmp:rw,nosuid,nodev,size=128m,mode=1777',
    'build_timeout_seconds': 300, 'startup_timeout_seconds': 50, 'environment': env,
    'runtime_environment_file': identity['root']+'/private/http-runtime.json',
    'runtime_mounts': [{'source': identity['postgres']['ca_file'], 'target': identity['postgres']['ca_mount'],
                        'sha256': None}],
    'source_root': '.', 'complete_packages': complete, 'patches': patches,
    'expected_source_hashes': {src: release.sha(ROOT/src) for src in patches},
    'expected_openapi_file': 'contract/openapi.json', 'expected_operations': 80, 'replace_existing': False,
}
(out/'profile.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=2)+'\n')
requirements = {
    'state': 'offline_candidate_not_runtime_ready',
    'identity_file': 'deploy/aisoc21/streaming-candidate-20261115-01/identity.json',
    'core_release': core['release'], 'core_manifest_sha256': release.sha(core_manifest),
    'shared_core_files': len(shared), 'frozen_http_files': len(freeze['http_package_source']),
    'extra_app_files': [src for src, dst in patches.items() if dst.startswith('app/') and dst not in core['files']],
    'runtime_environment_required_keys': ['DATABASE_URL', 'SOCAI2_CASE_DATABASE_URL'],
    'postgres': identity['postgres'],
    'missing': ['candidate database, migrations and tenant/actor provisioning',
                'real private reader/writer URLs at runtime_environment_file',
                'confirmed CA source sha256 in runtime_mounts; null deliberately refuses prepare',
                'target amd64 image/dependency and actual TCP validation'],
    'no_runtime_services_started': True,
}
(out/'requirements.json').write_text(json.dumps(requirements, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'profile': str(out/'profile.json'), 'source_files': len(patches),
                  'shared_core_files': len(shared), 'frozen_http_files': len(freeze['http_package_source'])}))
