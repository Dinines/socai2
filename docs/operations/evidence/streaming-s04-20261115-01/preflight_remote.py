"""Read current candidate config and Redis correlation; no writes or model calls."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

v = json.load(sys.stdin)
c = v['config']
root = Path(c['root'])


def run(args, input_text=None):
    return subprocess.run(args, input=input_text, capture_output=True, text=True,
                          check=True, timeout=c['command_timeout_seconds']).stdout


config_hashes = {name: hashlib.sha256((root/'analysis/config'/name).read_bytes()).hexdigest()
                 for name in v['expected_runtime_files']}
assert config_hashes == v['expected_runtime_files'], 'runtime config changed'
names = [c['container'], v['fusion_container'], v['http_container']]
containers = json.loads(run(['docker', 'inspect', *names]))
dispatch, fusion, http = containers
assert not dispatch['State']['Running'] and dispatch['State']['ExitCode'] == 0
assert dispatch['Image'] == c['image'] and fusion['Image'] == c['image']
assert fusion['State']['Running'] and http['State']['Running']
assert not any('analysis_dispatch_runtime' in row.get('Command', '')
               for row in (json.loads(line) for line in run(
                   ['docker', 'ps', '--no-trunc', '--format', '{{json .}}']).splitlines()))
probe = '''import asyncio, json, sys
from urllib.parse import urlparse
from app.core.config import settings
import redis.asyncio as redis
async def main():
    v=json.load(sys.stdin)
    r=redis.from_url(settings.redis_url, decode_responses=True)
    key=v['correlation_key']
    try:
        incident=await r.get(key)
        summary_key='aisoc:fusion:incident:'+str(incident)
        raw=await r.get(summary_key)
        summary=json.loads(raw) if raw else {}
        out={'redis_db':urlparse(settings.redis_url).path,
             'correlation_key':key,'incident_id':incident,
             'index_ttl_seconds':await r.ttl(key),
             'summary_ttl_seconds':await r.ttl(summary_key),
             'alert_count':summary.get('alert_count'),
             'alert_ids':summary.get('alert_ids'),
             'configured_window_seconds':settings.correlation_window_seconds,
             'configured_max_alerts':settings.max_alerts_per_incident}
        assert incident==v['expected_incident_id'] and out['index_ttl_seconds']>0
        assert out['summary_ttl_seconds']>0 and out['alert_count']==3
        print(json.dumps(out))
    finally:
        await r.aclose()
asyncio.run(main())
'''
corr = json.loads(run(['docker', 'exec', '-i', v['fusion_container'], 'python', '-c', probe],
                      json.dumps(v)))
env = dict(item.split('=', 1) for item in fusion['Config']['Env'])
for key, expected in v['expected_fusion_env'].items():
    assert env[key] == expected, key
http_lifecycle = hashlib.sha256((root/'analysis/config/lifecycle.json').read_bytes()).hexdigest()
assert any(m['Source'] == str(root/'analysis/config/lifecycle.json')
           and m['Destination'] == '/app/config/analysis-tasks.json'
           and not m['RW'] for m in http['Mounts'])
print(json.dumps({'status': 'passed', 'observed_at': datetime.now(timezone.utc).isoformat(),
                  'runtime_files': config_hashes, 'correlation': corr,
                  'containers': [{'name': row['Name'].lstrip('/'), 'id': row['Id'],
                                  'image': row['Image'], 'status': row['State']['Status']}
                                 for row in containers],
                  'http_lifecycle_sha256': http_lifecycle,
                  'kafka_messages_sent': 0, 'model_calls': 0,
                  'redis_mutations': 0}, indent=2))
