"""Verify the configured platform blob even when Docker exposes an index ID."""
import hashlib,json,subprocess,tarfile
from pathlib import Path
c=CONFIG;root=Path(c['remote_root']);package=root/'package'/c['package_release']
p=json.loads((package/'build-profile.json').read_text());a=json.loads((package/p['acceptance_image']).read_text())
d=json.loads(subprocess.run(['docker','image','inspect',a['base_ref']],capture_output=True,text=True,check=True).stdout)[0]
assert a['base_ref'] in d['RepoDigests'] and d['Architecture']=='amd64' and d['Os']=='linux'
proc=subprocess.Popen(['docker','image','save',a['base_ref']],stdout=subprocess.PIPE)
found=None
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
 for member in tar:
  if member.isfile() and member.size<=4194304:
   raw=tar.extractfile(member).read()
   if 'sha256:'+hashlib.sha256(raw).hexdigest()==a['base_id']:
    found={'name':member.name,'sha256':a['base_id'],'content':json.loads(raw)}
assert proc.wait(timeout=c['command_timeout_seconds'])==0 and found is not None
out={'status':'passed_pinned_base_identity','reference':a['base_ref'],'docker_image_id':d['Id'],'expected_platform_blob':found,'platform':'linux/amd64'}
(root/'base-identity.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
