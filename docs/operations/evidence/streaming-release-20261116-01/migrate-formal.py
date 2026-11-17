"""Apply the audited additive formal migrations once; retain schema/ACL evidence."""
import hashlib,json,os,subprocess,sys,tomllib
from pathlib import Path
root=Path(sys.argv[1]);c=json.loads((root/'config/release.json').read_text());db=c['database'];private=root/'private';cfg=tomllib.loads((root/'config/database-install.toml').read_text())
out={'release':c['release'],'database':db['name'],'steps':[]};stage='preflight'
def run(args,body=None):
 r=subprocess.run(args,input=body,text=True,capture_output=True,timeout=cfg['timeout_seconds'])
 if r.returncode:
  p=private/('migration-error-'+stage+'.log');p.write_text(r.stdout+'\n'+r.stderr);p.chmod(0o600)
  raise RuntimeError('command_failed; private_detail='+str(p))
 return r.stdout
psql=['docker','exec','-i',db['container'],'psql','-wXAtq','-U',db['admin'],'-d',db['name'],'-v','ON_ERROR_STOP=1']
try:
 manifest=json.loads((root/'frozen-manifest.json').read_text())
 for name,expected in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
 rows=json.loads(run(['docker','inspect',*c['must_remain_stopped']]))
 assert all(r['State']['Status'] in {'exited','created'} for r in rows)
 q="SELECT json_build_object('tables',(SELECT count(*) FROM information_schema.tables WHERE table_schema='socai2' AND table_type='BASE TABLE'),'columns',(SELECT count(*) FROM information_schema.columns WHERE table_schema='socai2'),'tasks_installed',to_regclass('socai2.analysis_tasks') IS NOT NULL);"
 out['before']=json.loads(run(psql,q));assert out['before']=={'tables':28,'columns':450,'tasks_installed':False}
 backup=private/'before-formal-schema.sql';assert not backup.exists()
 body=run(['docker','exec',db['container'],'pg_dump','-w','-U',db['admin'],'-d',db['name'],'--schema-only'])
 with backup.open('x') as f:backup.chmod(0o600);f.write(body)
 out['schema_backup']={'path':str(backup),'bytes':len(body.encode()),'sha256':hashlib.sha256(body.encode()).hexdigest()}
 for mode in db['steps']:
  stage=mode
  if mode=='support-access':
   args=psql+['-v','expected_database='+db['name'],'-v','ingress_role='+db['ingress'],'-v','lock_timeout='+str(cfg['analysis_ingress']['lock_timeout_seconds'])+'s','-v','statement_timeout='+str(cfg['analysis_ingress']['statement_timeout_seconds'])+'s']
   response=run(args,(root/'config/fusion-support-access.sql').read_text())
  else:response=run(['python3',str(root/'deploy/database/install_reader.py'),mode,'--profile',str(root/'config/database-install.toml')])
  out['steps'].append({'mode':mode,'exit':0,'stdout':response})
 out['after']=json.loads(run(psql,q));assert out['after']=={'tables':32,'columns':521,'tasks_installed':True}
 out['status']='passed';out['business_service_started']=False;out['model_calls']=0
except Exception as exc:
 out.update(status='failed',stage=stage,error=str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__)
print(json.dumps(out,indent=2));sys.exit(out['status']!='passed')
