"""Read the released HTTP contract and existing judgments; never write business data."""
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
p = argparse.ArgumentParser()
p.add_argument('--profile', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--fixture', type=Path)
a = p.parse_args()
cfg = json.loads(a.profile.read_text())
secret = json.loads((ROOT/cfg['credential']['file']).read_text())
if cfg['credential']['kind']=='existing_login':
    req=urllib.request.Request(cfg['credential']['login_url'],data=json.dumps({k:secret[k] for k in ('email','password')}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=cfg['timeout_seconds']) as r:
        token=json.load(r)['access_token']
else:
    token=secret['api_key']
observations=[]

def get(path):
    req=urllib.request.Request(cfg['base_url']+path,headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=cfg['timeout_seconds']) as r:
        raw=r.read();body=json.loads(raw)
        observations.append(dict(method='GET',path=path,status=r.status,sha256=hashlib.sha256(raw).hexdigest()))
        return body

assert get('/readyz')['status']=='ready'
doc=get('/openapi.json')
assert doc['info']['version']==cfg['release']
assert sum(len(v) for p,v in doc['paths'].items() if p.startswith('/api/v1/socai2'))==64
base='/api/v1/socai2/cases'
if a.fixture:
    fixture=json.loads(a.fixture.read_text());cid=fixture['case_id'];rid=fixture['result_id']
else:
    items=[item['case'] for item in get(base+'?limit=20')['items']]
    chosen=next((item for item in items if item.get('current_assessment_id')),None)
    if chosen is None:
        raise RuntimeError('no_existing_assessment_in_first_page; no business writes attempted')
    cid=chosen['id'];rid=None
case=get(base+'/'+cid)
history=get(base+'/'+cid+'/assessments?limit=1')
assert history['total']>=1 and len(history['items'])==1
latest=history['items'][0]
assert latest['id']==case['case']['current_assessment_id']
if rid is None:
    rid=latest['results'][0]['id']
preview=get(base+'/'+cid+'/results/'+rid+'/adoption-preview')
assert preview['case_id']==cid and preview['candidate']['id']==rid
assert preview['current_assessment']['id']==case['case']['current_assessment_id']
assert len(preview['review_token'])==64
if a.fixture:
    assert latest['id']==fixture['adoption']['assessment_id']
    assert get(base+'/'+cid+'/tasks/'+fixture['task_id'])['current']['state']=='not_started'
    assert get(base+'/'+cid+'/runs/'+fixture['pending_run_id'])['run']['state']=='pending_update'
result=dict(passed=True,mode='business_read_only',business_writes=0,release=cfg['release'],database=cfg['database'],
    operations=64,case_id=cid,result_id=rid,assessment_id=latest['id'],history_total=history['total'],
    can_adopt=preview['can_adopt'],refusal_reasons=preview['refusal_reasons'],
    unfinished_tasks=len(preview['unfinished_tasks']),unfinished_runs=len(preview['unfinished_runs']),
    http_requests=len(observations),observations=observations,model_calls=0)
a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='observations'}))
