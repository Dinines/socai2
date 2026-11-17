"""Compare scoped business HTTP to one actual completed batch snapshot."""
import hashlib, importlib.util, json, sys
from pathlib import Path
from urllib.parse import urlencode

root=Path(__file__).resolve().parent;phase=sys.argv[1]
spec=importlib.util.spec_from_file_location('existing_readback',root.parent/'streaming-ai-http-20261115-01/read_analysis.py')
io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
io.OUT=root/('http-readback-'+phase);io.SAVED='--verify-saved' in sys.argv
if not io.SAVED:io.OUT.mkdir()
p=json.loads((root/'batch/profile.json').read_text());host=p['http_base'];base=host+'/api/v1/socai2'
raw=(root/(phase+'-pg.json')).read_bytes();rows=json.loads(raw)['rows']
index={k:{x['id']:x for x in values} for k,values in rows.items() if k!='analysis_subject_state'}
calls=0;got={};pages={}
def get(urls,label):
    global calls
    urls=list(dict.fromkeys(urls));result={}
    for n in range(0,len(urls),20):
        result.update(io.get_all(urls[n:n+20],f'{label}-{n//20+1:02d}.json'))
    calls+=len(urls);got.update(result);return result
urls=[];runurls={}
for c in rows['cases']:
    urls += [base+'/cases/'+c['id'],base+'/cases/'+c['id']+'/history']
for t in rows['analysis_tasks']:
    urls.append(f"{base}/{t['subject_type']}s/{t['subject_id']}/analysis-tasks/{t['id']}")
for r in rows['runs']:
    kind='cases' if r['case_id'] else 'incidents' if r['incident_id'] else 'alerts'
    sid=r['case_id'] or r['incident_id'] or r['alert_id']
    url=f'{base}/{kind}/{sid}'+('' if kind=='cases' else '/analysis')+'/runs/'+r['id']
    runurls[r['id']]=url;urls.append(url)
    if phase=='final':urls.extend([base+'/analysis-runs/'+r['id']+'/steps',base+'/analysis-runs/'+r['id']+'/artifacts'])
for r in rows['results']:urls.append(f"{base}/cases/{r['case_id']}/results/{r['id']}")
get(urls,'records')
pages={u:[v] for u,v in got.items() if any(k in v for k in ('next_cursor','next_before_run_id','next_offset'))}
n=0
while True:
    nexts={}
    for url,values in pages.items():
        for key in ('cursor','before_run_id','offset'):
            if values[-1].get('next_'+key) is not None:
                nexts[url+'?'+urlencode({key:values[-1]['next_'+key]})]=url
    if not nexts:break
    assert not set(nexts)&set(got);n+=1
    for url,value in get(list(nexts),f'pages-{n}').items():pages[nexts[url]].append(value)
contents={};comparison=[];comparison_states=[]
for r in rows['runs']:
    rid=r['id'];view=got[runurls[rid]];io.same_fields(view['run'],r)
    table='results' if r['case_id'] else 'incident_diagnoses' if r['incident_id'] else 'alert_assessments'
    result=next((x for x in rows[table] if x['source_run_id']==rid),None)
    if result is not None:
        if r['case_id']:
            returned=got[f"{base}/cases/{r['case_id']}/results/{result['id']}"]['result']
        else:returned=view['result']
        io.same_fields(returned,result);assert returned['source_run_id']==rid
    if r['case_id']:
        comp=view['run'].get('comparison_context')
        frozen=index['artifacts'][r['input_artifact_id']]['content_json'].get('comparison_context')
        assert comp==frozen
        comparison_states.append({'run_id':rid,'context':comp})
        if comp and comp.get('previous_run_id'):
            assert index['runs'][comp['previous_run_id']]['case_id']==r['case_id']
            comparison.append(host+view['previous_run_url'])
            assert comp.get('comparison_result_id')==r['comparison_result_id']
            if comp.get('comparison_result_id'):
                assert index['results'][comp['comparison_result_id']]['source_run_id']==comp['previous_run_id']
                comparison.append(host+view['comparison_result_url'])
            else:
                assert view['comparison_result_url'] is None and comp['state']=='unavailable'
    if phase=='final':
        for section,table in [('steps','run_steps'),('artifacts','artifacts')]:
            url=base+'/analysis-runs/'+rid+'/'+section
            items=[x for page in pages[url] for x in page['items']]
            expected={x['id']:x for x in rows[table] if x['run_id']==rid}
            assert {x['id'] for x in items}==set(expected)
            for item in items:
                io.same_fields(item,expected[item['id']])
                if section=='artifacts' and (r['case_id'] or item['kind'] in {'model_request','model_response','input_snapshot','tool_response'}):
                    contents[item['id']]=host+item['content_url']
get([u for u in [*contents.values(),*comparison] if u not in got],'contents')
for aid,url in contents.items():
    value=got[url];assert value['availability']=='available'
    assert value['content_json']==index['artifacts'][aid]['content_json'] and value['content_text']==index['artifacts'][aid]['content_text']
case_summary=[]
for c in rows['cases']:
    cid=c['id'];url=base+'/cases/'+cid;v=got[url];io.same_fields(v['case'],c)
    members={x['alert_id'] for x in rows['case_alerts'] if x['case_id']==cid}
    assert {x['alert_id'] for x in v['members']}==members and v['member_count']==len(members)
    history=[x for page in pages[url+'/history'] for x in page['items']]
    assert {x['run']['id'] for x in history}=={x['id'] for x in rows['runs'] if x['case_id']==cid}
    case_summary.append({'case_id':cid,'members':len(members),'runs':len(history),'assessment_freshness':v['current_assessment']['input_freshness'] if v['current_assessment'] else None})
for t in rows['analysis_tasks']:
    v=got[f"{base}/{t['subject_type']}s/{t['subject_id']}/analysis-tasks/{t['id']}"]
    assert v['task_id']==t['id'] and v['status']==t['state']
    attempts=[a for a in rows['analysis_attempts'] if a['task_id']==t['id']]
    assert len(v['attempts'])==len(attempts)
    for a in v['attempts']:io.same_fields(a,next(x for x in attempts if x['attempt_no']==a['attempt_no']))
    if t['state']=='skipped':assert v['latest_run_id'] is None and not attempts
summary={'status':'passed','source':'actual_case_readback','batch_id':p['batch_id'],
 'snapshot_sha256':hashlib.sha256(raw).hexdigest(),'prepared_manifest_sha256':hashlib.sha256((root/'batch/manifest.json').read_bytes()).hexdigest(),
 'http_gets':calls,'all_http_200':True,'original_contents_read':len(contents),'comparison_links':comparison,
 'case_ids':[c['id'] for c in rows['cases']],'result_ids':[r['id'] for r in rows['results']],'cases':case_summary,
 'new_model_calls':0,'business_writes':0,'model_quality':'NOT_PASSED'}
if phase=='final':summary['comparison_states']=comparison_states
if not io.SAVED:io.save('validation.json',summary)
else:assert json.loads((io.OUT/'validation.json').read_text())==summary
print(json.dumps(summary,ensure_ascii=False,indent=2))
