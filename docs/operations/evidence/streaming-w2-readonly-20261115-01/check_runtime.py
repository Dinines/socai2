"""Read only the candidate containers/configs needed for W2 provenance."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

v = json.load(sys.stdin)
rows = json.loads(subprocess.run(['docker', 'inspect', *v['containers']], check=True,
    capture_output=True, text=True, timeout=v['timeout_seconds']).stdout)
by_name = {row['Name'].lstrip('/'): row for row in rows}
for name, expected in v['containers'].items():
    row = by_name[name]
    assert row['State']['Running'] == expected['running'], name
    if 'image' in expected:
        assert row['Image'] == expected['image'], name
    if name == v['dispatcher']:
        assert row['State']['ExitCode'] == 0
hashes = {name: hashlib.sha256((Path(v['runtime_directory'])/name).read_bytes()).hexdigest()
          for name in v['runtime_files']}
assert hashes == v['runtime_files']
print(json.dumps({'status': 'passed', 'observed_at': datetime.now(timezone.utc).isoformat(),
    'candidate_id': v['candidate_id'], 'runtime_files': hashes,
    'containers': [{'name': row['Name'].lstrip('/'), 'id': row['Id'], 'image': row['Image'],
                    'state': row['State']['Status'], 'exit_code': row['State']['ExitCode']}
                   for row in rows],
    'http_requests': 0, 'database_queries': 0, 'model_calls': 0,
    'kafka_messages': 0, 'service_mutations': 0}, indent=2))
