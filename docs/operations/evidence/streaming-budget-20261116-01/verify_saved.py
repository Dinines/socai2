"""Check this continuation against the saved S04 failure and fixed initial cases."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

folder = Path(__file__).resolve().parent
config = json.loads((folder/'control-config.json').read_text())
expected = json.loads((folder.parent/'test-streaming-s04-20261115-01/expected.json').read_text())
old = json.loads((folder.parent/'test-streaming-s04-20261115-01/analysis-pg-01.json').read_text())['rows']
raw = (folder/'analysis-pg-01.json').read_bytes()
snapshot = json.loads(raw)
rows = snapshot['rows']
indexed = {k: {r['id']: r for r in v} for k, v in rows.items() if k != 'analysis_subject_state'}
new = {k: [r for r in v if r['id'] not in {o['id'] for o in old[k]}]
       for k, v in rows.items() if k != 'analysis_subject_state'}
iid = config['expected_incident_id']
event_case, control = [c['case_id'] for c in expected['baseline_cases']]
members = {m['alert_id'] for m in rows['incident_alerts'] if m['incident_id'] == iid}
artifacts = indexed['artifacts']
checks, calls, mapped, quality = [], [], [], []


def check(ok, name, identity=None):
    checks.append({'passed': bool(ok), 'check': name, 'id': identity})


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def moment(value):
    return datetime.fromisoformat(value)


who = snapshot['identity']
check(who['database'] == config['config']['database'] and who['readonly'] == 'on' and who['ssl'], 'candidate_readonly_tls')
check(snapshot['tenant_case_count'] == 2 and len(members) == 4, 'same_two_cases_original_four_member_incident')
preserved = {}
for table in ('alerts', 'alert_materials', 'alert_source_refs', 'alert_assessments', 'incident_diagnoses',
              'runs', 'run_steps', 'artifacts', 'analysis_tasks', 'analysis_attempts', 'results',
              'case_assessments', 'case_assessment_sources', 'case_assessment_members'):
    changed = [r['id'] for r in old[table] if indexed[table].get(r['id']) != r]
    preserved[table] = {'previous_count': len(old[table]), 'changed_or_missing': changed}
    check(not changed, 'old_failed_and_initial_records_preserved_'+table)
check(not new['alerts'] and not new['alert_assessments'] and not new['cases'], 'no_alert_reanalysis_or_new_case')
check({m['alert_id'] for m in rows['case_alerts'] if m['case_id'] == event_case} == members,
      'active_case_followed_four_members')
check({m['alert_id'] for m in rows['case_alerts'] if m['case_id'] == control}
      == set(expected['baseline_cases'][1]['member_ids']), 'single_alert_control_fixed_scope')
check(not any(r['case_id'] == control for r in new['runs'])
      and not any(t['subject_id'] == control for t in new['analysis_tasks']), 'control_has_no_new_run_or_task')
check(indexed['cases'][control] == next(r for r in old['cases'] if r['id'] == control), 'control_case_row_preserved')
check(len([r for r in new['runs'] if r['incident_id'] == iid]) == 1, 'one_new_incident_run')
check(len([r for r in new['runs'] if r['case_id'] == event_case]) == 1, 'one_automatic_active_case_followup_run')
submitted = json.loads((folder/'submit-02.json').read_text())['receipt']['task_id']
for task in new['analysis_tasks']:
    check(task['state'] in {'completed', 'skipped'} and task['retry_count'] == 0, 'new_task_terminal_no_retry', task['id'])
    check((task['source'], task['intent'], task['subject_id']) == ('user', 'rerun', iid) if task['id'] == submitted
          else (task['source'], task['intent']) == ('periodic', 'check')
          and task['subject_id'] in {iid, event_case}, 'explicit_I_then_only_natural_checks', task['id'])
for artifact in new['artifacts']:
    body = artifact['content_json']
    size = len(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()) if body is not None else len((artifact['content_text'] or '').encode())
    sha = digest(body) if body is not None else hashlib.sha256((artifact['content_text'] or '').encode()).hexdigest()
    check(sha == artifact['sha256'] and size == artifact['size_bytes'] and artifact['material_state'] == 'complete',
          'new_artifact_complete_hash_and_size', artifact['id'])
for run in sorted(new['runs'], key=lambda r: r['started_at']):
    rid = run['id']
    attempts = [a for a in rows['analysis_attempts'] if a['run_id'] == rid]
    check(len(attempts) == 1 and attempts[0]['outcome'] == run['state'] == 'completed', 'one_ended_attempt_completed_run', rid)
    if not attempts:
        continue
    attempt = attempts[0]
    check(artifacts[attempt['policy_artifact_id']]['content_json']['sha256'] == config['new_policy_sha256'], 'new_policy_frozen_to_run', rid)
    source = artifacts[run['input_artifact_id']]['content_json']
    needed = {run['input_artifact_id'], attempt['policy_artifact_id']}
    models = [s for s in rows['run_steps'] if s['run_id'] == rid and s['kind'] == 'model']
    for step in models:
        req = artifacts[step['input_artifact_id']]['content_json']
        resp = artifacts[step['output_artifact_id']]['content_json'] if step['output_artifact_id'] else {}
        request, response = req.get('payload', req), resp.get('payload', resp)
        original = [a for a in new['artifacts'] if a['step_id'] == step['id']
                    and ((a.get('content_json') or {}).get('type') == 'model_original_response'
                         or (a.get('content_json') or {}).get('artifact_role') == 'model_original_response')]
        actual = response.get('raw') or {}
        finish = [c.get('finish_reason') for c in actual.get('choices', [])]
        cap = 8192 if run['incident_id'] else 16384 if step['stage_code'] in {'C3', 'C6'} else 8192
        check(request['body']['max_tokens'] == cap, 'actual_new_request_output_budget', step['id'])
        check(bool(finish) and all(f == 'stop' for f in finish), 'normal_model_end_without_truncation', step['id'])
        check(len(original) == 1 and original[0]['content_json']['raw'] == actual, 'original_reply_retained_equal', step['id'])
        needed.update([step['input_artifact_id'], step['output_artifact_id'], *[a['id'] for a in original]])
        calls.append({'run_id': rid, 'step_id': step['id'], 'stage': step['stage_code'],
                      'max_tokens': request['body']['max_tokens'], 'finish_reasons': finish, 'usage': step['usage'],
                      'request_artifact_id': step['input_artifact_id'], 'response_artifact_id': step['output_artifact_id'],
                      'original_artifact_ids': [a['id'] for a in original]})
        quality.append({'run_id': rid, 'stage': step['stage_code'], 'citation_review': response.get('citation_review'),
                        'validation_error': response.get('validation_error'), 'prose_quality': 'not_comprehensively_accepted'})
    entry = {'run_id': rid, 'task_id': attempt['task_id'], 'kind': run['kind'], 'state': run['state'],
             'subject_id': run['incident_id'] or run['case_id'], 'required_artifact_ids': needed}
    if run['incident_id']:
        check({m['alert']['id'] for m in source['members']} == members, 'I_frozen_four_members', rid)
        diagnosis = next(d for d in new['incident_diagnoses'] if d['source_run_id'] == rid)
        check(diagnosis['state'] == 'completed' and diagnosis['diagnosis'].get('validation_state') == 'accepted', 'new_diagnosis_accepted', rid)
        check(indexed['incidents'][iid]['latest_diagnosis_id'] == diagnosis['id'], 'new_diagnosis_current_pointer', rid)
        entry['result_id'] = diagnosis['id']
    else:
        context_artifact = next(a for a in new['artifacts'] if a['run_id'] == rid and a['schema_version'] == 'socai2.baseline-context.v1')
        context = context_artifact['content_json']
        needed.add(context_artifact['id'])
        check(set(context['scope']['alert_ids']) == set(context['alerts']) == members, 'Case_C1_four_members', rid)
        inc = context['incidents'][iid]
        check(inc['diagnosis_usable'] and inc['diagnosis_freshness'] == 'current'
              and inc['diagnosis']['id'] in {d['id'] for d in new['incident_diagnoses']}, 'Case_C1_uses_new_saved_diagnosis', rid)
        prior = expected['baseline_cases'][0]
        comparison = context['update_context']['comparison_context']
        check(comparison['state'] == 'eligible' and comparison['previous_run_id'] == prior['run_id']
              and comparison['comparison_result_id'] == prior['result_id']
              and run['comparison_result_id'] == prior['result_id'], 'comparison_own_immediate_previous_run_and_result', rid)
        irun = indexed['runs'][inc['diagnosis']['source_run_id']]
        check(moment(irun['ended_at']) <= moment(run['started_at']), 'Case_started_after_new_I_finished', rid)
        result = next(r for r in new['results'] if r['source_run_id'] == rid)
        check(result['comparison_result_id'] == prior['result_id'], 'result_saved_same_comparison', rid)
        check({m['alert_id'] for m in rows['result_members'] if m['result_id'] == result['id']} == members, 'result_four_member_scope', rid)
        check(artifacts[result['report_artifact_id']]['content_json']['conclusion'] == result['conclusion'], 'report_and_result_same_conclusion', rid)
        needed.add(result['report_artifact_id'])
        current = indexed['cases'][event_case]['current_assessment_id']
        check(current not in {a['id'] for a in old['case_assessments']}
              and indexed['case_assessments'][current]['conclusion'] == result['conclusion'], 'new_result_adopted', rid)
        entry.update(result_id=result['id'], comparison_context=comparison, incident_diagnosis_id=inc['diagnosis']['id'],
                     result_states={k: result[k] for k in ('validation_state', 'conclusion_state', 'delivery_state', 'change_kind')})
    needed.update(a['id'] for a in new['artifacts'] if a['run_id'] == rid and a['kind'] == 'tool_response')
    entry['required_artifact_ids'] = sorted(x for x in needed if x)
    mapped.append(entry)
failed = [c for c in checks if not c['passed']]
summary = {'status': 'passed' if not failed else 'failed', 'snapshot_sha256': hashlib.sha256(raw).hexdigest(),
           'check_count': len(checks), 'failed_checks': failed, 'checks': checks,
           'new_run_count': len(new['runs']), 'new_task_count': len(new['analysis_tasks']),
           'whole_change_accepted': False, 'model_quality': 'NOT_PASSED'}
outputs = {'saved-validation.json': summary, 'model-usage.json': {'generation_calls': len(calls), 'calls': calls, 'cost': None},
           'actual-map.json': {'snapshot_sha256': summary['snapshot_sha256'], 'runs': mapped, 'tasks': new['analysis_tasks'],
                               'control_case_id': control, 'event_case_id': event_case, 'incident_id': iid},
           'old-record-preservation.json': preserved, 'quality-findings.json': {'status': 'NOT_PASSED', 'records': quality}}
for name, value in outputs.items():
    with (folder/name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
print(json.dumps({k: v for k, v in summary.items() if k != 'checks'}, ensure_ascii=False))
