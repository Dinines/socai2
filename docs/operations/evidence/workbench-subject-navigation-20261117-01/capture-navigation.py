"""Capture only the existing subject/run/task directories for navigation review."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

profile = json.loads(Path(sys.argv[1]).read_text())
upstream = json.loads(Path(profile['upstream_file']).read_text())
output = Path(sys.argv[2])
output.mkdir(parents=True, exist_ok=False)
responses = []


def pages(path, params=None):
    params = dict(params or {}, limit=2)
    items, seen = [], set()
    while True:
        url = path + '?' + urlencode(params)
        with urlopen(upstream['base_url'] + url, timeout=upstream['read_timeout_seconds']) as response:
            raw = response.read()
            data = json.loads(raw)
            name = f'{len(responses) + 1:03d}.json'
            (output / name).write_bytes(raw)
            responses.append({'path': url, 'status': response.status, 'file': name,
                              'sha256': hashlib.sha256(raw).hexdigest()})
        items.extend(data['items'])
        cursor = data.get('next_cursor')
        if not cursor:
            break
        if cursor in seen:
            raise ValueError('cursor repeated')
        seen.add(cursor)
        params['cursor'] = cursor
    return items


subjects, runs, tasks = [], [], []
for kind, collection, sort in [('case', 'cases', 'business_updated_at'),
                               ('incident', 'incidents', 'last_activity_at'),
                               ('alert', 'alerts', 'event_time')]:
    for row in pages('/api/v1/socai2/' + collection, {'sort_by': sort, 'sort_order': 'desc'}):
        facts = row['case' if kind == 'case' else 'facts']
        subject_id = facts['id']
        own_runs = pages('/api/v1/socai2/analysis-runs', {'subject_type': kind, 'subject_id': subject_id})
        own_tasks = pages(f'/api/v1/socai2/{collection}/{subject_id}/analysis-tasks')
        assert all(r['subject_type'] == kind and r['subject_id'] == subject_id for r in own_runs)
        subjects.append({'type': kind, 'id': subject_id, 'runs': len(own_runs), 'tasks': len(own_tasks)})
        runs.extend(own_runs)
        tasks.extend(own_tasks)

report = {'state': 'captured_read_only', 'observed_at': datetime.now(timezone.utc).isoformat(),
          'environment': upstream['environment_label'], 'subjects': subjects,
          'run_ids': [r['run_id'] for r in runs], 'task_ids': [t['task_id'] for t in tasks],
          'active_tasks': [t['task_id'] for t in tasks if t['status'] in ('accepted', 'running')],
          'skipped_tasks': [{'task_id': t['task_id'], 'reason_code': t['reason_code'],
                             'latest_run_id': t['latest_run_id']} for t in tasks if t['status'] == 'skipped'],
          'responses': responses, 'http_get_count': len(responses),
          'business_writes': 0, 'model_calls': 0}
(output / 'index.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ('state', 'subjects', 'active_tasks', 'skipped_tasks', 'http_get_count')}, ensure_ascii=False))
