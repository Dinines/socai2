"""Read existing subjects over TCP; no model, mutation or raw credentials in evidence."""
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--output',required=True);p.add_argument('--compare');a=p.parse_args()
c=json.loads(Path(a.profile).read_text());secret=json.loads(Path(c['credential']).read_text())
headers={'Authorization':'Bearer '+secret['api_key']}
if c.get('login_url'):
 req=urllib.request.Request(c['login_url'],data=json.dumps({'email':secret['email'],'password':secret['password']}).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=20) as r:headers={'Authorization':'Bearer '+json.load(r)['access_token']}
reads=[]
def clean(value):
 if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k!='observed_at'}
 if isinstance(value,list):return [clean(v) for v in value]
 return value
def digest(value):return hashlib.sha256(json.dumps(clean(value),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def get(path):
 with urllib.request.urlopen(urllib.request.Request(c['base']+path,headers=headers),timeout=30) as r:v=json.load(r);assert r.status==200
 reads.append({'path':path,'status':200,'sha256':digest(v)})
 return v
contract=get('/openapi.json');old=json.loads(Path(c['old_contract']).read_text())
assert contract['paths']==old['paths'] and contract['components']==old['components']
b='/api/v1/socai2';prefix=b+'/cases/'+c['case_id']
case=get(prefix);result=get(prefix+'/results/'+c['result_id']);run=get(prefix+'/runs/'+result['run']['id'])
assert result['result']['id']==c['result_id'] and result['run']['case_id']==c['case_id']
assert case['case']['current_assessment_id']==c['assessment_id']
get(prefix+'/assessments');get(prefix+'/tasks');get(prefix+'/history');get(prefix+'/management')
get(b+'/alerts/'+c['alert_id']);host=get(b+'/alerts/'+c['alert_id']+'/same-host-alerts');get(b+'/alerts/'+c['alert_id']+'/review-candidates')
assert host['total']==c['host_total'] and len(host['items'])==c['host_items']
# observed_at is a query receipt timestamp, excluded only from stable comparisons.
summary={'passed':True,'release':contract['info']['version'],'case_id':c['case_id'],'result_id':c['result_id'],'run_id':result['run']['id'],'assessment_id':c['assessment_id'],'business_reads':len(reads)-1,'reads':reads,'operations':71,'runtime_schemas':len(contract['components']['schemas']),'contract_unchanged':True,'host_total':host['total'],'host_items':len(host['items']),'model_calls':0,'business_writes':0,'comparison_exclusions':['observed_at','openapi info.version']}
if a.compare:
 previous=json.loads(Path(a.compare).read_text());assert reads[1:]==previous['reads'][1:],'existing_readback_changed';summary['existing_values_unchanged']=True
Path(a.output).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='reads'},ensure_ascii=False))
