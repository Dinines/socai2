import json,shlex,subprocess,sys
from pathlib import Path
E=Path(__file__).resolve().parent;out=E/'revision-02/smoke/out';phase=sys.argv[1]
assert phase in {'ai','case'}
p=json.loads((out.parent/'profile.json').read_text());req=json.loads((out/'case-request.json').read_text())
cfg={k:req[k] for k in ('alert_id','incident_id')};cfg.update(tenant_id=p['tenant_id'],batch_id=p['batch_id'])
if phase=='case':cfg['case_id']=json.loads((out/'case-post.json').read_text())['response']['body']['primary_case_id']
dest=out/(phase+'-pg-01.json');assert not dest.exists()
code=(E/'capture-minimal.py').read_text()
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12','sting-infra21',shlex.join(['docker','exec','-i','socai2-production-http-20261116','python','-c',code])],input=json.dumps(cfg),capture_output=True,text=True,timeout=55)
if r.returncode:raise RuntimeError(r.stderr)
body=json.loads(r.stdout)
with dest.open('x') as f:json.dump(body,f,ensure_ascii=False,indent=2)
print(json.dumps({'source':body['source'],'identity':body['identity'],'counts':body['counts']},ensure_ascii=False,indent=2))
