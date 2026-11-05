"""Read-only m2 packet/hash and bounded gateway timeout metadata; no model calls."""
import json
import shlex
import subprocess

from evaluate_socai2_models_20261104 import ROOT, encode, sha, write
from verify_socai2_store_20261103 import DEST, SSH

OUT = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m2"
CODE = r'''
import hashlib,json,re,subprocess
from datetime import datetime,timedelta
from pathlib import Path
p=Path('/opt/sting-aisoc-socai2/evidence/next-model-comparison-20261104-m2')
body=(p/'plan-and-packets.json').read_bytes(); bundle=json.loads(body)
def digest(v): return hashlib.sha256(json.dumps(v,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()).hexdigest()
at=datetime.fromisoformat(json.loads((p/'C3-current-small-intent.json').read_text())['dispatch_intent_at'])
start=(at-timedelta(seconds=1)).isoformat(); end=(at+timedelta(seconds=48)).isoformat()
r=subprocess.run(['docker','logs','--timestamps','--since',start,'--until',end,'socai2-litellm-1'],capture_output=True,timeout=20,check=False)
events=[]
for line in (r.stdout+r.stderr).decode(errors='replace').splitlines():
    classes=re.findall(r'litellm\.([A-Za-z]*Timeout[A-Za-z]*)',line)
    status=re.search(r'"POST /v1/chat/completions HTTP/1\.[01]" (408|400|504)',line)
    if classes or status:
        events.append({'timestamp':line.split(' ',1)[0][:40], 'error_classes':sorted(set(classes)),
            'http_status':int(status[1]) if status else None,'mentions_selected_alias':'aisoc-investigation' in line})
        if len(events)>=20: break
# Export numeric timeout settings only, never arbitrary config values or logs.
config_code="import json,yaml; d=yaml.safe_load(open('/etc/litellm/config.yaml')); out={};\ndef visit(x,path):\n if isinstance(x,dict):\n  for k,v in x.items():\n   if 'timeout' in str(k).lower() and isinstance(v,(int,float)): out[path+'.'+str(k)]=v\n   visit(v,path+'.'+str(k))\n elif isinstance(x,list):\n  for i,v in enumerate(x): visit(v,path+'.'+str(i))\nvisit(d,'$'); print(json.dumps(out))"
c=subprocess.run(['docker','exec','socai2-litellm-1','python','-c',config_code],capture_output=True,timeout=20,check=False)
settings=json.loads(c.stdout) if c.returncode==0 else None
print(json.dumps({'remote_packet_file_sha256':hashlib.sha256(body).hexdigest(),
 'remote_packet_canonical_sha256':digest(bundle),'remote_runner_sha256':hashlib.sha256((p/'runner.py').read_bytes()).hexdigest(),
 'cell_body_hashes':{x['id']:digest(x['body']) for x in bundle['cells']},
 'gateway_window':{'since':start,'until':end,'exit_code':r.returncode},'gateway_error_metadata':events,
 'timeout_settings':settings,'timeout_settings_read_exit_code':c.returncode,'new_model_calls':0},ensure_ascii=False))
'''


def main():
    result = subprocess.run([*SSH, DEST, "python3 -c " + shlex.quote(CODE)], capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise RuntimeError("read-only m2 verification failed; no retry or inference")
    value = json.loads(result.stdout)
    bundle = json.loads((OUT / "plan-and-packets.json").read_text("utf-8"))
    assert value["remote_packet_canonical_sha256"] == sha(encode(bundle))
    assert value["cell_body_hashes"] == {c["id"]: c["body_sha256"] for c in bundle["cells"]}
    local_runner = (OUT / "runner.py").read_text("utf-8").encode()
    assert value["remote_runner_sha256"] == sha(local_runner)
    value["all_remote_requests_match_frozen_local_bodies"] = True
    value["file_bytes_differ_only_by_local_CRLF_remote_LF"] = value["remote_packet_file_sha256"] == sha(
        (OUT / "plan-and-packets.json").read_text("utf-8").encode())
    write(OUT / "remote-verification.json", value)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
