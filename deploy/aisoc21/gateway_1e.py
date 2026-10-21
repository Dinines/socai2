"""Host21 bounded gateway startup and environment verification for batch 1E.

Does not restart infrastructure, change API/Fusion config, or issue completions.
The companion probe owns the explicitly bounded five completion requests.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

ROOT = Path('/opt/sting-aisoc-socai2')
EVIDENCE = ROOT/'evidence/1e-20261020'
IMAGE = 'sha256:2e4c0371f3a8c28e4da131d77abaa8341cd3b0c2fcc4d34d7c5900431af7b9d0'
NAME = 'socai2-litellm-1'


def run(args):
    r = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if r.returncode: raise RuntimeError('Command failed: '+args[0])
    return r.stdout


def save(name, value):
    with (EVIDENCE/name).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')


def inspect(name):
    return json.loads(run(['docker','inspect',name]))[0]


def inventory():
    xs = json.loads(run(['docker','inspect',*run(['docker','ps','-aq']).split()]))
    return {'containers':{x['Name'].lstrip('/'): {'id':x['Id'],'image':x['Image'],
            'started_at':x['State']['StartedAt'],'status':x['State']['Status'],
            'restart_count':x['RestartCount'],'mounts':x['Mounts']} for x in xs},
            'volumes':run(['docker','volume','ls','-q']).split()}


def start():
    assert not (EVIDENCE/'runtime-start.json').exists(), 'Retained startup exists'
    assert NAME not in inventory()['containers'], 'Inspect existing gateway rather than replace it'
    with socket.socket() as port:
        port.bind(('127.0.0.1',14000))
    image = json.loads(run(['docker','image','inspect',IMAGE]))[0]
    assert image['Id']==IMAGE and image['Architecture']=='amd64'
    command = ['docker','compose','--project-directory',str(ROOT)]
    for name in ('services','embedding','gateway'):
        command += ['-f',str(ROOT/f'source/deploy/aisoc21/compose.{name}.yml')]
    run(command+['config','--quiet'])
    run(command+['up','-d','--no-deps','--pull','never','litellm'])
    start_time = time.monotonic()
    for _ in range(45):
        try:
            with urllib.request.urlopen('http://127.0.0.1:14000/health/liveliness',timeout=3) as r:
                health = json.load(r)
            break
        except OSError: time.sleep(1)
    else: raise RuntimeError('Gateway not ready; preserve first startup logs')
    x = inspect(NAME)
    assert x['Image']==IMAGE and x['Config']['User']=='10001:10001'
    assert x['HostConfig']['ReadonlyRootfs']
    assert x['NetworkSettings']['Ports']['4000/tcp']==[{'HostIp':'127.0.0.1','HostPort':'14000'}]
    code = '''import importlib.metadata,json,os,urllib.request,yaml,hashlib
c=yaml.safe_load(open('/etc/litellm/config.yaml'))
assert len(c['model_list'])==5 and c['router_settings']['num_retries']==0 and c['router_settings']['fallbacks']==[]
assert c['general_settings']['master_key']=='os.environ/LITELLM_MASTER_KEY'
base=os.environ['AISOC_LLM_API_BASE']
assert base=='http://192.168.1.43:8000/v1'
req=urllib.request.Request(base+'/models',headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']})
with urllib.request.urlopen(req,timeout=10) as r: data=json.load(r)
assert 'aisoc-test-investigation' in [m['id'] for m in data['data']]
print(json.dumps({'litellm_version':importlib.metadata.version('litellm'),'model_aliases':[m['model_name'] for m in c['model_list']],'upstream_base':base,'upstream_fast':os.environ['AISOC_LLM_MODEL_FAST'],'upstream_deep':os.environ['AISOC_LLM_MODEL_DEEP'],'upstream_model_ids':[m['id'] for m in data['data']],'upstream_model_listing_sha256':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),'router_settings':c['router_settings'],'request_timeout_seconds':int(os.environ['AISOC_LITELLM_REQUEST_TIMEOUT'])}))'''
    provider = json.loads(run(['docker','exec',NAME,'python','-c',code]))
    assert provider['litellm_version']=='1.106.0'
    line = next(line for line in Path(f"/proc/{x['State']['Pid']}/limits").read_text().splitlines()
                if line.startswith('Max open files'))
    assert line.split()[3:5]==['65536','65536']
    save('runtime-start.json', {'container_id':x['Id'],'image_id':x['Image'],
         'started_at':x['State']['StartedAt'],'user':x['Config']['User'],
         'read_only_rootfs':True,'ports':x['NetworkSettings']['Ports'],'mounts':x['Mounts'],
         'health_liveliness':health,'startup_seconds':round(time.monotonic()-start_time,3),
         'provider_preflight_no_inference':provider,'memory_bytes':x['HostConfig']['Memory'],
         'cpu_limit':x['HostConfig']['NanoCpus']/10**9,'process_nofile_line':line})
    probe = EVIDENCE/'probe'
    probe.mkdir(mode=0o750)
    run(['chown','10001:10001',str(probe)])
    print(json.dumps({'gateway_started':True,'version':provider['litellm_version'],
                      'provider_model_listing_reachable_from_gateway':True,'aliases':provider['model_aliases']}))


def verify():
    assert (EVIDENCE/'probe/summary.json').exists(), 'Require completed bounded probe'
    before = json.loads((EVIDENCE/'environment-before.json').read_text())
    after = inventory()
    for name, state in before['containers'].items():
        assert after['containers'][name]==state, 'Existing container changed: '+name
    assert sorted(after['volumes'])==sorted(before['volumes'])
    assert set(after['containers'])-set(before['containers'])=={NAME}
    x=inspect(NAME)
    assert x['State']['Health']['Status']=='healthy'
    # The model info endpoint returns keys in some versions; inspect remotely,
    # explicitly omit credentials and retain only the effective route fields.
    code='''import json,os,urllib.request
h={'Authorization':'Bearer '+os.environ['LITELLM_MASTER_KEY']}
req=urllib.request.Request('http://127.0.0.1:4000/model/info',headers=h)
with urllib.request.urlopen(req,timeout=8) as r: data=json.load(r)
rows=[{'alias':x['model_name'],'model':x['litellm_params']['model'],'api_base':x['litellm_params']['api_base']} for x in data['data']]
print(json.dumps(rows))'''
    routes=json.loads(run(['docker','exec',NAME,'python','-c',code]))
    assert len(routes)==5 and all(r['model']=='openai/aisoc-test-investigation' and r['api_base']=='http://192.168.1.43:8000/v1' for r in routes)
    health={}
    for service,port in [('api',18000),('fusion',18003),('embedding',11435)]:
        path='/api/version' if service=='embedding' else '/readyz'
        with urllib.request.urlopen(f'http://127.0.0.1:{port}'+path,timeout=8) as r:
            health[service]={'http_status':r.status}
    save('environment-after.json',after)
    save('verification.json', {'all_existing_containers_metadata_unchanged':len(before['containers']),
         'existing_volume_names_preserved':len(after['volumes']),'new_containers':[NAME],
         'gateway_healthy':True,'actual_loaded_routes':routes,'existing_project_health':health,
         'original_api_and_fusion_configuration_unmodified':True})
    print(json.dumps({'verified':True,'existing_containers_unchanged':len(before['containers']),
                      'actual_loaded_routes':len(routes),'gateway_healthy':True}))


def linkage():
    # Match each returned deployment ID to the effective upstream route, rather
    # than mistaking the response's alias for the underlying provider model.
    code = """import json,os,urllib.request
from prometheus_client.parser import text_string_to_metric_families
req=urllib.request.Request('http://127.0.0.1:4000/model/info',headers={'Authorization':'Bearer '+os.environ['LITELLM_MASTER_KEY']})
with urllib.request.urlopen(req,timeout=8) as r:data=json.load(r)
routes=[{'alias':x['model_name'],'model_id':str(x['model_info']['id']),'model':x['litellm_params']['model'],'api_base':x['litellm_params']['api_base']} for x in data['data']]
with urllib.request.urlopen('http://127.0.0.1:4000/metrics',timeout=8) as r:text=r.read().decode()
metrics=[]
for family in text_string_to_metric_families(text):
 for sample in family.samples:
  if sample.name.startswith('litellm_') and 'requests' in sample.name and sample.name.endswith('_total') and sample.value>0:
   metrics.append({'name':sample.name,'value':sample.value,'labels':{k:v for k,v in sample.labels.items() if k in ['model','requested_model','model_id','status_code','api_provider','exception_status']}})
print(json.dumps({'routes':routes,'request_metrics':metrics}))"""
    data=json.loads(run(['docker','exec',NAME,'python','-c',code]))
    routes={r['alias']:r for r in data['routes']}
    linked=[]
    for path in sorted((EVIDENCE/'probe').glob('request-*.json')):
        call=json.loads(path.read_text())
        route=routes['aisoc-'+call['role']]
        assert call['response_headers']['x-litellm-model-id']==route['model_id']
        assert call['response_headers']['x-litellm-model-group']==route['alias']
        assert route['api_base']=='http://192.168.1.43:8000/v1'
        assert route['model']=='openai/aisoc-test-investigation'
        linked.append({'role':call['role'],'client_call_id':call['call_id'],
            'gateway_call_id':call['response_headers']['x-litellm-call-id'],
            'gateway_deployment_id':route['model_id'],'upstream_base':route['api_base'],
            'configured_provider_model':route['model'],'response_model_field':call['response']['model']})
    assert len(linked)==5
    data['actual_response_header_route_linkage']=linked
    save('route-linkage.json',data)
    print(json.dumps({'response_header_routes_linked':5,'safe_request_metrics':len(data['request_metrics'])}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('start','verify','linkage'))
    args=parser.parse_args()
    try:
        {'start':start,'verify':verify,'linkage':linkage}[args.action]()
    except Exception as exc:
        print(json.dumps({'success':False,'action':args.action,'error_type':type(exc).__name__}))
        raise SystemExit(1)
