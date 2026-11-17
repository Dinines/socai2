"""Configure the existing workbench's saved-only mode and retain three saved cases."""
import base64
import hashlib
import importlib.util
import inspect
import json
import shlex
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
cfg = json.loads((HERE / 'config.json').read_text())
spec = importlib.util.spec_from_file_location('saved_batch_site', ROOT / cfg['source_helper'])
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
site = ROOT / cfg['local_site']
records = list(helper.site.existing(site / 'index.html').values())
assert len(records) == 3 and all(r['batch'].startswith(cfg['keep_batch']) for r in records)
files = {str(p.relative_to(site)): base64.b64encode(p.read_bytes()).decode()
         for p in site.rglob('*') if p.is_file() and p.relative_to(site).parts[0] in {'cases', 'subjects', 'logs'}}
request = {'config': cfg, 'records': records, 'files': files,
           'index': base64.b64encode((site / 'index.html').read_bytes()).decode(),
           'replace_source': inspect.getsource(helper.replace_site),
           'target': {'site': cfg['deployment']['site'], 'backup': cfg['deployment']['private']}}

REMOTE = r'''
import base64,copy,hashlib,json,os,subprocess,sys,time,urllib.request,urllib.error,re
from pathlib import Path
r=json.load(sys.stdin); c=r['config']; d=c['deployment']; root=Path(d['private'])
def sha(raw):return hashlib.sha256(raw).hexdigest()
def command(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=d['command_timeout_seconds'])
 if p.returncode:raise RuntimeError('command_failed_'+str(p.returncode))
 return p.stdout
def current():return json.loads(command([d['docker'],'inspect',d['container']]))[0]
def others():return {name:cid for name,cid in (line.split(' ',1) for line in command([d['docker'],'ps','--format','{{.Names}} {{.ID}}']).splitlines()) if name!=d['container']}
def write(name,value):
 with (root/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
 os.chmod(root/name,0o600)
before=current(); other_before=others()
assert before['Id']==d['expected_container_id'] and before['Image']==d['expected_image']
assert before['Config']['Labels']['com.docker.compose.project.config_files']==d['expected_compose']
oldfile=Path(d['expected_compose']);oldraw=oldfile.read_bytes()
assert sha(oldraw)==d['expected_compose_sha256']
root.mkdir(mode=0o700,parents=True,exist_ok=False)
(root/'workbench-before.json').write_bytes(oldraw);os.chmod(root/'workbench-before.json',0o600)
compose=json.loads(oldraw);assert set(compose['services'])=={d['service']}
after=copy.deepcopy(compose);service=after['services'][d['service']]
args=service['command'];assert args.count('--source')==1 and '--tenant' not in args
assert args[args.index('--source')+1]=='aisoc'
args[args.index('--source')+1]=c['source'];args.extend(['--tenant',c['tenant']])
service.setdefault('environment',{})['SOCAI2_AUDIT_DATABASE_URL']=c['database_url']
write('workbench-after.json',after)
compose_args=[d['docker'],'compose','--project-name',d['project'],'--project-directory',d['project_directory'],'-f',str(root/'workbench-after.json')]
command(compose_args+['config','--quiet'])
write('intent.json',{'mode':c['mode'],'container_before':before['Id'],'old_compose_sha256':sha(oldraw),'new_compose_sha256':sha((root/'workbench-after.json').read_bytes()),'keep_case_ids':[x['scope_id'] for x in r['records']],'database_writes':0})
command([d['docker'],'stop','--time',str(d['stop_timeout_seconds']),d['container']])
try:
 exec(r['replace_source'])
 receipt=replace_site(r)
 command(compose_args+['up','-d','--no-deps','--force-recreate',d['service']])
 deadline=time.monotonic()+d['health_timeout_seconds']
 while True:
  live=current()
  if live['State']['Running'] and live['State'].get('Health',{}).get('Status')=='healthy':break
  if time.monotonic()>deadline:raise RuntimeError('workbench_health_not_ready')
  time.sleep(1)
 assert live['Image']==before['Image'] and live['Mounts']==before['Mounts']
 assert live['Config']['Cmd']==args and live['Config']['Entrypoint']==before['Config']['Entrypoint']
 assert live['HostConfig']['NetworkMode']==before['HostConfig']['NetworkMode']
 env=dict(e.split('=',1) for e in live['Config']['Env']);oldenv=dict(e.split('=',1) for e in before['Config']['Env'])
 assert env.pop('SOCAI2_AUDIT_DATABASE_URL')=='';oldenv.pop('SOCAI2_AUDIT_DATABASE_URL');assert env==oldenv
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with op.open(d['base_url']+'/_workbench/status',timeout=8) as response:status=json.load(response)
 assert status=={'enabled':False,'source':c['source'],'tenant_id':c['tenant']}
 for path in ('/','/index.html',*[ '/'+x['detail'] for x in r['records']],*[ '/'+x['logs']['index'] for x in r['records']]):
  with op.open(d['base_url']+path,timeout=8) as response:
   raw=response.read();assert response.status==200
   if path in ('/','/index.html'):
    items=json.loads(re.search(rb'<script type="application/json" id="audit-records">(.*?)</script>',raw,re.S)[1]);assert {x['id'] for x in items}=={x['id'] for x in r['records']}
   else:assert raw==base64.b64decode(r['files'][path[1:]])
 assert others()==other_before
 receipt.update(mode=c['mode'],online_status=status,container_before=before['Id'],container_after=live['Id'],image_unchanged=True,source_and_mounts_unchanged=True,other_services_unchanged=True,compose=str(root/'workbench-after.json'),http_verified=8)
 write('delivery.json',receipt)
 print(json.dumps(receipt))
except BaseException as exc:
 write('failure.json',{'error_type':type(exc).__name__,'message':str(exc) if isinstance(exc,AssertionError) else 'workbench_switch_failed','state':'inspect_before_retry'})
 raise
'''

intent = HERE / 'intent.json'
with intent.open('x') as f:
    json.dump({'mode': cfg['mode'], 'target': request['target'], 'case_ids': [r['scope_id'] for r in records],
               'index_sha256': hashlib.sha256((site / 'index.html').read_bytes()).hexdigest(),
               'files': len(files) + 1, 'database_writes': 0, 'model_calls': 0}, f, indent=2)
d = cfg['deployment']
result = subprocess.run([d['ssh_binary'], '-T', '-o', 'BatchMode=yes', '-o', f"ConnectTimeout={d['connect_timeout_seconds']}",
                         d['ssh_target'], shlex.join([d['remote_python'], '-c', REMOTE])],
                        input=json.dumps(request), capture_output=True, text=True, timeout=d['command_timeout_seconds'])
if result.returncode:
    (HERE / 'failure.json').write_text(json.dumps({'code': result.returncode, 'stderr': result.stderr}, indent=2))
    raise RuntimeError('inspect_remote_private_receipt_before_any_retry')
receipt = json.loads(result.stdout)
with (HERE / 'remote.json').open('x') as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2); f.write('\n')
print(json.dumps(receipt, ensure_ascii=False))
