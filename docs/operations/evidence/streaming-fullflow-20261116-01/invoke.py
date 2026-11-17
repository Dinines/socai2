"""Explicit local-to-21 entry for one selected batch action; never retries."""
import json,shlex,subprocess,sys
from pathlib import Path
E=Path(__file__).resolve().parent;p=json.loads((E/'batch/profile.json').read_text());action=sys.argv[1];step=sys.argv[2]
if action=='start':
    code=(E/'runtime-start.py').read_text();argv=['python3','-c',code,p['release_root'],step];payload=None
elif action=='probe':
    inner=(E/'live-probe.py').read_text()
    code=r'''import hashlib,json,os,subprocess,sys,urllib.request
from pathlib import Path
folder=Path(sys.argv[1]);step=sys.argv[2];p=json.loads((folder/'profile.json').read_text());c=json.loads((Path(p['release_root'])/'config/release.json').read_text());m=json.loads((folder/'manifest.json').read_text())
def inspect(name):return json.loads(subprocess.check_output(['docker','inspect',name]))[0]
if step=='preflight':
 for name in c['must_remain_stopped']:assert not inspect(name)['State']['Running']
 for name in p['containers'].values():assert inspect(name)['State']['Running']
 with urllib.request.urlopen('http://'+c['fusion']['bind']+':'+str(c['fusion']['port'])+'/readyz',timeout=5) as response:ready=json.load(response)
 assert ready['status']=='ready' and ready['subscriptions']==['alerts+raw_events']
if step.endswith('context-readback'):
 phase=step.split('-')[0]+'-context';p['readback_events']=[json.loads((folder/r['wire']).read_text()) for r in m['phases'][phase]['records']]
r=subprocess.run(['docker','exec','-i',p['containers']['analysis'],'python','-c',sys.stdin.read(),step],input=json.dumps(p),capture_output=True,text=True,timeout=45)
if r.returncode:
 private=Path(p['release_root'])/'private';private.mkdir(exist_ok=True)
 path=private/('probe-'+step+'-'+str(len(list(private.glob('probe-*'))))+'.txt')
 with path.open('x') as f:path.chmod(0o600);f.write(r.stdout+'\n'+r.stderr)
 raise RuntimeError('probe_failed_private_log:'+str(path))
out=json.loads(r.stdout);out['prepared_manifest_sha256']=hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest()
if step=='preflight':out.update(source='actual_release_preflight',fusion_ready=True,unique_execution_services=True)
if step.endswith('context-readback'):out['context_receipt_sha256']=hashlib.sha256((folder/'out'/('send-'+step.split('-')[0]+'-context.json')).read_bytes()).hexdigest()
if step=='preflight' or step.endswith('context-readback'):
 with (folder/'out'/(step+'.json')).open('x') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out,ensure_ascii=False))
'''
    argv=['python3','-c',code,p['remote_directory'],step];payload=inner
elif action=='send':
    code='''import json,subprocess,sys
from pathlib import Path
folder=Path(sys.argv[1]);p=json.loads((folder/'profile.json').read_text());prior=Path(p['prior_runtime_root'])
cmd=['docker','run','--rm','--network',p['network'],'--user',p['user'],'--env','PYTHONDONTWRITEBYTECODE=1',
 '--mount','type=bind,src='+str(folder)+',dst=/batch,readonly','--mount','type=bind,src='+str(folder/'out')+',dst=/batch/out',
 '--mount','type=bind,src='+str(prior/'private/producer.env')+',dst=/run/producer.env,readonly',
 '--mount','type=bind,src='+p['ca_source']+',dst='+p['ca_target']+',readonly','--entrypoint','python',p['processing_image'],'/batch/send-batch.py',sys.argv[2]]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=50);print(r.stdout);assert r.returncode==0,r.stderr
'''
    argv=['python3','-c',code,p['remote_directory'],step];payload=None
else:raise ValueError(action)
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12',p['ssh_target'],shlex.join(argv)],input=payload,capture_output=True,text=True,timeout=60)
name=action+'-'+step+'-'+str(len(list(E.glob(action+'-'+step+'-*.json')))+1)+'.json'
with (E/name).open('x') as f:json.dump({'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},f,ensure_ascii=False,indent=2)
if r.returncode:print(json.dumps({'exit':r.returncode,'receipt':name}));raise SystemExit(r.returncode)
value=json.loads(r.stdout)
if action=='send':value={k:value[k] for k in ('phase','status','requested','accepted','not_attempted','cleanup_errors')}
elif action=='probe':value={k:v for k,v in value.items() if k!='lake_rows'}
print(json.dumps(value,ensure_ascii=False,indent=2))
