"""Read current A/I and submit exactly one neutral business Case request."""
import json,sys,urllib.error,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from uuid import UUID
root=Path(sys.argv[1]);phase=sys.argv[2];batch=root/'verification/release-smoke-20261116-01';p=json.loads((batch/'profile.json').read_text());request=json.loads(sys.stdin.read())
assert phase in {'read-ai','create-case'} and request['http_base']==p['http_base']
for key in ['alert_id','incident_id']:UUID(request[key])
outdir=batch/'out'
def write(name,value):
 with (outdir/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def http(method,path,body=None):
 item={'request':{'method':method,'path':path},'observed_at':datetime.now(timezone.utc).isoformat()}
 if body is not None:item['request']['body']=body
 req=urllib.request.Request(p['http_base']+path,method=method,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers={'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=30) as r:item['response']={'status':r.status,'body':json.load(r)}
 except urllib.error.HTTPError as exc:item['response']={'status':exc.code,'body':exc.read().decode()}
 except Exception as exc:item.update(outcome='unknown',error_type=type(exc).__name__)
 return item
if phase=='read-ai':
 out={'batch_id':p['batch_id'],'exchanges':[http('GET',f"/api/v1/socai2/{kind}s/{request[kind+'_id']}/analysis") for kind in ('alert','incident')]}
 write('ai-http.json',out)
else:
 ai=json.loads((outdir/'ai-http.json').read_text())
 for ex in ai['exchanges']:
  assert ex['response']['status']==200 and ex['response']['body']['current'] is not None
  assert ex['response']['body']['current']['valid_for_current_input']
 body=request['body'];UUID(body['operation_key'])
 assert body=={'operation_key':body['operation_key'],'title':'网络连接调查','incident_ids':[request['incident_id']]}
 write('case-intent.json',{'state':'started_outcome_unknown','request':request})
 out=http('POST','/api/v1/socai2/cases',body);write('case-post.json',out)
 assert out.get('response',{}).get('status')==201,'inspect_actual_outcome_before_any_retry'
 result=out['response']['body'];assert result['operation_key']==body['operation_key'] and len(result['allocations'])==1
 allocation=result['allocations'][0];cid=allocation['case_id']
 assert allocation['added_alert_ids']==[request['alert_id']] and allocation['linked_incident_ids']==[request['incident_id']]
 assert allocation['initial_task']['status']=='accepted' and allocation['initial_task']['subject_id']==cid
 reads={'exchanges':[http('GET',allocation['case_url']),http('GET',allocation['initial_task']['status_url'])]}
 write('case-initial-reads.json',reads)
 assert all(x['response']['status']==200 for x in reads['exchanges'])
print(json.dumps(out,ensure_ascii=False,indent=2))
