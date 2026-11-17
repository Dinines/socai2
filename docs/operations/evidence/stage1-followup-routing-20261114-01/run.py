"""One new isolated Case, real model and fixed read-only lake transport."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def read(path):
    return json.loads(path.read_text())


def save(folder, name, value):
    folder.mkdir(exist_ok=True, parents=True)
    with (folder / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write('\n')


def previous_helpers():
    path = HERE.parent / 'stage1-c3-completion-20261114-01/run.py'
    spec = importlib.util.spec_from_file_location('step4_read_helpers', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LakeTransport:
    def __init__(self, config, folder):
        self.source, self.folder, self.calls = config['source'], folder, 0

    def configured(self):
        return True

    def unavailable_reason(self, binding):
        return 'product_source_not_enabled' if binding['tool_name'] == 'product_host_details' else None

    async def query(self, args, query_id, timeout):
        from app.socai2.baseline_evidence_tools import normalize_rows, query_sql
        from clickhouse_driver.util.escape import escape_params
        cfg = self.source
        assert args['parameters']['tenant_id'] == cfg['tenant_id']
        assert args['parameters']['hostname'] == cfg['hostname']
        for key in ('window_start', 'window_end'):
            assert datetime.fromisoformat(args['scope'][key]) == datetime.fromisoformat(cfg[key])
        assert args['parameters']['source_database'] == cfg['database']
        assert args['limit'] <= cfg['query_read_limit'] and timeout >= 1
        sql, parameters = query_sql(args)
        # The core query supplies only strings and integers, not driver dates.
        rendered = sql % escape_params(parameters, context=None) + ' FORMAT JSON'
        self.calls += 1
        save(self.folder, f'query-{self.calls}-intent.json', {'args': args, 'sql': sql, 'parameters': parameters,
             'rendered_sql': rendered, 'query_id': query_id, 'transport': 'SSH_to_readonly_ClickHouse_HTTP'})
        worker = (HERE / 'lake_worker.py').read_text()
        command = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
                   '-o', 'ConnectTimeout=8', cfg['ssh_target'], shlex.join(['python3', '-c', worker])]
        def call():
            return subprocess.run(command, input=json.dumps({'source': cfg, 'sql': rendered, 'query_id': query_id}),
                capture_output=True, text=True, timeout=min(timeout, cfg['timeout_seconds'] + 10), check=False)
        result = await asyncio.to_thread(call)
        if result.returncode:
            raise RuntimeError('lake_transport_uncertain')
        received = json.loads(result.stdout)
        save(self.folder, f'query-{self.calls}-receipt.json', received)
        if received['state'] != 'response_received':
            raise RuntimeError('lake_response_uncertain')
        return normalize_rows(received['payload']['data'])


async def readback(service, tenant, folder, config):
    from app.models import socai2 as models
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from investigation_http.external_routes import cases
    from sqlalchemy import func, select
    old = previous_helpers()
    fixture = read(folder / 'fixture.json')
    cid, rid = UUID(fixture['case_id']), UUID(fixture['run_id'])
    before = await old.snapshot(service, tenant, cid, rid)
    artifacts = {row['id']: row for row in before['artifacts']}
    payloads = [row['content_json'] for row in artifacts.values() if row['content_json']]
    dispatch = next((v for v in payloads if v.get('type') == 'followup_dispatch'), None)
    initial = next((v for v in payloads if v.get('type') == 'analysis_summary' and v.get('phase') == 'C3_initial'), None)
    if initial is None:
        initial = next((v for v in payloads if v.get('schema_version', '').startswith('socai2.baseline-analysis') and 'analysis' in v), None)
    for row in (dispatch or {}).get('routes', []):
        if row['mode'] in {'query', 'human', 'graph'}:
            assert 'activity' in row
        for query in row.get('activity', {}).get('queries', []):
            raw = artifacts[query['query_artifact_id']]['content_json']
            assert query['state'] == raw['state'] and query['returned_rows'] == raw['returned_rows']
        if row['mode'] in {'human', 'graph'}:
            assert row['activity']['new_query_attempt_count'] == 0
    run = before['runs'][0]
    c4 = [s for s in before['run_steps'] if s['stage_code'] == 'C4.query']
    query_artifacts = [artifacts[s['output_artifact_id']]['content_json'] for s in c4 if s['output_artifact_id']]
    c6_requests = [a['content_json']['payload'] for a in artifacts.values() if a['kind'] == 'model_request'
        and any(s['id'] == a['step_id'] and s['stage_code'] == 'C6' for s in before['run_steps'])]
    assert all(p['final_reservation']['reserved_tokens'] == 51200 for p in c6_requests)
    async with service.transaction(tenant, readonly=True) as store:
        tasks = models.Tasks.__table__
        task_count = (await store.db.execute(select(func.count()).select_from(tasks).where(
            *store.where(tasks, tasks.c.case_id == cid)))).scalar_one()
    assert task_count == 0
    seed = read(ROOT / config['source']['seed_plan'])
    context_ids = {row['event_id'] for row in seed['rows'] if row['kind'] == 'authored_synthetic_context_only_in_lake'}
    returned_context = {row['event_id'] for receipt in query_artifacts for row in receipt.get('rows') or []} & context_ids
    seen_context = set()
    for artifact in artifacts.values():
        projection = artifact['content_json'] or {}
        if projection.get('type') != 'query_projection':
            continue
        receipt = artifacts[projection['receipt_id']]['content_json']
        for index, row in enumerate(projection['rows']):
            event_id = receipt['rows'][row['receipt_row']]['event_id']
            if event_id in context_ids and any(
                src['ref']['id'] == artifact['id'] and (src['ref']['source_path'] or '').startswith(f'$.rows.{index}.')
                for request in c6_requests for src in request['source_map'].values()):
                seen_context.add(event_id)
    app = FastAPI(); app.include_router(cases.router, prefix='/api/v1')
    app.dependency_overrides[cases.get_service] = lambda: service
    app.dependency_overrides[cases.ReadUser.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=tenant)
    replies, prefix = [], f'/api/v1/socai2/cases/{cid}'
    paths = [prefix, prefix + f'/runs/{rid}', *[prefix + f'/runs/{rid}/artifacts/{aid}' for aid in artifacts],
             *[prefix + f'/results/{row["id"]}' for row in before['results']]]
    async with AsyncClient(transport=ASGITransport(app), base_url=config['http_base_url']) as client:
        for path in paths:
            response = await client.get(path)
            assert response.status_code == 200, (path, response.status_code)
            value = response.json(); replies.append({'path': path, 'status': response.status_code, 'body': value})
            if '/artifacts/' in path:
                row = artifacts[path.rsplit('/', 1)[1]]
                assert value['content_json'] == row['content_json'] and value['content_text'] == row['content_text']
    assert await old.snapshot(service, tenant, cid, rid) == before
    assert await old.snapshot(service, tenant, UUID(fixture['source_case_id']), UUID(fixture['source_run_id'])) == read(folder / 'source-before.json')
    save(folder, 'database.json', before); save(folder, 'api-responses.json', replies)
    model_steps = [s for s in before['run_steps'] if s['kind'] == 'model']
    checks = {'case_id': str(cid), 'run_id': str(rid), 'run_state': run['state'],
        'delivery_state': run['delivery_state'], 'new_real_model_calls': len(model_steps), 'model_substitute_calls': 0,
        'C4_query_steps': len(c4), 'C4_step_states': [s['state'] for s in c4],
        'C4_query_states': [q['state'] for q in query_artifacts],
        'C4_returned_rows': [q['returned_rows'] for q in query_artifacts],
        'nonempty_source_evidence_passed': any(q['state'] == 'completed' and q['returned_rows'] > 0 for q in query_artifacts),
        'lake_only_context_returned': sorted(returned_context), 'lake_only_context_in_C6': sorted(seen_context),
        'query_origin': 'native_C3_plan_and_C4_dispatch', 'route_modes': [r['mode'] for r in (dispatch or {}).get('routes', [])],
        'C6_executed': bool(c6_requests), 'result_count': len(before['results']), 'http_gets': len(replies),
        'source_case_run_unchanged': True, 'GET_readonly': True, 'human_tasks_created': task_count,
        'C6_reserved_calls': 2, 'C6_reserved_tokens': 51200,
        'total_tokens': sum(s['usage']['total_tokens'] for s in model_steps if s['usage'] and s['usage'].get('total_tokens') is not None),
        'real_model_quality': 'NOT_PASSED', 'published': False}
    save(folder, 'checks.json', checks)
    names = ['database.json', 'api-responses.json', 'checks.json', 'fixture.json', 'execution.json']
    save(folder, 'manifest.json', {'schema_version': 'socai2.page-export.v1', 'batch_id': config['batch'],
        'tenant_id': str(tenant), 'case_id': str(cid), 'exported_at': datetime.now(UTC).isoformat(),
        'source_environment': 'isolated_PG_real_model_and_readonly_production_lake_synthetic_host',
        'database': config['expected_database'], 'input_kind': 'existing_synthetic_exercise_materials',
        'real_model_calls': len(model_steps), 'sources': [{'file': name, 'sha256': hashlib.sha256((folder / name).read_bytes()).hexdigest()} for name in names]})
    print(json.dumps(checks, ensure_ascii=False), flush=True)


async def main(action, folder, config):
    from app.socai2.baseline_contracts import Actor, Start
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.runtime_policy import active_policy
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tools.testdata.case_io_eval.model_eval import check_route, remote
    from tools.testdata.case_scope_recovery.real_model import Gateway
    from tools.testdata.incident_integration.run import connect
    engine = await connect(config)
    tenant = UUID(config['tenant_id']); service = CaseService(async_sessionmaker(engine, expire_on_commit=False))
    try:
        if action == 'readback':
            return await readback(service, tenant, folder, config)
        source = read(ROOT / config['source_export'])
        source_case = source['cases'][0]
        source_run = next(row for row in source['runs'] if row['case_id'] == source_case['id'])
        old = previous_helpers()
        save(folder, 'source-before.json', await old.snapshot(service, tenant, UUID(source_case['id']), UUID(source_run['id'])))
        runtime = {**config, 'transport': {**read(ROOT / config['transport_config'])['transport'],
                   'remote_evidence_dir': config['remote_evidence_dir'] + '/' + folder.name}}
        preflight = await asyncio.to_thread(remote, runtime, {'phase': 'preflight', 'timeout_seconds': config['preflight_timeout_seconds']})
        save(folder, 'preflight.json', preflight); check_route(config, preflight)
        gateway = Gateway({**runtime, 'preflight': preflight}, folder / 'model')
        lake = LakeTransport(config, folder / 'lake')
        actor = Actor(user_id=UUID(config['actor_id']), name='local-material-review@example.invalid')
        created = await service.create_case(tenant, CaseCreate(operation_key=uuid4(),
            title='步骤5演练：核对主机行为记录和补查能力',
            description='核查固定成员之间有无已证联系及待核事实。按现有认证、进程和网络记录能力补查；授权文件不在工具能力内时明确待补，不把建议当执行。',
            alert_ids=[UUID(row['id']) for row in source['alerts']]), actor=actor)
        cid, rid = created.case_id, created.pending_run_id
        save(folder, 'fixture.json', {'case_id': cid, 'run_id': rid, 'source_case_id': source_case['id'],
             'source_run_id': source_run['id'], 'source_export': config['source_export'],
             'input_kind': 'existing_synthetic_exercise_materials', 'created': created.model_dump(mode='json')})
        async with service.transaction(tenant, readonly=True) as store:
            limits = active_policy().case.limits(await store.now(), active_policy().identity)
        save(folder, 'limits.json', limits.model_dump(mode='json'))
        await service.start_full(tenant, cid, rid, Start(operation_key=uuid4(), expected_scope_revision=created.scope_revision,
            window_start=config['source']['window_start'], window_end=config['source']['window_end']),
            actor=actor, limits=limits, gateway=gateway, lake=lake)
        save(folder, 'execution.json', {'case_id': cid, 'run_id': rid, 'model_calls': gateway.calls,
             'lake_calls': lake.calls, 'model_unknown': gateway.unknown, 'new_A_I_calls': 0})
        await readback(service, tenant, folder, config)
    finally:
        await engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['run', 'readback']); parser.add_argument('--attempt', required=True)
    args = parser.parse_args(); assert Path(args.attempt).name == args.attempt
    config = read(HERE / 'config.json'); folder = HERE / args.attempt
    sys.path[:0] = [str(ROOT / 'services/api'), str(ROOT)]
    os.environ.update(read(ROOT / config['environment_file'])); os.environ.update(config['runtime_overrides'])
    os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(ROOT / config['policy'])
    if args.action == 'run':
        folder.mkdir(exist_ok=False)
        files = [*Path(ROOT / 'services/api/app/socai2').glob('*.py'), *Path(ROOT / 'services/api/app/socai2').glob('*.json'),
                 Path(__file__), HERE / 'config.json', HERE / 'lake_worker.py', ROOT / config['policy']]
        save(folder, 'plan.json', {'config': config, 'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}})
    try:
        asyncio.run(main(args.action, folder, config))
    except Exception:
        save(folder, 'failure-' + datetime.now(UTC).strftime('%H%M%S') + '.json', {'traceback': traceback.format_exc()})
        raise
