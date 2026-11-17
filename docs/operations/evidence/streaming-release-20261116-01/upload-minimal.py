"""Upload only the frozen source and business bytes; authored answers stay local."""
import io,json,shlex,subprocess,tarfile,hashlib
from pathlib import Path
E=Path(__file__).resolve().parent;src=E/'revision-02/smoke';m=json.loads((src/'manifest.json').read_text());p=json.loads((src/'profile.json').read_text())
cfg=json.loads((E.parents[3]/'deploy/aisoc21/streaming-release-20261116-02/release.json').read_text())
target=cfg['root']+'/verification/'+p['batch_id'];buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz') as tar:
 for name in [*m['files'],'manifest.json']:
  body=(src/name).read_bytes();entry=tarfile.TarInfo(name);entry.size=len(body);entry.mode=0o644;tar.addfile(entry,io.BytesIO(body))
raw=buf.getvalue();digest=hashlib.sha256(raw).hexdigest()
remote='''import hashlib,io,json,os,sys,tarfile
from pathlib import Path
target=Path(sys.argv[1]);root=Path(sys.argv[2]);raw=sys.stdin.buffer.read();assert hashlib.sha256(raw).hexdigest()==sys.argv[3]
target.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
 for member in tar.getmembers():
  path=Path(member.name);assert member.isfile() and not path.is_absolute() and '..' not in path.parts
  dest=target/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(member).read());dest.chmod(0o644)
manifest=json.loads((target/'manifest.json').read_text())
for name,digest in manifest['files'].items():assert hashlib.sha256((target/name).read_bytes()).hexdigest()==digest
out=target/'out';out.mkdir();os.chown(out,10001,10001)
env=json.loads((root/'config/fusion-env.json').read_text());transport={k:v for k,v in env.items() if k.startswith('KAFKA_')}
secret=root/'private/producer.env'
with secret.open('x') as f:secret.chmod(0o600);f.write(''.join(k+'='+v+'\\n' for k,v in transport.items()))
os.chown(secret,10001,10001)
print(json.dumps({'status':'uploaded_not_sent','root':str(target),'files':len(manifest['files'])+1,'expected_directory_uploaded':False,'manifest_sha256':hashlib.sha256((target/'manifest.json').read_bytes()).hexdigest(),'archive_sha256':sys.argv[3]}))
'''
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12',cfg['ssh_target'],shlex.join(['python3','-c',remote,target,cfg['root'],digest])],input=raw,capture_output=True,timeout=55)
assert r.returncode==0,r.stderr.decode();print(r.stdout.decode())
