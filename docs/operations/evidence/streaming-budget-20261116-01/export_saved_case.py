"""Append the updated event Case's saved two-round view, preserving prior cards."""
import hashlib
import json
import sys
from pathlib import Path

folder = Path(__file__).resolve().parent
root = folder.parents[3]
snapshot = json.loads((folder/'analysis-pg-01.json').read_text())
rows = snapshot['rows']
mapping = json.loads((folder/'actual-map.json').read_text())
cid = mapping['event_case_id']
case = next(r for r in rows['cases'] if r['id'] == cid)
run_ids = {r['id'] for r in rows['runs'] if r.get('case_id') in (None, cid)}
task_ids = {t['id'] for t in rows['analysis_tasks'] if t['subject_id'] != mapping['control_case_id']}
result_ids = {r['id'] for r in rows['results'] if r['source_run_id'] in run_ids}
data = {}
for table, values in rows.items():
    data[table] = [v for v in values if (table != 'cases' or v['id'] == cid)
                   and v.get('case_id') in (None, cid)
                   and v.get('run_id') in {None, *run_ids}
                   and v.get('source_run_id') in {None, *run_ids}
                   and v.get('subject_id') != mapping['control_case_id']
                   and (table != 'analysis_attempts' or v['task_id'] in task_ids)
                   and (table != 'result_members' or v['result_id'] in result_ids)]
out = folder/'saved-export'
destination = out/'readback/event_case'
destination.mkdir(parents=True, exist_ok=False)
raw = (json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode()
(destination/'database.json').write_bytes(raw)
plan = {'batch': folder.name, 'source_snapshot_sha256': mapping['snapshot_sha256'],
        'cases': [{'key': 'event_case', 'case_id': cid, 'title': case['title'],
                   'source': 'one_saved_real_postgres_snapshot',
                   'scope': 'four current members; initial three-member Run and failed I originals retained'}]}
(out/'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n')
(out/'readback/files.sha256.json').write_text(json.dumps({'event_case/database.json': hashlib.sha256(raw).hexdigest()}, indent=2)+'\n')
(out/'readback/summary.json').write_text(json.dumps({'snapshot': {'at': snapshot['identity']['captured_at']},
    'plan_sha256': hashlib.sha256((out/'plan.json').read_bytes()).hexdigest(),
    'source_snapshot_sha256': mapping['snapshot_sha256']}, indent=2)+'\n')
sys.path.insert(0, str(root/'docs/operations'))
import update_processing_audit as audit

previous = audit.existing(audit.OUTPUT/'index.html')
before = {str(p.relative_to(audit.OUTPUT)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (audit.OUTPUT/'cases').iterdir() if p.is_file()}
imported, total = audit.update([out], audit.OUTPUT)
after = audit.existing(audit.OUTPUT/'index.html')
assert imported == 1 and total == len(previous)+1
assert all(after[k] == v for k, v in previous.items())
assert all(hashlib.sha256((audit.OUTPUT/name).read_bytes()).hexdigest() == sha for name, sha in before.items())
receipt = {'status': 'passed', 'source_snapshot_sha256': mapping['snapshot_sha256'],
           'previous_cards_preserved': len(previous), 'previous_case_files_preserved': len(before),
           'added_cards': imported, 'total_cards': total, 'new_database_queries': 0,
           'running_4177_switched': False, 'new_model_calls': 0}
(folder/'audit-export.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt))
