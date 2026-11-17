"""Read-only source verification and exact exports of a completed scenario."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--scenario', choices=('B01', 'H01', 'H02'), required=True)
args = parser.parse_args()
folder = HERE / 'flow' / args.scenario


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_text() == body, 'saved_evidence_differs:' + str(path)
    else:
        with path.open('x') as file:
            file.write(body)


data = read(folder / 'export/database.json')
run_id = read(folder / 'start-request.json')['run_id']
run = next(r for r in data['runs'] if r['id'] == run_id)
artifacts = {a['id']: a for a in data['artifacts']}
current = [a for a in artifacts.values() if a['run_id'] == run_id]
steps = {s['id']: s for s in data['run_steps']}
context = next(a['content_json'] for a in current if a['schema_version'] == 'socai2.baseline-context.v1')
base = next((a['content_json'] for a in current if 'input_ledger' in (a['content_json'] or {})), None)
responses = {a['step_id']: a['content_json']['payload'] for a in current if a['kind'] == 'model_response'}
requests = [a for a in current if a['kind'] == 'model_request']
calls, known_usage, usage_unknown = [], {}, False
for file in sorted((folder / 'calls').glob('call-*-intent.json'), key=lambda p: int(p.name.split('-')[1])):
    number = int(file.name.split('-')[1])
    body = read(file)['body']
    matches = [a for a in requests if a['content_json']['payload']['body'] == body]
    assert len(matches) == 1, (file.name, len(matches))
    artifact = matches[0]
    payload = artifact['content_json']['payload']
    stage = steps[artifact['step_id']]['stage_code']
    prefix = f"call-{number:02}-{stage.replace('.', '-')}"
    text = body['messages'][1]['content']
    save(folder / 'review' / (prefix + '-input.txt'), text)
    reply_file = folder / 'calls' / f'call-{number}-receipt.json'
    receipt = read(reply_file) if reply_file.exists() else {}
    response = responses.get(artifact['step_id'], {})
    if receipt.get('state') == 'response_received':
        assert response['raw'] == receipt['raw'], 'saved_response_changed'
        raw_text = receipt['raw']['choices'][0]['message'].get('content')
        if isinstance(raw_text, str):
            save(folder / 'review' / (prefix + '-answer.txt'), raw_text)
    usage = (receipt.get('raw') or {}).get('usage')
    if usage is None:
        usage_unknown = True
    else:
        for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
            if isinstance(usage.get(key), int):
                known_usage[key] = known_usage.get(key, 0) + usage[key]
            else:
                usage_unknown = True
    records = payload.get('followup_boundary', (base or {}).get('input_ledger', {})).get('records', [])
    human = [r for r in records if r.get('context_kind') == 'human_feedback']
    for row in human:
        revision = context['tasks'][row['ref']['source_path'].split('.')[2]]['revision']
        assert row['value']['result_text'] == revision['result_text']
        assert row['original_scope'] == revision['result_scope'] and row['value']['revision'] == revision['revision']
    calls.append({'number': number, 'stage': stage, 'request_artifact_id': artifact['id'],
        'input_file': 'review/' + prefix + '-input.txt', 'answer_file': 'review/' + prefix + '-answer.txt' if receipt.get('state') == 'response_received' else None,
        'request_file': str(file.relative_to(folder)), 'request_sha256': digest(file),
        'reply_file': str(reply_file.relative_to(folder)) if reply_file.exists() else None,
        'reply_sha256': digest(reply_file) if reply_file.exists() else None,
        'characters': len(text), 'sources': len(payload['source_map']), 'messages': len(body['messages']),
        'validation_error': response.get('validation_error'), 'validation_review': response.get('validation_review'),
        'correction': payload.get('correction'),
        'human_sources': [{'id': r['id'], 'original_scope': r['original_scope'], 'ref': r['ref'],
            'attachment_source_ids': r['value'].get('source_refs', [])} for r in human],
        'knowledge_source_ids': [sid for sid, s in payload['source_map'].items() if s.get('knowledge')],
        'usage': usage})
assert len(calls) == read(folder / 'execution.json')['model_calls']
results = [r for r in data['results'] if r['source_run_id'] == run_id]
http = read(folder / 'export/http-readback.json')
assert http['run']['body']['run']['state'] == run['state']
for result in results:
    actual = http['result-' + result['id']]['body']['result']
    assert all(actual[k] == result[k] for k in ('id', 'source_run_id', 'conclusion', 'conclusion_state',
        'validation_state', 'delivery_state', 'findings', 'questions', 'recommendations', 'change_kind', 'change_summary'))
current_assessment = http['case']['body']['current_assessment']
if data['cases'][0]['current_assessment_id'] is None:
    assert current_assessment is None
else:
    adopted = next(a for a in data['case_assessments'] if a['id'] == data['cases'][0]['current_assessment_id'])
    assert current_assessment['value']['id'] == adopted['id']
    assert current_assessment['value']['conclusion'] == adopted['conclusion']
for task in data['task_revisions']:
    actual = http['H-' + task['id']]['body']
    assert all(actual[k] == task[k] for k in ('id', 'revision', 'result_text', 'result_scope', 'source_refs'))
delivery = next((a['content_json'] for a in current if (a['content_json'] or {}).get('type') == 'delivery_report'), None)
save(folder / 'review/delivery.json', delivery)
save(folder / 'summary.json', {'scenario': args.scenario, 'case_id': run['case_id'], 'run_id': run_id,
    'run_state': run['state'], 'stop_reason': run['stop_reason'], 'result_ids': [r['id'] for r in results],
    'results': [{k: r[k] for k in ('id', 'validation_state', 'conclusion_state', 'delivery_state', 'conclusion', 'change_kind', 'change_summary')} for r in results],
    'current_assessment': current_assessment, 'comparison': delivery.get('comparison') if delivery else None,
    'real_model_calls': len(calls), 'known_usage': known_usage, 'usage_unknown': usage_unknown, 'cost': None,
    'calls': calls, 'requests_and_raw_replies_equal_database': True, 'result_H_and_current_GETs_equal_database': True,
    'snapshot_sha256': digest(folder / 'export/database.json'), 'plan_sha256': digest(HERE / 'flow/plan.json'),
    'prose_quality': 'PENDING_REVIEW_NOT_INFERRED_FROM_VALIDATION',
    'scope': 'Real model plus existing isolated database; synthetic materials/H; original A/I reused; no accuracy claim.'})
print(args.scenario, run['state'], [(r['validation_state'], r['conclusion_state'], r['delivery_state']) for r in results], known_usage)
