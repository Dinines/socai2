"""Targeted restart, preserved prior readers and scoped disposition-key lifecycle."""
from collections import Counter
from pathlib import Path
import hashlib,json,subprocess,time,urllib.error,urllib.request
from prepare_dispositions_3a import R,E,TABLES,KEYS_DIR,rows
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from shared_1b import SharedBatch
from finish_context_2c import runtime
from finish_model_triage_3a import METRICS


def save(name,value):
    with (E/name).open('x') as stream:json.dump(value,stream,indent=2)
    (E/name).chmod(0o600)


def inspect(name):return json.loads(subprocess.check_output(['docker','inspect','socai2-'+name+'-1']))[0]


def status(url,key):
    request=urllib.request.Request(url,headers={'Authorization':'Bearer '+key})
    try:
        with urllib.request.urlopen(request,timeout=15) as response:return response.status
    except urllib.error.HTTPError as error:return error.code


def main(resume_postconditions=False):
    if resume_postconditions:
        assert (E/'import-revision-deployment.json').exists() and (E/'restart-acceptance.json').exists()
        assert not (E/'postconditions.json').exists() and not (E/'resident-read-after-restart.json').exists()
        revision=json.loads((E/'import-revision-deployment.json').read_text())
        before={name:inspect(name) for name in ['api','agents']}
        first=json.loads((E/'restart-before.json').read_text())
        assert before['api']['Id']==first['api']['id'] and before['api']['Image']==first['api']['image']
        assert before['agents']['Image']==revision['images']['after']
        assert all(item['State'].get('Health',{}).get('Status')=='healthy' for item in before.values())
        batch=SharedBatch(R);state=json.loads((R/'private/app-dispositions-3a.json').read_text());ids=state['identities']
        lifecycle=json.loads((E/'key-lifecycle.json').read_text());revoked=lifecycle['revoked_operation_statuses'];retained=lifecycle['retained_tenant_reader_keys']
        base='http://127.0.0.1:18000/api/v1/feedback/recent-dispositions?rule_id=R-DISP-A'
        statuses={name:status(base+'&tenant_id='+item['tenant_id'],item['key']) for name,item in ids.items()}
        assert statuses=={'a':401,'b':401,'denied':401,'reader_a':200,'reader_b':200}
        save('post-recovery-key-statuses.json',{'statuses':statuses,'new_restarts':0,'new_key_mutations':0,'new_ingress':0,'new_model_calls':0})
    else:
        assert (E/'verify-acceptance.json').exists() and not (E/'restart-before.json').exists(), 'Inspect checkpoints; never blindly repeat a restart'
        before={name:inspect(name) for name in ['api','agents']}
        save('restart-before.json',{name:{'id':item['Id'],'image':item['Image'],'mounts':item['Mounts']} for name,item in before.items()})
        for name,item in before.items():
            subprocess.run(['docker','restart','socai2-'+name+'-1'],check=True,capture_output=True)
            for _ in range(45):
                current=inspect(name)
                if current['State'].get('Health',{}).get('Status')=='healthy':break
                time.sleep(1)
            else:raise RuntimeError('Unhealthy '+name)
            assert current['Id']==item['Id'] and current['Image']==item['Image'] and current['Mounts']==item['Mounts']
        command=['docker','run','--rm','--user','0','--network','socai2_default','--env-file',str(R/'private/probe-dispositions-3a.env'),'-v',str(R/'private/app-dispositions-3a.json')+':/private/state.json:ro','-v',str(E)+':/evidence','-v',str(R/'source/deploy/aisoc21/acceptance_dispositions_3a.py')+':/probe.py:ro','-v',str(R/'source/services/api/app/api/v1/endpoints/feedback.py')+':/api-feedback.py:ro','-v',str(R/'certificates/socai2-ca.crt')+':/run/certs/ca.crt:ro']
        for host,target in [('org-memory-3a','org-memory'),('tenant-skill-3a','tenant-skill'),('kb-read-3a','triage-kb'),('dispositions-3a','dispositions')]:command+=['-v',str(R/'private'/host)+':/run/secrets/'+target+':ro']
        command+=['socai2-agents:dispositions-3a-20261020','python','/probe.py','restart']
        result=subprocess.run(command,text=True,capture_output=True)
        save('restart-probe-result.json',{'exit_code':result.returncode})
        (E/'restart-probe.log').write_text(result.stdout+result.stderr)
        assert result.returncode==0,'Inspect restart-probe.log; no repeat restart/model'
        batch=SharedBatch(R);state=json.loads((R/'private/app-dispositions-3a.json').read_text());ids=state['identities']
        revoked={};retained={}
        base='http://127.0.0.1:18000/api/v1/feedback/recent-dispositions?rule_id=R-DISP-A'
        for name in ['a','b','denied']:
            item=ids[name]
            batch.pg("SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='"+item['key_id']+"' AND tenant_id='"+item['tenant_id']+"' AND name='socai2-3a-dispositions-20261020-"+name+"';")
            revoked[name]=status(base,item['key']);assert revoked[name]==401
        for name in ['reader_a','reader_b']:
            item=ids[name];code=status(base+'&tenant_id='+item['tenant_id'],item['key'])
            assert code==200 and item['scopes']==['alerts:read']
            retained[name]={key:item[key] for key in ['tenant_id','scopes','expires_at']};retained[name]['status']=code
        save('key-lifecycle.json',{'revoked_operation_statuses':revoked,'retained_tenant_reader_keys':retained})
    code='''import asyncio,json,sys
from app.context import dispositions as d, knowledge_base as kb,organisation_memory as org,tenant_skills as skills
from app.workers.fused_alert_consumer import worker_enabled
async def main():
 d.clear_cache();kb.clear_cache();org.clear_cache();skills.clear_cache();out={}
 for tenant in json.loads(sys.argv[1]):
  found=await d.fetch_recent_dispositions(tenant,rule_id="R-DISP-A",entities=["disp-host-a"])
  read=found.as_read();assert read['status']=='success' and read['cache']['source']=='network'
  old=await org.fetch_organisation_memory(tenant);assert old['status']=='success'
  skillread=await skills.fetch_tenant_skills(tenant);assert skillread['status']=='success'
  selected=skills.select_skill(skillread['skills'],rule_id='R-SKILL-A');assert selected is not None
  kbread=(await kb.fetch_runbooks(tenant,query=sys.argv[2])).as_read();assert kbread['status']=='success'
  out[tenant]={'dispositions_status':read['status'],'adopted_count':read['adopted_count'],'feedback_ids':[row['feedback_id'] for row in read['decisions']],'cache':read['cache'],'org_memory_status':old['status'],'skill_status':skillread['status'],'skill_ref':selected.ref,'kb_status':kbread['status'],'kb_adopted_count':kbread['adopted_count']}
 assert not worker_enabled();print('RESULT_JSON='+json.dumps(out))
asyncio.run(main())'''
    kb_query=json.loads((R/'evidence/3a-kb-read-20261020/after-acceptance.json').read_text())['actual_query']
    output=subprocess.check_output(['docker','exec','socai2-agents-1','python','-c',code,json.dumps([ids[n]['tenant_id'] for n in ['a','b']]),kb_query]).decode()
    marked=[line.removeprefix('RESULT_JSON=') for line in output.splitlines() if line.startswith('RESULT_JSON=')];assert len(marked)==1
    resident=json.loads(marked[0]);assert resident[ids['a']['tenant_id']]['skill_ref']=='skill-a-rule@v3'
    assert resident[ids['b']['tenant_id']]['skill_ref']=='skill-b-valid@v1'
    save('resident-read-after-restart.json',resident)
    original=state['original_reader_credentials'];old_reader_metadata={}
    for name,stem,scope in [('org_memory','org-memory','alerts:read'),('tenant_skill','tenant-skill','settings:read'),('knowledge_base','kb-read','knowledge_base:read')]:
        path=R/('private/app-'+stem+'-3a.json');keyfile=R/'private'/(stem+'-3a')/'keys.json'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==original[name]['state_sha256']
        assert hashlib.sha256(keyfile.read_bytes()).hexdigest()==original[name]['keys_sha256']
        old=json.loads(path.read_text());old_reader_metadata[name]={}
        for alias in ['reader_a','reader_b']:
            item=old['identities'][alias]
            observed=json.loads(batch.pg("SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT id,tenant_id,is_active,scopes,expires_at FROM api_keys WHERE id='"+item['key_id']+"') t;").stdout)
            assert observed['is_active'] and observed['scopes']==[scope];old_reader_metadata[name][alias]=observed
    save('original-reader-credentials-unchanged.json',{'files_hash_unchanged':True,'metadata':old_reader_metadata})
    deltas={'alerts':1,'investigation_runs':2,'investigation_events':3,'investigation_artifacts':7,'aisoc_run_costs':1,'aisoc_shadow_mode':0,'aisoc_shadow_decisions':1,'aisoc_business_context_rule_sets':0,'aisoc_context_statements':0,'aisoc_tenant_skills':0,'aisoc_tenant_skill_versions':0,'aisoc_replay_evaluations':0,'aisoc_kb_documents':0,'aisoc_analyst_feedback':5};counts={}
    for name in ['alerts']+TABLES:
        material=json.loads(batch.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM ("+MATERIAL_SQL+") t;").stdout) if name=='alerts' else rows(batch,name)
        hashes=[hashlib.sha256(row['material'].encode()).hexdigest() for row in material];old=json.loads((E/('prior-'+name+'.json')).read_text())
        assert not Counter(old)-Counter(hashes),name
        assert len(hashes)==len(old)+deltas[name],(name,len(hashes),len(old),deltas[name])
        counts[name]={'old_preserved':len(old),'added':deltas[name],'total':len(hashes)}
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    pre=json.loads((E/'model-before-persist.json').read_text());metadata=json.loads((E/'model-metadata.json').read_text());usage=metadata['usage_metadata'];run_id=pre['run_id']
    assert metadata['route']=='http://192.168.1.43:8000/v1'
    cost=json.loads(batch.pg("SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT run_id,total_prompt_tokens,total_completion_tokens,call_count,measured_call_count,estimated_call_count,unpriced_call_count FROM aisoc_run_costs WHERE run_id='"+run_id+"') t;").stdout)
    tokens=int(batch.pg("SET ROLE aisoc; SELECT total_tokens FROM investigation_runs WHERE id='"+run_id+"';").stdout)
    assert pre['tokens']==usage['total_tokens']==tokens==cost['total_prompt_tokens']+cost['total_completion_tokens']
    assert usage['input_tokens']==cost['total_prompt_tokens'] and usage['output_tokens']==cost['total_completion_tokens'] and cost['call_count']==cost['unpriced_call_count']==1
    gateway=json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',METRICS]));old_gateway=json.loads((E/'gateway-before.json').read_text());expected=dict(old_gateway);expected['aisoc-triage']+=1;assert gateway==expected
    start=json.loads((E/'environment-before.json').read_text());end=snapshot()
    for name,item in start['containers'].items():
        if name not in ['socai2-api-1','socai2-agents-1']:assert end['containers'][name]==item,name
    assert set(start['containers'])==set(end['containers']) and start['volumes']==end['volumes']
    live={name:runtime(name) for name in before};assert not live['agents']['automatic_kafka_worker_enabled']
    assert subprocess.check_output(['docker','exec','socai2-api-1','python','-c','from importlib.util import find_spec; assert find_spec("aiosqlite") is None; print("absent")']).decode().strip()=='absent'
    live['api']['test_only_aiosqlite_absent']=True
    post={'only_recreated_and_restarted':list(before),'images':{name:inspect(name)['Image'] for name in before},'other_existing_containers_unchanged':len(start['containers'])-2,'volumes_preserved':len(end['volumes']),'material_counts':counts,'migrations_unchanged':134,'runtime':live,'usage':{'successful_calls':1,'prompt_tokens':usage['input_tokens'],'completion_tokens':usage['output_tokens'],'total_tokens':usage['total_tokens'],'unpriced_calls':1,'cost':None},'cost_row':cost,'gateway_before':old_gateway,'gateway_after':gateway,'operation_keys_deactivated':3,'revoked_operation_statuses':revoked,'retained_reader_keys':retained,'resident_read_after_restart':resident,'original_org_memory_skill_and_kb_credentials_files_and_scopes_preserved':True,'resident_worker_enabled':False,'schema_or_dependencies_changed':False}
    if resume_postconditions:
        post['import_revision']=json.loads((E/'import-revision-deployment.json').read_text())
        post['postconditions_resumed_without_new_restart_or_model']=True
    save('environment-after.json',end);save('postconditions.json',post)
    E.chmod(0o700)
    for path in E.iterdir():
        if path.is_file():path.chmod(0o600)
    print(json.dumps({k:v for k,v in post.items() if k!='runtime'}))


if __name__=='__main__':
    import sys
    assert sys.argv[1:] in ([], ['--resume-postconditions'])
    main(resume_postconditions=bool(sys.argv[1:]))
