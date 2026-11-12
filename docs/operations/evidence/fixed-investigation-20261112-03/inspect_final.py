"""Replay only C6 input assembly from the saved Run, never dispatch generation."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_scope_recovery.real_model import initialize
from tools.testdata.incident_integration.run import read, save, sha
config, folder = initialize(Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).with_name('config.json'))
from app.services.llm_safety import classify_message
from app.socai2 import case_followup_input as module
from app.socai2.baseline_context import Context
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.baseline_store import encoded
from app.socai2.case_followup_loader import graph_candidates

data = read(folder / 'export/database.json')
run_id = read(folder / 'execution.json')['run_id']
artifacts = {a['id']: a for a in data['artifacts'] if a['run_id'] == run_id
             and a['content_json'] and a['kind'] not in ['model_request','model_response']}
def one(schema):
    return next(a for a in artifacts.values() if a['schema_version'] == schema)
context = Context.model_validate(one('socai2.baseline-context.v1')['content_json'])
base = one('socai2.case-model-input.v1')['content_json']
previous_step = max((s for s in data['run_steps'] if s['run_id'] == run_id and s['kind'] == 'stage'
    and s['stage_code'] in ['C3','C3.reanalysis'] and s['state'] == 'completed'), key=lambda s:s['seq'])
previous = artifacts[previous_step['output_artifact_id']]
dispatch = next(a['content_json'] for a in artifacts.values() if a['content_json'].get('type') == 'followup_dispatch')
execution, planned = delivery_followups(dispatch, artifacts[dispatch['initial_analysis_artifact_id']]['content_json'])
bases = [a for a in artifacts.values() if a['kind'] == 'source_snapshot'
         and a['content_json'].get('type') in ['materials','query_projection','deep_summary','graph_snapshot']]
state, graphs = graph_candidates(bases, artifacts)
material = next(a['content_json'] for a in bases if a['content_json'].get('type') == 'materials')
report = next(a['content_json'] for a in artifacts.values() if a['content_json'].get('type') == 'delivery_report')
observed, original = [], module.blocked
original_message = module.blocked_message
def traced(value):
    rejected = original(value)
    if rejected:
        observed.append({'type': type(value).__name__, 'characters': len(value) if isinstance(value,str) else None,
            'encoded_characters': len(encoded(value).decode()), 'actual_text_reason': classify_message(value) if isinstance(value,str) else None,
            'encoded_reason': classify_message(encoded(value).decode()), 'value': value})
    return rejected
def traced_message(value):
    rejected = original_message(value)
    if rejected:
        observed.append({'type':'actual_message','characters':len(value),
            'actual_text_reason':classify_message(value),'value':value})
    return rejected
module.blocked = traced
module.blocked_message = traced_message
try:
    prepared = module.build('C6', context, base, artifacts, previous=previous['content_json'], prior_id=previous['id'],
        material=material, projections=[], extra={'round':'final_delivery','comparison':report['comparison'],
            'followup_execution':execution,'graph_state':state}, lead=planned, graphs=graphs)
finally:
    module.blocked = original
    module.blocked_message = original_message
summary = {'ready':prepared['ready'], 'reason':prepared['reason'], 'bytes':prepared['bytes'],
    'record_counts':dict(Counter(r['block'] for r in prepared['followup_boundary']['records'])), 'guard_diagnostics':observed,
    'prepared':prepared}
summary['source_sha256'] = {name: sha(ROOT / 'services/api/app/socai2' / name) for name in (
    'baseline_model_view.py','case_model_boundary.py','case_followup_input.py','case_input_text.py')}
if prepared['ready'] and len(sys.argv) == 2 and sys.argv[1] == 'C6-input-after.json':
    before = read(folder / 'C6-input-before.json')
    assert prepared['source_map'] == before['prepared']['source_map']
    assert prepared['messages'][1]['content'] == before['guard_diagnostics'][0]['value']
    summary['exact_original_sources_and_message_preserved'] = True
save(folder / sys.argv[1], summary)
print(json.dumps({**{k:v for k,v in summary.items() if k not in ['guard_diagnostics','prepared']},
                  'guards':[{k:v for k,v in r.items() if k!='value'} for r in observed]},ensure_ascii=False))
