"""Actual ordinary ingress support writes, all rolled back before service start."""
import json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);c=json.loads((root/'config/release.json').read_text())
code=r'''
import asyncio,json,os,uuid
from contextlib import asynccontextmanager
from datetime import datetime,timezone
import asyncpg
from app.services.sessions import SessionStore
from app.services.dlq import DeadLetter
from app.services.dlq_sink import PostgresDLQ
class Pool:
 def __init__(self,conn):self.conn=conn
 @asynccontextmanager
 async def acquire(self):yield self.conn
async def main():
 conn=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'),ssl='require');tenant=os.environ['PROBE_TENANT'];tx=conn.transaction();out={}
 tables=['sessions','aisoc_dead_letters','aisoc_ai_assets']
 try:
  out['role']=await conn.fetchval('SELECT current_user');out['database']=await conn.fetchval('SELECT current_database()')
  out['before']={name:await conn.fetchval('SELECT count(*) FROM public.'+name) for name in tables};assert not any(out['before'].values())
  assert await conn.fetchval('SELECT public.current_tenant_id()') is None
  await tx.start();pool=Pool(conn)
  event={'time':datetime.now(timezone.utc).isoformat(),'metadata':{'product':{'name':'runtime-check'}},'activity':{'session':{'key':'release-ingress','key_kind':'vendor_session'}}}
  ref=await SessionStore(pool).record_event(tenant,event);assert ref is not None
  await conn.execute("SELECT set_config('app.current_tenant_id','',true)")
  assert await PostgresDLQ(lambda:pool).record(DeadLetter(topic=os.environ['KAFKA_TOPIC_ALERTS_RAW'],reason='connection_probe_rollback',schema_version='v1',payload_excerpt='',tenant_id=tenant,partition=0,offset=0))
  await conn.execute("INSERT INTO public.aisoc_ai_assets(tenant_id,kind,external_id,discovery_source) VALUES ($1,'ai_app','release-ingress','declared')",uuid.UUID(tenant))
  out['inside']={name:await conn.fetchval('SELECT count(*) FROM public.'+name) for name in tables};assert all(n==1 for n in out['inside'].values())
 finally:
  await tx.rollback()
  out['after']={name:await conn.fetchval('SELECT count(*) FROM public.'+name) for name in tables}
  out['tenant_after_rollback']=await conn.fetchval('SELECT public.current_tenant_id()');await conn.close()
 assert not any(out['after'].values()) and out['tenant_after_rollback'] is None
 print(json.dumps({'status':'passed','actual_new_image_methods':True,'checks':out,'database_rows_committed':0,'model_calls':0}))
asyncio.run(main())
'''
compile(code,'<ordinary-ingress-probe>','exec')
base=json.loads((root/'fusion-docker-base.json').read_text())
r=subprocess.run([*base,'--rm','-i','--env','PROBE_TENANT='+c['identity']['tenant_id'],'--entrypoint','python',c['processing_image_tag'],'-B','-'],input=code,text=True,capture_output=True,timeout=c['command_timeout_seconds'])
if r.returncode:
 p=root/'private/ordinary-ingress-write-probe.log';p.write_text(r.stdout+'\n'+r.stderr);p.chmod(0o600);raise RuntimeError('probe_failed; private_detail='+str(p))
print(json.dumps(json.loads(r.stdout.splitlines()[-1]),indent=2))
