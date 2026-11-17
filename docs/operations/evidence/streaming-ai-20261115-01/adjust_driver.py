"""Align this unstarted dispatcher with the processing image's installed asyncpg driver."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

v = json.load(sys.stdin)
c = v['config']
root = Path(c['root'])
names = subprocess.run(['docker', 'ps', '-a', '--format', '{{.Names}}'], check=True,
                       capture_output=True, text=True).stdout.splitlines()
assert c['container'] not in names
private = root/'private'
url_file = private/'analysis-database-url'
old = url_file.read_text()
backup = private/'analysis-database-url-before-driver-01'
with backup.open('x') as stream:
    backup.chmod(0o600)
    stream.write(old)
parts = urlsplit(old.strip())
params = [(k, val) for k, val in parse_qsl(parts.query) if k not in {'sslmode', 'channel_binding'}]
new = urlunsplit((c['database_driver'], parts.netloc, parts.path, urlencode(params), parts.fragment))
url_file.write_text(new+'\n')
env_path = Path(c['private_runtime_path'])
env_text = env_path.read_text()
with (private/'analysis-before-driver-01.env').open('x') as stream:
    (private/'analysis-before-driver-01.env').chmod(0o600)
    stream.write(env_text)
env_path.write_text(env_text.replace(old.strip(), new))
for name, content in v['files'].items():
    assert Path(name).name == name
    (root/'analysis/config'/name).write_text(content)
(root/'analysis/config/deployment.json').write_text(json.dumps(c, indent=2)+'\n')
base = json.loads((root/'analysis/docker-base.json').read_text())
r = subprocess.run([*base, '--rm', '-i', '--entrypoint', 'python', c['image'], '-'],
    input=v['probe'], capture_output=True, text=True, check=False, timeout=c['command_timeout_seconds'])
out = {'observed_at': datetime.now(timezone.utc).isoformat(), 'database_driver': c['database_driver'],
       'status': 'passed' if r.returncode == 0 else 'failed', 'generation_calls': 0}
if r.returncode:
    path = private/'analysis-preflight-02-error.txt'
    with path.open('x') as stream:
        path.chmod(0o600)
        stream.write(r.stderr+'\n'+r.stdout)
    out['private_error'] = str(path)
else:
    out['readiness'] = json.loads(r.stdout.splitlines()[-1])
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(r.returncode)
