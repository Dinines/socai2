"""Activate, upload, and verify this batch against the actual r4 release receipts."""

import argparse
import base64
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

E = Path(__file__).resolve().parent
R = E.parents[3]
spec = importlib.util.spec_from_file_location("batch_invoke", E / "invoke.py")
invoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(invoke)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


UPLOAD = r'''
import base64,hashlib,json,os,sys
from pathlib import Path
x=json.load(sys.stdin);folder=Path(x['folder'])
assert not folder.exists()
folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir()
for name,encoded in x['files'].items():
 path=folder/name
 assert path.resolve().is_relative_to(folder.resolve())
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as f:f.write(base64.b64decode(encoded))
m=json.loads((folder/'manifest.json').read_text())
for name,want in m['files'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==want
(folder/'out').mkdir();uid,gid=map(int,x['user'].split(':'));os.chown(folder/'out',uid,gid)
print(json.dumps({'status':'uploaded_and_hash_verified','files':len(x['files']),'prepared_manifest_sha256':hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest(),'business_messages_sent':0}))
'''

PROBE = r'''
import hashlib,json,subprocess,sys,urllib.request
from pathlib import Path
from datetime import datetime,timezone
x=json.load(sys.stdin);folder=Path(x['folder']);phase=x['phase'];p=json.loads((folder/'profile.json').read_text());m=json.loads((folder/'manifest.json').read_text())
out={};root=Path(p['release_root'])
def h(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(argv,payload=None):
 r=subprocess.run(argv,input=payload,capture_output=True,text=True,timeout=p['timeouts']['remote_seconds']-5)
 if r.returncode:
  private=root/'private';private.mkdir(exist_ok=True)
  log=private/(p['batch_id']+'-'+x['label']+'.txt')
  with log.open('x') as f:log.chmod(0o600);f.write(r.stdout+'\n'+r.stderr)
  raise RuntimeError('probe_failed_private_log:'+str(log))
 return json.loads(r.stdout)
if phase=='preflight':
 a=x['activation'];ready=json.loads((root/'deployment-ready.json').read_text());cleanup=json.loads((root/'cleanup-zero.json').read_text())
 assert ready==x['release_receipts']['deployment-ready.json'] and cleanup==x['release_receipts']['cleanup-zero.json']
 assert h(root/'deployment-ready.json')==x['remote_receipt_sha256']['deployment-ready.json']
 assert h(root/'cleanup-zero.json')==x['remote_receipt_sha256']['cleanup-zero.json']
 assert ready['release']==p['release'] and ready['status']=='ready_for_new_full_flow'
 actual={}
 for key,want in ready['services'].items():
  found=run(['docker','inspect',want['name']])[0]
  assert found['Id']==want['id'] and found['Image']==want['image'] and found['State']['Running']
  actual[key]={'id':found['Id'],'image':found['Image'],'running':True,'restart_count':found['RestartCount']}
 for name in p['must_remain_stopped']:
  assert not run(['docker','inspect',name])[0]['State']['Running']
 with urllib.request.urlopen(p['fusion_ready_url'],timeout=p['timeouts']['http_seconds']) as response:fusion=json.load(response)
 assert fusion['status']=='ready' and fusion['subscriptions']==['alerts+raw_events']
 empty={}
 for subject in ('alerts','incidents','cases'):
  with urllib.request.urlopen(p['http_base']+'/api/v1/socai2/'+subject,timeout=p['timeouts']['http_seconds']) as response:empty[subject]=json.load(response)
  assert empty[subject]['total']==0 and empty[subject]['items']==[]
 hashes=run(['docker','exec','-i',p['containers']['analysis'],'python','-c',x['hash_code']],json.dumps(ready['runtime_input_profiles']))
 assert hashes['policy_sha256']==ready['policy_sha256']
 out.update(source='actual_release_preflight',fusion_ready=True,unique_execution_services=True,history_cleanup_verified=True,release_readiness_verified=True,cleanup_receipt_sha256=h(root/'cleanup-zero.json'),release_readiness_sha256=h(root/'deployment-ready.json'),local_receipts=a,services=actual,fusion_readiness=fusion,http_empty_reads=empty,runtime_hashes=hashes)
if phase.endswith('context-readback'):
 prefix=phase.split('-')[0];p['readback_events']=[json.loads((folder/r['wire']).read_text()) for r in m['phases'][prefix+'-context']['records']]
 ackpath=folder/'out'/('send-'+prefix+'-context.json');ack=json.loads(ackpath.read_text())
 assert ack['status']=='accepted_only' and ack['accepted']==len(p['readback_events']) and ack['not_attempted']==0 and not ack['cleanup_errors']
 out['context_receipt_sha256']=h(ackpath)
out.update(run(['docker','exec','-i',p['containers']['analysis'],'python','-c',x['probe_code'],phase],json.dumps(p)))
out.update(observed_at=datetime.now(timezone.utc).isoformat(),prepared_manifest_sha256=h(folder/'manifest.json'))
with (folder/'out'/(phase+'.json')).open('x') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out,ensure_ascii=False))
'''

HASH_CODE = r'''
import hashlib,json,os,sys
from pathlib import Path
want=json.load(sys.stdin);got={}
for name,value in want.items():
 got[name]=hashlib.sha256(Path(name).read_bytes()).hexdigest();assert got[name]==value
policy=Path(os.environ['SOCAI2_INVESTIGATION_POLICY'])
print(json.dumps({'input_profiles':got,'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'policy_path':str(policy)}))
'''

REGISTER = r'''
import json,subprocess,sys
from pathlib import Path
from uuid import UUID
x=json.load(sys.stdin);folder=Path(x['folder']);p=json.loads((folder/'profile.json').read_text());c=json.loads((Path(p['release_root'])/'config/release.json').read_text());r=p['connector'];UUID(r['id']);UUID(p['tenant_id'])
assert json.loads((folder/'out/preflight.json').read_text())['status']=='passed'
assert not r['is_enabled']
with (folder/'out/connector-intent.json').open('x') as f:json.dump({'state':'started_outcome_unknown','connector':r},f)
def q(s):return "'"+s.replace("'","''")+"'"
sql='BEGIN; INSERT INTO public.connectors(id,tenant_id,name,connector_type,category,is_enabled) VALUES('+','.join(q(t) for t in [r['id'],p['tenant_id'],r['name'],r['connector_type'],r['category']])+',false); SELECT row_to_json(t) FROM (SELECT id,tenant_id,name,connector_type,category,is_enabled FROM public.connectors WHERE id='+q(r['id'])+'::uuid) t; COMMIT;'
v=subprocess.run(['docker','exec','-i',c['database']['container'],'psql','-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-U',c['database']['admin'],'-d',c['database']['name']],input=sql,capture_output=True,text=True,timeout=p['timeouts']['http_seconds'])
assert v.returncode==0,'connector_configuration_failed'
row=json.loads(v.stdout);assert row==dict(r,tenant_id=p['tenant_id'])
with (folder/'out/connector.json').open('x') as f:json.dump(row,f,indent=2)
print(json.dumps(row))
'''


def activate(p):
    config = json.loads((E / "preparation-config.json").read_text())
    paths = {
        "cleanup": R / "docs/operations/evidence" / p["release"] / "cleanup-zero.json",
        "release_readiness": R / "docs/operations/evidence" / p["release"] / "deployment-ready.json",
    }
    cleanup, ready = (json.loads(paths[k].read_text()) for k in paths)
    assert ready["status"] == "ready_for_new_full_flow" and ready["release"] == p["release"]
    assert cleanup["preserved_tables_unchanged"] and ready["old_execution_services_stopped"]
    assert all(item["rows_after"] == 0 for item in cleanup["steps"]["postgres"])
    assert all(item["after"] == 0 for item in cleanup["steps"]["lake"])
    assert all(item["remaining_test_keys"] == 0 for item in cleanup["steps"]["redis"])
    assert all(item["all_start_equals_end"] for item in cleanup["steps"]["kafka"])
    assert all(item["remaining_files"] == 0 for item in cleanup["steps"]["ledger"])
    assert ready["database"] == p["database"]["name"]
    assert all(ready["database_state"][key] == 0 for key in ("tasks", "attempts", "runs", "results"))
    assert ready["viewer_empty_batches"]["total"] == 0
    assert digest(R / config["investigation_policy_file"]) == ready["policy_sha256"]
    for name, want in ready["runtime_input_profiles"].items():
        assert digest(R / "services/api" / name) == want
    activation = {
        "batch_id": p["batch_id"], "release": p["release"],
        "status": "actual_cleanup_and_release_verified",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "processing_image_id": ready["images"]["processing"],
        **{key: {"path": str(path.relative_to(R)), "sha256": digest(path)} for key, path in paths.items()},
    }
    with (E / "activation.json").open("x") as stream:
        json.dump(activation, stream, indent=2)
    print(json.dumps(activation))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("activate", "upload", "preflight", "register", "context-readback"))
    parser.add_argument("--label", required=True)
    parser.add_argument("--phase", choices=("S01", "S04"))
    args = parser.parse_args()
    assert args.label.replace("-", "").isalnum()
    p = json.loads((E / "batch/profile.json").read_text())
    if args.action == "activate":
        activate(p)
        return
    activation = invoke.require_ready(p)
    payload = {"folder": p["remote_directory"], "label": args.label}
    if args.action == "upload":
        m = json.loads((E / "batch/manifest.json").read_text())
        names = list(m["files"]) + ["manifest.json"]
        for name, want in m["files"].items():
            assert digest(E / "batch" / name) == want
        payload.update(user=p["user"], files={name: base64.b64encode((E / "batch" / name).read_bytes()).decode() for name in names})
        code = UPLOAD
    elif args.action == "register":
        code = REGISTER
    else:
        phase = "preflight" if args.action == "preflight" else args.phase + "-context-readback"
        payload.update(phase=phase, activation=activation, probe_code=(E / "live-probe.py").read_text(), hash_code=HASH_CODE)
        if args.action == "preflight":
            paths = {name: E / ("remote-" + name) for name in ("cleanup-zero.json", "deployment-ready.json")}
            for name, path in paths.items():
                assert json.loads(path.read_text()) == json.loads((R / "docs/operations/evidence" / p["release"] / name).read_text())
            payload.update(release_receipts={name: json.loads(path.read_text()) for name, path in paths.items()}, remote_receipt_sha256={name: digest(path) for name, path in paths.items()})
        code = PROBE
    out = invoke.remote(p, ["python3", "-c", code], json.dumps(payload), args.label)
    print(json.dumps({k: v for k, v in out.items() if k not in ("lake_rows", "services", "runtime_hashes", "http_empty_reads")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
