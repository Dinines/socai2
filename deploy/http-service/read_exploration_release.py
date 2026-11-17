"""Read-only release verification using existing Case data and source references."""
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--profile',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
a=parser.parse_args();cfg=json.loads(a.profile.read_text());a.output.mkdir(parents=True,exist_ok=False)
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
 (a.output/'responses.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
 return body
contract=get('/openapi.json');assert contract['info']['version']==cfg['release']
assert sum(len(v) for p,v in contract['paths'].items() if p.startswith('/api/v1/socai2'))==cfg['expected_operations']
path='/api/v1/socai2/cases/'+cfg['case_id'];case=get(path)
page=get(path+'/exploration-candidates?limit=1')
member=next((m for m in case['members'] if m['event_time']),None)
selected=None
if member:
 params={'alert_id':member['alert_id'],'limit':1}
 selected=get(path+'/exploration-candidates?'+urllib.parse.urlencode(params))
 if selected['next_cursor']:
  next_page=get(path+'/exploration-candidates?'+urllib.parse.urlencode({**params,'cursor':selected['next_cursor']}))
  assert not ({x['alert']['id'] for x in selected['items']} & {x['alert']['id'] for x in next_page['items']})
visible=selected if selected and selected['items'] else page
if visible['items']:
 row=visible['items'][0]
 assert get('/api/v1/socai2/alerts/'+row['alert']['id'])['facts']==row['alert']
 for ref in [row['matches'][0]['seed'],row['matches'][0]['candidate']]:
  objects=get('/api/v1/socai2/alerts/'+ref['alert_id']+'/records/objects?limit=100')
  actual=next(x for x in objects['items'] if x['id']==ref['id'])
  for k in ['alert_id','material_id','object_type','namespace','object_key','raw_value','normalized_value','source_path']:assert actual[k]==ref[k],k
  material=get('/api/v1/socai2/alerts/'+ref['alert_id']+'/materials/'+ref['material_id'])
  assert ref['raw_value'] in json.dumps(material,ensure_ascii=False)
assert get(path)['case']==case['case']
result={'passed':True,'release':cfg['release'],'database_expected':cfg['database'],'case_id':cfg['case_id'],'http_gets':len(receipts),'whole_case_total':page['total'],'selected_alert_total':selected['total'] if selected else None,'writes':0,'models':0,'case_unchanged':True}
(a.output/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
