"""Capture once after stop, then retrieve that same immutable snapshot."""
import json
import shlex
import subprocess
from pathlib import Path

folder = Path(__file__).resolve().parent
config = json.loads((folder/'control-config.json').read_text())
c = config['config']
destination = c['root']+'/analysis/evidence/'+config['batch_id']
files = {name: (folder/name).read_text() for name in (
    'analysis-capture.py', 'analysis-remote.py', 'capture-config.json', 'capture-runtime.json')}
source = """import json,subprocess,sys
from pathlib import Path
v=json.load(sys.stdin)
folder=Path(v['folder'])
for name,body in v['files'].items():
    with (folder/name).open('x') as stream: stream.write(body)
subprocess.run(['python3',str(folder/'analysis-remote.py')],check=True)
"""
ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', c['ssh_target']]
result = subprocess.run([*ssh, 'python3 -c '+shlex.quote(source)],
                        input=json.dumps({'folder': destination, 'files': files}),
                        capture_output=True, text=True, timeout=90, check=False)
with (folder/'capture-invocation.json').open('x') as stream:
    json.dump({'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}, stream, indent=2)
assert result.returncode == 0, result.stderr
for name in ('analysis-pg-01.json', 'analysis-capture-invocation-01.json'):
    result = subprocess.run([*ssh, 'cat '+shlex.quote(destination+'/'+name)], capture_output=True, timeout=90, check=True)
    with (folder/name).open('xb') as stream:
        stream.write(result.stdout)
print((folder/'analysis-capture-invocation-01.json').read_text())
