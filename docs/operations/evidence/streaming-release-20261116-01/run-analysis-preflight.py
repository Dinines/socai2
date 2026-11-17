import json,subprocess,sys
from pathlib import Path
v=json.load(sys.stdin);root=Path(v['root']);c=json.loads((root/'config/release.json').read_text());p=root/'probes/analysis';p.mkdir(parents=True);(p/'deployment.json').write_text(json.dumps(v['profile']))
base=json.loads((root/'analysis-docker-base.json').read_text())
r=subprocess.run([*base,'--rm','-i','--mount','type=bind,src='+str(p)+',dst=/run/probe,readonly','--entrypoint','python',c['processing_image_tag'],'-B','-'],input=v['probe'],text=True,capture_output=True,timeout=c['command_timeout_seconds'])
if r.returncode:
 log=root/'private/analysis-preflight-error.log';log.write_text(r.stdout+'\n'+r.stderr);log.chmod(0o600);raise RuntimeError('preflight_failed; private_detail='+str(log))
print(json.dumps(json.loads(r.stdout.splitlines()[-1]),indent=2))
