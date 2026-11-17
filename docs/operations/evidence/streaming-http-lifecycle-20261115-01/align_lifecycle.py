"""Align only the candidate HTTP's readonly lifecycle mount; retain its image."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
CONFIG = ROOT / 'deploy/http-service/streaming-20261115-01/lifecycle-runtime.json'
REMOTE = r'''
import hashlib,json,os,subprocess,time,urllib.request
from datetime import datetime,timezone
from pathlib import Path
payload=json.loads(PAYLOAD)
cfg,action=payload['config'],payload['action']
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def file_hash(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def command(args,timeout=None):
    result=subprocess.run(args,capture_output=True,timeout=timeout or cfg['timeout_seconds'])
    if result.returncode: raise RuntimeError('command_failed:'+args[0]+':'+str(result.returncode))
    return result.stdout
def inspect(name): return json.loads(command(['docker','inspect',name]))[0]
def protected():
    return {name:{'id':(row:=inspect(name))['Id'],'image':row['Image'],'status':row['State']['Status']}
            for name in cfg['protected_containers']}
def policy():
    code="import os,json,hashlib; from pathlib import Path; from dataclasses import asdict; from app.socai2.analysis_task_policy import AnalysisTaskPolicy; p=Path(os.environ['SOCAI2_ANALYSIS_TASKS_CONFIG_FILE']); print(json.dumps({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'policy':asdict(AnalysisTaskPolicy.load())}))"
    return json.loads(command(['docker','exec',cfg['container'],'python','-c',code]))
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
base=f"http://{cfg['bind']}:{cfg['port']}"
def web(path):
    with opener.open(base+path,timeout=5) as response:
        assert response.status==200,'http_not_200'
        return json.load(response)
def schema_check(doc):
    count=sum(1 for path,methods in doc['paths'].items() if path.startswith('/api/v1/socai2/')
              for method in methods if method in {'get','post','patch','delete','put'})
    assert count==cfg['expected_operations'],'operation_count_changed'
    assert doc['info']['version']==cfg['release'],'release_changed'
    assert not doc.get('security') and not doc.get('components',{}).get('securitySchemes'),'auth_contract_changed'
    return {'sha256':digest(doc),'operations':count,'release':doc['info']['version'],'authentication':'none'}
def snapshot(row):
    fields=['PortBindings','ReadonlyRootfs','CapDrop','SecurityOpt','RestartPolicy','Memory','NetworkMode','Tmpfs']
    return {'id':row['Id'],'image':row['Image'],'status':row['State']['Status'],
        'environment_sha256':digest(sorted(row['Config']['Env'])),
        'process':{key:row['Config'].get(key) for key in ['Cmd','Entrypoint','User','WorkingDir']},
        'host_config':{key:row['HostConfig'].get(key) for key in fields},
        'mounts':[{key:m.get(key) for key in ['Type','Source','Destination','RW']} for m in row['Mounts']]}
def emit(value): print(json.dumps(value,ensure_ascii=False),flush=True)
try:
    source=Path(cfg['mount']['source'])
    assert file_hash(source)==cfg['mount']['sha256'],'lifecycle_source_changed'
    target=json.loads(source.read_text())
    current=inspect(cfg['container'])
    assert current['Image']==cfg['expected_image'] and current['State']['Running'],'unexpected_http_candidate'
    compose=Path(cfg['base_compose'])
    service=json.loads(compose.read_text())['services'][cfg['service']]
    assert service['container_name']==cfg['container'],'compose_target_changed'
    assert inspect(service['image'])['Id']==cfg['expected_image'],'image_tag_changed'
    env=dict(item.split('=',1) for item in current['Config']['Env'])
    assert env['SOCAI2_ANALYSIS_TASKS_CONFIG_FILE']==cfg['mount']['target'],'lifecycle_env_changed'
    before={'at':datetime.now(timezone.utc).isoformat(),'container':snapshot(current),
            'loaded':policy(),'target':{'sha256':file_hash(source),'policy':target},
            'compose_sha256':file_hash(compose),'contract':schema_check(web('/openapi.json')),
            'ready':web('/readyz'),'protected':protected()}
    emit({'phase':'before','data':before})
    if action=='preflight':
        emit({'phase':'result','passed':True,'mutated':False})
    elif action=='apply':
        expected=payload['preflight']
        assert before['container']==expected['container'],'container_changed_since_preflight'
        assert before['compose_sha256']==expected['compose_sha256'],'compose_changed_since_preflight'
        assert before['protected']==expected['protected'],'protected_changed_since_preflight'
        override=Path(cfg['override_compose'])
        override.parent.mkdir(parents=True,exist_ok=True)
        volume={'type':'bind','source':str(source),'target':cfg['mount']['target'],'read_only':True,
                'bind':{'create_host_path':False}}
        with override.open('x') as stream:
            json.dump({'services':{cfg['service']:{'volumes':[volume]}}},stream,indent=2)
            stream.write('\n')
        original=json.loads(command(['docker','compose','-f',str(compose),'config','--format','json']))
        effective=json.loads(command(['docker','compose','-f',str(compose),'-f',str(override),'config','--format','json']))
        a,b=original['services'][cfg['service']],effective['services'][cfg['service']]
        assert {k:v for k,v in a.items() if k!='volumes'}=={k:v for k,v in b.items() if k!='volumes'},'unexpected_compose_delta'
        assert len(b.get('volumes',[]))==len(a.get('volumes',[]))+1,'unexpected_volume_count'
        emit({'phase':'prepared','override':str(override),'sha256':file_hash(override),'delta':'one_readonly_lifecycle_mount'})
        command(['docker','compose','-f',str(compose),'-f',str(override),'up','-d','--no-deps','--no-build','--pull','never',cfg['service']])
        deadline=time.monotonic()+cfg['startup_timeout_seconds']
        while True:
            try:
                ready=web('/readyz');doc=web('/openapi.json');break
            except Exception:
                if time.monotonic()>=deadline: raise
                time.sleep(1)
        after_row=inspect(cfg['container']);after=snapshot(after_row);loaded=policy()
        assert after['image']==before['container']['image'],'image_changed'
        for key in ['environment_sha256','process','host_config']:
            assert after[key]==before['container'][key],'runtime_changed:'+key
        old_mounts=before['container']['mounts']
        added=[m for m in after['mounts'] if m not in old_mounts]
        assert all(m in after['mounts'] for m in old_mounts),'old_mount_changed'
        assert added==[{'Type':'bind','Source':str(source),'Destination':cfg['mount']['target'],'RW':False}],'mount_mismatch'
        assert loaded['sha256']==cfg['mount']['sha256'] and loaded['policy']==target,'effective_policy_mismatch'
        assert schema_check(doc)==before['contract'],'http_contract_changed'
        after_protected=protected()
        assert after_protected==before['protected'],'protected_container_changed'
        assert file_hash(compose)==before['compose_sha256'],'original_compose_changed'
        emit({'phase':'after','at':datetime.now(timezone.utc).isoformat(),'container':after,'loaded':loaded,
              'contract':schema_check(doc),'ready':ready,'protected':after_protected})
        emit({'phase':'result','passed':True,'only_candidate_http_recreated':True,
              'same_image':True,'same_contract':True,'business_gets':0,'business_writes':0,
              'dispatcher_started':False,'image_built':False,'swagger_changed':False})
    else: raise ValueError('unknown_action')
except Exception as error:
    emit({'phase':'failure','passed':False,'error_type':type(error).__name__,'error':str(error)[:200]})
    raise SystemExit(1)
'''


def main():
    action = sys.argv[1]
    assert action in {'preflight', 'apply'}
    config = json.loads(CONFIG.read_text())
    import hashlib
    assert hashlib.sha256((ROOT / config['local_source']).read_bytes()).hexdigest() == config['mount']['sha256']
    payload = {'action': action, 'config': config}
    if action == 'apply':
        saved = json.loads((OUT / 'preflight-01.json').read_text())
        assert saved['ssh_exit'] == 0
        payload['preflight'] = next(x['data'] for x in saved['receipts'] if x['phase'] == 'before')
    output = OUT / f'{action}-01.json'
    assert not output.exists(), 'Inspect existing receipts before any new attempt.'
    code = REMOTE.replace('PAYLOAD', repr(json.dumps(payload, ensure_ascii=False)))
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', config['ssh_target'],
                             'python3', '-'], input=code, text=True, capture_output=True, timeout=180)
    receipts = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    with output.open('x') as stream:
        json.dump({'ssh_exit': result.returncode, 'ssh_stderr': result.stderr, 'receipts': receipts}, stream,
                  ensure_ascii=False, indent=2)
        stream.write('\n')
    assert result.returncode == 0 and receipts[-1]['phase'] == 'result' and receipts[-1]['passed'], str(output)
    print(json.dumps(receipts[-1], ensure_ascii=False))


if __name__ == '__main__':
    main()
