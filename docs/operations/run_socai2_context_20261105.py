"""Run once per phase using fixed synthetic materials; no model invocation."""
import hashlib
import json
import shlex
import subprocess
import sys

from verify_socai2_store_20261103 import DEST, ROOT, SSH

OUT = ROOT / '.local/testdata/k4-context-20261105'
QUERY = r'''
import asyncio,json,sys
from uuid import UUID,NAMESPACE_URL,uuid5
from app.socai2 import baseline_semantics
packet=json.load(sys.stdin)
# Candidate projection only in this diagnostic interpreter; service untouched.
exec(compile(packet['semantics'],'candidate_baseline_semantics.py','exec'),baseline_semantics.__dict__)
from app.socai2.baseline_context import Context
from app.socai2.baseline_evidence_tools import LakeGateway,catalog,validate_rows,row_projection
async def main():
 out=[]
 for item in packet['contexts']:
  c=Context.model_validate(item['context']);tenant=UUID(c.case['tenant_id'])
  for bid,b in catalog(c,tenant)['bindings'].items():
   if b['tool_name'] not in ('process_activity','network_connections','authentication_activity'):continue
   qid=str(uuid5(NAMESPACE_URL,'socai2-k4-context-20261105:'+item['key']+':'+b['tool_name']))
   args={'tool_name':b['tool_name'],'contract_version':b['contract_version'],'scope':b['scope'],'limit':50,
    'parameters':{'tenant_id':str(tenant),'hostname':b['hostname'],'source_database':b['source_database'],
     'alert_ids':b['alert_ids'],'binding_id':bid,'query_id':qid}}
   rows=await LakeGateway().query(args,qid,20)
   validate_rows(rows,args)
   out.append({'case_key':item['key'],'tool_name':b['tool_name'],'query_id':qid,'args':args,
    'rows':rows,'projection':[row_projection(row) for row in rows],'row_count':len(rows)})
 print(json.dumps(out))
asyncio.run(main())
'''


def main(phase):
    target = OUT / (phase + '-attempt.json')
    assert phase in {'seed', 'query'} and not target.exists(), 'fixed phase already attempted; inspect, do not retry'
    manifest = json.loads((OUT / 'manifest.json').read_text('utf-8'))
    assert hashlib.sha256((OUT / 'events.json').read_bytes()).hexdigest() == manifest['files']['events.json']
    sources = {name: (ROOT / path).read_text('utf-8') for name, path in {
        'writer': 'services/fusion/app/services/lake_writer.py', 'consumer': 'deploy/aisoc21/kafka_chain_child.py',
        'semantics': 'services/api/app/socai2/baseline_semantics.py'}.items()}
    sources['query'] = QUERY
    code = (ROOT / 'deploy/aisoc21/kafka_context_remote.py').read_text('utf-8')
    packet = {'phase': phase, 'manifest': manifest, 'sources': sources}
    if phase == 'seed':
        packet['events'] = json.loads((OUT / 'events.json').read_text('utf-8'))
    target.write_text(json.dumps({'state': 'started_outcome_unknown', 'phase': phase}), 'utf-8')
    (OUT / (phase + '-source.json')).write_text(json.dumps({'remote': code, 'sources': sources}), 'utf-8')
    result = subprocess.run(SSH + [DEST, shlex.join(['python3', '-c', code])], input=json.dumps(packet).encode(),
        capture_output=True, timeout=210, check=False)
    if result.returncode:
        (OUT / (phase + '-error.json')).write_text(json.dumps({'exit_code': result.returncode,
            'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()}), 'utf-8')
        raise RuntimeError('phase failed; inspect remote receipts before any follow-up')
    data = json.loads(result.stdout)
    for name, value in data.items():
        with (OUT / (name + '.json')).open('x', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, indent=2)
    print(json.dumps({'phase': phase, 'artifacts': list(data), 'summary': data.get('readback') if phase == 'seed' else
        [{k: r[k] for k in ('case_key', 'tool_name', 'row_count')} for r in data['tools']]}))


if __name__ == '__main__':
    main(sys.argv[1])
