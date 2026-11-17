"""Read this batch's extracted package without serving or opening any connection."""
import hashlib
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parent
batch = sys.argv[1]
assert batch in {'01', '02'}, 'select this batch package number'
receipt = json.loads((EVIDENCE/f'package-{batch}.json').read_text())
archive = ROOT/receipt['archive']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['sha256']
extracted = ROOT/f'.local/http-candidate/streaming-20261115-01/extracted-{batch}'
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
    env[name] = f"postgresql+asyncpg://{role}:synthetic@127.0.0.1:1/{cfg['database']}"
code = '''
import json, socket, sys
from dataclasses import asdict
from pathlib import Path
def forbidden(*args, **kwargs):
    raise AssertionError('offline validation cannot open connections')
socket.socket.connect = forbidden
socket.create_connection = forbidden
import investigation_http.main as entry
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
    'started_services':0,'database_connections':0,'model_calls':0}))
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
