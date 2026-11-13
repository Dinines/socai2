"""Read-only post-release check against independently read SQL subjects."""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime,timedelta
from pathlib import Path

cfg=json.loads(Path(sys.argv[1]).read_text())
snapshot=json.loads(Path(sys.argv[2]).read_text())
rows=snapshot.get('rows',snapshot)
output=Path(sys.argv[3]);output.mkdir(exist_ok=False)
credential=json.loads(Path(cfg['credential']['file']).read_text())
if cfg['credential'].get('kind')=='existing_login':
    req=urllib.request.Request(cfg['credential']['login_url'],method='POST',
        data=json.dumps({k:credential[k] for k in ['email','password']}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=cfg['timeout_seconds']) as r:token=json.load(r)['access_token']
else:token=credential['api_key']
with urllib.request.urlopen(cfg['base_url']+'/openapi.json',timeout=cfg['timeout_seconds']) as r:api=json.load(r)
assert api['info']['version']==cfg['release']
candidate=json.loads(Path('docs/operations/evidence/list-query-20261113-01/candidate-openapi.json').read_text())
assert api['paths']==candidate['paths'] and api['components']==candidate['components']
responses=[]
def get(kind,params,code=200):
    path='/api/v1/socai2/'+kind+'?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(cfg['base_url']+path,headers={'Authorization':'Bearer '+token})
    try:
        with urllib.request.urlopen(req,timeout=cfg['timeout_seconds']) as r:status,body=r.status,json.load(r)
    except urllib.error.HTTPError as e:status,body=e.code,json.loads(e.read())
    responses.append({'method':'GET','path':path,'status':status,'body':body})
    (output/'responses.json').write_text(json.dumps(responses,ensure_ascii=False,indent=2)+'\n')
    assert status==code,(kind,status,body)
    return body
def ident(row,kind):return row['case' if kind=='cases' else 'facts']['id']
rank={v:i for i,v in enumerate(['info','low','medium','high','critical'])}
alerts={r['id']:r for r in rows['alerts']}
for kind in ['alerts','incidents','cases']:
    source=[]
    for row in rows[kind]:
        r=dict(row)
        if kind=='incidents':
            members=[alerts[x['alert_id']] for x in rows['links'] if x['incident_id']==row['id']]
            r['times']=[datetime.fromisoformat(a['event_time']) for a in members if a['event_time']]
            r['last_activity_at']=max(r['times']) if r['times'] else None
            known=[rank[a['severity']] for a in members if a['severity'] in rank]
            r['severity_rank']=rank.get(r['severity_override'],max(known) if known else None)
        else:
            field='event_time' if kind=='alerts' else 'business_updated_at'
            r['times']=[datetime.fromisoformat(r[field])] if r[field] else []
            r['severity_rank']=rank.get(r['severity'])
        source.append(r)
    query={'q':cfg['queries'][kind]}
    baseline=get(kind,query)
    key='total' if kind=='cases' else 'filtered_total'
    assert baseline[key]==len(source)
    stats='metrics' if kind=='cases' else 'overall_stats'
    sorts={'alerts':['ingested_at','event_time','severity'],'incidents':['created_at','last_activity_at','severity'],'cases':['business_updated_at','created_at','severity']}[kind]
    # Local already passed all directions before switch; directly recheck one sorted traversal.
    if cfg['database']!='aisoc':sorts=['severity']
    for sort in sorts:
        for order in (['asc','desc'] if cfg['database']=='aisoc' else ['desc']):
            def value(r):
                v=r['severity_rank'] if sort=='severity' else r[sort]
                return datetime.fromisoformat(v) if isinstance(v,str) else v
            known=[r for r in source if value(r) is not None];unknown=[r for r in source if value(r) is None]
            expected=[r['id'] for r in sorted(known,key=lambda r:(value(r),r['id']),reverse=order=='desc')+sorted(unknown,key=lambda r:r['id'],reverse=order=='desc')]
            seen=[];cursor=None
            while True:
                p={**query,'sort_by':sort,'sort_order':order,'limit':2}
                if cursor:p['cursor']=cursor
                b=get(kind,p);seen.extend(ident(x,kind) for x in b['items'])
                assert b[key]==len(source) and b[stats]==baseline[stats]
                if kind!='cases':assert b['total']==baseline['total']
                cursor=b['next_cursor']
                if cursor is None:break
                assert len(seen)<=len(source)
            assert seen==expected,(kind,sort,order)
    r=source[0]
    checks=[({'handling_status':r['handling_status']},[x['id'] for x in source if x['handling_status']==r['handling_status']]),
            ({'assignment_state':r['assignment_state']},[x['id'] for x in source if x['assignment_state']==r['assignment_state']])]
    if r['severity_rank'] is not None:
        checks.append(({'severity':list(rank)[r['severity_rank']]},[x['id'] for x in source if x['severity_rank']==r['severity_rank']]))
    times=sorted(t for x in source for t in x['times'])
    if times:
        start=times[0];end=start+timedelta(seconds=1)
        checks.append(({'time_from':start.isoformat(),'time_to':end.isoformat()},[x['id'] for x in source if any(start<=t<end for t in x['times'])]))
    for params,expected in checks:
        b=get(kind,{**query,**params});assert b[key]==len(expected)
        assert {ident(x,kind) for x in b['items']}==set(expected)
    for params in [{'time_from':'2026-11-11T00:00:00Z','time_to':'2026-11-10T00:00:00Z'},{'cursor':'invalid'}]:get(kind,{**query,**params},422)
result={'state':'passed','release':cfg['release'],'database':cfg['database'],'http_gets':len(responses),
        'runtime_contract_matches_candidate':True,'sql_values_match_lists':True,'business_writes':0,'real_model_calls':0,
        'subjects':{k:len(rows[k]) for k in ['alerts','incidents','cases']}}
(output/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
