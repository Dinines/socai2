"""Prepare this release's private runtime files; no business service or DB mutation."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from urllib.parse import quote,urlsplit,urlunsplit,parse_qsl,urlencode

root=Path(sys.argv[1]);c=json.loads((root/'config/release.json').read_text());assert str(root)==c['root']
private=root/'private';private.mkdir(mode=0o700)
uid=tuple(int(v) for v in c['user'].split(':'))

def save(path,body,*,secret=False,owned=False):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x') as f:
  path.chmod(0o600 if secret else 0o644);f.write(body)
 if owned:os.chown(path,*uid)
def inspect(ref):
 r=json.loads(subprocess.check_output(['docker','inspect',ref['name']],text=True,timeout=c['command_timeout_seconds']))[0]
 assert r['Id']==ref['id'] and r['State']['Status']=='exited'
 return dict(v.split('=',1) for v in r['Config']['Env'] if '=' in v)
def env_file(path):return dict(v.split('=',1) for v in Path(path).read_text().splitlines() if v and not v.startswith('#') and '=' in v)
def validate_url(value,*,host,port,path,user):
 u=urlsplit(value);assert (u.hostname,u.port,u.path,u.username)==(host,port,path,user) and u.password
 return value
p=c['private_sources'];oldhttp=inspect(p['http_container']);oldfusion=inspect(p['fusion_container']);source=env_file(p['runtime']);db=c['database']
def db_url(role,secret,driver):
 password=Path(secret).read_text().strip();assert password and '\n' not in password
 return f"{driver}://{role}:{quote(password,safe='')}@{db['host']}:{db['port']}/{db['name']}"
writer=db_url(db['processor'],p['processor_password'],'postgresql+asyncpg')
ingress=db_url(db['ingress'],p['ingress_password'],'postgresql')+'?'+urlencode({'sslmode':db['sslmode']})
reader=validate_url(oldhttp['DATABASE_URL'],host=db['host'],port=db['port'],path='/'+db['name'],user=db['reader'])
u=urlsplit(reader)
query=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if k not in {'sslmode','ssl','sslrootcert','sslcert','sslkey'}]
reader=urlunsplit(u._replace(query=urlencode([*query,('sslmode',db['sslmode'])])))
analysis=json.loads((root/'config/analysis-env.json').read_text());fusion=json.loads((root/'config/fusion-env.json').read_text());http={}
for k in c['secret_env_keys']:
 assert source.get(k);analysis[k]=source[k];http[k]=source[k]
for target,old,key in [(analysis,oldhttp,'analysis'),(fusion,oldfusion,'fusion')]:
 r=c[key];target['REDIS_URL']=validate_url(old['REDIS_URL'],host=r['redis_host'],port=r['redis_port'],path='/'+str(r['redis_db']),user=r['redis_user'])
fusion.update(DATABASE_URL=ingress,CLICKHOUSE_PASSWORD=oldfusion['CLICKHOUSE_PASSWORD'])
analysis.update(DATABASE_URL=writer,SOCAI2_CASE_DATABASE_URL=writer,OPENAI_API_KEY=source[c['model']['key_name']],OPENAI_BASE_URL=c['model']['base_url'],OPENAI_MODEL=c['model']['alias'],CLICKHOUSE_PASSWORD=Path(p['lake_password']).read_text().strip())
http.update(DATABASE_URL=reader,SOCAI2_CASE_DATABASE_URL=writer,REDIS_URL=analysis['REDIS_URL'])
for name,env in [('analysis',analysis),('fusion',fusion)]:
 assert all(isinstance(v,str) and '\n' not in v and '\r' not in v for v in env.values())
 save(private/(name+'.env'),''.join(k+'='+v+'\n' for k,v in sorted(env.items())),secret=True)
save(private/'http-runtime.json',json.dumps(http)+'\n',secret=True)
save(private/'analysis-database-url',writer+'\n',secret=True,owned=True)
save(private/'analysis-redis-url',analysis['REDIS_URL']+'\n',secret=True,owned=True)
save(private/'qdrant-key',Path(p['qdrant_key']).read_text(),secret=True,owned=True)
for path in sorted((root/'config/analysis').iterdir()):save(root/'analysis/config'/path.name,path.read_text())
state=root/'analysis/state';state.mkdir();os.chown(state,*uid)
for kind in ['analysis','fusion']:
 s=c[kind]
 base=['docker','run','--network',c['network'],'--workdir',s['workdir'],'--user',c['user'],'--memory',s['memory'],'--pids-limit',str(s['pids_limit']),'--env-file',str(private/(kind+'.env'))]
 if kind=='analysis':
  for src,dst,ro in [(root/'analysis/config','/run/analysis',True),(state,'/var/lib/analysis',False),(private/'analysis-database-url','/run/secrets/analysis-database-url',True),(private/'analysis-redis-url','/run/secrets/analysis-redis-url',True),(private/'qdrant-key','/run/knowledge/qdrant-key',True)]:
   base+=['--mount','type=bind,src='+str(src)+',dst='+dst+(',readonly' if ro else '')]
 else:
  for src,dst in [(s['ca_source'],s['ca_target']),(root/'config/initial-task-policy.json','/run/config/initial-task-policy.json')]:
   base+=['--mount','type=bind,src='+str(src)+',dst='+str(dst)+',readonly']
 save(root/(kind+'-docker-base.json'),json.dumps(base,indent=2)+'\n')
print(json.dumps({'status':'prepared','release':c['release'],'database':db['name'],'reader':db['reader'],'processor':db['processor'],'ingress':db['ingress'],'private_files':[{'name':p.name,'mode':oct(p.stat().st_mode&0o777)} for p in sorted(private.iterdir())],'analysis_config_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'analysis/config').iterdir())},'services_changed':False,'database_writes':0,'model_calls':0},indent=2))
