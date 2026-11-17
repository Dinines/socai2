"""Clear only frozen socai2 test lake tables, after saving their original rows."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
c=json.load(sys.stdin);root=Path(c['backup_root']);root.mkdir(parents=True,exist_ok=True,mode=0o700)
auth=[]
if c.get('authentication_from_container_env'):
    env=dict(x.split('=',1) for x in json.loads(subprocess.check_output(['docker','inspect',c['container']]))[0]['Config']['Env'])
    auth=['--user',env['CLICKHOUSE_USER'],'--password',env['CLICKHOUSE_PASSWORD']]
def query(sql):
    p=subprocess.run(['docker','exec',c['container'],'clickhouse-client',*auth,'--query',sql],capture_output=True,timeout=45)
    if p.returncode:raise RuntimeError(p.stderr.decode()[-400:])
    return p.stdout
for table in c['tables']:
    assert table.count('.')==1 and all(part.replace('_','').isalnum() for part in table.split('.'))
    before=int(query('SELECT count() FROM '+table));schema=query('SHOW CREATE TABLE '+table)
    data=query('SELECT * FROM '+table+' FORMAT JSONEachRow')
    path=root/(table+'.jsonl')
    with path.open('xb') as f:f.write(data)
    os.chmod(path,0o600)
    query('TRUNCATE TABLE '+table)
    after=int(query('SELECT count() FROM '+table));assert after==0
    assert query('SHOW CREATE TABLE '+table)==schema
    print(json.dumps({'table':table,'before':before,'after':after,'schema_unchanged':True,
                      'backup_sha256':hashlib.sha256(data).hexdigest()}),flush=True)
