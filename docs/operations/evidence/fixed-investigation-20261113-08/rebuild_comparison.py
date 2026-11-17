"""Offline C6 display/feedback repair on actual H01 material; no redispatch."""
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'services/api'), str(ROOT)]
config = json.loads((HERE / 'config.json').read_text())
os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(ROOT / config['policy'])
from app.socai2 import case_followup_input as inputs
from app.socai2 import case_followup_output as outputs
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_context import Context
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.baseline_store import encoded
from app.socai2.case_followup_loader import graph_candidates
from app.socai2.model_protocol import prepare_request


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


folder = HERE / 'fix-preview-review'
folder.mkdir(exist_ok=False)
flow = HERE / 'flow/H01'
snapshot = flow / 'export/database.json'
originals = {str(p.relative_to(ROOT)): sha(p) for p in (HERE / 'flow').rglob('*') if p.is_file()}
(folder / 'original-files.json').write_text(json.dumps(originals, indent=2) + '\n')
db, summary = read(snapshot), read(flow / 'summary.json')
rid = summary['run_id']
arts = {a['id']: a for a in db['artifacts'] if a['run_id'] == rid}
call = next(c for c in summary['calls'] if c['stage'] == 'C6')
request_artifact = arts[call['request_artifact_id']]
context = Context.model_validate(next(a['content_json'] for a in arts.values() if a['schema_version'] == 'socai2.baseline-context.v1'))
base = next(a['content_json'] for a in arts.values() if a['schema_version'] == 'socai2.case-model-input.v1')


def stage(code):
    step = next(s for s in db['run_steps'] if s['run_id'] == rid and s['kind'] == 'stage' and s['stage_code'] == code)
    return arts[step['output_artifact_id']]


prior, dispatch = stage('C3'), stage('C4.routing')['content_json']
execution, plans = delivery_followups(dispatch, arts[dispatch['initial_analysis_artifact_id']]['content_json'])
comparison = summary['comparison']
result = context.prior_results[comparison['result_id']]
value = {k: result[k] for k in ('conclusion', 'conclusion_state', 'conclusion_origin', 'validation_state', 'delivery_state')}
value['comparison_result_id'] = comparison['result_id']
lead = [{'original': value, 'required': True, 'entry': {'value': value},
         'source': {'ref': inputs.reference('result', comparison['result_id'], 'prior_analysis'), 'alert_ids': comparison['shared_alert_ids']}}]
bases = sorted([a for a in arts.values() if (a['content_json'] or {}).get('type') in
                {'materials', 'query_projection', 'deep_summary', 'graph_snapshot'}], key=lambda a: a['id'])
graph_state, graphs = graph_candidates(bases, arts)
frozen = {aid: a for aid, a in arts.items() if a['content_json'] is not None and a['kind'] not in {'model_request', 'model_response'}
          and a['captured_at'] < request_artifact['captured_at']}
after = inputs.build('C6', context, base, frozen, previous=prior['content_json'], prior_id=prior['id'],
    material=stage('C4.materials')['content_json'], projections=[a for a in bases if a['content_json']['type'] == 'query_projection'],
    graphs=graphs, lead=[*lead, *plans], extra={'comparison': comparison, 'followup_execution': execution, 'graph_state': graph_state})
assert after['ready'], after['reason']
call = next(c for c in summary['calls'] if c['stage'] == 'C6')
request = arts[call['request_artifact_id']]['content_json']
before = copy.deepcopy(request['payload'])
before['coverage'] = copy.deepcopy(base['coverage'])
for aid, v in before['coverage'].items():
    v['included'] = sum(aid in r['alert_ids'] for r in before['followup_boundary']['records'])
# Only presentation and diagnostics change, never sources or selected prose.
assert before['source_map'] == after['source_map']
assert before['followup_boundary']['records'] == after['followup_boundary']['records']
body = after['messages'][1]['content']
assert '[N5_S94]（同文历史背景引用：[N5_S87]）' in body
assert '指定比较基线引用=[N5_S94]' in body and '[N5_S87,N5_S94]' not in body
wire = prepare_request(SimpleNamespace(provider=request['provider'], schema_profile=request['schema_profile']),
    {**before['body'], 'messages': after['messages'], 'response_format': outputs.final_format(after, context, comparison)})
(folder / 'C6-model-input.txt').write_text(body)
(folder / 'C6-request-preview.json').write_text(json.dumps(wire, ensure_ascii=False, indent=2) + '\n')
checks = []
for number in (3, 4):
    original = read(flow / f'calls/call-{number}-receipt.json')['raw']['choices'][0]['message']['content']
    feedback = outputs.FinalReview(before, context, comparison).feedback(original)
    assert feedback['allowed_sources'] == []
    missing = next(e for e in feedback['errors'] if e['code'] == 'comparison_needs_selected_baseline_and_current_sources')
    assert missing['selected_baseline_ids'] == ['N5_S94'] and missing['selected_baseline_missing']
    (folder / f'call-{number}-feedback.json').write_text(json.dumps(feedback, ensure_ascii=False, indent=2) + '\n')
    try:
        outputs.parse_final(original, before, context, comparison)
    except AnalysisRejected as exc:
        rejected = str(exc)
    else:
        raise AssertionError('original_answer_must_remain_rejected')
    checks.append({'original_call': number, 'rejection_unchanged': rejected,
                   'feedback_codes': sorted({e['code'] for e in feedback['errors']}),
                   'feedback_characters': len(encoded(feedback).decode()), 'sent': False})
    if number == 3:
        preview = copy.deepcopy(read(flow / 'calls/call-4-intent.json')['body'])
        original_messages = copy.deepcopy(preview['messages'])
        preview['messages'][-1]['content'] = encoded(feedback).decode()
        assert preview['messages'][:-1] == original_messages[:-1]
        (folder / 'first-correction-preview-not-sent.json').write_text(json.dumps(preview, ensure_ascii=False, indent=2) + '\n')
assert all(sha(ROOT / path) == expected for path, expected in originals.items())
(folder / 'verification.json').write_text(json.dumps({'status': 'passed', 'kind': 'offline_preview_not_dispatched',
    'source_run_id': rid, 'original_files_unchanged': len(originals), 'source_map_and_records_unchanged': True,
    'before_characters': len(before['body']['messages'][1]['content']), 'after_characters': len(body),
    'replays': checks, 'new_model_calls': 0, 'database_calls': 0, 'old_Result_remains_rejected': True}, ensure_ascii=False, indent=2) + '\n')
print('C6 preview and two original-answer checks passed;', len(originals), 'files unchanged; zero external calls.')
