"""Transfer this frozen release; create new directories only, no service/DB action."""
import hashlib,io,json,shlex,subprocess,tarfile
from pathlib import Path
R=Path(__file__).resolve().parents[4]
P=R/'deploy/aisoc21/streaming-release-20261116-01'
E=Path(__file__).resolve().parent
c=json.loads((P/'release.json').read_text())
files={}
def add_tree(source,target):
 for p in sorted(source.rglob('*')):
  if p.is_file():files[target+'/'+str(p.relative_to(source))]=p.read_bytes()
add_tree(P,'config')
http=R/'.local/streaming-release-20261116-01/http'
add_tree(http,'http/releases/'+json.loads((P/'http-profile.json').read_text())['release'])
for name in ['install_reader.py','analysis_lifecycle.sql','case_allocation.sql','analysis_ingress_access.sql','verify_socai2_v1_2_reader.sql']:
 files['deploy/database/'+name]=(R/'deploy/database'/name).read_bytes()
for name in ['128_socai2_analysis_lifecycle.sql','129_socai2_case_allocation.sql']:
 files['services/api/migrations/'+name]=(R/'services/api/migrations'/name).read_bytes()
add_tree(R/'deliverables/investigation-validation-20261106/http-handoff','swagger/handoff')
# Version/servers are presentation metadata; the 80-operation contract remains frozen.
openapi=json.loads(files['swagger/handoff/openapi.json']);openapi['servers']=[{'url':c['swagger']['upstream']}]
openapi['info']['version']=json.loads((P/'http-profile.json').read_text())['release']
files['swagger/handoff/openapi.json']=(json.dumps(openapi,ensure_ascii=False,indent=2)+'\n').encode()
files['swagger/compose.yml']=(R/'deploy/api-docs/compose.yml').read_bytes()
s=c['swagger'];files['swagger/runtime.env']=('\n'.join(k+'='+str(v) for k,v in {'SWAGGER_IMAGE':s['image'],'DOCS_PLATFORM':s['platform'],'DOCS_BIND':s['bind'],'DOCS_PORT':s['port'],'DOCS_CONTAINER_PORT':s['container_port'],'DOCS_CONTENT':c['root']+'/swagger/handoff'}.items())+'\n').encode()
manifest={'release':c['release'],'files':{n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())}}
files['frozen-manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz') as t:
 for n,b in sorted(files.items()):
  m=tarfile.TarInfo(n);m.size=len(b);m.mode=0o644;t.addfile(m,io.BytesIO(b))
raw=buf.getvalue();digest=hashlib.sha256(raw).hexdigest()
remote=r'''
import hashlib,io,json,pathlib,sys,tarfile
root=pathlib.Path(sys.argv[1]);raw=sys.stdin.buffer.read();assert hashlib.sha256(raw).hexdigest()==sys.argv[2]
assert not root.exists();root.mkdir()
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
 for m in t.getmembers():
  p=pathlib.PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts
  dest=root/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(t.extractfile(m).read());dest.chmod(0o644)
manifest=json.loads((root/'frozen-manifest.json').read_text())
for n,h in manifest['files'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
(root/'releases').mkdir();print(json.dumps({'status':'uploaded','root':str(root),'files':len(manifest['files']),'archive_sha256':sys.argv[2],'services_changed':False}))
'''
args=['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12',c['ssh_target'],shlex.join(['python3','-c',remote,c['root'],digest])]
r=subprocess.run(args,input=raw,capture_output=True,timeout=120)
(E/'frozen-manifest-01.json').write_text(json.dumps(manifest,indent=2)+'\n')
(E/'upload-01.json').write_text(json.dumps({'exit':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()},indent=2)+'\n')
print(r.stdout.decode());assert r.returncode==0
