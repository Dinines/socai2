"""Stop this candidate after a fresh observation found no remaining work or active attempt."""
import json
import subprocess
import sys
from datetime import datetime, timezone

v = json.load(sys.stdin)
c, observation = v['config'], v['observation']
assert observation['all_terminal'] and observation['running_attempts'] == 0


def run(args):
    return subprocess.run(args, capture_output=True, text=True, check=True,
                          timeout=c['command_timeout_seconds']).stdout


before = json.loads(run(['docker', 'inspect', c['container']]))[0]
assert before['Image'] == c['image'] and before['State']['Running']
run(['docker', 'stop', '--time', str(c['stop_timeout_seconds']), c['container']])
after = json.loads(run(['docker', 'inspect', c['container']]))[0]
print(json.dumps({'observed_at': datetime.now(timezone.utc).isoformat(), 'status': 'stopped_after_terminal',
    'container_id': after['Id'], 'image': after['Image'], 'exit_code': after['State']['ExitCode'],
    'state': after['State']['Status'], 'task_observation_at': observation['observed_at'],
    'running_attempts_before_stop': observation['running_attempts'], 'business_records_rewritten': False}, indent=2))
