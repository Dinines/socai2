"""Freeze, launch once, and observe this diagnostic without starting a scheduler."""
import hashlib,io,json,shlex,subprocess,sys,tarfile
from pathlib import Path

E=Path(__file__).resolve().parent
P=json.loads((E/'profile.json').read_text())
ACTION=sys.argv[1]
assert ACTION in {'upload','launch','observe','collect'}

def ssh(code, payload=''):
    return subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12',P['ssh_target'],
        shlex.join(['python3','-c',code,P['remote_directory']])],input=payload,capture_output=True,
        text=isinstance(payload,str),timeout=55)

common='''import hashlib,json,os,subprocess,sys
from pathlib import Path
folder=Path(sys.argv[1])
'''

if ACTION=='upload':
    checks=json.loads((E/'grammar-checks.json').read_text())
    assert checks['checks']['current']['sentence'] is False
    assert all(checks['checks']['candidate'][x] for x in ('sentence','line_break','escaped_quote'))
    names=['profile.json','original-request.json','candidate-request.json','preparation.json',
           'retry-once.py','grammar-checks.json']
    manifest={'files':{name:hashlib.sha256((E/name).read_bytes()).hexdigest() for name in names}}
    with (E/'manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz') as tar:
        for name in [*names,'manifest.json']:
            raw=(E/name).read_bytes();entry=tarfile.TarInfo(name);entry.size=len(raw);entry.mode=0o644
            tar.addfile(entry,io.BytesIO(raw))
    code=common+'''import io,tarfile
folder.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 for entry in tar.getmembers():
  assert entry.isfile() and len(Path(entry.name).parts)==1
  with (folder/entry.name).open('xb') as f:f.write(tar.extractfile(entry).read())
manifest=json.loads((folder/'manifest.json').read_text())
for name,digest in manifest['files'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest
out=folder/'out';out.mkdir();os.chown(out,10001,10001)
print(json.dumps({'status':'uploaded_not_sent','files':len(manifest['files'])+1,'manifest_sha256':hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest(),'model_calls':0}))
'''
    r=ssh(code,buf.getvalue())
    assert r.returncode==0,r.stderr.decode()
    receipt=json.loads(r.stdout)
    with (E/'upload.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt,indent=2))
elif ACTION=='launch':
    code=common+'''from datetime import datetime,timezone
p=json.loads((folder/'profile.json').read_text());manifest=json.loads((folder/'manifest.json').read_text())
for name,digest in manifest['files'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest
assert not (folder/'out/intent.json').exists()
for name in ['socai2-production-fusion-20261116','socai2-production-dispatch-20261116']:
 assert not json.loads(subprocess.check_output(['docker','inspect',name]))[0]['State']['Running']
assert subprocess.run(['docker','inspect',p['container']],capture_output=True).returncode!=0
with (folder/'launch-intent.json').open('x') as f:json.dump({'state':'launch_attempted','time':datetime.now(timezone.utc).isoformat(),'container':p['container']},f)
base=json.loads((Path(p['release_root'])/'analysis-docker-base.json').read_text())
assert base[:2]==['docker','run']
cmd=base+['--detach','--name',p['container'],'--read-only','--env','PYTHONDONTWRITEBYTECODE=1',
 '--mount','type=bind,src='+str(folder)+',dst=/probe,readonly',
 '--mount','type=bind,src='+str(folder/'out')+',dst=/probe/out',
 '--entrypoint','python',p['processing_image'],'/probe/retry-once.py']
r=subprocess.run(cmd,capture_output=True,text=True,timeout=40)
receipt={'exit':r.returncode,'container_id':r.stdout.strip(),'container':p['container'],'stderr':r.stderr}
with (folder/'launch.json').open('x') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt))
'''
    r=ssh(code);assert r.returncode==0,r.stderr
    receipt=json.loads(r.stdout)
    with (E/'launch.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt,indent=2));assert receipt['exit']==0
elif ACTION=='observe':
    code=common+'''p=json.loads((folder/'profile.json').read_text())
v=json.loads(subprocess.check_output(['docker','inspect',p['container']]))[0]
out=folder/'out';receipt={'container':p['container'],'image':v['Image'],'state':v['State'],'files':sorted(x.name for x in out.iterdir())}
if (out/'outcome.json').exists():receipt['outcome']=json.loads((out/'outcome.json').read_text())
if (out/'failure.json').exists():receipt['failure']=json.loads((out/'failure.json').read_text())
print(json.dumps(receipt,indent=2))
'''
    r=ssh(code);assert r.returncode==0,r.stderr
    print(r.stdout)
else:
    code=common+'''p=json.loads((folder/'profile.json').read_text());v=json.loads(subprocess.check_output(['docker','inspect',p['container']]))[0]
assert not v['State']['Running']
out=folder/'out';raw=json.loads((out/'response.json').read_text())
def check(node):
 if isinstance(node,dict):
  for key,value in node.items():
   if key in {'reasoning','reasoning_content','thinking','analysis'}:assert value in (None,'',[]), 'nonempty_hidden_reasoning_retained_remotely'
   check(value)
 elif isinstance(node,list):
  for value in node:check(value)
check(raw)
names=['token-measurement.json','intent.json','response.json','output.txt','outcome.json']
result={'container':{'name':p['container'],'image':v['Image'],'state':v['State']},'files':{name:(out/name).read_text() for name in names}}
print(json.dumps(result,ensure_ascii=False))
'''
    r=ssh(code);assert r.returncode==0,r.stderr
    result=json.loads(r.stdout);out=E/'out';out.mkdir()
    for name,body in result['files'].items():
        with (out/name).open('x') as f:f.write(body)
    with (E/'container-final.json').open('x') as f:json.dump(result['container'],f,indent=2)
    print(json.dumps({'copied':list(result['files']),'container':result['container']},indent=2))
