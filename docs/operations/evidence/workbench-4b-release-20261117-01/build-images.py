"""Build both reviewed package images on 21 before replacing the viewer."""
import hashlib,json,subprocess,tarfile
from pathlib import Path
c=CONFIG;root=Path(c['remote_root']);incoming=root/'incoming'
receipt=INPUT
archive=incoming/Path(receipt['archive']).name
assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['archive_sha256']
package=root/'package'/c['package_release']
if not package.exists():
 with tarfile.open(archive) as tar:
  for member in tar.getmembers():
   assert member.isfile() and member.name.startswith(c['package_release']+'/') and '..' not in Path(member.name).parts
  tar.extractall(root/'package')
manifest=json.loads((package/'package-manifest.json').read_text())
assert hashlib.sha256((package/'package-manifest.json').read_bytes()).hexdigest()==receipt['manifest_sha256']
for name,record in manifest['files'].items():assert hashlib.sha256((package/name).read_bytes()).hexdigest()==record['sha256'],name
profile=json.loads((package/'build-profile.json').read_text());accept=json.loads((package/profile['acceptance_image']).read_text())
def run(args,timeout=None):
 r=subprocess.run(args,text=True,capture_output=True,cwd=package,timeout=timeout or c['command_timeout_seconds'])
 if r.returncode:raise RuntimeError('command_failed:'+args[0]+':'+str(r.returncode)+':'+r.stderr[-1200:])
 return r.stdout
def image(ref):return json.loads(run(['docker','image','inspect',ref]))[0]
assert image(profile['image']['base_tag'])['Id']==profile['image']['base_id']
base=image(accept['base_ref'])
proof=json.loads((root/'base-identity.json').read_text())
assert proof['reference']==accept['base_ref'] and proof['docker_image_id']==base['Id']
assert proof['expected_platform_blob']['sha256']==accept['base_id'] and proof['status']=='passed_pinned_base_identity'
images={}
for kind,dockerfile,tag,network in [('viewer','Dockerfile',c['viewer_image'],'none'),('acceptance','Dockerfile.acceptance',c['acceptance_image'],accept['build_network'])]:
 log=root/(kind+'-build.log')
 with log.open('x') as f:
  r=subprocess.run(['docker','build','--pull=false','--network='+network,'--platform',c['platform'],'-f',dockerfile,'-t',tag,'.'],cwd=package,text=True,stdout=f,stderr=subprocess.STDOUT,timeout=c['command_timeout_seconds'])
 assert r.returncode==0,'image_build_failed:'+kind
 d=image(tag);assert d['Architecture']=='amd64' and d['Os']=='linux'
 images[kind]={'tag':tag,'id':d['Id'],'repo_digests':d['RepoDigests'],'architecture':d['Architecture'],'user':d['Config']['User']}
assert manifest['service_version']==c['version']
out={'status':'images_built_not_switched','package':str(package),'package_manifest_sha256':receipt['manifest_sha256'],'file_count':len(manifest['files']),'images':images,'services_changed':False}
(root/'images.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
