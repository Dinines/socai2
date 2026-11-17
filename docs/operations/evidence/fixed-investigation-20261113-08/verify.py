"""Inspect saved actual requests and their dependencies; never call a model or DB."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REF_KEYS = {'support_ids', 'counter_ids', 'evidence_ids', 'source_ids'}
MEMBER_KEYS = {'alert_ids', 'related_alert_ids', 'added_alert_ids', 'removed_alert_ids', 'shared_alert_ids'}


def read(path):
    return json.loads(path.read_text())


def normalized(value, sources, boundary):
    members = {v: k for k, v in boundary.get('member_aliases', {}).items()}
    objects = {v: k for k, v in boundary.get('object_aliases', {}).items()}
    if isinstance(value, list):
        return [normalized(v, sources, boundary) for v in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, child in value.items():
        if key in REF_KEYS:
            refs = [sources[s]['ref'] for s in child]
            result[key] = [r for i, r in enumerate(refs) if r not in refs[:i]]
        elif key in MEMBER_KEYS:
            result[key] = [members.get(v, v) for v in child]
        elif key == 'alert_id':
            result[key] = members.get(child, child)
        elif key == 'object_keys':
            result[key] = [objects.get(v, v) for v in child]
        else:
            result[key] = normalized(child, sources, boundary)
    return result


def used_refs(value):
    if isinstance(value, list):
        return [s for v in value for s in used_refs(v)]
    if isinstance(value, dict):
        return [s for key, child in value.items() for s in (child if key in REF_KEYS else used_refs(child))]
    return []


parser = argparse.ArgumentParser()
parser.add_argument('--scenario', choices=('B01', 'H01'), required=True)
args = parser.parse_args()
folder = HERE / 'flow' / args.scenario
summary, db = read(folder / 'summary.json'), read(folder / 'export/database.json')
artifacts = {a['id']: a for a in db['artifacts'] if a['run_id'] == summary['run_id']}
base = next(a['content_json'] for a in artifacts.values() if a['schema_version'] == 'socai2.case-model-input.v1')
material_rows = [r for r in base['input_ledger']['records'] if r.get('business_block', r['block']) == 'material']
c2 = next(a['content_json'] for a in artifacts.values() if a['schema_version'] == 'socai2.baseline-enrichment.v1' and a['kind'] == 'source_snapshot')
knowledge = next(s for s in c2['sources'] if s['source'] == 'knowledge')
calls = []
for call in summary['calls']:
    payload = artifacts[call['request_artifact_id']]['content_json']['payload']
    boundary = payload['case_boundary']
    records = payload.get('followup_boundary', base['input_ledger'])['records']
    by_ref = {json.dumps(r['ref'], sort_keys=True): r for r in records}
    if call['stage'] in {'C3', 'C6'}:
        for row in material_rows:
            actual = by_ref[json.dumps(row['ref'], sort_keys=True)]
            assert actual['value'] == row['value'] and actual['alert_ids'] == row['alert_ids']
    prior_checks = []
    for row in records:
        if call['stage'] != 'C6' or row['block'] != 'C3':
            continue
        prior = artifacts[row['ref']['id']]
        assert prior['run_id'] == summary['run_id'] and prior['content_json']['validation'] == 'structure_scope_sources_checked'
        original = prior['content_json']['analysis']
        assert not {'members', 'domains'}.intersection(row['value'])
        for field in ('summary', 'findings', 'questions', 'conflicts'):
            expected = original[field]
            if field == 'questions':
                expected = [q for q in expected if q['id'] != 'coverage']
            assert normalized(row['value'][field], payload['source_map'], boundary) == normalized(
                expected, prior['content_json']['source_map'], {}), ('C3_to_C6_changed', field)
        prior_checks.append({'artifact_id': prior['id'], 'source_run_id': prior['run_id'],
            'selected_prose_members_and_references_match': True, 'selected_fields': list(row['value'])})
    cards = [r for r in records if r.get('knowledge', {}).get('part') == 'card']
    for card in cards:
        assert payload['body']['messages'][1]['content'].count(card['value']['record']['content']) == 1
    raw = read(folder / call['reply_file']) if call['reply_file'] else {}
    content = raw.get('raw', {}).get('choices', [{}])[0].get('message', {}).get('content')
    try:
        answer = json.loads(content) if isinstance(content, str) else {}
    except ValueError:
        answer = {}  # Original unparseable answer remains in its receipt and validation.
    human = [r for r in records if r.get('context_kind') == 'human_feedback']
    if call['stage'] in {'C3', 'C6'}:
        assert bool(human) == (args.scenario == 'H01')
    source_ids = set(used_refs(answer))
    calls.append({'number': call['number'], 'stage': call['stage'], 'characters': call['characters'],
        'C3_to_C6': prior_checks, 'material_fields': len(material_rows) if call['stage'] in {'C3', 'C6'} else None,
        'human_sources': [r['id'] for r in human], 'human_cited_ids': sorted(source_ids & {r['id'] for r in human}),
        'knowledge_source_ids': call['knowledge_source_ids'],
        'knowledge_cited_ids': sorted(source_ids & set(call['knowledge_source_ids'])),
        'knowledge_cards': [{'id': r['id'], 'characters': len(r['value']['record']['content'])} for r in cards],
        'fixed_comparison': boundary.get('fixed_comparison'), 'validation_error': call['validation_error']})
old = read(HERE / 'flow/plan.json')['original_files_sha256']
assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha for p, sha in old.items())
result = {'scenario': args.scenario, 'status': 'passed', 'new_model_or_database_calls': 0,
          'old_files_unchanged': len(old), 'knowledge_receipt': knowledge, 'calls': calls,
          'scope': 'Actual request provenance and program transport only; prose quality reviewed separately.'}
body = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
path = folder / 'verification.json'
if path.exists():
    assert path.read_text() == body
else:
    path.write_text(body)
print(args.scenario, 'actual input/dependency verification passed;', len(calls), 'recorded calls;', len(old), 'old files unchanged')
