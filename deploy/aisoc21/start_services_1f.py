#!/usr/bin/env python3
"""Run the strict owner migration check, then start only socai2 API/Fusion."""
import json
from pathlib import Path
import time
import urllib.request

from shared_1b import SharedBatch

ROOT = Path('/opt/sting-aisoc-socai2')


def main():
    b=SharedBatch(ROOT)
    app=json.loads((ROOT/'private/app-1f.json').read_text())
    b.secrets.extend(v for v in app.values() if isinstance(v,str))
    b.secrets.extend(i['key'] for i in app['identities'].values())
    evidence=ROOT/'evidence/1f-20261020'
    command=['docker','run','--rm','--pull','never','--network','socai2_default',
             '--env-file',str(ROOT/'private/migrate-1f.env'),'--mount',
             'type=bind,src='+str(ROOT/'certificates/socai2-ca.crt')+',dst=/run/certs/ca.crt,readonly',
             'socai2-api:1f-20261020','python','-m','app.scripts.run_migrations']
    result=b.run(command,allow_error=True)
    log=b.redact(result.stdout+result.stderr)
    (evidence/'migrations.log').write_text(log)
    if result.returncode:
        raise RuntimeError('Strict migration check failed: '+log[-1200:])
    if 'Found 134 migration files' not in log or '134 migrations already applied; 0 pending' not in log:
        raise RuntimeError('Unexpected migration filename set; retained evidence, no app startup')
    compose=['docker','compose','--project-directory',str(ROOT),'-f',
             str(ROOT/'source/deploy/aisoc21/compose.services.yml')]
    b.run(compose+['config','--quiet'])
    b.run(compose+['up','-d','--pull','never','api','fusion'])
    ready={}
    for attempt in range(50):
        for name,port in [('api',18000),('fusion',18003)]:
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/readyz',timeout=2) as response:
                    ready[name]=json.loads(response.read()) if response.status==200 else None
            except Exception:ready[name]=None
        if all(ready.values()):break
        time.sleep(1)
    containers={}
    for name in ('api','fusion'):
        container='socai2-'+name+'-1'
        output=b.run(['docker','logs',container],allow_error=True)
        (evidence/('startup-'+name+'.log')).write_text(b.redact(output.stdout+output.stderr))
        item=b.inspect(container)
        containers[name]={'name':container,'id':item['Id'],'image_id':item['Image'],
                          'status':item['State']['Status'],'started_at':item['State']['StartedAt'],
                          'user':item['Config']['User'],'ports':item['HostConfig']['PortBindings'],
                          'read_only':item['HostConfig']['ReadonlyRootfs']}
    record={'migration_exit':result.returncode,'full_migration_set_checked':134,
            'migration_ledger_existing':134,'pending':0,'required':True,'strict':True,
            'owner_used_only_by_migration_container':True,'ready':ready,'containers':containers}
    (evidence/'startup.json').write_text(json.dumps(record,indent=2)+'\n')
    if not all(ready.values()):raise RuntimeError('Service not ready; inspect sanitized startup logs')
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
