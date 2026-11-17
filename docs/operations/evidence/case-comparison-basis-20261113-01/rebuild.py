"""Offline C6 selected-baseline business view; original Run and responses are never changed."""
import copy
import hashlib
import json
import os
import re
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / 'services/api'), str(ROOT)]
config = json.loads((HERE / 'config.json').read_text())
os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(ROOT / config['policy'])
from app.socai2 import case_followup_input as inputs
from app.socai2 import case_followup_output as outputs
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import Scope
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.case_followup_loader import graph_candidates
from app.socai2.model_protocol import prepare_request
from app.socai2.runtime_policy import active_policy


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if path.exists():
        assert path.read_text() == text, ('existing_evidence_differs', str(path))
    else:
        path.write_text(text)


flow = ROOT / config['original_flow'] / 'flow' / config['scenario']
db, summary = read(flow / 'export/database.json'), read(flow / 'summary.json')
arts = {a['id']: a for a in db['artifacts'] if a['run_id'] == summary['run_id']}
call = next(c for c in summary['calls'] if c['stage'] == 'C6')
request = arts[call['request_artifact_id']]
actual = request['content_json']['payload']
context = Context.model_validate(next(a['content_json'] for a in arts.values()
    if a['schema_version'] == 'socai2.baseline-context.v1'))
base = next(a['content_json'] for a in arts.values() if a['schema_version'] == 'socai2.case-model-input.v1')
frozen = {aid: a for aid, a in arts.items() if a['content_json'] is not None
          and a['kind'] not in {'model_request', 'model_response'} and a['captured_at'] < request['captured_at']}


def stage(code):
    step = next(s for s in db['run_steps'] if s['run_id'] == summary['run_id']
                and s['kind'] == 'stage' and s['stage_code'] == code)
    return frozen[step['output_artifact_id']]


prior, dispatch = stage('C3'), stage('C4.routing')['content_json']
execution, plans = delivery_followups(dispatch, frozen[dispatch['initial_analysis_artifact_id']]['content_json'])
# Restore the program-owned field order from BaselineDelivery.comparison and
# Scope; JSONB readback retains values but not the original presentation order.
comparison = {k: summary['comparison'][k] for k in ('result_id', 'state', 'prior_scope',
    'added_alert_ids', 'removed_alert_ids', 'shared_alert_ids', 'limitations')}
comparison['prior_scope'] = Scope.model_validate(comparison['prior_scope']).model_dump(mode='json')
result = context.prior_results[comparison['result_id']]
value = {k: result[k] for k in ('conclusion', 'conclusion_state', 'conclusion_origin', 'validation_state', 'delivery_state')}
value['comparison_result_id'] = comparison['result_id']
lead = [{'original': value, 'required': True, 'entry': {'value': value},
         'source': {'ref': inputs.reference('result', comparison['result_id'], 'prior_analysis'),
                    'alert_ids': comparison['shared_alert_ids']}}]
bases = sorted([a for a in frozen.values() if a['content_json'].get('type') in
                {'materials', 'query_projection', 'deep_summary', 'graph_snapshot'}], key=lambda a: a['id'])
graph_state, graphs = graph_candidates(bases, frozen)
profile = active_policy().case_io


def profile_from(path):
    raw = path.read_bytes()
    return replace(profile, raw=raw, sha256=hashlib.sha256(raw).hexdigest())


recorded_profile = profile_from(ROOT / config['recorded_profile'])
old_profile = profile_from(HERE / 'before-source/services/api/app/socai2/case-input-v1.json')
assert context.case_input_profile == recorded_profile.identity


def build(selected_profile):
    # Explicit offline binding, not a rewrite or restart of the frozen Run.
    rebound = context.model_copy(update={'case_input_profile': selected_profile.identity})
    selected_base = copy.deepcopy(base)
    selected_base['case_boundary']['profile'] = selected_profile.identity
    with patch.object(inputs, 'selected_profile', return_value=selected_profile):
        prepared = inputs.build('C6', rebound, selected_base, frozen,
            previous=prior['content_json'], prior_id=prior['id'], material=stage('C4.materials')['content_json'],
            projections=sorted([a for a in bases if a['content_json']['type'] == 'query_projection'],
                               key=lambda a: (a['captured_at'], a['id'])),
            graphs=graphs, lead=[*lead, *plans],
            extra={**actual['followup_boundary']['program_metadata'], 'comparison': comparison,
                   'followup_execution': execution, 'graph_state': graph_state})
    assert prepared['ready'], prepared['reason']
    return prepared, rebound


before, _ = build(old_profile)
after, rebound = build(profile)
assert before['messages'] == actual['body']['messages'], 'before_messages_not_exact_recorded_request'
assert before['source_map'] == actual['source_map']
assert before['followup_boundary'] == actual['followup_boundary']
before_rows = {r['id']: r for r in before['followup_boundary']['records']}
after_rows = {r['id']: r for r in after['followup_boundary']['records']}
assert before_rows.keys() == after_rows.keys()
changed = [sid for sid, row in after_rows.items() if row != before_rows[sid]]
assert changed and all(after_rows[sid].get('context_identity') == comparison['result_id'] for sid in changed)
for sid in changed:
    row = after_rows[sid]
    expected = copy.deepcopy(before_rows[sid])
    expected['value']['comparison_basis'] = row['value']['comparison_basis']
    assert row == expected
    basis = row['value']['comparison_basis']
    assert [f['statement'] for f in basis['findings']] == [f['statement'] for f in result['findings']]
    assert [f['limitations'] for f in basis['findings']] == [f['limitations'] for f in result['findings']]
    assert all(q['id'] != 'coverage' for q in basis['questions'])
    assert basis['case_impact']['cannot_generalize'] == result['case_impact']['cannot_generalize']
for sid, src in after['source_map'].items():
    assert {k: v for k, v in src.items() if k != 'visible_value_sha256'} == {
        k: v for k, v in before['source_map'][sid].items() if k != 'visible_value_sha256'}
assert after['followup_boundary']['dependencies'] == before['followup_boundary']['dependencies']
last = next(c for c in reversed(summary['calls']) if c['stage'] == 'C6')
reply = read(flow / last['reply_file'])
content = reply['raw']['choices'][0]['message']['content']
outputs.parse_final(content, before, rebound, comparison)
wire = prepare_request(SimpleNamespace(provider=request['content_json']['provider'],
    schema_profile=request['content_json']['schema_profile']),
    {**actual['body'], 'messages': after['messages'], 'response_format': outputs.final_format(after, rebound, comparison)})
out = HERE / config['output']
save(out / 'C6-model-input.txt', after['messages'][1]['content'])
save(out / 'C6-request-preview.json', wire)
save(out / 'C6-selection.json', {k: after[k] for k in ('source_map', 'case_boundary', 'followup_boundary', 'omissions')})
body = after['messages'][1]['content']
start = body.index('[' + changed[0] + ']')
following = re.search(r'^\[[^\n]*｜原范围=', body[start:], re.MULTILINE)
save(out / 'C6-selected-comparison.txt', body[start:start + following.start()] if following else body[start:])
save(HERE / 'before/C6-model-input.txt', before['messages'][1]['content'])
save(HERE / 'before/C6-original-request.json', actual['body'])
save(HERE / 'before/C6-original-final-response.json', reply)
save(HERE / 'before/selected-result.json', result)
old_files = read(HERE / 'before.json')['original_files_sha256']
assert all(sha(ROOT / name) == expected for name, expected in old_files.items())
save(HERE / 'verification.json', {
    'status': 'passed', 'kind': 'offline_preview_not_dispatched', 'source_run_id': summary['run_id'],
    'request_artifact_id': request['id'], 'before_rebuild_matches_actual_request_sources_and_boundary': True,
    'recorded_profile': recorded_profile.identity, 'before_profile': old_profile.identity, 'offline_after_profile': profile.identity,
    'before_characters': len(before['messages'][1]['content']), 'after_characters': len(after['messages'][1]['content']),
    'changed_sources': changed, 'preserved_source_references': len(after_rows),
    'unchanged_other_records': len(after_rows) - len(changed),
    'preserved_dependencies': len(after['followup_boundary']['dependencies']),
    'historical_findings': len(result['findings']),
    'selected_open_questions': [q['id'] for q in after_rows[changed[0]]['value']['comparison_basis']['questions']],
    'historical_prose_scope_and_impact_preserved': True, 'old_final_response_validated_only_against_old_boundary': True,
    'original_files_unchanged': len(old_files), 'new_model_calls': 0, 'database_calls': 0,
    'quality': 'NOT_PASSED_UNCHANGED_FROM_09',
})
print('C6 comparison preview passed:', len(after['messages'][1]['content']), 'characters;', len(changed), 'selected Result changed; other sources preserved.')
