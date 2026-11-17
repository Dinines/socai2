"""Start only the two audited r3 processing entries; preserve stopped predecessors."""
import fcntl,hashlib,json,subprocess,sys,time,urllib.request
from pathlib import Path
root=Path(sys.argv[1]);kind=sys.argv[2];assert kind in {'fusion','analysis'}
c=json.loads((root/'config/release.json').read_text());p=json.loads((root/'verification/streaming-fullflow-20261116-01/profile.json').read_text())
def run(args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=55)
    assert r.returncode==0,'command_failed:'+args[0]+':'+str(r.returncode)
    return r.stdout.strip()
def inspect(name):
    r=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=10)
    return json.loads(r.stdout)[0] if r.returncode==0 else None
for name in c['must_remain_stopped']:assert not inspect(name)['State']['Running'],name
assert not inspect(c[kind]['name'])
image=json.loads(run(['docker','image','inspect',c['processing_image_tag']]))[0]['Id'];assert image==p['processing_image']
base=json.loads((root/(kind+'-docker-base.json')).read_text());prior=Path(c['prior_runtime_root'])
assert base==json.loads((prior/(kind+'-docker-base.json')).read_text())
with (root/('start-'+kind+'-intent.json')).open('x') as f:json.dump({'kind':kind,'image':image,'state':'started_outcome_unknown'},f)
args=base+['-d','--name',c[kind]['name'],'--restart',c['restart'],'--entrypoint','python']
if kind=='fusion':
    s=c['fusion'];args+=['-p',f"{s['bind']}:{s['port']}:{s['container_port']}",image,'-m','uvicorn','app.main:app','--host','0.0.0.0','--port',str(s['container_port'])]
else:args+=[image,'-m','app.socai2.analysis_dispatch_runtime','--profile','/run/analysis/dispatcher.json']
identity=run(args);receipt={'kind':kind,'id':identity,'image':image,'runtime_bindings_unchanged':True}
deadline=time.monotonic()+45
while time.monotonic()<deadline:
    state=inspect(identity)['State'];assert state['Running'],'new_entry_exited'
    try:
        if kind=='fusion':
            with urllib.request.urlopen(f"http://{c['fusion']['bind']}:{c['fusion']['port']}/readyz",timeout=3) as response:ready=json.load(response)
            assert ready['status']=='ready' and ready['subscriptions']==['alerts+raw_events'];receipt['ready']=ready
        else:
            with (prior/'analysis/state/dispatch.lock').open('r') as f:
                try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:receipt['lock_held']=True
                else:raise ValueError('lock_not_held_yet')
        break
    except (OSError,ValueError,AssertionError):time.sleep(1)
else:raise RuntimeError('readiness_not_observed')
receipt['state']=inspect(identity)['State']['Status']
with (root/('start-'+kind+'.json')).open('x') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt,indent=2))
