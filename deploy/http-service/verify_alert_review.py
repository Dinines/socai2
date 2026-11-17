"""One local synthetic batch for source-backed alert review HTTP queries."""
import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['seed','verify']);p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();cfg=json.loads(a.profile.read_text());os.environ.update(json.loads((ROOT/cfg['environment']).read_text()));sys.path.insert(0,cfg['runtime_directory'])
from app.models import socai2 as m
from app.socai2.baseline_service import BaselineService
from sqlalchemy import URL,insert,select,text,update
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine
from httpx import AsyncClient


def save(name,obj):
    (a.output/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+'\n')


async def main():
    assert cfg['database']=='v12_upgrade_dev' and cfg['production_writes'] is False
    db=json.loads((ROOT/cfg['database_config']).read_text());assert (db['host'],db['port'],db['processing_database'],db['processor'])==(cfg['host'],cfg['port'],cfg['database'],cfg['role'])
    url=URL.create('postgresql+psycopg',username=db['admin'],password=Path(db['password_file']).read_text().strip(),host=cfg['host'],port=cfg['port'],database=cfg['database'])
    engine=create_async_engine(url,connect_args={'sslmode':cfg['sslmode'],'options':'-c role='+cfg['role']});svc=BaselineService(async_sessionmaker(engine,expire_on_commit=False));tenant=UUID(cfg['tenant_id']);secret=json.loads((ROOT/cfg['credential']['file']).read_text());a.output.mkdir(parents=True,exist_ok=True)
    assert not (a.output/(a.action+'-http.json')).exists(),'preserve completed attempts'
    receipts=[];base='/api/v1/socai2'
    try:
        async with engine.connect() as conn:assert (await conn.execute(text('select current_database(),current_user'))).one()==(cfg['database'],cfg['role'])
        async with AsyncClient(base_url=cfg['base_url'],timeout=cfg['timeout_seconds'],headers={'Authorization':'Bearer '+secret['api_key']}) as http:
            async def req(method,path,body=None,params=None,expected=200):
                save(a.action+'-intent-'+str(len(receipts)+1),{'method':method,'path':path,'input':body,'params':params})
                r=await http.request(method,path,json=body,params=params)
                try:data=r.json()
                except ValueError:data={'non_json':r.text}
                receipts.append({'method':method,'path':path,'input':body,'params':params,'status':r.status_code,'body':data});save(a.action+'-http',receipts)
                assert r.status_code==expected,(r.status_code,data)
                return data
            if a.action=='seed':
                at=datetime(2026,11,13,12,tzinfo=UTC);origin='synthetic-alert-review-'+str(uuid4());host=('host','HOST-A',{});ip=('ip','192.0.2.15',{});sha=('hash','a'*64,{'algorithm':'SHA256'})
                data={'seed':([host,ip,sha,('hash','b'*64,{}),('file','same-name.exe',{})],['Execution','Execution'],0),
                    'multi':([host,ip,ip,('hash','A'*64,{'algorithm':'sha-256'})],['Execution','Execution','Persistence'], -1),
                    'ip':([ip],[], -2),'hash':([('hash','a'*64,{'algorithm':'SHA_256'})],[], -2),
                    'host_only':([host],['Persistence'],-3),'tactic_only':([('host','OTHER',{})],['Execution'],-3),
                    'bad_hash':([('hash','a'*64,{'algorithm':'SHA512'}),('hash','b'*64,{})],[],-3),
                    'file_only':([('file','same-name.exe',{})],[],-3),'wrong_namespace':([host,ip],['Execution'],-3),
                    'wrong_source':([ip],[],-3),'old_material':([('host','OTHER',{})],['Execution'],-3),
                    'unknown':([ip],[],None),'unknown_seed':([ip],[],None),'same_time':([ip],[],0),'future':([ip],[],1),
                    'boundary':([ip],[],-30*24*60),'outside':([ip],[],-30*24*60-1),'bad_tags':([host],'Execution',-3),
                    'tactic_case':([host],['execution'],-3),'empty_seed':([('user','UserA',{})],[],0)}
                alerts={n:str(uuid4()) for n in data};materials={n:str(uuid4()) for n in data};objects={};iid=uuid4()
                f={'origin':origin,'alerts':alerts,'materials':materials,'objects':objects,'incident_id':str(iid),'seed_time':at.isoformat()};save('fixture-intent',f)
                async with svc.transaction(tenant) as store:
                    for n,(items,tags,minutes) in data.items():
                        aid,mid=UUID(alerts[n]),UUID(materials[n]);when=at+timedelta(minutes=minutes) if minutes is not None else None
                        await store.db.execute(insert(m.Alerts).values(id=aid,tenant_id=tenant,source_namespace=origin+'-other' if n=='wrong_source' else origin,source_identity_key=str(aid),title='SYNTHETIC alert review '+n,severity='medium',event_time=when,event_time_source='source' if when else 'unknown',handling_status='completed' if n=='ip' else 'new',disposition='false_positive' if n=='ip' else None))
                        raw={'synthetic':True,'objects':[{'type':t,'value':v,**attrs} for t,v,attrs in items]}
                        await store.db.execute(insert(m.AlertMaterials).values(id=mid,tenant_id=tenant,alert_id=aid,revision=2 if n=='old_material' else 1,raw_json=raw,detection={'tactics':tags},source_scope={},retention={},material_state='complete'))
                        objects[n]=[]
                        for index,(typ,value,attrs) in enumerate(items):
                            oid=uuid4();objects[n].append(str(oid))
                            await store.db.execute(insert(m.AlertObjects).values(id=oid,tenant_id=tenant,alert_id=aid,material_id=mid,object_type=typ,object_key=typ+':'+value,object_role='ioc' if typ in ['ip','hash'] else 'entity',namespace=origin+'-other' if n=='wrong_namespace' else origin,raw_value=value,normalized_value=value,source_path=f'$.raw_json.objects[{index}].value',attributes=attrs))
                        await store.db.execute(update(m.Alerts).where(m.Alerts.id==aid).values(latest_material_id=mid))
                        if n=='old_material':
                            old=uuid4();await store.db.execute(insert(m.AlertMaterials).values(id=old,tenant_id=tenant,alert_id=aid,revision=1,raw_json={'host':'HOST-A'},detection={'tactics':['Execution']},source_scope={},retention={},material_state='complete'))
                            await store.db.execute(insert(m.AlertObjects).values(id=uuid4(),tenant_id=tenant,alert_id=aid,material_id=old,object_type='host',object_key='host:HOST-A',object_role='entity',namespace=origin,raw_value='HOST-A',normalized_value='HOST-A',source_path='$.raw_json.host',attributes={}))
                    await store.db.execute(insert(m.Incidents).values(id=iid,tenant_id=tenant,source_namespace=origin,source_incident_id=str(iid),title='SYNTHETIC review source incident'))
                    await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(),tenant_id=tenant,incident_id=iid,alert_id=UUID(alerts['multi']),membership_source='manual',correlation_basis={'synthetic':True},basis_version='synthetic.review.v1',source_operation_id=uuid4()))
                save('seed-data',f)
                case=await req('POST',base+'/cases',{'operation_key':str(uuid4()),'title':'SYNTHETIC review source case','alert_ids':[alerts['multi']]});f['case_id']=case['case_id'];save('fixture',f);print(json.dumps({'seeded':len(alerts),'case_id':f['case_id']}));return

            f=json.loads((a.output/'fixture.json').read_text());ids=f['alerts'];endpoint=base+'/alerts/'+ids['seed']+'/review-candidates'
            async def snapshot():
                out={}
                async with svc.transaction(tenant,readonly=True) as store:
                    for model in [m.Alerts,m.AlertMaterials,m.AlertObjects,m.AlertAssessments,m.IncidentAlerts,m.Incidents,m.CaseAlerts,m.Cases,m.Runs,m.Results]:
                        t=model.__table__
                        if model==m.Alerts:cond=t.c.id.in_([UUID(v) for v in ids.values()])
                        elif model==m.Cases:cond=t.c.id==UUID(f['case_id'])
                        elif model==m.Incidents:cond=t.c.id==UUID(f['incident_id'])
                        elif model in [m.Runs,m.Results]:cond=t.c.case_id==UUID(f['case_id'])
                        else:cond=t.c.alert_id.in_([UUID(v) for v in ids.values()])
                        out[t.name]=[dict(row) for row in (await store.db.execute(select(t).where(t.c.tenant_id==tenant,cond).order_by(t.c.id))).mappings()]
                return json.loads(json.dumps(out,default=str))
            before=await snapshot();save('sql-before',before)
            first=await req('GET',endpoint);expected=[ids['multi'],*sorted([ids['ip'],ids['hash']],reverse=True),ids['boundary']]
            assert [x['alert']['id'] for x in first['items']]==expected and first['total']==4 and first['next_cursor'] is None,first
            assert first['scope']['time_from']=='2026-10-14T12:00:00Z' and first['scope']['time_to']=='2026-11-13T12:00:00Z'
            row=first['items'][0];assert len(row['matches'])==4 and len(row['matched_rules'])==3 and row['case_ids']==[f['case_id']] and row['incident_ids']==[f['incident_id']]
            match=next(p for p in row['matches'] if p['rule']=='same_host_and_tactic');assert match['shared_tactics']==[{'label':'Execution','seed_source_paths':['$.detection.tactics[0]','$.detection.tactics[1]'],'candidate_source_paths':['$.detection.tactics[0]','$.detection.tactics[1]']}]
            assert next(x for x in first['items'] if x['alert']['id']==ids['ip'])['alert']['disposition']=='false_positive'
            one=await req('GET',endpoint,params={'limit':2});two=await req('GET',endpoint,params={'limit':2,'cursor':one['next_cursor']});assert [x['alert']['id'] for p in [one,two] for x in p['items']]==expected and two['next_cursor'] is None
            await req('GET',endpoint,params={'cursor':one['next_cursor'],'time_from':'2026-11-13T12:00:00Z','time_to':'2026-11-14T12:00:00Z'},expected=409)
            later=await req('GET',endpoint,params={'time_from':'2026-11-13T12:00:00Z','time_to':'2026-11-14T12:00:00Z'});assert [x['alert']['id'] for x in later['items']]==[ids['future'],ids['same_time']]
            await req('GET',base+'/alerts/'+ids['unknown_seed']+'/review-candidates',expected=422)
            unknown=await req('GET',base+'/alerts/'+ids['unknown_seed']+'/review-candidates',params={'time_from':'2026-11-13T11:00:00Z','time_to':'2026-11-13T12:00:00Z'});assert unknown['total']==2 and all(x['time_delta_seconds'] is None for x in unknown['items'])
            empty=await req('GET',base+'/alerts/'+ids['empty_seed']+'/review-candidates');assert empty['total']==0 and len(empty['scope']['unavailable_rules'])==3
            for params in [{'time_from':'2026-11-01T00:00:00Z'},{'time_from':'2026-11-01T00:00:00','time_to':'2026-11-02T00:00:00'},{'cursor':'bad'},{'limit':0},{'unknown':1},[('limit',1),('limit',2)]]:await req('GET',endpoint,params=params,expected=422)
            await req('GET',base+'/alerts/'+str(uuid4())+'/review-candidates',expected=404)
            for x in first['items']:
                assert (await req('GET',base+'/alerts/'+x['alert']['id']))['facts']==x['alert']
            for ref in [match['seed'],match['candidate']]:
                material=await req('GET',base+'/alerts/'+ref['alert_id']+'/materials/'+ref['material_id']);assert ref['raw_value'] in json.dumps(material)
            after=await snapshot();save('sql-after',after);assert before==after
            # A new source-material pointer in this synthetic fixture invalidates its old cursor.
            newmid=uuid4()
            async with svc.transaction(tenant) as store:
                await store.db.execute(insert(m.AlertMaterials).values(id=newmid,tenant_id=tenant,alert_id=UUID(ids['seed']),revision=2,raw_json={'synthetic':True},detection={},source_scope={},retention={},material_state='complete'))
                await store.db.execute(update(m.Alerts).where(m.Alerts.id==UUID(ids['seed'])).values(latest_material_id=newmid))
            await req('GET',endpoint,params={'cursor':one['next_cursor']},expected=409)
            assert (await req('GET',endpoint))['total']==0
            save('summary',{'passed':True,'http_requests':len(receipts),'readonly_tables':list(before),'source_pointer_fixture_change_after_readonly_check':True,'source_alert_id':ids['seed'],'readback_alert_id':ids['future'],'models':0,'production_writes':0});print(json.dumps({'passed':True,'http_requests':len(receipts)}))
    finally:await engine.dispose()

asyncio.run(main())
