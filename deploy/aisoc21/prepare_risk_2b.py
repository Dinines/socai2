"""Create isolated 2B risk fixtures and preserve prior immutable materials."""
from pathlib import Path
import hashlib,json,secrets,uuid
from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2b-risk-20261020';B='2b-risk-20261020'
def main():
    p=R/'private/app-risk-2b.json';assert not p.exists(),'No fixture reseed'
    E.mkdir(exist_ok=False);(E/'environment-before.json').write_text(json.dumps(snapshot(),indent=2))
    b=SharedBatch(R)
    rows=json.loads(b.pg('SET ROLE aisoc; SELECT json_agg(t) FROM ('+MATERIAL_SQL+') t;').stdout)
    (E/'prior-alert-material.json').write_text(json.dumps([{'id':x['id'],'sha256':hashlib.sha256(x['material'].encode()).hexdigest()} for x in rows],indent=2))
    state={'identities':{}};ns=uuid.uuid5(uuid.NAMESPACE_URL,'socai2/'+B)
    for name in ['a','b']:
        i={k:str(uuid.uuid5(ns,k+'/'+name)) for k in ['tenant_id','user_id','key_id']};i['key']='aisoc_'+secrets.token_hex(24);state['identities'][name]=i
    p.write_text(json.dumps(state,indent=2));p.chmod(0o600)
    for name,i in state['identities'].items():
        digest=hashlib.sha256(i['key'].encode()).hexdigest()
        b.pg(f"SET ROLE aisoc; BEGIN; INSERT INTO tenants(id,name,slug) VALUES ('{i['tenant_id']}','socai2 {B} {name}','socai2-{B}-{name}'); INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{i['user_id']}','{i['tenant_id']}','{B}-{name}@test.invalid','socai2-risk-{name}','!disabled-api-only','soc_analyst',true); INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{i['key_id']}','{i['tenant_id']}','{i['user_id']}','socai2-{B}-{name}','{i['key'][:12]}','{digest}','[\"alerts:read\",\"alerts:write\"]'::jsonb,NOW()+interval '4 hours'); COMMIT;")
    (E/'fixtures.json').write_text(json.dumps({n:{k:v for k,v in i.items() if k!='key'} for n,i in state['identities'].items()},indent=2))
    print(json.dumps({'new_test_tenants':2,'prior_material_rows':len(rows),'keys':2}))
if __name__=='__main__':main()
