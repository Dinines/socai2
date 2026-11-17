"""Read-only production/candidate inventory; never print secret values."""
import json,subprocess,urllib.parse
from pathlib import Path

def call(args):return subprocess.check_output(args,text=True,timeout=20)
names=[n for n in call(['docker','ps','-a','--format','{{.Names}}']).splitlines() if n.startswith('socai2')]
rows=json.loads(call(['docker','inspect',*names]));result=[]
selected={'AISOC_ALERT_STORE_SCHEMA','AISOC_ALERT_SINK_ENABLED','AISOC_LAKE_WRITER_ENABLED','SOCAI2_HTTP_CONTEXT_FILE','SOCAI2_INVESTIGATION_POLICY','SOCAI2_KNOWLEDGE_PROFILE','SOCAI2_ANALYSIS_TASKS_CONFIG_FILE','SOCAI2_SERVICE_DATABASE_NAME','SOCAI2_LAKE_DATABASE','CLICKHOUSE_DATABASE','CLICKHOUSE_USER','KAFKA_BOOTSTRAP_SERVERS','KAFKA_TOPIC_ALERTS_RAW','KAFKA_TOPIC_ALERTS_FUSED','KAFKA_TOPIC_RAW_EVENTS','KAFKA_TOPIC_ALERTS_DLQ','KAFKA_GROUP_ID','KAFKA_SECURITY_PROTOCOL','AISOC_TENANT_ID','SOCAI2_TENANT_ID','SOCAI2_OPERATOR_USER_ID','SOCAI2_SOURCE_UEBA_ENABLED','SOCAI2_SOURCE_KNOWLEDGE_ENABLED','SOCAI2_SOURCE_GRAPH_ENABLED','SOCAI2_SOURCE_PRODUCT_HOST_ENABLED'}
for r in rows:
 e=dict(x.split('=',1) for x in r['Config']['Env'] if '=' in x);urls={}
 for k in ['DATABASE_URL','SOCAI2_CASE_DATABASE_URL','REDIS_URL']:
  if k in e:
   u=urllib.parse.urlsplit(e[k]);urls[k]={'scheme':u.scheme,'host':u.hostname,'port':u.port,'path':u.path,'user':u.username,'password_present':bool(u.password)}
 item={'name':r['Name'],'id':r['Id'],'image':r['Image'],'state':r['State']['Status'],'ports':r['HostConfig']['PortBindings'],'restart':r['HostConfig']['RestartPolicy'],'mounts':[{'source':m['Source'],'destination':m['Destination'],'rw':m['RW']} for m in r['Mounts']],'runtime':{k:e[k] for k in selected if k in e},'connections':urls}
 if any(x in r['Name'] for x in ['fusion','dispatch','http-api','production-api','production-workbench']):item['command']=(r['Config']['Entrypoint'] or [])+(r['Config']['Cmd'] or [])
 result.append(item)
pg=[]
for db in ['aisoc','socai2_streaming_20261115']:
 sql="SELECT json_build_object('database',current_database(),'schema_owner',(SELECT nspowner::regrole::text FROM pg_namespace WHERE nspname='socai2'),'tables',(SELECT count(*) FROM information_schema.tables WHERE table_schema='socai2' AND table_type='BASE TABLE'),'columns',(SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2'),'tenants',(SELECT json_agg(id) FROM public.tenants),'actors',(SELECT json_agg(id) FROM public.users));"
 pg.append(json.loads(call(['docker','exec','spirithub-postgres-1','psql','-wXAtq','-U','spirithub','-d',db,'-c',sql])))
private=Path('/opt/sting-aisoc-socai2/private')
print(json.dumps({'containers':result,'databases':pg,'private_files':[{ 'path':str(p),'mode':oct(p.stat().st_mode & 0o777)} for p in private.glob('processing-production/*') if p.is_file()]},indent=2))
