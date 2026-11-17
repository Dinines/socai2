"""Publish the two actually saved/read-back first rounds as the S04 precondition."""
import hashlib,json,shlex,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent;p=json.loads((root/'batch/profile.json').read_text())
gate=json.loads((root/'http-readback-first/validation.json').read_text());snap=json.loads((root/'first-pg.json').read_text())
assert gate['status']=='passed' and len(gate['case_ids'])==len(gate['result_ids'])==2
assert sorted((x['members'],x['runs']) for x in gate['cases'])==[(1,1),(3,1)]
assert all(t['state']=='completed' for t in snap['rows']['analysis_tasks'])
assert all(r['state']=='completed' for r in snap['rows']['runs'])
assert gate['snapshot_sha256']==hashlib.sha256((root/'first-pg.json').read_bytes()).hexdigest()
code='''import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);data=json.loads(sys.stdin.read());assert data['prepared_manifest_sha256']==hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest()
with (p/'out/first-round-gate.json').open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2)
print(json.dumps({'status':'passed','case_ids':data['case_ids'],'result_ids':data['result_ids']}))
'''
r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=12',p['ssh_target'],shlex.join(['python3','-c',code,p['remote_directory']])],input=json.dumps(gate),capture_output=True,text=True,timeout=30)
with (root/'first-round-gate-publication.json').open('x') as f:json.dump({'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},f,ensure_ascii=False,indent=2)
assert r.returncode==0;print(r.stdout)
