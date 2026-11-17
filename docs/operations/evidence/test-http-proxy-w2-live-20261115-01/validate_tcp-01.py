"""One bounded live ledger/proxy readback; no business writes, SQL, model, or retries."""
import hashlib
import json
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx

FOLDER = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text())
def sha(data):
    return hashlib.sha256(data).hexdigest()
def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def tree(path):
    return {str(p.relative_to(path)):sha(p.read_bytes()) for p in path.rglob('*') if p.is_file()}
def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2);f.write('\n')
def listening(url):
    u=urlsplit(url)
    try:
        with socket.create_connection((u.hostname,u.port),timeout=0.3):return True
    except OSError:return False


def main():
    c=read(FOLDER/'tcp-profile.json');plan=read(FOLDER/'plan.json');up=read(FOLDER/'upstream-config.json')
    out=Path(c['evidence_directory']);ledger=Path(c['ledger_root']);before=tree(ledger)
    snapshot=Path(plan['snapshot_file']);assert sha(snapshot.read_bytes())==plan['snapshot_sha256']
    rows=read(snapshot)['rows'];artifacts={v['id']:v for v in rows['artifacts']}
    doc=read(FOLDER/'inputs/document.json');bindings={v['operation_id']:v for v in plan['bindings']}
    result={'status':'started','source':'real_local_ledger_and_proxy_to_21_current_HTTP','started_at':datetime.now(timezone.utc).isoformat(),
            'source_snapshot_sha256':plan['snapshot_sha256'],'requests':[],'checks':[],'business_writes':0,'model_calls':0,'database_queries':0,
            'kafka_sends':0,'dispatcher_changes':0,'viewer_changes':0,'S04_success_path_accepted':False,'direct_reused_artifact_ref_covered':False}
    ssh=service=None
    seen=set()
    def check(ok,name):
        result['checks'].append({'passed':bool(ok),'check':name})
    with (out/'ssh.log').open('x') as sshlog,(out/'server.log').open('x') as serverlog:
        try:
            assert not listening(c['proxy_url']) and not listening(c['forward_url']), 'chosen temporary ports occupied'
            ssh=subprocess.Popen([c['ssh_binary'],'-N','-T','-o','BatchMode=yes','-o','ControlMaster=no','-o','ControlPath=none','-o','ExitOnForwardFailure=yes','-o',f"ConnectTimeout={c['connect_timeout_seconds']}",'-L',c['forward_spec'],c['ssh_target']],stdout=sshlog,stderr=sshlog)
            service=subprocess.Popen([c['python'],'-m','investigation_test','serve','--config',c['service_config'],'--upstream-config',c['upstream_config']],cwd=c['repository'],env={**os.environ,'PYTHONPATH':str(Path(c['repository'])/'services')},stdout=serverlog,stderr=serverlog)
            deadline=time.monotonic()+c['startup_timeout_seconds']
            while not (listening(c['proxy_url']) and listening(c['forward_url'])):
                assert service.poll() is None and ssh.poll() is None,'temporary process exited'
                if time.monotonic()>=deadline:raise TimeoutError('temporary services not ready')
                time.sleep(c['startup_poll_seconds'])
            with httpx.Client(timeout=c['request_timeout_seconds'],trust_env=False,follow_redirects=False) as client:
                def get(path,label,*,direct=False):
                    assert path.startswith('/') and not path.startswith('//') and not urlsplit(path).netloc,'relative configured path only'
                    assert (direct,path) not in seen,'duplicate request is outside this plan'
                    assert len(seen)<c['max_requests'],'request bound reached'
                    seen.add((direct,path));reply=client.get((c['forward_url'] if direct else c['proxy_url'])+path)
                    number=len(result['requests'])+1;name=f'response-{number:02d}.json'
                    (out/name).write_bytes(reply.content)
                    item={'method':'GET','path':path,'label':label,'source':'direct_contract' if direct else ('business_proxy' if path.startswith('/api/') else 'test_ledger'),
                          'status':reply.status_code,'response':name,'sha256':sha(reply.content),'headers':{k:v for k,v in reply.headers.items() if k in {'content-type','content-length','x-content-sha256','x-investigation-environment','x-investigation-contract'}},'observed_at':datetime.now(timezone.utc).isoformat()}
                    result['requests'].append(item);assert reply.status_code==200,(label,reply.status_code)
                    if path.startswith('/api/'):
                        check(reply.headers.get('x-investigation-environment')==c['environment_label'],'upstream_environment_'+label)
                        check(reply.headers.get('x-investigation-contract')==up['openapi_sha256'],'contract_header_'+label)
                    return reply.json(),reply

                cap,_=get('/test-api/v1/capabilities','capabilities')
                contract,wire=get('/openapi.json','actual_current_contract',direct=True)
                check(sha(wire.content)==up['openapi_sha256']==cap['investigation_http']['contract_sha256'],'actual_current_80_operation_contract')
                check(sum(m in {'get','post','put','patch','delete','head','options'} for item in contract['paths'].values() for m in item)==80,'current_80_operations')
                check(cap['service_version']=='0.2.0' and cap['viewer_version'] is None and cap['investigation_http']['get_operations']==55,'existing_service_version_no_viewer_claim')
                batches,_=get('/test-api/v1/batches','batches')
                check(len(batches['items'])==1 and batches['items'][0]['batch']['id']==plan['batch_id'],'new_ledger_single_actual_batch')
                batch,_=get(batches['items'][0]['detail_url'],'batch_detail')
                check(batch['batch']['mode']=='live' and batch['batch']['provenance']=='live_execution' and batch['batch']['execution_state']=='failed','live_reading_preserves_source_failure')
                cases,_=get(batch['links']['cases'],'test_cases')
                check(cases['total']==3 and {v['id']:v['status'] for v in cases['items']}=={v['id']:v['status'] for v in doc['cases']},'test_case_statuses_preserved')
                ops=[];cursor=None
                while True:
                    params={'limit':c['ledger_page_limit']}
                    if cursor:params['cursor']=cursor
                    page,_=get(batch['links']['operations']+'?'+urlencode(params),'operations_page')
                    ops+=page['items'];cursor=page['next_cursor']
                    if not cursor:break
                check(len(ops)==7 and {v['id']:v['mappings'] for v in ops}=={v['id']:v['mappings'] for v in doc['operations']},'seven_exact_operation_mappings_paged')
                prep,_=get(batch['links']['preparation'],'preparation')
                check(prep['preparation']['cleanup_mode']=='no_cleanup','preparation_no_cleanup')
                quality,_=get(batch['links']['quality-issues'],'quality_records')
                check(quality['total']==4 and sum(v['affects_flow'] for v in quality['items'])==1,'quality_separate_and_I_blocker_retained')
                evidence=next(v for v in batch['evidence'] if v['id']=='s04_failure')
                _,original=get(evidence['content_url'],'registered_source_failure_evidence')
                check(sha(original.content)==evidence['sha256'] and original.content==(FOLDER/'inputs/evidence/s04_failure.json').read_bytes(),'registered_test_evidence_original_bytes')

                # Bootstrap task identity comes from real published mappings and saved provider status URLs.
                case_runs={}
                for op in ops:
                    b=bindings[op['id']];mapped=op['mappings'][0]
                    check(mapped['subject_id']==b['subject_id'] and mapped['task_id']==b['task_id'],'mapped_task_identity_'+b['task_id'])
                    task,_=get(b['task_url'],'task_'+b['task_id'])
                    check(task['task_id']==b['task_id'] and task['status']==b['expected_state'] and task['latest_run_id']==b['run_id'] and task['retry_count']==0,'actual_task_state_'+b['task_id'])
                    if b['expected_state']=='skipped':
                        check(task['attempts']==[] and task['results']==[] and task['reason_code']=='automatic_attempts_stopped','skipped_has_no_invented_attempt_Run_'+b['task_id'])
                        continue
                    check(len(task['attempts'])==1 and task['attempts'][0]['run_id']==mapped['run_id'],'real_attempt_from_task_'+b['task_id'])
                    run,_=get(task['attempts'][0]['run_url'],'Run_'+b['run_id'])
                    check(run['run']['id']==b['run_id'] and run['run']['state']==b['expected_state'],'same_Run_state_'+b['run_id'])
                    if b['subject_type']=='case':
                        case_runs[b['run_id']]=run
                        detail,_=get(b['case_url'],'Case_'+b['subject_id'])
                        check(detail['member_count']==b['member_count'],'Case_member_count_'+b['subject_id'])
                        check(detail['current_assessment']['input_freshness']['state']=='stale','Case_current_freshness_preserved_'+b['subject_id'])
                        result_ref=next(v for v in task['results'] if v['id']==b['result_id'])
                        saved,_=get(result_ref['url'],'Case_result_'+b['result_id'])
                        check(saved['result']['id']==b['result_id'] and saved['result']['delivery_state']=='partial' and saved['result']['validation_state']=='accepted','Case_result_original_partial_'+b['result_id'])
                        check(run['previous_run_url'] is None and run['comparison_result_url'] is None and saved['previous_run_url'] is None and saved['comparison_result_url'] is None,'no_new_Case_previous_comparison_'+b['subject_id'])
                    elif b['subject_type']=='incident':
                        check(run['run']['stop_reason']=='model_response_not_complete' and run['result']['state']=='failed' and run['result']['diagnosis'] is None and run['valid_for_current_input'] is False,'I_failure_not_usable_current_diagnosis')
                        check(run['input_selection']['selected_count']==4,'failed_I_actual_four_selected_members')
                    else:
                        check(run['result']['id']==b['result_id'],'A04_result_matches_ledger')

                failed=plan['failed_I'];trace,_=get(failed['trace_url'],'failed_I_trace')
                all_steps=[];cursor=None
                while True:
                    params={'limit':c['step_page_limit']}
                    if cursor:params['cursor']=cursor
                    page,_=get(trace['steps_url']+'?'+urlencode(params),'failed_I_steps_page')
                    all_steps+=page['items'];cursor=page['next_cursor']
                    if not cursor:break
                expected_steps={s['id'] for s in rows['run_steps'] if s['run_id']==failed['run_id']}
                check({s['id'] for s in all_steps}==expected_steps and len(all_steps)==trace['steps_total']==2,'nonempty_steps_pagination_complete_no_duplicate')
                directory,_=get(trace['artifacts_url'],'failed_I_artifacts')
                raw_meta=next(v for v in directory['items'] if v['id']==failed['raw_artifact_id'])
                raw,_=get(raw_meta['content_url'],'failed_I_raw_original')
                def verify_content(content,meta):
                    f=artifacts[meta['id']];body=content['content_json']
                    check(content['availability']=='available' and body==f['content_json'] and content['content_text']==f['content_text'],'original_artifact_content_'+meta['id'])
                    check(sha(encoded(body))==meta['sha256']==f['sha256'] and len(encoded(body))==meta['size_bytes']==f['size_bytes'],'original_artifact_hash_size_'+meta['id'])
                    return body
                raw_body=verify_content(raw,raw_meta)
                check(raw_body['raw']['choices'][0]['finish_reason']=='length' and raw_body['raw']['usage']['completion_tokens']==3000,'I_raw_real_length_and_usage_preserved')

                cross=plan['cross_run_I'];run=case_runs[cross['case_run_id']]
                directory,_=get(run['artifacts_url'],'event_Case_artifacts')
                c1_meta=next(v for v in directory['items'] if v['id']==cross['C1_artifact_id'])
                c1,_=get(c1_meta['content_url'],'event_Case_C1')
                context=verify_content(c1,c1_meta)
                source=context['incidents'][cross['incident_id']]['diagnosis_scope']
                check(source['source_run_id']==cross['source_run_id'] and source['source_run_id']!=cross['case_run_id'] and source['input_artifact_id']==cross['input_artifact_id'],'C1_actual_cross_Run_source_identity')
                # Existing public directory route uses the saved source identity; content URL is never constructed.
                source_path='/api/v1/socai2/analysis-runs/'+source['source_run_id']+'/artifacts'
                directory,_=get(source_path,'original_I_source_artifacts')
                source_meta=next(v for v in directory['items'] if v['id']==source['input_artifact_id'])
                check(directory['subject_type']=='incident' and directory['subject_id']==cross['incident_id'] and source_meta['run_id']==source['source_run_id'],'source_directory_keeps_original_owner')
                source_body,_=get(source_meta['content_url'],'original_I_source_input')
                frozen=verify_content(source_body,source_meta)
                check(sha(encoded(frozen))==source['source_fingerprint'] and frozen['input_selection']['selected_count']==3,'original_I_frozen_three_member_scope_not_current_four')
                result['cross_run']={'current_Case_Run':cross['case_run_id'],'C1_artifact_id':cross['C1_artifact_id'],'actual_source_Run':source['source_run_id'],'actual_source_input_artifact':source['input_artifact_id'],'returned_content_url':source_meta['content_url'],'source_selection':3,'current_incident_members':4,'same_case_comparison':False}
                check(tree(ledger)==before,'ledger_unchanged_after_all_GETs')
                actual={kind:sum(v['source']==kind for v in result['requests']) for kind in ('test_ledger','business_proxy','direct_contract')}
                check(actual=={'test_ledger':9,'business_proxy':24,'direct_contract':1},'minimal_34_request_plan_exact')
                result.update(status='passed' if all(v['passed'] for v in result['checks']) else 'failed',request_counts=actual,ledger_unchanged=tree(ledger)==before)
        except BaseException as exc:  # noqa: BLE001 -- retain interruption/failure before stopping only our processes
            result.update(status='failed',error_type=type(exc).__name__,error=str(exc))
        finally:
            for process in (service,ssh):
                if process is not None:
                    process.terminate()
                    try:process.wait(timeout=c['stop_timeout_seconds'])
                    except subprocess.TimeoutExpired:
                        process.kill();process.wait(timeout=c['stop_timeout_seconds'])
            result['temporary_processes_stopped']=all(p is None or p.poll() is not None for p in (service,ssh))
            result['process_exit_codes']={'service':service.poll() if service else None,'ssh':ssh.poll() if ssh else None}
            result['temporary_ports_closed']=not listening(c['proxy_url']) and not listening(c['forward_url'])
            result['ledger_after']=tree(ledger);result['ledger_before']=before
            result['ended_at']=datetime.now(timezone.utc).isoformat()
            result['failed_checks']=[v for v in result['checks'] if not v['passed']]
            save(out/'result.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'requests','checks','ledger_before','ledger_after'}},ensure_ascii=False))
    return result['status']=='passed' and result['temporary_processes_stopped'] and result['temporary_ports_closed']

if __name__=='__main__':
    raise SystemExit(0 if main() else 1)
