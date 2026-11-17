"""One synthetic local candidate flow, original-material reads and explicit association."""
import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['seed', 'verify'])
parser.add_argument('--profile', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
cfg = json.loads(args.profile.read_text())
os.environ.update(json.loads((ROOT / cfg['environment']).read_text()))
sys.path.insert(0, cfg['runtime_directory'])
from app.models import socai2 as m
from app.socai2.case_service import CaseService
from httpx import AsyncClient
from sqlalchemy import URL, insert, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def save(name, value):
    (args.output / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


async def main():
    assert cfg['database'] == 'v12_upgrade_dev' and cfg['production_writes'] is False
    db = json.loads((ROOT / cfg['database_config']).read_text())
    assert (db['host'], db['port'], db['processing_database'], db['processor']) == (cfg['host'], cfg['port'], cfg['database'], cfg['role'])
    url = URL.create('postgresql+psycopg', username=db['admin'], password=Path(db['password_file']).read_text().strip(), host=cfg['host'], port=cfg['port'], database=cfg['database'])
    engine = create_async_engine(url, connect_args={'sslmode':cfg['sslmode'],'options':'-c role='+cfg['role']})
    svc = CaseService(async_sessionmaker(engine, expire_on_commit=False))
    tenant = UUID(cfg['tenant_id'])
    secret = json.loads((ROOT / cfg['credential']['file']).read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/(args.action+'-http.json')).exists(), 'preserve prior attempt before explicit continuation'
    receipts = []
    base = '/api/v1/socai2'
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text('select current_database(),current_user'))).one() == (cfg['database'],cfg['role'])
        async with AsyncClient(base_url=cfg['base_url'],timeout=cfg['timeout_seconds'],headers={'Authorization':'Bearer '+secret['api_key']}) as http:
            async def req(method,path,body=None,params=None,expected=200):
                save(args.action+'-intent-'+str(len(receipts)+1),{'method':method,'path':path,'body':body,'params':params})
                response=await http.request(method,path,json=body,params=params)
                try:data=response.json()
                except ValueError:data={'non_json':response.text}
                receipts.append({'method':method,'path':path,'params':params,'input':body,'status':response.status_code,'body':data})
                save(args.action+'-http',receipts)
                assert response.status_code==expected,(response.status_code,data)
                return data

            if args.action=='seed':
                assert not (args.output/'fixture.json').exists()
                origin='synthetic-exploration-'+str(uuid4())
                names=['seed','unknown_seed','multi','ip','hash','other_object_source','late','unknown','other_alert_source','old_material']
                alerts={name:str(uuid4()) for name in names}
                materials={name:str(uuid4()) for name in names}
                objects={}
                fixture={'alerts':alerts,'materials':materials,'objects':objects,'origin':origin,'association_key':str(uuid4())}
                save('fixture-intent',fixture)
                at=datetime(2026,11,13,10,tzinfo=UTC)
                data={
                    'seed':[('host','HOST-A',{}),('user','UserA',{}),('ip','192.0.2.9',{}),('domain','test.example',{}),('url','https://test.example/a',{}),('hash','a'*64,{'algorithm':'SHA256'}),('hash','b'*64,{}),('process','123',{})],
                    'unknown_seed':[('host','TIME-UNKNOWN',{})],
                    'multi':[('host','HOST-A',{}),('ip','192.0.2.9',{}),('hash','A'*64,{'algorithm':'sha-256'}),('ip','192.0.2.9',{})],
                    'ip':[('ip','192.0.2.9',{})],
                    'hash':[('hash','a'*64,{'algorithm':'SHA_256'}),('hash','b'*64,{})],
                    'other_object_source':[('host','HOST-A',{}),('hash','a'*64,{'algorithm':'SHA512'})],
                    'late':[('host','HOST-A',{})], 'unknown':[('host','HOST-A',{})],
                    'other_alert_source':[('ip','192.0.2.9',{})], 'old_material':[('host','UNRELATED',{})],
                }
                async with svc.transaction(tenant) as store:
                    for name in names:
                        aid,mid=UUID(alerts[name]),UUID(materials[name])
                        when=None if name in {'unknown','unknown_seed'} else at+timedelta(minutes={'multi':20,'ip':10,'hash':30}.get(name,0))
                        if name=='late':when=at+timedelta(days=3)
                        source=origin+'-other' if name=='other_alert_source' else origin
                        await store.db.execute(insert(m.Alerts).values(id=aid,tenant_id=tenant,source_namespace=source,source_identity_key=str(aid),title='SYNTHETIC exploration '+name,severity='medium',event_time=when,event_time_source='source' if when else 'unknown'))
                        raw={'synthetic':True,'objects':[]}
                        rows=[]
                        objects[name]=[]
                        for i,(typ,value,attrs) in enumerate(data[name]):
                            oid=uuid4();objects[name].append(str(oid))
                            raw['objects'].append({'type':typ,'value':value,**attrs})
                            ns=origin+'-object-other' if name=='other_object_source' and typ=='host' else origin
                            row=dict(id=oid,tenant_id=tenant,alert_id=aid,material_id=mid,object_type=typ,object_key=json.dumps([typ,value]),object_role='ioc' if typ=='hash' else 'entity',namespace=ns,raw_value=value,normalized_value=value,source_path=f'$.raw_json.objects[{i}].value',attributes=attrs)
                            rows.append(row)
                        await store.db.execute(insert(m.AlertMaterials).values(id=mid,tenant_id=tenant,alert_id=aid,revision=2 if name=='old_material' else 1,raw_json=raw,detection={},source_scope={},retention={},material_state='complete'))
                        for row in rows:await store.db.execute(insert(m.AlertObjects).values(**row))
                        await store.db.execute(update(m.Alerts).where(m.Alerts.id==aid).values(latest_material_id=mid))
                        if name=='old_material':
                            oldmid,oldoid=uuid4(),uuid4();fixture['old_object_id']=str(oldoid)
                            await store.db.execute(insert(m.AlertMaterials).values(id=oldmid,tenant_id=tenant,alert_id=aid,revision=1,raw_json={'host':'HOST-A'},detection={},source_scope={},retention={},material_state='complete'))
                            await store.db.execute(insert(m.AlertObjects).values(id=oldoid,tenant_id=tenant,alert_id=aid,material_id=oldmid,object_type='host',object_key='host:HOST-A',object_role='entity',namespace=origin,raw_value='HOST-A',normalized_value='HOST-A',source_path='host',attributes={}))
                save('seed-data',fixture)
                c=await req('POST',base+'/cases',{'operation_key':str(uuid4()),'title':cfg['title'],'alert_ids':[alerts['seed'],alerts['unknown_seed']]})
                fixture['case_id']=c['case_id'];save('fixture',fixture)
                other=await req('POST',base+'/cases',{'operation_key':str(uuid4()),'title':cfg['title']+' other','alert_ids':[alerts['multi']]})
                fixture['other_case_id']=other['case_id'];save('fixture',fixture)
                save('seed-summary',{'passed':True,'alerts':len(names),'cases':2,'models':0,'production_writes':0})
                print(json.dumps({'seeded':True,'case_id':fixture['case_id']}));return

            f=json.loads((args.output/'fixture.json').read_text());cid=UUID(f['case_id']);path=base+'/cases/'+str(cid);endpoint=path+'/exploration-candidates';a=f['alerts'];o=f['objects']
            async def snapshot():
                out={}
                async with svc.transaction(tenant,readonly=True) as store:
                    for table in [m.Alerts,m.AlertMaterials,m.AlertObjects,m.Cases,m.CaseAlerts,m.CaseIncidents,m.Runs,m.Results,m.Activities,m.ActivityTargets]:
                        t=table.__table__
                        if table==m.Alerts:cond=t.c.id.in_([UUID(x) for x in a.values()])
                        elif 'alert_id' in t.c and table not in [m.CaseAlerts,m.CaseIncidents,m.Runs,m.Results,m.Activities,m.ActivityTargets]:cond=t.c.alert_id.in_([UUID(x) for x in a.values()])
                        elif table==m.Cases:cond=t.c.id.in_([cid,UUID(f['other_case_id'])])
                        elif 'case_id' in t.c:cond=t.c.case_id.in_([cid,UUID(f['other_case_id'])])
                        else:cond=t.c.subject_case_id==cid
                        out[t.name]=[dict(r) for r in (await store.db.execute(select(t).where(t.c.tenant_id==tenant,cond).order_by(t.c.id))).mappings()]
                return json.loads(json.dumps(out,default=str))
            before=await snapshot();save('sql-before',before)
            first=await req('GET',endpoint)
            assert [x['alert']['id'] for x in first['items']]==[a['multi'],a['ip'],a['hash']],first
            assert first['total']==3 and first['items'][0]['shared_object_count']==3 and len(first['items'][0]['matches'])==4
            assert first['items'][0]['case_ids']==[f['other_case_id']] and not first['items'][0]['already_in_case']
            assert first['scope']['time_from']=='2026-11-12T10:00:00Z' and first['scope']['time_to']=='2026-11-14T10:00:00Z'
            assert {x['reason'] for x in first['scope']['excluded_objects']}=={'unsupported_object_type','hash_algorithm_or_value_invalid'}
            p1=await req('GET',endpoint,params={'limit':1});p2=await req('GET',endpoint,params={'limit':1,'cursor':p1['next_cursor']});p3=await req('GET',endpoint,params={'limit':1,'cursor':p2['next_cursor']})
            assert [p['items'][0]['alert']['id'] for p in [p1,p2,p3]]==[a['multi'],a['ip'],a['hash']] and p3['next_cursor'] is None
            await req('GET',endpoint,params={'alert_id':a['seed'],'cursor':p1['next_cursor']},expected=409)
            ip=await req('GET',endpoint,params={'object_id':o['seed'][2]});assert {x['alert']['id'] for x in ip['items']}=={a['multi'],a['ip']}
            h=await req('GET',endpoint,params={'object_id':o['seed'][5]});assert {x['alert']['id'] for x in h['items']}=={a['multi'],a['hash']}
            assert all(z['basis']=='same_hash_algorithm_and_value' and z['seed']['algorithm']==z['candidate']['algorithm']=='SHA256' for x in h['items'] for z in x['matches'])
            await req('GET',endpoint,params={'object_id':o['seed'][6]},expected=422)
            await req('GET',endpoint,params={'object_id':o['seed'][7]},expected=422)
            await req('GET',endpoint,params={'object_id':f['old_object_id']},expected=409)
            await req('GET',endpoint,params={'alert_id':a['other_alert_source']},expected=404)
            await req('GET',endpoint,params={'alert_id':a['unknown_seed']},expected=422)
            unknown=await req('GET',endpoint,params={'alert_id':a['unknown_seed'],'time_from':'2026-11-12T00:00:00Z','time_to':'2026-11-15T00:00:00Z'});assert unknown['total']==0
            bounded=await req('GET',endpoint,params={'time_from':'2026-11-13T10:10:00Z','time_to':'2026-11-13T10:20:00Z'});assert [x['alert']['id'] for x in bounded['items']]==[a['ip']]
            wider=await req('GET',endpoint,params={'time_from':'2026-11-12T00:00:00Z','time_to':'2026-11-18T00:00:00Z'});assert wider['total']==4 and a['late'] in [x['alert']['id'] for x in wider['items']]
            for params in [{'time_from':'2026-11-12T00:00:00Z'},{'time_from':'2026-11-12T00:00:00','time_to':'2026-11-13T00:00:00'}, {'alert_id':a['seed'],'object_id':o['seed'][0]},{'cursor':'invalid'},{'unsupported':1}, [('limit',1),('limit',2)]]:
                await req('GET',endpoint,params=params,expected=422)
            await req('GET',base+'/cases/'+str(uuid4())+'/exploration-candidates',expected=404)
            # Read both material originals and the unchanged alert DTO.
            matched=first['items'][0]
            for ref in [matched['matches'][0]['seed'],matched['matches'][0]['candidate']]:
                material=await req('GET',base+'/alerts/'+ref['alert_id']+'/materials/'+ref['material_id'])
                save('source-material-'+ref['material_id'],material)
                assert ref['raw_value'] in json.dumps(material,ensure_ascii=False)
            detail=await req('GET',base+'/alerts/'+a['multi']);assert detail['facts']==matched['alert']
            case_before=await req('GET',path)
            after=await snapshot();save('sql-after',after);assert before==after
            save('query-verification',{'passed':True,'http_requests':len(receipts),'sql_tables_unchanged':list(before),'models':0,'production_writes':0})
            added=await req('POST',path+'/associations',{'operation_key':f['association_key'],'expected_scope_revision':case_before['case']['scope_revision'],'alert_ids':[a['multi']]})
            assert added['added_alert_ids']==[a['multi']]
            final=await req('GET',path);save('case-after-association',final)
            after_add=await req('GET',endpoint,params={'object_id':o['seed'][2]});row=next(x for x in after_add['items'] if x['alert']['id']==a['multi']);assert row['already_in_case'] and set(row['case_ids'])=={f['case_id'],f['other_case_id']}
            await req('GET',endpoint,params={'cursor':p1['next_cursor']},expected=409)
            save('verification',{'passed':True,'http_requests':len(receipts),'case_id':str(cid),'new_association':a['multi'],'original_other_case_preserved':True,'models':0,'production_writes':0,'query_sql_unchanged':True})
            print(json.dumps({'passed':True,'http_requests':len(receipts)}))
    except Exception as exc:
        save(args.action+'-failure',{'error_type':type(exc).__name__,'message':str(exc)})
        raise
    finally:await engine.dispose()


if __name__=='__main__':asyncio.run(main())
