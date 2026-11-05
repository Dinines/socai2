"""Inspect/remove only the 16 exact synthetic rows misrouted by the fixed SQL."""
import argparse
import json
import shlex
import subprocess

from verify_socai2_store_20261103 import DEST, ROOT, SSH

CODE = r'''
import importlib.util,json,sys,hashlib
from pathlib import Path
from uuid import UUID
root=Path('/opt/sting-aisoc-socai2/evidence/next-kafka-lake-correction-20261105')
p=Path('/opt/sting-aisoc-socai2/evidence/next-kafka-k2-20261105/kafka_chain_remote.py')
s=importlib.util.spec_from_file_location('k2',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
expected={}
for batch in ('k1','k2'):
 plan=json.loads(Path('/opt/sting-aisoc-socai2/evidence/next-kafka-'+batch+'-20261105/plan.json').read_text())
 assert plan['tenant_id']==m.service.TENANT
 for c in plan['cases']:
  for e in c['events']:
   expected[str(UUID(e['event_id']))]=e['ocsf_event']
assert len(expected)==16
where='tenant_id='+m.service.literal(m.service.TENANT)+' AND event_id IN ('+','.join(m.service.literal(i) for i in sorted(expected))+')'
sql='SELECT toString(event_id) AS event_id,toString(tenant_id) AS tenant_id,ocsf_json,raw_payload FROM aisoc.raw_events WHERE '+where+' ORDER BY event_id FORMAT JSONEachRow'
def read():
 return [json.loads(x) for x in m.service.lake(sql).splitlines()]
def verify(rows):
 assert len(rows)==16 and {r['event_id'] for r in rows}==set(expected)
 for r in rows:
  value=json.loads(r['ocsf_json']);value.pop('_socai2_storage',None)
  assert value==expected[r['event_id']] and r['tenant_id']==m.service.TENANT
def save(name,value):
 path=root/(name+'.json')
 with path.open('x') as f: json.dump(value,f,ensure_ascii=False,indent=2)
 path.chmod(0o600)
phase=sys.argv[1]
if phase=='inspect':
 rows=read();verify(rows);root.mkdir(mode=0o700,exist_ok=False)
 save('before',{'rows':rows,'target':'aisoc.raw_events','verified_exact_synthetic_payloads':True})
 print(json.dumps({'rows':16,'verified_exact_synthetic_payloads':True,'modified':False,'export':{'before.json':{'rows':rows,'target':'aisoc.raw_events','verified_exact_synthetic_payloads':True}}}))
elif phase=='cleanup':
 rows=read();verify(rows)
 assert rows==json.loads((root/'before.json').read_text())['rows']
 save('cleanup-intent',{'event_ids':sorted(expected),'tenant_id':m.service.TENANT,'only_new_test_rows':True})
 m.service.lake('ALTER TABLE aisoc.raw_events DELETE WHERE '+where+' SETTINGS mutations_sync=2')
 remaining=read();assert remaining==[]
 save('cleanup-result',{'removed_exact_synthetic_rows':16,'remaining':0,'target':'aisoc.raw_events','other_rows_targeted':False})
 print(json.dumps({'removed_exact_synthetic_rows':16,'remaining':0,'other_rows_targeted':False}))
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['inspect', 'cleanup'])
    args = parser.parse_args()
    target = ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105/lake-correction'
    target.mkdir(exist_ok=True)
    path = target / (args.phase + '-receipt.json')
    assert not path.exists()
    result = subprocess.run(SSH + [DEST, shlex.join(['python3', '-c', CODE, args.phase])], capture_output=True, timeout=90, check=False)
    assert result.returncode == 0, 'correction phase failed; inspect exact state before any further action'
    data = json.loads(result.stdout)
    for name, value in data.pop('export', {}).items():
        assert name == 'before.json'
        (target / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    path.write_text(json.dumps(data, indent=2) + '\n', 'utf-8')
    print(json.dumps(data))
