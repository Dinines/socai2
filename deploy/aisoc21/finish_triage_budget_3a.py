"""Read existing/new products, restart Agents only, verify charges and revoke keys."""
from collections import Counter
import hashlib,json,subprocess
from prepare_triage_budget_3a import R,E,B,STATE,save,hashes,sha
from prepare_triage_request_3a import request,readers
from prepare_identity_read_3a import TABLES,lit
from shared_1b import SharedBatch
from prepare_2a import snapshot
from deploy_triage_request_3a import inspect,describe,healthy,verify_runtime_source,resident
from finish_model_triage_3a import METRICS


def budget_rows(batch):
    return json.loads(batch.pg("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT * FROM socai2_triage_budget_reservations ORDER BY run_id) t;").stdout)


def main():
    assert (E/'budget-verified.json').is_file() and not (E/'finish-started.json').exists()
    save('finish-started.json',{'batch':B,'new_ingress_or_models':0})
    state=json.loads(STATE.read_text());inputs=json.loads((E/'inputs.json').read_text());inputs.update(json.loads((E/'inputs-extra.json').read_text()));ids=state['identities'];checks=[]
    namespace=__import__('uuid').uuid5(__import__('uuid').NAMESPACE_URL,'tryaisoc.com/agents/auto-triage')
    runs={n:str(__import__('uuid').uuid5(namespace,v['alert_row_id']+':auto-triage-v1')) for n,v in inputs.items()}
    def get(path,who='a',expected=200):
        status,value=request(ids,path,who);checks.append({'path':path,'identity':who,'expected':expected,'status':status})
        assert status==expected,(path,who,status,expected)
        return value
    def products():
        result={}
        for alias,value in inputs.items():
            who='a' if alias.startswith('a_') else 'b';base='/api/v1/investigations/'+runs[alias]
            alert=get('/api/v1/alerts/'+value['alert_row_id'],who)
            if alias=='a_denied':
                get(base,who,404);result[alias]={'alert':alert,'run_absent':True};continue
            run=get(base,who);events=get(base+'/events',who);artifacts=get(base+'/artifacts',who)
            expected=[-1] if alias in ['a_unknown','a_done','b_denied'] else [-1,0,1]
            assert [v['seq'] for v in events['items']]==expected
            first=get(base+'/events?limit=1',who);assert first['next_seq']==-1
            later=get(base+'/events?since=-1',who);assert later['items']==events['items'][1:]
            if alias in ['a_unknown','a_done','b_denied']:assert not artifacts
            else:
                assert run['status']=='completed' and run['total_tokens']==0 and len(artifacts)==7
                details=[get(base+'/artifacts/'+v['id'],who) for v in artifacts]
                assert {v['kind'] for v in details}=={'organisation_memory_read','tenant_skill_read','knowledge_base_read','recent_dispositions_read','identity_context_read','llm_prompt','llm_response'}
            get(base+'/events','b' if who=='a' else 'a',404)
            get(base+'/events','denied',403);get(base+'/events',None,401)
            result[alias]={'alert':alert,'run':run,'events':events,'artifacts':artifacts}
        return result
    first=products();save('api-before-restart.json',first)
    batch=SharedBatch(R);before_rows=budget_rows(batch);assert len(before_rows)==5
    save('budget-before-restart.json',before_rows)
    old=inspect('socai2-agents-1');save('restart-before.json',describe(old))
    subprocess.run(['docker','restart','socai2-agents-1'],check=True,capture_output=True)
    after=healthy('agents');assert after['Id']==old['Id'] and after['Image']==old['Image']
    assert describe(after)['env_sha256']==describe(old)['env_sha256'] and after['Mounts']==old['Mounts']
    verify_runtime_source('agents')
    proof=resident()
    # resident() uses the previous read-only state only to check existing reader maps.
    second=products();save('api-after-restart.json',second)
    for alias in first:
        if alias in ['a_unknown','a_done','b_denied']:
            assert first[alias]['events']==second[alias]['events'] and first[alias]['artifacts']==second[alias]['artifacts']
        else:assert first[alias]==second[alias],alias
    assert budget_rows(batch)==before_rows
    save('budget-after-restart.json',budget_rows(batch))
    save('restart-after.json',{'runtime':describe(after),**proof,'same_completed_products':True,'same_budget_reservations':True,'unknown_start_preserved':True})
    revoked={}
    for alias,key in ids.items():
        batch.pg('SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='+lit(key['key_id'])+' AND tenant_id='+lit(key['tenant_id'])+' AND name='+lit('socai2-'+B+'-'+alias)+';')
        get('/api/v1/investigations/'+runs['b_done']+'/events',alias,401);revoked[alias]=401
    save('key-lifecycle.json',{'operation_keys_deactivated':revoked,'new_readers':0})
    assert readers(batch)==state['reader_credentials']
    assert sha(R/'private/identity-graph-3a/config.json')==state['graph_config_sha256']
    policy=R/'private/triage-budget-3a/policy.json'
    assert json.loads(policy.read_text())==json.loads((E/'budget-policy-final.json').read_text())
    counts={};deltas={'alerts':6,'investigation_runs':5,'investigation_events':9,'investigation_artifacts':14,'aisoc_shadow_decisions':2}
    for table in ['alerts']+TABLES:
        old_hashes=json.loads((E/('prior-'+table+'.json')).read_text());current=hashes(batch,table)
        assert not Counter(old_hashes)-Counter(current),table
        assert len(current)==len(old_hashes)+deltas.get(table,0),(table,len(current),len(old_hashes))
        counts[table]={'old_preserved':len(old_hashes),'added':deltas.get(table,0),'total':len(current)}
    gateway=json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',METRICS]))
    assert gateway==json.loads((E/'gateway-before.json').read_text())
    initial,end=json.loads((E/'environment-before.json').read_text()),snapshot()
    assert initial['volumes']==end['volumes'] and set(initial['containers'])==set(end['containers'])
    for name,value in initial['containers'].items():
        if name!='socai2-agents-1':assert end['containers'][name]==value,name
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    save('finish-http-checks.json',checks);save('environment-after.json',end)
    ingress_count=sum(len(json.loads((E/('ingress-'+n)/'normal-http-checks.json').read_text())) for n in inputs)
    verified=json.loads((E/'budget-verified.json').read_text());deployment=json.loads((E/'deployment-final.json').read_text())
    result={'batch':B,'material_counts':counts,'budget_reservations':len(before_rows),'budget_reserved_tokens':sum(v['charged_tokens'] for v in before_rows),
            'budget_observed_tokens_unknown_rows':sum(v['observed_tokens'] is None for v in before_rows),'budget_unsettled':sum(v['settled_at'] is None for v in before_rows),
            'budget_policy_sha256_initial':state['policy_sha256'],'budget_policy_sha256_final':sha(policy),'explicit_policy_topup_resets_charges':False,
            'images':{n:inspect('socai2-'+n+'-1')['Image'] for n in ['api','fusion','agents','actions']},
            'only_updated_and_restarted':['agents'],'controlled_agents_image_updates':2,'compose_layers':21,'runtime_layers':19,
            'other_containers_preserved':35,'containers_total':36,'volumes_preserved':18,'upstream_migrations_preserved':134,'project_additive_sql_tables':1,
            'backup_restore_verified':True,'http_explicit_count':len(checks)+ingress_count,'http_ingress_checks':ingress_count,'http_finish_checks':len(checks),
            'unit_tests_passed':json.loads((E/'tests-agents-final.json').read_text())['passed'],'broker_counts':verified['counts'],
            'reader_keys_preserved':10,'new_reader_keys':0,'operation_keys_deactivated':revoked,'gateway_before_after':gateway,
            'real_model_calls':0,'new_real_usage_or_cost_measurements':0,'new_cost_rows':0,'resident_worker_enabled':False,
            'bounded_budget_stop_recovery_accepted':True,'full_worker_admission_accepted':False,'model_quality_retested':False,
            'pending_backlog':'a_denied group offset0/end1; a_unknown, a_done and b_denied reservations remain unconfirmed',
            'next':'3A-10 admission audit against remaining quality/source/tool requirements; do not enable resident worker automatically'}
    save('postconditions.json',result);print(json.dumps(result))


if __name__=='__main__':main()
