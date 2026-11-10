"""Publish a workbench-only source revision, preserving image, data and other services."""
import argparse
import base64
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

VERIFY = r'''
import hashlib,json,pathlib,sys
request=json.load(sys.stdin); cfg=request['deployment']; release=pathlib.Path(cfg['release'])
sys.path.insert(0,str(release/'deploy/aisoc21'))
from release_12 import command,inspect,runtime_matches
manifest=json.loads((release/'workbench-manifest.json').read_text())
for name,expected in manifest['files'].items():
 p=release/name; assert p.resolve().is_relative_to(release) and hashlib.sha256(p.read_bytes()).hexdigest()==expected,'release_source_drift'
current=inspect(cfg['container']); effective=pathlib.Path(cfg['private'])/'workbench-after.json'
assert current['Config']['Labels']['com.docker.compose.project.config_files']==str(effective),'compose_drift'
runtime_matches({},json.loads(effective.read_text()),cfg['service'],current)
assert current['Image']==cfg['expected_image'] and current['State'].get('Health',{}).get('Status')=='healthy','not_ready'
assert any(m['Source']==str(release) and m['Destination']==cfg['source_mount'] for m in current['Mounts']),'source_mount_drift'
code="import hashlib,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); print(json.dumps({p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in json.loads(sys.argv[2])}))"
loaded=json.loads(command([cfg['docker'],'exec',cfg['container'],'python','-B','-c',code,cfg['source_mount'],json.dumps(manifest['overrides'])]))
assert loaded=={name:manifest['files'][name] for name in manifest['overrides']},'loaded_source_drift'
print(json.dumps({'status':'verified','release':str(release),'container':current['Id'],'health':'healthy','image':current['Image'],
 'source_files_verified':len(manifest['files']),'loaded_files':loaded,'model_calls':0,'database_writes':0}))
'''

REMOTE = r'''
import base64,hashlib,json,os,pathlib,subprocess,sys,time
request=json.load(sys.stdin); cfg=request['deployment']; docker=cfg['docker']
def sha(raw): return hashlib.sha256(raw).hexdigest()
def command(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=cfg['command_timeout_seconds'])
 if p.returncode: raise RuntimeError('workbench_command_failed_'+str(p.returncode))
 return p.stdout
def inspect(): return json.loads(command([docker,'inspect',cfg['container']]))[0]
def containers(): return dict(line.split(' ',1) for line in command([docker,'ps','--format','{{.Names}} {{.ID}}']).splitlines())
before=inspect(); other_before=containers()
assert before['Image']==cfg['expected_image'],'image_drift'
assert before['Config']['Labels']['com.docker.compose.project.config_files']==cfg['expected_compose'],'compose_drift'
assert any(m['Source']==cfg.get('expected_source_release',cfg['base_release']) and m['Destination']==cfg['source_mount'] for m in before['Mounts']),'source_drift'
base=pathlib.Path(cfg['base_release']); release=pathlib.Path(cfg['release']); private=pathlib.Path(cfg['private'])
assert all(p.resolve()==p for p in (base,release,private)),'path_drift'
assert not release.exists() and not private.exists(),'publication_exists_use_new_id'
manifest=json.loads((base/'manifest.json').read_bytes())
assert sha((base/'manifest.json').read_bytes())==cfg['base_manifest_sha256'],'base_manifest_drift'
files={}
for name,expected in manifest['files'].items():
 p=base/name; assert p.resolve().is_relative_to(base) and not p.is_symlink(),'source_escape'
 raw=p.read_bytes(); assert sha(raw)==expected,'base_source_drift'; files[name]=raw
for name,encoded in request['files'].items():
 p=pathlib.PurePosixPath(name)
 assert not p.is_absolute() and '..' not in p.parts and name.startswith('docs/operations/') and p.suffix=='.py','invalid_override'
 raw=base64.b64decode(encoded); compile(raw,name,'exec'); files[name]=raw
composition=json.loads(pathlib.Path(cfg['expected_compose']).read_text())
service=composition['services'][cfg['service']]
assert service['container_name']==cfg['container'],'unexpected_service'
mount=cfg['source_mount']; replacements=0
for volume in service['volumes']:
 target=volume['target']
 if target==mount or target.startswith(mount+'/'):
  relative=target[len(mount):].lstrip('/')
  assert not relative or relative in files,'missing_mounted_file'
  assert volume['read_only'] and volume['type']=='bind','source_mount_changed'
  volume['source']=str(release/relative); replacements+=1
assert replacements,'no_source_mount'
release.mkdir(mode=0o755); private.mkdir(mode=0o700,parents=True)
for name,raw in files.items():
 p=release/name; p.parent.mkdir(mode=0o755,parents=True,exist_ok=True); p.write_bytes(raw); p.chmod(0o644)
source_manifest={'release':cfg['release'],'base_release':str(base),'base_manifest_sha256':cfg['base_manifest_sha256'],
 'files':{name:sha(raw) for name,raw in sorted(files.items())},'overrides':list(request['files'])}
(release/'workbench-manifest.json').write_text(json.dumps(source_manifest,indent=2)+'\n')
effective=private/'workbench-after.json'; effective.write_text(json.dumps(composition)); effective.chmod(0o600)
(private/'workbench-before.json').write_bytes(pathlib.Path(cfg['expected_compose']).read_bytes())
(private/'workbench-before.json').chmod(0o600)
prefix=[docker,'compose','--project-directory',cfg['project_directory'],'-p',cfg['project'],'-f',str(effective)]
command(prefix+['up','-d','--no-deps','--no-build','--pull','never',cfg['service']])
deadline=time.monotonic()+cfg['health_timeout_seconds']
while True:
 after=inspect()
 if after['State'].get('Health',{}).get('Status')=='healthy': break
 if time.monotonic()>deadline: raise RuntimeError('workbench_health_timeout')
 time.sleep(1)
other_after=containers(); other_before.pop(cfg['container']); other_after.pop(cfg['container'])
assert other_before==other_after,'other_services_changed'
assert before['Image']==after['Image'] and sorted(before['Config']['Env'])==sorted(after['Config']['Env']),'image_or_environment_changed'
assert before['Config']['Cmd']==after['Config']['Cmd'] and before['Config']['Entrypoint']==after['Config']['Entrypoint'],'command_changed'
expected_mounts={(m['Destination'],m['Source'],m['RW']) for m in before['Mounts'] if not (m['Destination']==mount or m['Destination'].startswith(mount+'/'))}
actual_mounts={(m['Destination'],m['Source'],m['RW']) for m in after['Mounts'] if not (m['Destination']==mount or m['Destination'].startswith(mount+'/'))}
assert expected_mounts==actual_mounts,'data_or_certificate_mount_changed'
code="import hashlib,json,pathlib,sys; root=pathlib.Path(sys.argv[1]); print(json.dumps({p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in json.loads(sys.argv[2])}))"
loaded=json.loads(command([docker,'exec',cfg['container'],'python','-B','-c',code,mount,json.dumps(list(request['files']))]))
assert loaded=={name:sha(files[name]) for name in request['files']},'loaded_source_mismatch'
receipt={'status':'published','release':str(release),'image':after['Image'],'health':'healthy','compose':str(effective),
 'container_before':before['Id'],'container_after':after['Id'],'loaded_files':loaded,
 'source_manifest_sha256':sha((release/'workbench-manifest.json').read_bytes()),'other_services_unchanged':True,
 'image_environment_command_data_mounts_unchanged':True,'model_calls':0,'database_writes':0}
(private/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n'); (private/'receipt.json').chmod(0o600)
print(json.dumps(receipt))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--publish", action="store_true")
    actions.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    files = {name: (ROOT / name).read_bytes() for name in cfg["files"]}
    manifest = {"files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
                "deployment": cfg["deployment"]}
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    target = ROOT / cfg["manifest"]
    if target.exists() and target.read_bytes() != raw:
        raise ValueError("publication_manifest_changed_use_new_batch")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    if not (args.publish or args.verify):
        print(json.dumps({"prepared_files": len(files)}))
        return
    selected = cfg["deployment"]
    argv = [selected["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "UpdateHostKeys=no", "-o", f"ConnectTimeout={selected['connect_timeout_seconds']}",
            selected["ssh_target"], shlex.join([selected["remote_python"], "-c", VERIFY if args.verify else REMOTE])]
    payload = {"deployment": selected, "files": {name: base64.b64encode(raw).decode() for name, raw in files.items()}}
    result = subprocess.run(argv, input=json.dumps(payload), capture_output=True, text=True,
                            timeout=selected["publication_timeout_seconds"], check=False)
    if result.returncode:
        raise RuntimeError(result.stderr[-1500:])
    receipt = json.loads(result.stdout)
    receipt_path = Path(cfg["receipt"])
    if args.verify:
        receipt_path = receipt_path.with_name(receipt_path.stem + "-verification.json")
    (ROOT / receipt_path).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
