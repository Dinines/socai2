"""Read-only 21 repair preflight; only allowlisted metadata leaves the host."""
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REMOTE = r'''
import hashlib,json,subprocess,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
def command(args,body=None):
    p=subprocess.run(args,input=body,capture_output=True,check=False)
    if p.returncode: raise RuntimeError('read-only command failed: '+args[0])
    return p.stdout.decode().strip()
def inspect(name): return json.loads(command(['docker','inspect',name]))[0]
names=['socai2-next-api','socai2-api-1','socai2-investigation-api','socai2-fusion-1','socai2-agents-1']
containers={}
for name in names:
    row=inspect(name)
    containers[name]={'id':row['Id'],'image_id':row['Image'],'image_name':row['Config']['Image'],
        'started_at':row['State']['StartedAt'],'status':row['State']['Status'],
        'health':row['State'].get('Health',{}).get('Status')}
new=inspect(names[0])
env=dict(v.split('=',1) for v in new['Config'].get('Env',[]) if '=' in v)
allow=['SOCAI2_MODEL_PROTOCOL','SOCAI2_MODEL_SCHEMA_PROFILE','OPENAI_MODEL',
    'SOCAI2_SERVICE_DATABASE_NAME','SOCAI2_LAKE_DATABASE','CLICKHOUSE_DATABASE',
    'SOCAI2_CASE_API_ENABLED','SOCAI2_STAGE_EXECUTION_ENABLED']
config={k:env.get(k) for k in allow}
config['model_hostname']=urlsplit(env.get('OPENAI_BASE_URL','')).hostname
config['database_name']=urlsplit(env.get('DATABASE_URL','')).path.lstrip('/')
private=Path('/opt/sting-aisoc-socai2/private/next-20261104')
files={}
for name in ['identity.json','api.env','model.deepseek.env']:
    p=private/name
    files[name]={'exists':p.is_file(),'mode':oct(p.stat().st_mode&0o777) if p.is_file() else None}
query="""BEGIN READ ONLY;
SELECT json_build_object('database',current_database(),
 'freshness_function_present',to_regprocedure('socai2.baseline_input_freshness(uuid,uuid)') IS NOT NULL,
 'migration_125_recorded',EXISTS(SELECT 1 FROM public.aisoc_schema_migrations WHERE name='125_socai2_baseline_input_freshness.sql'),
 'socai2_tables',(SELECT count(*) FROM information_schema.tables WHERE table_schema='socai2' AND table_type='BASE TABLE'),
 'socai2_columns',(SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2'));
COMMIT;"""
db=json.loads(command(['docker','exec','-i','spirithub-postgres-1','psql','-X','-v','ON_ERROR_STOP=1',
    '-U','spirithub','-d','socai2_next_20261104','-A','-t','-q'],query.encode()))
source_code="""import hashlib,json,pathlib
names=['socai2/case_service.py','socai2/baseline_contracts.py','socai2/baseline_service.py','socai2/baseline_executor.py']
root=pathlib.Path('/app/app')
out={n:{'sha256':hashlib.sha256((root/n).read_bytes()).hexdigest()} for n in names}
out['case_start_contains_48000']='max_tokens=48000' in (root/names[0]).read_text()
print(json.dumps(out))"""
source=json.loads(command(['docker','exec','socai2-next-api','python','-c',source_code]))
health=json.loads(urllib.request.urlopen('http://127.0.0.1:18020/readyz',timeout=5).read())
openapi=json.loads(urllib.request.urlopen('http://127.0.0.1:18020/openapi.json',timeout=5).read())
image=inspect(new['Image'])
print(json.dumps({'containers':containers,'config':config,'private_files':files,'database':db,
 'runtime_sources':source,'readyz':health,'image_repo_digests':image.get('RepoDigests',[]),
 'case_collection_get_present':'get' in openapi['paths'].get('/api/v1/socai2/cases',{}),
 'compose_directory':new['Config'].get('Labels',{}).get('com.docker.compose.project.working_dir'),
 'credentials_exported':False,'mutations':0}))
'''


def main():
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
        "-o", "ConnectTimeout=8", "sting-infra21", "python3 -"], input=REMOTE.encode(),
        capture_output=True, timeout=50, check=False)
    if result.returncode:
        raise RuntimeError("read-only runtime probe failed; credentials and remote stderr suppressed")
    data = json.loads(result.stdout)
    data["probe_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    data["captured_at"] = datetime.now(UTC).isoformat()
    folder = ROOT / "docs/operations/evidence/investigation-repair-20261105"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (datetime.now(UTC).strftime("runtime-%Y%m%dT%H%M%S%fZ.json"))
    with path.open("x") as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(path)
    print(json.dumps({"database": data["database"], "config": data["config"],
        "image": data["containers"]["socai2-next-api"]["image_name"],
        "image_id": data["containers"]["socai2-next-api"]["image_id"],
        "case_collection_get_present": data["case_collection_get_present"], "mutations": 0}))


if __name__ == "__main__":
    main()
