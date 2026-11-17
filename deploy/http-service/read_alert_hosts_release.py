"""Read-only E71 release verification using existing records and original sources."""
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();cfg=json.loads(a.profile.read_text());a.output.mkdir(parents=True,exist_ok=False)
secret=json.loads((ROOT/cfg['credential']['file']).read_text())
if cfg['credential']['kind']=='existing_login':
 request=urllib.request.Request(cfg['credential']['login_url'],data=json.dumps({k:secret[k] for k in ('email','password')}).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(request,timeout=cfg['timeout_seconds']) as r:token=json.load(r)['access_token']
else:token=secret['api_key']
receipts=[]
def get(path):
 request=urllib.request.Request(cfg['base_url']+path,headers={'Authorization':'Bearer '+token})
 with urllib.request.urlopen(request,timeout=cfg['timeout_seconds']) as r:body=json.load(r);status=r.status
 receipts.append({'method':'GET','path':path,'status':status,'body':body})
 (a.output/'responses.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
 return body
contract=get('/openapi.json');assert contract['info']['version']==cfg['release']
assert sum(len(v) for k,v in contract['paths'].items() if k.startswith('/api/v1/socai2'))==cfg['expected_operations']
identity=cfg.get('alert_id')
if not identity:
 case=get('/api/v1/socai2/cases/'+cfg['case_id'])
 member=sorted([m for m in case['members'] if m['event_time']],key=lambda m:(m['event_time'],m['alert_id']),reverse=True)[0]
 identity=member['alert_id']
path='/api/v1/socai2/alerts/'+identity;before=get(path)
page=get(path+'/same-host-alerts');assert page['source_material_id']==before['facts']['latest_material_id']
assert page['source_alert_id']==identity and page['limit']==7 and len(page['items'])<=7
if page['items']:
 item=page['items'][0];assert get('/api/v1/socai2/alerts/'+item['alert']['id'])['facts']==item['alert']
 for ref in [item['matches'][0]['seed'],item['matches'][0]['candidate']]:
  material=get('/api/v1/socai2/alerts/'+ref['alert_id']+'/materials/'+ref['material_id'])
  assert ref['raw_value'] in json.dumps(material,ensure_ascii=False)
assert get(path)['facts']==before['facts']
result={'passed':True,'release':cfg['release'],'operations':cfg['expected_operations'],'database_expected':cfg['database'],'source_alert_id':identity,'http_gets':len(receipts),'candidate_total':page['total'],'returned':len(page['items']),'source_hosts':len(page['source_hosts']),'writes':0,'models':0,'source_alert_unchanged':True}
(a.output/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
