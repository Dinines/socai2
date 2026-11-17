"""Publish only the new actual batch using the already deployed r4 viewer image."""

import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path

E = Path(__file__).resolve().parent
R = E.parents[3]
spec = importlib.util.spec_from_file_location("batch_invoke", E / "invoke.py")
invoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(invoke)

CODE = r'''
import base64,hashlib,json,subprocess,sys
from pathlib import Path
x=json.load(sys.stdin);p=x['profile'];target=x['target'];label=x['label'];root=Path(p['release_root']);cfg=json.loads((root/'config/release.json').read_text());ready=json.loads((root/'deployment-ready.json').read_text());wanted=ready['services']['viewer']
container=json.loads(subprocess.check_output(['docker','inspect',wanted['name']]))[0]
assert container['Id']==wanted['id'] and container['State']['Running'] and container['Image']==wanted['image']
sources={m['Source']:m['Destination'] for m in container['Mounts']}
config_root=root/'viewer/config';state_root=Path(cfg['viewer']['state_root']);config_mount=sources[str(config_root)];state_mount=sources[str(state_root)]
service=json.loads((config_root/'service.json').read_text());assert service['environment_label']==p['release'] and service['ledger_root']==state_mount+'/ledger'
assert not (state_root/'ledger'/target/'current.json').exists()
def preserved():
 result={}
 for bid in x['preserve_batch_ids']:
  directory=state_root/'ledger'/bid;assert (directory/'current.json').is_file()
  result[bid]={str(f.relative_to(directory)):hashlib.sha256(f.read_bytes()).hexdigest() for f in directory.rglob('*') if f.is_file()}
 return result
before=preserved()
folder=Path(p['remote_directory'])/x['input_directory'];folder.mkdir()
for name,item in x['files'].items():
 assert Path(name).name==name
 raw=base64.b64decode(item['base64']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
 with (folder/name).open('xb') as f:f.write(raw)
 (folder/name).chmod(0o644)
document=json.loads((folder/'document.json').read_text());assert document['batch']['id']==target and document['batch']['execution_state']=='finished'
out=Path(p['remote_directory'])/'out'
with (out/(label+'-intent.json')).open('x') as f:json.dump({'batch_id':target,'expected_revision':0,'document_sha256':x['files']['document.json']['sha256'],'state':'started_outcome_unknown'},f)
cmd=['docker','run','--rm','--network',cfg['network'],'--user',cfg['user'],'--env','PYTHONDONTWRITEBYTECODE=1','--mount','type=bind,src='+str(config_root)+',dst='+config_mount+',readonly','--mount','type=bind,src='+str(state_root)+',dst='+state_mount,'--mount','type=bind,src='+str(folder)+',dst=/publish,readonly','--entrypoint','python',wanted['image'],'-m','investigation_test','publish','--config',config_mount+'/service.json','--document','/publish/document.json','--expected-revision','0']
result=subprocess.run(cmd,capture_output=True,text=True,timeout=p['timeouts']['http_seconds'])
if result.returncode:
 log=root/'private'/(target+'-'+label+'.txt')
 with log.open('x') as f:log.chmod(0o600);f.write(result.stdout+'\n'+result.stderr)
 raise RuntimeError('publication_failed_check_remote_intent_and_private_log:'+str(log))
after=preserved();assert before==after
receipt={'status':'published','batch_id':target,'viewer_container':wanted['name'],'image':container['Image'],'publication':json.loads(result.stdout),'files':{n:v['sha256'] for n,v in x['files'].items()},'state_root':str(state_root),'independent_review_sha256':x['review_sha256'],'prior_batches_unchanged':before==after,'preserved_files':before}
with (out/(label+'.json')).open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
print(json.dumps(receipt,ensure_ascii=False))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preparation", default="ledger-preparation.json")
    parser.add_argument("--label", default="viewer-publish-01")
    args = parser.parse_args()
    assert Path(args.preparation).name == args.preparation
    assert args.label.replace("-", "").isalnum()
    p = json.loads((E / "batch/profile.json").read_text())
    invoke.require_ready(p)
    reviews = {}
    for name in ("core-final-bundle-review-02.json", "http-final-bundle-review-01.json"):
        raw = (E / name).read_bytes()
        review = json.loads(raw)
        assert review["status"] in {"passed", "passed_with_unverified_boundaries"} and not review["blocking_findings"]
        reviews[name] = hashlib.sha256(raw).hexdigest()
    preparation = json.loads((E / args.preparation).read_text())
    directory = preparation.get("input_directory", "viewer-input")
    assert Path(directory).name == directory
    files = {}
    for name, info in preparation["files"].items():
        raw = (E / directory / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == info["sha256"]
        files[name] = {"sha256": info["sha256"], "base64": base64.b64encode(raw).decode()}
    payload = {"profile": p, "files": files, "review_sha256": reviews, "target": preparation["batch_id"], "label": args.label, "input_directory": directory, "preserve_batch_ids": preparation.get("preserve_batch_ids", [])}
    result = invoke.remote(p, ["python3", "-c", CODE], json.dumps(payload), args.label)
    print(json.dumps({k: v for k, v in result.items() if k != "files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
