"""Read only selected 21 containers, existing data identity and release prerequisites."""
import hashlib,json,subprocess,urllib.request
from pathlib import Path
c=CONFIG
def call(args):
 r=subprocess.run(args,text=True,capture_output=True,timeout=c['http_timeout_seconds'])
 if r.returncode:raise RuntimeError('command_failed:'+args[0]+':'+str(r.returncode))
 return r.stdout
def inspect(name):
 d=json.loads(call(['docker','inspect',name]))[0]
 return {'name':d['Name'],'id':d['Id'],'image':d['Image'],'running':d['State']['Running'],'started_at':d['State']['StartedAt'],'restart_count':d['RestartCount'],'mounts':d['Mounts'],'ports':d['NetworkSettings']['Ports']}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
old=inspect(c['old_container']);assert old['id']==c['old_id'] and old['running']
core={name:inspect(name) for name in c['core_containers']}
assert all(d['running'] for d in core.values())
state={str(p.relative_to(c['state_root'])):digest(p) for p in Path(c['state_root']).rglob('*') if p.is_file()}
configuration={p.name:json.loads(p.read_text()) for p in Path(c['old_config']).glob('*.json') if p.name in {'service.json','upstream.json','viewer.json'}}
assert configuration['upstream.json']['base_url']==c['upstream_base_url']
assert configuration['service.json']['environment_label']==configuration['upstream.json']['environment_label']==c['environment_label']
runtime={}
for line in Path(c['prior_acceptance_env']).read_text().splitlines():
 if '=' in line:
  k,v=line.split('=',1)
  if k in {'ACCEPTANCE_MATERIALS_DIR','ACCEPTANCE_MATERIALS_TARGET','ACCEPTANCE_RESULTS_DIR','ACCEPTANCE_RESULTS_TARGET','ACCEPTANCE_USER'}:runtime[k]=v.strip('"\'')
assert len(runtime)==5
prepared=Path(runtime['ACCEPTANCE_RESULTS_DIR'])/'prepared'
session=json.loads((prepared/'session.json').read_text())
assert session['profile']['environment_label']=='21 正式调查服务（aisoc.socai2）'
responses={}
for label,path in [('capabilities','/test-api/v1/capabilities'),('case','/api/v1/socai2/cases/'+c['case_id'])]:
 with urllib.request.urlopen(c['local_entry']+path,timeout=c['http_timeout_seconds']) as r:
  body=r.read();responses[label]={'status':r.status,'sha256':hashlib.sha256(body).hexdigest(),'data':json.loads(body)}
assert responses['case']['data']['case']['id']==c['case_id']
assert not Path(c['remote_root']).exists()
print(json.dumps({'status':'passed_readonly_preflight','old':old,'core':core,'ledger_sha256':state,'configuration':configuration,'acceptance_mounts':runtime,'prepared_sha256':digest(prepared/'session.json'),'http':responses},ensure_ascii=False))
