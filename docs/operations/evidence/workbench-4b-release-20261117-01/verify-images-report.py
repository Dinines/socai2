"""Verify built image contents, then report existing records in a networkless container."""
import hashlib,json,subprocess
from pathlib import Path
c=CONFIG;root=Path(c['remote_root']);images=json.loads((root/'images.json').read_text());package=Path(images['package'])
def run(args):
 r=subprocess.run(args,text=True,capture_output=True,timeout=c['command_timeout_seconds'])
 if r.returncode:raise RuntimeError('command_failed:'+args[0]+':'+str(r.returncode)+':'+r.stderr[-800:])
 return r.stdout
check="""import hashlib,json,sys
from pathlib import Path
p=Path.cwd();m=json.loads((p/'package-manifest.json').read_text())
for name,item in m['files'].items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==item['sha256'],name
print(json.dumps({'files':len(m['files']),'version':m['service_version'],'manifest_sha256':hashlib.sha256((p/'package-manifest.json').read_bytes()).hexdigest(),'python':sys.version.split()[0]}))
"""
checks={}
for kind,item in images['images'].items():
 actual=json.loads(run(['docker','image','inspect',item['tag']]))[0];assert actual['Id']==item['id']
 result=json.loads(run(['docker','run','--rm','--network','none','--read-only','--user',c['user'],'--entrypoint','python',item['tag'],'-c',check]))
 assert result['version']==c['version'] and result['manifest_sha256']==images['package_manifest_sha256']
 checks[kind]=result
mounts=INPUT['acceptance_mounts'];results=Path(mounts['ACCEPTANCE_RESULTS_DIR']);prepared=results/'prepared'
assert hashlib.sha256((prepared/'session.json').read_bytes()).hexdigest()==INPUT['prepared_sha256']
public=root/'report-config';public.mkdir();(public/'report.json').write_bytes((package/'deploy/investigation-test/releases'/c['release']/'report.json').read_bytes())
output=root/'report-output';output.mkdir();uid,gid=map(int,c['user'].split(':'))
import os
os.chown(output,uid,gid)
args=['docker','run','--rm','--network','none','--read-only','--user',c['user'],'--cap-drop','ALL','--security-opt','no-new-privileges:true','--memory',c['memory'],'--pids-limit',str(c['pids_limit']),'--tmpfs',c['tmpfs'],
 '--mount','type=bind,src='+mounts['ACCEPTANCE_MATERIALS_DIR']+',dst='+mounts['ACCEPTANCE_MATERIALS_TARGET']+',readonly',
 '--mount','type=bind,src='+str(results)+',dst='+mounts['ACCEPTANCE_RESULTS_TARGET']+',readonly',
 '--mount','type=bind,src='+str(public)+',dst=/run/report-config,readonly',
 '--mount','type=bind,src='+str(output)+',dst=/report-output',c['acceptance_image'],'report','--prepared',mounts['ACCEPTANCE_RESULTS_TARGET']+'/prepared','--output','/report-output/report-01','--report-config','/run/report-config/report.json']
summary=json.loads(run(args));report=json.loads((output/'report-01/report.json').read_text());manifest=json.loads((output/'report-01/manifest.json').read_text())
assert not any(report['this_command'].values())
case=next(s for s in report['subjects'] if s['kind']=='case' and s['id']==c['case_id'])
assert [r['run_id'] for r in case['rounds']]==c['case_run_ids']
assert [r['scope']['selected_count'] for r in case['rounds']]==[1,2]
for item in manifest['files']:assert hashlib.sha256((output/'report-01'/item['path']).read_bytes()).hexdigest()==item['sha256']
assert hashlib.sha256((prepared/'session.json').read_bytes()).hexdigest()==INPUT['prepared_sha256']
out={'status':'passed_images_and_offline_report','image_checks':checks,'summary':summary,'case_rounds':[{k:r[k] for k in ['round','run_id','viewer_url']} for r in case['rounds']],'report_directory':str(output/'report-01'),'network':'none','connection_secrets_mounted':False,'prepared_mount_readonly':True,'report_manifest_sha256':hashlib.sha256((output/'report-01/manifest.json').read_bytes()).hexdigest(),'services_changed':False}
(root/'images-and-report-verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
