"""Final T1 baseline: GET contracts/status; capture public OpenAPI and safe config only."""
import datetime
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request

cfg = json.load(sys.stdin)


def get(base, path):
    try:
        response = urllib.request.urlopen(base + path, timeout=cfg['probe_timeout_seconds'])
    except urllib.error.HTTPError as e:
        response = e
    with response:
        body = response.read()
        try:
            data = json.loads(body)
        except (ValueError, UnicodeError):
            data = None
        return {'method': 'GET', 'base_url': base, 'path': path, 'http_status': response.status,
                'sha256': hashlib.sha256(body).hexdigest(), 'body': data}


def operations(schema):
    return {(m.upper(), p) for p, item in schema.get('paths', {}).items()
            if p.startswith('/api/v1/socai2/') for m in item if m in ['get', 'post', 'patch', 'put', 'delete']}


out = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'mode': 'read_only', 'target': cfg['target'], 'model_calls': 0}
out['live_openapi'] = get(cfg['http_base'], '/openapi.json')
out['swagger_openapi'] = get(cfg['swagger_base'], '/handoff/openapi.json')
out['swagger_config'] = get(cfg['swagger_base'], '/handoff/swagger-config.json')
live, swagger = out['live_openapi']['body'], out['swagger_openapi']['body']
a, b = operations(live), operations(swagger)
out['contract_comparison'] = {'live_operations': len(a), 'swagger_operations': len(b),
    'missing_in_live': sorted(b - a), 'extra_in_live': sorted(a - b),
    'same_raw_sha256': out['live_openapi']['sha256'] == out['swagger_openapi']['sha256'],
    'live_security_schemes': list(live.get('components', {}).get('securitySchemes', {})),
    'swagger_security_schemes': list(swagger.get('components', {}).get('securitySchemes', {}))}
out['gets'] = [get(cfg['http_base'], p) for p in ['/livez', '/readyz',
    '/api/v1/socai2/cases?limit=1', '/api/v1/socai2/alerts?limit=1',
    '/api/v1/socai2/incidents?limit=1', '/api/v1/socai2/analysis-runs?limit=1']]
out['workbench_status'] = get(cfg['workbench_base'], '/_workbench/status')
source = r'''
import hashlib,json,os,pathlib,tomllib
p=pathlib.Path(os.environ['SOCAI2_INVESTIGATION_POLICY']);v=tomllib.loads(p.read_text())
print(json.dumps({'context_file_configured':bool(os.environ.get('SOCAI2_HTTP_CONTEXT_FILE')),
    'policy_hash':hashlib.sha256(p.read_bytes()).hexdigest(),
    'policy_limits':{k:v[k] for k in ['single_model_timeout_seconds','final_reserve_seconds','case','alert_basic','incident_diagnosis'] if k in v},
    'analysis_config_env_keys':[k for k in os.environ if k.startswith('SOCAI2_ANALYSIS_')]}))
'''
p = subprocess.run(['docker', 'exec', 'socai2-http-api', 'python', '-B', '-c', source],
                   capture_output=True, text=True, timeout=cfg['probe_timeout_seconds'])
out['loaded_config'] = json.loads(p.stdout) if p.returncode == 0 else {'state': 'probe_error'}
d = json.loads(subprocess.check_output(['docker', 'inspect', 'socai2-http-api'], text=True))[0]
out['http_process'] = {'image': d['Config']['Image'], 'image_id': d['Image'],
    'entrypoint': d['Config']['Entrypoint'], 'command': d['Config']['Cmd'],
    'started_at': d['State']['StartedAt']}
source = r'''
import json,os,pathlib,yaml
d=yaml.safe_load(pathlib.Path('/etc/litellm/config.yaml').read_text())
def resolve(v):
    return os.environ.get(v.split('/',1)[1]) if isinstance(v,str) and v.startswith('os.environ/') else v
print(json.dumps([{'alias':m.get('model_name'),'upstream_model':resolve(m.get('litellm_params',{}).get('model')),
    'upstream_base':resolve(m.get('litellm_params',{}).get('api_base'))} for m in d.get('model_list',[]) if m.get('model_name')=='aisoc-investigation']))
'''
p = subprocess.run(['docker', 'exec', 'socai2-litellm-1', 'python', '-B', '-c', source],
                   capture_output=True, text=True, timeout=cfg['probe_timeout_seconds'])
out['model_route_config_only'] = json.loads(p.stdout) if p.returncode == 0 else {'state': 'probe_error'}
print(json.dumps(out, ensure_ascii=False, indent=2))
