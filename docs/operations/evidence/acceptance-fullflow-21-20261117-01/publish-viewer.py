"""Publish this run's evidence through the existing offline ledger CLI, once."""
import base64
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REMOTE = r'''
import base64,hashlib,json,subprocess,sys
from pathlib import Path
x=json.load(sys.stdin);c=x['target'];options=x['options'];root=Path(c['release_root']);stage=Path(c['stage_root'])
config=json.loads((root/'config/release.json').read_text());ready=json.loads((root/'deployment-ready.json').read_text());wanted=ready['services']['viewer']
running=json.loads(subprocess.check_output(['docker','inspect',wanted['name']]))[0]
assert running['Id']==wanted['id'] and running['Image']==wanted['image'] and running['State']['Running']
mounts={m['Source']:m['Destination'] for m in running['Mounts']};configs=root/'viewer/config';state=Path(config['viewer']['state_root'])
service=json.loads((configs/'service.json').read_text());assert service['ledger_root']==mounts[str(state)]+'/ledger'
assert service['environment_label']==config['release']
ledger=state/'ledger';assert not (ledger/options['batch_id']/'current.json').exists()
before={str(p.relative_to(ledger)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ledger.rglob('*') if p.is_file()}
folder=stage/options['input_directory'];folder.mkdir()
for name,item in x['files'].items():
 assert Path(name).name==name
 raw=base64.b64decode(item['content']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
 assert len(raw)<=service['max_document_bytes' if name=='document.json' else 'max_evidence_bytes']
 with (folder/name).open('xb') as f:f.write(raw)
 (folder/name).chmod(0o644)
document=json.loads((folder/'document.json').read_text());assert document['batch']['id']==options['batch_id'] and document['batch']['execution_state']=='finished'
receipt_path=stage/'viewer-publication.json'
with receipt_path.open('x') as f:json.dump({'status':'started_outcome_unknown','batch_id':options['batch_id'],'expected_revision':0},f)
cmd=['docker','run','--rm','--read-only','--network',options['publication_network'],'--user',config['user'],
 '--env','PYTHONDONTWRITEBYTECODE=1','--cap-drop','ALL','--security-opt','no-new-privileges:true',
 '--mount','type=bind,src='+str(configs)+',dst='+mounts[str(configs)]+',readonly',
 '--mount','type=bind,src='+str(state)+',dst='+mounts[str(state)],
 '--mount','type=bind,src='+str(folder)+',dst=/publish,readonly','--entrypoint','python',wanted['image'],
 '-m','investigation_test','publish','--config',mounts[str(configs)]+'/service.json','--document','/publish/document.json','--expected-revision','0']
r=subprocess.run(cmd,capture_output=True,text=True,timeout=options['command_timeout_seconds'])
receipt={'status':'published' if r.returncode==0 else 'publication_failed_check_saved_intent','exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,
 'batch_id':options['batch_id'],'image':wanted['image'],'previous_files_unchanged':all((ledger/n).is_file() and hashlib.sha256((ledger/n).read_bytes()).hexdigest()==h for n,h in before.items()),
 'preserved_files':len(before),'new_business_calls':0,'new_model_calls':0,'automatic_4b_feature':False,'files':{n:v['sha256'] for n,v in x['files'].items()}}
receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps(receipt,ensure_ascii=False))
'''


def main():
    target=json.loads((ROOT/'target.json').read_text())
    options=json.loads((ROOT/'publish-options.json').read_text())
    preparation=json.loads((ROOT/options['preparation']).read_text())
    files={}
    for name,digest in preparation['files'].items():
        raw=(ROOT/options['input_directory']/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==digest
        files[name]={'sha256':digest,'content':base64.b64encode(raw).decode()}
    payload={'target':target,'options':options,'files':files}
    result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12',target['ssh_target'],shlex.join(['python3','-c',REMOTE])],
                          input=json.dumps(payload),capture_output=True,text=True,timeout=options['command_timeout_seconds']+30)
    with (ROOT/'viewer-publication.json').open('x') as out:
        json.dump({'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr},out,ensure_ascii=False,indent=2)
    print(result.stdout)
    if result.returncode:
        print('Publication outcome needs saved remote receipt inspection; do not replay.')


if __name__=='__main__':
    main()
