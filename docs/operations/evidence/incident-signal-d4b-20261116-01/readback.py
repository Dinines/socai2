"""D4b final read-only source/C1/terminal-state verification; no execution."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import UUID

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'services/api')]
BASE=Path(__file__).parent


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=lambda v:v.model_dump(mode='json') if hasattr(v,'model_dump') else str(v))+'\n')


async def main(config,out,complete_batch,complete_only):
    from app.models import socai2 as m
    from app.socai2.baseline_service import BaselineService
    from app.socai2.baseline_store import digest
    from app.socai2.stage_delivery import validate_sources
    from sqlalchemy import select
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out.mkdir(exist_ok=False)
    cfg=json.loads(Path(config['database_profile']).read_text())
    assert cfg['host']=='127.0.0.1' and cfg['processing_database']=='v12_upgrade_dev'
    url=URL.create('postgresql+psycopg',username=cfg['admin'],password=Path(cfg['password_file']).read_text().strip(),host=cfg['host'],port=cfg['port'],database=cfg['processing_database'])
    engine=create_async_engine(url,hide_parameters=True,connect_args={'sslmode':config['sslmode'],'options':'-c role='+cfg['processor']})
    service=BaselineService(async_sessionmaker(engine,expire_on_commit=False))
    tables=(m.Alerts,m.AlertMaterials,m.AlertObjects,m.AlertAssessments,m.Incidents,m.IncidentAlerts,m.IncidentDiagnoses,
        m.AnalysisTasks,m.AnalysisAttempts,m.AnalysisSubjectState,m.Cases,m.CaseAlerts,m.CaseIncidents,m.Runs,m.RunMembers,m.RunSteps,m.Artifacts)
    async def snapshot(tenant):
        rows={}
        async with service.transaction(tenant,readonly=True) as store:
            for model in tables:
                t=model.__table__
                values=[dict(r) for r in (await store.db.execute(select(t).where(t.c.tenant_id==tenant).order_by(*t.primary_key.columns))).mappings()]
                rows[t.name]=json.loads(json.dumps(values,default=str))
        return rows,{k:{'count':len(v),'sha256':digest(v)} for k,v in rows.items()}
    result={'state':'running','checks':[],'new_model_calls':0,'new_business_requests':0}
    try:
        targets=[('complete',complete_batch)] + ([] if complete_only else [('partial','pg-partial-02'),('none','pg-none-01')])
        for scenario,batch in targets:
            target=out/scenario;target.mkdir()
            accepted=json.loads((BASE/batch/'result.json').read_text())
            tenant,cid,rid=(UUID(accepted[k]) for k in ('tenant_id','case_id','case_run_id'))
            rows,before=await snapshot(tenant)
            read=await service.read_context(tenant,cid,rid)
            body=read.model_dump(mode='json')
            assert body==json.loads((BASE/batch/'frozen-context.json').read_text())
            save(target/'frozen-context-after-new-alert.json',body)
            material=body['incidents'][accepted['incident_id']]['analysis_material']
            ids={material[k]['id'] for k in ('input','response','receipt_source')}|{o['id'] for o in material['originals']}
            artifacts=[r for r in rows['artifacts'] if r['id'] in ids]
            assert len(artifacts)==len(ids)
            source={r['id']:r['content_json'] for r in artifacts}
            validate_sources(material['receipt'],source)
            for r in artifacts: assert digest(r['content_json'])==r['sha256']
            save(target/'source-artifacts-readback.json',artifacts)
            run=next(r for r in rows['runs'] if r['id']==str(rid))
            assert run['state']=='failed' and run['ended_at'] and run['stop_reason']=='component_capture_only'
            assert not any(r['state']=='running' for r in rows['runs'])
            assert not any(a['local_state']=='running' for a in rows['analysis_attempts'])
            save(target/'database-readback.json',rows)
            _,after=await snapshot(tenant)
            assert before==after
            save(target/'read-only-counts.json',{'before':before,'after':after})
            result['checks'].append({'scenario':scenario,'source_artifacts':len(artifacts),'tables':len(tables),
                'c1_after_new_alert_identical':True,'strict_sources_valid':True,'running_runs':0,'running_attempts':0,'read_only':True})
        result['state']='passed'
    finally:
        save(out/'result.json',result)
        await engine.dispose()
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);p.add_argument('--complete-batch',default='pg-complete-07');p.add_argument('--complete-only',action='store_true');a=p.parse_args()
    c=json.loads(Path(a.config).read_text());os.environ.update(json.loads(Path(c['environment_file']).read_text()));os.environ.update(c['runtime_overrides'])
    os.environ['SOCAI2_INVESTIGATION_POLICY']=c['investigation_policy_file']
    asyncio.run(main(c,Path(a.output),a.complete_batch,a.complete_only))
