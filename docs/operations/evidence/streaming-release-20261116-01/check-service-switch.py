"""Read back the exact release and unchanged surrounding service baseline."""
import hashlib,json,subprocess,sys,urllib.request
from pathlib import Path
root=Path(sys.argv[1]);c=json.loads((root/'config/release.json').read_text());hp=json.loads((root/'config/http-profile.json').read_text())
raw=subprocess.check_output(['docker','ps','-aq'],text=True).split()
allc=json.loads(subprocess.check_output(['docker','inspect',*raw]));by={x['Name'].lstrip('/'):x for x in allc}
names=[hp['container'],c['fusion']['name'],c['analysis']['name'],c['swagger']['container'],c['viewer']['name']]
out={'release':c['release'],'services':{}}
for name in names:
 d=by[name];assert d['State']['Running'] and d['RestartCount']==0
 out['services'][name]={'id':d['Id'],'image':d['Image'],'state':d['State']['Status'],'started_at':d['State']['StartedAt']}
for name in [*c['must_remain_stopped'],*c['stop_after_readiness'],c['viewer']['old']]:assert not by[name]['State']['Running'],name
before=json.loads((root/'http/releases'/hp['release']/'before.json').read_text())
allowed={*c['stop_after_readiness'],c['viewer']['old']}
for name,expected in before.items():
 n=name.lstrip('/')
 if n in allowed:continue
 d=by[n];assert d['State']['Running'] and {'id':d['Id'],'image':d['Image'],'started_at':d['State']['StartedAt']}==expected,n
out['other_running_services_unchanged']=len(before)-len(allowed)
out['old_execution_services_stopped']=True
base=f"http://{c['viewer']['bind']}:{c['viewer']['port']}"
out['reads']={}
for path in ['/api/v1/socai2/alerts','/test-api/v1/capabilities','/test-api/v1/batches']:
 with urllib.request.urlopen(base+path,timeout=10) as r:out['reads'][path]={'status':r.status,'body':json.load(r)}
cap=out['reads']['/test-api/v1/capabilities']['body'];assert cap['environment_label']==c['release'] and cap['service_version']=='0.6.0'
assert cap['investigation_http']['tenant_id']==c['identity']['tenant_id']
out['config_sha256']={name:hashlib.sha256((root/'viewer/config'/name).read_bytes()).hexdigest() for name in ['service.json','upstream.json','viewer.json','investigation-openapi.json']}
out['status']='passed';print(json.dumps(out,ensure_ascii=False,indent=2))
