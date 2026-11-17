"""Publish a new observation of existing executions; never send business requests."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import shutil
from urllib.parse import urlsplit

root=Path(__file__).resolve().parents[5]
p=Path(__file__).resolve().parent
inputs=p/'inputs'
inputs.mkdir()
w4=root/'docs/operations/evidence/streaming-w4-package-20261116-01'
d=json.loads((w4/'inputs/document.json').read_text())
for evidence in d['evidence']:
    shutil.copyfile(w4/'inputs'/evidence['path'], inputs/evidence['path'])
old=json.loads(next((w4/'state/ledger/w2-live-s01-s04-20261115-01').glob('rev-*/ledger.json')).read_text())['document']
first=copy.deepcopy(old['cases'][0]);first.update(id='case_round1',operation_ids=['case_round1'],evidence_ids=['http-exchanges'])
d['cases'].append(first)
op=copy.deepcopy(old['operations'][0]);op.update(id='case_round1',case_id='case_round1',evidence_ids=['http-exchanges']);d['operations'].append(op)
for q in old['quality_issues'][:2]:
    q=copy.deepcopy(q);q['case_id']='case_round1' if q['case_id']=='s01_event_case' else 'control';d['quality_issues'].append(q)
source=root/'docs/operations/evidence/test-streaming-case-initial-20261115-01/quality-findings-01.json'
shutil.copyfile(source, inputs/'case-quality.json')
d['evidence'].append(dict(id='case_quality',path='case-quality.json',label='首轮引用问题原记录',mime_type='application/json',visibility='public',source_ref=str(source.relative_to(root))))
now=datetime.now(timezone.utc).isoformat()
d['batch'].update(id='w5-execution-view-20261116-01',title='案例执行：请求、调查与结果（S01/S04）',started_at=now,updated_at=now)
d['preparation'].update(summary='仅整理已有HTTP受理和执行身份，逐步展示真实流程；未重发请求、未启动模型、未清理数据。',observed_at=now)
exchanges=[]
for label in ['whole_incident','single_alert_a01']:
    source=root/f'docs/operations/evidence/streaming-case-http-20261115-01/post-{label}.json'
    rec=json.loads(source.read_text())['receipts'][0]
    allocation=rec['body']['allocations'][0];task=allocation['initial_task'];mapping=next(m for o in d['operations'] for m in o['mappings'] if m['task_id']==task['task_id'])
    exchanges.append(dict(subject_type=mapping['subject_type'],subject_id=mapping['subject_id'],task_id=task['task_id'],run_id=mapping['run_id'],observed_at=rec['at'],request=dict(method=rec['request']['method'],path=urlsplit(rec['request']['url']).path,body=rec['request']['body']),response=dict(status=rec['status'],body=rec['body']),sources=[dict(path=str(source.relative_to(root)),sha256=hashlib.sha256(source.read_bytes()).hexdigest())]))
source=root/'docs/operations/evidence/streaming-budget-20261116-01/submit-02.json';rec=json.loads(source.read_text())
intent=json.loads((p/'submission-intent-original.json').read_text());mapping=next(m for o in d['operations'] for m in o['mappings'] if m['task_id']==rec['receipt']['task_id'])
exchanges.append(dict(subject_type=mapping['subject_type'],subject_id=mapping['subject_id'],task_id=mapping['task_id'],run_id=mapping['run_id'],observed_at=rec['observed_at'],request=dict(method='POST',path=intent['path'],body=intent['request']),response=dict(status=rec['http_status'],body=rec['receipt']),sources=[dict(path=str(source.relative_to(root)),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),dict(path=str((p/'submission-intent-original.json').relative_to(root)),sha256=hashlib.sha256((p/'submission-intent-original.json').read_bytes()).hexdigest())]))
(inputs/'http-exchanges.json').write_text(json.dumps(dict(schema='socai2.test-http-exchanges.v1',exchanges=exchanges),ensure_ascii=False,indent=2)+'\n')
d['evidence'].append(dict(id='http-exchanges',path='http-exchanges.json',label='真实HTTP请求与受理回执',mime_type='application/json',visibility='public',source_ref=str((inputs/'http-exchanges.json').relative_to(root))))
(inputs/'document.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
shutil.copytree(w4/'state',p/'state')
config=json.loads((p/'service.json').read_text());config['ledger_root']=str(p/'state/ledger');(p/'service.json').write_text(json.dumps(config,indent=2)+'\n')
print(json.dumps({'batch':d['batch']['id'],'operations':len(d['operations']),'http_exchanges':len(exchanges),'original_files_preserved':15}))
