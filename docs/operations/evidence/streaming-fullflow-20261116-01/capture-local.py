"""Capture the selected new identities through the existing ordinary HTTP reader."""
import json, shlex, subprocess, sys
from pathlib import Path

root = Path(__file__).resolve().parent
p = json.loads((root / 'batch/profile.json').read_text())
phase = sys.argv[1]
observed = json.loads(json.loads(sorted(root.glob('probe-observe-*.json'), key=lambda x:int(x.stem.split('-')[-1]))[-1].read_text())['stdout'])
assert observed['global_running_tasks'] == 0
cfg = dict(batch_id=p['batch_id'], tenant_id=p['tenant_id'],
           alert_ids=[r['id'] for r in observed['alerts']],
           incident_ids=[r['id'] for r in observed['incidents']],
           case_ids=[r['id'] for r in observed['cases']])
dest = root / (phase + '-pg.json')
assert not dest.exists()
code = (root / 'capture.py').read_text()
cmd = ['docker', 'exec', '-i', p['containers']['http'], 'python', '-c', code]
r = subprocess.run(['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=12', p['ssh_target'], shlex.join(cmd)], input=json.dumps(cfg), capture_output=True, text=True, timeout=55)
assert r.returncode == 0, r.stderr
body = json.loads(r.stdout)
with dest.open('x') as f: json.dump(body, f, ensure_ascii=False, indent=2)
print(json.dumps({'file':str(dest),'identity':body['identity'],'counts':body['counts']}, ensure_ascii=False))
