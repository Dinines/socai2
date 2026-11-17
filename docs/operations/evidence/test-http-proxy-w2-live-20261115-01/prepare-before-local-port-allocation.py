"""Prepare one explicit live lookup ledger from already executed 21 evidence; no network."""
import hashlib
import json
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'docs/operations/evidence'
def read(path):
    return json.loads(path.read_text())
def save(name, value):
    with (OUT/name).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2);f.write('\n')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

snapshot = EVIDENCE/'test-streaming-s04-20261115-01/analysis-pg-01.json'
s04 = read(EVIDENCE/'test-streaming-s04-20261115-01/actual-analysis-map-01.json')
cases = read(EVIDENCE/'test-streaming-case-initial-20261115-01/actual-case-run-map-01.json')['cases']
rows = read(snapshot)['rows']; artifacts = {v['id']:v for v in rows['artifacts']}; tasks = {v['id']:v for v in rows['analysis_tasks']}
assert sha(snapshot) == s04['snapshot_sha256']
http = []
for batch in ('streaming-s04-http-20261115-01','streaming-case-result-http-20261115-01','streaming-ai-http-20261115-01'):
    http += read(EVIDENCE/batch/'get-01.json')['receipts']
by_task = {v['body']['task_id']:v for v in http if isinstance(v['body'],dict) and 'task_id' in v['body']}
by_path = {urlsplit(v['url']).path:v for v in http}
newdir = OUT/'inputs';newdir.mkdir();(newdir/'evidence').mkdir()
sources = {
    'case_initial':EVIDENCE/'test-streaming-case-initial-20261115-01/acceptance-01.json',
    's04_failure':EVIDENCE/'test-streaming-s04-20261115-01/acceptance-01.json',
    's04_map':EVIDENCE/'test-streaming-s04-20261115-01/actual-analysis-map-01.json',
    's04_quality':EVIDENCE/'test-streaming-s04-20261115-01/quality-findings-01.json',
    'case_quality':EVIDENCE/'test-streaming-case-initial-20261115-01/quality-findings-01.json',
    'runtime':EVIDENCE/'streaming-w2-readonly-20261115-01/runtime-01.json',
}
for key,path in sources.items():
    shutil.copyfile(path,newdir/'evidence'/f'{key}.json')
operations=[]; testcases=[];issues=[]; bindings=[]
for c in cases:
    cid='s01_'+c['label'];opid=cid+'_initial'; task=tasks[c['task_id']]
    operation={'id':opid,'case_id':cid,'intent':'已执行的真实Case首轮；本轮仅live读取','execution_state':'completed','occurred_at':task['submitted_at'],
               'mappings':[{'subject_type':'case','subject_id':c['case_id'],'task_id':c['task_id'],'run_id':c['run_id'],'result_type':'case_result','result_id':c['result_id']}], 'evidence_ids':['case_initial']}
    operations.append(operation)
    testcases.append({'id':cid,'use_case_id':'F05','scenario_id':'S01','status':'passed','expected':['真实Case首轮保存和读回；质量独立记录'],
                      'actual':[f"原首轮completed/accepted/uncertain/partial；实际成员{len(c['member_ids'])}，不因S04失败重跑"], 'operation_ids':[opid],'evidence_ids':['case_initial']})
    issues.append({'id':cid+'_citation','case_id':cid,'run_id':c['run_id'],'stage':'C3/C6','category':'citation_quality','description':'原首轮引用问题保留NOT_PASSED，全文质量未全面验收；本轮仅读取。','status':'deferred','affects_flow':False,'evidence_ids':['case_quality']})
    bindings.append({'operation_id':opid,'task_id':c['task_id'],'task_url':by_task[c['task_id']]['body']['status_url'],'subject_type':'case','subject_id':c['case_id'],'member_count':len(c['member_ids']),'run_id':c['run_id'],'result_id':c['result_id'],'expected_state':'completed','case_url':f"/api/v1/socai2/cases/{c['case_id']}"})
s04_ops=[]
for task in s04['tasks']:
    opid='s04_'+task['id'];s04_ops.append(opid)
    rm=next((v for v in s04['runs'] if v['task_id']==task['id']),None)
    mapping={'subject_type':task['subject_type'],'subject_id':task['subject_id'],'task_id':task['id'],'run_id':rm['run_id'] if rm else None,
             'result_type':('alert_assessment' if task['subject_type']=='alert' else 'incident_diagnosis') if rm else None,'result_id':rm['result_ids'][0] if rm else None}
    operations.append({'id':opid,'case_id':'s04_update','intent':f"原真实{task['source']}/{task['intent']}；本轮仅live读取",'execution_state':task['state'],'occurred_at':task['submitted_at'],'mappings':[mapping],'evidence_ids':['s04_failure','s04_map']})
    bindings.append({'operation_id':opid,'task_id':task['id'],'task_url':by_task[task['id']]['body']['status_url'],'subject_type':task['subject_type'],'subject_id':task['subject_id'],'run_id':mapping['run_id'],'result_id':mapping['result_id'],'expected_state':task['state'],'reason_code':task['reason_code']})
    if rm:
        issues.append({'id':'s04_'+task['subject_type']+'_quality','case_id':'s04_update','run_id':rm['run_id'],'stage':'I' if task['subject_type']=='incident' else 'A','category':'output_truncated' if task['subject_type']=='incident' else 'single_character_rationale','description':'真实I输出length/3000、无可用诊断、阻断Case后轮。' if task['subject_type']=='incident' else '真实A04结构完成，但理由仅单字“告”，质量NOT_PASSED。','status':'deferred','affects_flow':task['subject_type']=='incident','evidence_ids':['s04_quality','s04_failure']})
testcases.append({'id':'s04_update','use_case_id':'F06','scenario_id':'S04','status':'failed','expected':['I先形成可用四成员诊断，再推动活跃Case后轮和自身前轮比较'],
                  'actual':['A04完成，I真实模型length/3000而失败，3check跳过；0新Case任务/Run，成功更新比较未通过'], 'operation_ids':s04_ops,'evidence_ids':['s04_failure','s04_map']})
observed=read(sources['runtime'])['observed_at']; tenant=read(EVIDENCE/'test-streaming-s04-20261115-01/expected.json')['tenant_id']
doc={'schema_version':1,'batch':{'id':'w2-live-s01-s04-20261115-01','environment':'streaming-20261115-01','title':'21真实S01/S04已执行调查：live只读查阅','scenario_version':'streaming-fixture-v1/S01-S04','execution_state':'failed','mode':'live','provenance':'live_execution','started_at':min(o['occurred_at'] for o in operations),'updated_at':observed,'quality_status':'issues_recorded'},'cases':testcases,'operations':operations,'preparation':{'status':'inspected','cleanup_mode':'no_cleanup','summary':'复用已结束真实批次及当前候选；仅发布本机查阅账本、代理GET，无新业务执行或清理。','resources':['21当前HTTP18424/r2；调度停止；Fusion r3；本机临时代理和隧道'],'observed_at':observed,'evidence_ids':['runtime','s04_failure']},'quality_issues':issues,'evidence':[{'id':k,'path':f'evidence/{k}.json','label':k,'mime_type':'application/json','visibility':'public','source_ref':str(v.relative_to(ROOT))} for k,v in sources.items()]}
with (newdir/'document.json').open('x') as f:json.dump(doc,f,ensure_ascii=False,indent=2);f.write('\n')
config=read(ROOT/'deploy/investigation-test/read-only.example.json');config.update(ledger_root='ledger',environment_label='streaming-20261115-01',port=free_port())
upstream=read(ROOT/'deploy/investigation-test/upstream.example.json');forward_port=free_port();assert forward_port!=config['port'];upstream.update(base_url=f'http://127.0.0.1:{forward_port}',openapi_file=str(ROOT/'docs/operations/evidence/test-http-proxy-w2-20261115-01/live-openapi.json'))
save('service-config.json',config);save('upstream-config.json',upstream)
i_run=next(v for v in s04['runs'] if v['kind']=='incident_diagnosis');event_case=next(v for v in cases if v['label']=='event_case');C1=artifacts[event_case['C1_artifact_id']]['content_json'];a01=next(k for k in C1['alerts'] if k=='09e85609-d734-5b2a-81ba-d086fc81b619');query=C1['alerts'][a01]['queries'][0]
source_trace=next(urlsplit(v['url']).path for v in http if query['run_id'] in v['url'] and v['url'].endswith('/trace'))
i_trace=next(urlsplit(v['url']).path for v in http if i_run['run_id'] in v['url'] and v['url'].endswith('/trace'))
plan={'batch_id':doc['batch']['id'],'environment_label':config['environment_label'],'tenant_id':tenant,'snapshot_file':str(snapshot),'snapshot_sha256':sha(snapshot),'source_files':{str(v.relative_to(ROOT)):sha(v) for v in sources.values()},'bindings':bindings,'failed_I':{'run_id':i_run['run_id'],'trace_url':i_trace,'raw_artifact_id':i_run['models'][0]['original_artifact_ids'][0]},'cross_run':{'case_id':event_case['case_id'],'case_run_id':event_case['run_id'],'C1_artifact_id':event_case['C1_artifact_id'],'source_alert_id':a01,'source_run_id':query['run_id'],'query_artifact_id':query['id'],'query_step_id':query['step_id'],'trace_url':source_trace,'source_type':'C1_paired_A_query_not_previous_Case_comparison'},'request_plan':{'test_api':['capabilities','batches','batch_detail','cases','operations_2_pages','preparation','quality_issues','one_registered_evidence_content'],'business':['7_actual_task_details','A04_and_failed_I_Run_details','two_Case_details_Run_Result','failed_I_trace_steps_2_pages_raw_artifact_content','event_Case_C1_directory_and_content','A01_source_Run_directory_trace_filtered_artifacts_content']},'direct_upstream_requests':['OpenAPI_once_for_current_hash'],'reused_tests':'old24component_and_TCP_empty_error_no_repeat','business_writes':0,'model_calls':0,'database_queries':0,'kafka_sends':0,'dispatcher_changes':0,'viewer_changes':0}
save('plan.json',plan)
profile={'repository':str(ROOT),'python':str(ROOT/'.local/conda-envs/socai2/bin/python'),'service_config':str(OUT/'service-config.json'),'upstream_config':str(OUT/'upstream-config.json'),'evidence_directory':str(OUT/'tcp-01'),'ledger_root':str(OUT/'ledger'),'ssh_binary':'/usr/bin/ssh','ssh_target':'sting-infra21','forward_spec':f'127.0.0.1:{forward_port}:127.0.0.1:18424','forward_url':upstream['base_url'],'proxy_url':f"http://127.0.0.1:{config['port']}",'connect_timeout_seconds':10,'request_timeout_seconds':30,'startup_timeout_seconds':20,'startup_poll_seconds':0.25,'stop_timeout_seconds':10,'ledger_page_limit':4,'step_page_limit':1,'max_requests':40,'environment_label':config['environment_label']}
save('tcp-profile.json',profile);(OUT/'tcp-01').mkdir()
save('preparation-01.json',{'status':'prepared_offline','prepared_at':datetime.now(timezone.utc).isoformat(),'business_execution_repeated':False,'mapping_operations':len(operations),'test_cases':len(testcases),'quality_issues':len(issues),'source_files_verified':plan['source_files'],'live_mode_means_current_HTTP_reading':True,'service_source_changed':False})
print(json.dumps({'status':'prepared','operations':len(operations),'cases':len(testcases),'quality_issues':len(issues),'cross_run':plan['cross_run']},ensure_ascii=False))
