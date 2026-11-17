"""Derive two readback views from the one saved PG snapshot; no live queries."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[4]
folder = Path(__file__).resolve().parent
source = root / 'docs/operations/evidence/test-streaming-case-initial-20261115-01/case-pg-01.json'
raw = source.read_bytes()
snapshot = json.loads(raw)
rows = snapshot['rows']
output = folder / 'saved-export'
assert not output.exists()
readback = output / 'readback'
readback.mkdir(parents=True)
case_ids = {case['id'] for case in rows['cases']}
plan = {'batch': 'streaming-case-20261115-01', 'source_snapshot_sha256': hashlib.sha256(raw).hexdigest(), 'cases': []}
sums = {}
for case in rows['cases']:
    cid = case['id']
    label = 'event_case' if len([a for a in rows['case_alerts'] if a['case_id'] == cid]) == 3 else 'single_A01_case'
    runs = {r['id'] for r in rows['runs'] if r.get('case_id') in (None, cid)}
    data = {}
    for name, values in rows.items():
        selected = []
        for value in values:
            if name == 'cases' and value['id'] != cid:
                continue
            if value.get('case_id') not in (None, cid):
                continue
            if value.get('run_id') and value['run_id'] not in runs:
                continue
            if value.get('source_run_id') and value['source_run_id'] not in runs:
                continue
            if value.get('subject_id') in case_ids - {cid}:
                continue
            selected.append(value)
        data[name] = selected
    destination = readback / label
    destination.mkdir()
    content = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()
    (destination / 'database.json').write_bytes(content)
    sums[label + '/database.json'] = hashlib.sha256(content).hexdigest()
    plan['cases'].append({'key': label, 'title': case['title'], 'case_id': cid,
                          'source': 'one_saved_real_postgres_snapshot',
                          'upstream_scope': 'A/I context retained with original source scope; not extra Case members'})
(output / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
(readback / 'files.sha256.json').write_text(json.dumps(sums, indent=2) + '\n')
(readback / 'summary.json').write_text(json.dumps({
    'snapshot': {'at': snapshot['identity']['captured_at']},
    'plan_sha256': hashlib.sha256((output / 'plan.json').read_bytes()).hexdigest(),
    'source_snapshot_sha256': hashlib.sha256(raw).hexdigest()}, indent=2) + '\n')
sys.path.insert(0, str(root / 'docs/operations'))
import update_processing_audit as audit

previous = audit.existing(audit.OUTPUT / 'index.html')
before = {str(file.relative_to(audit.OUTPUT)): hashlib.sha256(file.read_bytes()).hexdigest()
          for file in (audit.OUTPUT / 'cases').iterdir() if file.is_file()}
imported, total = audit.update([output], audit.OUTPUT)
after = audit.existing(audit.OUTPUT / 'index.html')
assert imported == 2 and total == len(previous) + 2
assert all(after[key] == value for key, value in previous.items())
assert all(hashlib.sha256((audit.OUTPUT / name).read_bytes()).hexdigest() == value for name, value in before.items())
receipt = {'state': 'passed', 'source_snapshot_sha256': hashlib.sha256(raw).hexdigest(),
           'existing_cards_preserved': len(previous), 'existing_case_files_unchanged': len(before),
           'added_saved_case_cards': imported, 'total_cards': total,
           'new_database_queries': 0, 'new_model_calls': 0,
           'running_4177_switched': False, 'site': str(audit.OUTPUT)}
(folder / 'audit-export-01.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
