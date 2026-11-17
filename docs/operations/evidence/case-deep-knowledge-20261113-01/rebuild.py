"""Rebuild one recorded Deep input offline; never dispatch or rewrite originals."""
import copy
import hashlib
import json
import os
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


original = ROOT / config['original_flow']
flow = original / 'flow' / config['scenario']
db, summary = read(flow / 'export/database.json'), read(flow / 'summary.json')
artifacts = {a['id']: a for a in db['artifacts'] if a['run_id'] == summary['run_id']}
call = next(c for c in summary['calls'] if c['stage'] == 'C4.deep')
request = artifacts[call['request_artifact_id']]
actual = request['content_json']['payload']
assert not actual['binding_map'], 'this_frozen_request_has_no_tool_candidates'
context = Context.model_validate(next(a['content_json'] for a in artifacts.values()
    if a['schema_version'] == 'socai2.baseline-context.v1'))
base = next(a['content_json'] for a in artifacts.values() if a['schema_version'] == 'socai2.case-model-input.v1')
prior_step = next(s for s in db['run_steps'] if s['run_id'] == summary['run_id']
                  and s['stage_code'] == 'C3' and s['kind'] == 'stage')
prior = artifacts[prior_step['output_artifact_id']]
frozen = {aid: a for aid, a in artifacts.items() if a['content_json'] is not None
          and a['kind'] not in {'model_request', 'model_response'} and a['captured_at'] < request['captured_at']}
material = next(a['content_json'] for a in frozen.values() if a['content_json'].get('type') == 'materials')
projections = sorted([a for a in frozen.values() if a['content_json'].get('type') == 'query_projection'],
                     key=lambda a: (a['captured_at'], a['id']))
profile = active_policy().case_io
old_profile = replace(profile, raw=(HERE / 'before-source/services/api/app/socai2/case-input-v1.json').read_bytes())
old_profile = replace(old_profile, sha256=hashlib.sha256(old_profile.raw).hexdigest())
assert context.case_input_profile == old_profile.identity
old_config = old_profile.config
new_config = profile.config
assert new_config['knowledge_selection']['deep_question_purposes'] == {'authorization': []}
new_config['knowledge_selection'].pop('deep_question_purposes')
assert new_config == old_config, 'only_question_knowledge_selection_changes'


def build(selected_profile):
    # Explicit offline profile binding; the persisted context and request are
    # never changed. Production still rejects frozen profile mismatches.
    rebound = context.model_copy(update={'case_input_profile': selected_profile.identity})
    selected_base = copy.deepcopy(base)
    selected_base['case_boundary']['profile'] = selected_profile.identity
    with patch.object(inputs, 'selected_profile', return_value=selected_profile):
        prepared = inputs.build('Deep', rebound, selected_base, frozen,
            previous=prior['content_json'], prior_id=prior['id'], question_id=actual['case_boundary']['question_id'],
            material=material, projections=projections, options=[], binding_map={})
    assert prepared['ready'], prepared['reason']
    return prepared


before, after = build(old_profile), build(profile)
assert before['messages'] == actual['body']['messages'], 'before_messages_not_exact_recorded_request'
assert before['source_map'] == actual['source_map']
assert before['followup_boundary'] == actual['followup_boundary']
before_rows = {r['id']: r for r in before['followup_boundary']['records']}
after_rows = {r['id']: r for r in after['followup_boundary']['records']}
removed = before_rows.keys() - after_rows.keys()
assert removed and all(before_rows[s].get('knowledge') for s in removed)
assert not any(d['visible_id'] in removed for d in before['followup_boundary']['dependencies'])
assert all(row == before_rows[sid] for sid, row in after_rows.items())
assert after['source_map'] == {sid: src for sid, src in before['source_map'].items() if sid not in removed}
assert after['followup_boundary']['dependencies'] == before['followup_boundary']['dependencies']
assert after['tool_presentation'] == before['tool_presentation']
assert after['program_facts'] == before['program_facts'] and after['source_states'] == before['source_states']
omissions = [o for o in after['omissions'] if o['reason'] == 'knowledge_purpose_not_for_question']
assert {json.dumps(o['ref'], sort_keys=True) for o in omissions} == {
    json.dumps(before_rows[s]['ref'], sort_keys=True) for s in removed}
assert 'knowledge_purpose_not_for_question' not in after['messages'][1]['content']
content = read(flow / call['reply_file'])['raw']['choices'][0]['message']['content']
assert outputs.parse_deep(content, before) == outputs.parse_deep(content, after)
wire = prepare_request(SimpleNamespace(provider=request['content_json']['provider'],
    schema_profile=request['content_json']['schema_profile']),
    {**actual['body'], 'messages': after['messages'], 'response_format': outputs.deep_format(after)})
out = HERE / config['output']
save(out / 'Deep-model-input.txt', after['messages'][1]['content'])
save(out / 'Deep-request-preview.json', wire)
save(out / 'Deep-selection.json', {k: after[k] for k in ('source_map', 'case_boundary', 'followup_boundary', 'omissions')})
save(HERE / 'before/Deep-model-input.txt', before['messages'][1]['content'])
save(HERE / 'before/Deep-original-request.json', actual['body'])
old_files = read(HERE / 'before.json')['original_files_sha256']
assert all(sha(ROOT / name) == expected for name, expected in old_files.items())
result = {
    'status': 'passed', 'kind': 'offline_preview_not_dispatched', 'source_run_id': summary['run_id'],
    'question_id': actual['case_boundary']['question_id'], 'request_artifact_id': request['id'],
    'before_rebuild_matches_actual_messages_sources_and_boundary': True,
    'before_profile': old_profile.identity, 'offline_after_profile': profile.identity,
    'before_characters': len(before['messages'][1]['content']), 'after_characters': len(after['messages'][1]['content']),
    'removed_optional_cards': [before_rows[s] for s in sorted(removed)],
    'preserved_records': len(after_rows), 'preserved_dependencies': len(after['followup_boundary']['dependencies']),
    'all_preserved_records_and_source_refs_equal': True, 'tool_presentation_and_program_facts_equal': True,
    'original_answer_receive_unchanged': True, 'original_files_unchanged': len(old_files),
    'new_model_calls': 0, 'database_calls': 0, 'quality': 'NOT_PASSED_UNCHANGED_FROM_09',
    'contract': 'Model input selection only; original output/store/read contract and old accepted result unchanged.',
}
save(HERE / 'verification.json', result)
print('Deep offline preview passed;', result['before_characters'], '->', result['after_characters'],
      'characters;', len(after_rows), 'records and', result['preserved_dependencies'], 'dependencies preserved.')
