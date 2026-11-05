"""Read-only actual Tool queries from the fixed first maintenance Case context."""
import json
import shlex
import subprocess

from verify_socai2_store_20261103 import DEST, ROOT, SSH

CHILD = r'''
import asyncio,json,sys
from uuid import UUID,NAMESPACE_URL,uuid5
from app.socai2.baseline_context import Context
from app.socai2.baseline_evidence_tools import LakeGateway,catalog,validate_rows
c=Context.model_validate(json.load(sys.stdin));tenant=UUID(c.case['tenant_id'])
async def main():
 out=[]
 for bid,b in catalog(c,tenant)['bindings'].items():
  if b['tool_name'] not in ('process_activity','network_connections','authentication_activity'):continue
  qid=str(uuid5(NAMESPACE_URL,'socai2-k3-readback-20261105:'+b['tool_name']))
  args={'tool_name':b['tool_name'],'contract_version':b['contract_version'],'scope':b['scope'],'limit':50,
    'parameters':{'tenant_id':str(tenant),'hostname':b['hostname'],'source_database':b['source_database'],
     'alert_ids':b['alert_ids'],'binding_id':bid,'query_id':qid}}
  rows=await LakeGateway().query(args,qid,20)
  out.append({'tool_name':b['tool_name'],'query_id':qid,'args':args,'rows':rows,'row_count':len(rows),
   'scope':'standalone actual Tool diagnostic, no new Run or model adoption'})
 print(json.dumps(out))
asyncio.run(main())
'''
CODE = r'''
import importlib.util,json,sys
from pathlib import Path
from uuid import UUID,uuid5
p=Path('/opt/sting-aisoc-socai2/evidence/next-kafka-k2-20261105/kafka_chain_remote.py')
s=importlib.util.spec_from_file_location('k2',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
cid=str(uuid5(UUID(m.service.TENANT),'socai2.case.create:'+m.uid('deepseek-maintenance-case')))
sql="SELECT content_json FROM socai2.artifacts WHERE tenant_id="+m.service.literal(m.service.TENANT)+" AND schema_version='socai2.baseline-context.v1' AND run_id=(SELECT id FROM socai2.runs WHERE tenant_id="+m.service.literal(m.service.TENANT)+" AND case_id="+m.service.literal(cid)+" ORDER BY requested_at LIMIT 1)"
context=json.loads(m.service.pg(m.service.DATABASE,sql));code=json.load(sys.stdin)['child']
rows=json.loads(m.service.command(['docker','exec','-i',m.service.NEW,'python','-c',code],body=json.dumps(context).encode(),timeout=90))
root=Path('/opt/sting-aisoc-socai2/evidence/next-kafka-k3-lake-20261105')
with (root/'tools.json').open('x') as f:json.dump(rows,f,indent=2)
(root/'tools.json').chmod(0o600)
print(json.dumps(rows))
'''

if __name__ == '__main__':
    target = ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105/k3-lake/tools.json'
    assert not target.exists()
    result = subprocess.run(SSH + [DEST, shlex.join(['python3', '-c', CODE])], input=json.dumps({'child':CHILD}).encode(), capture_output=True, timeout=100, check=False)
    assert result.returncode == 0, 'diagnostic failed; stderr withheld'
    data = json.loads(result.stdout)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n','utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k in {'tool_name','query_id','row_count'}} for r in data]))
