"""Start Case dispatch once, retaining the completed A/I container as history."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

v = json.load(sys.stdin)
c = v['config']
root = Path(c['root'])
assert v['source_ready'] and v['preflight_passed']
for name, expected in v['runtime_files'].items():
    assert hashlib.sha256((root/'analysis/config'/name).read_bytes()).hexdigest() == expected


def run(args):
    return subprocess.run(args, capture_output=True, text=True, check=True,
                          timeout=c['command_timeout_seconds']).stdout


names = run(['docker', 'ps', '-a', '--format', '{{.Names}}']).splitlines()
assert c['previous_container'] not in names
old = json.loads(run(['docker', 'inspect', c['container']]))[0]
assert not old['State']['Running'] and old['State']['ExitCode'] == 0 and old['Image'] == c['image']
run(['docker', 'rename', c['container'], c['previous_container']])
base = json.loads((root/'analysis/docker-base.json').read_text())
container_id = run([*base, '-d', '--name', c['container'], '--restart', 'no', '--entrypoint', 'python', c['image'],
                   '-m', 'app.socai2.analysis_dispatch_runtime', '--profile', '/run/analysis/dispatcher.json']).strip()
row = json.loads(run(['docker', 'inspect', c['container']]))[0]
assert row['Image'] == c['image']
print(json.dumps({'status': 'started_awaiting_execution', 'observed_at': datetime.now(timezone.utc).isoformat(),
                  'container_id': container_id, 'image_id': row['Image'], 'state': row['State']['Status'],
                  'pid': row['State']['Pid'], 'entrypoint': row['Config']['Entrypoint'], 'command': row['Config']['Cmd'],
                  'sources_receipt_sha256': v['sources_receipt_sha256'],
                  'preflight_sha256': v['preflight_sha256'], 'kafka_messages_sent': 0, 'cases_created': 0}, indent=2))
