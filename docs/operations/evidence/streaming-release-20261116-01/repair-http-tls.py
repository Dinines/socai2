"""Apply the selected release TLS mode to its copied reader DSN only."""
import json, os, shutil, subprocess, sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

root=Path(sys.argv[1]); cfg=json.loads((root/'config/release.json').read_text())
hp=json.loads((root/'config/http-profile.json').read_text())
assert str(root)==cfg['root'] and cfg['database']['sslmode']==hp['postgres_sslmode']=='require'
c=json.loads(subprocess.check_output(['docker','inspect',hp['container']]))[0]
assert c['Id']=='8b163e42e61a8e7117c1ea7d03e0253fa901fe02a3d9f91771b2f79f87f5bdb7'
assert not c['State']['Running'] and c['Image']=='sha256:f3f43ebaeedf2438498dcc13bd7e2b99934d0ae599e528b0b8e7a06c264439e4'
backup=root/'private/http-start-failure';backup.mkdir(mode=0o700)
(backup/'inspect.json').write_text(json.dumps(c));(backup/'inspect.json').chmod(0o600)
r=subprocess.run(['docker','logs',c['Id']],capture_output=True,timeout=20)
(backup/'logs.txt').write_bytes(r.stdout+r.stderr);(backup/'logs.txt').chmod(0o600)
paths=[root/'private/http-runtime.json',root/'http/private'/hp['release']/'runtime.env']
changed=[]
for path in paths:
 is_json=path.suffix=='.json'
 env=json.loads(path.read_text()) if is_json else dict(v.split('=',1) for v in path.read_text().splitlines())
 u=urlsplit(env['DATABASE_URL'])
 assert (u.hostname,u.port,u.path,u.username)==(cfg['database']['host'],cfg['database']['port'],'/'+cfg['database']['name'],cfg['database']['reader'])
 before=dict(parse_qsl(u.query));assert before=={'sslmode':'verify-full'}
 env['DATABASE_URL']=urlunsplit(u._replace(query=urlencode({'sslmode':cfg['database']['sslmode']})))
 shutil.copy2(path,backup/path.name)
 body=json.dumps(env)+'\n' if is_json else ''.join(k+'='+v+'\n' for k,v in sorted(env.items()))
 tmp=path.with_name(path.name+'.corrected')
 with tmp.open('x') as f:tmp.chmod(0o600);f.write(body)
 os.replace(tmp,path);changed.append(str(path.relative_to(root)))
print(json.dumps({'status':'configured_not_started','release':cfg['release'],'failed_container_id':c['Id'],'error':'PG root certificate required by inherited verify-full DSN','before_sslmode':'verify-full','after_sslmode':cfg['database']['sslmode'],'changed_files':changed,'changed_key':'DATABASE_URL.sslmode','target_role_password_unchanged':True,'image_unchanged':True,'private_backup':str(backup),'business_writes':0},indent=2))
