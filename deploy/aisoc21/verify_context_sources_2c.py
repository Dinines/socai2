"""Host21 real API/Agents missing-source probes with short-lived scoped keys.

No alert submission, LLM, shared outage, runtime configuration or schema change.
Keys are revoked in finally; fixture identities and evidence remain for audit.
The scoped-key Agents probe is a subprocess-only substitution, NOT production
workload-identity wiring or a demonstration of live lake tenant isolation.
"""
from pathlib import Path
import hashlib
import json
import secrets
import subprocess
import urllib.error
import urllib.request
import uuid

from prepare_identity_2a import MATERIAL_SQL
from prepare_2a import snapshot
from shared_1b import SharedBatch

R = Path('/opt/sting-aisoc-socai2')
E = R / 'evidence/2c-sources-20261020'
B = '2c-sources-20261020'


def main():
    E.mkdir(parents=True, exist_ok=True, mode=0o700)
    p = R / 'private/app-sources-2c.json'
    assert not p.exists(), 'Inspect existing attempt; never reseed or replay blindly'
    before = snapshot(); (E/'environment-before.json').write_text(json.dumps(before, indent=2))
    b = SharedBatch(R)
    def materials():
        return json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM ("+MATERIAL_SQL+") t;").stdout)
    prior = materials()
    prior_sha = hashlib.sha256(json.dumps(prior,sort_keys=True).encode()).hexdigest()
    (E/'alert-material-before.json').write_text(json.dumps({'rows':len(prior),'sha256':prior_sha},indent=2))
    ns = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/'+B)
    ids = {}
    for n in ['a', 'b', 'denied']:
        ids[n] = {k: str(uuid.uuid5(ns, k+'/'+n)) for k in ['tenant_id', 'user_id', 'key_id']}
        if n == 'denied':
            ids[n].update({k: ids['a'][k] for k in ['tenant_id', 'user_id']})
        ids[n]['key'] = 'aisoc_'+secrets.token_hex(24)
    p.write_text(json.dumps({'identities':ids}, indent=2)); p.chmod(0o600)
    checks = []; observations = {}
    def req(path, identity=None, body=None, expected=200):
        key = ids[identity]['key'] if identity else None
        r = urllib.request.Request('http://127.0.0.1:18000/api/v1/graph/investigate/'+path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json', **({'Authorization':'Bearer '+key} if key else {})})
        try:
            with urllib.request.urlopen(r, timeout=45) as response:
                code, data = response.status, json.load(response)
        except urllib.error.HTTPError as error:
            code, data = error.code, json.load(error)
        checks.append({'path':path,'identity':identity,'status':code,'expected':expected})
        (E/'http-checks.json').write_text(json.dumps(checks, indent=2))
        assert code == expected, (code, expected)
        return data
    def agent_probe(identity=None):
        # Execute the installed production tool method in a separate process.
        # API key (if provided) is passed on stdin, never argv or logs.
        content = '''import asyncio,json,os,sys
from app.tools.investigation import call_investigation_tool
s=json.loads(sys.stdin.readline())
if s.get('key'): os.environ['AISOC_API_SERVICE_TOKEN']=s['key']
result=asyncio.run(call_investigation_tool('entity_timeline',s['tenant'],hostname='SOCAI2-SOURCES-HOST',hours=1,limit=2))
print(json.dumps(result))
'''
        # Python -c needs stdin for the private JSON, not for the program itself.
        state={'tenant':ids['a']['tenant_id'] if identity is None else ids[identity]['tenant_id']}
        if identity: state['key']=ids[identity]['key']
        result=subprocess.run(['docker','exec','-i','socai2-agents-1','python','-c',content],input=json.dumps(state)+'\n',text=True,capture_output=True,timeout=50)
        assert result.returncode==0, 'Agents probe failed; inspect without printing secrets'
        # structlog may write preceding diagnostic lines; the result is last.
        return json.loads(result.stdout.splitlines()[-1])
    try:
        for n,i in ids.items():
            sql='SET ROLE aisoc; BEGIN; '
            if n!='denied':
                sql+=f"INSERT INTO tenants(id,name,slug) VALUES ('{i['tenant_id']}','socai2 {B} {n}','socai2-{B}-{n}'); INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{i['user_id']}','{i['tenant_id']}','{B}-{n}@test.invalid','socai2-sources-{n}','!disabled-api-only','soc_analyst',true); "
            scopes=['settings:read'] if n=='denied' else ['lake:query']
            sql+=f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{i['key_id']}','{i['tenant_id']}','{i['user_id']}','socai2-{B}-{n}','{i['key'][:12]}','{hashlib.sha256(i['key'].encode()).hexdigest()}','{json.dumps(scopes)}'::jsonb,NOW()+interval '1 hour'); COMMIT;"
            b.pg(sql)
        for n in ['a','b']:
            observations['tools_'+n]=req('tools',n)
            observations['query_'+n]=req('query',n,{'tool':'entity_timeline','args':{'hostname':'SOCAI2-SOURCES-HOST','hours':1,'limit':2}})
        observations['injected_tenant']=req('query','a',{'tool':'entity_timeline','args':{'hostname':'SOCAI2-SOURCES-HOST','tenant_id':ids['b']['tenant_id']}})
        observations['missing_data_class']=req('query','a',{'tool':'process_tree','args':{'hostname':'SOCAI2-SOURCES-HOST'}})
        observations['unknown_tool']=req('query','a',{'tool':'socai2_unknown','args':{}})
        req('query',None,{'tool':'entity_timeline','args':{}},401)
        req('query','denied',{'tool':'entity_timeline','args':{}},403)
        for n in ['query_a','query_b','injected_tenant']:
            x=observations[n]; assert x['available'] is False and x['rows']==[] and x['row_count']==0
            assert 'lookup failure' in x['reason'].lower()
        observations['agent_effective_configuration']=agent_probe()
        assert observations['agent_effective_configuration']['available'] is False
        for n in ['a','b']:
            observations['agent_scoped_key_'+n]=agent_probe(n)
            assert observations['agent_scoped_key_'+n]==observations['query_'+n]
        (E/'tool-observations.json').write_text(json.dumps(observations,indent=2))
    finally:
        # Safe even if fixture creation failed partway. Never delete fixture rows.
        keys=','.join("'"+i['key_id']+"'" for i in ids.values())
        b.pg(f'SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id IN ({keys});')
        for n in ids:
            req('tools',n,expected=401)
        after_material = materials()
        assert prior == after_material, 'Existing alert materials changed'
        assert b.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
        after=snapshot()
        (E/'environment-after.json').write_text(json.dumps(after,indent=2))
        assert before==after, 'Unexpected container/volume change'
        safe={n:{k:v for k,v in i.items() if k!='key'} for n,i in ids.items()}
        (E/'postconditions.json').write_text(json.dumps({'identities':safe,'test_keys_revoked':3,
            'containers_and_volumes_unchanged':True,'containers':len(before['containers']),
            'volumes':len(before['volumes']),'http_checks':len(checks),'agents_process_calls':3,
            'old_alert_material_rows_preserved':len(prior),'alert_material_sha256':prior_sha,'migrations_unchanged':134,
            'runtime_configuration_changed':False,'new_alerts_submitted':0,'model_calls':0},indent=2))
    print(json.dumps({'http_checks':len(checks),'agents_process_calls':3,'missing_source_returns_unavailable':True,
                      'live_data_consumption_accepted':False,'keys_revoked':3}))


def finish_only():
    """Recover final assertions without recreating keys or repeating tool probes."""
    b=SharedBatch(R); ids=json.loads((R/'private/app-sources-2c.json').read_text())['identities']
    checks=json.loads((E/'http-checks.json').read_text())
    assert len(checks)==12 and all(c['status']==c['expected'] for c in checks)
    observations=json.loads((E/'tool-observations.json').read_text())
    assert all(observations[n]['available'] is False for n in ['query_a','query_b','injected_tenant','missing_data_class','unknown_tool','agent_effective_configuration','agent_scoped_key_a','agent_scoped_key_b'])
    for n in ['a','b']: assert observations['agent_scoped_key_'+n]==observations['query_'+n]
    prior=json.loads((E/'alert-material-before.json').read_text())
    current=json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM ("+MATERIAL_SQL+") t;").stdout)
    assert len(current)==prior['rows'] and hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest()==prior['sha256']
    assert b.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    before=json.loads((E/'environment-before.json').read_text()); after=snapshot()
    (E/'environment-after-recheck.json').write_text(json.dumps(after,indent=2)); assert before==after
    for n,i in ids.items():
        assert b.pg("SELECT NOT is_active FROM api_keys WHERE id='"+i['key_id']+"';").stdout.strip()=='t'
        request=urllib.request.Request('http://127.0.0.1:18000/api/v1/graph/investigate/tools',headers={'Authorization':'Bearer '+i['key']})
        try: urllib.request.urlopen(request,timeout=10); raise AssertionError('Revoked key accepted')
        except urllib.error.HTTPError as error: assert error.code==401
    safe={n:{k:v for k,v in i.items() if k!='key'} for n,i in ids.items()}
    value={'identities':safe,'test_keys_revoked':3,'http_checks':12,'revoked_key_rechecks':3,'agents_process_calls':3,
        'containers_and_volumes_unchanged_on_recheck':True,'containers':len(before['containers']),'volumes':len(before['volumes']),
        'old_alert_material_rows_preserved':prior['rows'],'alert_material_sha256':prior['sha256'],'migrations_unchanged':134,
        'runtime_configuration_changed':False,'new_alerts_submitted':0,'model_calls':0,
        'initial_final_snapshot_assertion_failed':True,'cause':'Not established; concurrent transient test container was possible. Exact before/recheck snapshots match; no fixture or tool replay.'}
    (E/'postconditions.json').write_text(json.dumps(value,indent=2)); print(json.dumps(value))


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--finish-only']: finish_only()
    elif not sys.argv[1:]: main()
    else: raise SystemExit('Usage: verify_context_sources_2c.py [--finish-only]')
