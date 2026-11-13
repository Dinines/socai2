"""Create isolated synthetic subjects or compare HTTP receipts with their SQL rows."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import UUID, uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['seed', 'readback'])
    parser.add_argument('--environment', type=Path)
    parser.add_argument('--database', required=True)
    parser.add_argument('--tenant', type=UUID)
    parser.add_argument('--actor', type=UUID)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--responses', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.environment:
        os.environ.update(json.loads(args.environment.read_text()))
    root = Path(__file__).resolve().parents[2]
    if (root/'services/api').is_dir():
        sys.path.insert(0, str(root/'services/api'))
    from sqlalchemy import insert, select, text, update
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.models import socai2 as m
    from app.db.database import _normalize_async_pg_url
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_service import BaselineService
    from app.socai2.case_contracts import project
    from app.socai2.page_contracts import AlertFacts, IncidentFacts
    url = os.environ['SOCAI2_CASE_DATABASE_URL']
    assert make_url(url).database == args.database

    async def run():
        normalized, connect_args = _normalize_async_pg_url(url)
        engine = create_async_engine(normalized, connect_args=connect_args)
        service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))
        try:
            async with engine.connect() as conn:
                assert (await conn.execute(text('SELECT current_database()'))).scalar_one() == args.database
            if args.action == 'seed':
                assert args.tenant and args.actor and not args.fixture.exists()
                batch = str(uuid4())
                alerts, incidents, triage_ids = [], [], []
                async with service.transaction(args.tenant) as store:
                    now = await store.now()
                    for index in range(3):
                        aid, mid, tid, iid = uuid4(), uuid4(), uuid4(), uuid4()
                        alerts.append(str(aid)); incidents.append(str(iid)); triage_ids.append(str(tid))
                        await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=args.tenant,
                            title=f'SYNTHETIC subject management {batch} alert {index}',
                            source_namespace='synthetic-subject-management', source_identity_key=str(aid),
                            source_alert_id=str(aid), severity='medium', event_time=now, event_time_source='source',
                            tags=['synthetic', batch]))
                        await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=args.tenant,
                            alert_id=aid, revision=1, raw_json={'synthetic': True, 'batch': batch},
                            ocsf_json={'message':'Synthetic management verification; no real incident'},
                            detection={}, source_scope={}, material_state='complete', retention={}))
                        await store.db.execute(insert(m.AlertAssessments).values(id=tid, tenant_id=args.tenant,
                            alert_id=aid, kind='triage', input_material_id=mid, verdict='needs_review',
                            rationale='SYNTHETIC fixture; not model evidence', producer='synthetic.fixture',
                            actor=Actor(user_id=args.actor, name="synthetic.fixture@example.invalid").snapshot(), assessed_at=now, operation_key=str(tid)))
                        await store.db.execute(update(m.Alerts).where(m.Alerts.id==aid).values(latest_material_id=mid, latest_triage_id=tid))
                        await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=args.tenant,
                            source_namespace='synthetic-subject-management', source_incident_id=str(iid),
                            title=f'SYNTHETIC subject management {batch} incident {index}', tags=['synthetic', batch]))
                        await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=args.tenant,
                            incident_id=iid, alert_id=aid, membership_source='manual', source_operation_id=uuid4(),
                            correlation_basis={'synthetic': True}, basis_version='synthetic.v1'))
                data={'batch':batch,'tenant_id':str(args.tenant),'actor_id':str(args.actor),'database':args.database,
                      'alerts':alerts,'incidents':incidents,'triage_ids':triage_ids,'real_model_calls':0}
                args.fixture.parent.mkdir(parents=True, exist_ok=True)
                args.fixture.write_text(json.dumps(data,indent=2)+'\n')
                print(json.dumps({'seeded_alerts':3,'seeded_incidents':3,'fixture':str(args.fixture)}))
            else:
                fixture=json.loads(args.fixture.read_text());tenant=UUID(fixture['tenant_id'])
                expected={}
                for item in json.loads(args.responses.read_text()):
                    if item['method']=='GET' and item['status']==200 and isinstance(item['body'],dict):
                        body=item['body']
                        if body.get('kind') in ['alerts','incidents'] and 'facts' in body:
                            expected[(body['kind'],body['facts']['id'])]=body['facts']
                assert len(expected)==6
                async with service.transaction(tenant,readonly=True) as store:
                    for (kind,identity),facts in expected.items():
                        table,model=(m.Alerts.__table__,AlertFacts) if kind=='alerts' else (m.Incidents.__table__,IncidentFacts)
                        row=await store.one(select(table).where(*store.where(table,table.c.id==UUID(identity))))
                        assert project(model,row).model_dump(mode='json')==facts,(kind,identity)
                    for aid,tid in zip(fixture['alerts'],fixture['triage_ids'],strict=True):
                        row=await store.one(select(m.Alerts.__table__).where(m.Alerts.tenant_id==tenant,m.Alerts.id==UUID(aid)))
                        assert str(row['latest_triage_id'])==tid and row['severity']=='medium'
                        triage=await store.one(select(m.AlertAssessments.__table__).where(m.AlertAssessments.id==UUID(tid)))
                        assert triage['rationale']=='SYNTHETIC fixture; not model evidence'
                    runs=(await store.db.execute(select(m.Runs.id).where(m.Runs.tenant_id==tenant,
                        m.Runs.state.in_(['running','completed','unknown']),
                        (m.Runs.alert_id.in_([UUID(x) for x in fixture['alerts']])) |
                        (m.Runs.incident_id.in_([UUID(x) for x in fixture['incidents']]))))).all()
                    assert not runs
                result={'state':'passed','database':args.database,'subjects_compared':6,
                        'all_facts_fields_equal':True,'original_triage_and_severity_preserved':True,'real_model_calls':0}
                args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
        finally:
            await engine.dispose()
    asyncio.run(run())


if __name__=='__main__':main()
