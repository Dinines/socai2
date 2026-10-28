"""Host21 operator launcher: bounded temporary keys, real HTTP runner, final revoke."""
import hashlib,json,os
from pathlib import Path
import secrets,subprocess,sys
from uuid import uuid4
from datetime import UTC,datetime,timedelta

ROOT=Path(__file__).resolve().parent
BATCH='INVHTTP-20261028-01'
PRIVATE=Path('/opt/sting-aisoc-socai2/private')/(BATCH+'-tokens.json')
OUTPUT=ROOT/'results'
CLIENT=Path('/opt/sting-aisoc-socai2/investigation-v2/20261028-r1/scripts/investigation_client.py')
TENANTS=['f6a5c700-69b8-44fc-8238-609362fb1a9f','53824f24-d1d4-5820-8147-f6cfda8a1247']
SCOPES=['alerts:read','alerts:write','cases:read','cases:write','investigation:run']

def pg(sql):
    name='spirithub-postgres-1'
    container=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    env=dict(x.split('=',1) for x in container['Config']['Env'])
    r=subprocess.run(['docker','exec','-i',name,'psql','-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-U',env['POSTGRES_USER'],'-d','aisoc'],input=sql,text=True,capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr[:600])
    return r.stdout.strip()

os.umask(0o077)
assert not PRIVATE.exists() and not OUTPUT.exists(),'batch_already_prepared'
keys={};statements=[];receipts=[]
expires=(datetime.now(UTC)+timedelta(hours=2)).isoformat()
for tenant in TENANTS:
    raw='aisoc_'+secrets.token_hex(24);identity=str(uuid4());prefix=raw[:12]
    keys[tenant]=raw
    receipts.append({'id':identity,'tenant_id':tenant,'name':BATCH,'scopes':SCOPES,'expires_at':expires})
    statements.append(f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,is_active,expires_at,created_at) VALUES ('{identity}','{tenant}',NULL,'{BATCH}','{prefix}','{hashlib.sha256(raw.encode()).hexdigest()}','{json.dumps(SCOPES)}'::jsonb,true,'{expires}',now());")
ids=','.join("'"+x['id']+"'" for x in receipts)
record={'batch':BATCH,'keys':receipts,'raw_keys_logged':False,'roles_or_users_changed':False}
status=1
try:
    with PRIVATE.open('x',encoding='utf-8') as stream:json.dump(keys,stream)
    PRIVATE.chmod(0o600)
    pg('BEGIN;'+''.join(statements)+'COMMIT;')
    record['created']=True
    (ROOT/'credential-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    command=[sys.executable,'-B',str(ROOT/'investigation_http_cases.py'),'--manifest',str(ROOT/'cases.json'),'--tokens',str(PRIVATE),'--output',str(OUTPUT),'--batch',BATCH,'--client',str(CLIENT)]
    status=subprocess.run(command).returncode
finally:
    record['revoked']=json.loads(pg(f"UPDATE api_keys SET is_active=false WHERE id IN ({ids}) AND name='{BATCH}'; SELECT json_agg(json_build_object('id',id,'active',is_active)) FROM api_keys WHERE id IN ({ids});"))
    if PRIVATE.exists():PRIVATE.unlink()
    record['private_token_file_removed']=not PRIVATE.exists()
    record['runner_exit']=status
    (ROOT/'credential-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'batch':BATCH,'runner_exit':status,'test_keys_revoked':all(not x['active'] for x in record['revoked'] or []),'private_token_file_removed':record['private_token_file_removed']}),flush=True)
raise SystemExit(status)
