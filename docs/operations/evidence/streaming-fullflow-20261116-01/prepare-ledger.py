"""Prepare this completed live batch's public records from actual saved identities."""
import hashlib,json,shutil,sys
from pathlib import Path
from datetime import datetime,timezone
root=Path(__file__).resolve().parent
def read(name):return json.loads((root/name).read_text())
p=read('batch/profile.json');viewer=read('viewer-publication.json');snap=read('final-pg.json');rows=snap['rows']
saved=read('saved-validation.json');http=read('http-readback-final/validation.json');models=read('model-summary-final.json')
assert http['status']=='passed' and saved['snapshot_sha256']==http['snapshot_sha256']
out=root/'viewer-input';out.mkdir();now=datetime.now(timezone.utc).isoformat()
whole=read('http-create-whole.json')['response']['body']['primary_case_id'];single=read('http-create-single.json')['response']['body']['primary_case_id']
first_runs={r['id'] for r in read('first-pg.json')['rows']['runs']}
evidence=[]
for identity,path,label in [('saved-checks','saved-validation.json','数据库保存与前后轮核对'),('http-checks','http-readback-final/validation.json','同一快照HTTP读回核对'),('model-checks','model-summary-final.json','实际模型用量、结束状态及引用检查'),('input-residuals','input-residual-review-final.json','16次实际模型输入的后台字段残留记录')]:
    name=identity+'.json';shutil.copyfile(root/path,out/name)
    evidence.append(dict(id=identity,path=name,label=label,mime_type='application/json',visibility='public',source_ref=str(root.relative_to(Path.cwd())/path)))
testcases={key:dict(id=key,use_case_id=key,scenario_id=scene,status='passed',expected=expected,actual=[],operation_ids=[],evidence_ids=['saved-checks','http-checks']) for key,scene,expected in [
    ('whole_initial','S01',['三条告警归入同一事件；整案首轮运行C1–C6并保存结果。']),
    ('single_initial','S01',['单告警案完成首轮并保持固定成员。']),
    ('incremental','S04',['追加告警进入原事件；显式检查新诊断和整案后轮，冻结4成员。']),
    ('no_changes','S04',['第二次显式检查无变化时跳过，不新增Run或模型调用。'])]}
ops=[];run_case={}
for i,run in enumerate(sorted(rows['runs'],key=lambda x:x['started_at'])):
    case_key='single_initial' if run['case_id']==single else 'whole_initial' if run['id'] in first_runs else 'incremental'
    run_case[run['id']]=case_key
    subject='case' if run['case_id'] else 'incident' if run['incident_id'] else 'alert';sid=run[subject+'_id']
    attempt=next(a for a in rows['analysis_attempts'] if a['run_id']==run['id'])
    table={'case':'results','incident':'incident_diagnoses','alert':'alert_assessments'}[subject]
    result=next((x for x in rows[table] if x['source_run_id']==run['id']),None)
    mapping={'subject_type':subject,'subject_id':sid,'task_id':attempt['task_id'],'run_id':run['id']}
    if result:mapping.update(result_type={'case':'case_result','incident':'incident_diagnosis','alert':'alert_assessment'}[subject],result_id=result['id'])
    identity='run_'+str(i+1).zfill(2)
    ops.append(dict(id=identity,case_id=case_key,intent={'case':'Case完整调查','incident':'事件诊断','alert':'告警分诊'}[subject],execution_state=run['state'],occurred_at=run['started_at'],mappings=[mapping],evidence_ids=['saved-checks','http-checks','model-checks','http-exchanges']))
    testcases[case_key]['operation_ids'].append(identity)
    testcases[case_key]['actual'].append(f"{ops[-1]['intent']}：{run['state']}，交付={run['delivery_state']}，Run={run['id']}")
    if any(s['run_id']==run['id'] and s['state']=='failed' for s in rows['run_steps']):testcases[case_key]['status']='failed'
taskid=read('http-check-whole.json')['response']['body']['task_id'];task=next(x for x in rows['analysis_tasks'] if x['id']==taskid)
ops.append(dict(id='no_change_check',case_id='no_changes',intent='后轮完成后检查是否仍有新变化',execution_state=task['state'],occurred_at=task['submitted_at'],mappings=[dict(subject_type='case',subject_id=whole,task_id=taskid)],evidence_ids=['saved-checks','http-checks','http-exchanges']))
testcases['no_changes']['operation_ids']=['no_change_check'];testcases['no_changes']['actual']=['实际skipped/no_changes；无attempt、Run和模型调用。']
issues=[]
for rid,key in run_case.items():
    review=[x for x in models['review_records'] if x['run_id']==rid]
    failed=[x for x in rows['run_steps'] if x['run_id']==rid and x['state']=='failed']
    for stage,category,description,affects in ([('模型输出','citation_review',f'保存了{len(review)}条引用检查记录（包含诊断记录）；原文和来源在模型回执中，正文尚未全面验收。',False)] if review else [])+[(s['stage_code'],'validation_failure',s['error']['code'],True) for s in failed]:
        issues.append(dict(id='issue_'+str(len(issues)+1),case_id=key,run_id=rid,stage=stage,category=category,description=description,status='open' if affects else 'deferred',affects_flow=affects,evidence_ids=['model-checks']))
    ms=[m for m in models['models'] if m['run_id']==rid]
    if any(m['input_observations'].get('tenant_uid') for m in ms):
        issues.append(dict(id='issue_'+str(len(issues)+1),case_id=key,run_id=rid,stage='模型输入',category='backend_metadata',description='实际输入仍包含不必要的tenant_uid后台字段；固定中性告警源及测试标记未见于本批模型输入，整体输入边界仍未通过。',status='open',affects_flow=False,evidence_ids=['model-checks','input-residuals']))
exchanges=[]
for phase in ('create-whole','create-single','check-incident','check-whole-update','check-whole'):
    x=read('http-'+phase+'.json');b=x['response']['body']
    tid=b['allocations'][0]['initial_task']['task_id'] if phase.startswith('create-') else b['task_id']
    task=next(t for t in rows['analysis_tasks'] if t['id']==tid);a=next((a for a in rows['analysis_attempts'] if a['task_id']==tid),None)
    exchanges.append(dict(subject_type=task['subject_type'],subject_id=task['subject_id'],task_id=tid,run_id=a['run_id'] if a else None,**x,sources=[dict(path=str(root.relative_to(Path.cwd())/('http-'+phase+'.json')),sha256=hashlib.sha256((root/('http-'+phase+'.json')).read_bytes()).hexdigest())]))
(out/'http-exchanges.json').write_text(json.dumps({'schema':'socai2.test-http-exchanges.v1','exchanges':exchanges},ensure_ascii=False,indent=2)+'\n')
evidence.append(dict(id='http-exchanges',path='http-exchanges.json',label='真实HTTP请求与201/202回执',mime_type='application/json',visibility='public'))
cases=list(testcases.values())
for key,desc in [('periodic_due','正式I4小时、Case6小时周期尚未到，本批用显式HTTP check，未覆盖到时自动触发。'),('eligible_comparison','整案首轮C6拒收；后轮正确保留上一Run并标记结论不可用，未覆盖有效结论比较。')]:
    cases.append(dict(id=key,use_case_id=key,scenario_id='coverage',status='not_covered',expected=[desc],actual=[desc],operation_ids=[],evidence_ids=['saved-checks']))
document=dict(schema_version=1,batch=dict(id=p['batch_id'],environment=viewer['environment_label'],title='登录、进程与外联：首轮及增量调查',scenario_version='streaming-v2',execution_state='finished',mode='live',provenance='live_execution',started_at=min(r['started_at'] for r in rows['runs']),updated_at=now,quality_status='issues_recorded'),cases=cases,operations=ops,preparation=dict(status='prepared',cleanup_mode='no_cleanup',summary='21正式aisoc；独立新批4告警/13上下文。先读回上下文再投告警是本批发送顺序。I与Case后轮由显式HTTP检查触发；运行代码r3，HTTP/4177沿现环境标签。',resources=['真实Kafka','真实ClickHouse','真实PostgreSQL','Qwen3.5-9B经现有网关'],observed_at=now,evidence_ids=['saved-checks']),quality_issues=issues,evidence=evidence)
(out/'document.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n')
sys.path.insert(0,str(Path.cwd()/'services'))
from investigation_test.models import Document
Document.model_validate_json((out/'document.json').read_bytes())
print(json.dumps({'status':'validated_not_published','cases':len(cases),'operations':len(ops),'quality_issues':len(issues),'http_exchanges':len(exchanges)},ensure_ascii=False))
