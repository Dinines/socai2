"""One authorized batch: fixed empty graph table, exact profile, no automatic retries."""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'deploy/database'))
import install_reader

cfg = json.loads((HERE / 'profile.json').read_text())
assert json.loads((HERE / 'workbench-publication.json').read_text())['status'] == 'published'
assert json.loads((HERE / 'workbench-before-cleanup.json').read_text())['tables'] == 28
migration = ROOT / 'services/api/migrations/127_socai2_remove_unused_graph_table.sql'
assert hashlib.sha256(migration.read_bytes()).hexdigest() == json.loads((HERE / 'direct-validation.json').read_text())['migration_sha256']
inspect_sql = (HERE / 'inspect.sql').read_text()
checks = ['retained_catalog_sha256', 'retained_table_count', 'alerts', 'cases', 'runs', 'artifacts']

def execute(target, sql):
    return subprocess.run(target['command'], input=sql, text=True, capture_output=True, timeout=cfg['timeout_seconds'])

for name, target in cfg['targets'].items():
    receipt = HERE / (name + '-execution.json')
    assert not receipt.exists(), 'existing_execution_receipt_requires_manual_readback'
    assert re.fullmatch(r'[a-z_][a-z0-9_]+', target['database'])
    before = json.loads((HERE / (name + '-before.json')).read_text())
    now = execute(target, inspect_sql)
    assert now.returncode == 0, now.stderr
    current = json.loads(now.stdout)
    assert current == before, 'database_changed_since_review:' + name
    variables = '\\set expected_database ' + target['database'] + '\n'
    variables += '\\set cleanup_lock_timeout ' + str(cfg['lock_timeout_seconds']) + 's\n'
    variables += '\\set cleanup_statement_timeout ' + str(cfg['statement_timeout_seconds']) + 's\n'
    result = execute(target, variables + install_reader.render('remove_unused_graph_table.sql'))
    record = {'target': name, 'database': target['database'], 'at': datetime.now(timezone.utc).isoformat(),
              'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
              'migration_sha256': hashlib.sha256(migration.read_bytes()).hexdigest()}
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    assert result.returncode == 0, result.stderr
    final = execute(target, inspect_sql)
    assert final.returncode == 0, final.stderr
    after = json.loads(final.stdout)
    (HERE / (name + '-after.json')).write_text(json.dumps(after, indent=2) + '\n')
    assert after['socai2_tables'] == 28 and after['socai2_columns'] == 450
    assert not after['graph_exists'] and after['cleanup_recorded']
    assert all(before[k] == after[k] for k in checks), 'retained_state_changed:' + name
    print(json.dumps({'target': name, 'tables': 28, 'columns': 450, 'retained_catalog_and_business_counts_unchanged': True}), flush=True)
