"""Configure the stopped candidate for Case sources; no tasks or model generation."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

v = json.load(sys.stdin)
c = v['config']
root = Path(c['root'])
private = root / 'private'
out = {'batch_id': c['batch_id'], 'started_at': datetime.now(timezone.utc).isoformat(),
       'generation_calls': 0, 'cases_created': 0}


def run(args, body=None):
    result = subprocess.run(args, input=body, capture_output=True, text=True, check=False,
                            timeout=c['command_timeout_seconds'])
    if result.returncode:
        failure = private / 'case-prepare-error-01.txt'
        with failure.open('x') as stream:
            failure.chmod(0o600)
            stream.write(result.stderr + '\n' + result.stdout)
        raise RuntimeError('command_failed; private_detail=' + str(failure))
    return result.stdout


try:
    row = json.loads(run(['docker', 'inspect', c['container']]))[0]
    assert not row['State']['Running'] and row['State']['ExitCode'] == 0 and row['Image'] == c['image']
    archive = root / 'analysis/archive-ai'
    archive.mkdir()
    shutil.copytree(root / 'analysis/config', archive / 'config')
    shutil.copyfile(root / 'analysis/docker-base.json', archive / 'docker-base.json')
    env_path = Path(c['private_runtime_path'])
    secret_backup = private / 'analysis-ai-stopped.env'
    assert not secret_backup.exists()
    shutil.copyfile(env_path, secret_backup)
    secret_backup.chmod(0o600)
    env = dict(line.split('=', 1) for line in env_path.read_text().splitlines() if line)
    ch = json.loads(Path(c['private_clickhouse_source']).read_text())
    assert ch['database'] == c['database'] and ch['reader']['user'] == c['lake_reader']
    assert ch['host'] == c['runtime_env']['CLICKHOUSE_HOST'] and str(ch['port']) == c['runtime_env']['CLICKHOUSE_PORT']
    env.update(c['runtime_env'])
    env.update(CLICKHOUSE_USER=ch['reader']['user'], CLICKHOUSE_PASSWORD=ch['reader']['password'])
    assert all('\n' not in value and '\r' not in value for value in env.values())
    env_path.write_text(''.join(key + '=' + value + '\n' for key, value in sorted(env.items())))
    env_path.chmod(0o600)
    key_path = private / 'analysis-qdrant-key'
    assert not key_path.exists()
    shutil.copyfile(c['private_knowledge_source'], key_path)
    key_path.chmod(0o400)
    os.chown(key_path, *[int(x) for x in c['user'].split(':')])
    for name, content in v['files'].items():
        assert Path(name).name == name
        (root / 'analysis/config' / name).write_text(content)
    (root / 'analysis/config/deployment.json').write_text(json.dumps(c, indent=2) + '\n')
    base_file = root / 'analysis/docker-base.json'
    base = json.loads(base_file.read_text())
    base += ['--mount', 'type=bind,src=' + str(key_path) + ',dst=/run/knowledge/qdrant-key,readonly']
    base_file.write_text(json.dumps(base, indent=2) + '\n')
    raw = run([*base, '--rm', '-i', '--entrypoint', 'python', c['image'], '-'], v['probe'])
    out['readiness'] = json.loads(raw.splitlines()[-1])
    out['config_sha256'] = hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()
    out['status'] = 'passed'
except Exception as exc:  # noqa: BLE001 -- retain bounded preparation outcome without secret traceback
    out.update(status='failed', error=str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__)
out['ended_at'] = datetime.now(timezone.utc).isoformat()
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(0 if out['status'] == 'passed' else 1)
