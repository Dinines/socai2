"""Compare the completed Run with its frozen source; no model or database calls."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def read(path):
    return json.loads(path.read_text())


def differences(left, right, path=()):
    if left == right:
        return []
    if isinstance(left, dict) and isinstance(right, dict) and left.keys() == right.keys():
        return [p for key in left for p in differences(left[key], right[key], (*path, key))]
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        return [p for index, (a, b) in enumerate(zip(left, right, strict=True))
                for p in differences(a, b, (*path, index))]
    return [list(path)]


folder = HERE / 'flow/R01'
plan, summary = read(HERE / 'flow/plan.json'), read(folder / 'summary.json')
db, before = read(folder / 'export/database.json'), read(ROOT / plan['config']['snapshot'])
verification = read(folder / 'verification.json')
old_rows = {}
for table in ('runs', 'results', 'case_assessments', 'tasks', 'task_revisions'):
    after = {row['id']: row for row in db[table]}
    for row in before[table]:
        assert after[row['id']] == row, ('old_row_changed', table, row['id'])
    old_rows[table] = len(before[table])
for alert in db['alerts']:
    expected = plan['expected_alert_pointers'].get(alert['id'])
    if expected is not None:
        assert {key: alert[key] for key in expected} == expected
for incident in db['incidents']:
    expected = plan['expected_incident_pointers'].get(incident['id'])
    if expected is not None:
        assert incident['latest_diagnosis_id'] == expected

answers = [json.loads(read(folder / f'calls/call-{n}-receipt.json')['raw']['choices'][0]['message']['content'])
           for n in range(1, summary['real_model_calls'] + 1)]
assert [call['stage'] for call in summary['calls']] == ['C3', 'C4.deep', 'C6', 'C6']
first, final = answers[-2:]
changed = differences(first, final)
comparison_ids = set(verification['calls'][-1]['selected_baseline_ids'])
assert comparison_ids.intersection(final['comparison']['support_ids'])
current, previous = summary['current_assessment'], read(ROOT / plan['config']['original_flow'] / 'flow/H01/summary.json')['current_assessment']
assert current['input_freshness'] == {'state': 'current', 'reasons': []}
assert current['value']['id'] != previous['value']['id']
assert current['value']['conclusion'] == summary['results'][0]['conclusion']
assert any(s['result_id'] == summary['results'][0]['id'] for s in current['sources'])
http = read(folder / 'export/http-readback.json')
assert all(value['status'] == 200 for value in http.values())
transport = read(folder / 'transport-result.json')
assert transport['ready'] and transport['owned_forward_closed']
knowledge = verification['knowledge_receipt']
assert knowledge['outcome'] == 'data' and knowledge['returned_rows'] == 2
assert all(c['http_status'] == 200 for c in knowledge['source_metadata']['calls'])
result = {
    'run_id': summary['run_id'], 'result': summary['results'][0],
    'real_model_calls': summary['real_model_calls'], 'known_usage': summary['known_usage'], 'cost': None,
    'real_knowledge_embedding_calls': sum(c['backend'] == 'embedding' for c in knowledge['source_metadata']['calls']),
    'real_knowledge_search_calls': sum(c['backend'] == 'vector' and c['method'] == 'POST' for c in knowledge['source_metadata']['calls']),
    'knowledge_forward_closed': True, 'old_database_rows_unchanged': old_rows,
    'AI_current_pointers_unchanged': True, 'old_files_unchanged': verification['old_files_unchanged'],
    'actual_requests_raw_answers_and_GETs_equal_database': True, 'ASGI_GETs': len(http),
    'previous_assessment': {'id': previous['value']['id'], 'freshness': previous['input_freshness']},
    'current_assessment': {'id': current['value']['id'], 'freshness': current['input_freshness']},
    'selected_baseline_id': plan['config']['comparison_result_id'],
    'selected_baseline_source_ids': sorted(comparison_ids),
    'first_and_final_cited_selected_baseline': all(comparison_ids.intersection(a['comparison']['support_ids']) for a in (first, final)),
    'same_result_background_ids_in_actual_C6': verification['calls'][-1]['same_result_background_ids'],
    'correction_policy': summary['calls'][-1]['correction']['policy'],
    'correction_diagnostics': summary['calls'][-1]['correction']['errors'],
    'correction_changed_fields': changed,
    'conclusion_support_ids_before': first['conclusion']['support_ids'],
    'conclusion_support_ids_after': final['conclusion']['support_ids'],
    'conclusion_text_equal_selected_baseline': final['conclusion']['text'] == plan['comparison_result']['conclusion'],
    'comparison_prose_and_kind_unchanged_in_correction': first['comparison'] == final['comparison'],
    'Deep': {'action': answers[1]['action'], 'state': answers[1]['answer']['state']},
    'prose_quality': 'NOT_PASSED', 'quality_review': 'quality.json',
    'limits': ['synthetic_materials_and_H_no_accuracy_claim', 'one_new_Run_not_controlled_AB',
               'same_text_background_and_missing_baseline_feedback_not_triggered_in_this_Run',
               'strict_acceptance_is_not_prose_quality', 'no_additional_sampling_or_tests'],
}
body = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
path = HERE / 'review.json'
if path.exists():
    assert path.read_text() == body
else:
    path.write_text(body)
print('Saved Run comparison;', len(http), 'ASGI GETs;', 'changed fields:', changed)
