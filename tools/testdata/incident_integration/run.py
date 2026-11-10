"""Prepare, seed, execute once and export three scoped I examples; no DDL or Case."""
import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write('\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize(config_path):
    config = read(config_path)
    assert config['version'] == 'socai2.incident-integration-eval.v1'
    assert config['planned_model_calls'] == len(config['scenarios']) == 3 and config['attempts_per_event'] == 1
    os.environ.update(read(ROOT / config['environment_file']))
    os.environ.update(config['runtime_overrides'])
    os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(ROOT / config['policy'])
    sys.path[:0] = [str(ROOT / 'services/api'), str(ROOT / 'deploy/local-investigation')]
    config['transport'] = {**read(ROOT / config['transport_config'])['transport'], **config['transport_overrides']}
    return config, ROOT / config['output']


def prepare(config, config_path, output):
    from .fixtures import packets
    samples = packets(ROOT, config)
    assert len({s['incident_id'] for s in samples}) == len(samples)
    files = [p for base in (ROOT / 'services/api/app/socai2', Path(__file__).parent) for p in base.rglob('*')
             if p.is_file() and p.suffix in {'.py', '.json'}]
    files += [config_path, ROOT / config['policy'], ROOT / config['snapshot'], ROOT / config['corpus'],
        ROOT / 'tools/testdata/alert_io_eval/evaluate.py', ROOT / 'tools/testdata/alert_io_eval/remote_worker.py']
    output.mkdir(parents=True, exist_ok=False)
    plan = {'batch': config['batch'], 'config': config, 'cases': samples, 'planned_model_calls': 3,
        'retries': 0, 'real_A_calls': 0, 'fake_query_receipts': 0, 'database_scope': 'existing isolated local database',
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in files},
        'limitations': ['Synthetic test membership; no Fusion/Kafka verification.',
            'Recorded materials are copied unchanged; prior A conclusions and query receipts are not replayed as newly executed.',
            'No expected verdicts or authored answer key sent to the model; no accuracy claim from these examples.']}
    save(output / 'plan.json', plan)
    print(json.dumps({'state': 'prepared_no_calls', 'events': len(samples),
        'alerts': sum(len(s['members']) for s in samples), 'material_missing': 1}), flush=True)


def validate_plan(config, output):
    plan = read(output / 'plan.json')
    assert plan['config'] == config
    assert all(sha(ROOT / p) == value for p, value in plan['source_sha256'].items()), 'prepared_source_changed'
    return plan


async def connect(config):
    from sqlalchemy import URL, text
    from sqlalchemy.ext.asyncio import create_async_engine
    db = read(ROOT / config['database_profile'])
    assert db['processing_database'] == config['expected_database'], 'not_the_configured_isolated_database'
    url = URL.create('postgresql+psycopg', username=db['admin'], password=Path(db['password_file']).read_text().strip(),
        host=db['host'], port=db['port'], database=db['processing_database'])
    engine = create_async_engine(url, connect_args={'sslmode': config['sslmode'], 'options': '-c role=' + db['processor']})
    async with engine.connect() as conn:
        actual = (await conn.execute(text('SELECT current_database(), current_user'))).one()
        assert tuple(actual) == (config['expected_database'], db['processor'])
    return engine


async def seed(config, output):
    from app.models import socai2 as m
    from app.socai2.stage_results import StageResultService
    from sqlalchemy import insert, select, update
    from sqlalchemy.ext.asyncio import async_sessionmaker
    plan = validate_plan(config, output)
    assert not (output / 'seed-intent.json').exists(), 'seed_already_attempted'
    engine = await connect(config)
    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))
    tenant = UUID(config['tenant_id'])
    save(output / 'seed-intent.json', {'database': config['expected_database'], 'batch': config['batch']})
    try:
        async with service.transaction(tenant) as store:
            for sample in plan['cases']:
                iid = UUID(sample['incident_id'])
                assert not await store.one(select(m.Incidents.id).where(m.Incidents.id == iid)), 'fixture_already_exists'
                await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=tenant, title=sample['title'],
                    source_namespace=config['batch'], source_incident_id=str(iid)))
                for member in sample['members']:
                    aid = UUID(member['alert_id'])
                    values = dict(member['alert'])
                    if values['event_time']:
                        values['event_time'] = datetime.fromisoformat(values['event_time'].replace('Z', '+00:00'))
                    await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant,
                        source_namespace=config['batch'], source_identity_key=str(aid), **values))
                    if member['material'] is not None:
                        mid = UUID(member['material_id'])
                        await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant,
                            alert_id=aid, revision=1, **member['material']))
                        await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
                    await store.db.execute(insert(m.IncidentAlerts).values(id=uuid5(iid, str(aid)), tenant_id=tenant,
                        incident_id=iid, alert_id=aid, membership_source='manual', basis_version='explicit_synthetic_fixture',
                        correlation_basis={'reason': 'fixed_test_membership_not_inferred_association'}, source_operation_id=iid))
        save(output / 'seed-receipt.json', {'state': 'committed', 'events': 3, 'real_A_calls': 0, 'tool_receipts': 0})
    finally:
        await engine.dispose()


async def execute(config, output):
    from app.socai2.stage_results import StageResultService
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tools.testdata.alert_io_eval.evaluate import remote

    from .gateway import Gateway
    plan = validate_plan(config, output)
    assert read(output / 'seed-receipt.json')['state'] == 'committed'
    assert not (output / 'execute-intent.json').exists(), 'batch_already_attempted_do_not_redispatch'
    preflight = await asyncio.to_thread(remote, config, {'phase': 'preflight'})
    save(output / 'preflight.json', preflight)
    assert preflight['state'] == 'ready'
    config = {**config, 'preflight': preflight}
    engine = await connect(config)
    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))
    save(output / 'execute-intent.json', {'planned_model_calls': plan['planned_model_calls'], 'retries': 0})
    try:
        for sample in plan['cases']:
            folder = output / 'calls' / sample['key']
            folder.mkdir(parents=True, exist_ok=False)
            gateway = Gateway(config, folder, sample['key'])
            print(sample['key'] + ' starting', flush=True)
            try:
                result = await service.execute_incident(UUID(config['tenant_id']), UUID(sample['incident_id']),
                    UUID(sample['operation_key']), gateway=gateway)
            except Exception as exc:  # noqa: BLE001 -- transport/DB exceptions can contain credentials
                result = {'state': 'execution_exception', 'error_type': type(exc).__name__}
            save(folder / 'execution.json', {**result, 'gateway_dispatch_attempts': gateway.calls})
            print(sample['key'] + ' ' + str(result['state']), flush=True)
    finally:
        await engine.dispose()


async def export(config, output):
    from app.api.v1.endpoints import socai2_analysis as analysis
    from app.api.v1.endpoints import socai2_pages as pages
    from app.socai2.page_reader import PageReadService
    from app.socai2.stage_reader import StageReadService
    from fastapi import FastAPI
    from flow_export import TABLES, query_for
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker
    plan = validate_plan(config, output)
    engine = await connect(config)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    page_reader, stage_reader = PageReadService(sessions), StageReadService(sessions)
    app = FastAPI()
    for module in (analysis, pages):
        app.include_router(module.router)
        app.dependency_overrides[module.User.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=UUID(config['tenant_id']))
    app.dependency_overrides[pages.get_service] = lambda: page_reader
    app.dependency_overrides[analysis.get_service] = lambda: stage_reader
    summaries = []
    try:
        async with engine.begin() as conn, AsyncClient(transport=ASGITransport(app=app), base_url='http://isolated.local') as client:
            await conn.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            await conn.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {'tenant': config['tenant_id']})
            for sample in plan['cases']:
                ids = (await conn.execute(text('SELECT id FROM socai2.runs WHERE tenant_id=CAST(:tenant AS uuid) AND incident_id=CAST(:id AS uuid)'),
                    {'tenant': config['tenant_id'], 'id': sample['incident_id']})).scalars().all()
                params = {'p1': config['tenant_id'], 'p2': [m['alert_id'] for m in sample['members']],
                    'p3': sample['incident_id'], 'p4': None, 'p5': list(map(str, ids))}
                data = {}
                for table in TABLES:
                    sql = query_for(table)
                    for n in range(1, 6):
                        sql = sql.replace(f'${n}::uuid[]', f'CAST(:p{n} AS uuid[])').replace(f'${n}::uuid', f'CAST(:p{n} AS uuid)')
                    data[table] = (await conn.execute(text(sql), params)).scalar_one()
                assert len(data['runs']) == 1 and data['runs'][0]['kind'] == 'incident_diagnosis'
                for expected in sample['members']:
                    alert = next(a for a in data['alerts'] if a['id'] == expected['alert_id'])
                    assert alert['description'] == expected['alert']['description'] and alert['latest_triage_id'] is None
                    if expected['material'] is None:
                        assert alert['latest_material_id'] is None
                    else:
                        material = next(m for m in data['alert_materials'] if m['id'] == expected['material_id'])
                        assert all(material[k] == value for k, value in expected['material'].items())
                folder = output / 'readback' / sample['key']
                save(folder / 'database.json', data)
                iid, rid = sample['incident_id'], str(ids[0])
                paths = [f'/socai2/incidents/{iid}', f'/socai2/incidents/{iid}/analysis',
                    f'/socai2/incidents/{iid}/records/members', f'/socai2/incidents/{iid}/analysis/runs/{rid}/trace']
                for member in sample['members']:
                    paths.append(f"/socai2/alerts/{member['alert_id']}")
                    if member['material_id']:
                        paths.append(f"/socai2/alerts/{member['alert_id']}/materials/{member['material_id']}")
                for artifact in data['artifacts']:
                    paths.append(f"/socai2/incidents/{iid}/analysis/runs/{rid}/artifacts/{artifact['id']}")
                responses = []
                for path in paths:
                    response = await client.get(path)
                    assert response.status_code == 200, (path, response.status_code)
                    responses.append({'path': path, 'status': response.status_code, 'body': response.json()})
                entry = responses[1]['body']['entries'][0]
                assert entry['run']['delivery_state'] == data['runs'][0]['delivery_state']
                assert entry['result']['diagnosis'] == data['incident_diagnoses'][0]['diagnosis']
                save(folder / 'api-responses.json', responses)
                summaries.append({'key': sample['key'], 'run_id': rid, 'state': data['runs'][0]['state'],
                    'delivery_state': data['runs'][0]['delivery_state'], 'http_gets': len(paths),
                    'original_materials_equal': True, 'counts': {t: len(v) for t, v in data.items()}})
    finally:
        await engine.dispose()
    save(output / 'readback/summary.json', {'snapshot': {'at': datetime.now(UTC).isoformat()},
        'environment': 'isolated_local_pg', 'model': 'real_internal_gateway', 'fixtures': summaries})
    print(json.dumps(summaries, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'seed', 'execute', 'export'))
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    config, output = initialize(args.config.resolve())
    if args.phase == 'prepare':
        prepare(config, args.config.resolve(), output)
    else:
        asyncio.run({'seed': seed, 'execute': execute, 'export': export}[args.phase](config, output))


if __name__ == '__main__':
    main()
