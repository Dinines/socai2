"""Final bounded preservation check for this release's services, ledger and session."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

c = CONFIG
root = Path(c['remote_root'])
deployed = json.loads((root / 'deployment-ready.json').read_text())

def run(args):
    return subprocess.check_output(args, text=True, timeout=c['command_timeout_seconds'])

def inspect(name):
    d = json.loads(run(['docker', 'inspect', name]))[0]
    return {'id': d['Id'], 'image': d['Image'], 'running': d['State']['Running'],
            'started_at': d['State']['StartedAt'], 'restart_count': d['RestartCount'],
            'mounts': d['Mounts'], 'ports': d['NetworkSettings']['Ports']}

def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file()}

core = {name: inspect(name) for name in c['core_containers']}
for name, item in core.items():
    assert item['running']
    assert all(item[k] == INPUT['core'][name][k] for k in item)
current = inspect(c['container'])
assert current == deployed['container']
assert not inspect(c['old_container'])['running']
ledger = hashes(Path(c['state_root']))
assert ledger == INPUT['ledger_sha256']
prepared = Path(INPUT['acceptance_mounts']['ACCEPTANCE_RESULTS_DIR']) / 'prepared'
source_hashes = hashes(prepared)
assert source_hashes == INPUT['prepared_files']
assert hashlib.sha256((prepared / 'session.json').read_bytes()).hexdigest() == INPUT['prepared_sha256']
code = """import json,re,sys,subprocess
from pathlib import Path
from importlib.metadata import version
cfg=json.loads(Path('deploy/investigation-test/acceptance-image.json').read_text())
assert sys.version.split()[0]==cfg['python_version']
pins=dict(re.findall(r'^([A-Za-z0-9_-]+)==([^ \\n]+)',Path(cfg['requirements']).read_text(),re.M))
actual={name:version(name) for name in pins}
assert actual==pins
check=subprocess.run([sys.executable,'-m','pip','check'],text=True,capture_output=True)
assert check.returncode==0,check.stdout
print(json.dumps({'python':sys.version.split()[0],'locked_versions':actual,'pip_check':check.stdout.strip()}))
"""
deps = json.loads(run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--user', c['user'],
                       '--entrypoint', 'python', c['acceptance_image'], '-c', code]))
assert len(deps['locked_versions']) == 19
out = {'status': 'passed', 'observed_at': datetime.now(timezone.utc).isoformat(),
       'container': current, 'core': core, 'old_viewer_stopped_and_preserved': True,
       'ledger_sha256': ledger, 'prepared_file_count': len(source_hashes), 'prepared_files_unchanged': True,
       'dependency_runtime': deps, 'business_posts': 0, 'model_calls': 0}
(root / 'final-preservation.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(out, ensure_ascii=False))
