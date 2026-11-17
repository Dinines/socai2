"""Record one operation for this budget/S04 batch; never retry a mutation."""
import argparse
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['apply', 'submit', 'start', 'observe', 'stop'])
parser.add_argument('receipt')
args = parser.parse_args()
folder = Path(__file__).resolve().parent
v = json.loads((folder/'control-config.json').read_text())
v['action'] = args.action
v['receipt_name'] = Path(args.receipt).stem
v['observation_script'] = (folder.parent/'streaming-case-20261115-01/observe_case.py').read_text()
receipt = folder/args.receipt
assert receipt.parent == folder and not receipt.exists()
intent = {'action': args.action, 'started_at': datetime.now(timezone.utc).isoformat()}
with receipt.with_suffix('.invocation.json').open('x') as stream:
    json.dump(intent, stream)
process = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', v['config']['ssh_target'],
                          'python3 -c '+shlex.quote((folder/'control_remote.py').read_text())],
                         input=json.dumps(v), text=True, capture_output=True, timeout=90, check=False)
receipt.write_text(process.stdout)
receipt.with_suffix('.stderr.txt').write_text(process.stderr)
intent.update(returncode=process.returncode, ended_at=datetime.now(timezone.utc).isoformat())
receipt.with_suffix('.invocation.json').write_text(json.dumps(intent, indent=2)+'\n')
assert process.returncode == 0, process.stderr[:1500]
out = json.loads(process.stdout)
if 'observation' in out:
    old = json.loads((folder.parent/'test-streaming-s04-20261115-01/analysis-pg-01.json').read_text())
    old_ids = {t['id'] for t in old['rows']['analysis_tasks']}
    observation = out['observation']
    out['observation'] = {**{k: observation[k] for k in ('all_terminal', 'running_attempts')},
                          'new_tasks': [t for t in observation['tasks'] if t['id'] not in old_ids],
                          'running_steps': [s for s in observation['steps'] if s['state'] == 'running']}
print(json.dumps(out, ensure_ascii=False, indent=2))
