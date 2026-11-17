"""Step 4 direct PG/Redis workflow; controlled replies through actual A and I executors."""
import argparse
import asyncio
import json
import os
import re
import sys
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'services/api'), str(ROOT / 'services/api/tests')]


def save(path, value):
    path.write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2) + '\n')


async def run(args, config):
    from app.models import socai2 as m
    from app.socai2.analysis_alert_executor import AlertTaskExecutor
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_incident_executor import IncidentTaskExecutor, IncidentTaskPolicy, executors
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.stage_reader import StageReadService
    from app.socai2.stage_results import StageResultService
    from jsonschema import Draft202012Validator
    from redis.asyncio import Redis
    from socai2_test_model_view import synthetic_measure
    from sqlalchemy import select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    cfg = json.loads((ROOT / config['database_profile']).read_text())
    assert cfg['processing_database'] == 'v12_upgrade_dev'
    url = URL.create('postgresql+psycopg', username=cfg['admin'], password=Path(cfg['password_file']).read_text().strip(),
        host=cfg['host'], port=cfg['port'], database=cfg['processing_database'])
    admin = create_async_engine(url, hide_parameters=True, connect_args={'sslmode':config['sslmode']})
    engine = create_async_engine(url, hide_parameters=True, connect_args={'sslmode':config['sslmode'], 'options':'-c role='+cfg['processor']})
    tenant = uuid4()
    result = {'tenant_id':tenant, 'checks':[], 'model':'controlled A/I responses', 'state':'running'}
    redis = Redis.from_url(Path(config['redis_url_file']).read_text().strip())
    dispatcher = None
    calls = []
    try:
        async with admin.begin() as db:
            await db.execute(text("""INSERT INTO public.tenants (id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES (:id,:name,:slug,'enterprise',true,'{}','{}',now(),now())"""),
                {'id':tenant,'name':'I auto direct '+str(tenant),'slug':'i-auto-'+str(tenant)})
        lifecycle = AnalysisTaskPolicy(**json.loads(Path(config['lifecycle_policy_file']).read_text()))
        service = AnalysisTaskService(async_sessionmaker(engine, expire_on_commit=False), lifecycle)
        stage = StageResultService(service.sessions)
        reader = StageReadService(service.sessions)
        repository = DispatchRepository(service, tenant)
        policy = DispatchPolicy(**{**config['dispatch'],'receipt_directory':str(Path(config['dispatch']['receipt_directory'])/str(tenant))})
        queues = AnalysisQueues(redis, policy.namespace, tenant)
        registered = executors({'investigation_policy_file': str(ROOT/config['investigation_policy']), 'incident':config['incident']}, service)
        assert set(registered) == {'alert_triage','incident_diagnosis'}

        async def rows(model):
            table = model.__table__
            async with service.transaction(tenant, readonly=True) as s:
                return [dict(x) for x in (await s.db.execute(select(table).where(table.c.tenant_id==tenant))).mappings()]

        from controlled import Gateway
        gateway=Gateway(service,tenant,calls)

        i_executor=IncidentTaskExecutor(stage,service,IncidentTaskPolicy(**config['incident']),gateway_factory=lambda: gateway)
        dispatcher=AnalysisDispatcher(repository,queues,policy,{'alert_triage':AlertTaskExecutor(stage,gateway_factory=lambda: gateway),'incident_diagnosis':i_executor})
        await dispatcher.start()

        async def ingress(name,incident=None,replay=None):
            path=out/(name+'.json')
            argv=[sys.executable,str(HERE/'ingress.py'),'--config',str(ROOT/config['database_profile']),
                '--policy',config['lifecycle_policy_file'],'--tenant',str(tenant),'--output',str(path)]
            if incident: argv+=['--incident',str(incident)]
            if replay: argv+=['--replay',str(replay)]
            proc=await asyncio.create_subprocess_exec(*argv,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
            stdout,_=await proc.communicate();(out/(name+'.log')).write_bytes(stdout)
            assert proc.returncode==0, name+' ingress failed'
            return json.loads(path.read_text())

        async def drain():
            async with asyncio.timeout(config['check_timeout_seconds']):
                while True:
                    await dispatcher.tick()
                    tasks=await rows(m.AnalysisTasks)
                    if tasks and all(t['state'] in {'completed','failed','skipped','merged'} for t in tasks): return tasks
                    await asyncio.sleep(config['check_interval_seconds'])

        def check(name):
            result['checks'].append(name);print(name,flush=True)

        iid=uuid4()
        a1=await ingress('A1',iid);await ingress('A2',iid)
        await ingress('A1-replay',replay=out/'A1.json')
        tasks=await rows(m.AnalysisTasks)
        assert len(tasks)==3 and sum(t['kind']=='incident_diagnosis' for t in tasks)==1
        assert not await rows(m.Runs)
        check('native A1/A2 and one I initial task; replay does not create tasks or Runs')
        tasks=await drain()
        assert all(t['state']=='completed' for t in tasks),[(t['kind'],t['reason_code']) for t in tasks]
        assert len(calls)==3
        page=await reader.read_page(tenant,'incident_diagnosis',iid)
        assert page.current.valid_for_current_input and page.current.analysis_coverage.state=='complete'
        assert page.current.input_selection.selected_count==2 and page.current.analysis_coverage.unresolved_count==2
        assert await stage.freshness(tenant,page.current.run.id)
        save(out/'initial-page.json',page.model_dump(mode='json'))
        check('real A/I executors save bound frozen input, diagnosis and true unresolved coverage; I does not self-invalidate')
        before=len(calls)
        receipt=await service.submit(tenant,kind='incident_diagnosis',subject_id=iid,intent='check',source='user',operation_key=uuid4())
        await drain();detail=await service.read_task(tenant,'incident',iid,receipt['task_id'])
        assert detail['status']=='skipped' and detail['reason_code']=='no_changes' and not detail['attempts'] and len(calls)==before
        check('manual unchanged check skips without Run/model')
        # Move only the scan clock, not stored business activity.
        clock=datetime.now(UTC)+timedelta(hours=5)
        result_scan=await i_executor.check_updates(tenant,clock)
        assert result_scan=={'checked':1,'submitted':0}
        a3=await ingress('A3',iid);await drain()
        assert len(calls)==before+1
        scan=await i_executor.check_updates(tenant,clock+timedelta(hours=5))
        assert scan['submitted']==1
        await drain();page=await reader.read_page(tenant,'incident_diagnosis',iid)
        assert page.current.input_selection.selected_count==3 and page.current.analysis_coverage.state=='complete'
        check('new member/A becomes next periodic I input; scan checks latest content, no re-triage of old alerts')
        if args.boundaries:
            from boundaries import run as boundaries
            await boundaries(locals())
        result.update(state='passed',model_calls=len(calls),http_sample={'tenant_id':tenant,'incident_id':iid,
            'task_id':next(a['task_id'] for a in await rows(m.AnalysisAttempts) if a['run_id']==page.current.run.id),
            'run_id':page.current.run.id,'alert_id':a1['fused']['id']})
    except Exception:
        result.update(state='failed',error=traceback.format_exc());raise
    finally:
        save(out/'result.json',result);save(out/'model-io.json',calls)
        if dispatcher:
            for _,f in dispatcher.active.values(): f.cancel()
            if dispatcher.active: await asyncio.gather(*(f for _,f in dispatcher.active.values()),return_exceptions=True)
            dispatcher._collect();await dispatcher._flush_receipts()
        if 'service' in locals():
            data={}
            async with service.transaction(tenant,readonly=True) as s:
                for name in ('alerts','alert_materials','alert_assessments','incidents','incident_alerts','incident_diagnoses','alert_objects','analysis_tasks','analysis_attempts','analysis_subject_state','runs','run_steps','artifacts'):
                    data[name]=(await s.db.execute(text("SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM socai2."+name+' t WHERE tenant_id=:tenant'),{'tenant':tenant})).scalar_one()
            save(out/'database.json',data)
        await redis.aclose();await engine.dispose();await admin.dispose()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--batch',required=True);p.add_argument('--boundaries',action='store_true');args=p.parse_args()
    config=json.loads(args.config.read_text());os.environ.update(json.loads((ROOT/config['environment_file']).read_text()));os.environ.update(config['runtime_overrides'])
    os.environ['SOCAI2_INVESTIGATION_POLICY']=str(ROOT/config['investigation_policy']);os.environ['SOCAI2_ANALYSIS_TASKS_CONFIG_FILE']=config['lifecycle_policy_file'];os.environ.pop('SOCAI2_KNOWLEDGE_PROFILE',None)
    asyncio.run(run(args,config))
