"""One explicit HTTP Case/H acceptance, no Run start or model call.

Requests are not retried. Each intent and receipt is saved before the next step.
The caller supplies an existing credential or a synthetic local JWT configuration.
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from uuid import uuid4


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();cfg=json.loads(args.profile.read_text());root=Path(__file__).resolve().parents[2]
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    if cfg['credential']['kind']=='synthetic_local_jwt':
        os.environ.update(json.loads((root/cfg['credential']['environment']).read_text()))
        sys.path.insert(0,str(root/'services/api'))
        from app.core.security import create_access_token
        token=create_access_token({'sub':cfg['credential']['user_id']})
    else:
        credentials=json.loads((root/cfg['credential']['file']).read_text())
        if cfg['credential']['kind']=='existing_login':
            login=urllib.request.Request(cfg['credential']['login_url'],method='POST',
                data=json.dumps({k:credentials[k] for k in ['email','password']}).encode(),
                headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(login,timeout=cfg['timeout_seconds']) as r:
                token=json.load(r)['access_token']
        else:
            token=credentials['api_key']
    responses=[]

    def request(method,path,body=None,*,code=200,save=True):
        if save:
            intent={'method':method,'path':path,'input':body}
            (out/f'{len(responses)+1:02}-intent.json').write_text(json.dumps(intent,ensure_ascii=False,indent=2)+'\n')
        req=urllib.request.Request(cfg['base_url']+path,method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=cfg['timeout_seconds']) as r:
                status=r.status;data=json.load(r)
        except urllib.error.HTTPError as e:
            status=e.code;data=json.load(e)
        if save:
            responses.append({'method':method,'path':path,'status':status,'body':data})
            (out/'responses.json').write_text(json.dumps(responses,ensure_ascii=False,indent=2)+'\n')
        assert status==code,(status,data)
        return data

    prefix='/api/v1/socai2'
    if cfg.get('source_case_id'):
        source=request('GET',prefix+'/cases/'+cfg['source_case_id'],save=False)
        alert=source['members'][0]['alert_id']
    else:alert=cfg['source_alert_id']
    created=request('POST',prefix+'/cases',{'operation_key':str(uuid4()),'title':cfg['title'],'alert_ids':[alert]})
    case_id=created['case_id'];path=prefix+'/cases/'+case_id
    case=request('GET',path)
    assert case['member_count']==1 and case['case']['scope_revision']==1
    task=(request('POST',path+'/tasks',{'operation_key':str(uuid4()),'expected_scope_revision':1,
        'title':'核对调查资料（接口验收）','description':'本批只验证HTTP保存读取，不表示完成真实安全调查。'}))['task']
    original_revision=task['current_revision_id']
    edit={'operation_key':str(uuid4()),'expected_scope_revision':1,'expected_row_version':task['row_version'],
        'title':task['current']['title'],'description':task['current']['description'],'state':'completed',
        'result_text':'本批HTTP验收：资料引用可以读取；未核实业务授权，不形成安全判断。',
        'result_scope':{'kind':'whole_case','alert_ids':[alert],'object_keys':[],
            'window_start':None,'window_end':None,'limitations':['接口保存读回验收，非真实调查结论']},'source_refs':[]}
    endpoint=path+'/tasks/'+task['id']
    receipt=request('PUT',endpoint,edit)
    current=request('GET',endpoint)
    assert current==receipt['task'] and current['current']['revision']==2
    assert current['current']['result_text']==edit['result_text'] and current['current']['result_scope']==edit['result_scope']
    assert request('GET',endpoint+'/revisions/'+original_revision)['result_text'] is None
    assert request('GET',endpoint+'/revisions')['total']==2
    run=request('GET',path+'/runs/'+created['pending_run_id'])
    assert run['run']['state']=='pending_update' and run['run']['started_at'] is None
    reserved=request('POST',path+'/ai/messages',{'operation_key':str(uuid4()),'question':'接口验收占位请求'},code=501)
    assert reserved['detail']['code']=='case_ai_not_implemented'
    result={'state':'passed','case_id':case_id,'run_id':created['pending_run_id'],'task_id':task['id'],
        'current_revision_id':current['current_revision_id'],'requests':len(responses),'real_model_calls':0,
        'transport':'TCP HTTP','authentication':cfg['credential']['kind'],'database_expected':cfg['database'],
        'service_dependency_overrides':False,'run_started':False}
    (out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
