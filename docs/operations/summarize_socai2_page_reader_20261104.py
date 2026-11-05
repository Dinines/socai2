"""Freeze page-reader evidence, retaining failed fixtures and reused checks."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = [
    'docs/operations/evidence/socai2-page-reader-20261104/20261104T040213/receipt.json',
    'docs/operations/evidence/socai2-page-reader-20261104/20261104T040340/receipt.json',
    'docs/operations/evidence/socai2-page-reader-20261104/20261104T040605/receipt.json',
    'docs/operations/evidence/socai2-stage-reader-20261104/20261104T040734/receipt.json',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    latest, failures, receipts, hashes = {}, [], [], {}
    for name in RECEIPTS:
        p = ROOT / name
        data = json.loads(p.read_text(encoding='utf-8'))
        assert data['synthetic_only'] and data['database'] == 'socai2_schema_review_20261103_a1'
        assert any(r['name'] == 'restricted_test_role_and_tunnel_removed' and r['passed'] for r in data['observations'])
        receipts.append({'path': name, 'sha256': sha(p)})
        hashes.update({k.replace('\\', '/'): v for k, v in data['hashes'].items()})
        for row in data['observations']:
            if row['name'].startswith('test_'):
                latest[row['name']] = {'passed': row['passed'], 'receipt': name}
                if not row['passed']:
                    failures.append({'name': row['name'], 'receipt': name, 'detail': row['detail']})
    assert len(latest) == 10 and all(r['passed'] for r in latest.values()) and len(failures) == 5
    for path, fingerprint in hashes.items():
        assert sha(ROOT / path) == fingerprint, path
    prior = json.loads((ROOT/'docs/operations/socai2-incident-diagnosis-20261104.json').read_text(encoding='utf-8'))
    stable = ['services/api/app/models/socai2.py', 'services/api/app/socai2/enums.py',
        'services/api/app/socai2/contracts.schema.json', 'services/api/migrations/123_socai2_page_data_model.sql']
    old = {**prior['tested_hashes'], **prior['document_and_contract_hashes']}
    for name in stable:
        assert sha(ROOT/name) == old[name]
    documents = ['docs/investigation/socai2-page-reader-20261104.md', 'docs/design/socai2-page-reader-v1.openapi.json',
        'docs/architecture/investigation-planning-design.md', 'docs/design/socai2-schema-implementation-20261103.md',
        'docs/design/investigation-design-current-gap-review-20261103.md',
        'docs/design/alert-incident-case-product-requirements.md', 'docs/design/alert-ui-data-contract.md',
        'docs/design/incident-alert-data-showcase.md', 'prototypes/security-pages-v2/app.js']
    result = {'date': '2026-11-04', 'branch': 'codex/case-baseline-history-20261103', 'root': 'E:/aisoc/socai2',
        'change': 'complete-socai2-investigation-chain', 'task': '3.3', 'new_pg_methods': 8, 'regression_pg_methods': 2,
        'latest_pg_results': latest, 'preserved_failures': failures, 'receipts': receipts,
        'failure_summary': 'Fixture/expectation only: numeric scale text, missing object source_path, response reference source shape, existing other-tenant test data, missing step stage_code. Five targeted passes after corrections. Later three affected views plus one new statistics check passed after typed derived fields, triage validity and prototype unassigned-count alignment.',
        'local_regression': {'command': '.venv/Scripts/python.exe -m pytest services/api/tests/test_socai2_case_ai_reserved.py -q -p no:cacheprovider',
            'observed_tool_chunk': '099af1', 'stdout_summary': '3 passed, 18 subtests passed in 1.37s', 'exit_code': 0,
            'test_sha256': sha(ROOT/'services/api/tests/test_socai2_case_ai_reserved.py'),
            'route_sha256': sha(ROOT/'services/api/app/api/v1/endpoints/socai2_case_ai.py')},
        'static_initial_findings': ['imports and unused names in new files corrected',
            'pre-existing core/config.py I001, S110, BLE001 outside changed setting retained'],
        'validation_boundary': {'existing_isolated_pg': True, 'model_calls': 0, 'external_source_calls': 0,
            'identity': 'substitute', 'assets': 'existing public.assets synthetic fixture only',
            'test_roles_and_tunnels_cleaned': 4, 'new_tables_or_containers': False, 'schema_tables': 29, 'schema_columns': 458,
            'page_changed': False, 'production_switched': False, 'commit_push_deploy': False, 'old_r13': 'paused; 5.3 incomplete'},
        'latest_tested_hashes': hashes, 'unchanged_contract_hashes': {name: sha(ROOT/name) for name in stable},
        'document_hashes': {name: sha(ROOT/name) for name in documents},
        'next': '3.4 explicit incident/Case link and move transactions; H, external statuses/sources, production migration and real quality remain. Q deferred.'}
    path = ROOT/'docs/operations/socai2-page-reader-20261104.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'summary': str(path), 'latest_pg_passed': len(latest), 'local_regression_methods': 3,
        'preserved_failures': len(failures), 'fixed_receipts': len(receipts)}))


if __name__ == '__main__':
    main()
