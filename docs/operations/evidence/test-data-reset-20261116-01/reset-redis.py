"""Delete exact inventoried test keys; no FLUSHDB/FLUSHALL."""
import base64,hashlib,json,os,subprocess,sys
from pathlib import Path
from urllib.parse import urlsplit,unquote
c=json.load(sys.stdin);root=Path(c['backup_root']);root.mkdir(parents=True,exist_ok=True,mode=0o700)
for item in c['targets']:
    env=dict(x.split('=',1) for x in json.loads(subprocess.check_output(['docker','inspect',item['credential_container']]))[0]['Config']['Env'])
    password=env.get('REDIS_PASSWORD','')
    if item.get('credential_file'):password=Path(item['credential_file']).read_text().strip()
    if item.get('credential_url'):password=unquote(urlsplit(env[item['credential_url']]).password or '')
    for inv in c['inventory']:
        if inv['container']!=item['container']:continue
        args=['docker','exec',*(['-e','REDISCLI_AUTH='+password] if password else []),item['container'],'redis-cli','--no-auth-warning','-n',str(inv['database']),'--raw']
        def command(tail):
            p=subprocess.run(args+tail,capture_output=True,timeout=20)
            if p.returncode or p.stdout.startswith((b'NOAUTH',b'WRONGPASS',b'ERR')):raise RuntimeError('redis_command_failed')
            return p.stdout
        before=set(command(['--scan']).decode().splitlines());selected=set(inv['selected']) & before
        unselected=before-selected
        # Expiry may remove an inventoried key; newly created test keys stop cleanup.
        assert not {k for k in before if any(k.startswith(prefix) for prefix in item['prefixes'])}-set(inv['selected'])
        rows=[{'key':k,'pttl':int(command(['PTTL',k])),'dump_base64':base64.b64encode(command(['DUMP',k])[:-1]).decode()} for k in sorted(selected)]
        path=root/(item['container']+'-'+str(inv['database'])+'.json')
        with path.open('x') as f:json.dump(rows,f)
        os.chmod(path,0o600)
        if selected:command(['UNLINK',*sorted(selected)])
        after=set(command(['--scan']).decode().splitlines())
        assert not after & selected
        assert not after-unselected
        print(json.dumps({'container':item['container'],'database':inv['database'],'removed':len(selected),
                          'remaining_test_keys':sum(any(k.startswith(p) for p in item['prefixes']) for k in after),
                          'other_keys_retained_or_naturally_expired':True}),flush=True)
