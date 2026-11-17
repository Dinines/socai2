"""Apply one policy and operate only the existing candidate dispatcher/incident."""
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

v = json.load(sys.stdin)
c, action = v['config'], v['action']
root = Path(c['root'])
folder = root/'analysis/evidence'/v['batch_id']
folder.mkdir(parents=True, exist_ok=True)


def run(args, source=None):
    result = subprocess.run(args, input=source, capture_output=True, text=True,
                            timeout=c['command_timeout_seconds'], check=False)
    if result.returncode:
        # A failed runtime may include credentials in exceptions: retain privately.
        failure = root/'private'/(v['batch_id']+'-'+action+'-stderr.log')
        with failure.open('x') as stream:
            stream.write(result.stderr)
        failure.chmod(0o600)
        raise RuntimeError('operation_failed_exit_'+str(result.returncode)+'; private_log='+str(failure))
    return result.stdout


def inspect():
    row = json.loads(run(['docker', 'inspect', c['container']]))[0]
    assert row['Id'] == v['expected_container_id'] and row['Image'] == c['image']
    return row


def observe(running):
    command = (['docker', 'exec', '-i', c['container'], 'python', '-'] if running else
               ['docker', 'run', '--rm', '-i', '--network', c['network'], '--user', c['user'],
                '--workdir', c['workdir'], '--env-file', c['private_runtime_path'],
                '--volumes-from', c['container'], '--entrypoint', 'python', c['image'], '-'])
    return json.loads(run(command, v['observation_script']).splitlines()[-1])


row = inspect()
expected = dict(v['expected_runtime_files'])
if action != 'apply':
    expected['investigation-policy.toml'] = v['new_policy_sha256']
for name, sha in expected.items():
    assert hashlib.sha256((root/'analysis/config'/name).read_bytes()).hexdigest() == sha, name
out = {'action': action, 'observed_at': datetime.now(timezone.utc).isoformat(),
       'container_id': row['Id'], 'image_id': row['Image'], 'kafka_messages_sent': 0}
if action == 'apply':
    assert not row['State']['Running'] and row['State']['ExitCode'] == 0
    observation = observe(False)
    assert observation['all_terminal'] and observation['running_attempts'] == 0
    out['observation'] = observation
    policy = root/'analysis/config/investigation-policy.toml'
    with (folder/'policy.before.toml').open('xb') as stream:
        stream.write(policy.read_bytes())
    assert hashlib.sha256(v['new_policy'].encode()).hexdigest() == v['new_policy_sha256']
    stat = policy.stat()
    temporary = policy.with_name(v['batch_id']+'.toml')
    with temporary.open('x') as stream:
        stream.write(v['new_policy'])
    os.chmod(temporary, stat.st_mode)
    os.chown(temporary, stat.st_uid, stat.st_gid)
    os.replace(temporary, policy)
    code = """import json
from app.socai2.runtime_policy import active_policy
p=active_policy().require_execution_profiles()
print(json.dumps({'sha256':p.sha256,'context_tokens':p.model.context_tokens,
'max_prepared_bytes':p.model.max_prepared_bytes,'outputs':dict(p.model.output_tokens),
'totals':{k:getattr(p,k).max_total_tokens for k in ('alert_basic','incident_diagnosis','case')},
'final_reserved_input_tokens':p.model.final_reserved_input_tokens}))
"""
    command = ['docker', 'run', '--rm', '-i', '--network', 'none', '--user', c['user'],
               '--workdir', c['workdir'], '--env-file', c['private_runtime_path'],
               '--volumes-from', c['container'], '--entrypoint', 'python', c['image'], '-']
    out['loaded_policy'] = json.loads(run(command, code).splitlines()[-1])
    assert out['loaded_policy']['sha256'] == v['new_policy_sha256']
    out['runtime_files'] = {name: hashlib.sha256((root/'analysis/config'/name).read_bytes()).hexdigest()
                            for name in expected}
elif action == 'submit':
    assert not row['State']['Running']
    request = {'operation_key': v['operation_key'], 'mode': 'rerun'}
    assert not (folder/'submission-response.json').exists()
    with (folder/('submission-intent-'+v['receipt_name']+'.json')).open('x') as stream:
        json.dump({'path': v['request_path'], 'request': request}, stream)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(v['api_base_url']+v['request_path'], data=json.dumps(request).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with opener.open(req, timeout=v['http_timeout_seconds']) as response:
        out['http_status'], out['receipt'] = response.status, json.load(response)
    with (folder/'submission-response.json').open('x') as stream:
        json.dump(out, stream)
    assert out['http_status'] == 202 and out['receipt']['subject_id'] == v['expected_incident_id']
    req = urllib.request.Request(v['api_base_url']+out['receipt']['status_url'])
    with opener.open(req, timeout=v['http_timeout_seconds']) as response:
        out['accepted_readback'] = json.load(response)
elif action == 'start':
    assert not row['State']['Running'] and row['State']['ExitCode'] == 0
    assert json.loads((folder/'submission-response.json').read_text())['http_status'] == 202
    assert not any('analysis_dispatch_runtime' in item.get('Command', '') for item in
                   (json.loads(line) for line in run(['docker', 'ps', '--no-trunc', '--format', '{{json .}}']).splitlines()))
    run(['docker', 'start', c['container']])
elif action in {'observe', 'stop'}:
    out['observation'] = observe(row['State']['Running'])
    if action == 'stop':
        assert out['observation']['all_terminal'] and out['observation']['running_attempts'] == 0
        run(['docker', 'stop', '--time', str(c['stop_timeout_seconds']), c['container']])
else:
    raise ValueError('unsupported_action')
row = inspect()
out.update(status='passed', state=row['State']['Status'], exit_code=row['State']['ExitCode'],
           started_at=row['State']['StartedAt'], finished_at=row['State']['FinishedAt'])
print(json.dumps(out, ensure_ascii=False, indent=2))
