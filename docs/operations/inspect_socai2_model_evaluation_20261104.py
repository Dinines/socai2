"""Read-only verification and tightly timed C3 gateway error diagnosis. No retry."""
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

from verify_socai2_store_20261103 import DEST, SSH

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m1"

REMOTE_CODE = r'''
import hashlib,json,re,subprocess
from datetime import datetime,timedelta
from pathlib import Path
p=Path('/opt/sting-aisoc-socai2/evidence/next-model-comparison-20261104-m1')
body=(p/'plan-and-packets.json').read_bytes(); bundle=json.loads(body)
def digest(v): return hashlib.sha256(json.dumps(v,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()).hexdigest()
at=datetime.fromisoformat(json.loads((p/'C3-current-small-intent.json').read_text())['dispatch_intent_at'])
start=(at-timedelta(seconds=1)).isoformat(); end=(at+timedelta(seconds=2)).isoformat()
cmd=['docker','logs','--timestamps','--since',start,'--until',end,'socai2-litellm-1']
r=subprocess.run(cmd,capture_output=True,timeout=20,check=False)
log=(r.stdout+r.stderr).decode(errors='replace')
selected=[]
for line in log.splitlines():
    if re.search(r'BadRequestError|uniqueItems|xgrammar|Unsupported|unsupported|Invalid schema|invalid schema|constraint|400 Bad Request',line):
        line=re.sub(r'\x1b\[[0-9;]*m','',line)
        selected.append(line[:1600])
        if len(selected)>=12: break
for path in (Path('/opt/sting-aisoc-socai2/private/next-20261104/api.env'),Path('/opt/sting-aisoc-socai2/private/next-20261104/model.deepseek.env')):
    for line in path.read_text().splitlines():
        if '=' not in line: continue
        key,value=line.split('=',1)
        if value and any(t in key for t in ('KEY','TOKEN','PASSWORD','SECRET')):
            selected=[s.replace(value,'[REDACTED]') for s in selected]
result={'remote_packet_file_sha256':hashlib.sha256(body).hexdigest(),'remote_packet_canonical_sha256':digest(bundle),
 'cell_body_hashes':{c['id']:digest(c['body']) for c in bundle['cells']},
 'gateway_log_window':{'since':start,'until':end,'container':'socai2-litellm-1','returncode':r.returncode},
 'filtered_gateway_error_lines':selected,'new_model_calls':0}
print(json.dumps(result,ensure_ascii=False))
'''


def main():
    result = subprocess.run([*SSH, DEST, "python3 -c " + shlex.quote(REMOTE_CODE)], capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise RuntimeError("read-only evidence verification failed")
    value = json.loads(result.stdout)
    bundle = json.loads((OUT / "plan-and-packets.json").read_text("utf-8"))
    canonical = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    assert value["remote_packet_canonical_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert value["cell_body_hashes"] == {c["id"]: c["body_sha256"] for c in bundle["cells"]}
    value["all_remote_requests_match_frozen_local_bodies"] = True
    value["file_hash_difference_reason"] = "local CRLF versus remote LF; canonical JSON and all request body hashes identical"
    with (OUT / "remote-verification.json").open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
