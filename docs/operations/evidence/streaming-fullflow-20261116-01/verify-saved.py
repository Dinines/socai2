"""Direct checks of this batch's ingress, rounds and unchanged original records."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
def read(name):return json.loads((root/name).read_text())
p=read('batch/profile.json');first=read('first-pg.json')['rows'];final=read('final-pg.json')['rows']
whole=read('http-create-whole.json')['response']['body']['primary_case_id'];single=read('http-create-single.json')['response']['body']['primary_case_id']
checks=[]
def check(name,truth):
    assert truth,name
    checks.append(name)
for phase,count in p['counts'].items():
    receipt=json.loads(read('send-'+phase+'-1.json')['stdout'])
    check(phase+'_exact_ack',receipt['accepted']==receipt['requested']==count and receipt['not_attempted']==0 and not receipt['cleanup_errors'])
for phase,count in [('S01',12),('S04',1)]:
    receipt=json.loads(read('probe-'+phase+'-context-readback-1.json')['stdout'])
    check(phase+'_lake_originals',receipt['status']=='passed' and receipt['new_batch_context_count']==count)
check('four_exact_alerts',{x['id'] for x in final['alerts']}==set(p['alert_ids']))
check('one_event_preserved',len(final['incidents'])==1 and final['incidents'][0]['id']==first['incidents'][0]['id'])
check('event_four_members',{x['alert_id'] for x in final['incident_alerts']}==set(p['alert_ids']))
check('four_triages_two_diagnoses',len(final['alert_assessments'])==4 and len(final['incident_diagnoses'])==2)
case_results=[]
for cid,n,rounds in [(whole,4,2),(single,1,1)]:
    runs=sorted([x for x in final['runs'] if x['case_id']==cid],key=lambda x:x['started_at'])
    members=[x for x in final['case_alerts'] if x['case_id']==cid]
    check(cid+'_scope_and_rounds',len(members)==n and len(runs)==rounds)
    expected=[3,4] if cid==whole else [1]
    check(cid+'_frozen_members',[sum(m['run_id']==r['id'] for m in final['run_members']) for r in runs]==expected)
    case_results.append({'case_id':cid,'members':n,'rounds':rounds,'runs':[{'run_id':r['id'],'state':r['state'],'delivery_state':r['delivery_state'],
      'result':[{k:v[k] for k in ('id','validation_state','conclusion_state','delivery_state','comparison_result_id','change_kind')} for v in final['results'] if v['source_run_id']==r['id']]} for r in runs]})
for table in ('alert_materials','alert_assessments','incident_diagnoses','run_members','results','result_members','artifacts'):
    index={x['id']:x for x in final[table]}
    check(table+'_prior_originals_preserved',all(index.get(x['id'])==x for x in first[table]))
check('all_tasks_terminal',all(x['state'] in {'completed','failed','skipped'} for x in final['analysis_tasks']))
for name in ('check-incident','check-whole-update'):
    identity=read('http-'+name+'.json')['response']['body']['task_id']
    task=next(x for x in final['analysis_tasks'] if x['id']==identity)
    check(name+'_is_explicit_user_check',task['source']=='user' and task['intent']=='check' and task['state']=='completed')
check_task=read('http-check-whole.json')['response']['body']['task_id'];t=next(x for x in final['analysis_tasks'] if x['id']==check_task)
check('explicit_no_change_check',t['state']=='skipped' and t['reason_code']=='no_changes')
check('no_change_without_attempt_or_run',not any(x['task_id']==check_task for x in final['analysis_attempts']))
pre=read('updated-pg.json')['rows']
check('no_change_runs_and_artifacts_identical',pre['runs']==final['runs'] and pre['artifacts']==final['artifacts'])
second=next(x for x in final['runs'] if x['case_id']==whole and x['id'] not in {r['id'] for r in first['runs']})
frozen=next(x['content_json'] for x in final['artifacts'] if x['id']==second['input_artifact_id'])
prior=next(x for x in first['runs'] if x['case_id']==whole)
check('previous_run_frozen',frozen['comparison_context']['previous_run_id']==prior['id'])
check('rejected_previous_not_used_as_baseline',frozen['comparison_context']['comparison_result_id'] is None and frozen['comparison_context']['reason_code']=='previous_conclusion_unusable')
models=read('model-summary-final.json')['models']
check('all_model_outputs_stop',all(x['finish_reason']=='stop' for x in models))
check('no_whitespace_exhaustion',all(x['trailing_whitespace']==0 for x in models))
check('configured_output_budgets',all(x['max_tokens']==(16384 if x['stage'] in ('C3','C6') else 8192) for x in models))
check('no_test_source_or_answer_markers',all(not any(key in x['input_observations'] for key in ('telemetry-channel-01',root.name,'synthetic','is_test','expected_verdict')) for x in models))
summary={'status':'passed_with_quality_and_input_issues','batch_id':p['batch_id'],'checks':checks,'check_count':len(checks),'cases':case_results,
 'comparison':frozen['comparison_context'],'positive_eligible_comparison_branch':'not_covered_in_this_batch_previous_result_rejected',
 'automatic_due_trigger':'not_covered_current_incident_4h_case_6h_explicit_http_checks_used',
 'snapshot_sha256':hashlib.sha256((root/'final-pg.json').read_bytes()).hexdigest(),'model_calls':len(models),
 'model_quality':'NOT_PASSED','input_boundary':'NOT_PASSED_tenant_uid_residual','whole_change_accepted':False}
with (root/'saved-validation.json').open('x') as f:json.dump(summary,f,ensure_ascii=False,indent=2)
print(json.dumps(summary,ensure_ascii=False,indent=2))
