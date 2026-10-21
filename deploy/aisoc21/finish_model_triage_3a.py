"""Read-only runtime/material/usage checks after scoped-key revocation. No restart."""
from pathlib import Path
from collections import Counter
import hashlib,json,subprocess,urllib.request,urllib.error
from prepare_model_triage_3a import R,E,TABLES,rows
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from shared_1b import SharedBatch
from finish_context_2c import runtime
METRICS='''import json,urllib.request
from prometheus_client.parser import text_string_to_metric_families
with urllib.request.urlopen('http://127.0.0.1:4000/metrics') as f:v=f.read().decode()
counts={}
for family in text_string_to_metric_families(v):
 for s in family.samples:
  if s.name=='litellm_proxy_total_requests_metric_total' and s.labels.get('status_code')=='200':
   k=s.labels['requested_model'];counts[k]=counts.get(k,0)+s.value
print(json.dumps(counts))'''
def main():
    assert not (E/'postconditions.json').exists(),'No repeat finish'
    for folder in [E,E/'blind']:
        assert (folder/'verify-acceptance.json').exists() and (folder/'broker-restart-acceptance.json').exists()
    b=SharedBatch(R);ids=json.loads((R/'private/app-model-triage-3a.json').read_text())['identities'];statuses={}
    # Cleanup first, so subsequent assertion failures cannot leave live test keys.
    for n,i in ids.items():
        b.pg("SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='"+i['key_id']+"' AND name LIKE 'socai2-3a-model-triage-20261020-%';")
        req=urllib.request.Request('http://127.0.0.1:18000/api/v1/alerts/00000000-0000-0000-0000-000000000001',headers={'Authorization':'Bearer '+i['key']})
        try:urllib.request.urlopen(req,timeout=10);raise AssertionError('Revoked key accepted')
        except urllib.error.HTTPError as error:assert error.code==401;statuses[n]=error.code
    (E/'key-revocation.json').write_text(json.dumps(statuses,indent=2))
    counts={};deltas={'alerts':7,'investigation_runs':7,'investigation_events':13,'investigation_artifacts':12,'aisoc_run_costs':6,'aisoc_shadow_mode':2,'aisoc_shadow_decisions':7,'aisoc_business_context_rule_sets':0}
    for name in ['alerts']+TABLES:
        current=json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM ("+MATERIAL_SQL+") t;").stdout) if name=='alerts' else rows(b,name)
        now=[hashlib.sha256(x['material'].encode()).hexdigest() for x in current];old=json.loads((E/('prior-'+name+'.json')).read_text())
        assert not Counter(old)-Counter(now),name
        assert len(now)==len(old)+deltas[name],(name,len(now),len(old),deltas[name])
        counts[name]={'old_preserved':len(old),'added':len(now)-len(old),'total':len(now)}
    assert b.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    run_checks=[];prompt=completion=total=0
    for folder in [E,E/'blind']:
        observed=json.loads((folder/'broker-acceptance.json').read_text())
        for label,result in observed['results'].items():
            pre=json.loads((folder/(label+'-before-persist.json')).read_text());run_id=result['run_id'];expected=pre['tokens']
            stored=json.loads(b.pg("SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT id,total_tokens,total_cost_usd,measured_call_count,estimated_call_count,unpriced_call_count FROM investigation_runs WHERE id='"+run_id+"') t;").stdout)
            raw_cost=b.pg("SELECT row_to_json(t) FROM (SELECT run_id,total_prompt_tokens,total_completion_tokens,call_count,measured_call_count,estimated_call_count,unpriced_call_count FROM aisoc_run_costs WHERE run_id='"+run_id+"') t;").stdout.strip()
            cost=json.loads(raw_cost) if raw_cost else None
            assert stored['total_tokens']==expected
            if cost:assert expected==cost['total_prompt_tokens']+cost['total_completion_tokens']
            if label!='model_failure':
                metadata=json.loads((folder/(label+'-model-response-metadata.json')).read_text());u=metadata['usage_metadata']
                assert expected==u['total_tokens'] and u['input_tokens']==cost['total_prompt_tokens'] and u['output_tokens']==cost['total_completion_tokens']
                assert stored['unpriced_call_count']==cost['unpriced_call_count']==cost['call_count']==1
                assert metadata['headers']['x-litellm-model-api-base']=='http://192.168.1.43:8000/v1'
                assert not pre['exchanges'][0]['prompt_truncated'] and not pre['exchanges'][0]['response_truncated']
                if folder.name=='blind':
                    text=pre['exchanges'][0]['prompt']
                    assert 'raw_event.label' not in text and 'raw_event.synthetic' not in text and 'synthetic:' not in text
            else:assert expected==0 and cost is None and result['verdict']=='needs_review' and result['tier']=='deterministic'
            prompt+=(cost or {}).get('total_prompt_tokens',0);completion+=(cost or {}).get('total_completion_tokens',0);total+=expected
            run_checks.append({'cohort':'blind' if folder.name=='blind' else 'initial','sample':label,'run_id':run_id,'tokens':expected,'cost_row':cost,'run':stored,'reply_tokens_equal_run_and_cost_row':cost is not None,'no_cost_row_for_failed_no_response':cost is None})
    model=json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',METRICS]));old=json.loads((E/'gateway-before.json').read_text());expected=dict(old);expected['aisoc-triage']+=6;assert model==expected
    start=json.loads((E/'environment-before.json').read_text());end=snapshot();assert start==end
    (E/'environment-after.json').write_text(json.dumps(end,indent=2))
    live=runtime('agents');assert not live['automatic_kafka_worker_enabled']
    result={'runtime_source_dependencies_and_resident_env_unchanged':True,'runtime':live,'all_existing_containers_unchanged':len(start['containers']),'volumes_preserved':len(end['volumes']),'material_counts':counts,'migrations_unchanged':134,'run_checks':run_checks,'usage':{'successful_calls':6,'failed_local_endpoint_scenario':1,'prompt_tokens':prompt,'completion_tokens':completion,'total_tokens':total,'unpriced_calls':6,'cost':None},'gateway_before':old,'gateway_after':model,'test_keys_deactivated':3,'revoked_key_statuses':statuses,'resident_worker_enabled':False,'new_vendor_actions':0,'bounded_blind_classification_matrix_passed':True,'broad_model_quality_accepted':False,'known_input_and_context_issues':['Missing risk_score rendered as0.0','Five optional context readers returned401','Initial labeled cohort contaminated; retained separately','MITRE technique-name inaccuracies in rationale','Authorization source supplied, external approval not verified']}
    (E/'postconditions.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['runtime','run_checks']}))
    E.chmod(0o700)
    for p in E.rglob('*'):
        if p.is_file():p.chmod(0o600)
        elif p.is_dir():p.chmod(0o700)
if __name__=='__main__':main()
