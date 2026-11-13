"""Six explicit single/batch operations over HTTP on a new synthetic fixture."""
import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();cfg=json.loads(args.profile.read_text())
    root=Path(__file__).resolve().parents[2]
    fixture=json.loads((root/cfg['fixture']).read_text())
    assert fixture['database']==cfg['database']
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    credentials=json.loads((root/cfg['credential']['file']).read_text())
    if cfg['credential']['kind']=='existing_login':
        req=urllib.request.Request(cfg['credential']['login_url'],method='POST',
            data=json.dumps({k:credentials[k] for k in ['email','password']}).encode(),
            headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=cfg['timeout_seconds']) as response:
            token=json.load(response)['access_token']
    else:token=credentials['api_key']
    receipts=[]
    prefix='/api/v1/socai2'

    def request(method,path,body=None,code=200):
        (out/f'{len(receipts)+1:02}-intent.json').write_text(json.dumps(
            {'method':method,'path':path,'input':body},ensure_ascii=False,indent=2)+'\n')
        req=urllib.request.Request(cfg['base_url']+prefix+path,method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=cfg['timeout_seconds']) as response:
                status,data=response.status,json.load(response)
        except urllib.error.HTTPError as error:
            status,data=error.code,json.load(error)
        receipts.append({'method':method,'path':prefix+path,'status':status,'body':data})
        (out/'responses.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
        assert status==code,(path,status,data)
        return data

    def get(kind,identity):return request('GET',f'/{kind}/{identity}')
    def single(kind,identity,suffix,fields):
        version=get(kind,identity)['facts']['row_version']
        body={'operation_key':str(uuid4()),'expected_row_version':version,**fields}
        response=request('POST' if suffix=='feedback' else 'PATCH',f'/{kind}/{identity}/{suffix}',body)
        assert get(kind,identity)['facts']==response['facts']
        return response,body
    def batch(kind,ids,suffix,fields):
        items=[{'id':identity,'expected_row_version':get(kind,identity)['facts']['row_version']} for identity in ids]
        key='feedback' if suffix=='feedback-batch' else 'changes'
        body={'operation_key':str(uuid4()),'items':items,key:fields}
        response=request('POST',f'/{kind}/{suffix}',body)
        for item in response['items']:assert get(kind,item['facts']['id'])['facts']==item['facts']
        return response,body

    alerts,incidents=fixture['alerts'],fixture['incidents'];actor=fixture['actor_id']
    initial={kind:[get(kind,x) for x in ids] for kind,ids in [('alerts',alerts),('incidents',incidents)]}
    case=request('POST','/cases',{'operation_key':str(uuid4()),'title':'SYNTHETIC manual management '+fixture['batch'],
                                 'alert_ids':alerts[:2]})
    cid=case['case_id']
    closed,body=single('alerts',alerts[0],'feedback',{'disposition':'false_positive','reason':'SYNTHETIC confirmed false positive'})
    assert closed['facts']['handling_status']=='completed' and closed['facts']['closed_by']==actor
    current=get('alerts',alerts[0]);assert current['feedback']['rationale']==body['reason']
    assert current['feedback']['input_material_id']==initial['alerts'][0]['facts']['latest_material_id']
    assert request('POST',f'/alerts/{alerts[0]}/feedback',body)==closed
    request('POST',f'/alerts/{alerts[0]}/feedback',{**body,'reason':'different intent'},409)
    reopened,body=batch('alerts',alerts[:2],'feedback-batch',{'disposition':'true_positive','reason':'SYNTHETIC further verification'})
    outcomes={item['facts']['id']:item for item in reopened['items']}
    assert outcomes[alerts[0]]['facts']['handling_status']=='in_progress'
    assert outcomes[alerts[0]]['facts']['closed_at'] is None and outcomes[alerts[0]]['facts']['reopened_at']
    assert outcomes[alerts[1]]['facts']['handling_status']=='new'
    assert request('POST','/alerts/feedback-batch',body)==reopened
    # Explicit close keeps the human verdict; assignment does not reopen or advance an alert.
    closed,_=single('alerts',alerts[0],'management',{'handling_status':'completed','reason':'SYNTHETIC manual closure','tags':['synthetic','reviewed']})
    assert closed['facts']['disposition']=='true_positive'
    assigned,body=batch('alerts',alerts[:2],'management-batch',{'owner_id':actor,'tags':['synthetic','assigned']})
    assert request('POST','/alerts/management-batch',body)==assigned
    states={item['facts']['id']:item['facts']['handling_status'] for item in assigned['items']}
    assert states=={alerts[0]:'completed',alerts[1]:'new'}
    cleared,_=single('alerts',alerts[0],'management',{'owner_id':None,'tags':[]})
    assert cleared['facts']['assignment_state']=='unassigned' and cleared['facts']['assigned_at'] is None
    before=[get('alerts',aid) for aid in alerts[:2]]
    versions=[{'id':a['facts']['id'],'expected_row_version':a['facts']['row_version']} for a in before]
    stale=[dict(v) for v in versions];stale[1]['expected_row_version']-=1
    request('POST','/alerts/management-batch',{'operation_key':str(uuid4()),'items':stale,'changes':{'tags':['should-not-save']}},409)
    assert [get('alerts',aid) for aid in alerts[:2]]==before
    request('POST','/alerts/feedback-batch',{'operation_key':str(uuid4()),'items':stale,
            'feedback':{'disposition':'benign','reason':'should-not-save'}},409)
    assert [get('alerts',aid) for aid in alerts[:2]]==before
    request('PATCH',f'/alerts/{alerts[1]}/management',{'operation_key':str(uuid4()),
            'expected_row_version':versions[1]['expected_row_version'],'handling_status':'completed'},422)
    request('POST','/alerts/management-batch',{'operation_key':str(uuid4()),'items':versions,
            'changes':{'owner_id':str(uuid4())}},422)
    request('POST','/alerts/management-batch',{'operation_key':str(uuid4()),'items':[versions[0],versions[0]],
            'changes':{'tags':[]}},422)
    request('POST',f'/alerts/{uuid4()}/feedback',{'operation_key':str(uuid4()),'expected_row_version':1,
            'disposition':'needs_review','reason':'SYNTHETIC missing subject'},404)
    assigned,_=single('incidents',incidents[0],'management',{'owner_id':actor,'severity_override':'high',
            'severity_override_reason':'SYNTHETIC manual severity'})
    assert assigned['facts']['handling_status']=='in_progress'
    assert get('incidents',incidents[0])['derived']['severity_effective']=='high'
    resolved,_=single('incidents',incidents[0],'management',{'handling_status':'resolved','resolution_note':'SYNTHETIC resolution'})
    assert resolved['facts']['resolved_by']==actor
    reassigned,_=single('incidents',incidents[0],'management',{'owner_id':None})
    assert reassigned['facts']['handling_status']=='resolved'
    opened,_=single('incidents',incidents[0],'management',{'handling_status':'in_progress','severity_override':None})
    assert opened['facts']['resolved_at'] is None and opened['facts']['resolution_note'] is None
    assert opened['facts']['severity_override_reason'] is None
    assert get('incidents',incidents[0])['derived']['severity_effective']=='medium'
    assigned,body=batch('incidents',incidents[:2],'management-batch',{'owner_id':actor,'severity_override':'critical',
            'severity_override_reason':'SYNTHETIC batch severity','tags':['synthetic','batch-managed']})
    assert all(item['facts']['handling_status']=='in_progress' for item in assigned['items'])
    assert request('POST','/incidents/management-batch',body)==assigned
    # A same-value new intent records a receipt without increasing the subject version.
    noop,_=single('incidents',incidents[0],'management',{'severity_override':'critical',
            'severity_override_reason':'SYNTHETIC batch severity'})
    assert not noop['changed']
    resolved,_=batch('incidents',incidents[:2],'management-batch',{'handling_status':'resolved','resolution_note':'SYNTHETIC batch resolution'})
    assert all(item['facts']['handling_status']=='resolved' for item in resolved['items'])
    activity_ids={closed['activity_id'],reopened['items'][0]['activity_id']}
    for kind,ids in [('alerts',alerts),('incidents',incidents)]:
        for index,identity in enumerate(ids):
            value=get(kind,identity)
            if index==2:assert value==initial[kind][index]
            if kind=='alerts':
                assert value['facts']['latest_triage_id']==fixture['triage_ids'][index]
                assert value['facts']['severity']=='medium'
            activities=request('GET',f'/{kind}/{identity}/records/activities')
            if index<2:assert activities['total']>0
    activities=request('GET',f'/cases/{cid}/activities')
    assert activity_ids <= {item['id'] for item in activities['items']}
    caseview=request('GET',f'/cases/{cid}');assert caseview['case']['handling_status']=='new'
    run=request('GET',f'/cases/{cid}/runs/{case["pending_run_id"]}')
    assert run['run']['state']=='pending_update' and run['run']['started_at'] is None
    result={'state':'passed','requests':len(receipts),'case_id':cid,'fixture_batch':fixture['batch'],
        'database_expected':cfg['database'],'transport':'TCP HTTP','single_and_batch_operations':6,
        'atomic_conflict_checks':True,'original_triage_preserved':True,'unselected_unchanged':True,'real_model_calls':0}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
