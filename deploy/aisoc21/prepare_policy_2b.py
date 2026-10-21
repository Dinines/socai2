"""Create only isolated policy fixtures; retain prior alert/rule digests."""
from pathlib import Path
import hashlib,json,secrets,uuid
from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2b-policy-20261020';B='2b-policy-20261020'
POLICY_SQL='SELECT tenant_id,row_to_json(t)::text AS material FROM (SELECT * FROM aisoc_business_context_rule_sets) t ORDER BY tenant_id'
def main():
    p=R/'private/app-policy-2b.json';assert not p.exists(),'No fixture reseed'
    b=SharedBatch(R)
    (E/'environment-before.json').write_text(json.dumps(snapshot(),indent=2))
    for name,sql,col in [('prior-alert-material.json',MATERIAL_SQL,'id'),('prior-policy-material.json',POLICY_SQL,'tenant_id')]:
        rows=json.loads(b.pg('SET ROLE aisoc; SELECT COALESCE(json_agg(t),\'[]\'::json) FROM ('+sql+') t;').stdout)
        (E/name).write_text(json.dumps([{'id':x[col],'sha256':hashlib.sha256(x['material'].encode()).hexdigest()} for x in rows],indent=2))
    ns=uuid.uuid5(uuid.NAMESPACE_URL,'socai2/'+B);state={'identities':{}}
    for name in ['a','b','read_a']:
        i={k:str(uuid.uuid5(ns,k+'/'+name)) for k in ['tenant_id','user_id','key_id']}
        if name=='read_a':i.update({k:state['identities']['a'][k] for k in ['tenant_id','user_id']})
        i['key']='aisoc_'+secrets.token_hex(24);state['identities'][name]=i
    p.write_text(json.dumps(state,indent=2));p.chmod(0o600)
    for name,i in state['identities'].items():
        sql='SET ROLE aisoc; BEGIN; '
        if name!='read_a':sql+=f"INSERT INTO tenants(id,name,slug) VALUES ('{i['tenant_id']}','socai2 {B} {name}','socai2-{B}-{name}'); INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{i['user_id']}','{i['tenant_id']}','{B}-{name}@test.invalid','socai2-policy-{name}','!disabled-api-only','soc_analyst',true); "
        scopes=['settings:read'] if name=='read_a' else ['settings:read','settings:write','alerts:read','alerts:write']
        sql+=f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{i['key_id']}','{i['tenant_id']}','{i['user_id']}','socai2-{B}-{name}','{i['key'][:12]}','{hashlib.sha256(i['key'].encode()).hexdigest()}','{json.dumps(scopes)}'::jsonb,NOW()+interval '3 hours'); COMMIT;"
        b.pg(sql)
    (E/'fixtures.json').write_text(json.dumps({n:{k:v for k,v in i.items() if k!='key'} for n,i in state['identities'].items()},indent=2));print(json.dumps({'test_tenants':2,'keys':3}))
if __name__=='__main__':main()
