"""Bounded1G HTTP/PG acceptance. Run in API image on socai2 network.

Only one investigation launch is allowed. Verification after restart reads
retained IDs; it never submits again. All test identities remain private.
"""
import argparse,asyncio,hashlib,json,os,time,uuid
from datetime import datetime,timezone
from pathlib import Path
import asyncpg,httpx
E=Path('/evidence');BATCH='1g-20261020'
state=json.loads(Path('/private/app-1g.json').read_text());ids=state['identities']

def save(name,value):
 with (E/name).open('x') as f:json.dump(value,f,indent=2,default=str);f.write('\n')

def auth(name='a',api=False):return {'Authorization':'Bearer '+ids[name]['key' if api else 'jwt']}

async def main(action):
 db=await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://','postgresql://'))
 try:
  async with httpx.AsyncClient(timeout=25,trust_env=False) as http:
   checks=[]
   async def req(method,url,headers=None,body=None,status=200):
    response=await http.request(method,url,headers=headers,json=body)
    checks.append({'method':method,'url':url,'status':response.status_code,'expected':status})
    if response.status_code!=status:
     save('failed-http-'+uuid.uuid4().hex+'.json',{'checks':checks,'body_sha256':hashlib.sha256(response.content).hexdigest()})
     raise RuntimeError('Unexpected HTTP status')
    return response
   if action=='actions':
    await req('GET','http://actions:8085/api/v1/live-actions',status=401)
    await req('GET','http://actions:8085/api/v1/live-actions',{'Authorization':'Bearer invalid'},status=401)
    header={'Authorization':'Bearer '+state['actions_token']}
    discovered=(await req('GET','http://actions:8085/api/v1/live-actions',header)).json()
    for path in ['/api/v1/live-actions/dispatch','/api/v1/actions','/api/v1/actions/test/approve']:
     await req('POST','http://actions:8085'+path,header,{},404)
    body={'request_id':str(uuid.uuid4()),'capability':'isolate_host','vendor_id':'crowdstrike','target':'socai2-1g-test-host','tenant_id':ids['a']['tenant_id'],'case_id':ids['a']['case_id'],'dry_run':False,'params':{'cs_client_id':'test-sentinel','cs_client_secret':'test-sentinel','cs_base_url':'http://127.0.0.1:9'}}
    response=(await req('POST','http://actions:8085/api/v1/live-actions/dry-run',header,body)).json()
    assert response['mode']=='dry_run' and response['result']['status']=='simulated',response
    save('actions-http.json',{'checks':checks,'builtin_descriptor_count':len(discovered['executors']),'input':body,'result':response,'note':'Dry-run endpoint forces true; original adapter strips credentials. Network interception unit tests separate.'})
    print(json.dumps({'actions_http_checks':len(checks),'result':response['result']['status']}));return
   if action in ('run','resume'):
    if action=='run':
     assert not (E/'launched.json').exists() and not (E/'alert-accepted.json').exists(),'Do not repeat launches'
     original={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,BATCH+'/existing-alert')),'source':'socai2-migration-edr','title':'socai2 1g marked suspicious PowerShell finding','description':'Synthetic existing alert about PowerShell execution with reserved benchmark IOC 198.18.0.1; no evidence of compromise or vendor access.','severity':'medium','hostname':'socai2-1g-test-host','src_ip':'198.18.0.1','mitre_techniques':['T1059'],'event_time':datetime.now(timezone.utc).isoformat(),'source_event_ids':[BATCH+'-source'],'external_id':BATCH+'-finding','connector_type':'migration-test','tags':[BATCH],'raw_event':{'batch':BATCH,'synthetic':True,'ioc':'198.18.0.1'}}
     accepted=(await req('POST','http://api:8000/api/v1/alert-ingress',auth(api=True),original,202)).json()
     save('alert-accepted.json',{'input':original,'accepted':accepted})
     for _ in range(40):
      response=await http.get('http://api:8000'+accepted['result_url'],headers=auth(api=True))
      if response.status_code==200:break
      await asyncio.sleep(.5)
     else:raise RuntimeError('Marked alert not visible')
     detail=response.json();canonical=accepted['canonical_alert_id'];assert detail['id']==canonical
     await db.execute('UPDATE aisoc_cases SET alert_ids=ARRAY[$1::uuid] WHERE id=$2 AND tenant_id=$3',uuid.UUID(canonical),uuid.UUID(ids['a']['case_id']),uuid.UUID(ids['a']['tenant_id']))
     save('case-alert.json',{'case_id':ids['a']['case_id'],'tenant_id':ids['a']['tenant_id'],'canonical_alert_id':canonical,'api_detail':detail})
    else:
     assert not (E/'launched.json').exists(),'Do not repeat launch'
     original=json.loads((E/'alert-accepted.json').read_text())['input']
     detail=json.loads((E/'case-alert.json').read_text())['api_detail']
    body={'tenant_id':ids['a']['tenant_id'],'alert_summary':original['title']+'. '+original['description'],'raw_alert':{**detail,'batch':BATCH}}
    base='http://agents:8084/api/v1/cases/'
    await req('POST',base+ids['a']['case_id']+'/investigate',body=body,status=401)
    await req('POST',base+ids['a']['case_id']+'/investigate',auth('b'),body,403)
    await req('POST',base+ids['b']['case_id']+'/investigate',auth(),body,404)
    for path in ['/api/v1/agent-runs','/api/v1/hunts','/api/v1/playbooks/runs']:
     await req('POST','http://agents:8084'+path,auth(),{},404)
    launched=(await req('POST',base+ids['a']['case_id']+'/investigate',auth(),body)).json()
    save('launched.json',{'input':body,'launch':launched,'checks_before_and_at_launch':checks})
   launch=json.loads((E/'launched.json').read_text())['launch'];run_id=launch['run_id']
   if action in ('run','resume'):
    for _ in range(180):
     response=await http.get('http://agents:8084/api/v1/investigations/'+run_id,headers=auth())
     response.raise_for_status();run=response.json()
     if run['status'] in ['completed','failed']:break
     await asyncio.sleep(1)
    else:raise RuntimeError('Investigation remained nonterminal')
    # Persist response before asserting completion. Do not relaunch failed/unknown work.
    save('run-terminal.json',{'run':run})
    assert run['status']=='completed',run.get('error')
    for suffix in ['', '/report.md','/report.html']:
     await req('GET','http://agents:8084/api/v1/investigations/'+run_id+suffix,auth('b'),status=404)
    report=await req('GET','http://agents:8084/api/v1/investigations/'+run_id+'/report.md',auth())
    save('report-cache.json',{'sha256':hashlib.sha256(report.content).hexdigest(),'size':len(report.content)})
   durable=(await req('GET','http://api:8000/api/v1/investigations/'+run_id,auth(api=True))).json()
   await req('GET','http://api:8000/api/v1/investigations/'+run_id,auth('b',api=True),status=404)
   await req('GET','http://api:8000/api/v1/cases/'+ids['a']['case_id'],auth(api=True))
   artifacts=(await req('GET','http://api:8000/api/v1/investigations/'+run_id+'/artifacts',auth(api=True))).json()
   reports=[a for a in artifacts if a['kind']=='report_md'];assert len(reports)==1,artifacts
   artifact=(await req('GET','http://api:8000/api/v1/investigations/'+run_id+'/artifacts/'+reports[0]['id'],auth(api=True))).json()
   assert reports[0]['sha256']==json.loads((E/'report-cache.json').read_text())['sha256']
   row=await db.fetchrow('SELECT id,tenant_id,case_id,status,total_tokens,measured_call_count,unpriced_call_count,total_cost_usd FROM investigation_runs WHERE id=$1',uuid.UUID(run_id))
   events=await db.fetch('SELECT seq,kind,agent,summary,payload FROM investigation_events WHERE run_id=$1 ORDER BY seq',uuid.UUID(run_id))
   assert row and row['status']=='completed' and str(row['tenant_id'])==ids['a']['tenant_id'] and row['case_id']==ids['a']['case_id']
   assert [x['seq'] for x in events]==list(range(len(events)))
   llm=[e for e in events if e['kind']=='llm_response'];tools=[e for e in events if e['kind']=='tool_call']
   assert len(llm)==4 and tools,'Require actual model and read-only tool records'
   data={'checks':checks,'run_id':run_id,'durable_api_run':durable,'pg_run':dict(row),'event_counts':{kind:sum(e['kind']==kind for e in events) for kind in sorted({e['kind'] for e in events})},'events':[dict(e) for e in events],'report_artifact':artifact,'report_metadata':reports[0],'cost_semantics':'DB defaultzero is not measured cost when measured_call_count0; inspect actual cost provenance','realtime_service_absent':True,'actual_enrichment_dependency':'deliberately unconnected; recorded partial/error, no real vendor query'}
   save('durable-'+('run' if action=='resume' else action)+'.json',data)
   print(json.dumps({'action':action,'run_id':run_id,'status':row['status'],'events':len(events),'llm_responses':len(llm),'tool_calls':len(tools),'tokens':row['total_tokens']}))
 finally:await db.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['actions','run','resume','verify']);a=p.parse_args()
 try:asyncio.run(main(a.action))
 except Exception as exc:print(json.dumps({'success':False,'error_type':type(exc).__name__,'action':a.action,'instruction':'Inspect retained records; do not replay successful/unknown requests'}));raise SystemExit(1)
