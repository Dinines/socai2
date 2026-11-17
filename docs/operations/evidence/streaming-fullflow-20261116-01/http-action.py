"""One explicit business HTTP operation; intent and complete exchanges are exclusive."""
import json, sys, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

folder=Path(sys.argv[1]);phase=sys.argv[2];p=json.loads((folder/'profile.json').read_text());request=json.loads(sys.stdin.read())
outdir=folder/'out'
def write(name,value):
    with (outdir/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def http(method,path,body=None):
    record={'request':{'method':method,'path':path},'observed_at':datetime.now(timezone.utc).isoformat()}
    if body is not None:record['request']['body']=body
    req=urllib.request.Request(p['http_base']+path,method=method,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:record['response']={'status':r.status,'body':json.load(r)}
    except urllib.error.HTTPError as e:record['response']={'status':e.code,'body':e.read().decode()}
    except Exception as e:record.update(outcome='unknown',error_type=type(e).__name__)
    return record
if phase=='read-ai':
    result={'batch_id':p['batch_id'],'exchanges':[http('GET',path) for path in request['paths']]}
elif phase in {'create-whole','create-single'}:
    ai=json.loads((outdir/'http-read-ai.json').read_text())
    assert len(ai['exchanges'])==4
    for x in ai['exchanges']:
        assert x['response']['status']==200 and x['response']['body']['current']['valid_for_current_input']
    write('intent-'+phase+'.json',{'state':'started_outcome_unknown','request':request})
    result=http('POST','/api/v1/socai2/cases',request['body'])
elif phase in {'check-whole','check-whole-update','check-incident'}:
    assert request['body']['mode']=='check'
    write('intent-'+phase+'.json',{'state':'started_outcome_unknown','request':request})
    result=http('POST',request['path'],request['body'])
else:raise ValueError(phase)
write('http-'+phase+'.json',result)
print(json.dumps(result,ensure_ascii=False))
