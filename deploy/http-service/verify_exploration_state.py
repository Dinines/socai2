"""Direct synthetic local save/restore acceptance; no models or production writes."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--profile', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--continue-history', action='store_true')
args = p.parse_args()
cfg = json.loads(args.profile.read_text())
os.environ.update(json.loads((ROOT / cfg['environment']).read_text()))
os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(ROOT / cfg['policy'])
sys.path.insert(0, cfg['runtime_directory'])
from app.models import socai2 as m
from app.socai2.baseline_contracts import Actor, FULL_EXECUTOR_VERSION, Publication, Scope, Start
from app.socai2.baseline_context import reference
from app.socai2.case_contracts import PrepareBaseline
from app.socai2.case_service import CaseService
from app.socai2.runtime_policy import active_policy
from sqlalchemy import URL, insert, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from httpx import AsyncClient


def save(name, obj):
    (args.output / (name + '.json')).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + '\n')


async def main():
    assert cfg['database'] == 'v12_upgrade_dev' and cfg['production_writes'] is False
    db = json.loads((ROOT / cfg['database_config']).read_text())
    assert (db['host'], db['port'], db['processing_database'], db['processor']) == (cfg['host'], cfg['port'], cfg['database'], cfg['role'])
    url = URL.create('postgresql+psycopg', username=db['admin'], password=Path(db['password_file']).read_text().strip(), host=cfg['host'], port=cfg['port'], database=cfg['database'])
    engine = create_async_engine(url, connect_args={'sslmode': cfg['sslmode'], 'options': '-c role=' + cfg['role']})
    service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
    tenant = UUID(cfg['tenant_id'])
    secret = json.loads((ROOT / cfg['credential']['file']).read_text())
    prefix = 'continuation' if args.continue_history else 'verify'
    assert not (args.output / (prefix+'-http.json')).exists(), 'preserve previous evidence'
    f = json.loads((args.output / 'fixture.json').read_text())
    cid = UUID(f['case_id']); path = '/api/v1/socai2/cases/' + str(cid)
    receipts = []
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text('select current_database(),current_user'))).one() == (cfg['database'], cfg['role'])
        async with AsyncClient(base_url=cfg['base_url'], timeout=cfg['timeout_seconds'], headers={'Authorization': 'Bearer '+secret['api_key']}) as http:
            async def req(method, suffix='', body=None, expected=200, params=None, other=None):
                route = other or path + suffix
                save(prefix+'-intent-'+str(len(receipts)+1), {'method':method,'path':route,'body':body,'params':params})
                r = await http.request(method, route, json=body, params=params)
                try: data = r.json()
                except ValueError: data = {'non_json':r.text}
                receipts.append({'method':method,'path':route,'input':body,'params':params,'status':r.status_code,'body':data})
                save(prefix+'-http',receipts)
                assert r.status_code == expected, (r.status_code, data)
                return data

            async def protected():
                out = {}
                async with service.transaction(tenant,readonly=True) as store:
                    for model in [m.Cases,m.CaseAlerts,m.CaseIncidents,m.Runs,m.Results,m.Tasks,m.CaseAssessments]:
                        t=model.__table__; key=t.c.id if model is m.Cases else t.c.case_id
                        out[t.name]=[dict(r) for r in (await store.db.execute(select(t).where(t.c.tenant_id==tenant,key==cid).order_by(t.c.id))).mappings()]
                return json.loads(json.dumps(out,default=str))

            if not args.continue_history:
                before = await protected(); save('sql-before',before)
                assert (await req('GET','/exploration'))['snapshot'] is None
                b = await req('GET','/exploration-base'); assert b['kind']=='members' and b['run_id'] is None
                candidates=await req('GET','/exploration-candidates')
                pair=candidates['items'][0]['matches'][0]
                link={'seed_object_id':pair['seed']['id'],'candidate_object_id':pair['candidate']['id']}
                body={'operation_key':str(uuid4()),'expected_snapshot_id':None,'base_fingerprint':b['fingerprint'],'expanded_links':[link],
                    'view_state':{'positions':{'alert:'+f['alerts']['seed']:{'x':12.5,'y':-90}},'selected':[pair['candidate']['id']],'zoom':1.25,'filters':{'high':False}}}
                first=await req('PUT','/exploration',body); assert first['base']==b and first['view_state']==body['view_state']
                assert (await req('GET','/exploration'))['snapshot']==first
                assert await req('PUT','/exploration',body)==first
                await req('PUT','/exploration',{**body,'view_state':{}},409)
                await req('PUT','/exploration',{**body,'operation_key':str(uuid4())},409)
                cont={'operation_key':str(uuid4()),'expected_snapshot_id':first['id'],'base_snapshot_id':first['id'],'expanded_links':[link],'view_state':{'zoom':2}}
                second=await req('PUT','/exploration',cont); assert second['base']==first['base'] and second['expanded_sources']==first['expanded_sources']
                err={**cont,'operation_key':str(uuid4()),'expected_snapshot_id':second['id']}
                await req('PUT','/exploration',{**err,'expanded_links':[{'seed_object_id':str(uuid4()),'candidate_object_id':pair['candidate']['id']}]},404)
                await req('PUT','/exploration',{**err,'expanded_links':[{'seed_object_id':f['objects']['seed'][0],'candidate_object_id':f['objects']['ip'][0]}]},422)
                await req('PUT','/exploration',{**err,'expanded_links':[{'seed_object_id':f['objects']['multi'][0],'candidate_object_id':f['objects']['late'][0]}]},422)
                await req('PUT','/exploration',{**err,'expanded_links':[{'seed_object_id':f['objects']['seed'][2],'candidate_object_id':f['objects']['other_alert_source'][0]}]},404)
                await req('PUT','/exploration',{**err,'base_snapshot_id':str(uuid4())},404)
                await req('PUT','/exploration',{**err,'expanded_links':[link,link]},422)
                await req('GET','/exploration',params={'unknown':1},expected=422)
                await req('GET','/exploration-base',params={'run_id':str(uuid4())},expected=404)
                await req('GET',other='/api/v1/socai2/cases/'+str(uuid4())+'/exploration',expected=404)
                stale={**body,'operation_key':str(uuid4()),'expected_snapshot_id':second['id'],'base_fingerprint':'0'*64}
                await req('PUT','/exploration',stale,409)
                undo=await req('PUT','/exploration',{**err,'operation_key':str(uuid4()),'expanded_links':[],'view_state':{}})
                assert undo['expanded_links']==[] and undo['expanded_sources']=={'alerts':[],'objects':[]}
                after=await protected(); save('sql-after-save',after); assert before==after
    
            else:
                previous=json.loads((args.output/'verify-http.json').read_text())
                undo=previous[-1]['body']
                link={'seed_object_id':previous[2]['body']['items'][0]['matches'][0]['seed']['id'],'candidate_object_id':previous[2]['body']['items'][0]['matches'][0]['candidate']['id']}
                before=json.loads((args.output/'sql-before.json').read_text())

            # Complete two program-only Runs to prove saved bases remain fixed.
            async with service.transaction(tenant,readonly=True) as store:
                case=await store.case(cid,lock=False); actor=Actor(user_id=case['created_by'],name='SYNTHETIC exploration fixture')
            alerts=[UUID(f['alerts'][n]) for n in ['seed','unknown_seed']]
            async def finish_run(graph):
                prep=await service.prepare_baseline(tenant,cid,PrepareBaseline(operation_key=uuid4(),expected_scope_revision=1),actor=actor)
                rid=prep.pending_run_id
                async def idle(_): pass
                async with service.transaction(tenant,readonly=True) as store:
                    lim=active_policy().case.limits(await store.now(),'synthetic.exploration-state.v1')
                await service.start(tenant,cid,rid,Start(operation_key=uuid4(),expected_scope_revision=1),actor=actor,executor=idle,executor_version=FULL_EXECUTOR_VERSION,limits=lim)
                scope=Scope(kind='whole_case',alert_ids=alerts,object_keys=[],window_start=None,window_end=None,limitations=[])
                pub=Publication(operation_key=uuid4(),terminal_state='completed',stop_reason='synthetic_exploration_fixture',title='SYNTHETIC exploration baseline',conclusion='SYNTHETIC program fixture, not model output',conclusion_state='uncertain',conclusion_origin='system',validation_state='system_only',closing_note='zero model calls',findings=[],recommendations=[],questions=[],change_kind='initial',change_summary=None,delivery_state='partial',case_impact={'summary':None,'supported_changes':[],'cannot_generalize':['Synthetic only'],'affected_scope':scope,'next_steps':[]},members=[{'alert_id':aid,'read_state':'read','assessment_state':'unresolved','conclusion_covered':True,'assessment':None,'limitations':'Synthetic only','evidence_refs':[reference('alert_material',UUID(f['materials'][n]),'observation')]} for aid,n in zip(alerts,['seed','unknown_seed'],strict=True)])
                if graph:
                    async with service.transaction(tenant) as store:
                        gid=uuid4()
                        await store.db.execute(insert(m.Artifacts).values(id=gid,tenant_id=tenant,case_id=cid,run_id=rid,kind='alert_graph',schema_version='synthetic.graph.v1',content_json=graph,mime_type='application/json',captured_at=await store.now(),material_state='complete',source_refs=[],retention={}))
                    pub=pub.model_copy(update={'graph_artifact_id':gid})
                published=await service.publish(tenant,cid,rid,pub)
                save('synthetic-run-'+str(rid),{'run_id':rid,'publication':pub.model_dump(mode='json'),'result':published})
                return str(rid)
            rid1=await finish_run({'nodes':[{'id':'synthetic-old','label':'SYNTHETIC saved base'}],'edges':[]})
            assert (await req('GET','/exploration'))['snapshot']==undo
            fresh=await req('GET','/exploration-base'); assert fresh['run_id']==rid1 and fresh['delivery_state']=='partial'
            reset=await req('PUT','/exploration',{'operation_key':str(uuid4()),'expected_snapshot_id':undo['id'],'base_run_id':rid1,'base_fingerprint':fresh['fingerprint'],'expanded_links':[link],'view_state':{'selected':['synthetic-old']}})
            rid2=await finish_run(None)
            latest=await req('GET','/exploration-base'); assert latest['run_id']==rid2 and latest['graph_state']=='unavailable' and latest['graph'] is None
            assert (await req('GET','/exploration-base',params={'run_id':rid1}))==fresh
            pinned=await req('PUT','/exploration',{'operation_key':str(uuid4()),'expected_snapshot_id':reset['id'],'base_snapshot_id':reset['id'],'expanded_links':[link],'view_state':{'zoom':0.5}})
            assert pinned['base']==reset['base'] and pinned['base']['run_id']==rid1
            assert (await req('GET','/exploration'))['snapshot']==pinned
            save('summary',{'passed':True,'http_requests':len(receipts)+(len(previous) if args.continue_history else 0),'protected_tables_equal':list(before),'models':0,'production_writes':0,'latest_snapshot_id':pinned['id'],'case_id':str(cid),'run_with_graph':rid1,'new_run_missing_graph':rid2})
            print(json.dumps({'passed':True,'http_requests':len(receipts)+(len(previous) if args.continue_history else 0),'case_id':str(cid)}))
    finally:
        await engine.dispose()

asyncio.run(main())
