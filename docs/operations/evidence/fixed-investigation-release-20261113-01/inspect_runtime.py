"""Read current deployment metadata and code hashes; never prints credentials."""
import json
import shlex
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE / "config.json").read_text())
inner = r'''
import asyncio,hashlib,json,os
from pathlib import Path
from app.socai2.runtime_policy import active_policy
from app.db.case_database import get_case_write_sessions
from sqlalchemy import text
p=active_policy()
async def status():
    async with get_case_write_sessions()() as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"),{'tenant':CONFIG['tenant_id']})
        database=(await db.execute(text('SELECT current_database()'))).scalar_one()
        recent=(await db.execute(text("SELECT id,kind,state,started_at FROM socai2.runs WHERE tenant_id=CAST(:tenant AS uuid) AND state='running' AND started_at>=CAST(CAST(:started AS text) AS timestamptz)"),{'tenant':CONFIG['tenant_id'],'started':CONFIG['container_started_at']})).mappings().all()
        return {'database':database,'runs_active_since_container_start':[dict(r) for r in recent]}
root=Path(CONFIG['application_root'])
policy_path=Path(os.environ['SOCAI2_INVESTIGATION_POLICY'])
data={'files':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(CONFIG['source_root']).rglob('*') if p.is_file() and p.suffix in {'.py','.json','.sql'}},
 'policy_path':str(policy_path),'policy_sha256':hashlib.sha256(policy_path.read_bytes()).hexdigest(),
 'policy':{'alert_max_calls':p.alert_basic.max_model_calls,'incident_max_calls':p.incident_diagnosis.max_model_calls,'case_max_calls':p.case.max_model_calls,'case_total_tokens':p.case.max_total_tokens,'model_alias':p.model.alias,'case_io':p.case_io.identity if p.case_io else None},
 'flags':{k:os.environ.get(k) for k in ('SOCAI2_CASE_API_ENABLED','SOCAI2_STAGE_EXECUTION_ENABLED','SOCAI2_HTTP_RELEASE','SOCAI2_KNOWLEDGE_PROFILE')},'database':asyncio.run(status())}
print(json.dumps(data,default=str))
'''
remote = r'''
import json,os,subprocess,sys,urllib.request
cfg=json.load(sys.stdin)
current=json.loads(subprocess.check_output(['docker','inspect',cfg['container']]))[0]
assert current['Image']==cfg['expected_base_image'],'runtime_base_changed'
contract=None
if cfg.get('contract_path'):
    with urllib.request.urlopen(cfg['endpoint']+cfg['contract_path'],timeout=10) as response:contract=json.load(response)
    if cfg['expected_base_release'] is not None:assert contract['info']['version']==cfg['expected_base_release'],'runtime_release_changed'
cfg['container_started_at']=current['State']['StartedAt']
guard="""import traceback
try:
    exec(compile(SOURCE, '<runtime_probe>', 'exec'))
except Exception as exc:
    print(json.dumps({'error_type':type(exc).__name__,'code':getattr(exc,'code',None),
      'attribute':getattr(exc,'name',None),'frames':[{'file':f.filename,'line':f.lineno} for f in traceback.extract_tb(exc.__traceback__)]}))
    raise SystemExit(1)
"""
code='import json\nCONFIG='+repr(cfg)+'\nSOURCE='+repr(cfg['inner'])+'\n'+guard
result=subprocess.run(['docker','exec','-i',cfg['container'],'python','-'],input=code.encode(),capture_output=True)
if result.returncode:
    print(json.dumps({'error':'runtime_probe_failed','returncode':result.returncode,
                      'diagnostic':json.loads(result.stdout) if result.stdout else None}));sys.exit(1)
preserved={}
for name in cfg['preserved_services']:
    row=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    preserved[name]={'id':row['Id'],'image':row['Image'],'started_at':row['State']['StartedAt'],'mounts':row['Mounts'],'compose':row['Config']['Labels'].get('com.docker.compose.project.config_files')}
    if name=='socai2-agents-1':preserved[name]['consumer_disabled']=next((x.split('=',1)[1] for x in row['Config']['Env'] if x.startswith('AISOC_AGENT_KAFKA_DISABLE=')),None)
print(json.dumps({'container':{'name':cfg['container'],'id':current['Id'],'image':current['Image'],'started_at':current['State']['StartedAt'],'mounts':current['Mounts'],'compose':current['Config']['Labels'].get('com.docker.compose.project.config_files')},'runtime':json.loads(result.stdout),'contract':contract,'preserved_services':preserved,'current_pointer':os.path.realpath(cfg['current_pointer'])}))
'''
args = [cfg["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={cfg['connect_timeout_seconds']}",
        cfg["ssh_target"], shlex.join(["python3", "-c", remote])]
result = subprocess.run(args, input=json.dumps({**cfg, "inner": inner}).encode(), capture_output=True,
                        timeout=cfg["command_timeout_seconds"])
with (HERE / "preflight-05.json").open("x") as stream:
    stream.write(result.stdout.decode() if result.stdout else json.dumps({"transport_returncode": result.returncode}))
if result.returncode:
    raise SystemExit("Read-only preflight failed; no runtime change.")
data = json.loads(result.stdout)
print(json.dumps({"release":data["contract"]["info"]["version"] if data["contract"] else "core_production_openapi_disabled","image":data["container"]["image"],
                  "runtime_source_files":len(data["runtime"]["files"]),"policy":data["runtime"]["policy"],
                  "database":data["runtime"]["database"]},ensure_ascii=False))
