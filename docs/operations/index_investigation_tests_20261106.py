"""Index preserved local investigation batches without rerunning any investigation."""
import json
from collections import Counter

from audit_investigation_tests_20261106 import BASE, OUT, ROOT, read, sha


def main():
    batches, unique = [], {}
    for plan_file in sorted(BASE.glob('*/plan.json')):
        folder = plan_file.parent
        exports = sorted((folder / 'exports').glob('*/manifest.json'))
        if not exports:
            continue
        exp = exports[-1].parent
        plan, manifest, data = read(plan_file), read(exports[-1]), read(exp / 'database.json')
        for source in manifest['sources']:
            assert sha(exp / source['file']) == source['sha256'], (folder.name, source['file'])
        attempts = [s for s in data['run_steps'] if s['kind'] == 'model' and s['state'] not in ('planned', 'skipped')]
        for table, rows in data.items():
            unique.setdefault(table, {})
            for row in rows:
                key = (row['tenant_id'], row['id'])
                if key in unique[table]:
                    assert unique[table][key] == row, (table, key)
                unique[table][key] = row
        indexes = {a['id']: a for a in data['artifacts']}
        failures = []
        for step in attempts:
            if step['state'] != 'completed':
                payload = (indexes.get(step.get('output_artifact_id'), {}).get('content_json') or {})
                payload = payload.get('payload') or payload
                failures.append({'stage': step['stage_code'], 'step_id': step['id'], 'run_id': step['run_id'],
                    'state': step['state'], 'error': step.get('error'),
                    'provider_status': (payload.get('raw') or {}).get('status')})
        cas = data['cases'][0]
        assessment = next((a for a in data['case_assessments'] if a['id'] == cas['current_assessment_id']), None)
        quality = 'see_original_review_not_regraded'
        if folder.name.startswith('local-eval-20261106'):
            quality = 'see_semantic-review.json'
        elif folder.name.startswith('local-eval-20261105'):
            quality = 'quality_not_passed_see_local-comparison-summary.json'
        batches.append({'batch': folder.name, 'scenario': plan['case'].get('scenario', 'maintenance'),
            'plan': str(plan_file.relative_to(ROOT)), 'plan_sha256': sha(plan_file),
            'expected': str((folder / 'expected.json').relative_to(ROOT)),
            'expected_sha256': sha(folder / 'expected.json'),
            'selected_export': str(exp.relative_to(ROOT)), 'earlier_export_count': len(exports) - 1,
            'database_sha256': sha(exp / 'database.json'), 'manifest_sha256': sha(exp / 'manifest.json'),
            'table_counts': manifest['table_counts'], 'model_attempts': len(attempts),
            'run_states': dict(Counter(r['state'] for r in data['runs'])),
            'model_states': dict(Counter(s['state'] for s in attempts)), 'failures': failures,
            'case_id': cas['id'], 'current_assessment_at_export': assessment,
            'quality_status': quality,
            'baseline_runs': [{k: r[k] for k in ('id', 'state', 'stop_reason', 'delivery_state')} for r in data['runs'] if r['kind'] == 'baseline']})
    all_attempts = [s for s in unique['run_steps'].values() if s['kind'] == 'model' and s['state'] not in ('planned', 'skipped')]
    assert len(all_attempts) == sum(b['model_attempts'] for b in batches) == 63
    current = [read(OUT / ('local-eval-20261106-' + n + '.json')) for n in ('01', '02', '03')]
    extended = read(OUT / 'extended-readback.json')['reports']
    page = read(OUT / 'page-verification.json')
    report = {'scope': '13 preserved local model batches; latest export per batch, earlier exports retained',
        'historical_remote_results_are_separate': True,
        'batches': batches, 'unique_table_counts': {t: len(rows) for t, rows in unique.items()},
        'model_attempts': len(all_attempts), 'previous_attempts': 48, 'new_attempts': 15,
        'campaign_cap': 69, 'additional_cap': 21, 'unused_additional_attempts': 6,
        'remote_deployed_model_tested_this_campaign': False,
        'new_readback': {'http_get_count': sum(r['live_readback']['get_count'] for r in current) + sum(r['get_count'] for r in extended),
            'checks': sum(len(r['live_readback']['checks']) for r in current) + sum(len(r['checks']) for r in extended),
            'mismatches': sum(len(r['live_readback']['mismatches']) for r in current) + sum(len(r['mismatches']) for r in extended),
            'relationship_violations': sum(len(r['relationship_violations']) for r in current),
            'original_materials_exact': all(r['original_materials_exact'] and r['lake_originals_exact'] for r in current)},
        'new_page_readback': {k: page[k] for k in ('check_count', 'rendered_count', 'failure_count')},
        'browser': {'surface': 'original template, localhost:4174', 'checks': ['three current conclusions in Case list', 'three Case-info conclusions and source links', '01 saved graph 8 nodes / 6 edges', '01 AI stages C3 failed and C6 completed', '01 execution ledger 15 saved steps', '03 raw file_rename event and notes.docx.locked'], 'business_save_actions': 0},
        'data_contract_only_batch': {'batch': 'page-data-20261106T013645Z', 'cases': 4, 'alerts': 8, 'runs': 0, 'model_attempts': 0,
            'evidence': 'docs/operations/evidence/page-data-20261106/summary.json'},
        'limitations': ['snapshot aggregation is not a live current-state reread of all old Cases', 'semantic correctness is reviewed separately', 'new runs do not produce an independent evidence index', 'A/I history context shares operator-0 across prior synthetic tests', 'Case history endpoint requires separate A/I trace aggregation for original UI history count']}
    (OUT / 'test-index.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('model_attempts', 'new_attempts', 'unique_table_counts', 'new_readback', 'new_page_readback')}, ensure_ascii=False))
    for b in batches:
        a = b['current_assessment_at_export'] or {}
        print(b['batch'], b['model_attempts'], b['run_states'], a.get('origin'), a.get('validity'), [(f['stage'], (f['error'] or {}).get('code')) for f in b['failures']])


if __name__ == '__main__':
    main()
