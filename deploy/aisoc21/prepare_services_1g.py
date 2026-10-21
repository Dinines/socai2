"""Host21 batch1G scoped configs and uniquely marked fixtures; no legacy data changes."""
from pathlib import Path
import base64,hashlib,hmac,json,secrets,time,uuid
from shared_1b import SharedBatch
ROOT=Path('/opt/sting-aisoc-socai2')
BATCH='1g-20261020'


def main():
 b=SharedBatch(ROOT);state_path=ROOT/'private/app-1g.json'
 assert not state_path.exists(),'Retain existing batch; no reseed/rotation'
 previous=json.loads((ROOT/'private/app-1f.json').read_text())
 gateway=dict(s.split('=',1) for s in (ROOT/'private/gateway-client-1e.env').read_text().splitlines())
 namespace=uuid.uuid5(uuid.NAMESPACE_URL,'socai2/'+BATCH)
 state={'agents_token':secrets.token_hex(32),'actions_token':secrets.token_hex(32),'identities':{}}
 def jwt(claims):
  enc=lambda x:base64.urlsafe_b64encode(x).rstrip(b'=').decode()
  head=enc(b'{"alg":"HS256","typ":"JWT"}');body=enc(json.dumps(claims).encode());raw=head+'.'+body
  return raw+'.'+enc(hmac.new(previous['secret_key'].encode(),raw.encode(),hashlib.sha256).digest())
 for name in ['a','b']:
  item={k:str(uuid.uuid5(namespace,k+'-'+name)) for k in ['tenant_id','user_id','case_id','key_id']}
  item['key']='aisoc_'+secrets.token_hex(24)
  item['jwt']=jwt({'type':'access','sub':item['user_id'],'tenant_id':item['tenant_id'],'exp':int(time.time())+3600,'iat':int(time.time())})
  state['identities'][name]=item
 state_path.write_text(json.dumps(state,indent=2)+'\n');state_path.chmod(0o600)
 pg='postgresql://aisoc_app:'+b.config['app_password']+'@192.168.1.21:5432/aisoc?sslmode=verify-full'
 common={'ENV':'production','ENVIRONMENT':'production','DATABASE_URL':pg,'PGSSLROOTCERT':'/run/certs/ca.crt','AISOC_DEV_MODE':'false','AISOC_DEV_AUTH_BYPASS':'false','AISOC_PUBLISHED_BIND_ADDRS':'127.0.0.1','AISOC_SCOPED_BASELINE':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','OTEL_EXPORTER':'none'}
 agents={**common,**gateway,'SECRET_KEY':previous['secret_key'],'AISOC_AGENTS_SERVICE_TOKEN':state['agents_token'],
  'AISOC_AGENT_KAFKA_DISABLE':'1','KAFKA_CONSUMER_GROUP':'socai2-agents-triage','KAFKA_TOPIC_ALERTS_FUSED':'socai2.alerts.fused',
  'AISOC_AGENT_ESCALATE_TO_GRAPH':'0','AISOC_AGENT_MEMORY_SUPPRESSION':'0','AISOC_AGENT_MEMORY_WRITEBACK':'0',
  'AISOC_HUNT_SCHEDULER_DISABLE':'1','AISOC_PLAYBOOK_SWEEPER_DISABLE':'1','AISOC_INVESTIGATION_REAPER_DISABLE':'1',
  'AISOC_PLAYBOOK_SEED_DISABLE':'1','AISOC_ATTCK_STARTUP_DISABLE':'1','AISOC_ATTCK_INDEX_DISABLE':'1','AISOC_ATTCK_CDN_FETCH':'0',
  'AISOC_GATEWAY_COST_TRUST':'0','AISOC_INVESTIGATE_USE_ROUTER':'0','AISOC_INVESTIGATION_MAX_SECONDS':'180','AISOC_INVESTIGATOR_MAX_COMPLETION_TOKENS':'1024',
  'API_SERVICE_URL':'http://api:8000','ENRICHMENT_SERVICE_URL':'http://127.0.0.1:9',
  'REALTIME_URL':'http://127.0.0.1:9','REDIS_URL':'redis://socai2:'+b.config['redis_password']+'@192.168.1.21:6379/10',
  'INSTITUTIONAL_MEMORY_STORE_PATH':'/tmp/institutional-memory.json','PLAYBOOK_STORE_DIR':'/tmp/playbooks'}
 actions={**common,'AISOC_ACTIONS_SERVICE_TOKEN':state['actions_token'],'AISOC_ACTIONS_REQUIRE_PRINCIPAL':'true','AISOC_ACTIONS_REQUIRE_APPROVER':'true','AISOC_FEATURE_CHATOPS_VERIFY':'false','AISOC_FEATURE_MAILBOX_REMEDIATION':'false','AISOC_MATURITY_TIER':'L0','AISOC_API_BASE_URL':'http://api:8000','REDIS_URL':'redis://socai2:'+b.config['redis_password']+'@192.168.1.21:6379/11'}
 for name,values in [('agents-1g.env',agents),('actions-1g.env',actions)]:
  p=ROOT/'private'/name;p.write_text(''.join(k+'='+v+'\n' for k,v in values.items()));p.chmod(0o600)
 for name,item in state['identities'].items():
  key_hash=hashlib.sha256(item['key'].encode()).hexdigest()
  b.pg(f"SET ROLE aisoc; INSERT INTO tenants(id,name,slug) VALUES ('{item['tenant_id']}','socai2 {BATCH} {name}','socai2-{BATCH}-{name}');"
       f"INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES ('{item['user_id']}','{item['tenant_id']}','{BATCH}-{name}@test.invalid','socai2-1g-{name}','!disabled-api-only','soc_analyst',true);"
       f"INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes) VALUES ('{item['key_id']}','{item['tenant_id']}','{item['user_id']}','socai2-{BATCH}-{name}','{item['key'][:12]}','{key_hash}','[\"cases:read\",\"alerts:read\"]'::jsonb);"
       f"INSERT INTO aisoc_cases(id,tenant_id,title,description,tags) VALUES ('{item['case_id']}','{item['tenant_id']}','socai2 {BATCH} {name}','Marked baseline fixture','{{\"batch\":\"{BATCH}\"}}'::jsonb);")
 safe={'batch':BATCH,'identities':{name:{k:v for k,v in item.items() if k not in ['key','jwt']} for name,item in state['identities'].items()},'owner_credentials_not_in_runtime':True,'automatic_workers_disabled':True,'knowledge_embedding_and_vendor_adapters_not_connected':True}
 (ROOT/f'evidence/{BATCH}/prepared.json').write_text(json.dumps(safe,indent=2)+'\n');print(json.dumps(safe))

if __name__=='__main__':main()
