"""Read-only verification for released exploration save/restore endpoints."""
import argparse
import json
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--profile',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();cfg=json.loads(a.profile.read_text());a.output.mkdir(parents=True,exist_ok=False)
secret=json.loads((ROOT/cfg['credential']['file']).read_text())
if cfg['credential']['kind']=='existing_login':
 request=urllib.request.Request(cfg['credential']['login_url'],data=json.dumps({k:secret[k] for k in ('email','password')}).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(request,timeout=cfg['timeout_seconds']) as r: token=json.load(r)['access_token']
else: token=secret['api_key']
receipts=[]
def get(path):
 request=urllib.request.Request(cfg['base_url']+path,headers={'Authorization':'Bearer '+token})
 with urllib.request.urlopen(request,timeout=cfg['timeout_seconds']) as r: body=json.load(r);status=r.status
 receipts.append({'method':'GET','path':path,'status':status,'body':body})
 (a.output/'responses.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
 return body
contract=get('/openapi.json');assert contract['info']['version']==cfg['release']
assert sum(len(v) for k,v in contract['paths'].items() if k.startswith('/api/v1/socai2'))==cfg['expected_operations']
path='/api/v1/socai2/cases/'+cfg['case_id'];before=get(path)
base=get(path+'/exploration-base');saved=get(path+'/exploration')['snapshot']
assert base['case_id']==cfg['case_id']
if 'expected_snapshot_id' in cfg:
 assert saved and saved['id']==cfg['expected_snapshot_id']
 assert saved['base']['run_id']==cfg['expected_base_run_id']
 assert base['run_id']==cfg['expected_latest_run_id'] and base['graph_state']=='unavailable'
if base['run_id']:
 assert get(path+'/exploration-base?run_id='+base['run_id'])==base
assert get(path)['case']==before['case']
result={'passed':True,'release':contract['info']['version'],'database_expected':cfg['database'],'operations':cfg['expected_operations'],'case_id':cfg['case_id'],'http_gets':len(receipts),'base_kind':base['kind'],'graph_state':base['graph_state'],'has_saved_exploration':saved is not None,'writes':0,'models':0,'case_unchanged':True}
(a.output/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
