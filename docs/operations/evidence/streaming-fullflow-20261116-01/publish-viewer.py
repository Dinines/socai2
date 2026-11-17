"""Publish only this finished batch with the already deployed 4177 package."""
import base64,hashlib,io,json,shlex,subprocess,tarfile
from pathlib import Path
root=Path(__file__).resolve().parent;p=json.loads((root/'batch/profile.json').read_text());v=json.loads((root/'viewer-publication.json').read_text())
files=list((root/'viewer-input').glob('*.json'));assert len(files)==6
document=json.loads((root/'viewer-input/document.json').read_text());assert document['batch']['id']==p['batch_id'] and document['batch']['execution_state']=='finished'
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w:gz') as tar:
    for f in files:tar.add(f,arcname=f.name)
payload={'config':v,'directory':p['remote_directory']+'/viewer-input','batch_id':p['batch_id'],'archive':base64.b64encode(buffer.getvalue()).decode(),'files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
code='''import base64,hashlib,io,json,subprocess,sys,tarfile
from pathlib import Path
p=json.loads(sys.stdin.read());v=p['config'];container=json.loads(subprocess.check_output(['docker','inspect',v['container']]))[0]
assert container['State']['Running'] and container['Image']==v['image']
service=json.loads((Path(v['config_root'])/'service.json').read_text());assert service['environment_label']==v['environment_label']
assert service['ledger_root']==v['ledger_mount']+'/ledger'
assert not (Path(v['state_root'])/'ledger'/p['batch_id']/'current.json').exists()
folder=Path(p['directory']);folder.mkdir()
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(p['archive'])),mode='r:gz') as tar:
 for member in tar.getmembers():
  assert member.isfile() and member.name in p['files'] and Path(member.name).name==member.name
  raw=tar.extractfile(member).read();assert hashlib.sha256(raw).hexdigest()==p['files'][member.name]
  with (folder/member.name).open('xb') as f:f.write(raw)
  (folder/member.name).chmod(0o644)
cmd=['docker','run','--rm','--network',v['network'],'--user',v['uid_gid'],'--env','PYTHONDONTWRITEBYTECODE=1',
 '--mount','type=bind,src='+v['config_root']+',dst='+v['config_mount']+',readonly',
 '--mount','type=bind,src='+v['state_root']+',dst='+v['ledger_mount'],
 '--mount','type=bind,src='+str(folder)+',dst=/publish,readonly','--entrypoint','python',v['image'],
 '-m','investigation_test','publish','--config',v['config_mount']+'/service.json','--document','/publish/document.json','--expected-revision',str(v['expected_revision'])]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
print(json.dumps({'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'files':p['files'],'image':container['Image'],'state_root':v['state_root']},ensure_ascii=False));assert r.returncode==0
'''
with (root/'viewer-publish-intent.json').open('x') as f:json.dump({k:x for k,x in payload.items() if k!='archive'},f,ensure_ascii=False,indent=2)
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12',v['ssh_target'],shlex.join(['python3','-c',code])],input=json.dumps(payload),capture_output=True,text=True,timeout=50)
with (root/'viewer-publish-receipt.json').open('x') as f:json.dump({'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},f,ensure_ascii=False,indent=2)
assert r.returncode==0,'inspect actual receipt before any repeat'
print(r.stdout)
