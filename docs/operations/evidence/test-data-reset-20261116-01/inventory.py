"""Read-only inventory for the owner's explicit old-test-data reset."""
import json
import subprocess
import sys
from datetime import datetime, timezone

def run(args, body=None):
    p = subprocess.run(args, input=body, capture_output=True, text=True, timeout=55)
    if p.returncode:
        raise RuntimeError('command_failed: ' + args[0] + ': ' + p.stderr[-500:])
    return p.stdout

def sql(container, role, db, statement):
    return run(['docker', 'exec', '-i', container, 'psql', '-wXAtq', '-v', 'ON_ERROR_STOP=1',
                '-U', role, '-d', db], 'BEGIN READ ONLY;\n'+statement+'\nROLLBACK;')

config = json.load(sys.stdin)
all_ids = run(['docker','ps','-aq']).split()
inspected = json.loads(run(['docker','inspect', *all_ids]))
containers = [{"name": d['Name'].lstrip('/'), 'id':d['Id'], 'image':d['Config']['Image'],
    'status':d['State']['Status'], 'started':d['State']['StartedAt'],
    'mounts':[{k:m[k] for k in ('Type','Source','Destination','RW')} for m in d['Mounts']],
    'pg': {k:v for k,v in (e.split('=',1) for e in d['Config'].get('Env',[]) or [])
           if k in {'POSTGRES_USER','POSTGRES_DB'}}} for d in inspected]
results = {'at':datetime.now(timezone.utc).isoformat(), 'site':config['site'],
           'containers':containers, 'postgres':[]}
for pg in config['postgres']:
    databases = sql(pg['container'], pg['role'], pg['database'],
        "SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate ORDER BY 1;").splitlines()
    result = {**pg, 'databases':databases, 'selected':[]}
    for db in databases:
        if not (db in config['database_names'] or any(db.startswith(x) for x in config['database_prefixes'])):
            continue
        try:
            tables = sql(pg['container'],pg['role'],db,
                "SELECT json_build_object('schema',schemaname,'table',tablename) FROM pg_tables "
                "WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1::text;")
        except RuntimeError as exc:
            result['selected'].append({'database':db,'error':str(exc)})
            continue
        rows=[]
        for line in tables.splitlines():
            t=json.loads(line)
            # Inventory only counts and column names, never raw business or secret values.
            ident='"'+t['schema'].replace('"','""')+'"."'+t['table'].replace('"','""')+'"'
            t['count']=int(sql(pg['container'],pg['role'],db,'SELECT count(*) FROM '+ident+';'))
            rows.append(t)
        fks=sql(pg['container'],pg['role'],db,"SELECT json_build_object('from',conrelid::regclass::text," 
            "'to',confrelid::regclass::text,'name',conname) FROM pg_constraint WHERE contype='f';")
        result['selected'].append({'database':db, 'tables':rows, 'foreign_keys':[json.loads(l) for l in fks.splitlines()]})
    results['postgres'].append(result)
print(json.dumps(results,ensure_ascii=False,indent=2))
