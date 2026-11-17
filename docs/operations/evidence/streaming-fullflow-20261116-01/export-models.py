"""Export complete actual requests and visible original replies without re-generation."""
import json,re,sys
from pathlib import Path
root=Path(__file__).resolve().parent;phase=sys.argv[1]
rows=json.loads((root/(phase+'-pg.json')).read_text())['rows'];dest=root/('models-'+phase);dest.mkdir(exist_ok=True)
assert not any(dest.iterdir()),'completed model export already exists'
steps={s['id']:s for s in rows['run_steps']};runs={r['id']:r for r in rows['runs']}
requests={};responses={};issues=[]
for a in rows['artifacts']:
    c=a.get('content_json') or {};v=c.get('payload',c)
    if a['kind']=='model_request':requests[a['step_id']]=a
    if isinstance(v,dict) and isinstance(v.get('raw'),dict) and v['raw'].get('choices'):
        # Case raw source_snapshot and protocol response can contain the same response.
        key=v['raw']['id']
        if key not in responses or a['kind']=='source_snapshot':responses[key]=(a,v)
    for key in ('citation_review','validation_review'):
        for issue in (c.get(key) or {}).get('issues',[]):issues.append({'run_id':a['run_id'],'artifact_id':a['id'],'review':key,**issue})
summary=[]
for a,v in sorted(responses.values(),key=lambda pair:pair[0]['captured_at']):
    step=steps[a['step_id']];run=runs[a['run_id']];req=requests[a['step_id']];rc=req['content_json'];body=rc.get('body') or rc.get('payload',{}).get('body')
    assert isinstance(body,dict) and isinstance(body['messages'],list)
    key=f"{run['id']}-{step['seq']:02d}-{step['stage_code'].replace('.','-')}"
    folder=dest/key;folder.mkdir();raw=v['raw'];original=raw['choices'][0]['message']['content']
    for name,value in [('request.json',body),('response.json',raw)]:
        (folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    (folder/'input.txt').write_text('\n\n'.join('['+m['role']+']\n'+m['content'] for m in body['messages']))
    (folder/'output.txt').write_text(original)
    user='\n'.join(m['content'] for m in body['messages'] if m['role']!='system')
    findings={token:user.count(token) for token in ('telemetry-channel-01','tenant_uid',root.name,'synthetic','is_test','expected_verdict') if token in user}
    summary.append({'run_id':run['id'],'case_id':run['case_id'],'stage':step['stage_code'],'step_id':step['id'],'step_state':step['state'],'error':step['error'],
        'request_artifact_id':req['id'],'response_artifact_id':a['id'],'max_tokens':body['max_tokens'],'usage':raw['usage'],'finish_reason':raw['choices'][0]['finish_reason'],
        'output_chars':len(original),'trailing_whitespace':len(original)-len(original.rstrip()),'input_observations':findings,
        'files':{n:str(folder.relative_to(root)/n) for n in ('input.txt','output.txt','request.json','response.json')}})
(root/('model-summary-'+phase+'.json')).write_text(json.dumps({'models':summary,'review_records':issues,'cost_state':'unknown','quality':'NOT_PASSED'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'calls':len(summary),'stops':[x['finish_reason'] for x in summary],'input_observations':[{'stage':x['stage'],**x['input_observations']} for x in summary],'review_record_count':len(issues)},ensure_ascii=False))
