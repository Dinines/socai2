import json, shlex, subprocess, sys
from pathlib import Path
from uuid import uuid4

root=Path(__file__).resolve().parent;p=json.loads((root/'batch/profile.json').read_text());phase=sys.argv[1]
snapshot=json.loads((root/'ai-initial-pg.json').read_text());iid=snapshot['rows']['incidents'][0]['id']
assert len(snapshot['rows']['incident_alerts'])==3
dest=root/('http-'+phase+'.json');assert not dest.exists()
if phase=='read-ai':
    req={'paths':[f'/api/v1/socai2/alerts/{a}/analysis' for a in p['alert_ids'][:3]]+[f'/api/v1/socai2/incidents/{iid}/analysis']}
elif phase in {'create-whole','create-single'}:
    kind=phase.split('-')[1]
    body={'operation_key':str(uuid4()),'title':p['case_titles'][kind]}
    body.update({'incident_ids':[iid]} if kind=='whole' else {'alert_ids':[p['alert_ids'][0]]})
    req={'body':body}
elif phase in {'check-whole','check-whole-update'}:
    cid=json.loads((root/'http-create-whole.json').read_text())['response']['body']['primary_case_id']
    req={'path':f'/api/v1/socai2/cases/{cid}/investigations','body':{'operation_key':str(uuid4()),'mode':'check'}}
elif phase=='check-incident':
    before=json.loads((root/'before-incident-check-pg.json').read_text())['rows']
    assert len(before['incident_alerts'])==4 and len(before['alert_assessments'])==4 and len(before['incident_diagnoses'])==1
    req={'path':f'/api/v1/socai2/incidents/{iid}/diagnose','body':{'operation_key':str(uuid4()),'mode':'check'}}
else:raise ValueError(phase)
with (root/('request-'+phase+'.json')).open('x') as f:json.dump(req,f,ensure_ascii=False,indent=2)
code=(root/'http-action.py').read_text()
cmd=['python3','-c',code,p['remote_directory'],phase]
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12',p['ssh_target'],shlex.join(cmd)],input=json.dumps(req),capture_output=True,text=True,timeout=55)
with (root/('exchange-'+phase+'.json')).open('x') as f:json.dump({'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},f,ensure_ascii=False,indent=2)
assert r.returncode==0,'inspect exchange receipt before any retry'
result=json.loads(r.stdout)
with dest.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
if phase=='read-ai':
    for x in result['exchanges']:assert x['response']['status']==200 and x['response']['body']['current']['valid_for_current_input']
    print(json.dumps({'phase':phase,'statuses':[x['response']['status'] for x in result['exchanges']]}))
else:
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert result.get('response',{}).get('status')==(202 if phase.startswith('check-') else 201)
