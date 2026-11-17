"""Invoke one recorded S04 dispatcher operation with the frozen candidate profile."""
import argparse
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['start', 'observe', 'stop'])
parser.add_argument('receipt')
parser.add_argument('--ingress-receipt', type=Path)
args = parser.parse_args()
folder = Path(__file__).resolve().parent
root = folder.parents[3]
v = json.loads((folder/'preflight-input-01.json').read_text())
v['action'] = args.action
v['expected_container_id'] = json.loads((folder/'preflight-01.json').read_text())['containers'][0]['id']
v['observation_script'] = (folder.parent/'streaming-case-20261115-01/observe_case.py').read_text()
if args.action == 'start':
    assert args.ingress_receipt
    raw = args.ingress_receipt.read_bytes()
    gate = json.loads(raw)
    assert gate['status'] == 'passed'
    v.update(ingress_ready=True, ingress_receipt_sha256=hashlib.sha256(raw).hexdigest())
receipt = folder/args.receipt
assert receipt.parent == folder and not receipt.exists()
result = subprocess.run(['ssh', v['config']['ssh_target'], 'python3 -c '+shlex.quote(
    (folder/'control_remote.py').read_text())], input=json.dumps(v), text=True,
    capture_output=True, timeout=65, check=False)
receipt.write_text(result.stdout)
receipt.with_suffix('.stderr.txt').write_text(result.stderr)
assert result.returncode == 0, result.stderr[:1000]
out = json.loads(result.stdout)
observation = out.get('observation')
if observation:
    old = json.loads((folder.parent/'test-streaming-case-initial-20261115-01/case-pg-01.json').read_text())
    old_ids = {task['id'] for task in old['rows']['analysis_tasks']}
    out['observation'] = {**{key: observation[key] for key in ['observed_at', 'all_terminal', 'running_attempts']},
                          'new_tasks': [task for task in observation['tasks'] if task['id'] not in old_ids
                                        and task['reason_code'] != 'closed_before_start'],
                          'running_steps': [step for step in observation['steps'] if step['state'] == 'running']}
print(json.dumps(out, ensure_ascii=False, indent=2))
