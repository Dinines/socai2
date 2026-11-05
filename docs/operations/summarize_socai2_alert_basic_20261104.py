"""Summarize fixed A executor receipts without rerunning or rewriting them."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = [
    'docs/operations/evidence/socai2-alert-basic-20261104/20261104T025541/receipt.json',
    'docs/operations/evidence/socai2-alert-basic-20261104/20261104T025629/receipt.json',
    'docs/operations/evidence/socai2-alert-basic-20261104/20261104T025945/receipt.json',
    'docs/operations/evidence/socai2-stage-results-20261104/20261104T030024/receipt.json',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    latest, failures, receipts = {}, [], []
    for name in RECEIPTS:
        p = ROOT / name
        r = json.loads(p.read_text(encoding='utf-8'))
        assert r['database'] == 'socai2_schema_review_20261103_a1' and r['synthetic_only']
        assert any(x['name'] == 'restricted_test_role_and_tunnel_removed' and x['passed'] for x in r['observations'])
        receipts.append({'path': name, 'sha256': sha(p)})
        for row in r['observations']:
            if row['name'].startswith('test_'):
                latest[row['name']] = {'passed': row['passed'], 'receipt': name}
                if not row['passed']:
                    failures.append({'name': row['name'], 'receipt': name, 'detail': row['detail']})
    assert len(latest) == 14 and all(x['passed'] for x in latest.values())
    assert len(failures) == 10
    paths = ['services/api/app/socai2/' + name for name in (
        'alert_basic_contract.py', 'alert_basic_executor.py', 'stage_results.py', 'stage_result_contracts.py',
        'stage_inputs.py', 'baseline_enrichment_sources.py', 'baseline_analysis_model.py', 'baseline_model_view.py',
        'contracts.schema.json')]
    paths += ['services/api/tests/test_socai2_alert_basic_executor.py', 'docs/operations/verify_socai2_store_20261103.py',
        'services/api/migrations/123_socai2_page_data_model.sql', 'services/api/app/models/socai2.py',
        'services/api/app/socai2/enums.py', 'docs/investigation/socai2-alert-basic-executor-20261104.md',
        'docs/design/socai2-alert-basic-answer-v1.schema.json', 'docs/architecture/investigation-planning-design.md',
        'docs/design/investigation-design-current-gap-review-20261103.md', 'docs/design/socai2-schema-implementation-20261103.md']
    assert sha(ROOT/'services/api/migrations/123_socai2_page_data_model.sql') == 'ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da'
    result = {'date': '2026-11-04', 'branch': 'codex/case-baseline-history-20261103', 'root': 'E:/aisoc/socai2',
        'change': 'complete-socai2-investigation-chain', 'task': '3.1', 'new_tests': 9, 'regressions': 5,
        'latest_results': latest, 'preserved_failures': failures, 'receipts': receipts,
        'failure_summary': '9 initial synthetic tenant transaction RLS failures; then 1 multi-run harness timeout. Fixture and harness corrected; 3 targeted tests passed after path guard/omission adjustment. Business 120s/call/token limits unchanged.',
        'static_pretest_fixes': ['two extra closing parentheses', 'one unused test import'],
        'validation_boundary': {'database': 'existing isolated synthetic PostgreSQL', 'source_sql': ['assets', 'history', 'threat_intel'],
            'model': 'substitute only', 'unavailable_asset_error': 'substitute in one check',
            'test_roles_and_tunnels_cleaned': 4, 'real_model_calls': 0, 'production_switched': False,
            'new_container_or_ddl': False, 'commit_push_deploy': False, 'schema_tables': 29, 'schema_columns': 458,
            'old_r13': 'paused; 5.3 incomplete'},
        'current_hashes': {name: sha(ROOT/name) for name in paths},
        'next': '3.2 incident diagnosis executor; complete DTOs, incident/Case relationships, H, external sources and real validation remain. Q implementation deferred.'}
    p = ROOT/'docs/operations/socai2-alert-basic-20261104.json'
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'summary': str(p), 'latest_passed': len(latest), 'preserved_failures': len(failures), 'receipts': len(receipts)}))


if __name__ == '__main__':
    main()
