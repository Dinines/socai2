"""Synthetic source-labelled context contract fixtures, existing PG tables only."""
from pathlib import Path
import hashlib,json,secrets,uuid
from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2c-context-20261020';B='2c-context-20261020'
TABLES=['assets','identity_privilege','asset_vulnerabilities','alert_asset_correlations']
def material_sql(table):
    assert table in TABLES
    return f'SELECT id,row_to_json(t)::text AS material FROM (SELECT * FROM {table}) t ORDER BY id'
def main():
    p=R/'private/app-context-2c.json';assert not p.exists(),'No fixture reseed'
    b=SharedBatch(R);(E/'environment-before.json').write_text(json.dumps(snapshot(),indent=2))
    for name,sql in [('alerts',MATERIAL_SQL)]+[(t,material_sql(t)) for t in TABLES]:
        rows=json.loads(b.pg('SET ROLE aisoc; SELECT COALESCE(json_agg(t),\'[]\'::json) FROM ('+sql+') t;').stdout)
        (E/('prior-'+name+'.json')).write_text(json.dumps([{'id':x['id'],'sha256':hashlib.sha256(x['material'].encode()).hexdigest()} for x in rows],indent=2))
    ns=uuid.uuid5(uuid.NAMESPACE_URL,'socai2/'+B);state={'identities':{}}
    for name in ['a','b','denied']:
        i={k:str(uuid.uuid5(ns,k+'/'+name)) for k in ['tenant_id','user_id','key_id']}
        if name=='denied':i.update({k:state['identities']['a'][k] for k in ['tenant_id','user_id']})
        i['key']='aisoc_'+secrets.token_hex(24);state['identities'][name]=i
    state['records']={k:str(uuid.uuid5(ns,'record/'+k)) for k in ['asset_a','asset_b','identity_a','identity_b','vuln_open','vuln_closed','link']}
    p.write_text(json.dumps(state,indent=2));p.chmod(0o600)
    fixture=R/'source/tests/porting/fixtures/processing-context-2c.json';source=json.loads(fixture.read_text());source_ref='sha256:'+hashlib.sha256(fixture.read_bytes()).hexdigest()
    for name,i in state['identities'].items():
        sql='SET ROLE aisoc; BEGIN; '
        if name!='denied':sql+=f"INSERT INTO tenants(id,name,slug) VALUES ('{i['tenant_id']}','socai2 {B} {name}','socai2-{B}-{name}'); INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{i['user_id']}','{i['tenant_id']}','{B}-{name}@test.invalid','socai2-context-{name}','!disabled-api-only','soc_analyst',true); "
        scopes=['settings:read'] if name=='denied' else ['alerts:read','alerts:write']
        sql+=f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{i['key_id']}','{i['tenant_id']}','{i['user_id']}','socai2-{B}-{name}','{i['key'][:12]}','{hashlib.sha256(i['key'].encode()).hexdigest()}','{json.dumps(scopes)}'::jsonb,NOW()+interval '3 hours'); COMMIT;";b.pg(sql)
    def lit(v):return "'"+str(v).replace("'","''")+"'"
    for name in ['a','b']:
        tenant=state['identities'][name]['tenant_id'];r=state['records'];meta=json.dumps({'source':source['source'],'source_ref':source_ref,'synthetic':True,'batch':B,'internet_facing':False})
        b.pg(f"SET ROLE aisoc; BEGIN; SELECT set_config('app.current_tenant_id','{tenant}',true); INSERT INTO assets(id,tenant_id,name,asset_type,criticality,metadata) VALUES ('{r['asset_'+name]}','{tenant}','SOCAI2-CONTEXT-HOST','host','{'high' if name=='a' else 'low'}',{lit(meta)}::jsonb); INSERT INTO identity_privilege(id,tenant_id,principal,privilege_tier,is_service,source) VALUES ('{r['identity_'+name]}','{tenant}','svc-context','{'admin' if name=='a' else 'standard'}',true,'socai2-context-fixture'); COMMIT;")
    tenant=state['identities']['a']['tenant_id'];r=state['records']
    for name,closed in [('vuln_open',False),('vuln_closed',True)]:
        meta=json.dumps({'source_ref':source_ref,'synthetic':True,'batch':B,'kev':closed})
        b.pg(f"SET ROLE aisoc; BEGIN; SELECT set_config('app.current_tenant_id','{tenant}',true); INSERT INTO asset_vulnerabilities(id,tenant_id,asset_id,title,severity,is_exploited,source,remediated_at,metadata) VALUES ('{r[name]}','{tenant}','{r['asset_a']}','Synthetic exposure {name}','high',true,'socai2-context-fixture',{'NOW()' if closed else 'NULL'},{lit(meta)}::jsonb); COMMIT;")
    safe={n:{k:v for k,v in i.items() if k!='key'} for n,i in state['identities'].items()}
    (E/'fixtures.json').write_text(json.dumps({'identities':safe,'records':state['records'],'source':source,'source_ref':source_ref},indent=2));print(json.dumps({'test_tenants':2,'keys':3,'assets':2,'identity_privileges':2,'vulnerabilities':2,'synthetic_not_vendor_export':True}))
if __name__=='__main__':main()
