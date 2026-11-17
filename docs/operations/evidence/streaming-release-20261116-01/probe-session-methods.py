"""Run the changed SessionStore methods under formal RLS; roll back all changes."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from urllib.parse import quote
v=json.load(sys.stdin);root=Path(v['root']);c=json.loads((root/'config/release.json').read_text());db=c['database']
p=root/'probes/session-rls';p.mkdir(parents=True);source=v['source'].encode();assert hashlib.sha256(source).hexdigest()==v['source_sha256'];(p/'sessions.py').write_bytes(source)
pg=json.loads(subprocess.check_output(['docker','inspect',db['container']],text=True,timeout=c['command_timeout_seconds']))[0]
env=dict(s.split('=',1) for s in pg['Config']['Env'] if '=' in s);password=env['POSTGRES_PASSWORD']
url='postgresql://'+db['admin']+':'+quote(password,safe='')+'@'+db['host']+':'+str(db['port'])+'/'+db['name']
private=root/'private/session-probe.env'
with private.open('x') as f:
 private.chmod(0o600);f.write('PROBE_DATABASE_URL='+url+'\nPROBE_TENANT='+c['identity']['tenant_id']+'\nPROBE_ROLE='+db['ingress']+'\n')
code=r'''
import asyncio,json,os,uuid
from contextlib import asynccontextmanager
from datetime import datetime,timezone,timedelta
import asyncpg
from app.services.sessions import SessionStore
class Pool:
 def __init__(self,conn):self.conn=conn
 @asynccontextmanager
 async def acquire(self):yield self.conn
async def main():
 conn=await asyncpg.connect(os.environ['PROBE_DATABASE_URL'],ssl='require');tenant=os.environ['PROBE_TENANT'];role=os.environ['PROBE_ROLE'];tx=conn.transaction();out={}
 try:
  await tx.start();await conn.execute('GRANT SELECT,INSERT,UPDATE ON public.sessions TO "'+role+'"');await conn.execute('SET LOCAL ROLE "'+role+'"')
  assert await conn.fetchval('SELECT current_user')==role
  assert await conn.fetchval('SELECT public.current_tenant_id()') is None
  out['started_with_no_tenant']=True
  store=SessionStore(Pool(conn));at=(datetime.now(timezone.utc)-timedelta(seconds=1800)).isoformat()
  def event(block):return {'time':at,'metadata':{'product':{'name':'runtime-check'}},'activity':{'session':block,'actor':{'kind':'human','id':'operator'},'location':{'ip':'192.0.2.70'}}}
  parent=await store.record_event(tenant,event({'key':'release-parent','key_kind':'vendor_session','issued':{'key':'release-child','key_source':'credential'}}));assert parent is not None
  rows=await conn.fetch('SELECT id,parent_session_id,key_kind,ended_at FROM public.sessions WHERE tenant_id=$1',uuid.UUID(tenant));assert len(rows)==2 and sum(r['parent_session_id']==parent.id for r in rows)==1
  out['parent_and_child_saved']=True
  await conn.execute("SELECT set_config('app.current_tenant_id','',true)")
  derived=await store.record_event(tenant,event({'key':'release-derived','key_kind':'derived'}));assert derived is not None
  # A different explicit tenant must not close the first tenant's row.
  await conn.execute("SELECT set_config('app.current_tenant_id','',true)")
  assert await store.close_idle(900,tenant_id=str(uuid.UUID(int=2)))==0
  await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)",tenant)
  assert await conn.fetchval('SELECT ended_at IS NULL FROM public.sessions WHERE id=$1',derived.id)
  await conn.execute("SELECT set_config('app.current_tenant_id','',true)")
  assert await store.close_idle(900)==1
  await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)",tenant)
  rows=await conn.fetch('SELECT key_kind,ended_at FROM public.sessions WHERE tenant_id=$1',uuid.UUID(tenant))
  assert sum(r['ended_at'] is not None for r in rows)==1
  assert all(r['ended_at'] is None for r in rows if r['key_kind']!='derived')
  out.update(derived_closed=True,vendor_sessions_kept=True,other_tenant_close_did_not_affect_subject=True,rows_inside_transaction=len(rows))
 finally:
  await tx.rollback()
  out['after_rollback']={'rows':await conn.fetchval('SELECT count(*) FROM public.sessions'),'ingress_insert_grant':await conn.fetchval("SELECT has_table_privilege($1,'public.sessions','INSERT')",role),'tenant':str(await conn.fetchval('SELECT public.current_tenant_id()'))}
  assert out['after_rollback']['rows']==0 and out['after_rollback']['ingress_insert_grant'] is False and out['after_rollback']['tenant']=='None'
  await conn.close()
 print(json.dumps({'status':'passed','ordinary_role':role,'checks':out,'database_rows_committed':0,'grants_committed':False,'model_calls':0}))
asyncio.run(main())
'''
compile(code,'<runtime-method-probe>','exec')
base=json.loads((root/'fusion-docker-base.json').read_text())
args=[*base,'--env-file',str(private),'--mount','type=bind,src='+str(p/'sessions.py')+',dst='+c['fusion']['workdir']+'/app/services/sessions.py,readonly','--rm','-i','--entrypoint','python',c['processing_image_tag'],'-B','-']
r=subprocess.run(args,input=code,text=True,capture_output=True,timeout=c['command_timeout_seconds'])
if r.returncode:
 log=root/'private/session-method-probe-error.log';log.write_text(r.stdout+'\n'+r.stderr);log.chmod(0o600)
 raise RuntimeError('session_method_probe_failed; private_detail='+str(log))
print(json.dumps({'source_sha256':v['source_sha256'],'probe':json.loads(r.stdout.splitlines()[-1])},indent=2))
