"""Execute the single frozen operation and keep transport and business receipts."""
import json,shlex,subprocess,sys
from pathlib import Path
E=Path(__file__).resolve().parent;out=E/'revision-02/smoke/out';phase=sys.argv[1]
assert phase in {'read-ai','create-case'}
dest=out/('http-'+phase+'-invocation.json');assert not dest.exists()
code=(E/'minimal-case-http.py').read_text();root='/opt/sting-aisoc-socai2/deployments/streaming-release-20261116-02'
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12','sting-infra21',shlex.join(['python3','-c',code,root,phase])],input=(out/'case-request.json').read_text(),capture_output=True,text=True,timeout=55)
with dest.open('x') as f:json.dump({'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},f,ensure_ascii=False,indent=2)
if r.stdout:
 value=json.loads(r.stdout)
 with (out/('ai-http.json' if phase=='read-ai' else 'case-post.json')).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
 print(json.dumps({'exit':r.returncode,'response_status':value.get('response',{}).get('status'),'receipt':str(dest)},indent=2))
assert r.returncode==0,r.stderr
