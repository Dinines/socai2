"""Real isolated PG A-five -> I-four save/read with explicit model substitutes."""
import asyncio
import copy
import json
import traceback
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import runtime_policy
from app.socai2.page_reader import PageReadService
from app.socai2.stage_reader import StageReadService
from app.socai2.stage_results import A, F, StageResultService
from socai2_test_model_view import synthetic_measure
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_socai2_incident_boundary_pg import Gateway as IncidentGateway

ROOT = Path(__file__).resolve().parents[3]
TENANT = UUID(int=1)


class Gateway:
    provider, model = 'synthetic', 'synthetic-five-field'

    def __init__(self, service, aid, *, mode='valid'):
        self.service, self.aid, self.mode = service, aid, mode
        self.calls, self.responses = 0, []

    async def configure(self, *_):
        return True

    async def measure(self, body, stage):
        return await synthetic_measure(body, stage)

    async def complete(self, body, timeout):
        self.calls += 1
        async with self.service.transaction(TENANT, readonly=True) as store:
            request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.alert_id == self.aid, F.c.kind == 'model_request')).order_by(F.c.captured_at.desc()).limit(1))).scalar_one()
        assert request['body'] == body and timeout > 0
        sid = next(s for s, v in request['source_map'].items() if v['ref']['role'] == 'observation')
        answer = {'verdict': 'needs_review', 'confidence': None, 'rationale': 'S3 业务原文仍需核实授权。',
                  'evidence_ids': [sid], 'recommendations': []}
        if self.mode in {'bad_advice', 'bad_core'}:
            answer['recommendations'] = [{'reason': '待核实。', 'source_ids': [sid]},
                                         {'reason': '无效建议。', 'source_ids': ['N999_S999']}]
        if self.mode == 'bad_core':
            answer['evidence_ids'] = ['N999_S999']
        if self.mode == 'malformed':
            answer['unexpected'] = 'must reject'
        result = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(answer)}}],
                  'usage': {'prompt_tokens': 150, 'completion_tokens': 80, 'total_tokens': 230}}
        self.responses.append(copy.deepcopy(result))
        return result


async def run_checks(engine, record, only=None):
    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))
    reader = StageReadService(service.sessions)

    async def fixture():
        aid, mid, iid = uuid4(), uuid4(), uuid4()
        async with service.transaction(TENANT) as store:
            await store.db.execute(insert(A).values(id=aid, tenant_id=TENANT, source_namespace='synthetic.ai-boundary',
                source_identity_key=str(aid), title='Synthetic A-I boundary', description='原有采集说明。'))
            await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=TENANT, alert_id=aid, revision=1,
                raw_text='Synthetic original statement.', raw_json={'process': {'pid': 42},
                'custom': {'id': 'business-id', 'authorized': False, 'size': 0, 'permissions_after': []}},
                detection={}, source_scope={}, retention={}, material_state='complete'))
            await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
            await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=TENANT,
                source_namespace='synthetic.ai-boundary', source_incident_id=str(iid), title='Synthetic event'))
            await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=TENANT,
                incident_id=iid, alert_id=aid, membership_source='fusion', basis_version='synthetic',
                correlation_basis={'reason': 'explicit test membership'}, source_operation_id=uuid4()))
        return aid, mid, iid

    async def artifacts(rid):
        async with service.transaction(TENANT, readonly=True) as store:
            return [dict(r) for r in (await store.db.execute(select(F).where(*store.where(F, F.c.run_id == rid)))).mappings()]

    async def http_gets(aid, mid, iid, arid, irid):
        from app.api.v1.endpoints import socai2_analysis as analysis
        from app.api.v1.endpoints import socai2_pages as pages
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        app = FastAPI()
        def dependency(value):
            return lambda: value
        for module, instance in ((analysis, reader), (pages, PageReadService(service.sessions))):
            app.include_router(module.router)
            app.dependency_overrides[module.get_service] = dependency(instance)
            app.dependency_overrides[module.User.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=TENANT)
        paths = [f'/socai2/alerts/{aid}', f'/socai2/alerts/{aid}/materials/{mid}',
            f'/socai2/alerts/{aid}/analysis', f'/socai2/alerts/{aid}/analysis/runs/{arid}',
            f'/socai2/alerts/{aid}/records/incidents', f'/socai2/incidents/{iid}',
            f'/socai2/incidents/{iid}/records/members', f'/socai2/incidents/{iid}/analysis/runs/{irid}']
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://synthetic.local') as client:
            replies = [await client.get(path) for path in paths]
        assert all(r.status_code == 200 for r in replies)
        values = [r.json() for r in replies]
        assert values[0]['facts']['description'] == '原有采集说明。'
        assert values[1]['content_text'] == 'Synthetic original statement.'
        assert values[1]['content_json']['raw_json']['custom']['permissions_after'] == []
        assert values[3]['run']['delivery_state'] == 'complete'
        assert values[7]['run']['delivery_state'] == 'complete'
        return len(paths)

    async def test_ai_five_field_to_incident_and_original_gets():
        aid, mid, iid = await fixture()
        gateway = Gateway(service, aid)
        ar = await service.execute_alert(TENANT, aid, uuid4(), gateway=gateway)
        assert ar['state'] == 'completed' and gateway.calls == 1
        entry = await reader.read_entry(TENANT, 'alert_basic', aid, ar['run_id'])
        assert entry.run.delivery_state == 'complete' and entry.result.verdict == 'needs_review'
        assert entry.explanation.content['generation_method'] == 'template'
        arts = await artifacts(ar['run_id'])
        request = next(a['content_json'] for a in arts if a['kind'] == 'model_request')
        assert request['alert_boundary']['version'] == 'socai2.alert-boundary.v1'
        assert 'business-id' in request['body']['messages'][1]['content']
        response = next(a['content_json'] for a in arts if a['kind'] == 'model_response')
        assert response['raw'] == gateway.responses[0]
        ir = await service.execute_incident(TENANT, iid, uuid4(), gateway=IncidentGateway(service, iid))
        assert ir['state'] == 'completed'
        arts = await artifacts(ir['run_id'])
        source = next(a['content_json'] for a in arts if a['id'] == ir['input_artifact_id'])
        assert source['members'][0]['triage']['source_run_id'] == str(ar['run_id'])
        assert len(source['triage_queries'][str(aid)]) == 3
        return {'run_id': str(ir['run_id']), 'alert_run_id': str(ar['run_id']),
            'http_gets': await http_gets(aid, mid, iid, ar['run_id'], ir['run_id']), 'real_model_calls': 0}

    async def test_ai_invalid_advice_partial_bad_core_not_adopted():
        aid, _, iid = await fixture()
        first = await service.execute_alert(TENANT, aid, uuid4(), gateway=Gateway(service, aid, mode='bad_advice'))
        entry = await reader.read_entry(TENANT, 'alert_basic', aid, first['run_id'])
        assert first['state'] == 'completed' and entry.run.delivery_state == 'partial'
        assert entry.result.verdict == 'needs_review' and len(entry.result.recommendations) == 1
        failures = []
        for mode in ('bad_core', 'malformed'):
            gateway, op = Gateway(service, aid, mode=mode), uuid4()
            result = await service.execute_alert(TENANT, aid, op, gateway=gateway)
            assert result['state'] == 'failed'
            await service.execute_alert(TENANT, aid, op, gateway=gateway)
            assert gateway.calls == 1
            current = await reader.read_page(TENANT, 'alert_basic', aid)
            assert str(current.current.run.id) == str(first['run_id'])
            failures.append(str(result['run_id']))
        # Use an I Run solely as the export anchor; no I model invocation.
        from app.socai2.stage_result_contracts import INCIDENT_EXECUTOR_VERSION
        anchor = await service.begin(TENANT, 'incident_diagnosis', iid, uuid4(), producer=INCIDENT_EXECUTOR_VERSION, limits=None)
        await service.stop(TENANT, anchor['run_id'], state='cancelled', code='synthetic_export_anchor')
        return {'run_id': str(anchor['run_id']), 'partial_run_id': str(first['run_id']), 'failed_runs': failures,
                'real_model_calls': 0, 'old_judgment_preserved': True}

    original = runtime_policy.active_policy
    policy = runtime_policy.load_policy(ROOT / 'deploy/local-investigation/investigation-policy-ai-v1.toml')
    runtime_policy.active_policy = lambda: policy
    try:
        checks = [v for k, v in locals().copy().items() if k.startswith('test_ai_')]
        for check in checks:
            if only and check.__name__ not in only:
                continue
            try:
                record(check.__name__, True, await asyncio.wait_for(check(), 120))
            except Exception:  # noqa: BLE001 -- preserve each actual test failure
                record(check.__name__, False, traceback.format_exc())
    finally:
        runtime_policy.active_policy = original
