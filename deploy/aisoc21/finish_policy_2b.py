"""Restart only API/Agents; verify stored rules/materials, then revoke keys."""
from pathlib import Path
import hashlib,json,subprocess,time
from prepare_2a import snapshot
from prepare_policy_2b import R,E,POLICY_SQL
from prepare_identity_2a import MATERIAL_SQL
from shared_1b import SharedBatch
RUNTIME='''import hashlib,json,sys
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
 try:version(name);raise AssertionError(name+' in runtime')
 except PackageNotFoundError:pass
data={'python':sys.version.split()[0],'dependencies':checks,'app_hashes':{str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}}
if sys.argv[1]=='agents':
 from app.workers.fused_alert_consumer import worker_enabled
 data['automatic_kafka_worker_enabled']=worker_enabled();assert not worker_enabled()
print(json.dumps(data))'''
def save(n,v):
    with (E/n).open('x') as f:json.dump(v,f,indent=2)
def inspect(n):return json.loads(subprocess.check_output(['docker','inspect','socai2-'+n+'-1']))[0]
def runtime(n):
    v=json.loads(subprocess.check_output(['docker','exec','socai2-'+n+'-1','python','-c',RUNTIME,n]));root=R/f'source/services/{n}/app'
    assert v.pop('app_hashes')=={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    v['all_runtime_app_files_match_source']=True;return v
def main():
    assert not (E/'restart-before.json').exists(),'No repeat restart; inspect journal'
    assert (E/'after-acceptance.json').exists()
    before={n:inspect(n) for n in ['api','agents']};save('runtime-before-restart.json',{n:runtime(n) for n in before})
    save('restart-before.json',{n:{'id':x['Id'],'image':x['Image'],'started_at':x['State']['StartedAt']} for n,x in before.items()})
    for n in ['api','agents']:
        subprocess.run(['docker','restart','socai2-'+n+'-1'],check=True,capture_output=True)
        for _ in range(45):
            x=inspect(n)
            if x['State'].get('Health',{}).get('Status')=='healthy':break
            time.sleep(1)
        else:raise RuntimeError('Unhealthy '+n)
        assert x['Id']==before[n]['Id'] and x['Image']==before[n]['Image'] and x['Mounts']==before[n]['Mounts']
    probe=['docker','run','--rm','--network','socai2_default','--env-file',str(R/'private/agents-1g.env'),'-v',str(R/'private/app-policy-2b.json')+':/private/state.json:ro','-v',str(E)+':/evidence','-v',str(R/'source/deploy/aisoc21/acceptance_policy_2b.py')+':/probe.py:ro','-v',str(R/'certificates/socai2-ca.crt')+':/run/certs/ca.crt:ro','socai2-agents:policy-2b-20261020','python','/probe.py','restart']
    subprocess.run(probe,check=True)
    b=SharedBatch(R);counts={}
    for file,sql,col,added in [('prior-alert-material.json',MATERIAL_SQL,'id',3),('prior-policy-material.json',POLICY_SQL,'tenant_id',1)]:
        rows=json.loads(b.pg('SET ROLE aisoc; SELECT COALESCE(json_agg(t),\'[]\'::json) FROM ('+sql+') t;').stdout)
        now={x[col]:hashlib.sha256(x['material'].encode()).hexdigest() for x in rows};old=json.loads((E/file).read_text())
        for x in old:assert now[x['id']]==x['sha256']
        assert len(now)==len(old)+added;counts[file]={'old_preserved':len(old),'added':added,'total':len(now)}
    assert b.pg('SELECT COUNT(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    start=json.loads((E/'environment-before.json').read_text());end=snapshot()
    for n,x in start['containers'].items():
        if n not in ['socai2-api-1','socai2-agents-1']:assert end['containers'][n]==x,n
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
    model=json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',metrics]));assert model=={'aisoc-triage':1,'aisoc-recon':3,'aisoc-investigation':5,'aisoc-summary':1,'aisoc-report':3}
    state=json.loads((R/'private/app-policy-2b.json').read_text())
    for i in state['identities'].values():b.pg("SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='"+i['key_id']+"' AND name LIKE 'socai2-2b-policy-20261020-%';")
    code='''import asyncio,json,httpx
from pathlib import Path
async def main():
 s=json.loads(Path('/private/state.json').read_text())['identities']
 async with httpx.AsyncClient(trust_env=False) as c:
  statuses={n:(await c.get('http://api:8000/api/v1/business-context/rules',headers={'Authorization':'Bearer '+i['key']})).status_code for n,i in s.items()}
 assert set(statuses.values())=={401};print(json.dumps(statuses))
asyncio.run(main())'''
    statuses=json.loads(subprocess.check_output(['docker','run','--rm','--network','socai2_default','-v',str(R/'private/app-policy-2b.json')+':/private/state.json:ro','socai2-api:policy-2b-20261020','python','-c',code]))
    lag=subprocess.check_output(['docker','exec','sting-infra21-kafka-1','kafka-consumer-groups','--bootstrap-server','192.168.1.21:9092','--describe','--group','socai2-fusion-consumer'],stderr=subprocess.DEVNULL).decode();parts=[x.split() for x in lag.splitlines() if 'socai2.alerts.raw' in x];assert len(parts)==3 and all(x[5]=='0' for x in parts)
    save('environment-after.json',end)
    result={'other_existing_containers_unchanged':len(start['containers'])-2,'only_recreated_and_restarted':['api','agents'],'volume_names_preserved':len(end['volumes']),'material_counts':counts,'migrations_unchanged':134,'runtime':{n:runtime(n) for n in before},'gateway_counters_unchanged':model,'fusion_partition_lags':[int(x[5]) for x in parts],'fixture_key_statuses':statuses,'test_keys_deactivated':3,'images':{n:inspect(n)['Image'] for n in before},'original_alert_results_not_rewritten':True,'automatic_worker_remains_off':True}
    save('postconditions.json',result);print(json.dumps({k:v for k,v in result.items() if k!='runtime'}))
if __name__=='__main__':main()
