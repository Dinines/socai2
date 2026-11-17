"""One before/after read of the existing production Case; no model or write."""
import argparse
import json
import shlex
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
INNER = r'''
import asyncio, hashlib, json
from uuid import UUID
from sqlalchemy import text
from app.db.case_database import get_case_write_sessions, close_case_database
from app.socai2.case_service import CaseService
def encode(value):
    if hasattr(value, 'model_dump'): return value.model_dump(mode='json')
    return str(value)
def digest(value):
    return hashlib.sha256(json.dumps(value, default=encode, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
async def main():
    tenant, case = UUID(CONFIG['tenant_id']), UUID(CONFIG['existing_case_id'])
    svc = CaseService(get_case_write_sessions())
    detail = await svc.read_case(tenant, case)
    async with svc.transaction(tenant, readonly=True) as store:
        ids = (await store.db.execute(text('SELECT id FROM socai2.results WHERE tenant_id=:tenant AND case_id=:case ORDER BY id'), {'tenant':tenant,'case':case})).scalars().all()
        rows = {}
        for name in ('cases','runs','results','case_assessments'):
            key = 'id' if name == 'cases' else 'case_id'
            values = (await store.db.execute(text(f'SELECT to_jsonb(t) FROM socai2.{name} t WHERE tenant_id=:tenant AND {key}=:case ORDER BY id'), {'tenant':tenant,'case':case})).scalars().all()
            rows[name] = {'count':len(values),'sha256':digest(values)}
        active = (await store.db.execute(text("SELECT id FROM socai2.runs WHERE tenant_id=:tenant AND state='running' AND started_at>=CAST(CAST(:started AS text) AS timestamptz)"), {'tenant':tenant,'started':CONFIG['container_started_at']})).scalars().all()
    results = {}
    for result_id in ids:
        value = await svc.read_result(tenant, case, result_id)
        results[str(result_id)] = {'sha256':digest(value),'keys':sorted(value)}
    current = detail['current_assessment']
    output = {'case_id':str(case),'case_read_sha256':digest(detail),'current_assessment_id':str(detail['case'].current_assessment_id) if detail['case'].current_assessment_id else None,
      'assessment_read_sha256':digest(current),'results':results,'saved_rows':rows,
      'active_runs_since_previous_container_start':[str(x) for x in active],
      'model_calls':0,'business_writes':0,'read_path':'CaseService inside running core API / real aisoc PostgreSQL; not authenticated TCP business HTTP'}
    await close_case_database()
    return output
print(json.dumps(asyncio.run(main())))
'''
REMOTE = r'''
import hashlib,json,os,subprocess,sys,urllib.request
cfg=json.load(sys.stdin)
def inspect(name): return json.loads(subprocess.check_output(['docker','inspect',name]))[0]
core=inspect(cfg['container'])
assert core['Image']==cfg['expected_image'],'core_image_changed'
code='CONFIG='+repr(cfg)+'\n'+cfg['inner']
p=subprocess.run(['docker','exec','-i',cfg['container'],'python','-B','-'],input=code.encode(),capture_output=True)
if p.returncode:
    print(json.dumps({'error':'business_readback_failed','returncode':p.returncode}));sys.exit(1)
data=json.loads(p.stdout)
with urllib.request.urlopen(cfg['endpoint']+'/health',timeout=10) as response: status=response.status
preserved={}
for name in cfg['preserved_services']:
    row=inspect(name)
    preserved[name]={'id':row['Id'],'image':row['Image'],'started_at':row['State']['StartedAt'],'mounts':row['Mounts'],'compose':row['Config']['Labels'].get('com.docker.compose.project.config_files')}
    if name=='socai2-agents-1':preserved[name]['consumer_disabled']=next((x.split('=',1)[1] for x in row['Config']['Env'] if x.startswith('AISOC_AGENT_KAFKA_DISABLE=')),None)
print(json.dumps({'readback':data,'http_health':status,'core':{'id':core['Id'],'image':core['Image'],'started_at':core['State']['StartedAt'],'health':core['State'].get('Health',{}).get('Status')},'preserved_services':preserved,'current_pointer':os.path.realpath(cfg['current_pointer'])}))
'''

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("phase", choices=("before", "after"))
args = parser.parse_args()
cfg = json.loads((HERE / "config.json").read_text())
baseline = json.loads((HERE / "preflight-05.json").read_text())
cfg["container_started_at"] = baseline["container"]["started_at"]
cfg["expected_image"] = cfg["expected_base_image"]
if args.phase == "after":
    builds = sorted(HERE.glob("unified-build-*.json"))
    cfg["expected_image"] = json.loads(json.loads(builds[-1].read_text())["stdout"])["images"]["api"]["id"]
cfg["inner"] = INNER
cmd = [cfg["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={cfg['connect_timeout_seconds']}",
       cfg["ssh_target"], shlex.join(["python3", "-c", REMOTE])]
completed = subprocess.run(cmd, input=json.dumps(cfg).encode(), capture_output=True, timeout=cfg["command_timeout_seconds"])
output = json.loads(completed.stdout) if completed.stdout else {"error":"transport_failed","returncode":completed.returncode}
with (HERE / f"readback-{args.phase}.json").open("x") as stream:
    json.dump(output, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
assert completed.returncode == 0, "Readback failed; receipt retained."
assert output["http_health"] == 200
assert output["preserved_services"] == baseline["preserved_services"], "Preserved service changed."
assert not output["readback"]["active_runs_since_previous_container_start"]
if args.phase == "after":
    before = json.loads((HERE / "readback-before.json").read_text())
    assert output["readback"] == before["readback"], "Existing Case readback changed."
print(json.dumps({"phase":args.phase,"health":output["http_health"],"image":output["core"]["image"],
                  "results_read":len(output["readback"]["results"]),"saved_rows":output["readback"]["saved_rows"],
                  "preserved_services":len(output["preserved_services"]),"model_calls":0,"business_writes":0}))
