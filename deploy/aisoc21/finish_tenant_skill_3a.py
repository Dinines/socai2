"""Restart only API/Agents, verify frozen products, revoke operation keys; retain tenant reader keys."""
import hashlib,json,subprocess,sys,time,urllib.request,urllib.error
from collections import Counter
from pathlib import Path
from prepare_tenant_skill_3a import R,E,TABLES,rows,KEYS_DIR
from prepare_identity_2a import MATERIAL_SQL
from prepare_2a import snapshot
from shared_1b import SharedBatch
from finish_context_2c import runtime
from finish_model_triage_3a import METRICS

def inspect(n):return json.loads(subprocess.check_output(['docker','inspect','socai2-'+n+'-1']))[0]
def save(n,data):
    with (E/n).open('x') as f:json.dump(data,f,indent=2)
    (E/n).chmod(0o600)
def status(url,key):
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+key})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:return response.status
    except urllib.error.HTTPError as error:return error.code
def main(resume=False):
    assert (E/'verify-acceptance.json').exists()
    b=SharedBatch(R);state=json.loads((R/'private/app-tenant-skill-3a.json').read_text());ids=state['identities']
    if resume:
        assert (E/'restart-acceptance.json').exists() and (E/'key-lifecycle.json').exists()
        assert not (E/'resident-read-after-restart.json').exists() and not (E/'postconditions.json').exists()
        checkpoint=json.loads((E/'restart-before.json').read_text());before={n:inspect(n) for n in checkpoint}
        for n,current in before.items():
            assert all(current[k]==checkpoint[n][k.lower()] for k in ['Id','Image','Mounts'])
            assert current['State'].get('Health',{}).get('Status')=='healthy'
        lifecycle=json.loads((E/'key-lifecycle.json').read_text())
        revoked=lifecycle['revoked_operation_statuses'];retained=lifecycle['retained_tenant_reader_keys']
        assert set(revoked.values())=={401} and all(x['status']==200 for x in retained.values())
        save('finish-read-only-resume.json',{'restart_and_key_lifecycle_already_verified':True,'new_restarts':0,'new_key_mutations':0,'new_alerts':0,'new_model_calls':0,'reason':'resident stdout log prefix caused JSONDecodeError after successful HTTP reads; parse marked JSON only'})
    else:
        assert not (E/'restart-before.json').exists(),'Inspect prior checkpoints; no repeat restart'
        before={n:inspect(n) for n in ['api','agents']}
        save('restart-before.json',{n:{'id':x['Id'],'image':x['Image'],'mounts':x['Mounts']} for n,x in before.items()})
        for n in before:
            subprocess.run(['docker','restart','socai2-'+n+'-1'],check=True,capture_output=True)
            for _ in range(45):
                current=inspect(n)
                if current['State'].get('Health',{}).get('Status')=='healthy':break
                time.sleep(1)
            else:raise RuntimeError('Unhealthy '+n)
            assert current['Id']==before[n]['Id'] and current['Image']==before[n]['Image'] and current['Mounts']==before[n]['Mounts']
        command=['docker','run','--rm','--user','0','--network','socai2_default','--env-file',str(R/'private/probe-tenant-skill-3a.env'),'-v',str(R/'private/app-tenant-skill-3a.json')+':/private/state.json:ro','-v',str(KEYS_DIR)+':/run/secrets/tenant-skill:ro','-v',str(R/'private/org-memory-3a')+':/run/secrets/org-memory:ro','-v',str(E)+':/evidence','-v',str(R/'source/deploy/aisoc21/acceptance_tenant_skill_3a.py')+':/probe.py:ro','-v',str(R/'certificates/socai2-ca.crt')+':/run/certs/ca.crt:ro','socai2-agents:tenant-skill-3a-20261020','python','/probe.py','restart']
        subprocess.run(command,check=True,capture_output=True)
        revoked={};retained={}
        for n in ['a','b','denied']:
            i=ids[n];b.pg("SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='"+i['key_id']+"' AND tenant_id='"+i['tenant_id']+"' AND name='socai2-3a-tenant-skill-20261020-"+n+"';")
            revoked[n]=status('http://127.0.0.1:18000/api/v1/tenant-skills/resolved/active',i['key']);assert revoked[n]==401
        for n in ['reader_a','reader_b']:
            i=ids[n];retained[n]={'status':status('http://127.0.0.1:18000/api/v1/tenant-skills/resolved/active?tenant_id='+i['tenant_id'],i['key']),'tenant_id':i['tenant_id'],'scopes':i['scopes'],'expires_at':i['expires_at']}
            assert retained[n]['status']==200 and i['scopes']==['settings:read']
        save('key-lifecycle.json',{'revoked_operation_statuses':revoked,'retained_tenant_reader_keys':retained})
    code='''import asyncio,json
from app.context import tenant_skills as m
from app.context import organisation_memory as org
from app.workers.fused_alert_consumer import worker_enabled
async def main():
 m.clear_cache();out={}
 for tenant in json.loads(__import__('sys').argv[1]):
  read=await m.fetch_tenant_skills(tenant);assert read['status']=='success' and read['cache']['source']=='network'
  skill=m.select_skill(read['skills'],rule_id='R-SKILL-A');assert skill is not None
  old=await org.fetch_organisation_memory(tenant);assert old['status']=='success'
  out[tenant]={'status':read['status'],'candidate_count':read['candidate_count'],'selected_ref':skill.ref,'cache':read['cache'],'org_memory_status':old['status']}
 assert not worker_enabled();print('RESULT_JSON='+json.dumps(out))
asyncio.run(main())'''
    output=subprocess.check_output(['docker','exec','socai2-agents-1','python','-c',code,json.dumps([ids[n]['tenant_id'] for n in ['a','b']])]).decode()
    marked=[line.removeprefix('RESULT_JSON=') for line in output.splitlines() if line.startswith('RESULT_JSON=')]
    assert len(marked)==1
    resident=json.loads(marked[0])
    assert resident[ids['a']['tenant_id']]['selected_ref']=='skill-a-rule@v3'
    save('resident-read-after-restart.json',resident)
    original=json.loads((E/'prior-org-memory-credentials.json').read_text())
    assert hashlib.sha256((R/'private/app-org-memory-3a.json').read_bytes()).hexdigest()==original['org_memory_state_sha256']
    assert hashlib.sha256((R/'private/org-memory-3a/keys.json').read_bytes()).hexdigest()==original['org_memory_keys_sha256']
    org_state=json.loads((R/'private/app-org-memory-3a.json').read_text());org_credentials={}
    for n in ['reader_a','reader_b']:
        i=org_state['identities'][n]
        observed=json.loads(b.pg("SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT id,tenant_id,is_active,scopes,expires_at FROM api_keys WHERE id='"+i['key_id']+"') t;").stdout)
        assert observed['is_active'] and observed['scopes']==['alerts:read']
        org_credentials[n]=observed
    save('original-org-memory-credentials-unchanged.json',{'files_hash_unchanged':True,'reader_key_metadata':org_credentials})
    evaluations=json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT id,status,headline_accuracy,score,method FROM aisoc_replay_evaluations ORDER BY id) t;").stdout)
    assert len(evaluations)==4 and all(x['status']=='failed' and x['headline_accuracy'] is None and x['score'] is None and x['method']['not_actual_backtest'] for x in evaluations)
    deltas={'alerts':1,'investigation_runs':2,'investigation_events':3,'investigation_artifacts':5,'aisoc_run_costs':1,'aisoc_shadow_mode':0,'aisoc_shadow_decisions':1,'aisoc_business_context_rule_sets':0,'aisoc_context_statements':0,'aisoc_tenant_skills':10,'aisoc_tenant_skill_versions':12,'aisoc_replay_evaluations':4};counts={}
    for n in ['alerts']+TABLES:
        current=json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM ("+MATERIAL_SQL+") t;").stdout) if n=='alerts' else rows(b,n)
        hashes=[hashlib.sha256(x['material'].encode()).hexdigest() for x in current];old=json.loads((E/('prior-'+n+'.json')).read_text())
        assert not Counter(old)-Counter(hashes),n
        assert len(hashes)==len(old)+deltas[n],(n,len(hashes),len(old),deltas[n])
        counts[n]={'old_preserved':len(old),'added':deltas[n],'total':len(hashes)}
    assert b.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    pre=json.loads((E/'model-before-persist.json').read_text());rid=pre['run_id'];metadata=json.loads((E/'model-metadata.json').read_text());usage=metadata['usage_metadata']
    cost=json.loads(b.pg("SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT run_id,total_prompt_tokens,total_completion_tokens,call_count,measured_call_count,estimated_call_count,unpriced_call_count FROM aisoc_run_costs WHERE run_id='"+rid+"') t;").stdout)
    run_tokens=int(b.pg("SET ROLE aisoc; SELECT total_tokens FROM investigation_runs WHERE id='"+rid+"';").stdout)
    assert pre['tokens']==usage['total_tokens']==run_tokens==cost['total_prompt_tokens']+cost['total_completion_tokens']
    assert usage['input_tokens']==cost['total_prompt_tokens'] and usage['output_tokens']==cost['total_completion_tokens'] and cost['call_count']==cost['unpriced_call_count']==1
    assert metadata['route']=='http://192.168.1.43:8000/v1'
    gateway=json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',METRICS]));old_gateway=json.loads((E/'gateway-before.json').read_text());expected=dict(old_gateway);expected['aisoc-triage']+=1;assert gateway==expected
    start=json.loads((E/'environment-before.json').read_text());end=snapshot()
    for n,x in start['containers'].items():
        if n not in ['socai2-api-1','socai2-agents-1']:assert end['containers'][n]==x,n
    assert set(start['containers'])==set(end['containers']) and start['volumes']==end['volumes']
    live={n:runtime(n) for n in before};assert not live['agents']['automatic_kafka_worker_enabled']
    # SQLite supports only the upstream unit suite; it must not enter production.
    sqlite_probe='from importlib.util import find_spec; assert find_spec("aiosqlite") is None; print("absent")'
    assert subprocess.check_output(['docker','exec','socai2-api-1','python','-c',sqlite_probe]).decode().strip()=='absent'
    live['api']['test_only_aiosqlite_absent']=True
    result={'only_recreated_and_restarted':list(before),'images':{n:inspect(n)['Image'] for n in before},'other_existing_containers_unchanged':len(start['containers'])-2,'volumes_preserved':len(end['volumes']),'material_counts':counts,'migrations_unchanged':134,'runtime':live,'usage':{'successful_calls':1,'prompt_tokens':usage['input_tokens'],'completion_tokens':usage['output_tokens'],'total_tokens':usage['total_tokens'],'unpriced_calls':1,'cost':None},'cost_row':cost,'gateway_before':old_gateway,'gateway_after':gateway,'operation_keys_deactivated':3,'revoked_operation_statuses':revoked,'retained_reader_keys':retained,'resident_read_after_restart':resident,'original_org_memory_credential_files_and_scopes_preserved':True,'failed_replay_fk_fixtures_not_actual_backtests':evaluations,'resident_worker_enabled':False,'schema_or_dependencies_changed':False,'configuration_change':'Agents adds dedicated tenant-skill key path/read-only directory; existing org-memory credentials/env/mounts preserved'}
    save('environment-after.json',end);save('postconditions.json',result);print(json.dumps({k:v for k,v in result.items() if k!='runtime'}))
    E.chmod(0o700)
    for p in E.iterdir():
        if p.is_file():p.chmod(0o600)
if __name__=='__main__':
    assert sys.argv[1:] in [[],['--resume-after-key-lifecycle']]
    main(bool(sys.argv[1:]))
