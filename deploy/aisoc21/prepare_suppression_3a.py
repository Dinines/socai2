"""Isolated3A identities and old material hashes; no schema or shared-service edits."""
from pathlib import Path
import hashlib,json,secrets,uuid
from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/3a-suppression-20261020';B='3a-suppression-20261020'
TABLES=['investigation_runs','investigation_events','aisoc_business_context_rule_sets']
def rows(b,t):
    assert t in TABLES
    return json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(x),'[]'::json) FROM (SELECT row_to_json(t)::text AS material FROM "+t+" t ORDER BY row_to_json(t)::text) x;").stdout)
def main():
    p=R/'private/app-suppression-3a.json';assert not p.exists(),'No fixture reseed'
    E.mkdir(exist_ok=True,mode=0o700);E.chmod(0o700);b=SharedBatch(R)
    (E/'environment-before.json').write_text(json.dumps(snapshot(),indent=2))
    for name,data in [('alerts',json.loads(b.pg("SET ROLE aisoc; SELECT COALESCE(json_agg(t),'[]'::json) FROM ("+MATERIAL_SQL+") t;").stdout))]+[(t,rows(b,t)) for t in TABLES]:
        (E/('prior-'+name+'.json')).write_text(json.dumps([hashlib.sha256(x['material'].encode()).hexdigest() for x in data],indent=2))
    ns=uuid.uuid5(uuid.NAMESPACE_URL,'socai2/'+B);ids={}
    for n in ['a','b','denied']:
        i={k:str(uuid.uuid5(ns,k+'/'+n)) for k in ['tenant_id','user_id','key_id']}
        if n=='denied':i.update({k:ids['a'][k] for k in ['tenant_id','user_id']})
        i['key']='aisoc_'+secrets.token_hex(24);ids[n]=i
    p.write_text(json.dumps({'identities':ids},indent=2));p.chmod(0o600)
    for n,i in ids.items():
        sql='SET ROLE aisoc; BEGIN; '
        if n!='denied':sql+=f"INSERT INTO tenants(id,name,slug) VALUES ('{i['tenant_id']}','socai2 {B} {n}','socai2-{B}-{n}'); INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{i['user_id']}','{i['tenant_id']}','{B}-{n}@test.invalid','socai2-suppression-{n}','!disabled-api-only','soc_analyst',true); "
        scopes=['settings:read'] if n=='denied' else ['alerts:read','alerts:write','cases:read','settings:read','settings:write']
        sql+=f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{i['key_id']}','{i['tenant_id']}','{i['user_id']}','socai2-{B}-{n}','{i['key'][:12]}','{hashlib.sha256(i['key'].encode()).hexdigest()}','{json.dumps(scopes)}'::jsonb,NOW()+interval '3 hours'); COMMIT;";b.pg(sql)
    item=json.loads(__import__('subprocess').check_output(['docker','inspect','socai2-agents-1']))[0]
    f=R/'private/probe-suppression-3a.env';values=dict(x.split('=',1) for x in item['Config']['Env'] if '=' in x)
    fusion=json.loads(__import__('subprocess').check_output(['docker','inspect','socai2-fusion-1']))[0]
    values.update({k:v for x in fusion['Config']['Env'] if '=' in x for k,v in [x.split('=',1)] if k.startswith('KAFKA_')})
    f.write_text(''.join(k+'='+v+'\n' for k,v in values.items()));f.chmod(0o600)
    print(json.dumps({'tenants':2,'keys':3,'prior_materials_hashed':4,'runtime_env_snapshot_private':True}))
if __name__=='__main__':main()
