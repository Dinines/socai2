"""Read candidate state and backend capacity without generation or credentials in output."""
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

settings = json.load(sys.stdin)
c = settings['config']
root = Path(c['root'])
out = {'observed_at': datetime.now(timezone.utc).isoformat(), 'generation_calls': 0}
names = [c['container'], settings['fusion_container'], settings['http_container']]
rows = json.loads(subprocess.check_output(['docker', 'inspect', *names], text=True))
out['containers'] = [{'name': r['Name'], 'id': r['Id'], 'image': r['Image'],
                      'state': r['State']['Status'], 'exit_code': r['State']['ExitCode'],
                      'command': r['Config']['Cmd'],
                      'mounts': [{'source': x['Source'], 'destination': x['Destination']} for x in r['Mounts']]}
                     for r in rows]
out['runtime_files'] = {name: hashlib.sha256((root/'analysis/config'/name).read_bytes()).hexdigest()
                        for name in settings['expected_runtime_files']}
out['policy_text'] = (root/'analysis/config/investigation-policy.toml').read_text()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
base = c['backend_base_url'].removesuffix('/v1')

def request(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base+path, data=data, headers={'Content-Type': 'application/json'})
    with opener.open(req, timeout=c['probe_timeout_seconds']) as response:
        return json.load(response)

out['models'] = [{k: r.get(k) for k in ('id', 'root', 'parent', 'max_model_len')} for r in request('/v1/models')['data']]
value = request('/tokenize', {'model': c['backend_model'], 'prompt': 'capacity check',
                             'add_special_tokens': False, 'return_token_strs': False})
out['tokenizer'] = {k: value.get(k) for k in ('count', 'max_model_len')}
try:
    info = request('/server_info')
    out['server_info_keys'] = list(info) if isinstance(info, dict) else []
    for name in ('vllm_config', 'engine_config', 'engine_args'):
        config = info.get(name) if isinstance(info, dict) else None
        if isinstance(config, dict):
            for section in ('model_config', 'cache_config', 'parallel_config'):
                values = config.get(section, {})
                if isinstance(values, dict):
                    out.setdefault('server_capacity', {})[section] = {k: values[k] for k in (
                        'model', 'max_model_len', 'dtype', 'gpu_memory_utilization', 'tensor_parallel_size') if k in values}
except (urllib.error.URLError, ValueError, TimeoutError) as exc:
    out['server_info_error_type'] = type(exc).__name__
print(json.dumps(out, ensure_ascii=False, indent=2))
