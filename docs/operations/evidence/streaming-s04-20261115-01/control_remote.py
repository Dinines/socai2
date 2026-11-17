"""Bounded S04 operations on the existing dispatcher; does not submit tasks."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

v = json.load(sys.stdin)
c = v['config']
root = Path(c['root'])


def run(args, input_text=None):
    result = subprocess.run(args, input=input_text, capture_output=True, text=True, check=False,
                            timeout=c['command_timeout_seconds'])
    if result.returncode:
        raise RuntimeError('operation failed: ' + args[1] + '; exit=' + str(result.returncode))
    return result.stdout


row = json.loads(run(['docker', 'inspect', c['container']]))[0]
assert row['Id'] == v['expected_container_id'] and row['Image'] == c['image']
for name, expected in v['expected_runtime_files'].items():
    assert hashlib.sha256((root/'analysis/config'/name).read_bytes()).hexdigest() == expected
assert v['action'] in {'start', 'observe', 'stop'}
out = {'action': v['action'], 'observed_at': datetime.now(timezone.utc).isoformat(),
       'container_id': row['Id'], 'image_id': row['Image'],
       'submitted_tasks': 0, 'kafka_messages_sent': 0}
if v['action'] == 'start':
    assert v['ingress_ready'] and v['ingress_receipt_sha256']
    assert not row['State']['Running'] and row['State']['ExitCode'] == 0
    assert not any('analysis_dispatch_runtime' in item.get('Command', '') for item in
                   (json.loads(line) for line in run(
                       ['docker', 'ps', '--no-trunc', '--format', '{{json .}}']).splitlines()))
    run(['docker', 'start', c['container']])
    out['ingress_receipt_sha256'] = v['ingress_receipt_sha256']
else:
    assert row['State']['Running']
    raw = run(['docker', 'exec', '-i', c['container'], 'python', '-'], v['observation_script'])
    out['observation'] = json.loads(raw.splitlines()[-1])
    if v['action'] == 'stop':
        assert out['observation']['all_terminal'] and out['observation']['running_attempts'] == 0
        run(['docker', 'stop', '--time', str(c['stop_timeout_seconds']), c['container']])
row = json.loads(run(['docker', 'inspect', c['container']]))[0]
out.update(state=row['State']['Status'], exit_code=row['State']['ExitCode'],
           started_at=row['State']['StartedAt'], finished_at=row['State']['FinishedAt'])
if v['action'] == 'stop':
    assert not row['State']['Running'] and row['State']['ExitCode'] == 0
out['status'] = 'passed'
print(json.dumps(out, indent=2))
