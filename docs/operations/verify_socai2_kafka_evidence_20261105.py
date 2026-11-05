"""Read only fixed synthetic lake IDs and its one real Tool query receipt."""
import json
import shlex
import subprocess

from verify_socai2_store_20261103 import DEST, ROOT, SSH

CODE = r'''
import importlib.util,json
from pathlib import Path
p=Path('/opt/sting-aisoc-socai2/evidence/next-kafka-k2-20261105')
s=importlib.util.spec_from_file_location('k2',p/'kafka_chain_remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
ids=[e['event_id'] for c in m.PLAN['cases'] for e in c['events']]
sql='SELECT toString(event_id) AS event_id,count() AS rows FROM socai2_next_validation.raw_events WHERE tenant_id='+m.service.literal(m.service.TENANT)+' AND event_id IN ('+','.join(m.service.literal(i) for i in ids)+') GROUP BY event_id ORDER BY event_id FORMAT JSONEachRow'
rows=[json.loads(x) for x in m.service.lake(sql).splitlines()]
qid='35f99521-b181-49b4-8f7c-f38fc713fdcf'
sql="SELECT type,query_id,read_rows,result_rows,exception_code FROM system.query_log WHERE query_id="+m.service.literal(qid)+" AND type IN ('QueryFinish','ExceptionBeforeStart','ExceptionWhileProcessing') FORMAT JSONEachRow"
queries=[json.loads(x) for x in m.service.lake(sql).splitlines()]
print(json.dumps({'lake_rows':rows,'tool_query':queries,'all_8_exactly_once':len(rows)==8 and all(int(r['rows'])==1 for r in rows),'protected_unchanged':m.service.protected_model_config()==m.read('ingest-intent')['protected_before'],'model_profile':m.service.environment(m.service.NEW).get('SOCAI2_MODEL_SCHEMA_PROFILE','standard'),'read_only':True}))
'''

if __name__ == '__main__':
    out = ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105/k2/lake-readback.json'
    assert not out.exists()
    result = subprocess.run(SSH + [DEST, shlex.join(['python3', '-c', CODE])], capture_output=True, timeout=60, check=False)
    assert result.returncode == 0, 'readback failed; stderr withheld'
    data = json.loads(result.stdout)
    out.write_text(json.dumps(data, indent=2) + '\n', 'utf-8')
    print(json.dumps(data))
