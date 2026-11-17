"""Copy the frozen, unexecuted 4a inputs and instantiate private 21 connections only."""
import hashlib
import io
import json
import shlex
import subprocess
import sys
import tarfile
from pathlib import Path

REMOTE = r'''
import hashlib,io,json,os,subprocess,sys,tarfile
from pathlib import Path
c=json.loads(sys.argv[1]); root=Path(c['stage_root']); private=Path(c['private_root']); release=Path(c['release_root'])
assert not root.exists() and not private.exists(), 'stage_already_exists'
r=json.loads((release/'config/release.json').read_text()); h=json.loads((release/'config/http-profile.json').read_text())
ready=json.loads((release/'deployment-ready.json').read_text()); assert ready['status']=='ready_for_new_full_flow'
assert (release/'cleanup-zero.json').is_file()
assert r['network']==c['network'] and r['acceptance']['image_reference']==c['image']
uid,gid=c['uid'],c['gid']; root.mkdir();private.mkdir(mode=0o700);os.chown(private,uid,gid)
raw=sys.stdin.buffer.read();assert hashlib.sha256(raw).hexdigest()==sys.argv[2]
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
 for item in t.getmembers():
  n=Path(item.name); assert item.isfile() and not n.is_absolute() and '..' not in n.parts
  p=root/n;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(t.extractfile(item).read())
manifest=json.loads((root/'inputs-manifest.json').read_text())
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in manifest.items())
assert not (root/'results/prepared/runs').exists()

def inspect(name):
 return json.loads(subprocess.check_output(['docker','inspect',name]))[0]
def env(row):return dict(v.split('=',1) for v in row['Config']['Env'] if '=' in v)
f,a=inspect(r['fusion']['name']),inspect(r['analysis']['name']); fe,ae=env(f),env(a)
assert f['State']['Running'] and a['State']['Running']
prior=Path(r['prior_runtime_root']); config=private/'config';config.mkdir(mode=0o700)
(config/'secrets').mkdir(mode=0o700)
def write(path,data):
 with path.open('xb') as out:out.write(data)
 os.chmod(path,0o600);os.chown(path,uid,gid)
def put(name,value):write(config/name,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
write(config/'profile.json',(root/'profile.json').read_bytes())
write(config/'secrets/analysis-database-url',(prior/'private/analysis-database-url').read_bytes())
write(config/'secrets/lake-password',ae['CLICKHOUSE_PASSWORD'].encode())
write(config/'secrets/fusion-redis-url',fe['REDIS_URL'].encode())
write(config/'secrets/analysis-redis-url',(prior/'private/analysis-redis-url').read_bytes())
producer={k:v for k,v in fe.items() if k.startswith('KAFKA_') and not k.startswith('KAFKA_CONSUMER')}
for key in ['KAFKA_SSL_CAFILE','KAFKA_SSL_CERTFILE','KAFKA_SSL_KEYFILE']:
 if producer.get(key):
  source=next(Path(m['Source']) for m in f['Mounts'] if m['Destination']==producer[key])
  filename=key.lower();write(config/'secrets'/filename,source.read_bytes());producer[key]='/run/acceptance-config/secrets/'+filename
write(config/'secrets/producer.env',(''.join(k+'='+json.dumps(v)+'\n' for k,v in sorted(producer.items()))).encode())
t=c['connection']; d=r['database']; tenant=r['identity']['tenant_id']
put('http.json',{'base_url':'http://'+h['container']+':'+str(h['container_port']),'tenant_id':tenant,'timeout_seconds':t['timeout_seconds'],'page_size':t['page_size'],'fusion_ready_url':'http://'+r['fusion']['name']+':'+str(r['fusion']['container_port'])+'/readyz'})
put('postgres.json',{'database_url_file':'/run/acceptance-config/secrets/analysis-database-url','expected_database':d['name'],'expected_user':d['processor'],'schema_name':'socai2','ssl':d['sslmode'],'connect_timeout_seconds':t['connect_timeout_seconds'],'query_timeout_seconds':t['timeout_seconds']})
put('kafka.json',{'producer_env_file':'/run/acceptance-config/secrets/producer.env','expected_bootstrap_servers':fe['KAFKA_BOOTSTRAP_SERVERS'],'security_protocol':fe['KAFKA_SECURITY_PROTOCOL'],'topics':{'alert':fe['KAFKA_TOPIC_ALERTS_RAW'],'context':fe['KAFKA_TOPIC_RAW_EVENTS']},'timeout_seconds':t['timeout_seconds'],'request_timeout_ms':t['request_timeout_ms']})
put('lake.json',{'host':ae['CLICKHOUSE_HOST'],'port':int(ae['CLICKHOUSE_PORT']),'database':ae['CLICKHOUSE_DATABASE'],'table':t['lake_table'],'user':ae['CLICKHOUSE_USER'],'password_file':'/run/acceptance-config/secrets/lake-password','secure':t['lake_secure'],'verify':t['lake_verify'],'ca_certs':t['lake_ca_certs'],'connect_timeout_seconds':t['connect_timeout_seconds'],'read_timeout_seconds':t['timeout_seconds'],'query_timeout_seconds':int(t['timeout_seconds'])})
put('admission.json',{'expected':c['runtime_expectations'],'redis_timeout_seconds':t['connect_timeout_seconds'],'release':r['release'],'http_version':ready['http_version'],'policy_sha256':ready['policy_sha256'],'fusion_redis_url_file':'/run/acceptance-config/secrets/fusion-redis-url','analysis_redis_url_file':'/run/acceptance-config/secrets/analysis-redis-url','redis_databases':{'fusion':r['fusion']['redis_db'],'analysis':r['analysis']['redis_db']},'final_receipts':{n:hashlib.sha256((release/n).read_bytes()).hexdigest() for n in ['cleanup-zero.json','deployment-ready.json']}})
for p in config.rglob('*'):
 os.chown(p,uid,gid)
 if p.is_dir():os.chmod(p,0o700)
os.chown(config,uid,gid)
for p in [root/'results',*(root/'results').rglob('*')]:
 os.chown(p,uid,gid);os.chmod(p,0o750 if p.is_dir() else 0o640)
values={'ACCEPTANCE_PROJECT':c['project'],'ACCEPTANCE_IMAGE':c['image'],'ACCEPTANCE_PLATFORM':'linux/amd64','ACCEPTANCE_USER':str(uid)+':'+str(gid),'ACCEPTANCE_NETWORK':c['network'],'ACCEPTANCE_CPUS':c['cpu'],'ACCEPTANCE_MEMORY':c['memory'],'ACCEPTANCE_PIDS':c['pids'],'ACCEPTANCE_TMPFS_SIZE':c['tmpfs'],'ACCEPTANCE_MATERIALS_DIR':str(root/'materials'),'ACCEPTANCE_CONFIG_DIR':str(config),'ACCEPTANCE_RESULTS_DIR':str(root/'results'),'ACCEPTANCE_MATERIALS_TARGET':'/materials','ACCEPTANCE_CONFIG_TARGET':'/run/acceptance-config','ACCEPTANCE_RESULTS_TARGET':'/results'}
write(root/'run.env',''.join(k+'='+str(v)+'\n' for k,v in values.items()).encode())
receipt={'status':'staged_not_executed','root':str(root),'private_config':str(config),'compose':str(release/c['compose_relative']),'image':c['image'],'uid':uid,'network':c['network'],'files_sha256':manifest,'connection_files':{n:json.loads((config/(n+'.json')).read_text()) for n in ['http','postgres','kafka','lake']},'connection_sha256':{n:hashlib.sha256((config/(n+'.json')).read_bytes()).hexdigest() for n in ['http','postgres','kafka','lake']},'runs_exists':False,'new_business_writes':0,'model_calls':0}
print(json.dumps(receipt,ensure_ascii=False))
'''


def main():
    config_path=Path(sys.argv[1]).resolve(); c=json.loads(config_path.read_text()); project=Path.cwd(); source=project/c['source']; evidence=project/c['evidence']
    files={}
    for prefix in ['materials','results/prepared']:
        for p in sorted((source/prefix).rglob('*')):
            if p.is_file():
                assert not p.is_symlink();files[str(p.relative_to(source))]=p.read_bytes()
    assert len(files)==13
    manifest={n:hashlib.sha256(b).hexdigest() for n,b in files.items()}
    files['inputs-manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    files['profile.json']=(source/'config/profile.json').read_bytes()
    files['results/admission-21.py']=(evidence/'admission-21.py').read_bytes()
    archive=io.BytesIO()
    with tarfile.open(fileobj=archive,mode='w:gz') as t:
        for n,b in files.items():
            item=tarfile.TarInfo(n);item.mode=0o644;item.size=len(b);t.addfile(item,io.BytesIO(b))
    body=archive.getvalue()
    command=['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15',c['ssh_target'],shlex.join(['python3','-c',REMOTE,json.dumps(c),hashlib.sha256(body).hexdigest()])]
    result=subprocess.run(command,input=body,capture_output=True,timeout=60)
    # Remote tracebacks can contain private values; preserve raw stderr only outside repository.
    if result.returncode:
        private=project/'.local/acceptance-fullflow-21-20261117-01';private.mkdir(mode=0o700,exist_ok=True)
        (private/'stage-error.txt').write_bytes(result.stderr)
        print(json.dumps({'status':'failed','exit':result.returncode,'error_saved_privately':True}));sys.exit(2)
    receipt=json.loads(result.stdout)
    with (evidence/'staging-01.json').open('x') as out:json.dump(receipt,out,ensure_ascii=False,indent=2)
    print(json.dumps({k:receipt[k] for k in ['status','root','network','runs_exists','new_business_writes']}))

if __name__=='__main__':main()
