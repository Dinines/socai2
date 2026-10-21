"""Targeted Agents restart, frozen material/source check and scoped-key cleanup."""
from pathlib import Path
import hashlib,json,subprocess,time,urllib.request,urllib.error
from collections import Counter
from prepare_2a import snapshot
from prepare_suppression_3a import R,E,rows
from prepare_identity_2a import MATERIAL_SQL
from shared_1b import SharedBatch
from finish_context_2c import runtime

def main():
    assert (E/'broker-acceptance.json').exists() and not (E/'restart-before.json').exists()
    start=json.loads((E/'environment-before.json').read_text());b=SharedBatch(R)
    def inspect():return json.loads(subprocess.check_output(['docker','inspect','socai2-agents-1']))[0]
    x=inspect();(E/'restart-before.json').write_text(json.dumps({'id':x['Id'],'image':x['Image']},indent=2))
    subprocess.run(['docker','restart','socai2-agents-1'],check=True,capture_output=True)
    for _ in range(45):
        now=inspect()
        if now['State'].get('Health',{}).get('Status')=='healthy':break
        time.sleep(1)
    else:raise AssertionError('Agents unhealthy')
    assert now['Id']==x['Id'] and now['Image']==x['Image'] and now['Mounts']==x['Mounts']
    cmd=['docker','run','--rm','--network','socai2_default','--env-file',str(R/'private/probe-suppression-3a.env'),'-v',str(R/'private/app-suppression-3a.json')+':/private/state.json:ro','-v',str(E)+':/evidence','-v',str(R/'source/deploy/aisoc21/acceptance_suppression_3a.py')+':/probe.py:ro','-v',str(R/'certificates/socai2-ca.crt')+':/run/certs/ca.crt:ro','socai2-agents:suppression-3a-20261020','python','/probe.py','restart']
    subprocess.run(cmd,check=True,capture_output=True)
    counts={}
    for name,added in [('alerts',2),('investigation_runs',3),('investigation_events',3),('aisoc_business_context_rule_sets',1)]:
        current=json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM ("+MATERIAL_SQL+") t;").stdout) if name=='alerts' else rows(b,name)
        hashes=[hashlib.sha256(x['material'].encode()).hexdigest() for x in current]
        old=json.loads((E/('prior-'+name+'.json')).read_text());assert not Counter(old)-Counter(hashes)
        assert len(hashes)==len(old)+added,(name,len(hashes),len(old),added)
        counts[name]={'old_preserved':len(old),'added':added,'total':len(hashes)}
    assert b.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    end=snapshot()
    for name,value in start['containers'].items():
        if name!='socai2-agents-1':assert end['containers'][name]==value,name
    assert set(start['containers'])==set(end['containers']) and start['volumes']==end['volumes']
    # Exact runtime file hashes, original locked dependencies and worker-off flag.
    runtime_check=runtime('agents');assert not runtime_check['automatic_kafka_worker_enabled']
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
    ids=json.loads((R/'private/app-suppression-3a.json').read_text())['identities'];statuses={}
    for name,i in ids.items():
        b.pg("SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='"+i['key_id']+"' AND name LIKE 'socai2-3a-suppression-20261020-%';")
        req=urllib.request.Request('http://127.0.0.1:18000/api/v1/business-context/rules',headers={'Authorization':'Bearer '+i['key']})
        try:urllib.request.urlopen(req,timeout=10);raise AssertionError('Key still accepted')
        except urllib.error.HTTPError as error:assert error.code==401;statuses[name]=error.code
    result={'only_recreated_and_restarted':['agents'],'agents_image':now['Image'],'other_existing_containers_unchanged':len(start['containers'])-1,'volumes_preserved':len(end['volumes']),'material_counts':counts,'migrations_unchanged':134,'runtime':runtime_check,'successful_model_request_counters_unchanged':model,'test_keys_deactivated':3,'revoked_key_statuses':statuses,'resident_worker_enabled':False,'schema_or_runtime_environment_changed':False}
    (E/'environment-after.json').write_text(json.dumps(end,indent=2));(E/'postconditions.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='runtime'}))
if __name__=='__main__':main()
