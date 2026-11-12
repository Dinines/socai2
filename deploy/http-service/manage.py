"""Prepare one explicit HTTP overlay; never migrates or starts consumers.

package/local run on the Mac. prepare/build/start/verify run on the selected host.
Credentials are inherited on that host and written only to its private directory.
"""
import argparse
import hashlib
import json
import os
import socket
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value, *, private=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600 if private else 0o644), 'w') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def command(args, *, timeout=60, env=None):
    r = subprocess.run(args, capture_output=True, timeout=timeout, env=env)
    if r.returncode:
        # Docker/driver stderr can carry sensitive connection configuration.
        raise RuntimeError('command_failed: '+args[0]+': '+str(r.returncode))
    return r.stdout


def inspect(name):
    return json.loads(command(['docker','inspect',name]))[0]


def snapshot(exclude):
    names = command(['docker','ps','--format','{{.Names}}']).decode().splitlines()
    return {n:{'id':c['Id'],'image':c['Image'],'started_at':c['State']['StartedAt']}
            for n in names if n != exclude for c in [inspect(n)]}


def package(profile, output):
    root = Path(__file__).resolve().parents[2]
    output.mkdir(parents=True, exist_ok=False)
    for source, target in profile['patches'].items():
        dst = output/target
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((root/source).read_bytes())
    (output/'manage.py').write_bytes(Path(__file__).read_bytes())
    save(output/'profile.json', profile)
    dockerfile = 'FROM '+profile['base_tag']+'\nUSER root\nWORKDIR /app\n'
    for target in profile['patches'].values():
        dockerfile += 'COPY --chown=10001:10001 '+target+' /app/'+target+'\n'
    dockerfile += 'USER 10001:10001\n'
    (output/'Dockerfile').write_text(dockerfile)
    save(output/'manifest.json', {'release':profile['release'],'base_image':profile['base_image'],
        'files':{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}})
    archive = output.with_suffix('.tar')
    with tarfile.open(archive,'w') as t:
        for p in sorted(output.rglob('*')):
            if p.is_file():t.add(p,arcname=str(p.relative_to(output)))
    return {'archive':str(archive),'sha256':sha(archive),'overlay_files':list(profile['patches'].values())}


def verify_files(folder):
    m=json.loads((folder/'manifest.json').read_text())
    assert all(sha(folder/k)==v for k,v in m['files'].items()), 'candidate_file_changed'


def prepare(cfg, folder):
    verify_files(folder)
    ref=inspect(cfg['reference_container'])
    assert ref['Image']==cfg['base_image'], 'reference_image_changed'
    if cfg.get('replace_existing', False):
        current=inspect(cfg['container'])
        assert current['Image']==cfg['base_image'], 'replacement_base_changed'
        bindings=current['HostConfig']['PortBindings'][str(cfg['container_port'])+'/tcp']
        assert bindings==[{'HostIp':cfg['bind'],'HostPort':str(cfg['port'])}], 'replacement_endpoint_changed'
    else:
        with socket.socket() as s:s.bind((cfg['bind'],cfg['port']))
    private=Path(cfg['root'])/'private'/cfg['release']
    private.mkdir(parents=True, exist_ok=False)
    env=dict(x.split('=',1) for x in ref['Config']['Env'])
    assert env.get('DATABASE_URL') and env.get('SOCAI2_CASE_DATABASE_URL'), 'existing_explicit_connections_required'
    env.update(cfg['environment'])
    env.update(SOCAI2_SERVICE_DATABASE_NAME=cfg['database'],SOCAI2_HTTP_RELEASE=cfg['release'])
    assert all('\n' not in v and '\r' not in v for v in env.values()), 'unsupported_environment_value'
    with os.fdopen(os.open(private/'runtime.env',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        f.write('\n'.join(k+'='+v for k,v in sorted(env.items()))+'\n')
    volumes=[]
    for m in ref['Mounts']:
        if m['Type']=='tmpfs':
            continue  # New tmpfs comes exclusively from this release's profile.
        assert not m['RW'], 'reference_writable_mount_requires_explicit_design'
        volumes.append({'type':'bind','source':m['Source'],'target':m['Destination'],'read_only':True})
    service={'container_name':cfg['container'],'image':cfg['image'],'platform':cfg['platform'],'pull_policy':'never',
        'command':['python','-m','uvicorn',cfg['entry'],'--host','0.0.0.0','--port',str(cfg['container_port']),'--workers','1'],
        'env_file':[{'path':str(private/'runtime.env'),'format':'raw'}],
        'ports':[f"{cfg['bind']}:{cfg['port']}:{cfg['container_port']}"],
        'volumes':volumes,'read_only':True,'tmpfs':[cfg['tmpfs']],'cap_drop':['ALL'],
        'security_opt':['no-new-privileges:true'],'restart':'unless-stopped','mem_limit':cfg['memory'],'networks':['existing']}
    save(folder/'compose.json',{'name':cfg['project'],'services':{'api':service},
        'networks':{'existing':{'external':True,'name':cfg['network']}}})
    save(folder/'before.json',snapshot(cfg['container']))
    return {'prepared':True,'database':cfg['database'],'new_endpoint':f"http://{cfg['bind']}:{cfg['port']}",
            'private_environment_exported':False,'existing_services_changed':False}


def verify(cfg, folder):
    base=f"http://{cfg['bind']}:{cfg['port']}"
    with urllib.request.urlopen(base+'/readyz',timeout=5) as r:assert r.status==200
    with urllib.request.urlopen(base+'/openapi.json',timeout=10) as r:doc=json.load(r)
    paths={p:{m:v for m,v in methods.items() if m in {'get','post','put','patch','delete'}}
           for p,methods in doc['paths'].items() if p.startswith('/api/v1/socai2/')}
    assert sum(len(v) for v in paths.values())==cfg['expected_operations'], 'current_contract_not_complete'
    current=inspect(cfg['container'])
    assert current['Image']==inspect(cfg['image'])['Id'], 'runtime_image_mismatch'
    before=json.loads((folder/'before.json').read_text())
    assert snapshot(cfg['container'])==before, 'existing_containers_changed'
    return {'release':doc['info']['version'],'database':cfg['database'],'endpoint':base,
            'route_count':cfg['expected_operations'],'paths':{p:list(v) for p,v in paths.items()},'image':current['Image'],
            'container':cfg['container'],'ready':True,'previous_running_containers_unchanged':True,
            'overlay_sha256':json.loads((folder/'manifest.json').read_text())['files']}


def local(cfg):
    root=Path(__file__).resolve().parents[2]
    with socket.socket() as s:s.bind((cfg['bind'],cfg['port']))
    env=json.loads((root/cfg['private_environment']).read_text())
    env.update(SOCAI2_SERVICE_DATABASE_NAME=cfg['database'],SOCAI2_HTTP_RELEASE=cfg['release'])
    # Use only this explicit environment plus the process's basic executable path.
    env.setdefault('PATH',os.environ.get('PATH',''))
    with (root/cfg['log_file']).open('ab') as log:
        p=subprocess.Popen([str(root/cfg['python']),'-m','uvicorn',cfg['entry'],'--host',cfg['bind'],
            '--port',str(cfg['port']),'--workers','1'],cwd=root/cfg['app_directory'],env=env,
            stdout=log,stderr=log,start_new_session=True)
    (root/cfg['pid_file']).write_text(str(p.pid)+'\n')
    return {'pid':p.pid,'endpoint':f"http://{cfg['bind']}:{cfg['port']}",'database':cfg['database']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,required=True)
    parser.add_argument('action',choices=['package','prepare','build','start','verify','local'])
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();cfg=json.loads(args.profile.read_text());folder=args.profile.resolve().parent
    assert cfg['version']=='socai2.http-service.v1'
    if args.action=='package':result=package(cfg,args.output)
    elif args.action=='prepare':result=prepare(cfg,folder)
    elif args.action=='local':result=local(cfg)
    elif args.action=='build':
        verify_files(folder)
        assert inspect(cfg['base_image'])['Id']==cfg['base_image']
        command(['docker','tag',cfg['base_image'],cfg['base_tag']])
        assert inspect(cfg['base_tag'])['Id']==cfg['base_image']
        command(['docker','build','--pull=false','--network','none','--platform',cfg['platform'],
                 '-t',cfg['image'],str(folder)],timeout=cfg['build_timeout_seconds'],
                env={**os.environ,'DOCKER_BUILDKIT':'1' if cfg['buildkit'] else '0'})
        result={'image':inspect(cfg['image'])['Id'],'release':cfg['release']}
    elif args.action=='start':
        verify_files(folder)
        command(['docker','compose','-f',str(folder/'compose.json'),'up','-d'])
        deadline=time.monotonic()+cfg['startup_timeout_seconds']
        while True:
            try:
                result=verify(cfg,folder);break
            except (OSError,ValueError):
                if time.monotonic()>=deadline:raise
                time.sleep(1)
    else:result=verify(cfg,folder)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
