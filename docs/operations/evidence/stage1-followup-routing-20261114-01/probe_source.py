"""Read only a fixed synthetic exercise host/window; do not dispatch models."""
import json
import shlex
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
config = json.loads((HERE / 'config.json').read_text())
source = config['source']
sql = (f"SELECT class_uid,count() AS rows FROM {source['database']}.raw_events "
       f"WHERE tenant_id=toUUID('{source['tenant_id']}') AND src_hostname='{source['hostname']}' "
       f"AND event_time>=parseDateTime64BestEffort('{source['window_start']}') "
       f"AND event_time<parseDateTime64BestEffort('{source['window_end']}') "
       "GROUP BY class_uid ORDER BY class_uid FORMAT JSON")
worker = (HERE / 'lake_worker.py').read_text()
command = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
           '-o', 'ConnectTimeout=8', source['ssh_target'], shlex.join(['python3', '-c', worker])]
response = subprocess.run(command, input=json.dumps({'source': source, 'sql': sql}), capture_output=True,
                          text=True, timeout=source['timeout_seconds'] + 10, check=False)
assert response.returncode == 0, 'source_transport_unavailable'
result = json.loads(response.stdout)
with (HERE / 'source-probe.json').open('x') as stream:
    json.dump({'source': source, 'sql': sql, 'result': result}, stream, ensure_ascii=False, indent=2)
print(json.dumps(result))
