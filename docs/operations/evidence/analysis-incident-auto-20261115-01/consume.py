"""Consume accepted local verification tasks using the real A/I handlers and controlled replies."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import UUID
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'services/api'),str(ROOT/'services/api/tests')]

async def run(config,tenant,out):
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_incident_executor import executors
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from controlled import Gateway
    from redis.asyncio import Redis
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine
    from sqlalchemy import text
    cfg=json.loads((ROOT/config['database_profile']).read_text())
    assert cfg['processing_database']=='v12_upgrade_dev'
    engine=create_async_engine(URL.create('postgresql+psycopg',username=cfg['admin'],password=Path(cfg['password_file']).read_text().strip(),
        host=cfg['host'],port=cfg['port'],database=cfg['processing_database']),hide_parameters=True,
        connect_args={'sslmode':config['sslmode'],'options':'-c role='+cfg['processor']})
    redis=Redis.from_url(Path(config['redis_url_file']).read_text().strip())
    service=AnalysisTaskService(async_sessionmaker(engine,expire_on_commit=False),AnalysisTaskPolicy(**json.loads(Path(config['lifecycle_policy_file']).read_text())))
    handlers=executors({'investigation_policy_file':str(ROOT/config['investigation_policy']),'incident':config['incident']},service)
    gateway=Gateway(service,tenant)
    for handler in handlers.values(): handler.gateway_factory=lambda:gateway
    policy=DispatchPolicy(**{**config['dispatch'],'receipt_directory':str(Path(config['dispatch']['receipt_directory'])/str(tenant))})
    dispatcher=AnalysisDispatcher(DispatchRepository(service,tenant),AnalysisQueues(redis,policy.namespace,tenant),policy,handlers)
    try:
        await dispatcher.start()
        async with asyncio.timeout(config['check_timeout_seconds']):
            while True:
                await dispatcher.tick()
                async with service.transaction(tenant,readonly=True) as store:
                    waiting=(await store.db.execute(text("SELECT count(*) FROM socai2.analysis_tasks WHERE tenant_id=:tenant AND state IN ('accepted','waiting','running')"),{'tenant':tenant})).scalar_one()
                if not waiting: break
                await asyncio.sleep(config['check_interval_seconds'])
        out.write_text(json.dumps({'tenant_id':str(tenant),'state':'drained','model':'controlled replies','calls':gateway.calls},default=str,ensure_ascii=False,indent=2)+'\n')
    finally:
        for _,f in dispatcher.active.values(): f.cancel()
        if dispatcher.active: await asyncio.gather(*(f for _,f in dispatcher.active.values()),return_exceptions=True)
        dispatcher._collect();await dispatcher._flush_receipts();await redis.aclose();await engine.dispose()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--tenant',type=UUID,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    cfg=json.loads(args.config.read_text());os.environ.update(json.loads((ROOT/cfg['environment_file']).read_text()));os.environ.update(cfg['runtime_overrides'])
    os.environ['SOCAI2_INVESTIGATION_POLICY']=str(ROOT/cfg['investigation_policy']);os.environ['SOCAI2_ANALYSIS_TASKS_CONFIG_FILE']=cfg['lifecycle_policy_file'];os.environ.pop('SOCAI2_KNOWLEDGE_PROFILE',None)
    asyncio.run(run(cfg,args.tenant,args.output))
