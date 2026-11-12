"""Offline readback assertions and A2 reconstruction; no model or database call."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_scope_recovery.real_model import initialize
from tools.testdata.incident_integration.run import read, save, sha
config, folder = initialize(Path(__file__).with_name('config.json'))
from app.socai2 import alert_model_boundary, alert_basic_contract
from app.socai2.baseline_store import encoded, StoreError
from app.socai2.runtime_policy import active_policy

data = read(folder / 'export/database.json')
artifacts = {a['id']: a for a in data['artifacts']}
run = next(r for r in data['runs'] if r['id'] == read(folder / 'A2-execution.json')['run_id'])
source = artifacts[run['input_artifact_id']]['content_json']
queries = [(a['id'], a['content_json']) for a in data['artifacts']
           if a['run_id'] == run['id'] and a['kind'] == 'tool_response']
queries.sort(key=lambda q: next(i for i,n in enumerate(('assets','history','threat_intel')) if n==q[1]['tool_name']))
try:
    alert_basic_contract.build(source, run['input_artifact_id'], queries, execution_time=run['started_at'], complete_material=True)
except StoreError as exc:
    assert exc.code == 'alert_model_view_unavailable'
else:
    raise AssertionError('legacy cap must still reject this source')
messages, sources, _, prepared = alert_model_boundary.build(source, run['input_artifact_id'], queries,
    active_policy().alert_io, execution_time=run['started_at'])
assert sources
rebuilt = {'state': 'offline_rebuilt_not_dispatched', 'source_run_id': run['id'],
    'input_artifact_id': run['input_artifact_id'], 'original_run_state': run['state'],
    'messages': messages, 'source_map': sources, 'message_bytes': len(encoded(messages)), 'source_count': len(sources),
    'boundary': prepared['boundary'], 'source_sha256': {name: sha(ROOT / name) for name in (
        'services/api/app/socai2/alert_basic_contract.py', 'services/api/app/socai2/alert_model_boundary.py')}}
path = folder / 'A2-rebuilt-not-dispatched.json'
if path.exists():
    assert read(path) == rebuilt
else:
    save(path, rebuilt)

result = data['results'][0]
result_http = read(folder / 'http' / ('result-' + result['id'] + '.json'))['body']
case_http = read(folder / 'http/case.json')['body']
run_http = read(folder / 'http/run.json')['body']
for key in ('id','source_run_id','conclusion','validation_state','delivery_state','recommendations','report_artifact_id'):
    assert result_http['result'][key] == result[key], key
assert result['conclusion'] is None and result['validation_state'] == 'rejected'
assert case_http['current_assessment'] is None
assert result['id'] in run_http['result_ids']
assert len(result_http['members']) == len(data['result_members']) == 3
assert artifacts[result['report_artifact_id']]['run_id'] == result['source_run_id']
case_run = next(r for r in data['runs'] if r['id'] == result['source_run_id'])
c1 = next(a['content_json'] for a in data['artifacts'] if a['run_id'] == case_run['id'] and a['schema_version'] == 'socai2.baseline-context.v1')
assert len(c1['alerts']) == 3 and len(c1['incidents']) == 1
models = []
for step in sorted(data['run_steps'],key=lambda x:(x['run_id'],x['seq'])):
    if step['kind'] != 'model': continue
    req = artifacts[step['input_artifact_id']]['content_json']; req = req.get('payload',req)
    res = artifacts[step['output_artifact_id']]['content_json']; res = res.get('payload',res)
    knowledge = {sid: src for sid,src in req.get('source_map',{}).items() if src.get('knowledge')}
    used=[]
    def scan(value,path):
        if isinstance(value,dict):
            for key,v in value.items(): scan(v,path+[key])
        elif isinstance(value,list):
            for index,v in enumerate(value): scan(v,path+[index])
        elif isinstance(value,str) and value in knowledge:
            used.append({'path':path,'id':value,'ref':knowledge[value]['ref']})
    content=res.get('raw',{}).get('choices',[{}])[0].get('message',{}).get('content')
    if content: scan(json.loads(content),[])
    models.append({'stage':step['stage_code'],'seq':step['seq'],'state':step['state'],
        'validation_error':res.get('validation_error'),'knowledge_input_sources':len(knowledge),'knowledge_references':used})
summary={'batch':config['batch'],'real_model_calls':read(folder/'execution.json')['model_calls'],
    'total_tokens':sum(s['usage']['total_tokens'] for s in data['run_steps'] if s['kind']=='model'),
    'case_run_state':case_run['state'],'result_id':result['id'],'validation_state':result['validation_state'],
    'delivery_state':result['delivery_state'],'conclusion':result['conclusion'],'adopted':False,
    'database_http_fields_match':True,'frozen_A_members':len(c1['alerts']),'frozen_I_members':len(c1['incidents']),
    'A2_offline_rebuilt_bytes':len(encoded(messages)),'A2_new_dispatches':0,'models':models,
    'quality':'NOT_PASSED','full_fixed_flow_acceptance':False}
verification = folder/'verification.json'
if verification.exists():
    assert read(verification) == summary
else:
    save(verification, summary)
final_model = next(m for m in models if m['stage'] == 'C6')
stored_questions = {q['id']: q for q in result['questions']}
stored_refs = [ref for q in stored_questions.values() for ref in q['evidence_refs']]
knowledge_refs = [c['ref'] for c in final_model['knowledge_references']]
assert knowledge_refs and all(ref in stored_refs for ref in knowledge_refs)
assert result_http['result']['questions'] == result['questions']
readback = {'knowledge_original_refs_saved': knowledge_refs, 'database_http_questions_match': True,
    'historical_roles_unchanged': all(ref['role'] == 'prior_analysis' for ref in knowledge_refs),
    'conclusion_null_rejected_not_adopted': True}
path = folder/'knowledge-readback.json'
if path.exists():
    assert read(path) == readback
else:
    save(path, readback)
from app.socai2.baseline_context import Context
from app.socai2 import case_followup_output
from app.socai2.baseline_analysis_contract import AnalysisRejected
step = next(s for s in data['run_steps'] if s['kind'] == 'model' and s['stage_code'] == 'C6')
request = artifacts[step['input_artifact_id']]['content_json']['payload']
# Same coverage derivation as case_followup_input.build, using frozen records only.
base = next(a['content_json'] for a in data['artifacts'] if a['run_id'] == case_run['id']
            and a['schema_version'] == 'socai2.case-model-input.v1')
request = {**request, 'coverage': {aid: {**row, 'included': sum(aid in r['alert_ids']
    for r in request['followup_boundary']['records'])} for aid,row in base['coverage'].items()}}
response = artifacts[step['output_artifact_id']]['content_json']['payload']
content = response['raw']['choices'][0]['message']['content']
context = Context.model_validate(c1)
comparison = request['followup_boundary']['program_metadata']['comparison']
try:
    case_followup_output.parse_final(content, request, context, comparison)
except AnalysisRejected as exc:
    assert str(exc) == 'recommendation_needs_sources'
else:
    raise AssertionError('old invalid answer must remain rejected')
review = case_followup_output.FinalReview(request, context, comparison)
assert review.partial(content) is None
# PostgreSQL jsonb changes object-key order in the program coverage sentence;
# compare authored analysis exactly and keep that display-only boundary explicit.
retained = review.details['retained_analysis']
prior = response['validation_review']['retained_analysis']
assert {**retained, 'questions': [q for q in retained['questions'] if q['id'] != 'coverage']} == {
    **prior, 'questions': [q for q in prior['questions'] if q['id'] != 'coverage']}
left = next(q for q in retained['questions'] if q['id'] == 'coverage')
right = next(q for q in prior['questions'] if q['id'] == 'coverage')
assert {k:v for k,v in left.items() if k != 'answer'} == {k:v for k,v in right.items() if k != 'answer'}
assert [sorted(line.split('；')) if 'tool_name=' in line else line for line in left['answer'].splitlines()] == [
    sorted(line.split('；')) if 'tool_name=' in line else line for line in right['answer'].splitlines()]
receipt = {'state': 'offline_receive_check_no_dispatch', 'original_response_artifact_id': step['output_artifact_id'],
    'rejection_unchanged': 'recommendation_needs_sources', 'retained_business_analysis_unchanged': True, 'program_coverage_query_field_order_only': True,
    'source_sha256': {name: sha(ROOT / name) for name in ('services/api/app/socai2/baseline_delivery_contract.py',
        'services/api/app/socai2/case_followup_output.py', 'services/api/app/socai2/case_citation_feedback.py')}}
path = folder/'C6-receive-after.json'
if path.exists():
    assert read(path) == receipt
else:
    save(path, receipt)
print(json.dumps({k:v for k,v in summary.items() if k!='models'},ensure_ascii=False))
