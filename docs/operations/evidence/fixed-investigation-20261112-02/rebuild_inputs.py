"""Rebuild the exact rejected I/C3 inputs offline; no dispatch or DB mutation."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_scope_recovery.real_model import initialize
from tools.testdata.incident_integration.run import read, save, sha

config, folder = initialize(Path(__file__).with_name('config.json'))
from app.socai2 import case_followup_input, case_model_boundary, incident_model_boundary
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import digest
from app.socai2.runtime_policy import active_policy

data = read(folder / 'export/database.json')
artifacts = {a['id']: a for a in data['artifacts']}
execution = read(folder / 'execution.json')
i_run = next(r for r in data['runs'] if r['id'] == read(folder / 'I-execution.json')['run_id'])
messages, sources, _, prepared = incident_model_boundary.build(
    artifacts[i_run['input_artifact_id']]['content_json'], i_run['input_artifact_id'], active_policy().incident_io,
    execution_time=i_run['started_at'])
old_messages = read(folder / 'I/calls/tokenizer-1.json')['request']['messages']

def shown_ids(text):
    return {sid for group in re.findall(r'^\[(N\d+_S\d+(?:,N\d+_S\d+)*)\]', text, flags=re.MULTILINE)
            for sid in group.split(',')}

assert shown_ids(old_messages[1]['content']) == shown_ids(messages[1]['content']) == set(sources)
assert len(messages[1]['content']) < len(old_messages[1]['content'])
assert any(len(row['source_ids']) > 1 and row['source_paths'][0].startswith('$.rows.') for row in prepared['records'])
case_run = next(r for r in data['runs'] if r['id'] == execution['run_id'])
case_arts = [a for a in data['artifacts'] if a['run_id'] == case_run['id']]
c1 = next(a for a in case_arts if a['schema_version'] == 'socai2.baseline-context.v1')
context = Context.model_validate(c1['content_json'])
old_base = next(a['content_json'] for a in case_arts if a['schema_version'] == 'socai2.case-model-input.v1')
enrichment = [(a['id'], a['content_json'], {}) for a in case_arts if a['kind'] == 'tool_response']
materials = {aid: next(m for m in data['alert_materials'] if m['id'] == alert.material['id'])
             for aid, alert in context.alerts.items() if alert.material}
base = case_model_boundary.build(context, c1['id'], enrichment, old_base['source_state_ledger'], materials,
    execution_time=case_run['started_at'], run_id=case_run['id'])
assert base['ready'], base['reason']
def refs(mapping):
    return {digest(item['ref']): {k: item[k] for k in ('ref','alert_ids','visible_value_sha256')} for item in mapping.values()}
assert refs(base['source_map']) == refs(old_base['source_map'])
assert len(base['input_ledger']['user']) < len(old_base['input_ledger']['user'])
final = case_followup_input.build('C6', context, base, {}, extra={'comparison': {'state': 'initial', 'result_id': None}})
assert final['ready'], final['reason']
summary = {'state': 'offline_rebuilt_not_dispatched', 'I': {'original_characters': len(old_messages[1]['content']),
    'characters': len(messages[1]['content']), 'all_source_ids_preserved': True, 'sources': len(sources)},
    'C3': {'original_characters': len(old_base['input_ledger']['user']), 'characters': len(base['input_ledger']['user']),
           'ready': base['ready'], 'original_references_roles_values_scopes_preserved': True, 'sources': len(base['source_map'])},
    'C6': {'ready': final['ready'], 'characters': len(final['messages'][1]['content'])},
    'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in (ROOT/'services/api/app/socai2').glob('*.py')},
    'I_messages': messages, 'C3_messages': base['messages'], 'C6_messages': final['messages']}
save(folder / 'input-rebuild.json', summary)
print(json.dumps({k:v for k,v in summary.items() if k in ['state','I','C3','C6']}, ensure_ascii=False))
