"""SSH-side read-only ClickHouse HTTP transport; credentials stay on 21."""
import base64
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

request = json.load(sys.stdin)
cfg = request['source']
env = dict(line.split('=', 1) for line in Path(cfg['runtime_env_file']).read_text().splitlines()
           if line and not line.startswith('#'))
assert env['CLICKHOUSE_HOST'] == cfg['expected_host']
assert env['CLICKHOUSE_DATABASE'] == env['SOCAI2_LAKE_DATABASE'] == cfg['database']
assert env['CLICKHOUSE_USER'] == cfg['user']
sql = request['sql']
assert sql.startswith('SELECT ') and ';' not in sql and sql.endswith(' FORMAT JSON')
auth = base64.b64encode((env['CLICKHOUSE_USER'] + ':' + env['CLICKHOUSE_PASSWORD']).encode()).decode()
options = {'readonly': 1, 'max_execution_time': cfg['timeout_seconds']}
if request.get('query_id'):
    options.update(query_id=request['query_id'], max_result_rows=cfg['query_read_limit'] + 1)
url = 'http://' + cfg['expected_host'] + ':' + str(cfg['http_port']) + '/?' + urlencode(options)
wire = urllib.request.Request(url, data=sql.encode(), headers={'Authorization': 'Basic ' + auth}, method='POST')
try:
    with urllib.request.urlopen(wire, timeout=cfg['timeout_seconds']) as response:
        payload = json.load(response)
    print(json.dumps({'state': 'response_received', 'payload': payload}))
except (OSError, ValueError) as exc:
    print(json.dumps({'state': 'unknown', 'exception_type': type(exc).__name__}))
