"""Isolated historical IOC import; no current-maliciousness claim."""
from pathlib import Path
import hashlib,json,secrets,uuid
from shared_1b import SharedBatch
from prepare_2a import snapshot
from prepare_identity_2a import MATERIAL_SQL
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2c-ioc-20261020';B='2c-ioc-20261020'
IOC_SQL='SELECT id,row_to_json(t)::text AS material FROM (SELECT * FROM threat_intel_iocs) t ORDER BY id'
def main():
    p=R/'private/app-ioc-2c.json';assert not p.exists(),'No reseeding completed fixtures'
    b=SharedBatch(R);(E/'environment-before.json').write_text(json.dumps(snapshot(),indent=2))
    for filename,sql in [('prior-alert-material.json',MATERIAL_SQL),('prior-ioc-material.json',IOC_SQL)]:
        rows=json.loads(b.pg('SET ROLE aisoc; SELECT COALESCE(json_agg(t),\'[]\'::json) FROM ('+sql+') t;').stdout)
        (E/filename).write_text(json.dumps([{'id':r['id'],'sha256':hashlib.sha256(r['material'].encode()).hexdigest()} for r in rows],indent=2))
    ns=uuid.uuid5(uuid.NAMESPACE_URL,'socai2/'+B);state={'identities':{}}
    for name in ['a','b']:
        i={k:str(uuid.uuid5(ns,k+'/'+name)) for k in ['tenant_id','user_id','key_id']};i['key']='aisoc_'+secrets.token_hex(24);state['identities'][name]=i
    state['ioc_ids']={name:str(uuid.uuid5(ns,'ioc/'+name)) for name in ['historical','expired']}
    p.write_text(json.dumps(state,indent=2));p.chmod(0o600)
    for name,i in state['identities'].items():
        b.pg(f"SET ROLE aisoc; BEGIN; INSERT INTO tenants(id,name,slug) VALUES ('{i['tenant_id']}','socai2 {B} {name}','socai2-{B}-{name}'); INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{i['user_id']}','{i['tenant_id']}','{B}-{name}@test.invalid','socai2-ioc-{name}','!disabled-api-only','soc_analyst',true); INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{i['key_id']}','{i['tenant_id']}','{i['user_id']}','socai2-{B}-{name}','{i['key'][:12]}','{hashlib.sha256(i['key'].encode()).hexdigest()}','[\"alerts:read\",\"alerts:write\",\"threat_intel:read\"]'::jsonb,NOW()+interval '3 hours'); COMMIT;")
    source=json.loads((R/'source/tests/porting/fixtures/historical-ioc-2c.json').read_text())
    def lit(v):return "'"+str(v).replace("'","''")+"'"
    tenant=state['identities']['a']['tenant_id'];context=json.dumps({**source,'batch':B,'import_purpose':'historical evidence, not current reputation'})
    b.pg(f"SET ROLE aisoc; INSERT INTO threat_intel_iocs(id,tenant_id,ioc_type,value,confidence,severity,tlp,source,source_ref,first_seen,last_seen,tags,context) VALUES ('{state['ioc_ids']['historical']}','{tenant}','domain',{lit(source['value'])},50,'medium','white','socai2-historical-report',{lit(source['source_url'])},{lit(source['observed_at'])},{lit(source['observed_at'])},ARRAY['{B}','historical-reference'],{lit(context)}::jsonb); INSERT INTO threat_intel_iocs(id,tenant_id,ioc_type,value,confidence,source,expires_at,tags,context) VALUES ('{state['ioc_ids']['expired']}','{tenant}','domain','expired.socai2.invalid',50,'socai2-synthetic-expired',NOW()-interval '1 day',ARRAY['{B}'],'{{\"synthetic\":true}}');")
    (E/'fixtures.json').write_text(json.dumps({'identities':{n:{k:v for k,v in i.items() if k!='key'} for n,i in state['identities'].items()},'ioc_ids':state['ioc_ids'],'historical_source':source},indent=2));print(json.dumps({'tenants':2,'keys':2,'historical_ioc_rows':1,'synthetic_expired_ioc_rows':1}))
if __name__=='__main__':main()
