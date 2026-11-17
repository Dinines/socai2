"""One local synthetic story fixture and read-only HTTP/SQL acceptance; no models."""
import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['seed', 'verify', 'snapshot-verify'])
parser.add_argument('--profile', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
cfg = json.loads(args.profile.read_text())
os.environ.update(json.loads((ROOT / cfg['environment']).read_text()))
os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(ROOT / cfg['policy'])
sys.path.insert(0, cfg['runtime_directory'])
from app.models import socai2 as m
from app.socai2.baseline_contracts import Actor, FULL_EXECUTOR_VERSION, Publication, Scope, Start
from app.socai2.baseline_context import reference
from app.socai2.case_service import CaseService
from app.socai2.runtime_policy import active_policy
from sqlalchemy import URL, insert, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from httpx import AsyncClient


def value(v):
    if hasattr(v, 'model_dump'):
        return v.model_dump(mode='json')
    return str(v)


def save(name, obj):
    (args.output / (name + '.json')).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=value) + '\n')


async def main():
    assert cfg['database'] == 'v12_upgrade_dev' and cfg['production_writes'] is False
    db = json.loads((ROOT / cfg['database_config']).read_text())
    assert (db['host'], db['port'], db['processing_database'], db['processor']) == (cfg['host'], cfg['port'], cfg['database'], cfg['role'])
    url = URL.create('postgresql+psycopg', username=db['admin'], password=Path(db['password_file']).read_text().strip(), host=cfg['host'], port=cfg['port'], database=cfg['database'])
    engine = create_async_engine(url, connect_args={'sslmode': cfg['sslmode'], 'options': '-c role=' + cfg['role']})
    service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
    tenant = UUID(cfg['tenant_id'])
    secret = json.loads((ROOT / cfg['credential']['file']).read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    receipt_path = args.output / (args.action + '-http.json')
    assert not receipt_path.exists(), 'use a new output or preserve prior failure before scoped continuation'
    receipts = []
    base = '/api/v1/socai2/cases'
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text('select current_database(),current_user'))).one() == (cfg['database'], cfg['role'])
        async with AsyncClient(base_url=cfg['base_url'], timeout=cfg['timeout_seconds'], headers={'Authorization': 'Bearer ' + secret['api_key']}) as http:
            async def request(method, path, body=None, expected=200, params=None):
                save(args.action + '-intent-' + str(len(receipts)+1), {'method': method, 'path': path, 'params': params, 'body': body})
                response = await http.request(method, path, json=body, params=params)
                try:
                    data = response.json()
                except ValueError:
                    data = {'non_json': response.text}
                receipts.append({'method': method, 'path': path, 'params': params, 'input': body, 'status': response.status_code, 'body': data})
                save(args.action + '-http', receipts)
                assert response.status_code == expected, (response.status_code, data)
                return data

            if args.action == 'seed':
                assert not (args.output/'fixture.json').exists()
                alerts, materials = [uuid4() for _ in range(3)], [uuid4() for _ in range(3)]
                async with service.transaction(tenant) as store:
                    for i, (aid, mid) in enumerate(zip(alerts, materials, strict=True)):
                        await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant, source_namespace='synthetic-story-20261113', source_identity_key=str(aid),
                            title=['SYNTHETIC story 100%_literal', 'SYNTHETIC second alert', 'SYNTHETIC unknown time'][i], severity=['high','low',None][i],
                            event_time=datetime(2026,11,13,tzinfo=UTC) if i<2 else None, event_time_source='source' if i<2 else 'unknown'))
                        await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid, revision=1,
                            raw_text='SYNTHETIC story input; not an actual security observation', raw_json={'synthetic':True}, detection={}, source_scope={}, retention={}, material_state='complete'))
                        await store.db.execute(update(m.Alerts).where(m.Alerts.id==aid).values(latest_material_id=mid))
                        await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant, alert_id=aid, material_id=mid, object_key=f'story-host-{i}',
                            object_type='host', object_role='entity', namespace='synthetic-story', raw_value=f'StoryHost{i}', normalized_value=f'storyhost{i}', source_path='host', attributes={}))
                        if i==0:
                            await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant, alert_id=aid, material_id=mid, object_key='story-user',
                                object_type='user', object_role='entity', namespace='synthetic-story', raw_value='StoryOperator', normalized_value='storyoperator', source_path='user', attributes={}))
                created = await request('POST', base, {'operation_key':str(uuid4()), 'title':cfg['title'], 'alert_ids':list(map(str,alerts))})
                other = await request('POST', base, {'operation_key':str(uuid4()), 'title':cfg['title']+' other', 'alert_ids':[str(alerts[0])]})
                cid, rid = UUID(created['case_id']), UUID(created['pending_run_id'])
                fixture={'case_id':str(cid),'other_case_id':other['case_id'],'alerts':list(map(str,alerts)),'materials':list(map(str,materials)),'run_id':str(rid)}
                save('fixture',fixture)
                async with service.transaction(tenant,readonly=True) as store:
                    case=await store.case(cid,lock=False)
                    actor=Actor(user_id=case['created_by'],name='Synthetic story fixture')
                    limits=active_policy().case.limits(await store.now(),'synthetic.story.v1')
                async def idle(_):
                    pass
                await service.start(tenant,cid,rid,Start(operation_key=uuid4(),expected_scope_revision=1),actor=actor,executor=idle,executor_version=FULL_EXECUTOR_VERSION,limits=limits)
                scope=Scope(kind='whole_case',alert_ids=alerts,object_keys=[],window_start=None,window_end=None,limitations=[])
                publication=Publication(operation_key=uuid4(),terminal_state='completed',stop_reason='synthetic_story_fixture',title='SYNTHETIC saved investigation',
                    conclusion='SYNTHETIC conclusion NeedleConclusion; still requires confirmation.',conclusion_state='uncertain',conclusion_origin='model',validation_state='accepted',
                    closing_note='Program fixture only; zero model calls.',findings=[],recommendations=[],questions=[],change_kind='initial',change_summary=None,delivery_state='partial',
                    case_impact={'summary':None,'supported_changes':[],'cannot_generalize':['Synthetic only'],'affected_scope':scope,'next_steps':[]},
                    members=[{'alert_id':aid,'read_state':'read','assessment_state':'unresolved','conclusion_covered':True,'assessment':None,'limitations':'Synthetic only',
                        'evidence_refs':[reference('alert_material',mid,'observation')]} for aid,mid in zip(alerts,materials,strict=True)])
                save('publication-input',publication)
                published=await service.publish(tenant,cid,rid,publication)
                save('publication-output',published)
                fixture['result_id']=published['result_id']
                path=base+'/'+str(cid)
                task=(await request('POST',path+'/tasks',{'operation_key':str(uuid4()),'expected_scope_revision':1,'title':'SYNTHETIC human confirmation',
                    'state':'completed','result_text':'SYNTHETIC NeedleHuman confirmation','result_scope':scope.model_dump(mode='json')}))['task']
                fixture['task_id']=task['id'];fixture['revision_id']=task['current_revision_id']
                await request('PUT',path+'/tasks/'+task['id'],{'operation_key':str(uuid4()),'expected_scope_revision':1,'expected_row_version':task['row_version'],
                    'title':task['current']['title'],'state':'in_progress'})
                prepared=await request('POST',path+'/baseline/prepare',{'operation_key':str(uuid4()),'expected_scope_revision':1})
                fixture['active_run_id']=prepared['pending_run_id']
                await service.start(tenant,cid,UUID(prepared['pending_run_id']),Start(operation_key=uuid4(),expected_scope_revision=1),actor=actor,
                    executor=idle,executor_version=FULL_EXECUTOR_VERSION,limits=limits)
                save('fixture',fixture)
                save('seed-verification',{'passed':True,'case_id':str(cid),'models':0,'run_executor':'idle program fixture; no actual model execution','database':cfg['database']})
                print('Created one story fixture and one isolation Case; zero model calls')
                return

            fixture=json.loads((args.output/'fixture.json').read_text());cid=UUID(fixture['case_id']);path=base+'/'+str(cid)
            async def snapshot(name):
                async with service.transaction(tenant,readonly=True) as store:
                    tables=[m.Cases,m.CaseAlerts,m.Runs,m.RunMembers,m.Results,m.ResultMembers,m.Tasks,m.TaskRevisions]
                    data={table.__tablename__:[dict(r) for r in (await store.db.execute(select(table.__table__).where(table.tenant_id==tenant,
                        (table.id if table is m.Cases else table.case_id)==cid).order_by(table.id))).mappings()] for table in tables}
                    for table in [m.Alerts,m.AlertMaterials,m.AlertObjects]:
                        data[table.__tablename__]=[dict(r) for r in (await store.db.execute(select(table.__table__).where(table.tenant_id==tenant,
                            (table.id if table is m.Alerts else table.alert_id).in_(list(map(UUID,fixture['alerts'])))).order_by(table.id))).mappings()]
                save(name,data);return data
            before=await snapshot(args.action+'-sql-before')
            if args.action == 'snapshot-verify':
                page=await request('GET',path+'/story',params={'limit':100})
                for item in page['items']:
                    if item['alert']:
                        row=next(v for v in before['alerts'] if str(v['id'])==item['alert']['id'])
                        assert str(row['title'])==item['alert']['title'] and row['severity']==item['alert']['severity']
                        assert row['event_time']==(datetime.fromisoformat(item['occurred_at']) if item['occurred_at'] else None)
                    if item['run']:
                        row=next(v for v in before['runs'] if str(v['id'])==item['run']['id'])
                        assert row['state']==item['run']['state']
                        for result in item['results']:
                            source=next(v for v in before['results'] if str(v['id'])==result['id'])
                            assert source['conclusion']==result['conclusion'] and source['questions']==result['questions']
                    if item['task_revision']:
                        revision=item['task_revision']
                        row=next(v for v in before['task_revisions'] if str(v['id'])==revision['id'])
                        assert row['result_text']==revision['result_text']
                after=await snapshot(args.action+'-sql-after')
                assert before==after
                save('snapshot-verification',{'passed':True,'http_requests':len(receipts),'raw_sql_tables':len(before),'source_values_matched':True,'data_unchanged':True,'models':0})
                print('Raw SQL snapshots and source values passed; one GET, no writes')
                return
            contract=await request('GET','/openapi.json')
            save('candidate-openapi',contract)
            assert contract['info']['version']==cfg['release']
            page=await request('GET',path+'/story',params={'limit':100})
            assert page['total']==6 and page['next_cursor'] is None
            assert [v['kind'] for v in page['items']].count('alert')==3
            assert page['items'][-1]['alert']['event_time'] is None and page['items'][-1]['time_source']=='unknown'
            known=[(v['occurred_at'],v['id']) for v in page['items'] if v['occurred_at']]
            assert known==sorted(known,reverse=True)
            accumulated=[];cursor=None
            while True:
                part=await request('GET',path+'/story',params={'limit':2,**({'cursor':cursor} if cursor else {})})
                accumulated+=part['items'];cursor=part['next_cursor']
                if not cursor:break
            assert accumulated==page['items'] and len({v['id'] for v in accumulated})==6
            for q,kind,n in [('storyhost0','alert',1),('STORYOPERATOR','alert',1),('100%_literal','alert',1),('NeedleConclusion','investigation',1),('NeedleHuman','human_result',1),('does-not-exist','alert',0)]:
                found=await request('GET',path+'/story',params={'q':q})
                assert found['total']==n and all(v['kind']==kind for v in found['items'])
            high=await request('GET',path+'/story',params={'severity':'high'})
            assert high['total']==4 and [v['alert']['id'] for v in high['items'] if v['alert']]==[fixture['alerts'][0]]
            for item in page['items']:
                if item['alert']:
                    original=await request('GET','/api/v1/socai2/alerts/'+item['alert']['id'])
                    assert original['subject']['facts']==item['alert'] if 'subject' in original else original['facts']==item['alert']
                if item['run']:
                    original=await request('GET',path+'/runs/'+item['run']['id'])
                    assert original['run']==item['run']
                    if item['run']['state']=='running':assert item['results']==[]
                    for result in item['results']:
                        original=await request('GET',path+'/results/'+result['id'])
                        assert original['result']==result
                if item['task_revision']:
                    revision=item['task_revision']
                    original=await request('GET',path+'/tasks/'+revision['task_id']+'/revisions/'+revision['id'])
                    assert original==revision and item['is_current_task_revision'] is False
            first=await request('GET',path+'/story',params={'limit':1})
            await request('GET',path+'/story',params={'cursor':first['next_cursor'],'q':'changed'},expected=422)
            await request('GET',base+'/'+fixture['other_case_id']+'/story',params={'cursor':first['next_cursor']},expected=422)
            for params in [{'cursor':'broken'}, {'limit':0}, {'severity':'invalid'}, {'q':'x'*201}, {'extra':'x'}, [('q','a'),('q','b')]]:
                await request('GET',path+'/story',params=params,expected=422)
            await request('GET',base+'/'+str(uuid4())+'/story',expected=404)
            other=await request('GET',base+'/'+fixture['other_case_id']+'/story')
            assert other['total']==2 and not any(v['task_revision'] or v['results'] for v in other['items'])
            after=await snapshot(args.action+'-sql-after');assert before==after
            save('verification',{'passed':True,'http_requests':len(receipts),'source_tables_unchanged':True,'database':cfg['database'],'models':0,
                'checks':['actual_source_times_nulls_last','same_time_paging','keyword_name_host_account_conclusion_human','severity_alert_only',
                    'source_HTTP_readback','old_completed_revision_not_current','active_run_no_conclusion','cursor_binding_and_422','case_scope_404']})
            print('Story HTTP/SQL verification passed:',len(receipts),'requests')
    finally:
        await engine.dispose()


if __name__=='__main__':
    asyncio.run(main())
