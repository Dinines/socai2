"""Create only marked2A fixtures; preserve all existing data/config/runtime."""
from pathlib import Path
import hashlib,json,secrets,subprocess,uuid
from shared_1b import SharedBatch
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2a-20261020'

def snapshot():
    names=subprocess.check_output(['docker','ps','-aq']).decode().split()
    xs=json.loads(subprocess.check_output(['docker','inspect',*names]))
    return {'containers':{x['Name'].lstrip('/'): {'id':x['Id'],'image':x['Image'],'started_at':x['State']['StartedAt'],'status':x['State']['Status'],'restart_count':x['RestartCount'],'mounts':x['Mounts']} for x in xs},'volumes':subprocess.check_output(['docker','volume','ls','-q']).decode().split()}

def main():
    p=R/'private/app-2a.json';assert not p.exists(),'No fixture reseed'
    E.mkdir(exist_ok=False);(E/'environment-before.json').write_text(json.dumps(snapshot(),indent=2))
    b=SharedBatch(R);ns=uuid.uuid5(uuid.NAMESPACE_URL,'socai2/2a-20261020');state={'identities':{}}
    for name in ['a','b']:
        item={k:str(uuid.uuid5(ns,k+'/'+name)) for k in ['tenant_id','user_id','key_id']};item['key']='aisoc_'+secrets.token_hex(24);state['identities'][name]=item
    p.write_text(json.dumps(state,indent=2));p.chmod(0o600)
    for name,i in state['identities'].items():
        keyhash=hashlib.sha256(i['key'].encode()).hexdigest()
        b.pg(f"SET ROLE aisoc; BEGIN; INSERT INTO tenants(id,name,slug) VALUES ('{i['tenant_id']}','socai2 2a {name}','socai2-2a-20261020-{name}');"
             f"INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{i['user_id']}','{i['tenant_id']}','2a-20261020-{name}@test.invalid','socai2-2a-{name}','!disabled-api-only','soc_analyst',true);"
             f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('{i['key_id']}','{i['tenant_id']}','{i['user_id']}','socai2-2a-20261020-{name}','{i['key'][:12]}','{keyhash}','[\"alerts:read\",\"alerts:write\"]'::jsonb,NOW()+interval '2 hours'); COMMIT;")
    safe={name:{k:v for k,v in item.items() if k!='key'} for name,item in state['identities'].items()}
    (E/'fixtures.json').write_text(json.dumps(safe,indent=2));print(json.dumps({'new_test_tenants':2,'new_test_api_keys':2,'business_configuration_changed':False}))
if __name__=='__main__':main()
