"""Import one real historical C3 receipt into a new isolated Run, complete once."""
import argparse
import asyncio
import copy
import hashlib
import json
import os
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def save(folder, name, data):
    path = folder / name
    with path.open('x') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, default=str)
        stream.write('\n')


async def snapshot(service, tenant, cid, rid):
    from app.models import socai2 as m
    from app.socai2.baseline_enrichment import S
    from app.socai2.baseline_store import RM, C, F, R
    from sqlalchemy import select
    tables = {'cases': (C, C.c.id == cid), 'case_alerts': (m.CaseAlerts.__table__, m.CaseAlerts.__table__.c.case_id == cid),
        'runs': (R, R.c.id == rid), 'run_members': (RM, RM.c.run_id == rid),
        'run_steps': (S, S.c.run_id == rid), 'artifacts': (F, F.c.run_id == rid),
        'results': (m.Results.__table__, m.Results.__table__.c.source_run_id == rid)}
    data = {key: [] for key in read(ROOT / read(HERE / 'config.json')['source_export'])}
    async with service.transaction(tenant, readonly=True) as store:
        for name, (table, condition) in tables.items():
            rows = (await store.db.execute(select(table).where(*store.where(table, condition)))).mappings().all()
            data[name] = sorted([dict(row) for row in rows], key=lambda r: str(r['id']))
    return json.loads(json.dumps(data, default=str))


async def readback(service, tenant, folder, config):
    from app.socai2.baseline_store import digest
    from app.socai2.case_service import CaseService
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from investigation_http.external_routes import cases
    fixture = read(folder / 'fixture.json')
    cid, rid = UUID(fixture['case_id']), UUID(fixture['run_id'])
    before = await snapshot(service, tenant, cid, rid)
    artifacts = {a['id']: a for a in before['artifacts']}
    outcome = read(folder / 'c3-outcome.json')
    merged = outcome['basis']['section_completion']
    assert outcome['state'] == 'completed' and merged['state'] == 'merged'
    assert merged['attempts'] == 1 and merged['missing_fields'] == ['followups']
    original = artifacts[merged['initial_original_artifact_id']]['content_json']['raw']
    initial_request = artifacts[merged['initial_request_artifact_id']]['content_json']['payload']
    supplement_original = artifacts[merged['supplement_original_artifact_id']]['content_json']
    supplement_request = artifacts[supplement_original['request_artifact_id']]['content_json']['payload']
    assert original == read(folder / 'imported-packet.json')['raw']
    assert original['choices'][0]['finish_reason'] == 'length'
    assert supplement_request['body']['max_tokens'] == 8192
    schema = supplement_request['body']['response_format']['json_schema']['schema']
    assert schema['required'] == ['followups'] and set(schema['properties']) == {'followups'}
    assert not schema['additionalProperties']
    assert supplement_request['source_map'] == initial_request['source_map']
    assert supplement_request['case_boundary'] == initial_request['case_boundary']
    assert supplement_request['body']['messages'][1:-1] == initial_request['body']['messages'][1:]
    assert supplement_request['final_reservation'] == read(folder / 'reservation.json')
    for key, value in merged['retained_sections'].items():
        assert merged['merged_sections'][key] == value
        assert merged['field_origins'][key]['original_artifact_id'] == merged['initial_original_artifact_id']
        assert merged['field_origins'][key]['value_sha256'] == digest(value)
    assert merged['field_origins']['followups']['original_artifact_id'] == merged['supplement_original_artifact_id']
    assert merged['merged_sections']['followups'] == json.loads(supplement_original['raw']['choices'][0]['message']['content'])['followups']
    assert artifacts[merged['artifact_id']]['content_json']['derived'] == outcome['analysis']
    models = [s for s in before['run_steps'] if s['kind'] == 'model']
    assert len(models) == 2 and models[0]['stage_code'] == models[1]['stage_code'] == 'C3'
    first = next(s for s in models if s['name'] == 'imported_historical_C3_no_dispatch')
    second = next(s for s in models if s['name'] == 'bounded_reasoning_step')
    assert first['state'] == 'failed' and second['state'] == 'completed'
    used = sum(s['usage']['total_tokens'] for s in models)
    run = before['runs'][0]
    assert used + supplement_request['final_reservation']['reserved_tokens'] <= run['limits']['max_tokens']
    assert len(models) + supplement_request['final_reservation']['model_calls'] <= run['limits']['max_model_calls']
    assert before['results'] == []  # This step stops at C3; no C6/adoption claim.
    app = FastAPI(); app.include_router(cases.router, prefix='/api/v1')
    app.dependency_overrides[cases.get_service] = lambda: CaseService(service.sessions)
    app.dependency_overrides[cases.ReadUser.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=tenant)
    replies = []
    path = f'/api/v1/socai2/cases/{cid}'
    async with AsyncClient(transport=ASGITransport(app=app), base_url=config['http_base_url']) as client:
        for url in [path, path + f'/runs/{rid}', *[path + f'/runs/{rid}/artifacts/{a}' for a in artifacts]]:
            response = await client.get(url)
            assert response.status_code == 200, (url, response.status_code)
            value = response.json(); replies.append({'path': url, 'status': response.status_code, 'body': value})
            if '/artifacts/' in url:
                row = artifacts[url.rsplit('/', 1)[1]]
                assert value['content_json'] == row['content_json'] and value['content_text'] == row['content_text']
    assert await snapshot(service, tenant, cid, rid) == before
    after_source = await snapshot(service, tenant, UUID(fixture['source_case_id']), UUID(fixture['source_run_id']))
    assert after_source == read(folder / 'source-before.json')
    save(folder, 'database.json', before); save(folder, 'api-responses.json', replies)
    checks = {'case_id': str(cid), 'run_id': str(rid), 'historical_initial_model_calls': 1, 'new_real_model_calls': 1,
        'model_substitute_calls': 0, 'supplement_attempts': 1, 'retained_sections': list(merged['retained_sections']),
        'requested_sections': merged['missing_fields'], 'initial_usage': first['usage'], 'supplement_usage': second['usage'],
        'accounted_total_tokens': used, 'C6_reserved_tokens': supplement_request['final_reservation']['reserved_tokens'],
        'C6_reserved_calls': supplement_request['final_reservation']['model_calls'], 'http_gets': len(replies),
        'frozen_material_messages_and_maps_equal': True, 'retained_values_unchanged': True,
        'field_origins_verified': True, 'initial_failure_preserved': True, 'source_case_and_run_unchanged': True,
        'GET_readonly': True, 'C6_executed': False, 'external_source_calls': 0, 'real_model_quality': 'NOT_PASSED'}
    save(folder, 'checks.json', checks)
    names = ['database.json', 'api-responses.json', 'checks.json', 'c3-outcome.json', 'fixture.json', 'imported-packet.json']
    save(folder, 'manifest.json', {'schema_version': 'socai2.page-export.v1', 'batch_id': config['batch'],
        'tenant_id': str(tenant), 'case_id': str(cid), 'exported_at': datetime.now(UTC).isoformat(),
        'source_environment': 'isolated_pg_historical_C3_import_and_one_real_model_supplement',
        'database': config['expected_database'], 'input_kind': 'historical_real_model_receipt', 'real_model_calls': 1,
        'sources': [{'file': name, 'sha256': hashlib.sha256((folder / name).read_bytes()).hexdigest()} for name in names]})
    print(json.dumps(checks, ensure_ascii=False), flush=True)


async def execute(service, tenant, folder, config, runtime):
    from app.models import socai2 as m
    from app.socai2.baseline_analysis import BaselineAnalysis
    from app.socai2.baseline_analysis_contract import EXECUTION_SCHEMA
    from app.socai2.baseline_analysis_model import usage
    from app.socai2.baseline_capacity import final_reservation
    from app.socai2.baseline_context import Context, reference
    from app.socai2.baseline_contracts import FULL_EXECUTOR_VERSION
    from app.socai2.baseline_enrichment import S, error
    from app.socai2.baseline_reasoning import ModelSteps
    from app.socai2.baseline_store import RM, C, F, R, digest
    from app.socai2.case_c3_completion_flow import complete_sections
    from app.socai2.case_output_adapter import output_format
    from app.socai2.citation_quality import new_review
    from app.socai2.runtime_policy import active_policy
    from sqlalchemy import insert, null, select, update

    from tools.testdata.case_io_eval.model_eval import check_route, remote
    from tools.testdata.incident_integration.gateway import Gateway

    preflight = await asyncio.to_thread(remote, runtime, {'phase': 'preflight', 'timeout_seconds': config['preflight_timeout_seconds']})
    save(folder, 'preflight.json', preflight); check_route(runtime, preflight)
    runtime['preflight'] = preflight
    packet = read(ROOT / config['source_capacity'] / 'plan.json')
    source_rid, source_cid = UUID(packet['source_run_id']), UUID(packet['context']['case_id'])
    save(folder, 'source-before.json', await snapshot(service, tenant, source_cid, source_rid))
    cid, rid, stage_id, mid = uuid4(), uuid4(), uuid4(), uuid4()
    context_id, manifest_id, prepared_id, plan_step = uuid4(), uuid4(), uuid4(), uuid4()
    fixture = {'case_id': str(cid), 'run_id': str(rid), 'stage_id': str(stage_id), 'imported_model_step': str(mid),
        'source_case_id': str(source_cid), 'source_run_id': str(source_rid), 'scope': 'new validation Run; original business view and real failed reply imported, no historical dispatch'}
    save(folder, 'fixture.json', fixture)
    policy = active_policy(); prepared = copy.deepcopy(packet['prepared'])
    context = copy.deepcopy(packet['context']); context['case_id'] = str(cid); context['case']['id'] = str(cid)
    context['case_input_profile'] = policy.case_io.identity
    context = Context.model_validate(context)
    boundary = prepared['case_boundary']; boundary['profile'] = policy.case_io.identity
    boundary['c3_output'] = {k: policy.case_io.config['c3_output'][k] for k in ('version', 'max_findings')}
    system = '\n'.join(line for line in prepared['messages'][0]['content'].splitlines() if not line.startswith(('仅返回符合response_format', '一次返回summary')))
    boundary['c3_completion'] = {**policy.case_io.config['c3_completion'], 'system': system}
    runner = ModelSteps(service, EXECUTION_SCHEMA)
    async with service.transaction(tenant) as store:
        old_run = await store.run(source_cid, source_rid)
        old_step = await store.one(select(S).where(*store.where(S, S.c.run_id == source_rid, S.c.stage_code == 'C3', S.c.kind == 'model')).order_by(S.c.seq).limit(1))
        old_request = await store.one(select(F).where(*store.where(F, F.c.id == old_step['input_artifact_id'])))
        old_response = await store.one(select(F).where(*store.where(F, F.c.id == old_step['output_artifact_id'])))
        assert old_request['content_json']['payload']['body'] == packet['cells'][0]['body']
        assert old_request['content_json']['payload']['source_map'] == prepared['source_map']
        raw = old_response['content_json']['payload']['raw']
        assert raw['choices'][0]['finish_reason'] == 'length' and usage(raw)['usage_state'] == 'reported'
        assert raw['choices'][0]['message']['content'] == (ROOT / config['source_capacity'] / 'C02-4096/answer.txt').read_text()
        save(folder, 'imported-packet.json', {'source_request': old_request['content_json'], 'raw': raw,
            'source_context': packet['context'], 'source_prepared': packet['prepared'],
            'source_response_artifact_id': str(old_response['id']), 'source_request_artifact_id': str(old_request['id']),
            'historical_initial_output_limit': old_request['content_json']['payload']['body']['max_tokens']})
        now = await store.now(); limits = policy.case.limits(now, 'stage1.c3-completion.real-import.v1')
        await store.db.execute(insert(C).values(id=cid, tenant_id=tenant, title='C3真实截断原答补答验证', scope_revision=old_run['scope_revision'], created_by=UUID(config['actor_id'])))
        run_row = {**old_run, 'id': rid, 'case_id': cid, 'state': 'running', 'started_at': now, 'requested_at': now,
            'ended_at': None, 'stop_reason': None, 'stop_detail': None, 'delivery_state': 'none',
            'input_artifact_id': manifest_id, 'executor_version': FULL_EXECUTOR_VERSION,
            'limits': limits.model_dump(mode='json'), 'operation_key': str(uuid4()), 'request_hash': digest(fixture),
            'comparison_result_id': None, 'retry_of_run_id': None, 'row_version': 1, 'title': 'C3历史首答导入与一次真实补答'}
        pending = {**run_row, 'state': 'pending_update', 'started_at': None, 'input_artifact_id': None,
            'executor_version': None, 'operation_key': None, 'request_hash': None, 'limits': null()}
        await store.db.execute(insert(R).values(**pending))
        run = await store.run(cid, rid)
        for table in (m.CaseAlerts.__table__, RM):
            condition = table.c.run_id == source_rid if 'run_id' in table.c else table.c.case_id == source_cid
            rows = (await store.db.execute(select(table).where(*store.where(table, condition)))).mappings().all()
            for row in rows:
                values = {**row, 'id': uuid4(), 'case_id': cid}
                if 'run_id' in table.c:
                    values.update(run_id=rid, analysis_state='not_analyzed')
                await store.db.execute(insert(table).values(**values))
        manifest = copy.deepcopy((await store.one(select(F).where(*store.where(F, F.c.id == old_run['input_artifact_id']))))['content_json'])
        manifest['source_materials'] = [reference('artifact', context_id, 'execution_receipt')]
        for identity, payload, kind, schema in [(context_id, context.model_dump(mode='json'), 'source_snapshot', context.schema_version),
            (manifest_id, manifest, 'input_snapshot', manifest['schema_version']),
            (prepared_id, prepared, 'source_snapshot', prepared['schema_version'])]:
            await store.save_input_artifact(cid, rid, identity, payload, kind=kind, schema=schema,
                captured_at=now, refs=[], actor_id=UUID(config['actor_id']))
        await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(**run_row))
        run = await store.run(cid, rid)
        reservation = final_reservation(None, context, limits); save(folder, 'reservation.json', reservation)
        await store.db.execute(insert(S).values(id=plan_step, tenant_id=tenant, run_id=rid, seq=1, kind='stage', stage_code='C1.executor', state='running', name='historical_input_validation_plan', started_at=now))
        plan_id = await runner.save(store, run, plan_step, {'schema_version': EXECUTION_SCHEMA, 'type': 'execution_plan',
            'run_id': str(rid), 'limits': run['limits'], 'final_reservation': reservation, 'historical_input_import': fixture}, 'source_snapshot')
        await store.db.execute(update(S).where(S.c.id == plan_step).values(state='completed', ended_at=now, output_artifact_id=plan_id))
        await store.db.execute(insert(S).values(id=stage_id, tenant_id=tenant, run_id=rid, seq=2, kind='stage', stage_code='C3', state='running', name='initial_main_and_domain_analysis', started_at=now, input_artifact_id=prepared_id))
        await store.db.execute(insert(S).values(id=mid, tenant_id=tenant, run_id=rid, seq=3, kind='model', stage_code='C3', parent_step_id=stage_id, state='running', name='imported_historical_C3_no_dispatch', started_at=now))
        request = copy.deepcopy(old_request['content_json']); request['payload'].update(case_boundary=boundary, input_view_id=str(prepared_id), input_artifact_ids=[str(prepared_id)], historical_input_import=fixture)
        request_id = await runner.save(store, run, mid, request, 'model_request')
        original_id = await runner.save(store, run, mid, {'schema_version': EXECUTION_SCHEMA, 'type': 'model_original_response',
            'request_artifact_id': str(request_id), 'raw': raw, 'usage': usage(raw), 'historical_input_import': fixture}, 'source_snapshot')
        response = copy.deepcopy(old_response['content_json']); response['payload']['citation_review'] = {
            'original_response_artifact_id': str(original_id), 'request_artifact_id': str(request_id)}
        response_id = await runner.save(store, run, mid, response, 'model_response', [reference('artifact', request_id, 'execution_receipt')])
        await store.db.execute(update(S).where(S.c.id == mid).values(state='failed', ended_at=now, usage=usage(raw), error=error('model_response_not_complete', now), input_artifact_id=request_id, output_artifact_id=response_id))
    # A native current C3 call uses the same frozen prepared/request pairing.
    prepared.update(citation_review=new_review(), input_artifact_ids=[str(prepared_id)], input_view_id=str(prepared_id), binding_map=packet['bindings'])
    gateway = Gateway(runtime, folder / 'model', config['batch'] + '-supplement')
    result = await complete_sections(service, tenant, cid, rid, stage_id, prepared, context, packet['bindings'],
        output_format(prepared, context, packet['bindings']), gateway, (None, 'model_response_not_complete', mid, response_id), schema=EXECUTION_SCHEMA)
    analysis, rejection, model_id, result_id = result
    service_analysis = BaselineAnalysis(service); service_analysis.schema = EXECUTION_SCHEMA
    outcome = await service_analysis.finish(tenant, cid, rid, stage_id, model_id,
        'completed' if analysis else 'failed', rejection, [reference('artifact', prepared_id, 'execution_receipt')],
        analysis=analysis, source_map=prepared['source_map'], context=context, response_id=result_id,
        basis={'binding_map': packet['bindings'], 'citation_review': prepared['citation_review'],
            'section_completion': prepared.get('section_completion_result')})
    save(folder, 'c3-outcome.json', outcome)
    async with service.transaction(tenant) as store:
        await store.run(cid, rid)
        await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(state='completed' if analysis else 'failed',
            ended_at=await store.now(), delivery_state='partial', stop_reason='stage_output_saved' if analysis else 'c3_completion_failed'))
    assert gateway.calls == 1, 'real_supplement_was_not_dispatched'
    await readback(service, tenant, folder, config)


async def main(action, folder, config):
    from app.socai2.baseline_service import BaselineService
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tools.testdata.incident_integration.run import connect
    runtime = {**config, 'transport': {**read(ROOT / config['transport_config'])['transport'], 'remote_evidence_dir': config['remote_evidence_dir']}}
    engine = await connect(config)
    try:
        service, tenant = BaselineService(async_sessionmaker(engine, expire_on_commit=False)), UUID(config['tenant_id'])
        if action == 'run':
            await execute(service, tenant, folder, config, runtime)
        else:
            await readback(service, tenant, folder, config)
    finally:
        await engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('action', choices=['run', 'readback']); parser.add_argument('--attempt', required=True)
    args = parser.parse_args(); assert Path(args.attempt).name == args.attempt
    config = read(HERE / 'config.json'); folder = HERE / args.attempt
    assert config['planned_real_model_calls'] == 1 and config['model_substitute_calls'] == 0 and config['retries'] == 0
    sys.path[:0] = [str(ROOT / 'services/api'), str(ROOT)]
    os.environ.update(read(ROOT / config['environment_file'])); os.environ.update(config['runtime_overrides'])
    os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(ROOT / config['policy'])
    if args.action == 'run':
        folder.mkdir(exist_ok=False)
        sources = [*Path(ROOT / 'services/api/app/socai2').glob('*.py'), *Path(ROOT / 'services/api/app/socai2').glob('*.json'),
            Path(__file__), HERE / 'config.json', ROOT / config['policy']]
        save(folder, 'plan.json', {'config': config, 'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}})
    try:
        asyncio.run(main(args.action, folder, config))
    except Exception:
        save(folder, 'failure-' + datetime.now(UTC).strftime('%H%M%S') + '.txt.json', {'traceback': traceback.format_exc()})
        raise
