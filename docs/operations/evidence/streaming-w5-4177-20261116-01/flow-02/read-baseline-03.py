"""Refresh only the actual baseline after the separately authorized data reset."""
import hashlib,json,shlex,subprocess
from pathlib import Path
p=Path(__file__).resolve().parent;root=p.parents[4]
profile=json.loads((root/'deploy/investigation-test/release-4177.json').read_text())
old=json.loads((p.parent/'preflight.json').read_text())
remote='''import hashlib,json,subprocess,sys
from pathlib import Path
v=json.load(sys.stdin);c=v['profile']
names=[r['name'].lstrip('/') for r in v['baseline']['containers']]
rows=json.loads(subprocess.check_output(['docker','inspect',*names],text=True))
def hashes(folder):
 return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
r={'containers':[{'name':r['Name'],'id':r['Id'],'image':r['Image'],'state':r['State']['Status'],'restart':r['HostConfig']['RestartPolicy'],'ports':r['HostConfig']['PortBindings']} for r in rows], 'old_site_files':hashes(Path(c['old_site'])),'w4_ledger_files':hashes(Path(c['state_source'])/'ledger'),'current_ledger_hashes':hashes(Path(c['state_root'])/'ledger')}
assert set(r['current_ledger_hashes']).issubset({'.publish.lock'})
for a,b in zip(r['containers'],v['baseline']['containers']):
 if 'streaming-fusion' in a['name']:
  assert a['state']=='exited';a2=dict(a);a2['state']='running';assert a2==b
 else:assert a==b
assert r['old_site_files']==v['baseline']['old_site_files']
assert r['w4_ledger_files']==v['baseline']['w4_ledger_files']
print(json.dumps(r,indent=2))'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',profile['ssh_target'],'python3 -c '+shlex.quote(remote)],input=json.dumps({'profile':profile,'baseline':old}),capture_output=True,text=True,timeout=45)
(p/'baseline-03.stderr.txt').write_text(r.stderr)
assert r.returncode==0,r.stderr
with (p/'baseline-03.json').open('x') as f:f.write(r.stdout)
v=json.loads(r.stdout);print(json.dumps({'containers':len(v['containers']),'active_ledger_records':0,'old_source_files_preserved':len(v['w4_ledger_files']),'fusion':'exited','http':'running'}))
