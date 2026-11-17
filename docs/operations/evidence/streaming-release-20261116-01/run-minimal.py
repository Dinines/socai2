"""Run the separately frozen one-batch entry in the audited processing image."""
import json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);phase=sys.argv[2];cfg=json.loads((root/'config/release.json').read_text())
batch=root/'verification/release-smoke-20261116-01';profile=json.loads((batch/'profile.json').read_text())
assert phase in {'validate','context','alert'} and profile['release']==cfg['release']
cmd=['docker','run','--rm','--network',profile['network'],'--user',cfg['user'],'--read-only','--env','PYTHONDONTWRITEBYTECODE=1','--workdir','/batch','--mount','type=bind,src='+str(batch)+',dst=/batch,readonly','--mount','type=bind,src='+str(batch/'out')+',dst=/batch/out','--mount','type=bind,src='+str(root/'private/producer.env')+',dst=/run/producer.env,readonly','--mount','type=bind,src='+profile['ca_source']+',dst='+profile['ca_target']+',readonly','--entrypoint','python',profile['processing_image'],'/batch/send-minimal.py',phase]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=cfg['command_timeout_seconds'])
print(r.stdout,end='')
if r.returncode:
 print(r.stderr,file=sys.stderr);raise SystemExit(r.returncode)
