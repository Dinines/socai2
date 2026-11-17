"""Read-only, metadata/count inventory for this deployment's explicit cleanup scope."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

c = json.load(sys.stdin)


def call(args, body=None):
    result = subprocess.run(args, input=body, capture_output=True, timeout=55)
    if result.returncode:
        raise RuntimeError('inventory_command_failed:' + args[0] + ':' + str(result.returncode))
    return result.stdout


p = c['postgres']
psql = ['docker', 'exec', '-i', p['container'], 'psql', '-wXAtq', '-v', 'ON_ERROR_STOP=1',
        '-U', p['role'], '-d', p['database']]


def query(sql):
    return call(psql, ('BEGIN READ ONLY;' + sql + ';COMMIT;').encode()).decode().strip()


tables = json.loads(query("SELECT json_agg(json_build_object('schema',schemaname,'table',tablename)) FROM pg_tables WHERE schemaname IN ('socai2','public')"))
counts = query(' UNION ALL '.join("SELECT '" + t['schema'] + '.' + t['table'] + "',count(*) FROM \"" + t['schema'] + '\".\"' + t['table'] + '\"' for t in tables))
counts = {name: int(value) for line in counts.splitlines() for name, value in [line.rsplit('|', 1)]}
foreign = json.loads(query("SELECT coalesce(json_agg(json_build_object('table',conrelid::regclass::text,'references',confrelid::regclass::text,'definition',pg_get_constraintdef(oid))),'[]'::json) FROM pg_constraint WHERE contype='f'"))
columns = json.loads(query("SELECT json_build_object('tables',count(DISTINCT table_name),'columns',count(*)) FROM information_schema.columns WHERE table_schema='socai2'"))
result = {'postgres': {'database': p['database'], 'counts': counts, 'foreign_keys': foreign, 'socai2_shape': columns}}

k = c['kafka']
offsets = {}
for key, time in [('start', '-2'), ('end', '-1')]:
    raw = call(['docker', 'exec', k['container'], 'kafka-run-class', 'kafka.tools.GetOffsetShell',
                '--broker-list', k['bootstrap'], '--topic', k['topic_regex'], '--time', time]).decode()
    offsets[key] = {':'.join(parts[:2]): int(parts[2]) for row in raw.splitlines() if (parts := row.rsplit(':', 2))}
result['kafka'] = offsets

r = c['redis']
env = dict(item.split('=', 1) for item in json.loads(call(['docker', 'inspect', r['container']]))[0]['Config']['Env'])
redis = []
for db in r['databases']:
    args = ['docker', 'exec', '-e', 'REDISCLI_AUTH=' + env['REDIS_PASSWORD'], r['container'],
            'redis-cli', '--no-auth-warning', '-n', str(db), '--raw']
    keys = call(args + ['--scan']).decode().splitlines()
    assert not any(key.startswith(('NOAUTH', 'WRONGPASS', 'ERR')) for key in keys)
    selected = sorted(key for key in keys if any(key.startswith(prefix) for prefix in r['prefixes']))
    redis.append({'container': r['container'], 'database': db, 'total': len(keys), 'selected': selected,
                  'preserved_keys_sha256': hashlib.sha256(json.dumps(sorted(set(keys) - set(selected))).encode()).hexdigest()})
result['redis'] = redis

v = c['vector']
headers = {'api-key': Path(v['key_file']).read_text().strip()}
vectors = {}
for name in v['collections']:
    with urlopen(Request(v['url'] + '/collections/' + name, headers=headers), timeout=20) as response:
        data = json.load(response)['result']
    vectors[name] = {'points_count': data.get('points_count'), 'config_sha256': hashlib.sha256(json.dumps(data['config'], sort_keys=True).encode()).hexdigest()}
result['vectors'] = vectors

l = c['lake']
lake = {}
for table in l['tables']:
    lake[table] = int(call(['docker', 'exec', l['container'], 'clickhouse-client', '--query', 'SELECT count() FROM ' + table]))
result['lake'] = lake

root = Path(c['ledger']['root'])
result['ledger'] = {'root': str(root), 'batches': sorted(path.name for path in root.iterdir() if path.is_dir()),
                    'files': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(root.rglob('*')) if path.is_file()}}
print(json.dumps(result, ensure_ascii=False, indent=2))
