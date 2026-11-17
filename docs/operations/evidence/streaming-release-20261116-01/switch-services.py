"""Start one explicitly selected release component and save an immediate receipt."""
import hashlib, json, subprocess, sys, time, urllib.request
from pathlib import Path

root=Path(sys.argv[1]);step=sys.argv[2];cfg=json.loads((root/'config/release.json').read_text())
assert str(root)==cfg['root']
def run(args):
 r=subprocess.run(args,capture_output=True,text=True,timeout=cfg['command_timeout_seconds'])
 assert r.returncode==0, 'command_failed:'+args[0]+':'+str(r.returncode)
 return r.stdout.strip()
def inspect(name):
 r=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=10)
 return json.loads(r.stdout)[0] if r.returncode==0 else None
def absent(name):assert inspect(name) is None, 'target_already_exists_read_status_before_retry'
def get(url):
 with urllib.request.urlopen(url,timeout=5) as r:return r.status,r.read()
def ready(url):
 deadline=time.monotonic()+cfg['startup_timeout_seconds'];last=None
 while time.monotonic()<deadline:
  try:
   status,body=get(url);assert status==200;return body
  except Exception as exc:last=type(exc).__name__;time.sleep(1)
 raise RuntimeError('readiness_failed:'+str(last))
def stopped_old():
 for name in cfg['must_remain_stopped']:
  d=inspect(name);assert d is not None and not d['State']['Running'],name+':unexpected_active'
def public(c):
 return {'name':c['Name'],'id':c['Id'],'image':c['Image'],'state':c['State']['Status'],'restart_count':c['RestartCount'],'ports':c['NetworkSettings']['Ports'],'started_at':c['State']['StartedAt']}
out={'release':cfg['release'],'step':step};stopped_old()
if step=='swagger':
 s=cfg['swagger'];name=s['container'];absent(name)
 # Keep the original compose entry; the override selects the reviewed explicit name.
 override=root/'swagger/container-name.json'
 with override.open('x') as f:json.dump({'services':{'swagger':{'container_name':name}}},f)
 run(['docker','compose','--env-file',str(root/'swagger/runtime.env'),'-f',str(root/'swagger/compose.yml'),'-f',str(override),'-p',s['project'],'up','-d'])
 url=f"http://{s['bind']}:{s['port']}";ready(url+'/')
 raw=ready(url+'/handoff/openapi.json');assert raw==(root/'swagger/handoff/openapi.json').read_bytes()
 doc=json.loads(raw);assert doc['servers']==[{'url':s['upstream']}]
 out.update(openapi_sha256=hashlib.sha256(raw).hexdigest(),operations=sum(m in {'get','post','put','patch','delete'} for ps in doc['paths'].values() for m in ps),tags=[t['name'] for t in doc['tags']])
 request=urllib.request.Request(s['upstream']+'/openapi.json',headers={'Origin':url})
 with urllib.request.urlopen(request,timeout=5) as r:assert r.headers.get('Access-Control-Allow-Origin')==url
 out['cors_origin_allowed']=url
elif step in {'fusion','analysis'}:
 s=cfg[step];name=s['name'];absent(name)
 image=json.loads(run(['docker','image','inspect',cfg['processing_image_tag']]))[0]['Id']
 assert image=='sha256:e95a878b8d1bed6a6639666d5e46215bd38f478a5bd46c9bee5e30992cc7669d'
 args=json.loads((root/(step+'-docker-base.json')).read_text())+['-d','--name',name,'--restart',cfg['restart'],'--entrypoint','python']
 if step=='fusion':args+=['-p',f"{s['bind']}:{s['port']}:{s['container_port']}",image,'-m','uvicorn','app.main:app','--host','0.0.0.0','--port',str(s['container_port'])]
 else:args+=[image,'-m','app.socai2.analysis_dispatch_runtime','--profile','/run/analysis/dispatcher.json']
 run(args)
 if step=='fusion':out['readiness']=json.loads(ready(f"http://{s['bind']}:{s['port']}/readyz"))
 else:
  time.sleep(3);assert inspect(name)['State']['Running'];assert (root/'analysis/state/dispatch.lock').exists()
  # The actual process holds the configured exclusive lock.
  import fcntl
  with (root/'analysis/state/dispatch.lock').open('r') as f:
   try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:out['dispatch_lock_held']=True
   else:raise AssertionError('dispatcher_does_not_hold_lock')
elif step=='viewer':
 s=cfg['viewer'];name=s['name'];absent(name);old=inspect(s['old']);assert old['Id']==s['old_id'] and old['State']['Running']
 ready(s['upstream']+'/readyz')
 run(['docker','stop','--time',str(cfg['stop_timeout_seconds']),s['old_id']])
 args=['docker','run','-d','--name',name,'--restart',cfg['restart'],'--network',cfg['network'],'--user',cfg['user'],'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--memory',s['memory'],'--pids-limit',str(s['pids_limit']),'--tmpfs',s['tmpfs'],'-p',f"{s['bind']}:{s['port']}:{s['container_port']}",'-v',str(root/'viewer/config')+':/run/test-config:ro','-v',s['state_root']+':/var/lib/investigation-test:ro','--entrypoint','python',s['image'],'-m','investigation_test','serve','--config','/run/test-config/service.json','--upstream-config','/run/test-config/upstream.json','--viewer-config','/run/test-config/viewer.json']
 run(args);ready(f"http://{s['bind']}:{s['port']}/viewer/")
 out['previous_stopped']=public(inspect(s['old']))
elif step=='retire_candidate':
 # No old execution service is resumed; only the two named read endpoints stop.
 ready(cfg['viewer']['upstream']+'/readyz');ready(f"http://{cfg['swagger']['bind']}:{cfg['swagger']['port']}/handoff/openapi.json")
 out['stopped']=[]
 for name in cfg['stop_after_readiness']:
  d=inspect(name);assert d is not None and d['State']['Running']
  run(['docker','stop','--time',str(cfg['stop_timeout_seconds']),d['Id']]);out['stopped'].append(public(inspect(name)))
 name=None
else:raise ValueError('unknown step')
stopped_old()
if name:
 c=inspect(name);assert c['State']['Running'] and c['RestartCount']==0;out['container']=public(c)
out.update(status='passed',old_execution_services_stopped=True)
receipt=root/('switch-'+step+'.json')
with receipt.open('x') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out,ensure_ascii=False,indent=2))
