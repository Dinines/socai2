"""One fixed A/I -> Case batch using existing drivers; never redispatch an intent."""
import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_knowledge.run import application
from tools.testdata.case_scope_recovery.real_model import Gateway, initialize, plan_for
from tools.testdata.incident_integration.fixtures import identity
from tools.testdata.incident_integration.run import connect, read, save, sha


async def run(config, folder):
    from app.db import database
    from app.db.case_database import close_case_database
    from app.models import socai2 as m
    from app.socai2 import baseline_executor
    from app.socai2.stage_results import StageResultService
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from tools.testdata.case_io_eval.model_eval import check_route, remote

    plan = plan_for(config, folder)
    assert not (folder / 'execute-intent.json').exists(), 'do_not_redispatch'
    preflight = await asyncio.to_thread(remote, config, {'phase': 'preflight', 'timeout_seconds': config['preflight_timeout_seconds']})
    save(folder / 'preflight.json', preflight)
    check_route(config, preflight)
    save(folder / 'execute-intent.json', {'attempts': 1, 'plan_sha256': sha(folder / 'plan.json'),
        'A_runs': len(config['rerun_alert_indices']), 'I_runs': 0, 'Case_runs': 1, 'retries': 0})
    gateways, responses, stages = {}, [], []
    tenant, iid = UUID(config['tenant_id']), UUID(read(ROOT / config['previous_flow'] / 'execution.json')['incident_id'])
    def gateway(key):
        assert key not in gateways
        transport = {**config['transport'], 'remote_evidence_dir': config['remote_evidence_dir'] + '/' + key}
        gateways[key] = Gateway({**config, 'transport': transport, 'preflight': preflight}, folder / key / 'calls')
        return gateways[key]
    engine = await connect(config)
    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))
    original = baseline_executor.TenantChatGateway
    outcome = {'state': 'not_completed'}
    try:
        async with service.transaction(tenant, readonly=True) as store:
            links = (await store.db.execute(select(m.IncidentAlerts.alert_id).where(
                m.IncidentAlerts.tenant_id == tenant, m.IncidentAlerts.incident_id == iid))).scalars().all()
            assert set(map(str, links)) == {member['alert_id'] for member in plan['members']}
            for member in plan['members']:
                material = (await store.db.execute(select(m.AlertMaterials.__table__).where(
                    m.AlertMaterials.id == UUID(member['material_id']), m.AlertMaterials.tenant_id == tenant))).mappings().one()
                assert {key: material[key] for key in member['material']} == member['material']
        for index, member in enumerate(plan['members'], 1):
            key = 'A' + str(index)
            if index in config['reuse_alert_indices']:
                previous = read(ROOT / config['reuse_alert_results'][str(index)])
                assert previous['state'] in {'completed', 'failed'}
                if previous['state'] == 'completed':
                    assert await service.freshness(tenant, UUID(previous['run_id']))
                stages.append(previous)
                save(folder / (key + '-reused.json'), {'source_file': config['reuse_alert_results'][str(index)], **previous})
                continue
            assert index in config['rerun_alert_indices']
            result = await service.execute_alert(tenant, UUID(member['alert_id']), UUID(identity(config['batch'], key)),
                gateway=gateway(key), requested_by=UUID(config['actor_id']))
            stages.append(result)
            save(folder / (key + '-execution.json'), result)
            print(key, result['state'], flush=True)
            assert not gateways[key].unknown, 'unknown_dispatch_stop'
        result = read(ROOT / config['reuse_incident_result'])
        stages.append(result)
        save(folder / 'I-reused.json', {'source_file': config['reuse_incident_result'], **result})
        baseline_executor.TenantChatGateway = lambda: gateway('Case')
        async with AsyncClient(transport=ASGITransport(app=application(config)), base_url=config['http_base_url'],
                               timeout=config['http_timeout_seconds']) as client:
            async def request(label, method, path, body=None):
                response = await client.request(method, path, json=body)
                record = {'label': label, 'method': method, 'path': path, 'request': body,
                          'status': response.status_code, 'body': response.json()}
                responses.append(record)
                save(folder / 'http' / (label + '.json'), record)
                print(label, response.status_code, flush=True)
                assert response.is_success, label
                return record['body']
            created = await request('create', 'POST', '/api/v1/socai2/cases', {'operation_key': plan['operation_key'],
                'title': config['title'], 'incident_ids': [str(iid)]})
            save(folder / 'created.json', created)
            base, rid = '/api/v1/socai2/cases/' + created['case_id'], created['pending_run_id']
            times = [datetime.fromisoformat(member['alert']['event_time']) for member in plan['members']]
            pad = timedelta(seconds=config['window_padding_seconds'])
            await request('start', 'POST', base + f'/runs/{rid}/start', {'expected_scope_revision': created['scope_revision'],
                'operation_key': identity(config['batch'], 'start'), 'window_start': (min(times)-pad).isoformat(),
                'window_end': (max(times)+pad).isoformat()})
            result = await request('run', 'GET', base + '/runs/' + rid)
            for result_id in result['result_ids']:
                await request('result-' + result_id, 'GET', base + '/results/' + result_id)
            await request('case', 'GET', base)
            outcome = {'state': result['run']['state'], 'case_id': created['case_id'], 'run_id': rid}
    except Exception as exc:
        outcome = {'state': 'execution_exception', 'error_type': type(exc).__name__, 'code': getattr(exc, 'code', None)}
    finally:
        baseline_executor.TenantChatGateway = original
        save(folder / 'execution.json', {**outcome, 'incident_id': str(iid), 'stages': stages,
            'model_calls': {key: value.calls for key, value in gateways.items()},
            'unknown': any(value.unknown for value in gateways.values())})
        save(folder / 'api-responses.json', responses)
        await close_case_database()
        await database.engine.dispose()
        await engine.dispose()
    print(outcome, flush=True)


async def export(config, folder):
    from app.socai2.case_data import export_page_data
    from flow_export import TABLES, query_for
    from sqlalchemy import text
    plan = plan_for(config, folder)
    created, execution = read(folder / 'created.json'), read(folder / 'execution.json')
    engine = await connect(config)
    try:
        data = {}
        async with engine.begin() as db:
            await db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {'tenant': config['tenant_id']})
            params = {'p1': config['tenant_id'], 'p2': [member['alert_id'] for member in plan['members']],
                'p3': execution['incident_id'], 'p4': created['case_id'], 'p5': [str(s['run_id']) for s in execution['stages']]}
            for table in TABLES:
                sql = query_for(table)
                for index in range(1, 6):
                    sql = sql.replace(f'${index}::uuid[]', f'CAST(:p{index} AS uuid[])').replace(f'${index}::uuid', f'CAST(:p{index} AS uuid)')
                data[table] = (await db.execute(text(sql), params)).scalar_one()
        out = folder / 'export'
        save(out / 'database.json', data)
        save(out / 'case-page-data.json', await export_page_data(data))
        save(out / 'api-responses.json', read(folder / 'api-responses.json'))
        save(out / 'manifest.json', {'schema_version': 'socai2.page-export.v1', 'batch_id': config['batch'],
            'exported_at': datetime.now(UTC).isoformat(), 'source_environment': 'local_pg_qdrant_real_embedding_and_model',
            'database': config['expected_database'], 'tenant_id': config['tenant_id'], 'case_id': created['case_id'],
            'sources': [{'file': name, 'sha256': sha(out / name)} for name in ('database.json', 'case-page-data.json', 'api-responses.json')],
            'table_counts': {key: len(value) for key, value in data.items()}, 'limitations': config['limitations']})
        print({key: len(data[key]) for key in ('alert_assessments','incident_diagnoses','cases','runs','results')}, flush=True)
    finally:
        await engine.dispose()


def prepare(config, path, folder):
    from app.socai2.runtime_policy import active_policy
    previous = ROOT / config['previous_flow'] / 'plan.json'
    files = [path, previous, ROOT / config['policy'], Path(__file__)]
    files += [p for p in (ROOT / 'services/api/app/socai2').glob('*') if p.suffix in {'.py', '.json'}]
    folder.mkdir(parents=True, exist_ok=False)
    save(folder / 'plan.json', {'config': config, 'members': read(previous)['members'],
        'operation_key': identity(config['batch'], 'create'), 'max_model_calls': active_policy().case.max_model_calls,
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in files}})
    print('prepared: reuse A/I, one new Case only', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'run', 'export'))
    args = parser.parse_args()
    path = Path(__file__).with_name('config.json')
    config, folder = initialize(path)
    if args.phase == 'prepare':
        prepare(config, path, folder)
        save(folder / 'driver-sha256.json', {'driver': sha(Path(__file__))})
    else:
        assert read(folder / 'driver-sha256.json')['driver'] == sha(Path(__file__))
        asyncio.run({'run': run, 'export': export}[args.phase](config, folder))
