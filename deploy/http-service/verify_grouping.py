"""One local synthetic grouping batch; acceptance and production reads never write."""
import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str)+'\n')


async def database(cfg, action, fixture):
    if cfg.get('environment'):
        os.environ.update(json.loads((ROOT/cfg['environment']).read_text()))
    sys.path.insert(0,str(ROOT/'services/api'))
    from sqlalchemy import insert,select,text,or_
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
    from app.db.database import _normalize_async_pg_url
    from app.models import socai2 as m
    from app.socai2.baseline_service import BaselineService
    url=os.environ['SOCAI2_CASE_DATABASE_URL'];assert make_url(url).database==cfg['database']
    url,options=_normalize_async_pg_url(url);engine=create_async_engine(url,connect_args=options)
    service=BaselineService(async_sessionmaker(engine,expire_on_commit=False));tenant=UUID(cfg['tenant_id'])
    A,I,L=(x.__table__ for x in (m.Alerts,m.Incidents,m.IncidentAlerts))
    try:
        if action=='seed':
            assert cfg['local_seed_allowed'] and cfg['database']=='v12_upgrade_dev' and not fixture.exists()
            prefix='synthetic-grouping-'+str(uuid4());data={'sources':[prefix,prefix+'-secondary'],'start':cfg['fixture_time'],
                'alert_ids':[str(uuid4()) for _ in range(8)],'incident_ids':[str(uuid4()) for _ in range(4)]}
            save(fixture.with_suffix('.intent.json'),data);start=datetime.fromisoformat(data['start'])
            async with service.transaction(tenant) as store:
                for i,identity in enumerate(data['alert_ids']):
                    when=start+timedelta(minutes=[0,30,60,90,120,0,15,-60][i]) if i!=5 else None
                    await store.db.execute(insert(A).values(id=UUID(identity),tenant_id=tenant,
                        source_namespace=data['sources'][i>=6],source_identity_key=identity,
                        title=f'SYNTHETIC grouping {prefix} alert {i}',severity='high',
                        event_time=when,event_time_source='source' if when else 'unknown'))
                for i,identity in enumerate(data['incident_ids']):
                    await store.db.execute(insert(I).values(id=UUID(identity),tenant_id=tenant,
                        source_namespace=data['sources'][0],source_incident_id=identity,
                        title=f'SYNTHETIC grouping {prefix} incident {i}',
                        handling_status=['in_progress','resolved','new','in_progress'][i]))
                for group,members in enumerate(((0,1,6),(2,3),(7,),())):
                    for member in members:
                        await store.db.execute(insert(L).values(id=uuid4(),tenant_id=tenant,
                            alert_id=UUID(data['alert_ids'][member]),incident_id=UUID(data['incident_ids'][group]),
                            membership_source='manual',source_operation_id=uuid4(),correlation_basis={'synthetic':True},basis_version='synthetic.grouping.v1'))
            save(fixture,data)
        else:data=json.loads(fixture.read_text())
        async with service.transaction(tenant,readonly=True) as store:
            identity=dict((await store.db.execute(text('SELECT current_database() AS database,current_user AS role'))).mappings().one())
            assert identity['database']==cfg['database']
            alerts=[dict(r) for r in (await store.db.execute(select(A).where(A.c.tenant_id==tenant,A.c.source_namespace.in_(data['sources'])).order_by(A.c.id))).mappings()]
            incident_ids=select(L.c.incident_id).where(L.c.tenant_id==tenant,L.c.alert_id.in_([r['id'] for r in alerts]))
            incidents=[dict(r) for r in (await store.db.execute(select(I).where(I.c.tenant_id==tenant,
                or_(I.c.source_namespace.in_(data['sources']),I.c.id.in_(incident_ids))).order_by(I.c.id))).mappings()]
            links=[dict(r) for r in (await store.db.execute(select(L).where(L.c.tenant_id==tenant,
                L.c.incident_id.in_([r['id'] for r in incidents])).order_by(L.c.id))).mappings()]
        return json.loads(json.dumps({'identity':identity,'alerts':alerts,'incidents':incidents,'links':links},default=str))
    finally:await engine.dispose()


def verify(cfg,fixture,snapshot,out):
    secret=json.loads((ROOT/cfg['credential']['file']).read_text())
    if cfg['credential'].get('kind')=='existing_login':
        request=urllib.request.Request(cfg['credential']['login_url'],data=json.dumps({k:secret[k] for k in ('email','password')}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=cfg['timeout_seconds']) as r:token=json.load(r)['access_token']
    else:token=secret['api_key']
    data=json.loads(fixture.read_text());calls=[]
    with urllib.request.urlopen(cfg['base_url']+'/openapi.json',timeout=cfg['timeout_seconds']) as r:contract=json.load(r)
    if cfg.get('release'):assert contract['info']['version']==cfg['release']
    assert '/api/v1/socai2/incidents/grouping-summary' in contract['paths']
    def expected(params):
        alerts=[r for r in snapshot['alerts'] if r['source_namespace']==params['source_namespace']]
        for name,cmp in [('time_from',lambda a,b:a>=b),('time_to',lambda a,b:a<b)]:
            if name in params:alerts=[r for r in alerts if r['event_time'] and cmp(datetime.fromisoformat(r['event_time']),datetime.fromisoformat(params[name]))]
        aids={r['id'] for r in alerts};links=[r for r in snapshot['links'] if r['alert_id'] in aids]
        grouped={r['alert_id'] for r in links};incidents={r['incident_id'] for r in links}
        return {'alert_count':len(aids),'grouped_alert_count':len(grouped),'ungrouped_alert_count':len(aids-grouped),'incident_count':len(incidents),
            'in_progress_incident_count':sum(r['id'] in incidents and r['handling_status']=='in_progress' for r in snapshot['incidents']),
            'compression_rate':(len(grouped)-len(incidents))/len(grouped) if grouped else None}
    start=datetime.fromisoformat(data['start']);source=data['sources'][0]
    cases=[({'source_namespace':s},200) for s in data['sources']]
    cases += [({'source_namespace':source,**{k:(start+timedelta(minutes=v)).isoformat() for k,v in params.items()}},200) for params in (
        {'time_from':0,'time_to':120},{'time_from':120,'time_to':180},{'time_from':0},{'time_to':0})]
    cases += [({'source_namespace':source+' absent'},200)]
    cases += [({'source_namespace':source,**p},422) for p in ({'q':'x'},{'limit':1},{'handling_status':'new'},
        {'time_from':start.replace(tzinfo=None).isoformat()},{'time_from':start.isoformat(),'time_to':start.isoformat()},{'source_namespace':' '})]
    for params,code in cases:
        path='/api/v1/socai2/incidents/grouping-summary?'+urllib.parse.urlencode(params)
        request=urllib.request.Request(cfg['base_url']+path,headers={'Authorization':'Bearer '+token})
        try:r=urllib.request.urlopen(request,timeout=cfg['timeout_seconds'])
        except urllib.error.HTTPError as exc:r=exc
        with r:status,body=r.code,json.load(r)
        calls.append({'method':'GET','path':path,'status':status,'body':body});save(out/'responses.json',calls);assert status==code,(params,status,body)
        if code==200:
            assert body['schema_version']=='socai2.incident-grouping.v1';assert datetime.fromisoformat(body['observed_at']).tzinfo
            assert {k:body[k] for k in expected(params)}==expected(params),(params,body,expected(params))
            assert body['scope']['source_namespace']==params['source_namespace']
            for field in ('time_from','time_to'):
                assert (datetime.fromisoformat(body['scope'][field]) if body['scope'][field] else None)==(datetime.fromisoformat(params[field]) if field in params else None)
    result={'passed':True,'release':contract['info']['version'],'database':cfg['database'],'http_gets':len(calls),
        'successes':sum(x['status']==200 for x in calls),'expected_422':sum(x['status']==422 for x in calls),
        'actual_counts_match_independent_sql_rows':True,'models':0,'business_writes':0}
    save(out/'verification.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['seed','verify','http'])
    for name in ('profile','fixture','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--snapshot',type=Path);args=parser.parse_args();cfg=json.loads(args.profile.read_text());args.output.mkdir(parents=True,exist_ok=False)
    snapshot=json.loads(args.snapshot.read_text()) if args.action=='http' else asyncio.run(database(cfg,args.action,args.fixture))
    save(args.output/'sql-before.json',snapshot)
    if args.action=='seed':print(json.dumps({'seeded':{k:len(snapshot[k]) for k in ('alerts','incidents','links')}}));return
    result=verify(cfg,args.fixture,snapshot,args.output)
    if args.action=='verify':
        after=asyncio.run(database(cfg,'read',args.fixture));save(args.output/'sql-after.json',after);assert snapshot==after;result['sql_unchanged']=True;save(args.output/'verification.json',result)
    print(json.dumps(result))

if __name__=='__main__':main()
