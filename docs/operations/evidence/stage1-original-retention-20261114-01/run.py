"""Original storage/read acceptance. New isolated fixture; no model dispatch."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4, uuid5

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUTPUT = HERE


def read(path):
    return json.loads(path.read_text())


def save(name, value):
    with (OUTPUT / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write('\n')


def plain(value):
    return json.loads(json.dumps(value, default=str))


def snapshot_helper():
    path = HERE.parent / 'stage1-c3-completion-20261114-01/run.py'
    spec = importlib.util.spec_from_file_location('original_retention_snapshot', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.snapshot


async def run_fixture(service, stages, cfg):
    from app.models import socai2 as m
    from app.socai2.alert_basic_executor import AlertBasicExecutor
    from app.socai2.baseline_context import reference
    from app.socai2.baseline_contracts import Actor, Start
    from app.socai2.baseline_delivery import BaselineDelivery
    from app.socai2.baseline_enrichment import S
    from app.socai2.baseline_evidence import BaselineEvidence
    from app.socai2.baseline_reasoning import ModelSteps
    from app.socai2.baseline_store import A, R
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.runtime_policy import active_policy
    from app.socai2.stage_result_contracts import ALERT_EXECUTOR_VERSION, INCIDENT_EXECUTOR_VERSION
    from sqlalchemy import insert, update

    tenant, actor_id = UUID(cfg['tenant_id']), UUID(cfg['actor_id'])
    aid, iid, mid = [uuid5(tenant, cfg['batch'] + ':' + key) for key in ('alert', 'incident', 'material')]
    body = cfg['fixture_text_pattern'] * cfg['fixture_text_characters']
    actor = Actor(user_id=actor_id, name='original-retention-validation')
    host = cfg['batch']
    save('write-intent.json', {'alert_id': aid, 'incident_id': iid, 'material_id': mid,
         'fixture_bytes': len(body.encode()), 'real_model_calls': 0, 'model_substitute_calls': 0})
    async with service.transaction(tenant) as store:
        now = await store.now()
        await store.db.execute(insert(A).values(id=aid, tenant_id=tenant, source_namespace=cfg['batch'],
            source_identity_key=str(aid), title='原件存取测试，无模型分析', event_time=now, event_time_source='source'))
        await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid,
            revision=1, raw_json={'storage_fixture': True, 'text': body}, detection={}, source_scope={},
            retention={}, material_state='complete'))
        await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant, alert_id=aid,
            material_id=mid, object_type='host', object_role='entity', object_key='host:' + host,
            namespace=cfg['batch'], raw_value=host, normalized_value=host,
            source_path='$.fixture.host', attributes={}))
        await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=tenant, title='原件存取验证事件',
            source_namespace=cfg['batch'], source_incident_id=str(iid)))
        await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant, incident_id=iid,
            alert_id=aid, membership_source='manual', correlation_basis={'storage_fixture': True},
            basis_version=cfg['batch'], source_operation_id=uuid4()))
    await seed_asset(cfg, tenant, host, body, now)
    claims = {}
    for kind, subject, producer in [('alert_basic', aid, ALERT_EXECUTOR_VERSION),
                                   ('incident_diagnosis', iid, INCIDENT_EXECUTOR_VERSION)]:
        claims[kind] = await stages.begin(tenant, kind, subject, uuid4(), producer=producer, limits=None,
            requested_by=actor_id)
    executor = AlertBasicExecutor(stages)
    arid = claims['alert_basic']['run_id']
    async with stages.transaction(tenant) as store:
        arun, source = await executor.locked(store, arid)
        astep = await executor.step(store, arun, 'stage', 'original_storage_validation_only')
    _, query = await executor.background(tenant, arid, astep, source, 'assets')
    assert query['rows'][0]['record']['tags'] == [body] and query['returned_rows'] == 1
    assert query['overflow_rows'] == [] and not query['truncated']
    async with stages.transaction(tenant) as store:
        await store.db.execute(update(S).where(S.c.id == astep).values(state='completed', ended_at=await store.now()))
    for claim in claims.values():
        await stages.stop(tenant, claim['run_id'], state='cancelled', code='storage_validation_only_no_analysis')

    created = await service.create_case(tenant, CaseCreate(operation_key=uuid4(), alert_ids=[aid],
        title='第六步原件存取验证，无调查结论'), actor=actor)
    cid, rid = created.case_id, created.pending_run_id
    async with service.transaction(tenant) as store:
        now = await store.now()
        limits = active_policy().case.limits(now, active_policy().identity)
        await store.claim(cid, rid, Start(operation_key=uuid4(), expected_scope_revision=created.scope_revision),
            actor=actor, executor_version='storage-validation.v1', limits=limits)
    # Actual existing SQL source read, using the separately seeded oversized asset.
    enriched = await service.enrich(tenant, cid, rid)
    assert any(row['source'] == 'assets' and row['returned_rows'] == 1 for row in enriched['sources'])
    async with service.transaction(tenant) as store:
        run = await store.run(cid, rid)
        step = uuid4()
        await store.db.execute(insert(S).values(id=step, tenant_id=tenant, run_id=rid,
            seq=await BaselineEvidence(service).seq(store, rid), kind='stage', stage_code='storage_validation',
            name='original_storage_validation_no_model', state='running', started_at=await store.now(),
            input_artifact_id=run['input_artifact_id']))
        refs = [reference('artifact', run['input_artifact_id'], 'execution_receipt')]
        payload = {'storage_fixture': True, 'not_model_output': True, 'text': body}
        original = await BaselineEvidence(service).artifact(store, run, payload, step=step, refs=refs)
        derived = await ModelSteps(service, 'storage-validation.v1').save(store, run, step,
            {'storage_fixture': True, 'text': body, 'original_artifact_id': str(original)}, 'source_snapshot',
            [reference('artifact', original, 'execution_receipt')])
        markdown = await BaselineDelivery(service).save_markdown(store, run, step,
            '原件存取夹具；未生成业务结论。\n' + body, original, derived)
        await store.db.execute(update(S).where(S.c.id == step).values(state='completed',
            ended_at=await store.now(), output_artifact_id=derived))
        await store.db.execute(update(R).where(R.c.id == rid).values(state='cancelled', ended_at=await store.now(),
            stop_reason='storage_validation_only_no_analysis', row_version=R.c.row_version + 1))
    save('fixture.json', {'case_id': cid, 'run_id': rid, 'alert_id': aid, 'incident_id': iid, 'material_id': mid,
        'stage_runs': claims, 'original_artifact_id': original, 'derived_artifact_id': derived,
        'text_artifact_id': markdown, 'text_bytes': len(body.encode()), 'text_sha256': hashlib.sha256(body.encode()).hexdigest(),
        'actual_sources': ['A.assets PostgreSQL', 'C2 PostgreSQL'], 'real_model_calls': 0, 'model_substitute_calls': 0})


async def seed_asset(cfg, tenant, host, body, now):
    """Fixture insertion with configured DB owner; processor remains read-only on assets."""
    from sqlalchemy import URL, text
    from sqlalchemy.ext.asyncio import create_async_engine
    db = read(ROOT / cfg['database_profile'])
    assert cfg['fixture_writer'] == 'configured_isolated_database_admin'
    engine = create_async_engine(URL.create('postgresql+psycopg', username=db['admin'],
        password=Path(db['password_file']).read_text().strip(), host=db['host'], port=db['port'],
        database=cfg['expected_database']), connect_args={'sslmode': cfg['sslmode']})
    try:
        async with engine.begin() as conn:
            assert tuple((await conn.execute(text('SELECT current_database(), current_user'))).one()) == (cfg['expected_database'], db['admin'])
            await conn.execute(text("INSERT INTO public.assets (id,tenant_id,name,asset_type,criticality,tags,first_seen,last_seen,metadata,created_at,updated_at) "
                "VALUES (:id,:tenant,:name,'host','medium',ARRAY[:body],:now,:now,'{}',:now,:now)"),
                {'id': uuid5(tenant, cfg['batch'] + ':asset'), 'tenant': tenant, 'name': host, 'body': body, 'now': now})
    finally:
        await engine.dispose()


async def snapshot_all(service, cfg, fixture):
    from app.models import socai2 as m
    from sqlalchemy import select
    tenant = UUID(cfg['tenant_id'])
    cid, rid, aid, iid = (UUID(fixture[k]) for k in ('case_id', 'run_id', 'alert_id', 'incident_id'))
    data = await snapshot_helper()(service, tenant, cid, rid)
    run_ids = [rid, *(UUID(v['run_id']) for v in fixture['stage_runs'].values())]
    filters = {'alerts': (m.Alerts, m.Alerts.id == aid), 'alert_materials': (m.AlertMaterials, m.AlertMaterials.alert_id == aid),
        'alert_objects': (m.AlertObjects, m.AlertObjects.alert_id == aid), 'incidents': (m.Incidents, m.Incidents.id == iid),
        'incident_alerts': (m.IncidentAlerts, m.IncidentAlerts.incident_id == iid),
        'incident_diagnoses': (m.IncidentDiagnoses, m.IncidentDiagnoses.incident_id == iid),
        'runs': (m.Runs, m.Runs.id.in_(run_ids)), 'run_steps': (m.RunSteps, m.RunSteps.run_id.in_(run_ids)),
        'artifacts': (m.Artifacts, m.Artifacts.run_id.in_(run_ids))}
    async with service.transaction(tenant, readonly=True) as store:
        for key, (model, condition) in filters.items():
            table = model.__table__
            rows = (await store.db.execute(select(table).where(*store.where(table, condition)))).mappings().all()
            data[key] = sorted(plain([dict(row) for row in rows]), key=lambda r: r['id'])
    return data


def application(service, pages_service, tenant):
    from fastapi import FastAPI
    from investigation_http.external_routes import cases, pages
    app = FastAPI()
    for mod, dep in [(cases, cases.ReadUser), (pages, pages.User)]:
        app.include_router(mod.router, prefix='/api/v1')
        app.dependency_overrides[dep.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=tenant)
    app.dependency_overrides[cases.get_service] = lambda: service
    app.dependency_overrides[pages.get_service] = lambda: pages_service
    return app


async def readback(service, pages_service, cfg):
    from app.socai2.baseline_store import encoded
    from httpx import ASGITransport, AsyncClient
    fixture = read(OUTPUT / 'fixture.json')
    data = await snapshot_all(service, cfg, fixture)
    tenant = UUID(cfg['tenant_id']); checks = []
    app = application(service, pages_service, tenant)
    run_by_id = {row['id']: row for row in data['runs']}
    async with AsyncClient(transport=ASGITransport(app=app), base_url=cfg['http_base_url']) as client:
        for art in data['artifacts']:
            run = run_by_id[art['run_id']]
            if run['kind'] == 'baseline':
                path = f"/api/v1/socai2/cases/{run['case_id']}/runs/{run['id']}/artifacts/{art['id']}"
            else:
                subject, key = ('alerts', 'alert_id') if run['kind'] == 'alert_basic' else ('incidents', 'incident_id')
                path = f"/api/v1/socai2/{subject}/{run[key]}/analysis/runs/{run['id']}/artifacts/{art['id']}"
            response = await client.get(path)
            assert response.status_code == 200, (path, response.status_code)
            value = response.json()
            assert value['availability'] == 'available'
            assert value['content_json'] == art['content_json'] and value['content_text'] == art['content_text']
            raw = encoded(value['content_json']) if value['content_json'] is not None else value['content_text'].encode()
            assert len(raw) == art['size_bytes'] and hashlib.sha256(raw).hexdigest() == art['sha256']
            checks.append({'path': path, 'status': 200, 'size_bytes': len(raw), 'sha256': art['sha256'], 'complete': True})
        path = f"/api/v1/socai2/alerts/{fixture['alert_id']}/materials/{fixture['material_id']}"
        response = await client.get(path)
        assert response.status_code == 200 and response.json()['content_json']['raw_json'] == data['alert_materials'][0]['raw_json']
        checks.append({'path': path, 'status': 200, 'material_complete': True})
    assert await snapshot_all(service, cfg, fixture) == data
    for run in data['runs']:
        art = next(a for a in data['artifacts'] if a['id'] == run['input_artifact_id'])
        policy = next(a for a in data['artifacts'] if a['run_id'] == run['id'] and a['schema_version'] == 'socai2.runtime-policy.v1')
        assert any(r['id'] == policy['id'] for r in art['source_refs'])
    assert not data['results'] and not any(s['kind'] == 'model' for s in data['run_steps'])
    save('database.json', data); save('api-readback.json', checks)
    summary = {'http_gets': len(checks), 'artifacts_checked': len(data['artifacts']),
        'oversized_artifacts': [{'id': a['id'], 'kind': a['kind'], 'size_bytes': a['size_bytes'], 'sha256': a['sha256']}
                               for a in data['artifacts'] if a['size_bytes'] > 1048576],
        'GET_readonly': True, 'configuration_snapshots_linked': 3, 'real_model_calls': 0,
        'model_substitute_calls': 0, 'business_result_generated': False, 'run_states': [r['state'] for r in data['runs']]}
    save('readback-checks.json', summary)
    save('manifest.json', {'schema_version': 'socai2.page-export.v1', 'batch_id': cfg['batch'],
        'tenant_id': cfg['tenant_id'], 'case_id': fixture['case_id'], 'exported_at': datetime.now(UTC).isoformat(),
        'database': cfg['expected_database'], 'source_environment': 'isolated_PG_storage_only_no_model',
        'input_kind': 'synthetic_storage_fixture_not_investigation_result', 'real_model_calls': 0,
        'sources': [{'file': name, 'sha256': hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest()}
                    for name in ['database.json', 'api-readback.json', 'fixture.json', 'readback-checks.json']]})
    print(json.dumps(summary, ensure_ascii=False), flush=True)


async def main(action, cfg):
    from app.socai2.case_service import CaseService
    from app.socai2.page_reader import PageReadService
    from app.socai2.stage_results import StageResultService
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from tools.testdata.incident_integration.run import connect
    engine = await connect(cfg); sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        service = CaseService(sessions)
        if action == 'run':
            await run_fixture(service, StageResultService(sessions), cfg)
        elif action == 'readback':
            await readback(service, PageReadService(sessions), cfg)
    finally:
        await engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['run', 'readback'])
    parser.add_argument('--attempt', default='attempt03')
    args = parser.parse_args(); action = args.action
    assert args.attempt == 'attempt03'
    OUTPUT = HERE / args.attempt
    OUTPUT.mkdir(exist_ok=True)
    config = read(HERE / 'config.json')
    config['batch'] += '-' + args.attempt
    os.environ.update(read(ROOT / config['environment_file'])); os.environ.update(config['runtime_overrides'])
    os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(ROOT / config['policy'])
    sys.path[:0] = [str(ROOT), str(ROOT / 'services/api')]
    try:
        asyncio.run(main(action, config))
    except Exception:
        save(action + '-failure.json', {'error': traceback.format_exc(), 'retry': False})
        raise
