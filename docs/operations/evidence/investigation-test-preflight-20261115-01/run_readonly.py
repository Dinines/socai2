"""Run one reviewed T1 SSH probe and save its sanitized stdout in a NEW file."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--config', type=Path, required=True)
p.add_argument('--probe', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
if a.output.exists():
    raise SystemExit('Evidence already exists; choose a new output path')
cfg = json.loads(a.config.read_text())
result = subprocess.run([cfg['ssh_binary'], '-T', '-o', 'BatchMode=yes', '-o',
    'ConnectTimeout=' + str(cfg['connect_timeout_seconds']), cfg['target'],
    shlex.join(['python3', '-c', a.probe.read_text()])], input=json.dumps(cfg),
    capture_output=True, text=True, timeout=cfg['command_timeout_seconds'])
if result.returncode:
    # Probe exceptions never include connection secrets. Preserve class/exit without raw stderr.
    a.output.write_text(json.dumps({'state': 'probe_failed', 'returncode': result.returncode,
        'last_error': result.stderr.splitlines()[-1] if result.stderr else 'no_stderr'}, indent=2) + '\n')
    raise SystemExit('Probe failed; sanitized error saved')
data = json.loads(result.stdout)
a.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'output': str(a.output), 'observed_at': data.get('observed_at'), 'mode': data.get('mode')}, ensure_ascii=False))
