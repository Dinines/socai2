"""Record one W5 installation attempt and capture its actual receipt."""
import base64
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

p = Path(__file__).resolve().parent
repo = p.parents[3]
profile = json.loads((repo/'deploy/investigation-test/release-4177.json').read_text())
build = json.loads((repo/'deploy/investigation-test/package-build.json').read_text())
receipt = json.loads((p/'build-01.json').read_text())
v = {'profile': profile, 'build': build, 'baseline': json.loads((p/'preflight.json').read_text()),
     'archive_sha256': receipt['archive_sha256'], 'service_version': receipt['service_version']}
(p/'runtime.json').write_text(json.dumps(v, indent=2)+'\n')
intent = {'started_at': datetime.now(timezone.utc).isoformat(), 'automatic_retry': False}
with (p/'deployment-01.invocation.json').open('x') as stream:
    json.dump(intent, stream)
v['upload'] = base64.b64encode(Path(receipt['archive']).read_bytes()).decode()
result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', profile['ssh_target'],
    'python3 -c '+shlex.quote((p/'deploy_remote.py').read_text())], input=json.dumps(v),
    capture_output=True, text=True, timeout=build['image']['build_timeout_seconds']+60, check=False)
(p/'deployment-01.json').write_text(result.stdout)
(p/'deployment-01.stderr.txt').write_text(result.stderr)
intent.update(returncode=result.returncode, ended_at=datetime.now(timezone.utc).isoformat())
(p/'deployment-01.invocation.json').write_text(json.dumps(intent, indent=2)+'\n')
assert result.returncode == 0, result.stderr[-1800:]
print(result.stdout)
