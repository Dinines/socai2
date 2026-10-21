"""Start only requested new1G services; original infrastructure is never restarted."""
from pathlib import Path
import argparse,json,subprocess,time,urllib.request
ROOT=Path('/opt/sting-aisoc-socai2');E=ROOT/'evidence/1g-20261020'


def compose():
 c=['docker','compose','--project-directory',str(ROOT)]
 for part in ['services','embedding','gateway','investigation']:c+=['-f',str(ROOT/f'source/deploy/aisoc21/compose.{part}.yml')]
 return c


def start(service):
 subprocess.run(compose()+['config','--quiet'],check=True)
 subprocess.run(compose()+['up','-d','--no-deps','--pull','never',service],check=True,capture_output=True)
 port=18004 if service=='agents' else 18005
 for _ in range(40):
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/readyz',timeout=3) as r:health=json.load(r)
   break
  except OSError:time.sleep(1)
 else:raise RuntimeError('New service not ready; inspect sanitized logs')
 x=json.loads(subprocess.check_output(['docker','inspect','socai2-'+service+'-1']))[0]
 env=dict(v.split('=',1) for v in x['Config']['Env'])
 assert env['AISOC_SCOPED_BASELINE']=='1' and env['AISOC_DEV_MODE']=='false'
 assert x['Config']['User']=='10001:10001' and x['HostConfig']['ReadonlyRootfs']
 p=E/(service+'-startup.json');assert not p.exists()
 data={'image_id':x['Image'],'container_id':x['Id'],'started_at':x['State']['StartedAt'],'ports':x['NetworkSettings']['Ports'],'mounts':x['Mounts'],'health':health,'user':x['Config']['User'],'read_only_rootfs':True,'memory_bytes':x['HostConfig']['Memory'],'cpu_limit':x['HostConfig']['NanoCpus']/10**9,'process_nofile_line':next(l for l in Path(f"/proc/{x['State']['Pid']}/limits").read_text().splitlines() if l.startswith('Max open files')),'safe_flags':{k:v for k,v in env.items() if k.startswith('AISOC_') and ('DISABLE' in k or 'REQUIRE' in k or k in ['AISOC_SCOPED_BASELINE','AISOC_DEV_MODE','AISOC_AGENT_MEMORY_WRITEBACK','AISOC_AGENT_ESCALATE_TO_GRAPH','AISOC_AGENT_MEMORY_SUPPRESSION','AISOC_INVESTIGATE_USE_ROUTER','AISOC_INVESTIGATOR_MAX_COMPLETION_TOKENS','AISOC_INVESTIGATION_MAX_SECONDS'])}}
 p.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({'started':service,'ready':True,'image_id':x['Image']}))


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('service',choices=['agents','actions']);p.add_argument('--build',action='store_true');a=p.parse_args()
 try:
  if a.build:
   base=json.loads(subprocess.check_output(['docker','image','inspect','python:3.11-slim']))[0]
   assert base['Id']=='sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce'
   subprocess.run(['docker','build','--pull=false','-f',f'deploy/aisoc21/build/Dockerfile.{a.service}','-t',f'socai2-{a.service}:1g-20261020',f'services/{a.service}'],cwd=ROOT/'source',check=True)
  else:start(a.service)
 except Exception as exc:print(json.dumps({'success':False,'error_type':type(exc).__name__}));raise SystemExit(1)
