"""Read this batch's extracted package without serving or opening any connection."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parent
batch = sys.argv[1]
assert batch == '01', 'select this batch package number'
receipt = json.loads((EVIDENCE/f'package-{batch}.json').read_text())
archive = ROOT/receipt['archive']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['sha256']
extracted = ROOT/f'.local/http-candidate/streaming-pg-password-20261115-01/extracted-{batch}'
extracted.mkdir(exist_ok=False)
with tarfile.open(archive) as bundle:
    bundle.extractall(extracted, filter='data')
manifest = json.loads((extracted/'manifest.json').read_text())
assert all(hashlib.sha256((extracted/n).read_bytes()).hexdigest() == h for n, h in manifest['files'].items())
cfg = json.loads((extracted/'profile.json').read_text())
env = {k: v.replace('/app/', str(extracted)+'/') if v.startswith('/app/') else v
       for k, v in cfg['environment'].items()}
env.update(PATH=os.environ.get('PATH', ''), PYTHONPATH=str(extracted),
    SOCAI2_SERVICE_DATABASE_NAME=cfg['database'], SOCAI2_HTTP_RELEASE=cfg['release'])
# Synthetic import-only URLs never leave this subprocess and are never published as a runtime profile.
for name, role in [('DATABASE_URL', 'reader'), ('SOCAI2_CASE_DATABASE_URL', 'writer')]:
    env[name] = f"postgresql+asyncpg://{role}:synthetic@{cfg['database_host']}:{cfg['database_port']}/{cfg['database']}"
spec = importlib.util.spec_from_file_location('packaged_release', extracted/'manage.py')
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)
with tempfile.TemporaryDirectory() as temporary:
    private = Path(temporary)/'import-only.json'
    private.write_text(json.dumps(env))
    checked, mounts = manager.explicit_runtime_inputs({**cfg, 'runtime_environment_file': str(private), 'environment': {}})
    assert mounts == [] and 'PGSSLROOTCERT' not in checked
    assert all('sslmode=require' in checked[n] for n in ('DATABASE_URL', 'SOCAI2_CASE_DATABASE_URL'))
    env = checked
# Deliberately invalid inherited CA proves shared require handling ignores it.
env['PGSSLROOTCERT'] = '/nonexistent/import-only/ca.crt'
code = '''
import json, socket, sys, ssl
from dataclasses import asdict
from pathlib import Path
def forbidden(*args, **kwargs):
    raise AssertionError('offline validation cannot open connections')
socket.socket.connect = forbidden
socket.create_connection = forbidden
import investigation_http.main as entry
from app.db import database, case_database
assert isinstance(database._connect_args['ssl'], ssl.SSLContext)
assert database._connect_args['ssl'].verify_mode == ssl.CERT_NONE
assert database._connect_args['ssl'].check_hostname is False
write_args = {}
real_create = case_database.create_async_engine
def capture_engine(*args, **kwargs):
    write_args.update(kwargs['connect_args'])
    return real_create(*args, **kwargs)
case_database.create_async_engine = capture_engine
case_database.get_case_write_sessions()
assert isinstance(write_args['ssl'], ssl.SSLContext)
assert write_args['ssl'].verify_mode == ssl.CERT_NONE and write_args['ssl'].check_hostname is False
from investigation_http.adapters.identity import load_context
from app.socai2 import subject_management, exploration_matching, exploration_state, alert_review, alert_hosts
from app.socai2.list_export import ExportLimits
from app.socai2.run_records import RunRecordLimits
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.case_allocation_policy import CaseAllocationPolicy
from app.socai2.runtime_policy import active_policy
root = Path.cwd()
modules = {n: str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if n.split('.')[0] in {'app', 'investigation_http'} and getattr(m, '__file__', None)}
assert all(Path(p).is_relative_to(root) for p in modules.values())
doc = entry.app.openapi()
expected = json.loads((root/'contract/openapi.json').read_text())
def contract(d): return {k:v for k,v in d.items() if k not in {'info','servers'}}
assert contract(doc) == contract(expected)
assert not doc.get('security') and not doc.get('components', {}).get('securitySchemes')
operations = sum(m in {'get','post','put','patch','delete'} for p,ms in doc['paths'].items()
                 if p.startswith('/api/v1/socai2/') for m in ms)
assert operations == 80
context = load_context()
policy = active_policy().require_execution_profiles()
print(json.dumps({'operations':operations,'auth':'none','loaded_modules':len(modules),
    'all_application_modules_from_extracted_package':True,'configured_database':entry.configured_database_name(),
    'release':doc['info']['version'],'context':{k:str(v) for k,v in asdict(context).items()},
    'policy_sha256':policy.sha256,'loaded_query_configs':{
        'max_batch_items':subject_management.batch_limit(),'export':asdict(ExportLimits.load()),
        'exploration_window_hours':exploration_matching.window_hours(),
        'exploration_state':exploration_state.limits(),'alert_review_days':alert_review.lookback_days(),
        'alert_host_limit':alert_hosts.display_limit(),'run_records':asdict(RunRecordLimits.load()),
        'analysis_tasks':asdict(AnalysisTaskPolicy.load()),'case_allocation':asdict(CaseAllocationPolicy.load())},
    'started_services':0,'database_connections':0,'model_calls':0,
    'ordinary_password_prepare':True,'extra_mounts':0,'sslmode':'require',
    'read_and_write_context_CERT_NONE':True,'invalid_inherited_CA_ignored':True}))
'''
run = subprocess.run([sys.executable, '-c', code], cwd=extracted, env=env,
                     text=True, capture_output=True, check=False)
(EVIDENCE/f'offline-{batch}.stdout.txt').write_text(run.stdout)
(EVIDENCE/f'offline-{batch}.stderr.txt').write_text(run.stderr)
assert run.returncode == 0, 'offline_import_failed_see_saved_output'
result = json.loads(run.stdout.strip().splitlines()[-1])
result.update(archive_sha256=receipt['sha256'], manifest_files=len(manifest['files']),
              runtime_ready=False, target_amd64_image_tested=False)
(EVIDENCE/f'offline-{batch}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(result, ensure_ascii=False))
