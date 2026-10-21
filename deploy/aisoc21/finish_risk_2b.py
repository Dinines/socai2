"""Read back risks/materials after a targeted Fusion restart; revoke fixtures."""
from pathlib import Path
import hashlib,json,subprocess,time
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from shared_1b import SharedBatch
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2b-risk-20261020'
RUNTIME_CODE='''import asyncio,hashlib,json,sys,urllib.request,urllib.error
from pathlib import Path
from packaging.requirements import Requirement
from importlib.metadata import version,PackageNotFoundError
import redis.asyncio as redis
from app.core.config import settings
from app.security.tenant_scope import resolve_service_token
tenant=sys.argv[1]
checks=[]
for raw in Path('/requirements.txt').read_text().splitlines():
 line=raw.strip().removesuffix(chr(92)).strip()
 if not line or line.startswith(('#','--')):continue
 r=Requirement(line)
 if r.marker and not r.marker.evaluate():continue
 v=version(r.name);assert v in r.specifier;checks.append({'name':r.name,'version':v})
for name in ['pytest','poetry']:
 try:version(name);raise AssertionError(name+' in runtime')
 except PackageNotFoundError:pass
req=urllib.request.Request('http://127.0.0.1:8003/ml/status',headers={'Authorization':'Bearer '+resolve_service_token(),'X-AiSOC-Tenant-ID':tenant})
try:
 with urllib.request.urlopen(req,timeout=10) as f:ml={'http_status':f.status,'body':json.load(f)}
except urllib.error.HTTPError as exc:
 ml={'http_status':exc.code,'body':json.load(exc),'training_state_observed':False}
cfg={k:v for k,v in settings.model_dump().items() if k.startswith('rba_')}
async def risk():
 c=redis.from_url(settings.redis_url,decode_responses=True)
 try:return {name:await c.hgetall('aisoc:fusion:rba:entity:'+tenant+':user:'+name) for name in ['socai2-risk-before','socai2-risk-after','socai2-risk-direct']}
 finally:await c.aclose()
print(json.dumps({'python':sys.version.split()[0],'dependencies':checks,'app_hashes':{str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts},'rba_config':cfg,'rba_config_sha256':hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),'ml_live_status':ml,'risk_hashes':asyncio.run(risk())}))'''
READ_CODE='''import asyncio,hashlib,json,httpx
from pathlib import Path
async def main():
 s=json.loads(Path('/private/state.json').read_text())['identities'];checks=[]
 async with httpx.AsyncClient(trust_env=False,timeout=20) as c:
  for name,identity in [('before-first','a'),('after-first','a'),('after-tenant-b','b')]:
   old=json.loads(Path('/evidence/main/'+name+'-result.json').read_text());i=s[identity]
   r=await c.get('http://api:8000/api/v1/alerts/'+old['receipt']['canonical_alert_id'],headers={'Authorization':'Bearer '+i['key']});assert r.status_code==200
   v=r.json();assert v['raw_event']==old['api']['raw_event'] and v['fusion_incident_id']==old['api']['fusion_incident_id'] and v['event_time']==old['api']['event_time']
   checks.append({'id':v['id'],'status':r.status_code,'raw_event_and_incident_and_time_unchanged':True})
 print(json.dumps(checks))
asyncio.run(main())'''
REVOKED_CODE='''import asyncio,json,httpx
from pathlib import Path
async def main():
 s=json.loads(Path('/private/state.json').read_text())['identities']
 async with httpx.AsyncClient(trust_env=False) as c:
  statuses={n:(await c.get('http://api:8000/api/v1/alerts/00000000-0000-0000-0000-000000000001',headers={'Authorization':'Bearer '+i['key']})).status_code for n,i in s.items()}
 assert set(statuses.values())=={401};print(json.dumps(statuses))
asyncio.run(main())'''
def save(n,v):
    with (E/n).open('x') as f:json.dump(v,f,indent=2)
def inspect():return json.loads(subprocess.check_output(['docker','inspect','socai2-fusion-1']))[0]
def probe(code):
    return json.loads(subprocess.check_output(['docker','run','--rm','--network','socai2_default','-v',str(R/'private/app-risk-2b.json')+':/private/state.json:ro','-v',str(E)+':/evidence:ro','socai2-api:identity-2a-20261020','python','-c',code]))
def runtime(tenant):
    v=json.loads(subprocess.check_output(['docker','exec','socai2-fusion-1','python','-c',RUNTIME_CODE,tenant]))
    source=R/'source/services/fusion/app';expected={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert expected==v.pop('app_hashes');v['app_files_matched']=len(expected);return v
def main():
    assert not (E/'restart-before.json').exists(),'No blind restart/replay; inspect journal'
    assert json.loads((E/'main/after-acceptance.json').read_text())['risk_replay_unchanged']
    state=json.loads((R/'private/app-risk-2b.json').read_text());tenant=state['identities']['a']['tenant_id']
    live=inspect();before=runtime(tenant);save('runtime-before-restart.json',before)
    save('restart-before.json',{'container_id':live['Id'],'image':live['Image'],'started_at':live['State']['StartedAt']})
    subprocess.run(['docker','restart','socai2-fusion-1'],check=True,capture_output=True)
    for _ in range(45):
        after=inspect()
        if after['State'].get('Health',{}).get('Status')=='healthy':break
        time.sleep(1)
    else:raise RuntimeError('Unhealthy after restart')
    assert live['Id']==after['Id'] and live['Image']==after['Image'] and live['Mounts']==after['Mounts']
    now=runtime(tenant);assert now['risk_hashes']==before['risk_hashes'] and now['rba_config_sha256']==before['rba_config_sha256']
    save('runtime-after-restart.json',now);save('restart-api-readback.json',probe(READ_CODE))
    b=SharedBatch(R);rows=json.loads(b.pg('SET ROLE aisoc; SELECT json_agg(t) FROM ('+MATERIAL_SQL+') t;').stdout)
    current={r['id']:hashlib.sha256(r['material'].encode()).hexdigest() for r in rows};old=json.loads((E/'prior-alert-material.json').read_text())
    for r in old:assert current[r['id']]==r['sha256'],r['id']
    assert len(current)==len(old)+3 and b.pg('SELECT COUNT(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    start=json.loads((E/'environment-before.json').read_text());end=snapshot()
    for name,data in start['containers'].items():
        if name!='socai2-fusion-1':assert end['containers'][name]==data,name
    assert set(start['containers'])==set(end['containers']) and start['volumes']==end['volumes']
    metrics='''import json,urllib.request
from prometheus_client.parser import text_string_to_metric_families
with urllib.request.urlopen('http://127.0.0.1:4000/metrics') as f:v=f.read().decode()
counts={}
for family in text_string_to_metric_families(v):
 for s in family.samples:
  if s.name=='litellm_proxy_total_requests_metric_total' and s.labels.get('status_code')=='200':
   k=s.labels['requested_model'];counts[k]=counts.get(k,0)+s.value
print(json.dumps(counts))'''
    counts=json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',metrics]));assert counts=={'aisoc-triage':1,'aisoc-recon':3,'aisoc-investigation':5,'aisoc-summary':1,'aisoc-report':3}
    lag=subprocess.check_output(['docker','exec','sting-infra21-kafka-1','kafka-consumer-groups','--bootstrap-server','192.168.1.21:9092','--describe','--group','socai2-fusion-consumer'],stderr=subprocess.DEVNULL).decode();parts=[x.split() for x in lag.splitlines() if 'socai2.alerts.raw' in x];assert len(parts)==3 and all(x[5]=='0' for x in parts)
    for i in state['identities'].values():b.pg("SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='"+i['key_id']+"' AND name LIKE 'socai2-2b-risk-20261020-%';")
    result={'other_existing_containers_unchanged':len(start['containers'])-1,'only_recreated_and_restarted':['fusion'],'volume_names_preserved':len(end['volumes']),'old_alert_material_rows_unchanged':len(old),'new_alert_rows':3,'total_alert_rows':len(current),'migration_count_unchanged':134,'gateway_success_counters_unchanged':counts,'fusion_partition_lags':[int(x[5]) for x in parts],'fixture_key_http_status':probe(REVOKED_CODE),'test_keys_deactivated':2,'risk_hashes_and_config_unchanged_after_restart':True,'image':after['Image'],'runtime_source_and_locked_dependencies_matched':True}
    save('environment-after.json',end);save('postconditions.json',result);print(json.dumps(result))
if __name__=='__main__':main()
