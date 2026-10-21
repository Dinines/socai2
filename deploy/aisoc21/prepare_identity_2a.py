"""Marked source-identity fixtures; no schema or existing alert mutation."""
from pathlib import Path
import hashlib,json,secrets,subprocess,uuid
from shared_1b import SharedBatch
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2a-identity-20261020';B='2a-identity-20261020'
MATERIAL_SQL="SELECT id,row_to_json(x)::text AS material FROM (SELECT id,tenant_id,title,description,event_time AT TIME ZONE 'UTC' AS event_time_utc,raw_event,source_event_ids,external_id,dedup_hash,enrichment_data FROM alerts) x ORDER BY id"
def main():
    p=R/'private/app-identity-2a.json';assert not p.exists()
    b=SharedBatch(R);rows=json.loads(b.pg("SET ROLE aisoc; SELECT json_agg(t) FROM ("+MATERIAL_SQL+") t;").stdout)
    before=[{'id':x['id'],'sha256':hashlib.sha256(x['material'].encode()).hexdigest()} for x in rows]
    (E/'prior-alert-material.json').write_text(json.dumps(before,indent=2))
    ns=uuid.uuid5(uuid.NAMESPACE_URL,'socai2/'+B);state={'identities':{}}
    old=json.loads((R/'private/app-2a.json').read_text())['identities']['a']
    for name in ['a','b','legacy']:
        i={k:str(uuid.uuid5(ns,k+'/'+name)) for k in ['tenant_id','user_id','key_id']}
        if name=='legacy':i.update(tenant_id=old['tenant_id'],user_id=old['user_id'])
        i['key']='aisoc_'+secrets.token_hex(24);state['identities'][name]=i
    p.write_text(json.dumps(state,indent=2));p.chmod(0o600)
    for name,i in state['identities'].items():
        sql='SET ROLE aisoc; BEGIN; '
        if name!='legacy':
            sql+=f"INSERT INTO tenants(id,name,slug) VALUES ('{i['tenant_id']}','socai2 {B} {name}','socai2-{B}-{name}'); INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{i['user_id']}','{i['tenant_id']}','{B}-{name}@test.invalid','socai2-identity-{name}','!disabled-api-only','soc_analyst',true); "
        digest=hashlib.sha256(i['key'].encode()).hexdigest()
        sql+=f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{i['key_id']}','{i['tenant_id']}','{i['user_id']}','socai2-{B}-{name}','{i['key'][:12]}','{digest}','[\"alerts:read\",\"alerts:write\"]'::jsonb,NOW()+interval '2 hours'); COMMIT;"
        b.pg(sql)
    (E/'fixtures.json').write_text(json.dumps({n:{k:v for k,v in i.items() if k!='key'} for n,i in state['identities'].items()},indent=2));print(json.dumps({'new_test_tenants':2,'marked_keys':3,'prior_alert_material_rows':len(before),'schema_changed':False}))
if __name__=='__main__':main()
