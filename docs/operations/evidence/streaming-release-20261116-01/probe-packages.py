"""No-network import/configuration checks against the newly built release images."""
import json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);c=json.loads((root/'config/release.json').read_text());hp=json.loads((root/'config/http-profile.json').read_text())

def run(args,code):
 r=subprocess.run(args,input=code,text=True,capture_output=True,timeout=c['command_timeout_seconds'])
 if r.returncode:
  p=root/'private'/('offline-probe-'+str(len(list((root/'private').iterdir())))+'.log');p.write_text(r.stdout+'\n'+r.stderr);p.chmod(0o600)
  raise RuntimeError('probe_failed; private_detail='+str(p))
 return json.loads(r.stdout.splitlines()[-1])
http_code='''import hashlib,json,pathlib
from investigation_http.main import app,configured_database_name
p=pathlib.Path('/app');m=json.loads(pathlib.Path('/run/package-manifest.json').read_text())
files=0
for name,h in m['files'].items():
 if name in {'manage.py','profile.json','Dockerfile'}:continue
 data=(p/name).read_bytes();assert hashlib.sha256(data).hexdigest()==h,name
 if name.endswith('.py'):compile(data,str(p/name),'exec')
 files+=1
actual=app.openapi();expected=json.loads((p/'contract/openapi.json').read_text())
contract=lambda d:{k:v for k,v in d.items() if k not in {'info','servers'}}
assert contract(actual)==contract(expected)
assert not actual.get('security') and not actual.get('components',{}).get('securitySchemes')
count=sum(1 for path,methods in actual['paths'].items() for verb in methods if path.startswith('/api/v1/socai2/') and verb in {'get','post','put','patch','delete'})
print(json.dumps({'source_files':files,'operations':count,'release':actual['info']['version'],'database':configured_database_name(),'network':'none','database_writes':0,'model_calls':0}))
'''
hdir=root/'http/releases'/hp['release']
http=run(['docker','run','--rm','-i','--network','none','--read-only','--env-file',str(root/'http/private'/hp['release']/'runtime.env'),'--mount','type=bind,src='+str(hdir/'manifest.json')+',dst=/run/package-manifest.json,readonly','--entrypoint','python',hp['image'],'-B','-'],http_code)
analysis_code='''import json,os
from app.socai2.analysis_dispatch_runtime import load_profile
from app.socai2.runtime_policy import load_policy
from app.socai2.analysis_case_executor import executors
p=load_profile('/run/analysis/dispatcher.json'); policy=load_policy('/run/analysis/investigation-policy.toml')
assert int(os.environ['AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS'])==policy.model.max_prepared_bytes
print(json.dumps({'factory_imported':callable(executors),'enabled':p['enabled'],'tenant_id':p['tenant_id'],'max_running_tasks':p['dispatch']['max_running_tasks'],'poll_interval_seconds':p['dispatch']['poll_interval_seconds'],'policy_sha256':policy.sha256,'output_tokens':dict(policy.model.output_tokens),'max_prepared_bytes':policy.model.max_prepared_bytes,'total_tokens':{'alert':policy.alert_basic.max_total_tokens,'incident':policy.incident_diagnosis.max_total_tokens,'case':policy.case.max_total_tokens},'network':'none','database_writes':0,'model_calls':0}))
'''
base=json.loads((root/'analysis-docker-base.json').read_text());i=base.index('--network');base[i+1]='none'
analysis=run([*base,'--rm','-i','--entrypoint','python',c['processing_image_tag'],'-B','-'],analysis_code)
print(json.dumps({'status':'passed','http':http,'analysis':analysis},indent=2))
