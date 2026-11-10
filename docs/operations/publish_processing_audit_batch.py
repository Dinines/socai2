"""Merge saved audit batches into an existing 4177 site, without restarting it."""
import argparse
import base64
import inspect
import json
import shlex
import subprocess
from pathlib import Path

import update_processing_audit as site
from read_processing_audit_20261106 import check_credentials

ROOT = Path(__file__).resolve().parents[2]

REMOTE = r'''
import base64,fcntl,hashlib,json,os,pathlib,re,subprocess,sys,tempfile
from datetime import datetime
import urllib.request
request=json.load(sys.stdin); cfg=request['deployment']; output=pathlib.Path(cfg['site'])
def sha(raw): return hashlib.sha256(raw).hexdigest()
def command(args):
 p=subprocess.run(args,text=True,capture_output=True,timeout=30)
 if p.returncode: raise RuntimeError('workbench_command_failed_'+str(p.returncode))
 return p.stdout
def inspect_container(): return json.loads(command([cfg['docker'],'inspect',cfg['container']]))[0]
def container_ids(): return sorted(command([cfg['docker'],'ps','--format','{{.Names}} {{.ID}}']).splitlines())
def atomic(path,raw,mode=0o644,owner=None):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f: f.write(raw); temp=pathlib.Path(f.name)
 try:
  os.chmod(temp,mode)
  if owner: os.chown(temp,*owner)
  temp.replace(path)
 finally: temp.unlink(missing_ok=True)
def registry(raw):
 match=re.search(r'<script type="application/json" id="audit-records">(.*?)</script>',raw.decode(),re.S)
 assert match,'unrecognized_registry'
 return {r['id']:r for r in json.loads(match[1])}
before=inspect_container(); ids_before=container_ids()
assert before['Image']==cfg['expected_image'],'unexpected_image'
assert before['Config']['Labels']['com.docker.compose.project.config_files']==cfg['expected_compose'],'unexpected_compose'
assert any(m['Source']==cfg['expected_base_release'] and m['Destination']==cfg['source_mount'] for m in before['Mounts']),'unexpected_release'
assert output.resolve()==output,'unexpected_site_path'
lock_path=pathlib.Path(tempfile.gettempdir())/('socai2-audit-'+sha(os.path.normcase(str(output.resolve())).encode())+'.lock')
with lock_path.open('a+b') as lock:
 fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 index=output/'index.html'; old_index=index.read_bytes(); old=registry(old_index)
 history_helper={'datetime':datetime}
 exec(request['history_helper_source'],history_helper)
 merged=dict(old); refreshed=[]
 for row in request['records']:
  if row['id'] in old and old[row['id']]!=row:
   expected=cfg.get('refresh_records',{}).get(row['id'])
   assert expected and sha(json.dumps(old[row['id']],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())==expected,'record_conflict'
   assert history_helper['preserves_history'](old[row['id']],row),'snapshot_would_replace_history'
   refreshed.append(row['id'])
  merged[row['id']]=row
 decoded={name:base64.b64decode(value) for name,value in request['files'].items()}
 for name,raw in decoded.items():
  path=pathlib.PurePosixPath(name); target=output/path
  assert not path.is_absolute() and '..' not in path.parts and path.parts[0] in {'cases','subjects','logs'},'invalid_file_path'
  assert target.resolve().is_relative_to(output) and not target.is_symlink(),'file_path_escape'
  assert not target.exists() or target.read_bytes()==raw,'immutable_file_conflict'
 # Use the exact local index renderer; saved evidence is never executable code.
 namespace={}; exec(request['index_renderer_source'],namespace)
 helper={'render_index':namespace['render_index'],'json':json,'datetime':datetime}
 exec(request['registry_helper_source'],helper)
 match=re.search(r'<script type="application/json" id="audit-retired-records">(.*?)</script>',old_index.decode(),re.S)
 retired=json.loads(match[1]) if match else []
 new_index=helper['registry_html'](merged,output,retired)
 assert all(key in refreshed or registry(new_index)[key]==value for key,value in old.items()),'old_records_changed'
 private=pathlib.Path(cfg['private']); assert private.resolve()==private,'unexpected_private_path'
 private.mkdir(parents=True,exist_ok=True,mode=0o700)
 if not (private/'index-before.html').exists(): atomic(private/'index-before.html',old_index,0o600)
 for name,raw in decoded.items():
  if not (output/name).exists(): atomic(output/name,raw,owner=cfg['site_owner'])
 atomic(index,new_index,owner=cfg['site_owner'])
 for name,raw in {**decoded,'index.html':new_index}.items():
  with urllib.request.urlopen(cfg['base_url']+'/'+name,timeout=5) as response:
   assert response.status==200 and response.read()==raw,'http_content_mismatch'
 after=inspect_container(); ids_after=container_ids()
 assert before['Id']==after['Id'] and ids_before==ids_after,'containers_changed'
 receipt={'status':'published','static_only':True,'model_calls':0,'database_writes':0,'runtime_sources_changed':False,
  'old_records':len(old),'new_records':len(merged),'added_records':len(merged)-len(old),
  'old_records_preserved':not refreshed,'refreshed_records':refreshed,'old_files_preserved':True,'unrelated_records_preserved':True,
  'files_verified':len(decoded),'http_verified':len(decoded)+1,'containers_unchanged':True,
  'old_index_sha256':sha(old_index),'new_index_sha256':sha(new_index),'batch_manifest_sha256':request['manifest_sha256'],
  'incident_urls':[cfg['base_url']+'/'+s['detail'] for r in request['records'] for s in r['subjects'] if s['kind']=='incident']}
 atomic(private/'receipt.json',(json.dumps(receipt,indent=2)+'\n').encode(),0o600)
 print(json.dumps(receipt))
'''


def prepare(config):
    records, files = [], {}
    for batch in config['batches']:
        for row in site.cases_from(ROOT / batch):
            record, additions = site.prepare(*row)
            for name, content in additions.items():
                check_credentials(content)
                if name in files and files[name] != content:
                    raise ValueError('batch_file_conflict')
            records.append(record)
            files.update(additions)
    if not records or len({r['id'] for r in records}) != len(records):
        raise ValueError('batch_records_invalid')
    manifest = {'batches': config['batches'], 'record_ids': [r['id'] for r in records],
                'files': {name: site.sha(raw) for name, raw in files.items()},
                'static_only': True, 'model_calls': 0, 'database_writes': 0}
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    path = ROOT / config['manifest']
    if path.exists() and path.read_bytes() != raw:
        raise ValueError('immutable_publication_manifest_changed')
    if not path.exists():
        path.write_bytes(raw)
    return {'deployment': config['deployment'], 'records': records,
            'files': {name: base64.b64encode(raw).decode() for name, raw in files.items()},
            'manifest_sha256': site.sha(raw),
            'history_helper_source': inspect.getsource(site.timestamp) + '\n' + inspect.getsource(site.preserves_history),
            'index_renderer_source': (ROOT / 'docs/operations/processing_audit_index.py').read_text(),
            'registry_helper_source': inspect.getsource(site.timestamp) + '\n' + inspect.getsource(site.registry_html)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    config = site.read(args.config)
    payload = prepare(config)
    if not args.publish:
        print(json.dumps({'status': 'prepared', 'records': len(payload['records']), 'files': len(payload['files'])}))
        return
    cfg = config['deployment']
    argv = [cfg['ssh_binary'], '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o',
            'UpdateHostKeys=no', '-o', f"ConnectTimeout={cfg['connect_timeout_seconds']}", cfg['ssh_target'],
            shlex.join([cfg['remote_python'], '-c', REMOTE])]
    response = subprocess.run(argv, input=json.dumps(payload).encode(), capture_output=True,
                              timeout=cfg['command_timeout_seconds'], check=False)
    if response.returncode:
        raise RuntimeError(response.stderr.decode(errors='replace')[-1500:])
    receipt = json.loads(response.stdout)
    (ROOT / config['receipt']).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
