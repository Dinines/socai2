"""Restart only this batch's three services, read back frozen result, revoke keys."""
import hashlib,json,subprocess,time,urllib.request,urllib.error
from collections import Counter
from pathlib import Path
from prepare_risk_score_3a import R,E,TABLES,rows
from prepare_identity_2a import MATERIAL_SQL
from prepare_2a import snapshot
from shared_1b import SharedBatch
from finish_context_2c import runtime
from finish_model_triage_3a import METRICS

def inspect(n):return json.loads(subprocess.check_output(['docker','inspect','socai2-'+n+'-1']))[0]
def main():
    assert (E/'verify-acceptance.json').exists() and not (E/'restart-before.json').exists()
    before={n:inspect(n) for n in ['api','fusion','agents']}
    (E/'restart-before.json').write_text(json.dumps({n:{'id':x['Id'],'image':x['Image']} for n,x in before.items()},indent=2))
    for n in before:
        subprocess.run(['docker','restart','socai2-'+n+'-1'],check=True,capture_output=True)
        for _ in range(45):
            x=inspect(n)
            if x['State'].get('Health',{}).get('Status')=='healthy':break
            time.sleep(1)
        else:raise RuntimeError('Unhealthy '+n)
        assert x['Id']==before[n]['Id'] and x['Image']==before[n]['Image'] and x['Mounts']==before[n]['Mounts']
    cmd=['docker','run','--rm','--network','socai2_default','--env-file',str(R/'private/probe-risk-score-3a.env'),'-v',str(R/'private/app-risk-score-3a.json')+':/private/state.json:ro','-v',str(E)+':/evidence','-v',str(R/'source/deploy/aisoc21/acceptance_risk_score_3a.py')+':/probe.py:ro','-v',str(R/'certificates/socai2-ca.crt')+':/run/certs/ca.crt:ro','socai2-agents:risk-score-3a-20261020','python','/probe.py','restart']
    subprocess.run(cmd,check=True,capture_output=True)
    b=SharedBatch(R);ids=json.loads((R/'private/app-risk-score-3a.json').read_text())['identities'];statuses={}
    for n,i in ids.items():
        b.pg("SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='"+i['key_id']+"' AND name LIKE 'socai2-3a-risk-20261020-%';")
        req=urllib.request.Request('http://127.0.0.1:18000/api/v1/alerts/00000000-0000-0000-0000-000000000001',headers={'Authorization':'Bearer '+i['key']})
        try:urllib.request.urlopen(req,timeout=10);raise AssertionError('Revoked key accepted')
        except urllib.error.HTTPError as error:assert error.code==401;statuses[n]=error.code
    (E/'key-revocation.json').write_text(json.dumps(statuses,indent=2))
    deltas={'alerts':4,'investigation_runs':1,'investigation_events':2,'investigation_artifacts':2,'aisoc_run_costs':1,'aisoc_shadow_mode':2,'aisoc_shadow_decisions':1,'aisoc_business_context_rule_sets':0};counts={}
    for n in ['alerts']+TABLES:
        current=json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM ("+MATERIAL_SQL+") t;").stdout) if n=='alerts' else rows(b,n)
        hashes=[hashlib.sha256(x['material'].encode()).hexdigest() for x in current];old=json.loads((E/('prior-'+n+'.json')).read_text())
        assert not Counter(old)-Counter(hashes),n
        assert len(hashes)==len(old)+deltas[n],(n,len(hashes),len(old),deltas[n])
        counts[n]={'old_preserved':len(old),'added':deltas[n],'total':len(hashes)}
    assert b.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    pre=json.loads((E/'model-before-persist.json').read_text());rid=pre['run_id'];metadata=json.loads((E/'model-metadata.json').read_text());usage=metadata['usage_metadata']
    cost=json.loads(b.pg("SELECT row_to_json(t) FROM (SELECT run_id,total_prompt_tokens,total_completion_tokens,call_count,measured_call_count,estimated_call_count,unpriced_call_count FROM aisoc_run_costs WHERE run_id='"+rid+"') t;").stdout)
    run_tokens=int(b.pg("SET ROLE aisoc; SELECT total_tokens FROM investigation_runs WHERE id='"+rid+"';").stdout)
    assert pre['tokens']==usage['total_tokens']==run_tokens==cost['total_prompt_tokens']+cost['total_completion_tokens']
    assert usage['input_tokens']==cost['total_prompt_tokens'] and usage['output_tokens']==cost['total_completion_tokens'] and cost['call_count']==cost['unpriced_call_count']==1
    assert metadata['route']=='http://192.168.1.43:8000/v1'
    gateway=json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',METRICS]));old=json.loads((E/'gateway-before.json').read_text());expected=dict(old);expected['aisoc-triage']+=1;assert gateway==expected
    start=json.loads((E/'environment-before.json').read_text());end=snapshot()
    for n,x in start['containers'].items():
        if n not in ['socai2-api-1','socai2-fusion-1','socai2-agents-1']:assert end['containers'][n]==x,n
    assert set(start['containers'])==set(end['containers']) and start['volumes']==end['volumes']
    live={n:runtime(n) for n in before};assert not live['agents']['automatic_kafka_worker_enabled']
    result={'only_recreated_and_restarted':list(before),'images':{n:inspect(n)['Image'] for n in before},'other_existing_containers_unchanged':len(start['containers'])-3,'volumes_preserved':len(end['volumes']),'material_counts':counts,'migrations_unchanged':134,'runtime':live,'usage':{'successful_calls':1,'prompt_tokens':usage['input_tokens'],'completion_tokens':usage['output_tokens'],'total_tokens':usage['total_tokens'],'unpriced_calls':1,'cost':None},'cost_row':cost,'gateway_before':old,'gateway_after':gateway,'test_keys_deactivated':3,'revoked_key_statuses':statuses,'resident_worker_enabled':False,'schema_or_dependencies_or_resident_env_changed':False}
    (E/'environment-after.json').write_text(json.dumps(end,indent=2));(E/'postconditions.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='runtime'}))
    E.chmod(0o700)
    for p in E.iterdir():
        if p.is_file():p.chmod(0o600)
if __name__=='__main__':main()
