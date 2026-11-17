"""Read-only post-release story and source checks using an explicit profile."""
import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--profile',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();cfg=json.loads(args.profile.read_text())
args.output.mkdir(parents=True,exist_ok=False)
secret=json.loads((ROOT/cfg['credential']['file']).read_text())
if cfg['credential']['kind']=='existing_login':
    req=urllib.request.Request(cfg['credential']['login_url'],data=json.dumps({k:secret[k] for k in ('email','password')}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=cfg['timeout_seconds']) as r:token=json.load(r)['access_token']
else:token=secret['api_key']
receipts=[]
def get(path):
    req=urllib.request.Request(cfg['base_url']+path,headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=cfg['timeout_seconds']) as r:body=json.load(r);status=r.status
    receipts.append({'method':'GET','path':path,'status':status,'body':body})
    (args.output/'responses.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
    return body
contract=get('/openapi.json')
assert contract['info']['version']==cfg['release']
assert sum(len(methods) for p,methods in contract['paths'].items() if p.startswith('/api/v1/socai2'))==cfg['expected_operations']
path='/api/v1/socai2/cases/'+cfg['case_id']
case=get(path)
page=get(path+'/story?limit=100')
alerts={r['alert_id'] for r in case['members']}
for item in page['items']:
    if item['alert']:
        assert item['alert']['id'] in alerts
    if item['run']:
        assert item['run']['case_id']==cfg['case_id']
        assert all(r['source_run_id']==item['run']['id'] and r['case_id']==cfg['case_id'] for r in item['results'])
    if item['task_revision']:assert item['task_revision']['case_id']==cfg['case_id']
for kind in ['alert','investigation','human_result']:
    row=next((r for r in page['items'] if r['kind']==kind),None)
    if not row:continue
    if kind=='alert':assert get('/api/v1/socai2/alerts/'+row['alert']['id'])['facts']==row['alert']
    if kind=='investigation':
        assert get(path+'/runs/'+row['run']['id'])['run']==row['run']
        for result in row['results']:assert get(path+'/results/'+result['id'])['result']==result
    if kind=='human_result':
        rev=row['task_revision'];assert get(path+'/tasks/'+rev['task_id']+'/revisions/'+rev['id'])==rev
assert get(path)['case']==case['case']
result={'passed':True,'release':cfg['release'],'database_expected':cfg['database'],'case_id':cfg['case_id'],'http_gets':len(receipts),'writes':0,'models':0,'story_total':page['total'],'case_unchanged':True}
(args.output/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
