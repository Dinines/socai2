"""Dispatch the single authorized insert, retaining intent before sending."""
import argparse
import json
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['insert', 'read'])
args = parser.parse_args()
plan = json.loads((HERE / 'lake-seed-plan.json').read_text())
stamp = datetime.now(UTC).strftime('%H%M%S')
if args.action == 'insert':
    with (HERE / 'lake-insert-intent.json').open('x') as stream:
        json.dump({'event_ids': [r['event_id'] for r in plan['rows']], 'rows': 6, 'retries': 0, 'time': stamp}, stream)
worker = (HERE / 'seed_lake_worker.py').read_text()
command = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
           '-o', 'ConnectTimeout=8', plan['source']['ssh_target'], shlex.join(['python3', '-c', worker])]
result = subprocess.run(command, input=json.dumps({'plan': plan, 'action': args.action}), capture_output=True,
                        text=True, timeout=plan['source']['timeout_seconds'] * 3 + 10, check=False)
value = json.loads(result.stdout) if result.returncode == 0 else {'state': 'unknown', 'returncode': result.returncode,
                                                              'stderr': result.stderr}
with (HERE / f'lake-{args.action}-{stamp}.json').open('x') as stream:
    json.dump(value, stream, ensure_ascii=False, indent=2)
print(json.dumps({'state': value['state'], 'rows': value.get('inserted', value.get('snapshot', {}).get('rows'))}))
raise SystemExit(result.returncode)
