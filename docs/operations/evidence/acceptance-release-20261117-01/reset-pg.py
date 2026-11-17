"""Execute one frozen, owner-authorized list of test tables. No CASCADE/drop."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

c=json.load(sys.stdin)
root=Path(c['backup_root']);root.mkdir(parents=True,exist_ok=True,mode=0o700)
def call(args,body=None):
    p=subprocess.run(args,input=body,capture_output=True,timeout=55)
    if p.returncode:
        raise RuntimeError(p.stderr.decode()[-700:])
    return p.stdout
def quote(s): return '"'+s.replace('"','""')+'"'
results=[]
for item in c['databases']:
    key=item['container']+'--'+item['database']
    receipt=root/(key+'.receipt.json')
    if receipt.exists():
        raise RuntimeError('already_executed_use_saved_receipt')
    base=['docker','exec','-i',item['container']]
    sql=base+['psql','-wXAtq','-v','ON_ERROR_STOP=1','-U',item['role'],'-d',item['database']]
    tables=[quote(t['schema'])+'.'+quote(t['table']) for t in item['tables']]
    if not tables:
        continue
    countsql=' UNION ALL '.join("SELECT '"+t['schema']+'.'+t['table']+"',count(*) FROM "+q for t,q in zip(item['tables'],tables))+';'
    before=call(sql,('BEGIN READ ONLY;'+countsql+'COMMIT;').encode()).decode()
    schema=call(base+['pg_dump','-U',item['role'],'-d',item['database'],'--schema-only','--no-owner','--no-privileges'])
    args=base+['pg_dump','-U',item['role'],'-d',item['database'],'--data-only','--format=custom']
    for t in tables:args.extend(['--table',t])
    backup=call(args)
    backup_path=root/(key+'.dump')
    with backup_path.open('xb') as f:f.write(backup)
    os.chmod(backup_path,0o600)
    with (root/(key+'.schema.sql')).open('xb') as f:f.write(schema)
    request='BEGIN;SET LOCAL lock_timeout=\'3s\';SET LOCAL statement_timeout=\'45s\';TRUNCATE TABLE '+','.join(tables)+';'+countsql+'COMMIT;'
    after=call(sql,request.encode()).decode()
    assert all(line.endswith('|0') for line in after.splitlines()),after
    schema_after=call(base+['pg_dump','-U',item['role'],'-d',item['database'],'--schema-only','--no-owner','--no-privileges'])
    def stable(data):
        return b'\n'.join(line for line in data.splitlines() if not line.startswith((b'\\restrict ',b'\\unrestrict ')))
    assert stable(schema)==stable(schema_after),'schema_changed'
    result={"container":item['container'],"database":item['database'],"tables":len(tables),
        "rows_before":{line.rsplit('|',1)[0]:int(line.rsplit('|',1)[1]) for line in before.splitlines()},
        "rows_after":0,"schema_unchanged":True,"backup":str(backup_path),
        "backup_sha256":hashlib.sha256(backup).hexdigest(),"at":datetime.now(timezone.utc).isoformat()}
    receipt.write_text(json.dumps(result,indent=2)+'\n');os.chmod(receipt,0o600)
    results.append(result)
    print(json.dumps(result),flush=True)
