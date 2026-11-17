"""Confirm only the API and its Swagger container changed during this release."""
import hashlib,json,subprocess,sys
from pathlib import Path
folder=Path(sys.argv[1]);cfg=json.loads((folder/'profile.json').read_text())
def inspect(name):return json.loads(subprocess.check_output(['docker','inspect',name]))[0]
before=json.loads((folder/'before.json').read_text())
excluded={cfg['container'],'socai2-api-docs-swagger-1'}
names=subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).splitlines()
after={n:{'id':c['Id'],'image':c['Image'],'started_at':c['State']['StartedAt']} for n in names if n not in excluded for c in [inspect(n)]}
assert after=={k:v for k,v in before.items() if k not in excluded}
runtime=inspect(cfg['container']);env=dict(x.split('=',1) for x in runtime['Config']['Env'])
assert env['SOCAI2_HTTP_RELEASE']==cfg['release'] and env['SOCAI2_SERVICE_DATABASE_NAME']==cfg['database']
targets=list(cfg['patches'].values())
code='import hashlib,json;from pathlib import Path;print(json.dumps({p:hashlib.sha256(Path("/app",p).read_bytes()).hexdigest() for p in '+repr(targets)+'}))'
hashes=json.loads(subprocess.check_output(['docker','exec',cfg['container'],'python','-c',code]))
manifest=json.loads((folder/'manifest.json').read_text())
assert all(hashes[p]==manifest['files'][p] for p in targets)
assert runtime['Config']['Cmd'][3]==cfg['entry']
print(json.dumps({'state':'passed','release':env['SOCAI2_HTTP_RELEASE'],'database':env['SOCAI2_SERVICE_DATABASE_NAME'],
    'image':runtime['Image'],'entry':cfg['entry'],'source_sha256':hashes,'other_containers_unchanged':len(after),
    'expected_changed_containers':sorted(excluded)},indent=2))
