"""Run one recorded W4 operation through the configured SSH entry; no retries."""
import argparse
import base64
import hashlib
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['prepare', 'validate'])
args = parser.parse_args()
folder = Path(__file__).resolve().parent
value = json.loads((folder/'remote-runtime.json').read_text())
if args.action == 'prepare':
    value['uploads'] = {}
    for name, path in [('release.tar.gz', value['release_archive']), ('state.tar.gz', str(folder/'state.tar.gz'))]:
        data = Path(path).read_bytes()
        value['uploads'][name] = {'sha256': hashlib.sha256(data).hexdigest(),
                                'base64': base64.b64encode(data).decode()}
receipt = folder/(args.action+'-remote-01.json')
assert not receipt.exists()
intent = {'action': args.action, 'started_at': datetime.now(timezone.utc).isoformat(), 'automatic_retry': False}
intent_file = receipt.with_suffix('.invocation.json')
with intent_file.open('x') as stream:
    json.dump(intent, stream)
code = (folder/(args.action+'_remote.py')).read_text()
result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
    value['candidate']['ssh_target'], 'python3 -c '+shlex.quote(code)], input=json.dumps(value),
    capture_output=True, text=True, timeout=value['build']['image']['build_timeout_seconds']+60, check=False)
receipt.write_text(result.stdout)
receipt.with_suffix('.stderr.txt').write_text(result.stderr)
intent.update(returncode=result.returncode, ended_at=datetime.now(timezone.utc).isoformat())
intent_file.write_text(json.dumps(intent, indent=2)+'\n')
assert result.returncode == 0, result.stderr[-1800:]
print(result.stdout)
