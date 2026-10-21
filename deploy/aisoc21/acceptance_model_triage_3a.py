"""Checkpointed actual alert ingress/API readback; never rerun accepted samples."""
import asyncio,hashlib,json,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
import httpx
E=Path('/evidence');B='3a-model-triage-20261020'
def save(n,x):
    with (E/n).open('x') as f:json.dump(x,f,indent=2,default=str)
async def main(mode):
    save(mode+'-started.json',{'at':datetime.now(timezone.utc)})
    ids=json.loads(Path('/private/state.json').read_text())['identities'];checks=[]
    async with httpx.AsyncClient(base_url='http://api:8000',trust_env=False,timeout=25) as c:
      async def req(path,n='a',body=None,status=200):
        r=await c.request('POST' if body else 'GET',path,headers={'Authorization':'Bearer '+ids[n]['key']} if n else {},json=body)
        checks.append({'path':path,'identity':n,'status':r.status_code,'expected':status});(E/(mode+'-http-checks.json')).write_text(json.dumps(checks,indent=2));assert r.status_code==status,(r.status_code,r.text[:150]);return r.json()
      if mode=='setup':
        fixture=json.loads(Path('/fixture.json').read_text());batch=fixture['batch'];blind=fixture.get('blind_input_projection',False);inputs={};alerts={}
        for index,(label,sample) in enumerate(fixture['samples'].items()):
            n=sample['tenant'];body={k:v for k,v in sample.items() if k not in ['tenant','expected']}
            body.update({'id':str(uuid.uuid5(uuid.NAMESPACE_URL,batch+'/sample-'+str(index))),'source':'socai2-'+batch,'source_event_ids':[str(uuid.uuid5(uuid.NAMESPACE_URL,batch+'/event-'+str(index)))],'event_time':datetime.now(timezone.utc).isoformat(),'tags':[batch]})
            body['raw_event']={k:v for k,v in body.get('raw_event',{}).items() if not blind or k=='evidence_summary'}
            if not blind:body['raw_event'].update({'batch':batch,'label':label,'synthetic':True})
            save(label+'-sending.json',body);ack=await req('/api/v1/alert-ingress',n,body,202);save(label+'-ack.json',ack)
            for _ in range(80):
                r=await c.get('/api/v1/alerts/'+ack['canonical_alert_id'],headers={'Authorization':'Bearer '+ids[n]['key']})
                if r.status_code==200:break
                assert r.status_code==404;await asyncio.sleep(.25)
            else:raise AssertionError('Accepted outcome unknown; inspect, do not resubmit')
            alerts[label]=r.json();inputs[label]={'id':ack['canonical_alert_id'],'alert_row_id':ack['canonical_alert_id'],'tenant_id':ids[n]['tenant_id'],'test_label':label,'alert':{**body,'id':ack['canonical_alert_id'],'tenant_id':ids[n]['tenant_id']}}
            save(label+'-stored-alert.json',alerts[label])
        save('setup-acceptance.json',{'inputs':inputs,'alerts':alerts,'checks':checks,'fixture_sha256':hashlib.sha256(Path('/fixture.json').read_bytes()).hexdigest()});return
      old=json.loads((E/'setup-acceptance.json').read_text());observed=json.loads((E/'broker-acceptance.json').read_text());outputs={}
      for label,result in observed['results'].items():
        n='b' if label=='model_failure' else 'a';rid=result['run_id'];base='/api/v1/investigations/'+rid
        detail=await req(base,n);events=await req(base+'/events',n);artifacts=await req(base+'/artifacts',n)
        assert detail['status']=='completed'
        assert any(x['kind']=='triage_verdict' for x in events['items'])
        if label!='model_failure':assert any(x['kind']=='llm_call' for x in events['items']) and len(artifacts)==2
        else:assert not artifacts and not any(x['kind']=='llm_call' for x in events['items'])
        blobs=[]
        for artifact in artifacts:
            blob=await req(base+'/artifacts/'+artifact['id'],n);blobs.append(blob)
        alert=await req('/api/v1/alerts/'+old['inputs'][label]['id'],n)
        for k in ['raw_event','severity','status','disposition','resolved_at','priority']:assert alert.get(k)==old['alerts'][label].get(k),(label,k)
        assert result['shadow'] and not result['response_dispatched'] and not result['approvals_raised'] and result['source_writeback'] is None
        outputs[label]={'run':detail,'events':events,'artifacts':artifacts,'artifact_details':blobs,'alert':alert}
      first=next(iter(observed['results'].values()))['run_id']
      await req('/api/v1/investigations/'+first,'b',status=404)
      await req('/api/v1/investigations/'+first,'denied',status=403)
      await req('/api/v1/investigations/'+first,None,status=401)
      save(mode+'-acceptance.json',{'outputs':outputs,'checks':checks,'manual_alert_state_preserved':True})
if __name__=='__main__':asyncio.run(main(sys.argv[1]))
