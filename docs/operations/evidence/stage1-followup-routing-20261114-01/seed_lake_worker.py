"""One authorized synthetic lake insert; exact ID reads, no replay on uncertainty."""
import base64
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

request = json.load(sys.stdin)
plan, action = request['plan'], request['action']
cfg = plan['source']
rows = [packet['row'] for packet in plan['rows']]
assert len(rows) == 6 and len({r['event_id'] for r in rows}) == 6
assert all(r['tenant_id'] == cfg['tenant_id'] and r['src_hostname'] == cfg['hostname']
           and r['connector_type'] == cfg['synthetic_connector'] for r in rows)
reader = dict(line.split('=', 1) for line in Path(cfg['runtime_env_file']).read_text().splitlines()
              if line and not line.startswith('#'))
assert reader['CLICKHOUSE_USER'] == cfg['user'] and reader['CLICKHOUSE_DATABASE'] == cfg['database']
ids = ','.join("'" + row['event_id'] + "'" for row in rows)
columns = ','.join(rows[0])
query = (f"SELECT {columns} FROM {cfg['database']}.raw_events WHERE tenant_id=toUUID('{cfg['tenant_id']}') "
         f"AND event_id IN ({ids}) ORDER BY event_id FORMAT JSON")


def execute(env, payload, *, readonly):
    options = {'readonly': int(readonly), 'max_execution_time': cfg['timeout_seconds']}
    url = 'http://' + cfg['expected_host'] + ':' + str(cfg['http_port']) + '/?' + urlencode(options)
    auth = base64.b64encode((env['CLICKHOUSE_USER'] + ':' + env['CLICKHOUSE_PASSWORD']).encode()).decode()
    wire = urllib.request.Request(url, data=payload.encode(), headers={'Authorization': 'Basic ' + auth}, method='POST')
    with urllib.request.urlopen(wire, timeout=cfg['timeout_seconds']) as response:
        return response.read().decode()


before = json.loads(execute(reader, query, readonly=True))
if action == 'read':
    print(json.dumps({'state': 'read_only', 'snapshot': before}))
else:
    assert action == 'insert' and before['rows'] == 0, 'existing_ids_no_replay'
    result = subprocess.run(['docker', 'inspect', cfg['writer_container']], capture_output=True, text=True, check=True)
    writer = dict(item.split('=', 1) for item in json.loads(result.stdout)[0]['Config']['Env'] if '=' in item)
    assert writer['CLICKHOUSE_HOST'] == cfg['expected_host'] and writer['CLICKHOUSE_DATABASE'] == cfg['database']
    assert writer['CLICKHOUSE_USER'] == cfg['writer_user']
    body = f"INSERT INTO {cfg['database']}.raw_events ({columns}) FORMAT JSONEachRow\n"
    body += '\n'.join(json.dumps(row, ensure_ascii=False) for row in rows)
    execute(writer, body, readonly=False)
    after = json.loads(execute(reader, query, readonly=True))
    assert after['rows'] == len(rows)
    expected = {r['event_id']: r for r in rows}
    for row in after['data']:
        original = expected[row['event_id']]
        assert all(row[key] == original[key] for key in ('ocsf_json', 'raw_payload', 'src_hostname', 'class_uid', 'connector_type'))
    print(json.dumps({'state': 'inserted_and_read_back', 'inserted': len(rows), 'before': before, 'after': after}))
