"""Actual preflight/connector setup and bounded lake readback for one new batch."""
import hashlib,json,os,subprocess,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from uuid import UUID
root=Path(sys.argv[1]);phase=sys.argv[2];cfg=json.loads((root/'config/release.json').read_text());batch=root/'verification/release-smoke-20261116-01'
p=json.loads((batch/'profile.json').read_text());m=json.loads((batch/'manifest.json').read_text());digest=hashlib.sha256((batch/'manifest.json').read_bytes()).hexdigest()
def run(args,body=None):
 r=subprocess.run(args,input=body,capture_output=True,text=True,timeout=cfg['command_timeout_seconds'])
 if r.returncode:
  log=root/'private'/('minimal-'+phase+'-error-'+str(len(list((root/'private').glob('minimal-*error*'))))+'.txt')
  with log.open('x') as f:log.chmod(0o600);f.write(r.stdout+'\n'+r.stderr)
  raise RuntimeError('probe_failed_private_log:'+str(log))
 return r.stdout
def write(name,value):
 path=batch/'out'/name
 with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,default=str)
 os.chmod(path,0o644)
def inspect(name):return json.loads(run(['docker','inspect',name]))[0]
base={'batch_id':p['batch_id'],'tenant_id':p['tenant_id'],'prepared_manifest_sha256':digest,'observed_at':datetime.now(timezone.utc).isoformat()}
if phase=='connector':
 record=p['connector'];UUID(record['id']);UUID(p['tenant_id'])
 assert record=={'id':record['id'],'name':'Endpoint Collector','connector_type':'telemetry-channel-01','category':'custom','is_enabled':False}
 write('connector-intent.json',{**base,'state':'started_outcome_unknown','connector':record})
 def q(value):return "'"+value.replace("'","''")+"'"
 sql="BEGIN; INSERT INTO public.connectors(id,tenant_id,name,connector_type,category,is_enabled) VALUES("+','.join(q(record[k]) for k in ('id',))+','+q(p['tenant_id'])+','+','.join(q(record[k]) for k in ('name','connector_type','category'))+",false); SELECT row_to_json(t) FROM (SELECT id,tenant_id,name,connector_type,category,is_enabled FROM public.connectors WHERE id="+q(record['id'])+"::uuid) t; COMMIT;"
 body=run(['docker','exec','-i',cfg['database']['container'],'psql','-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-U',cfg['database']['admin'],'-d',cfg['database']['name']],sql)
 row=json.loads(body.strip());assert row['id']==record['id'] and row['tenant_id']==p['tenant_id']
 out={**base,'status':'passed','connector':row,'business_records_inserted':0,'configuration_records_inserted':1};write('connector.json',out)
elif phase in {'preflight','context-readback'}:
 payload={'phase':phase,'tenant_id':p['tenant_id'],'events':[json.loads((batch/r['wire']).read_text()) for r in m['phases']['context']['records']]}
 code='DATA='+repr(payload)+'\n'+r'''
import asyncio,json,os
from datetime import datetime
from pathlib import Path
from uuid import UUID
from clickhouse_driver import Client
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.socai2.analysis_dispatch_runtime import load_profile
from app.socai2.stage_results import StageResultService
async def main():
 profile=load_profile('/run/analysis/dispatcher.json')
 engine=create_async_engine(Path(profile['database_url_file']).read_text().strip(),connect_args=profile['database_connect_args'],hide_parameters=True)
 service=StageResultService(async_sessionmaker(engine,expire_on_commit=False));out={}
 try:
  async with service.transaction(UUID(DATA['tenant_id']),readonly=True) as store:
   out['business_counts']={table:await store.db.scalar(text('SELECT count(*) FROM socai2.'+table)) for table in ['alerts','incidents','cases','analysis_tasks','analysis_attempts','runs']}
 finally:await engine.dispose()
 assert not any(out['business_counts'].values()),'unexpected_business_rows_before_alert'
 lake=Client(host=os.environ['CLICKHOUSE_HOST'],port=int(os.environ['CLICKHOUSE_PORT']),database=os.environ['CLICKHOUSE_DATABASE'],user=os.environ['CLICKHOUSE_USER'],password=os.environ['CLICKHOUSE_PASSWORD'],connect_timeout=5,send_receive_timeout=10,settings={'readonly':1,'max_execution_time':10})
 try:
  who=lake.execute('SELECT currentDatabase(),currentUser()')[0];out['lake_identity']={'database':who[0],'role':who[1]}
  rows,cols=lake.execute('SELECT *,toUnixTimestamp64Milli(event_time) AS event_time_ms FROM raw_events WHERE tenant_id=%(tenant)s ORDER BY event_id',{'tenant':DATA['tenant_id']},with_column_types=True)
  saved=[dict(zip([c[0] for c in cols],r)) for r in rows]
  out['lake_row_count']=len(saved)
  if DATA['phase']=='preflight':assert not saved
  else:
   assert len(saved)==3;by={str(r['event_id']):r for r in saved}
   assert set(by)=={e['id'] for e in DATA['events']}
   for event in DATA['events']:
    row=by[event['id']];ocsf=event['ocsf_event']
    assert str(row['tenant_id'])==event['tenant_id'] and row['src_hostname']==ocsf['device']['name']
    assert row['class_uid']==4001 and row['event_time_ms']==round(datetime.fromisoformat(ocsf['time']).timestamp()*1000)
    assert row['raw_payload']==ocsf['raw_data'];stored=json.loads(row['ocsf_json'])
    assert all(stored.get(k)==v for k,v in ocsf.items())
    assert not stored['_socai2_storage']['raw_payload']['truncated'] and not stored['_socai2_storage']['event_time_fallback']
   out['event_ids']=sorted(by);out['lake_rows']=saved
 finally:lake.disconnect()
 print(json.dumps(out,default=str))
asyncio.run(main())
'''
 out={**base,**json.loads(run(['docker','exec','-i',cfg['analysis']['name'],'python','-'],code).splitlines()[-1])}
 if phase=='preflight':
  for name in cfg['must_remain_stopped']:assert not inspect(name)['State']['Running']
  for name in [cfg['fusion']['name'],cfg['analysis']['name']]:assert inspect(name)['State']['Running'] and inspect(name)['RestartCount']==0
  with urllib.request.urlopen(f"http://{cfg['fusion']['bind']}:{cfg['fusion']['port']}/readyz",timeout=5) as r:ready=json.load(r)
  assert ready['status']=='ready' and ready['subscriptions']==['alerts+raw_events']
  code=r'''import asyncio,json,os
from aiokafka import AIOKafkaConsumer,TopicPartition
from app.core.kafka_security import kafka_client_kwargs
async def main():
 topics=[os.environ['KAFKA_TOPIC_RAW_EVENTS'],os.environ['KAFKA_TOPIC_ALERTS_RAW']]
 consumer=AIOKafkaConsumer(*topics,bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=None,enable_auto_commit=False,**kafka_client_kwargs(environment='production'))
 await consumer.start()
 try:
  topics=[os.environ['KAFKA_TOPIC_RAW_EVENTS'],os.environ['KAFKA_TOPIC_ALERTS_RAW']]
  partitions=[TopicPartition(t,i) for t in topics for i in sorted(consumer.partitions_for_topic(t))]
  begin=await consumer.beginning_offsets(partitions);end=await consumer.end_offsets(partitions)
  print(json.dumps([{'topic':tp.topic,'partition':tp.partition,'begin':begin[tp],'end':end[tp]} for tp in partitions]))
 finally:await consumer.stop()
asyncio.run(main())
'''
  out.update(kafka_offsets=json.loads(run(['docker','exec','-i',cfg['fusion']['name'],'python','-'],code).splitlines()[-1]),fusion_ready=True,unique_execution_services=True,source='actual_release_preflight')
  assert all(x['begin']==x['end'] for x in out['kafka_offsets'])
  assert json.loads((batch/'out/connector.json').read_text())['status']=='passed'
 else:
  out.update(source='real_lake_readback',context_receipt_sha256=hashlib.sha256((batch/'out/send-context.json').read_bytes()).hexdigest())
 out['status']='passed';write(phase+'.json',out)
else:raise ValueError('unknown phase')
print(json.dumps(out,ensure_ascii=False,indent=2,default=str))
