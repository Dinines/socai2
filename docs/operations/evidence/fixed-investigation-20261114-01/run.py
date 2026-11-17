"""One requested three-Case demonstration using existing core, transport and exports."""
import argparse
import asyncio
import copy
import importlib.util
import json
import sys
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tools.testdata.case_scope_recovery.real_model import Gateway, initialize
from tools.testdata.incident_integration.fixtures import identity
from tools.testdata.incident_integration.run import connect, read, save, sha


def prepare(config, folder):
    from app.socai2.baseline_contracts import Scope
    from app.socai2.human_task_contracts import TaskCreate
    from app.socai2.runtime_policy import active_policy

    original = read(ROOT / config['source_plan'])['members']
    groups = []
    for group in config['fixture_groups']:
        members = []
        for source in original:
            action = source['material']['ocsf_json']['activity']['action']
            if action not in group['actions']:
                continue
            member = copy.deepcopy(source)
            member.update(source_alert_id=source['alert_id'],
                alert_id=identity(config['batch'], group['key']+':'+source['alert_id']),
                material_id=identity(config['batch'], group['key']+':'+source['material_id']))
            members.append(member)
        assert len(members) == len(group['actions'])
        times = [datetime.fromisoformat(m['alert']['event_time']) for m in members]
        padding = timedelta(seconds=config['window_padding_seconds'])
        scope = Scope(kind='whole_case', alert_ids=[m['alert_id'] for m in members],object_keys=[],
            window_start=min(times)-padding,window_end=max(times)+padding,limitations=[]).model_dump(mode='json')
        groups.append({**group,'incident_id':identity(config['batch'],group['key']), 'members':members,'scope':scope})
    scenarios = []
    for item in config['scenarios']:
        group = next(g for g in groups if g['key'] == item['group'])
        human = None
        if item.get('human_text'):
            selected = [m for m in group['members'] if m['material']['ocsf_json']['activity']['action']==item['human_action']]
            human = TaskCreate(operation_key=identity(config['batch'],item['key']+':H'),expected_scope_revision=1,
                title='核实资产盘点命令的授权范围',description='本批演练人工陈述，不代表实际业务人员授权。',
                state='completed',result_text=item['human_text'],result_scope={**group['scope'],'kind':'selected_alerts',
                'alert_ids':[m['alert_id'] for m in selected]},source_refs=[{'type':'alert_material','id':m['material_id']} for m in selected]).model_dump(mode='json')
        scenarios.append({**item,'human_request':human,'operations':{name:identity(config['batch'],item['key']+':'+name) for name in ('create','start')}})
    files = [HERE/'config.json',Path(__file__),ROOT/config['source_plan'],ROOT/config['policy'],ROOT/config['knowledge_profile'],
        ROOT/config['source_driver'],ROOT/config['transport_config'],ROOT/config['local_services'],
        ROOT/'tools/testdata/case_scope_recovery/real_model.py',ROOT/'tools/testdata/incident_integration/run.py',
        ROOT/'tools/testdata/incident_integration/gateway.py',ROOT/'tools/testdata/case_io_eval/model_worker.py',ROOT/'tools/testdata/case_io_eval/model_eval.py']
    files += sorted(p for p in (ROOT/'services/api/app/socai2').glob('*') if p.suffix in {'.py','.json'})
    files += sorted(p for p in (ROOT/'services/api/investigation_http').rglob('*') if p.suffix in {'.py','.json'})
    files += [ROOT/'services/api/app/models/socai2.py',ROOT/'docs/operations/capture_processing_case.py',
        ROOT/'docs/operations/update_processing_audit.py',ROOT/'docs/operations/processing_audit_import.py']
    folder.mkdir(exist_ok=False)
    policy=active_policy()
    save(folder/'plan.json',{'config':config,'groups':groups,'scenarios':scenarios,
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},'new_A':4,'new_I':2,'new_Case':3,
        'limits':{k:getattr(policy,k).limits(datetime.now(UTC),policy.identity).model_dump(mode='json') for k in ('alert_basic','incident_diagnosis','case')}})
    with tarfile.open(HERE/'replay-source.tar.gz','w:gz') as archive:
        for p in files:
            archive.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
    print('Prepared 4 A + 2 I + 3 Case, with source archive; no model or DB writes.',flush=True)


def plan_for(config, folder):
    plan=read(folder/'plan.json')
    assert config==plan['config']
    assert all(sha(ROOT/p)==value for p,value in plan['source_sha256'].items()),'prepared_source_changed'
    return plan


async def preflight(config, folder):
    from app.db import database
    from sqlalchemy import text
    from tools.testdata.case_io_eval.model_eval import check_route, remote

    plan_for(config,folder)
    engine=await connect(config)
    try:
        async with engine.connect() as db:
            db_name=(await db.execute(text('SELECT current_database()'))).scalar_one()
        async with database.engine.connect() as db:
            shared_db=(await db.execute(text('SELECT current_database()'))).scalar_one()
        assert db_name==shared_db==config['expected_database']
        route=await asyncio.to_thread(remote,config,{'phase':'preflight','timeout_seconds':config['preflight_timeout_seconds']})
        save(folder/'model-route.json',route)
        check_route(config,route)
        save(folder/'preflight.json',{'state':'ready','processing_database':db_name,'source_database':shared_db,'model_route':route,'generation_calls':0})
        print('Preflight ready:',db_name,route['state'],flush=True)
    finally:
        await engine.dispose()
        await database.engine.dispose()


async def seed(config,folder):
    from app.models import socai2 as m
    from app.socai2.stage_results import StageResultService
    from sqlalchemy import insert,select,update
    from sqlalchemy.ext.asyncio import async_sessionmaker

    plan=plan_for(config,folder)
    assert read(folder/'preflight.json')['state']=='ready'
    save(folder/'seed-intent.json',{'database':config['expected_database'],'alerts':4,'incidents':2})
    engine=await connect(config)
    service=StageResultService(async_sessionmaker(engine,expire_on_commit=False))
    tenant=UUID(config['tenant_id'])
    try:
        async with service.transaction(tenant) as store:
            for group in plan['groups']:
                iid=UUID(group['incident_id'])
                assert not await store.one(select(m.Incidents.id).where(m.Incidents.id==iid))
                await store.db.execute(insert(m.Incidents).values(id=iid,tenant_id=tenant,title=group['title'],source_namespace=config['batch'],source_incident_id=str(iid)))
                for member in group['members']:
                    aid,mid=UUID(member['alert_id']),UUID(member['material_id'])
                    alert=dict(member['alert']);alert['event_time']=datetime.fromisoformat(alert['event_time'])
                    await store.db.execute(insert(m.Alerts).values(id=aid,tenant_id=tenant,source_namespace=config['batch'],source_identity_key=str(aid),**alert))
                    await store.db.execute(insert(m.AlertMaterials).values(id=mid,tenant_id=tenant,alert_id=aid,revision=1,**member['material']))
                    await store.db.execute(update(m.Alerts).where(m.Alerts.id==aid).values(latest_material_id=mid))
                    for i,obj in enumerate(member['objects']):
                        await store.db.execute(insert(m.AlertObjects).values(id=UUID(identity(config['batch'],f'{aid}:object:{i}')),tenant_id=tenant,alert_id=aid,material_id=mid,**obj))
                    await store.db.execute(insert(m.IncidentAlerts).values(id=UUID(identity(config['batch'],f'{iid}:{aid}')),tenant_id=tenant,
                        incident_id=iid,alert_id=aid,membership_source='manual',basis_version='explicit_synthetic_fixture',
                        correlation_basis={'reason':'fixed_demonstration_membership_not_inferred'},source_operation_id=iid))
        save(folder/'seed-receipt.json',{'state':'committed','alerts':4,'incidents':2,'original_materials_unchanged':True})
        print('Seed committed: 4 alerts, 2 incidents.',flush=True)
    finally:
        await engine.dispose()


def gateway(config,folder,key):
    return Gateway({**config,'preflight':read(folder/'model-route.json'),'transport':{**config['transport'],
        'remote_evidence_dir':config['remote_evidence_dir']+'/'+key}},folder/key/'calls')


async def stages(config,folder):
    from app.socai2.stage_results import StageResultService
    from sqlalchemy.ext.asyncio import async_sessionmaker
    plan=plan_for(config,folder)
    assert read(folder/'seed-receipt.json')['state']=='committed'
    save(folder/'stages-intent.json',{'A':4,'I':2,'attempts_per_run':1})
    engine=await connect(config)
    service=StageResultService(async_sessionmaker(engine,expire_on_commit=False))
    tenant,actor=UUID(config['tenant_id']),UUID(config['actor_id'])
    try:
        for group in plan['groups']:
            jobs=[('A'+str(i),m['alert_id'],'alert') for i,m in enumerate(group['members'],1)]+[('I',group['incident_id'],'incident')]
            results=[]
            for label,subject,kind in jobs:
                key=group['key']+'/'+label
                g=gateway(config,folder,key)
                save(folder/key/'execute-intent.json',{'kind':kind,'subject':subject,'operation_key':identity(config['batch'],key)})
                fn=service.execute_alert if kind=='alert' else service.execute_incident
                result=await fn(tenant,UUID(subject),UUID(identity(config['batch'],key)),gateway=g,requested_by=actor)
                save(folder/key/'execution.json',{**result,'model_calls':g.calls,'unknown':g.unknown})
                results.append(result)
                print(key,result.get('state'),'calls',g.calls,flush=True)
                assert not g.unknown,'unknown_execution_not_redispatched'
            save(folder/group['key']/'stages.json',results)
    finally:
        await engine.dispose()


async def case(config,folder,key):
    from app.socai2.baseline_contracts import Actor,Start
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.human_task_contracts import TaskCreate
    from app.socai2.human_task_service import HumanTaskService
    from app.socai2.runtime_policy import active_policy
    from fastapi.encoders import jsonable_encoder
    from sqlalchemy.ext.asyncio import async_sessionmaker

    plan=plan_for(config,folder)
    scenario=next(s for s in plan['scenarios'] if s['key']==key)
    group=next(g for g in plan['groups'] if g['key']==scenario['group'])
    assert all(r.get('state') not in {'unknown','running'} for r in read(folder/group['key']/'stages.json'))
    out=folder/key
    save(out/'execute-intent.json',{'new_Case_runs':1,'A_I_reused_from':group['key'],'attempts':1})
    engine=await connect(config)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    service,human=CaseService(sessions),HumanTaskService(sessions)
    tenant=UUID(config['tenant_id']); actor=Actor(user_id=UUID(config['actor_id']),name=config['actor_name'])
    g=gateway(config,folder,key)
    cid=rid=None; phase='create'; outcome={}
    try:
        created=await service.create_case(tenant,CaseCreate(operation_key=scenario['operations']['create'],title=scenario['title'],
            description=scenario['purpose'],incident_ids=[group['incident_id']]),actor=actor)
        save(out/'created.json',created.model_dump(mode='json'))
        cid,rid=created.case_id,created.pending_run_id
        if scenario['human_request']:
            phase='save_H'
            reply=await human.write(tenant,cid,TaskCreate.model_validate(scenario['human_request']),actor=actor)
            save(out/'human.json',reply.model_dump(mode='json'))
        request=Start(operation_key=scenario['operations']['start'],expected_scope_revision=created.scope_revision,
            window_start=group['scope']['window_start'],window_end=group['scope']['window_end'])
        save(out/'start-request.json',{'case_id':cid,'run_id':rid,'body':request.model_dump(mode='json')})
        async with service.transaction(tenant,readonly=True) as store:
            now=await store.now()
        limits=active_policy().case.limits(now,active_policy().identity)
        save(out/'limits.json',limits.model_dump(mode='json'))
        phase='C1_C6'
        await service.start_full(tenant,cid,rid,request,actor=actor,limits=limits,gateway=g)
        actual=jsonable_encoder(await service.read_run(tenant,cid,rid))
        save(out/'run-readback.json',actual)
        outcome={'state':actual['run']['state'],'result_ids':actual['result_ids']}
    except Exception as exc:
        outcome={'state':'execution_exception','phase':phase,'error_type':type(exc).__name__,'code':getattr(exc,'code',None)}
    finally:
        save(out/'execution.json',{**outcome,'case_id':cid,'run_id':rid,'model_calls':g.calls,'unknown':g.unknown})
        await engine.dispose()
    print(key,outcome,'calls',g.calls,flush=True)


async def export(config,folder,key):
    from app.api.v1.endpoints import socai2_cases as case_api,socai2_tasks as task_api,socai2_analysis as stage_api
    from app.socai2.case_service import CaseService
    from app.socai2.human_task_service import HumanTaskService
    from app.socai2.stage_reader import StageReadService
    from fastapi import FastAPI
    from httpx import ASGITransport,AsyncClient
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker
    sys.path.insert(0,str(ROOT/'docs/operations'))
    from capture_processing_case import TABLES,check_credentials,scoped_table_query
    import update_processing_audit as site

    plan=plan_for(config,folder);scenario=next(s for s in plan['scenarios'] if s['key']==key)
    group=next(g for g in plan['groups'] if g['key']==scenario['group'])
    execution=read(folder/key/'execution.json');cid,rid=execution['case_id'],execution['run_id']
    assert cid and rid,'no_case_run_to_export'
    stage_ids=[str(s['run_id']) for s in read(folder/group['key']/'stages.json')]
    engine=await connect(config);out=folder/key/'export'
    data={}
    try:
        async with engine.begin() as db:
            await db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"),{'tenant':config['tenant_id']})
            scope='WITH scope AS (SELECT CAST(:tenant AS uuid) tenant,CAST(:aids AS uuid[]) aids,CAST(:incident AS uuid[]) incident,CAST(:cid AS uuid) cid,CAST(:stages AS uuid[]) stages) '
            params={'tenant':config['tenant_id'],'aids':[m['alert_id'] for m in group['members']],'incident':[group['incident_id']],'cid':cid,'stages':stage_ids}
            for table in TABLES:
                data[table]=(await db.execute(text(scope+scoped_table_query(table)),params)).scalar_one()
        check_credentials(json.dumps(data,default=str).encode())
        save(out/'database.json',data)
        sessions=async_sessionmaker(engine,expire_on_commit=False)
        app=FastAPI()
        for module,service in ((case_api,CaseService(sessions)),(task_api,HumanTaskService(sessions)),(stage_api,StageReadService(sessions))):
            app.include_router(module.router)
            app.dependency_overrides[module.get_service]=(lambda value:lambda:value)(service)
            user=module.ReadUser if hasattr(module,'ReadUser') else module.User
            app.dependency_overrides[user.__metadata__[0].dependency]=lambda:SimpleNamespace(tenant_id=UUID(config['tenant_id']))
        paths={'case':f'/socai2/cases/{cid}','run':f'/socai2/cases/{cid}/runs/{rid}'}
        for result in data['results']:
            if result['source_run_id']==rid:paths['result-'+result['id']]=f"/socai2/cases/{cid}/results/{result['id']}"
        for revision in data['task_revisions']:
            paths['H-'+revision['id']]=f"/socai2/cases/{cid}/tasks/{revision['task_id']}/revisions/{revision['id']}"
        for member in group['members']:
            paths['A-'+member['alert_id']]=f"/socai2/alerts/{member['alert_id']}/analysis"
        paths['I']=f"/socai2/incidents/{group['incident_id']}/analysis"
        replies={}
        async with AsyncClient(transport=ASGITransport(app=app),base_url=config['http_base_url']) as client:
            for label,path in paths.items():
                response=await client.get(path)
                replies[label]={'path':path,'status':response.status_code,'body':response.json()}
        save(out/'http-readback.json',replies)
        save(out/'manifest.json',{'schema_version':'socai2.page-export.v1','batch_id':config['batch']+'-'+key,'case_id':cid,
            'tenant_id':config['tenant_id'],'exported_at':datetime.now(UTC),'source_environment':'isolated_local_pg_real_model_new_AI',
            'database':config['expected_database'],'sources':[{'file':n,'sha256':sha(out/n)} for n in ('database.json','http-readback.json')],
            'table_counts':{k:len(v) for k,v in data.items()},'limitations':config['limitations']})
        imported,total=site.update([out],ROOT/'deliverables/investigation-validation-20261106/processing-audit')
        save(folder/key/'processing-audit-update.json',{'imported':imported,'records':total})
        assert all(r['status']==200 for r in replies.values()),'read_error_saved'
        print(key,'exported',len(replies),'GETs; local 4177 records',total,flush=True)
    finally:
        await engine.dispose()


def forward_driver(config):
    spec=importlib.util.spec_from_file_location('prior_forward',ROOT/config['source_driver'])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


async def main_async(config,folder,phase,key):
    if phase=='preflight':await preflight(config,folder)
    elif phase=='seed':await seed(config,folder)
    elif phase=='stages':await stages(config,folder)
    elif phase=='case':await case(config,folder,key)
    elif phase=='export':await export(config,folder,key)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('prepare','preflight','seed','stages','case','export'))
    parser.add_argument('--scenario',choices=('C01','C02','C03'))
    args=parser.parse_args()
    config,folder=initialize(HERE/'config.json')
    if args.phase=='prepare':prepare(config,folder)
    elif args.phase in {'stages','case'}:
        assert args.phase!='case' or args.scenario
        # The established forward is owned only for this phase, then closed.
        transport_out=folder/('transport-'+(args.scenario or args.phase))
        transport_out.mkdir(exist_ok=False)
        with forward_driver(config).knowledge_forward(config,transport_out):
            asyncio.run(main_async(config,folder,args.phase,args.scenario))
    else:asyncio.run(main_async(config,folder,args.phase,args.scenario))
