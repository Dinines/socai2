"""Read-only ordinary-account connections; missing migration grants remain explicit."""
import json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);c=json.loads((root/'config/release.json').read_text());db=c['database']

def run(args,code):
 r=subprocess.run(args,input=code,text=True,capture_output=True,timeout=c['command_timeout_seconds'])
 if r.returncode:
  p=root/'private'/('connection-probe-'+str(len(list((root/'private').iterdir())))+'.log');p.write_text(r.stdout+'\n'+r.stderr);p.chmod(0o600)
  raise RuntimeError('probe_failed; private_detail='+str(p))
 return json.loads(r.stdout.splitlines()[-1])
code=r'''import asyncio,json,os,uuid
import asyncpg
from redis.asyncio import Redis
from clickhouse_driver import Client
async def main():
 conn=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'),ssl='require')
 out={}
 try:
  out['postgres']=dict(await conn.fetchrow('SELECT current_database() AS database,current_user AS role,ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()'))
  out['socai2_tables']=await conn.fetchval("SELECT count(*) FROM information_schema.tables WHERE table_schema='socai2' AND table_type='BASE TABLE'")
  out['support_grants']=[dict(v) for v in await conn.fetch("SELECT t AS object,has_table_privilege(current_user,t,'SELECT') AS readable,has_table_privilege(current_user,t,'INSERT') AS insertable,has_table_privilege(current_user,t,'UPDATE') AS updatable FROM unnest(ARRAY['public.sessions','public.aisoc_ai_assets','public.aisoc_dead_letters']) t")]
  out['business_counts']={}
  async with conn.transaction(readonly=True):
   await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)",os.environ['PROBE_TENANT'])
   for table in ['alerts','incidents','cases','runs']:
    if await conn.fetchval('SELECT has_table_privilege(current_user,$1,\'SELECT\')','socai2.'+table):out['business_counts'][table]=await conn.fetchval('SELECT count(*) FROM socai2.'+table)
 finally:await conn.close()
 redis=Redis.from_url(os.environ['REDIS_URL'],socket_timeout=5,socket_connect_timeout=5)
 try:out['redis']={'ping':await redis.ping(),'selected_database':os.environ['REDIS_URL'].rsplit('/',1)[-1],'keys':await redis.dbsize()}
 finally:await redis.aclose()
 lake=Client(host=os.environ['CLICKHOUSE_HOST'],port=int(os.environ['CLICKHOUSE_PORT']),database=os.environ['CLICKHOUSE_DATABASE'],user=os.environ['CLICKHOUSE_USER'],password=os.environ['CLICKHOUSE_PASSWORD'])
 try:out['lake']={'database':os.environ['CLICKHOUSE_DATABASE'],'user':lake.execute('SELECT currentUser()')[0][0],'raw_event_rows':lake.execute('SELECT count(*) FROM raw_events')[0][0]}
 finally:lake.disconnect()
 print(json.dumps(out))
asyncio.run(main())
'''
results={}
for kind in ['analysis','fusion']:
 base=json.loads((root/(kind+'-docker-base.json')).read_text())
 results[kind]=run([*base,'--rm','-i','--env','PROBE_TENANT='+c['identity']['tenant_id'],'--entrypoint','python',c['processing_image_tag'],'-B','-'],code)
 expected=db['processor' if kind=='analysis' else 'ingress']
 assert results[kind]['postgres']['database']==db['name'] and results[kind]['postgres']['role']==expected and results[kind]['postgres']['ssl']
 assert results[kind]['redis']['ping'] and results[kind]['lake']['database']==db['name']
print(json.dumps({'status':'connections_passed','database_writes':0,'model_calls':0,'missing_migrations_and_ingress_support_grants_remain_pending':True,'connections':results},indent=2))
