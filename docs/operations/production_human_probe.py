"""Run one scoped H service operation with the current processing identity.

This acceptance adapter uses the deployed HumanTaskService, not a raw SQL write
or an HTTP-write acceptance claim. Credentials and the request cross stdin;
only a typed service receipt is retained. A pre-existing intent is never retried.
"""
import argparse
import hashlib
import json
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from production_case_probe import save

INNER = r'''
import asyncio,json,os,sys,tempfile
from pathlib import Path
from uuid import UUID
sys.path.insert(0,'/opt/processor')
import production_job as job

async def main(p):
 from app.db.database import AsyncSessionLocal,engine
 from app.socai2.baseline_contracts import Actor
 from app.socai2.human_task_contracts import TaskCreate,TaskEdit
 from app.socai2.human_task_service import HumanTaskService
 keyfile=None
 try:
  _,_,tenant,actor=await job.verify_target()
  await job.verify_sources(tenant)
  with tempfile.NamedTemporaryFile(mode='w',prefix='socai2-h-key-',delete=False) as f:
   f.write(p['key'])
   keyfile=Path(f.name)
  os.environ['SOCAI2_PROCESSING_API_KEY_FILE']=str(keyfile)
  user=await job.principal(tenant,actor,'cases:write')
  request=(TaskEdit if p['task_id'] else TaskCreate).model_validate(p['request'])
  result=await HumanTaskService(AsyncSessionLocal).write(tenant,UUID(p['case_id']),request,
   actor=Actor(user_id=user.user_id,name=user.email),task_id=UUID(p['task_id']) if p['task_id'] else None)
  return result.model_dump(mode='json')
 finally:
  if keyfile is not None:
   keyfile.unlink(missing_ok=True)
  await engine.dispose()
try:
 result=asyncio.run(main(json.load(sys.stdin)))
except Exception as exc:
 result={'error':str(exc) if isinstance(exc,job.Refused) or exc.__class__.__module__=='app.socai2.baseline_store' else type(exc).__name__}
print(json.dumps(result,ensure_ascii=False))
sys.exit(1 if 'error' in result else 0)
'''

HOST = r'''
import json,subprocess,sys
from pathlib import Path
p=json.load(sys.stdin)
try:
 profile_path=Path(p['transport']['processing_profile_file']).resolve(strict=True)
 sys.path.insert(0,str(profile_path.parent))
 import production_processing as runtime
 profile=runtime.select_profile(profile_path)
 runtime.image_check()
 envfile=Path(profile.paths.private_dir)/'runtime.env'
 runtime.secure_file(envfile)
 saved=dict(line.split('=',1) for line in envfile.read_text().splitlines() if '=' in line)
 runtime.need(saved.get('SOCAI2_PROCESSING_PROFILE_SHA256')==profile.sha256 and saved.get('SOCAI2_INVESTIGATION_POLICY_SHA256')==profile.policy_sha256,'installed_profile_or_policy_changed')
 argv=[p['transport']['remote_docker'],'run','--rm','-i','--pull=never','--network',profile.docker.network,
  '--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--memory='+profile.docker.memory,
  '--pids-limit='+str(profile.docker.pids_limit),'--tmpfs',profile.docker.tmpfs,'--env-file',str(envfile),
  '-e','SOCAI2_PROCESSING_TENANT_ID='+p['tenant'],'-e','SOCAI2_PROCESSING_ACTOR_ID='+p['actor']]
 for local,remote in ((profile_path.parent/'processing_job.py','/opt/processor/production_job.py'),
   (Path(profile.paths.ca_file),profile.paths.ca_mount),(Path(profile.paths.policy_file),profile.paths.policy_mount)):
  runtime.need(local.is_file(),'processing_mount_missing')
  argv+=['--mount','type=bind,src='+str(local)+',dst='+remote+',readonly']
 argv+=['--entrypoint','python',profile.image.id,'-B','-c',p['inner']]
 result=subprocess.run(argv,input=json.dumps(p['operation']),text=True,capture_output=True,check=False,
  timeout=p['transport']['command_timeout_seconds'])
 bodies=[]
 for line in result.stdout.splitlines():
  try: bodies.append(json.loads(line))
  except ValueError: pass
 out={'exit_code':result.returncode,'receipt':bodies[-1] if bodies else {'error':'missing_h_receipt'},
  'profile_sha256':profile.sha256,'policy_sha256':profile.policy_sha256,'image_id':profile.image.id}
except Exception as exc:
 out={'error':type(exc).__name__,'inspection_required':True}
print(json.dumps(out,ensure_ascii=False))
'''


def run(config_path, request_path, output, case_id, task_id=None):
    cfg = json.loads(config_path.read_text())
    t, target = cfg['transport'], cfg['target']
    request = json.loads(request_path.read_text())
    output.mkdir(parents=True, exist_ok=False)
    keyfile = Path(target['user_api_key_file'])
    if keyfile.stat().st_mode & 0o077:
        raise ValueError('private_credential_file_required')
    key = json.loads(keyfile.read_text())[target['user_api_key_json_path']]
    assert key.startswith('aisoc_')
    save(output / 'intent.json', {'at': datetime.now(UTC).isoformat(), 'case_id': str(UUID(case_id)),
        'task_id': str(UUID(task_id)) if task_id else None, 'request': request,
        'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'mode': 'deployed_HumanTaskService_with_authenticated_processor', 'model_calls': 0})
    payload = {'transport': t, 'tenant': target['tenant_id'], 'actor': target['actor_id'], 'inner': INNER,
        'operation': {'key': key, 'case_id': case_id, 'task_id': task_id, 'request': request}}
    result = subprocess.run([t['ssh_binary'], '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UpdateHostKeys=no', '-o', f"ConnectTimeout={t['connect_timeout_seconds']}", t['ssh_target'],
        shlex.join([t['remote_python'], '-c', HOST])], input=json.dumps(payload), text=True, capture_output=True,
        timeout=t['command_timeout_seconds'] + t['connect_timeout_seconds'], check=False)
    if result.returncode:
        raise RuntimeError('H_transport_uncertain_inspect_before_retry')
    receipt = json.loads(result.stdout)
    save(output / 'receipt.json', {'at': datetime.now(UTC).isoformat(), **receipt})
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if receipt.get('exit_code') == 0 and 'task' in receipt.get('receipt', {}) else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--task')
    args = parser.parse_args()
    raise SystemExit(run(args.config, args.request, args.output, args.case, args.task))
