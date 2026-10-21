"""Read-only final2A runtime/source/fixture checks, after targeted key cleanup."""
import hashlib,json,subprocess
from pathlib import Path
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2a-20261020'

def main():
    out=E/'verification.json';assert not out.exists()
    code='''import asyncio,hashlib,json,os,uuid
from pathlib import Path
from importlib.metadata import version
from packaging.requirements import Requirement
import asyncpg,httpx
async def main():
 state=json.loads(Path('/private/app-2a.json').read_text())
 original=json.loads(Path('/evidence/acceptance.json').read_text());db=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'))
 # Frozen original row material remains exactly as observed before the fix.
 for old in original['final_pg_rows']:
  row=await db.fetchrow('SELECT id,tenant_id,title,source_event_ids,event_time,external_id,raw_event FROM alerts WHERE id=$1',uuid.UUID(old['id']))
  actual=json.loads(json.dumps(dict(row),default=str));assert actual==old
 async with httpx.AsyncClient(trust_env=False) as client:
  statuses={name:(await client.get('http://api:8000/api/v1/alerts/'+original['final_pg_rows'][0]['id'],headers={'Authorization':'Bearer '+item['key']})).status_code for name,item in state['identities'].items()}
 assert set(statuses.values())=={401}
 print(json.dumps({'original_pg_rows_unchanged':len(original['final_pg_rows']),'deactivated_api_keys_actual_http_status':statuses}));await db.close()
asyncio.run(main())'''
    cmd=['docker','run','--rm','--network','socai2_default','--env-file',str(R/'private/fusion-1f.env'),'-v',str(R/'private/app-2a.json')+':/private/app-2a.json:ro','-v',str(R/'certificates/socai2-ca.crt')+':/run/certs/ca.crt:ro','-v',str(E)+':/evidence:ro','socai2-api:1f-20261020','python','-c',code]
    result=json.loads(subprocess.check_output(cmd))
    code='''from pathlib import Path
import hashlib,json,sys
from importlib.metadata import version,PackageNotFoundError
from packaging.requirements import Requirement
checks=[]
for raw in Path('/requirements.txt').read_text().splitlines():
 line=raw.strip().removesuffix(chr(92)).strip()
 if not line or line.startswith(('#','--')):continue
 req=Requirement(line)
 if req.marker is not None and not req.marker.evaluate():continue
 actual=version(req.name);assert actual in req.specifier;checks.append({'name':req.name,'version':actual})
try:version('pytest');pytest_present=True
except PackageNotFoundError:pytest_present=False
print(json.dumps({'python':sys.version.split()[0],'dependencies':checks,'pytest_in_runtime':pytest_present,'app_hashes':{str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}}))'''
    runtime=json.loads(subprocess.check_output(['docker','exec','socai2-fusion-1','python','-c',code]))
    source=R/'source/services/fusion/app';expected={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts};assert expected==runtime.pop('app_hashes')
    assert not runtime['pytest_in_runtime'];runtime['source_app_files_match']=len(expected);result['fusion_runtime']=runtime
    # Reuse1E's safe metrics selector, without writing its immutable receipts.
    code='''import json,urllib.request
from prometheus_client.parser import text_string_to_metric_families
with urllib.request.urlopen('http://127.0.0.1:4000/metrics') as r:t=r.read().decode()
counts={}
for f in text_string_to_metric_families(t):
 for s in f.samples:
  if s.name=='litellm_proxy_total_requests_metric_total' and s.labels.get('status_code')=='200':
   role=s.labels['requested_model'];counts[role]=counts.get(role,0)+s.value
print(json.dumps(counts))'''
    metrics=json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',code]));assert metrics=={'aisoc-triage':1,'aisoc-recon':3,'aisoc-investigation':5,'aisoc-summary':1,'aisoc-report':3}
    result['gateway_success_counters_unchanged_since_1g']=metrics
    out.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='fusion_runtime'}))
if __name__=='__main__':main()
