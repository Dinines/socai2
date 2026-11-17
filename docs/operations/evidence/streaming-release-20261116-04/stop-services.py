"""Stop this release's old writers after checking actual terminal state."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

c = json.load(sys.stdin)
root = Path(c['root'])
assert not (root / 'stop-services.json').exists(), 'already_stopped_read_receipt'


def run(args, body=None):
    p = subprocess.run(args, input=body, capture_output=True, timeout=55)
    assert not p.returncode, 'command_failed:' + args[0] + ':' + str(p.returncode)
    return p.stdout


def inspect(name):
    return json.loads(run(['docker', 'inspect', name]))[0]


d = c['database']
sql = ['docker', 'exec', '-i', d['container'], 'psql', '-wXAtq', '-v', 'ON_ERROR_STOP=1',
       '-U', d['admin'], '-d', d['name']]


def idle():
    body = """BEGIN READ ONLY;
SELECT json_build_object(
 'nonterminal_tasks',(SELECT count(*) FROM socai2.analysis_tasks WHERE state NOT IN ('completed','failed','skipped','merged')),
 'nonterminal_runs',(SELECT count(*) FROM socai2.runs WHERE state NOT IN ('completed','failed')),
 'open_attempts',(SELECT count(*) FROM socai2.analysis_attempts WHERE local_state!='ended'));
COMMIT;"""
    value = json.loads(run(sql, body.encode()))
    assert not any(value.values()), 'work_still_active:' + json.dumps(value)
    directory = Path(c['prior_runtime_root']) / 'analysis/state/completions'
    assert not list(directory.glob('*.json')), 'completion_receipts_pending'
    return value


before = idle()
stopped = []
for name in c['stop_before_cleanup']:
    previous = inspect(name)
    assert previous['State']['Running'], 'expected_old_service_not_running:' + name
    run(['docker', 'stop', '--time', str(c['stop_timeout_seconds']), name])
    after = inspect(name)
    assert after['Id'] == previous['Id'] and not after['State']['Running']
    stopped.append({'name': name, 'id': after['Id'], 'image': after['Image'], 'state': after['State']['Status']})
    if name == c['stop_before_cleanup'][1]:
        idle()
after = idle()
result = {'before': before, 'after': after, 'services': stopped, 'pending_completion_files': 0,
          'schema_or_data_changed': False}
with (root / 'stop-services.json').open('x') as output:
    json.dump(result, output, indent=2)
print(json.dumps(result, indent=2))
