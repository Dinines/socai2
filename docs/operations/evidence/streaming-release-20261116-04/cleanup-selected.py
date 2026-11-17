"""Apply the frozen user-authorized cleanup, preserving unrelated rows and schema."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

c = json.load(sys.stdin)
scope, release = c['scope'], c['release']
root = Path(scope['backup_root'])
root.mkdir(parents=True, exist_ok=False, mode=0o700)
os.chmod(root, 0o700)
for name in release['stop_before_cleanup']:
    state = json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]
    assert not state['State']['Running'], 'writer_still_running:' + name
assert not list((Path(scope['dispatcher_state_root']) / 'completions').glob('*.json'))

p = scope['postgres']
args = ['docker', 'exec', '-i', p['container'], 'psql', '-wXAtq', '-v', 'ON_ERROR_STOP=1',
        '-U', p['role'], '-d', p['database']]


def preserved():
    sql = ' UNION ALL '.join("SELECT '" + name + "',count(*),coalesce(md5(string_agg(md5(to_jsonb(t)::text),'' ORDER BY md5(to_jsonb(t)::text))),'empty') FROM " + name + ' t' for name in scope['preserved_tables'])
    result = subprocess.run(args, input=('BEGIN READ ONLY;' + sql + ';COMMIT;').encode(), capture_output=True, timeout=55)
    assert not result.returncode, 'preservation_snapshot_failed'
    return result.stdout


before = preserved()
with (root / 'preserved-tables-before.txt').open('xb') as output:
    output.write(before)
os.chmod(root / 'preserved-tables-before.txt', 0o600)
receipts = {}
for step in c['steps']:
    name = step['name']
    assert hashlib.sha256(step['script'].encode()).hexdigest() == step['script_sha256']
    result = subprocess.run(['python3', '-c', step['script']], input=json.dumps(step['config']).encode(),
                            capture_output=True, timeout=360)
    safe = {'step': name, 'exit': result.returncode, 'stdout': result.stdout.decode(),
            'stderr': result.stderr.decode()[-1500:]}
    with (root / (name + '-receipt.json')).open('x') as output:
        json.dump(safe, output, indent=2)
    os.chmod(root / (name + '-receipt.json'), 0o600)
    print(json.dumps(safe), flush=True)
    assert not result.returncode, 'cleanup_step_failed:' + name
    receipts[name] = [json.loads(line) for line in result.stdout.decode().splitlines() if line.strip()]
after = preserved()
with (root / 'preserved-tables-after.txt').open('xb') as output:
    output.write(after)
os.chmod(root / 'preserved-tables-after.txt', 0o600)
assert before == after, 'unselected_table_contents_changed'
summary = {'steps': receipts, 'preserved_tables': len(scope['preserved_tables']),
           'preserved_tables_unchanged': True, 'preservation_sha256': hashlib.sha256(after).hexdigest(),
           'backup_root': str(root), 'cleanup_scope_sha256': hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()}
with (Path(release['root']) / 'cleanup-zero.json').open('x') as output:
    json.dump(summary, output, indent=2)
print(json.dumps({'cleanup_complete': True, 'summary': summary}), flush=True)
