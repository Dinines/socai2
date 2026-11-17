"""Register the disabled neutral routing connector once; no alert/Case writes."""
import json,shlex,subprocess
from pathlib import Path
E=Path(__file__).resolve().parent;p=json.loads((E/'batch/profile.json').read_text())
code='''import json,subprocess,sys
from pathlib import Path
from uuid import UUID
folder=Path(sys.argv[1]);p=json.loads((folder/'profile.json').read_text());c=json.loads((Path(p['release_root'])/'config/release.json').read_text());r=p['connector'];UUID(r['id']);UUID(p['tenant_id'])
with (folder/'out/connector-intent.json').open('x') as f:json.dump({'state':'started_outcome_unknown','connector':r},f)
def q(s):return "'"+s.replace("'","''")+"'"
sql='BEGIN; INSERT INTO public.connectors(id,tenant_id,name,connector_type,category,is_enabled) VALUES('+','.join(q(x) for x in [r['id'],p['tenant_id'],r['name'],r['connector_type'],r['category']])+',false); SELECT row_to_json(t) FROM (SELECT id,tenant_id,name,connector_type,category,is_enabled FROM public.connectors WHERE id='+q(r['id'])+'::uuid) t; COMMIT;'
v=subprocess.run(['docker','exec','-i',c['database']['container'],'psql','-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-U',c['database']['admin'],'-d',c['database']['name']],input=sql,capture_output=True,text=True,timeout=30)
assert v.returncode==0,'connector_configuration_failed'
row=json.loads(v.stdout);assert row['id']==r['id'] and row['tenant_id']==p['tenant_id']
with (folder/'out/connector.json').open('x') as f:json.dump(row,f,indent=2)
print(json.dumps(row))
'''
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12',p['ssh_target'],shlex.join(['python3','-c',code,p['remote_directory']])],capture_output=True,text=True,timeout=45)
with (E/'connector.json').open('x') as f:json.dump({'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},f,indent=2)
print(r.stdout);assert r.returncode==0
