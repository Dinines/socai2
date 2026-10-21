"""Check recovery API products, restart only Agents and revoke batch keys."""
from collections import Counter
from pathlib import Path
import hashlib, json, subprocess, time, urllib.error, urllib.request, uuid
from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
from prepare_identity_read_3a import TABLES, rows, lit
from prepare_triage_admission_3a import READERS, sha
from prepare_triage_recovery_3a import R, E, B, save
from finish_model_triage_3a import METRICS
from deploy_triage_recovery_3a import inspect, describe

def read(name): return json.loads((E / name).read_text())

def main():
    assert not (E / 'finish-started.json').exists(), 'Inspect partial cleanup/restart; no blind rerun'
    assert (E / 'recovery-verify-complete.json').is_file()
    save('finish-started.json', {'batch': B, 'new_ingress_or_model': False})
    state = json.loads((R / 'private/app-triage-recovery-3a.json').read_text())
    ids, inputs, checks = state['identities'], read('inputs.json'), []
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'tryaisoc.com/agents/auto-triage')
    run_ids = {key: str(uuid.uuid5(namespace, value['alert_row_id'] + ':auto-triage-v1')) for key,value in inputs.items()}
    def request(path, who='a', expected=200):
        headers = {'Authorization': 'Bearer ' + ids[who]['key']} if who else {}
        item = {'path': path, 'identity': who, 'expected': expected, 'status': None}
        checks.append(item)
        try:
            with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18000'+path, headers=headers),timeout=20) as res:
                code, body = res.status, res.read()
        except urllib.error.HTTPError as exc: code, body = exc.code, exc.read()
        item['status'] = code
        assert code == expected, (path,code,expected)
        return json.loads(body) if body else None
    def delivery():
        result = {}
        for alias in ['warm','concurrent']:
            base='/api/v1/investigations/'+run_ids[alias]
            run=request(base); events=request(base+'/events'); artifacts=request(base+'/artifacts')
            details=[request(base+'/artifacts/'+item['id']) for item in artifacts]
            assert run['status']=='completed' and run['total_tokens']==0
            assert run['event_count']==len(events['items'])==2 and len(artifacts)==5
            assert [item['seq'] for item in events['items']]==[-1,1]
            verdict=next(item for item in events['items'] if item['kind']=='triage_verdict')
            assert verdict['payload']['recovery']['schema_version']==1
            kinds={'organisation_memory_read','tenant_skill_read','knowledge_base_read','recent_dispositions_read','identity_context_read'}
            assert {item['kind'] for item in details}==kinds
            for item in details:
                blob=item['content'].encode()
                assert hashlib.sha256(blob).hexdigest()==item['sha256'] and len(blob)==item['size_bytes']
                assert item['event_id']==verdict['id'] and json.loads(item['content'])==verdict['payload'][item['kind']]
            alert=request('/api/v1/alerts/'+inputs[alias]['alert_row_id'])
            before=read('ingress-'+alias+'/normal-stored-alert.json')
            for key in ['raw_event','severity','status','disposition','resolved_at','priority','tags']:
                assert alert.get(key)==before.get(key),key
            result[alias]={'run':run,'events':events,'artifacts':artifacts,'artifact_details':details,'alert':alert}
        return result
    first=delivery()
    base='/api/v1/investigations/'+run_ids['warm']
    request(base,'b',404); request(base,'denied',403); request(base,None,401)
    unknown_base='/api/v1/investigations/'+run_ids['unknown']
    def unknown():
        run=request(unknown_base); events=request(unknown_base+'/events'); artifacts=request(unknown_base+'/artifacts')
        assert run['status'] in ['running','failed'] and run['total_tokens']==0
        assert len(events['items'])==1 and events['items'][0]['seq']==-1 and events['items'][0]['kind']=='triage_started'
        assert events['items'][0]['payload']['model_invocation_established'] is False and not artifacts
        return {'run':run,'events':events,'artifacts':artifacts}
    unknown_first=unknown()
    # Explicit new limitation: the existing incremental cursor rejects -1.
    request(unknown_base+'/events?since=-1',expected=422)
    save('api-before-restart.json',first);save('unknown-api-before-restart.json',unknown_first)
    agent=inspect('socai2-agents-1');save('restart-before.json',describe(agent))
    subprocess.run(['docker','restart','socai2-agents-1'],check=True,capture_output=True)
    for _ in range(45):
        current=inspect('socai2-agents-1')
        if current['State'].get('Health',{}).get('Status')=='healthy':break
        time.sleep(1)
    else: raise RuntimeError('Restart incomplete; inspect rather than rerunning')
    assert current['Id']==agent['Id'] and current['Image']==agent['Image']
    assert describe(current)['env_sha256']==describe(agent)['env_sha256'] and current['Mounts']==agent['Mounts']
    code="import os,json;from app.workers.fused_alert_consumer import worker_enabled;from app.workers.triage_delivery import lookup,claim;assert os.getuid()==10001 and not worker_enabled();print(json.dumps({'uid':os.getuid(),'worker_enabled':False,'recovery_imports':True}))"
    resident=json.loads(subprocess.check_output(['docker','exec','socai2-agents-1','python','-c',code]))
    second=delivery();assert second==first
    unknown_second=unknown();assert unknown_second['events']==unknown_first['events'] and unknown_second['artifacts']==unknown_first['artifacts']
    save('api-after-restart.json',second);save('unknown-api-after-restart.json',unknown_second)
    save('restart-after.json',{'runtime':describe(current),'resident':resident,'same_completed_api_delivery':True,
         'unknown_run_status_before':unknown_first['run']['status'],'unknown_run_status_after':unknown_second['run']['status'],
         'unknown_started_event_preserved':True,'negative_cursor_accepted':False})
    batch=SharedBatch(R);revoked={}
    for name,item in ids.items():
        batch.pg('SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='+lit(item['key_id'])+' AND tenant_id='+lit(item['tenant_id'])+' AND name='+lit('socai2-'+B+'-'+name)+';')
        request(base,name,401);revoked[name]=401
    save('key-lifecycle.json',{'operation_keys_deactivated':revoked,'reader_keys_rotated':0})
    readers = {}
    for stem, scope in READERS:
        path = R / ('private/app-' + stem + '-3a.json'); keyfile = R / ('private/' + stem + '-3a/keys.json')
        frozen = state['reader_credentials'][stem]
        assert sha(path) == frozen['state_sha256'] and sha(keyfile) == frozen['keys_sha256']
        old = json.loads(path.read_text()); metadata = {}
        for alias in ['reader_a', 'reader_b']:
            item = old['identities'][alias]
            value = json.loads(batch.pg('SET ROLE aisoc; SELECT row_to_json(t) FROM (SELECT id,tenant_id,is_active,scopes,expires_at FROM api_keys WHERE id=' + lit(item['key_id']) + ') t;').stdout)
            assert value == frozen['metadata'][alias] and value['scopes'] == [scope]
            metadata[alias] = value
        readers[stem] = {'original_hashes_preserved': True, 'metadata': metadata}
    assert sha(R / 'private/identity-graph-3a/config.json') == state['graph_config_sha256']
    counts={};deltas={'alerts':3,'investigation_runs':3,'investigation_events':5,'investigation_artifacts':10,'aisoc_shadow_decisions':2}
    for table in ['alerts']+TABLES:
        material=json.loads(batch.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM ("+MATERIAL_SQL+') t;').stdout) if table=='alerts' else rows(batch,table)
        old=read('prior-'+table+'.json');actual=[hashlib.sha256(row['material'].encode()).hexdigest() for row in material]
        assert not Counter(old)-Counter(actual),table
        assert len(actual)==len(old)+deltas.get(table,0),(table,len(actual),len(old))
        counts[table]={'old_preserved':len(old),'added':deltas.get(table,0),'total':len(actual)}
    gateway = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-litellm-1', 'python', '-c', METRICS]))
    assert gateway == read('gateway-before.json')
    start, end = read('environment-before.json'), snapshot()
    assert set(start['containers']) == set(end['containers']) and start['volumes'] == end['volumes']
    for name, item in start['containers'].items():
        if name != 'socai2-agents-1':
            assert end['containers'][name] == item, name
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip() == '134'
    assert describe(current)['env_sha256'] == read('runtime-baseline.json')['env_sha256']['agents']
    save('finish-http-checks.json', checks)
    save('environment-after.json', end)
    ingress_count=sum(len(read('ingress-'+alias+'/normal-http-checks.json')) for alias in inputs)
    post={'batch':B,'material_counts':counts,'images':{name:inspect('socai2-'+name+'-1')['Image'] for name in ['api','fusion','agents','actions']},
          'only_updated_and_restarted':['agents'],'other_containers_preserved':35,'containers_total':36,'volumes_preserved':18,'migrations_preserved':134,
          'gateway_before':read('gateway-before.json'),'gateway_after':gateway,'real_model_calls':0,'model_tokens':0,'new_cost_rows':0,
          'new_reader_keys':0,'reader_keys_preserved':10,'reader_credentials':readers,'operation_keys_deactivated':revoked,
          'compose_layers':19,'unit_tests_passed':read('tests-acceptance.json')['passed'],
          'http_explicit_count':ingress_count+len(checks),'http_ingress_checks':ingress_count,'http_finish_checks':len(checks),
          'broker_counts':read('recovery-verify-complete.json')['counts'],'resident_worker_enabled':False,'bounded_3a_10_02_accepted':True,
          'full_worker_admission_accepted':False,'model_quality_retested':False,'schema_ddl_changed':False,
          'negative_started_cursor_incremental_api_accepted':False,'next':'3A-10-03 SDK/request/stop budgets and negative started-event cursor before admission'}
    save('postconditions.json',post)
    print(json.dumps({k:v for k,v in post.items() if k!='reader_credentials'}))

if __name__=='__main__':main()
