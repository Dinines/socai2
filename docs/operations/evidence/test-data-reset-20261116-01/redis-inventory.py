"""Inventory only selected Redis DBs; credentials and key payloads stay private."""
import json,subprocess,sys,hashlib
from pathlib import Path
from urllib.parse import urlsplit,unquote
c=json.load(sys.stdin);results=[]
for item in c['targets']:
    env=dict(x.split('=',1) for x in json.loads(subprocess.check_output(['docker','inspect',item['credential_container']]))[0]['Config']['Env'])
    password=env.get('REDIS_PASSWORD','')
    if item.get('credential_file'):password=Path(item['credential_file']).read_text().strip()
    if item.get('credential_url'):
        url=urlsplit(env[item['credential_url']]);password=unquote(url.password or '')
    for db in item['databases']:
        args=['docker','exec',*(['-e','REDISCLI_AUTH='+password] if password else []),item['container'],'redis-cli','--no-auth-warning','-n',str(db),'--raw']
        p=subprocess.run(args+['--scan'],capture_output=True,timeout=20)
        if p.returncode or b'NOAUTH' in p.stdout or b'WRONGPASS' in p.stderr:raise RuntimeError('redis_auth_failed:'+item['container']+':'+str(db))
        keys=p.stdout.decode().splitlines();selected=[k for k in keys if any(k.startswith(prefix) for prefix in item['prefixes'])]
        results.append({'container':item['container'],'database':db,'total':len(keys),'selected':selected,
                        'preserved_keys_sha256':hashlib.sha256(json.dumps(sorted(set(keys)-set(selected))).encode()).hexdigest()})
print(json.dumps(results,indent=2))
