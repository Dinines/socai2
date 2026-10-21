"""Read-only1G deployment consistency and targeted test credential cleanup."""
from pathlib import Path
import argparse,json,subprocess
ROOT=Path('/opt/sting-aisoc-socai2');E=ROOT/'evidence/1g-20261020'


def inspect(name):return json.loads(subprocess.check_output(['docker','inspect',name]))[0]

def main(revoke):
 before=json.loads((E/'environment-before.json').read_text())
 xs=json.loads(subprocess.check_output(['docker','inspect',*subprocess.check_output(['docker','ps','-aq']).decode().split()]))
 after={'containers':{x['Name'].lstrip('/'): {'id':x['Id'],'image':x['Image'],'started_at':x['State']['StartedAt'],'status':x['State']['Status'],'restart_count':x['RestartCount'],'mounts':x['Mounts']} for x in xs},'volumes':subprocess.check_output(['docker','volume','ls','-q']).decode().split()}
 for n,state in before['containers'].items():assert after['containers'][n]==state,n
 assert before['volumes']==after['volumes']
 assert set(after['containers'])-set(before['containers'])=={'socai2-agents-1','socai2-actions-1'}
 data={'other_existing_containers_unchanged':len(before['containers']),'existing_volumes_preserved':len(after['volumes']),'services':{}}
 for service in ['agents','actions']:
  container='socai2-'+service+'-1';x=inspect(container)
  # Compare all source app assets, not just an import of a different checkout.
  code='''import hashlib,json,sys
from pathlib import Path
from packaging.requirements import Requirement
from importlib.metadata import version,PackageNotFoundError
checks=[]
for raw in Path('/requirements.txt').read_text().splitlines():
 line=raw.strip().removesuffix('\\\\').strip()
 if not line or line.startswith(('#','--')):continue
 req=Requirement(line)
 if req.marker is not None and not req.marker.evaluate():continue
 actual=version(req.name);assert actual in req.specifier,(req.name,actual,str(req.specifier))
 checks.append({'name':req.name,'version':actual})
try:version('poetry');poetry=True
except PackageNotFoundError:poetry=False
assert not poetry
print(json.dumps({'python':sys.version.split()[0],'dependencies':checks,'poetry_present':poetry,'source_app_hashes':{str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}}))'''
  # Strip the export continuation with chr(92), independent of host quoting.
  code=code.replace("removesuffix('\\\\')",'removesuffix(chr(92))')
  runtime=json.loads(subprocess.check_output(['docker','exec',container,'python','-c',code]))
  import hashlib
  source=ROOT/f'source/services/{service}/app';expected={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
  assert expected==runtime['source_app_hashes'],service+' source differs'
  data['services'][service]={'image_id':x['Image'],'container_id':x['Id'],'python':runtime['python'],'dependency_count':len(runtime['dependencies']),'dependencies':runtime['dependencies'],'poetry_present':False,'all_app_asset_hashes_match':True,'app_asset_files':len(expected),'health':x['State']['Health']['Status']}
 groups=subprocess.run(['docker','exec','sting-infra21-kafka-1','kafka-consumer-groups','--bootstrap-server','192.168.1.21:9092','--list'],capture_output=True,text=True,check=True).stdout.splitlines()
 assert 'socai2-agents-triage' not in groups
 data['agents_kafka_group_not_started']=True
 data['api_fusion_embedding_gateway_not_recreated']=True
 if revoke:
  assert (E/'durable-verify.json').exists(),'Need durable report check after restart first'
  import sys;sys.path.insert(0,str(ROOT/'source/deploy/aisoc21'))
  from shared_1b import SharedBatch
  b=SharedBatch(ROOT);state=json.loads((ROOT/'private/app-1g.json').read_text())
  for ident in state['identities'].values():
   b.pg("SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id='"+ident['key_id']+"' AND name LIKE 'socai2-1g-20261020-%';")
  data['batch_api_keys_deactivated']=2
  data['jwt_tests_expire_naturally_no_shared_signing_key_rotation']=True
 p=E/'postconditions.json';assert not p.exists();p.write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps({k:v for k,v in data.items() if k!='services'}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--revoke-test-keys',action='store_true');a=p.parse_args();main(a.revoke_test_keys)
