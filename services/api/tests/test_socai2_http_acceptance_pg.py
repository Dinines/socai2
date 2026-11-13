"""Current HTTP workflows with real isolated PG and explicit model substitutes.

Run through the existing restricted-PG runner, not pytest collection. Authentication
is substituted. No production configuration, real model or vendor is contacted.
"""
import asyncio
import json
import traceback
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import (
    socai2_analysis,
    socai2_case_ai,
    socai2_cases,
    socai2_stage_execution,
    socai2_tasks,
)
from app.models import socai2 as m
from app.socai2.baseline_store import F
from app.socai2.human_task_service import HumanTaskService
from app.socai2.stage_reader import StageReadService
from app.socai2.stage_results import StageResultService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.services import CaseBackend as CaseService
from investigation_http.adapters.services import ExecutionBackend
from jsonschema import Draft202012Validator
from socai2_test_model_view import synthetic_measure
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_socai2_ai_boundary_pg import Gateway as AlertGateway
from test_socai2_case_followup_boundary import final_answer
from test_socai2_case_model_boundary import answer_for
from test_socai2_incident_boundary_pg import Gateway as IncidentGateway

TENANT, USER = UUID(int=1), UUID(int=3)
BASE = '/api/v1/socai2/cases'


class CurrentGateway:
    provider, model = 'synthetic', 'http-contract-no-network'

    def __init__(self, service, case_id, run_id):
        self.service, self.case_id, self.run_id = service, case_id, run_id
        self.calls = []

    async def configure(self, *_):
        return True

    async def measure(self, body, stage):
        return await synthetic_measure(body, stage)

    async def complete(self, body, timeout):
        assert timeout > 0
        async with self.service.transaction(TENANT, readonly=True) as store:
            request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.run_id == self.run_id, F.c.kind == 'model_request'))
                .order_by(F.c.captured_at.desc()).limit(1))).scalar_one()['payload']
            context = await store.read_context(self.case_id, self.run_id)
        assert request['body'] == body
        stage = request['case_boundary'].get('stage', 'C3')
        self.calls.append(stage)
        if stage == 'C3':
            answer = answer_for(request, context)
        else:
            assert stage == 'C6'
            answer = final_answer(request, context, request['followup_boundary']['program_metadata']['comparison'])
        Draft202012Validator(body['response_format']['json_schema']['schema']).validate(answer)
        return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(answer)}}],
                'usage': {'prompt_tokens': 200, 'completion_tokens': 100, 'total_tokens': 300}}


async def run_checks(engine, record, only=None):
    class CurrentCaseService(CaseService):
        async def start_full(self, tenant, cid, rid, *args, **kwargs):
            self.gateway = CurrentGateway(self, cid, rid)
            with patch('app.socai2.baseline_enrichment.sources.CONNECTED', frozenset()):
                return await super().start_full(tenant, cid, rid, *args, **kwargs,
                    gateway=self.gateway, lake=SimpleNamespace(configured=lambda: False))

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service, tasks = CurrentCaseService(sessions), HumanTaskService(sessions)
    async def empty_query(service, tenant, name, args):
        async with service.transaction(tenant, readonly=True) as store:
            return [], await store.now()

    class CurrentStages(StageResultService):
        async def execute_alert(self, tenant, aid, operation, **kwargs):
            return await super().execute_alert(tenant, aid, operation, **kwargs,
                gateway=AlertGateway(self, aid), query=empty_query)

        async def execute_incident(self, tenant, iid, operation, **kwargs):
            return await super().execute_incident(tenant, iid, operation, **kwargs,
                gateway=IncidentGateway(self, iid))

    stages = CurrentStages(sessions)
    app = FastAPI()
    for api in (socai2_cases, socai2_tasks, socai2_case_ai, socai2_stage_execution, socai2_analysis):
        app.include_router(api.router, prefix='/api/v1')
    principal = CurrentUser(USER, TENANT, 'admin', 'synthetic-http@example.invalid',
        scopes=['cases:read', 'cases:write', 'alerts:read', 'alerts:write'])
    app.dependency_overrides[get_current_user] = lambda: principal
    app.dependency_overrides[socai2_cases.get_service] = lambda: service
    app.dependency_overrides[socai2_tasks.get_service] = lambda: tasks
    execution_backend = ExecutionBackend(sessions)
    execution_backend._execution = stages  # Existing model substitute, same HTTP port.
    app.dependency_overrides[socai2_stage_execution.get_execution_service] = lambda: execution_backend
    app.dependency_overrides[socai2_analysis.get_service] = lambda: StageReadService(sessions)
    client = AsyncClient(transport=ASGITransport(app=app), base_url='http://synthetic.local')

    async def request(method, path, *, code=200, **kwargs):
        response = await client.request(method, path, **kwargs)
        assert response.status_code == code, (response.status_code, response.text)
        return response.json()

    async def fixture():
        aid, mid = uuid4(), uuid4()
        async with service.transaction(TENANT) as store:
            now = await store.now()
            await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=TENANT,
                title='Synthetic HTTP acceptance', source_namespace='http-acceptance-20261112', source_identity_key=str(aid)))
            await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=TENANT, alert_id=aid,
                revision=1, raw_json={'process': {'pid': 42, 'cmd_line': 'synthetic --inspect'}},
                ocsf_json={'process': {'pid':42, 'cmd_line':'synthetic --inspect'}},
                detection={}, source_scope={}, material_state='complete', retention={}))
            await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
        created = await request('POST', BASE, json={'operation_key': str(uuid4()),
            'title':'Synthetic HTTP acceptance', 'alert_ids':[str(aid)]})
        return created, aid, mid, now

    async def test_http_metadata_evidence_and_human_revision_readback():
        created, aid, mid, now = await fixture()
        cid, path = created['case_id'], BASE+'/'+created['case_id']
        unchanged = await request('PUT', path+'/members', json={'operation_key':str(uuid4()),
            'expected_scope_revision':1, 'alert_ids':[str(aid)]})
        assert unchanged['scope_revision'] == 1
        case = (await request('GET', path))['case']
        body = {'operation_key':str(uuid4()), 'expected_row_version':case['row_version'],
            'classification':'informational', 'due_at':(now+timedelta(days=1)).isoformat(),
            'source':'manual', 'source_note':'Synthetic verification of stored fields'}
        changed = await request('PATCH', path+'/page-data', json=body)
        assert changed == await request('PATCH', path+'/page-data', json=body)
        page = await request('GET', path+'/page-data')
        assert page['classification'] == body['classification'] and page['due_at']
        assert (await request('GET', path))['page_data'] == page
        await request('PATCH', path+'/page-data', json={**body, 'operation_key':str(uuid4())}, code=409)
        ref = {'type':'alert_material', 'id':str(mid), 'external':None,
            'source_path':'/ocsf_json/process/pid', 'row_keys':[], 'role':'observation'}
        publish = {'operation_key':str(uuid4()), 'expected_row_version':changed['row_version'],
            'expected_current_artifact_id':None, 'index':{'schema_version':'socai2.case-evidence.v1',
                'scope_revision':1, 'alert_ids':[str(aid)], 'supersedes_artifact_id':None,
                'availability_state':'available', 'limitations':[], 'entries':[{
                    'evidence_id':'synthetic:process', 'title':'Synthetic process record', 'type':'log',
                    'alert_ids':[str(aid)], 'object_keys':[], 'source_refs':[ref], 'verdict':'unknown',
                    'verdict_sources':[], 'threat':None, 'remediation':None, 'state':'active'}]}}
        published = await request('POST', path+'/evidence-index', json=publish)
        assert published == await request('POST', path+'/evidence-index', json=publish)
        page = await request('GET', path+'/page-data')
        assert page['evidence']['evidence_count'] == 1 and page['evidence']['threat_count'] == 0
        assert page['evidence']['artifact_id'] == published['current_evidence_artifact_id']
        artifact = await request('GET', path+'/artifacts/'+published['current_evidence_artifact_id'])
        assert artifact['availability'] == 'available'
        task_body = {'operation_key':str(uuid4()), 'expected_scope_revision':1, 'title':'Confirm authorization',
            'description':'Synthetic manual confirmation', 'source_refs':[{'type':'alert_material','id':str(mid)}]}
        task = (await request('POST', path+'/tasks', json=task_body))['task']
        old = task['current_revision_id']
        completion = {'operation_key':str(uuid4()), 'expected_scope_revision':1, 'expected_row_version':task['row_version'],
            'title':task_body['title'], 'description':task_body['description'], 'state':'completed',
            'result_text':'Synthetic operator statement; authorization still unconfirmed.',
            'result_scope':{'kind':'whole_case','alert_ids':[str(aid)],'object_keys':[],
                'window_start':None,'window_end':None,'limitations':['Synthetic only']}, 'source_refs':task_body['source_refs']}
        endpoint = path+'/tasks/'+task['id']
        receipt = await request('PUT', endpoint, json=completion)
        assert receipt == await request('PUT', endpoint, json=completion)
        current = await request('GET', endpoint)
        assert current['current']['result_text'] == completion['result_text']
        assert current['current']['result_scope'] == completion['result_scope']
        assert current['current']['revision'] == 2 and current['row_version'] == 2
        history = await request('GET', endpoint+'/revisions')
        assert history['total'] == 2
        assert (await request('GET', endpoint+'/revisions/'+old))['result_text'] is None
        assert (await request('GET', path+'/tasks'))['items'][0] == current
        run = await request('GET', path+'/runs/'+created['pending_run_id'])
        assert run['run']['state'] == 'pending_update' and run['run']['started_at'] is None
        async with service.transaction(TENANT, readonly=True) as store:
            persisted = await store.case(UUID(cid), lock=False)
            revision = (await store.db.execute(select(m.TaskRevisions.__table__).where(m.TaskRevisions.id == UUID(current['current_revision_id'])))).mappings().one()
            assert persisted['classification'] == body['classification']
            assert persisted['due_at'] == now+timedelta(days=1)
            assert revision['result_text'] == completion['result_text']
        replaced = await request('PUT', path+'/members', json={'operation_key':str(uuid4()),
            'expected_scope_revision':1, 'alert_ids':[]})
        assert replaced['scope_revision'] == 2 and (await request('GET', path))['member_count'] == 0
        assert (await request('GET', endpoint))['current']['result_scope']['alert_ids'] == [str(aid)]
        return {'case_id':cid, 'task_id':task['id'], 'evidence_artifact_id':published['current_evidence_artifact_id']}

    async def test_http_current_case_start_persisted_result_and_frozen_material():
        created, aid, mid, now = await fixture()
        path, rid = BASE+'/'+created['case_id'], created['pending_run_id']
        prepared = await request('POST', path+'/baseline/prepare', json={'operation_key':str(uuid4()),'expected_scope_revision':1})
        assert prepared['pending_run_id'] == rid and not prepared['created']
        start = {'operation_key':str(uuid4()), 'expected_scope_revision':1,
                 'window_start':(now-timedelta(minutes=5)).isoformat(), 'window_end':now.isoformat()}
        finished = await request('POST', path+'/runs/'+rid+'/start', json=start)
        assert finished['run']['state'] == 'completed', finished
        assert service.gateway.calls == ['C3','C6']
        result_id = finished['result_ids'][0]
        result = await request('GET', path+'/results/'+result_id)
        assert result['result']['validation_state'] == 'accepted', result
        assert result['result']['conclusion_state'] == 'uncertain'
        for field in ['report_artifact_id','graph_artifact_id']:
            artifact = await request('GET', path+'/runs/'+rid+'/artifacts/'+result['result'][field])
            assert artifact['availability'] == 'available'
        newer = uuid4()
        async with service.transaction(TENANT) as store:
            await store.db.execute(insert(m.AlertMaterials).values(id=newer, tenant_id=TENANT, alert_id=aid,
                revision=2, raw_json={'process':{'pid':99}}, detection={}, source_scope={}, material_state='complete', retention={}))
            await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=newer))
        assert (await request('GET', path+'/runs/'+rid+'/materials/'+str(mid)))['raw_json']['process']['pid'] == 42
        await request('GET', path+'/runs/'+rid+'/materials/'+str(newer), code=404)
        assert (await request('GET', path+'/history'))['items'][0]['result']['id'] == result_id
        replay = await request('POST', path+'/runs/'+rid+'/start', json=start)
        assert replay['result_ids'] == [result_id]
        async with service.transaction(TENANT, readonly=True) as store:
            saved = (await store.db.execute(select(m.Results.__table__).where(m.Results.id == UUID(result_id)))).mappings().one()
            for field in ['conclusion','conclusion_state','validation_state','findings','questions','recommendations']:
                assert result['result'][field] == saved[field], field
        return {'case_id':created['case_id'],'run_id':rid,'result_id':result_id,'real_model_calls':0}

    async def test_http_reserved_functions_are_unimplemented():
        created, _, _, _ = await fixture()
        path = BASE+'/'+created['case_id']
        for suffix, body in [('/ai/messages', {'question':'Synthetic question'}),
                ('/ai/messages/'+str(uuid4())+'/save', {'title':'Synthetic answer','conclusion':'Unverified'}),
                ('/results/'+str(uuid4())+'/adopt', {'expected_scope_revision':1})]:
            response = await request('POST', path+suffix, json={'operation_key':str(uuid4()), **body}, code=501)
            assert response['detail']['code'] == 'case_ai_not_implemented'
        return {'implemented':False, 'http_status':501}

    async def test_http_alert_incident_execution_saved_and_replayed():
        _, aid, _, _ = await fixture()
        iid = uuid4()
        async with service.transaction(TENANT) as store:
            await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=TENANT,
                title='Synthetic HTTP event', source_namespace='http-acceptance-20261112', source_incident_id=str(iid)))
            await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=TENANT,
                alert_id=aid, incident_id=iid, membership_source='fusion', correlation_basis={},
                basis_version='synthetic', source_operation_id=uuid4()))
        runs = []
        for endpoint in [f'/api/v1/socai2/alerts/{aid}/analyze', f'/api/v1/socai2/incidents/{iid}/diagnose']:
            body = {'operation_key':str(uuid4())}
            result = await request('POST', endpoint, json=body)
            assert result['run']['state'] == 'completed' and result['result'] is not None, result
            assert result['is_current_pointer'] and result['valid_for_current_input']
            assert result == await request('POST', endpoint, json=body)
            subject_path = endpoint.rsplit('/', 1)[0]
            assert result == await request('GET', subject_path+'/analysis/runs/'+result['run']['id'])
            runs.append(result['run']['id'])
        return {'alert_id':str(aid), 'incident_id':str(iid), 'run_ids':runs,
                'real_model_calls':0, 'production_flag_bypassed_only_for_isolated_logic_test':True}

    try:
        for check in [test_http_metadata_evidence_and_human_revision_readback,
                      test_http_current_case_start_persisted_result_and_frozen_material,
                      test_http_reserved_functions_are_unimplemented,
                      test_http_alert_incident_execution_saved_and_replayed]:
            if only is not None and check.__name__ not in only:
                continue
            try:
                record(check.__name__, True, await asyncio.wait_for(check(), 120))
            except Exception:
                record(check.__name__, False, traceback.format_exc())
    finally:
        await client.aclose()
