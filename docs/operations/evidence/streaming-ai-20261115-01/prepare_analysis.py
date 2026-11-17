"""Prepare this candidate's explicit A/I profile and run the no-generation probe."""
import hashlib
import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

payload = json.load(sys.stdin)
c = payload['config']
root = Path(c['root'])
private = root/'private'
config_dir = root/'analysis/config'
state_dir = root/'analysis/state'
out = {'candidate_id': c['candidate_id'], 'batch_id': c['batch_id'], 'status': 'preparing',
       'started_at': datetime.now(timezone.utc).isoformat(), 'generation_calls': 0}


def save_secret(path, value, *, uid=None):
    with path.open('x') as stream:
        path.chmod(0o600)
        stream.write(value)
    if uid:
        os.chown(path, *uid)


def run(args, body=None):
    result = subprocess.run(args, input=body, text=True, capture_output=True, check=False,
                            timeout=c['command_timeout_seconds'])
    if result.returncode:
        p = private/('analysis-prepare-error-'+secrets.token_hex(4)+'.txt')
        save_secret(p, result.stderr+'\n'+result.stdout)
        raise RuntimeError('command_exit_'+str(result.returncode)+'; private_detail='+str(p))
    return result.stdout


try:
    names = run(['docker', 'ps', '-a', '--format', '{{.Names}}']).splitlines()
    assert c['container'] not in names
    assert not config_dir.exists() and not state_dir.exists()
    config_dir.mkdir(parents=True)
    state_dir.mkdir()
    uid = tuple(int(x) for x in c['user'].split(':'))
    os.chown(state_dir, *uid)
    for name, content in payload['files'].items():
        assert Path(name).name == name
        (config_dir/name).write_text(content)
    (config_dir/'deployment.json').write_text(json.dumps(c, indent=2)+'\n')
    source_env = dict(line.split('=', 1) for line in Path(c['private_model_source']).read_text().splitlines()
                      if line and not line.startswith('#') and '=' in line)
    http = json.loads(Path(c['private_http_source']).read_text())
    db_url = http['SOCAI2_CASE_DATABASE_URL']
    assert urlsplit(db_url).path == '/'+c['database'] and urlsplit(db_url).username == c['writer']
    parts = urlsplit(db_url)
    params = [(k, v) for k, v in parse_qsl(parts.query) if k not in {'sslmode', 'channel_binding'}]
    db_url = urlunsplit((c['database_driver'], parts.netloc, parts.path, urlencode(params), parts.fragment))
    redis_secret = json.loads(Path(c['private_redis_source']).read_text())['password']
    redis_url = 'redis://:'+quote(redis_secret, safe='')+'@'+c['redis_container']+':'+str(c['redis_port'])+'/'+str(c['redis_db'])
    save_secret(private/'analysis-database-url', db_url+'\n', uid=uid)
    save_secret(private/'analysis-redis-url', redis_url+'\n', uid=uid)
    env = dict(c['runtime_env'])
    for key in ('SECRET_KEY', 'JWT_SECRET', 'METRICS_TOKEN', 'AISOC_CREDENTIAL_KEY', 'AISOC_REALTIME_JWT_SECRET'):
        assert source_env.get(key)
        env[key] = source_env[key]
    env.update(OPENAI_API_KEY=source_env[c['model_key_name']], OPENAI_MODEL=c['model_alias'],
        OPENAI_BASE_URL=c['model_base_url'], DATABASE_URL=db_url, SOCAI2_CASE_DATABASE_URL=db_url,
        REDIS_URL=redis_url, SOCAI2_KNOWLEDGE_PROFILE='')
    assert all('\n' not in value and '\r' not in value for value in env.values())
    save_secret(Path(c['private_runtime_path']), ''.join(key+'='+value+'\n' for key,value in sorted(env.items())))
    base = ['docker', 'run', '--network', c['network'], '--workdir', c['workdir'], '--user', c['user'],
        '--memory', c['memory'], '--pids-limit', str(c['pids_limit']), '--env-file', c['private_runtime_path'],
        '--mount', 'type=bind,src='+str(config_dir)+',dst=/run/analysis,readonly',
        '--mount', 'type=bind,src='+str(state_dir)+',dst=/var/lib/analysis',
        '--mount', 'type=bind,src='+str(private/'analysis-database-url')+',dst=/run/secrets/analysis-database-url,readonly',
        '--mount', 'type=bind,src='+str(private/'analysis-redis-url')+',dst=/run/secrets/analysis-redis-url,readonly']
    (root/'analysis/docker-base.json').write_text(json.dumps(base, indent=2)+'\n')
    probe = run([*base, '--rm', '-i', '--entrypoint', 'python', c['image'], '-'], payload['probe'])
    out['readiness'] = json.loads(probe.splitlines()[-1])
    out['config_sha256'] = hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()
    out['status'] = 'passed'
except Exception as exc:  # noqa: BLE001 -- preserve this one-shot preparation failure
    out['status'] = 'failed'
    out['error'] = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
finally:
    out['ended_at'] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(1 if out['status'] == 'failed' else 0)
