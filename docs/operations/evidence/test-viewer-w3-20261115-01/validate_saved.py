"""Offline direct verification of the unique W3 browser's saved responses."""
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs

ROOT=Path(__file__).resolve().parent
records=[json.loads(s) for s in (ROOT/'requests.jsonl').read_text().splitlines()]
checks=[]
def check(name, condition):
    checks.append({'check':name,'passed':bool(condition)})
    if not condition: raise AssertionError(name)
def body(row): return json.loads((ROOT/row['response_file']).read_bytes())
for row in records:
    check(f"GET only {row['sequence']}",row['method']=='GET')
    if row['response_file']:
        raw=(ROOT/row['response_file']).read_bytes()
        check(f"complete saved bytes {row['sequence']}",len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'])
business=[r for r in records if r['path'].startswith('/api/')]
check('26 business GET only',len(business)==26)
check('business status and environment',all(r['status']==200 and r['headers']['x-investigation-environment']=='streaming-20261115-01' for r in business))
check('same frozen current contract',len({r['headers']['x-investigation-contract'] for r in business})==1)
tasks=[body(r) for r in business if '/analysis-tasks/' in r['path']]
check('seven actual tasks',len(tasks)==7 and len({t['task_id'] for t in tasks})==7)
check('three skipped no invented Run',sum(t['status']=='skipped' and t['attempts']==[] and t['results']==[] and t['latest_run_id'] is None for t in tasks)==3)
check('task execution outcomes preserved',sorted(t['status'] for t in tasks)==['completed']*3+['failed']+['skipped']*3)
runs={body(r)['run']['id']:body(r) for r in business if '/runs/' in r['path'] and not any(s in r['path'] for s in ['/artifacts','/trace'])}
check('four separate Run observations',len(runs)==4)
i=runs['c119d6be-e735-5189-a6d2-8db8490ab84d'];check('failed I current never mistaken for usable',i['run']['state']=='failed' and i['freshness']=='current' and not i['valid_for_current_input'] and i['result']['diagnosis'] is None)
check('I froze four members',i['input_selection']['selected_count']==4 and i['analysis_coverage']['state']=='unknown')
for rid in ['d1b17106-0ee7-4265-ac84-beb9ebf048eb','3327b87f-f4d8-451e-b91d-39618622ead9']:
    d=runs[rid];check('initial partial '+rid,d['run']['state']=='completed' and d['run']['delivery_state']=='partial' and d['run']['comparison_context']['state']=='initial' and d['previous_run_url'] is None and d['comparison_result_url'] is None)
cases=[body(r) for r in business if r['path'].startswith('/api/v1/socai2/cases/') and len(r['path'].split('/'))==6]
check('two current Cases retain adopted but stale judgments',len(cases)==2 and all(c['current_assessment']['value']['validity']=='accepted' and c['current_assessment']['input_freshness']=={'state':'stale','reasons':['incident_context_changed']} for c in cases))
results=[body(r)['result'] for r in business if '/results/' in r['path']]
check('two same Run results remain uncertain partial accepted',len(results)==2 and all(r['conclusion_state']=='uncertain' and r['delivery_state']=='partial' and r['validation_state']=='accepted' and r['source_run_id'] in runs for r in results))
pages=[r for r in business if r['path']=='/api/v1/socai2/analysis-runs/d1b17106-0ee7-4265-ac84-beb9ebf048eb/artifacts']
check('actual three artifact pages',len(pages)==3 and [len(body(r)['items']) for r in pages]==[20,20,8])
check('returned cursor carried to next page',all(parse_qs(pages[n+1]['query'])['cursor'][0]==body(pages[n])['next_cursor'] for n in [0,1]))
check('48 unique artifact identities, terminal cursor',len({v['id'] for r in pages for v in body(r)['items']})==48 and body(pages[-1])['next_cursor'] is None)
contents=[body(r) for r in business if '/artifacts/' in r['path']]
byid={d.get('metadata',d.get('artifact'))['id']:d for d in contents}
check('three lazy originals only',len(byid)==3)
c1=byid['bf3a8ed9-eedf-4bae-8f50-ebbf51eeba53']; scope=c1['content_json']['incidents']['263a1c58-e9c6-4ba4-9204-3b0568970551']['diagnosis_scope']; original=byid[scope['input_artifact_id']]
check('C1 original scope and ownership retained',original['metadata']['run_id']==scope['source_run_id'] and original['metadata']['incident_id']=='263a1c58-e9c6-4ba4-9204-3b0568970551' and original['metadata']['case_id'] is None and original['metadata']['sha256']==scope['source_fingerprint'] and original['content_json']['input_selection']['selected_count']==3)
raw=byid['69087f2c-687e-4fd1-a755-b960c50f6776']['content_json']['raw']
check('original length failure and usage retained',raw['choices'][0]['finish_reason']=='length' and raw['usage']['completion_tokens']==3000 and raw['choices'][0]['message']['content'].endswith('"N1_S110'))
quality=next(body(r) for r in records if r['path'].endswith('/quality-issues'))
check('four deferred quality issues, I flow blocking remains',len(quality['items'])==4 and all(q['status']=='deferred' for q in quality['items']) and sum(q['affects_flow'] for q in quality['items'])==1)
idle=json.loads((ROOT/'terminal-idle-after.json').read_text());check('terminal object no polling over six intervals',idle['unchanged'] and idle['elapsed_seconds']>30)
shutdown=json.loads((ROOT/'shutdown.json').read_text());check('ledger unchanged and both temporary ports closed',shutdown['ledger_unchanged'] and all(shutdown['ports_closed'].values()))
result={'status':'passed','scope':'W3 saved browser responses only; not S04 or model quality acceptance','http_requests':len(records),'business_get':len(business),'test_api_get':sum(r['path'].startswith('/test-api/') for r in records),'asset_or_page_get':sum(not r['path'].startswith(('/api/','/test-api/')) for r in records),'non_200':[{'sequence':r['sequence'],'path':r['path'],'status':r['status']} for r in records if r['status']!=200],'checks':checks,'new_model_calls':0,'business_writes':0,'database_queries':0,'kafka_messages':0,'whole_change_accepted':False}
(ROOT/'readback-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['checks','non_200']},ensure_ascii=False));print(f'{len(checks)} checks passed')
