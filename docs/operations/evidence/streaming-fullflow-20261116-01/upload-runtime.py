"""Install this batch and point new execution containers at the unchanged r2 runtime."""
import hashlib,io,json,shlex,subprocess,tarfile
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[3];P=R/'deploy/aisoc21/streaming-release-20261116-03'
c=json.loads((P/'release.json').read_text());p=json.loads((E/'batch/profile.json').read_text())
files={'config/'+name:(P/name).read_bytes() for name in ('release.json','identity.json','processing-build.toml')}
for path in (E/'batch').rglob('*'):
    if path.is_file() and '__pycache__' not in path.parts:files['verification/'+p['batch_id']+'/'+str(path.relative_to(E/'batch'))]=path.read_bytes()
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz') as tar:
    for name,raw in files.items():
        entry=tarfile.TarInfo(name);entry.size=len(raw);entry.mode=0o644;tar.addfile(entry,io.BytesIO(raw))
body=buf.getvalue()
code='''import hashlib,io,json,os,sys,tarfile
from pathlib import Path
root=Path(sys.argv[1]);assert root.is_dir() and not (root/'config').exists()
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 for entry in tar.getmembers():
  path=Path(entry.name);assert entry.isfile() and not path.is_absolute() and '..' not in path.parts
  dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as f:f.write(tar.extractfile(entry).read())
c=json.loads((root/'config/release.json').read_text());prior=Path(c['prior_runtime_root'])
for kind in ('fusion','analysis'):
 raw=(prior/(kind+'-docker-base.json')).read_bytes();(root/(kind+'-docker-base.json')).write_bytes(raw)
batch=root/'verification'/sys.argv[2];m=json.loads((batch/'manifest.json').read_text())
for name,digest in m['files'].items():assert hashlib.sha256((batch/name).read_bytes()).hexdigest()==digest
out=batch/'out';out.mkdir();os.chown(out,10001,10001)
receipt={'status':'prepared_not_started','prior_runtime_root':str(prior),'runtime_bindings_unchanged':True,'credentials_copied':False,'model_calls':0,'batch':str(batch),'files':len(m['files'])}
with (root/'runtime-binding.json').open('x') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt))
'''
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12',c['ssh_target'],shlex.join(['python3','-c',code,c['root'],p['batch_id']])],input=body,capture_output=True,timeout=55)
receipt={'exit':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode(),'archive_sha256':hashlib.sha256(body).hexdigest()}
with (E/'runtime-upload.json').open('x') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt,indent=2));assert r.returncode==0
