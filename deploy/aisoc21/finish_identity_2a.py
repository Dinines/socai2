"""Final bounded identity checks and cleanup of only the three marked API keys."""
from pathlib import Path
import hashlib,json,subprocess
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from shared_1b import SharedBatch
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2a-identity-20261020'
def main():
    out=E/'postconditions.json';assert not out.exists() and (E/'restart-verification.json').exists()
    before=json.loads((E/'environment-before.json').read_text());after=snapshot()
    for name,data in before['containers'].items():
        if name not in ['socai2-api-1','socai2-fusion-1']:assert after['containers'][name]==data,name
    assert set(after['containers'])==set(before['containers']) and after['volumes']==before['volumes']
    b=SharedBatch(R);rows=json.loads(b.pg('SET ROLE aisoc; SELECT json_agg(t) FROM ('+MATERIAL_SQL+') t;').stdout)
    current={r['id']:hashlib.sha256(r['material'].encode()).hexdigest() for r in rows};old=json.loads((E/'prior-alert-material.json').read_text())
    for r in old:assert current[r['id']]==r['sha256'],r['id']
    assert len(current)==len(old)+7
    assert b.pg('SELECT COUNT(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    source_checks={}
    code='''import json,hashlib,sys
from pathlib import Path
from packaging.requirements import Requirement
from importlib.metadata import version,PackageNotFoundError
checks=[]
for raw in Path('/requirements.txt').read_text().splitlines():
 line=raw.strip().removesuffix(chr(92)).strip()
 if not line or line.startswith(('#','--')):continue
 r=Requirement(line)
 if r.marker and not r.marker.evaluate():continue
 v=version(r.name);assert v in r.specifier;checks.append({'name':r.name,'version':v})
for name in ['pytest','poetry']:
 try:version(name);raise AssertionError(name+' unexpectedly in runtime')
 except PackageNotFoundError:pass
print(json.dumps({'python':sys.version.split()[0],'dependencies':checks,'app_hashes':{str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}}))'''
    for name in ['api','fusion']:
        runtime=json.loads(subprocess.check_output(['docker','exec','socai2-'+name+'-1','python','-c',code]));source=R/f'source/services/{name}/app';expected={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts};assert expected==runtime.pop('app_hashes')
        runtime['all_app_assets_match']=len(expected);source_checks[name]=runtime
    metricscode='''import json,urllib.request
from prometheus_client.parser import text_string_to_metric_families
with urllib.request.urlopen('http://127.0.0.1:4000/metrics') as r:text=r.read().decode()
counts={}
for f in text_string_to_metric_families(text):
 for s in f.samples:
  if s.name=='litellm_proxy_total_requests_metric_total' and s.labels.get('status_code')=='200':
   key=s.labels['requested_model'];counts[key]=counts.get(key,0)+s.value
print(json.dumps(counts))'''
    counts=json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',metricscode]));assert counts=={'aisoc-triage':1,'aisoc-recon':3,'aisoc-investigation':5,'aisoc-summary':1,'aisoc-report':3}
    lagtext=subprocess.check_output(['docker','exec','sting-infra21-kafka-1','kafka-consumer-groups','--bootstrap-server','192.168.1.21:9092','--describe','--group','socai2-fusion-consumer'],stderr=subprocess.DEVNULL).decode();parts=[x.split() for x in lagtext.splitlines() if 'socai2.alerts.raw' in x];assert len(parts)==3 and all(x[5]=='0' for x in parts)
    state=json.loads((R/'private/app-identity-2a.json').read_text())
    for i in state['identities'].values():b.pg("SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='"+i['key_id']+"' AND name LIKE 'socai2-2a-identity-20261020-%';")
    code='''import asyncio,json,httpx
from pathlib import Path
async def main():
 s=json.loads(Path('/private/state.json').read_text())
 async with httpx.AsyncClient(trust_env=False) as c:
  statuses={name:(await c.get('http://api:8000/api/v1/alerts/00000000-0000-0000-0000-000000000001',headers={'Authorization':'Bearer '+i['key']})).status_code for name,i in s['identities'].items()}
 assert set(statuses.values())=={401};print(json.dumps(statuses))
asyncio.run(main())'''
    statuses=json.loads(subprocess.check_output(['docker','run','--rm','--network','socai2_default','-v',str(R/'private/app-identity-2a.json')+':/private/state.json:ro','socai2-api:identity-2a-20261020','python','-c',code]))
    data={'other_existing_containers_unchanged':len(before['containers'])-2,'only_recreated_services':['fusion','api'],'volume_names_preserved':len(after['volumes']),'prior_immutable_alert_material_rows_unchanged':len(old),'new_alert_rows':7,'total_alert_rows':len(current),'schema_migrations_count_unchanged':134,'runtime':source_checks,'gateway_success_counters_unchanged':counts,'fusion_partition_lags':[int(x[5]) for x in parts],'fixture_key_http_status':statuses,'test_keys_deactivated':3,'original_databases_and_volumes_not_cleared':True}
    out.write_text(json.dumps(data,indent=2));print(json.dumps({k:v for k,v in data.items() if k!='runtime'}))
if __name__=='__main__':main()
