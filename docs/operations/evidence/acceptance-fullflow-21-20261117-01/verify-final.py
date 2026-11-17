"""Validate this actual two-part run using saved originals, without regeneration."""
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(relative):
    return json.loads((ROOT / relative).read_text())


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def main():
    prepared = ROOT / 'results/prepared'
    first = read('results/prepared/runs/part1/saved-records.json')
    final = read('results/prepared/runs/part2/saved-records.json')
    report = read('results/report-01/report.json')
    session = read('results/prepared/session.json')
    checks = {}
    checks['two_completed_parts'] = all(read(f'results/prepared/runs/{part}/state.json')['status'] == 'completed'
                                        for part in ('part1', 'part2'))
    checks['session_report_complete'] = report['all_parts_completed'] and report['statistics_state'] == 'saved_snapshots_complete'
    checks['no_report_or_execution_blockers'] = not report['blocking_issues'] and not report['report_issues'] and not report['models']['issues']
    checks['expected_subjects'] = len(final['alerts']) == 2 and len(final['incidents']) == len(final['cases']) == 1
    checks['same_incident_and_case'] = (first['incidents'][0]['id'] == final['incidents'][0]['id']
                                       and first['cases'][0]['id'] == final['cases'][0]['id'])
    checks['members_one_to_two'] = len(first['case_alerts']) == 1 and len(final['case_alerts']) == len(final['incident_alerts']) == 2
    checks['first_part_files_unchanged'] = all(hashlib.sha256((prepared/'runs/part1'/name).read_bytes()).hexdigest() == digest
                                            for name, digest in read('part1-checkpoint.json')['sha256'].items())
    checks['both_http_readbacks'] = all(read(f'results/prepared/runs/{part}/readback.json')['status'] == 'passed'
                                       for part in ('part1', 'part2'))
    checks['append_readback'] = read('results/prepared/runs/part2/append-readback.json')['status'] == 'passed'
    sends = [json.loads(p.read_text()) for p in prepared.glob('runs/*/send-*.json')]
    checks['five_records_sent_once'] = len(sends) == 5 and all(s['accepted'] == 1 and s['not_attempted'] == 0
                                                            and s['status'] == 'accepted_only' for s in sends)
    context_rows = [r for part in ('part1', 'part2')
                    for r in read(f'results/prepared/runs/{part}/context-readback.json')['rows']]
    checks['three_context_records'] = len({r['event_id'] for r in context_rows}) == len(context_rows) == 3
    checks['no_inflight'] = (all(t['state'] in {'completed', 'skipped', 'merged'} and t['ended_at'] for t in final['analysis_tasks'])
                             and all(a['local_state'] == 'ended' and a['local_ended_at'] for a in final['analysis_attempts'])
                             and all(r['state'] == 'completed' and r['ended_at'] for r in final['runs']))
    timeline = [(stamp(a['started_at']), 1) for a in final['analysis_attempts']]
    timeline += [(stamp(a['local_ended_at']), -1) for a in final['analysis_attempts'] if a['local_ended_at']]
    current = peak = 0
    for _, delta in sorted(timeline):
        current += delta
        peak = max(peak, current)
    checks['actual_attempts_never_overlap'] = peak == 1 and current == 0
    cid = final['cases'][0]['id']
    runs = sorted((r for r in final['runs'] if r['case_id'] == cid), key=lambda r: stamp(r['started_at']))
    results = {r['source_run_id']: r for r in final['results']}
    checks['two_case_rounds_and_results'] = len(runs) == len(results) == 2
    checks['r2_compares_real_r1'] = (len(runs) == 2 and runs[1]['comparison_result_id'] == results[runs[0]['id']]['id']
        and any(a['run_id'] == runs[1]['id'] and a['previous_run_id'] == runs[0]['id']
                and a['comparison_result_id'] == results[runs[0]['id']]['id'] for a in final['analysis_attempts']))
    checks['frozen_scope_one_to_two'] = [sum(m['run_id'] == r['id'] for m in final['run_members']) for r in runs] == [1, 2]
    forbidden = ['tenant_uid', 'tenant_id', 'telemetry-channel-02', session['execution']['execution_id'],
                 '34411091-9934-5a5e-b116-3868e76a90cd', 'test_batch', 'expected_verdict']
    requests, leaks, output_checks, query_results = [], [], [], []
    steps = {s['id']: s for s in final['run_steps']}
    for artifact in final['artifacts']:
        content = artifact.get('content_json') or {}
        stage = steps.get(artifact['step_id'], {}).get('stage_code')
        if artifact['kind'] == 'model_request':
            body = (content.get('payload') or content).get('body', {})
            text = json.dumps(body.get('messages', []), ensure_ascii=False)
            hits = [marker for marker in forbidden if marker in text]
            if hits:
                leaks.append({'request_id': artifact['id'], 'markers': hits})
            requests.append({'id': artifact['id'], 'run_id': artifact['run_id'], 'stage': stage,
                             'max_tokens': body.get('max_tokens')})
        if 'raw' in content and stage == 'C6':
            raw = content['raw']['choices'][0]['message']['content']
            output_checks.append(json.loads(raw)['conclusion']['text'] == results[artifact['run_id']]['conclusion'])
        if artifact['kind'] == 'tool_response' and stage == 'C4.query':
            query_results.append({'run_id': artifact['run_id'], 'tool': content.get('tool_name'),
                                  'state': content.get('state'), 'returned_rows': content.get('returned_rows'),
                                  'error': content.get('error')})
    checks['model_inputs_exclude_control_identity'] = not leaks
    checks['actual_request_output_limits'] = all(x['max_tokens'] == (16384 if x['stage'] in {'C3', 'C6'} else 8192) for x in requests)
    checks['c6_original_conclusions_preserved'] = len(output_checks) == 2 and all(output_checks)
    gets = posts = 0
    http_status = Counter()
    for path in prepared.glob('runs/*/http/*.json'):
        if path.name.endswith('.intent.json'):
            continue
        row = json.loads(path.read_text())
        method = row.get('request', {}).get('method')
        gets += method == 'GET'
        posts += method == 'POST'
        http_status[row.get('response', {}).get('status', 'unknown')] += 1
    value = {'status': 'passed_for_business_flow' if all(checks.values()) else 'failed',
             'checks': checks, 'actual_peak_open_attempts': peak, 'case_id': cid,
             'incident_id': final['incidents'][0]['id'], 'case_runs': runs,
             'counts': report['counts'], 'model_requests': requests, 'model_input_leaks': leaks,
             'models': {k: report['models'][k] for k in ['request_count', 'finish_reasons', 'usage', 'cost_state']},
             'quality': report['quality'], 'step_issues': report['step_issues'], 'queries': query_results,
             'http': {'gets': gets, 'posts': posts, 'statuses': dict(http_status)},
             'unverified': ['model_body_correctness', 'natural_4h_6h_schedule', 'D5_D6_abnormal_continuation', '4b_automatic_viewer_linking']}
    with (ROOT/'final-validation.json').open('x') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
    print(json.dumps({k: value[k] for k in ['status', 'checks', 'counts', 'models', 'http']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
