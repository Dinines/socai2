"""Isolated admission checks for I/Case; execution is verified in separate batches."""
import json
import os
import traceback
from pathlib import Path
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_contracts import Actor
from app.socai2.baseline_store import digest
from app.socai2.case_management import manage_case, read_management
from app.socai2.case_management_contracts import CaseLifecycleRequest
from app.socai2.case_service import CaseService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.analysis_submissions import AnalysisSubmissionBackend
from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.analysis_submission_contracts import AnalysisTaskReceipt
from investigation_http.dependencies import (
    analysis_submission_service,
    analysis_task_service,
)
from investigation_http.external_routes import analysis_submissions, analysis_tasks
from investigation_http.main import app as public_app
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker

TENANT, ACTOR = UUID(int=1), UUID(int=3)


def contract_app():
    app = FastAPI(title="Isolated asynchronous Incident/Case admission contract")
    app.include_router(analysis_submissions.case_router, prefix="/api/v1")
    app.include_router(analysis_submissions.incident_router, prefix="/api/v1")
    app.include_router(analysis_tasks.router, prefix="/api/v1")
    return app


async def run_checks(engine, record, only=None):
    if only and "analysis_submission_preparation" not in only:
        return
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    policy = AnalysisTaskPolicy(**json.loads((Path(__file__).resolve().parents[3] /
        "deploy/local-investigation/analysis-tasks.json").read_text()))
    service = AnalysisTaskService(sessions, policy)
    writer, reader = AnalysisSubmissionBackend(sessions, policy=policy), AnalysisTaskBackend(sessions, policy=policy)
    aid, cases, incidents = uuid4(), [uuid4() for _ in range(4)], [uuid4() for _ in range(2)]
    subjects = [aid, *cases, *incidents]
    calls, receipts = [], []
    app = contract_app()
    app.state.business_context = BusinessContext(TENANT, ACTOR, "Synthetic submitter")
    app.dependency_overrides[analysis_submission_service] = lambda: writer
    app.dependency_overrides[analysis_task_service] = lambda: reader
    old_policy = os.environ.get("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE")

    async def fixture():
        async with service.transaction(TENANT) as store:
            await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=TENANT,
                source_namespace="analysis-submit-preparation-20261114", source_identity_key=str(aid), title="Admission fixture"))
            for n, cid in enumerate(cases):
                await store.db.execute(insert(m.Cases).values(id=cid, tenant_id=TENANT, title="Admission fixture"))
                if n != 2:
                    await store.db.execute(insert(m.CaseAlerts).values(id=uuid4(), tenant_id=TENANT,
                        case_id=cid, alert_id=aid, membership_source="manual", source_operation_id=uuid4()))
            for n, iid in enumerate(incidents):
                await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=TENANT,
                    source_namespace="analysis-submit-preparation-20261114", source_incident_id=str(iid), title="Admission fixture"))
                if n == 0:
                    await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=TENANT,
                        incident_id=iid, alert_id=aid, membership_source="manual", correlation_basis={},
                        basis_version="synthetic.v1", source_operation_id=uuid4()))
        case_service = CaseService(sessions)
        view = await read_management(case_service, TENANT, cases[3])
        await manage_case(case_service, TENANT, cases[3], CaseLifecycleRequest(operation_key=uuid4(),
            expected_row_version=view.case.row_version), Actor(user_id=ACTOR, name="Synthetic submitter"), action="case_closed")

    async def saved():
        async with service.transaction(TENANT, readonly=True) as store:
            result = {}
            for model in (m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState):
                table = model.__table__
                rows = (await store.db.execute(select(table).where(*store.where(table, table.c.subject_id.in_(subjects)))
                    .order_by(table.c.subject_id))).mappings()
                result[table.name] = [dict(row) for row in rows]
            run_table = m.Runs.__table__
            result['run_ids'] = list((await store.db.execute(select(run_table.c.id).where(*store.where(run_table,
                (run_table.c.case_id.in_(cases)) | (run_table.c.incident_id.in_(incidents)))))).scalars())
            retained = {}
            for model, field in ((m.Alerts, m.Alerts.id), (m.Cases, m.Cases.id), (m.Incidents, m.Incidents.id),
                                 (m.CaseAlerts, m.CaseAlerts.case_id), (m.IncidentAlerts, m.IncidentAlerts.incident_id),
                                 (m.Tasks, m.Tasks.case_id)):
                table = model.__table__
                rows = (await store.db.execute(select(table).where(*store.where(table, field.in_(subjects)))
                    .order_by(table.c.id))).mappings()
                values = [dict(row) for row in rows]
                retained[table.name] = {'count':len(values), 'sha256':digest(json.loads(json.dumps(values, default=str)))}
            result['retained'] = retained
            return result

    try:
        await fixture()
        before = await saved()
        assert not before['analysis_tasks'] and not before['run_ids']
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
            async def post(url, body, status=202, code=None):
                response = await client.post(url, json=body)
                data = response.json()
                calls.append({'method':'POST', 'url':url, 'input':body, 'status':response.status_code, 'body':data})
                assert response.status_code == status, calls[-1]
                if code:
                    assert data['detail']['code'] == code, data
                if status == 202:
                    AnalysisTaskReceipt.model_validate(data)
                return data

            async def get(url):
                response = await client.get(url)
                data=response.json()
                calls.append({'method':'GET', 'url':url, 'status':response.status_code, 'body':data})
                assert response.status_code == 200, calls[-1]
                return data

            case_url=f'/api/v1/socai2/cases/{cases[0]}/investigations'
            incident_url=f'/api/v1/socai2/incidents/{incidents[0]}/diagnose'
            case_body={'operation_key':str(uuid4()), 'mode':'check'}
            incident_body={'operation_key':str(uuid4()), 'mode':'rerun'}
            for url, body, kind in ((case_url, case_body, 'case'), (incident_url, incident_body, 'incident')):
                receipt=await post(url, body)
                assert await post(url, body) == receipt
                detail=await get(receipt['status_url'])
                assert detail['status']=='accepted' and detail['intent']==body['mode'] and detail['subject_type']==kind
                assert detail['latest_run_id'] is None and not detail['attempts'] and not detail['results']
                receipts.append(receipt)
            await post(case_url,{**case_body,'mode':'rerun'},409,'operation_conflict')
            await post(f'/api/v1/socai2/cases/{cases[1]}/investigations',case_body,409,'operation_conflict')
            await post(f'/api/v1/socai2/cases/{cases[2]}/investigations',case_body,409,'operation_conflict')
            await post(f'/api/v1/socai2/cases/{cases[2]}/investigations',{'operation_key':str(uuid4()),'mode':'check'},409,'empty_scope')
            await post(f'/api/v1/socai2/incidents/{incidents[1]}/diagnose',{'operation_key':str(uuid4()),'mode':'check'},409,'empty_scope')
            await post(f'/api/v1/socai2/cases/{cases[3]}/investigations',{'operation_key':str(uuid4()),'mode':'rerun'},409,'subject_closed')
            await post(f'/api/v1/socai2/cases/{uuid4()}/investigations',{'operation_key':str(uuid4()),'mode':'check'},404,'subject_not_found')
            await post('/api/v1/socai2/cases/not-a-uuid/investigations',case_body,422)
            for body in ({'operation_key':str(uuid4())}, {'mode':'check'}, {'operation_key':'bad','mode':'check'},
                         {'operation_key':str(uuid4()),'mode':'initial'}, {**case_body,'source':'periodic'},
                         {**case_body,'submitted_by':str(uuid4())}, {**case_body,'window_start':'2026-11-14T00:00:00Z'},
                         {**case_body,'mode':None}):
                await post(case_url,body,422)
            await post(case_url+'?extra=yes',case_body,422,'invalid_input')
            async with service.transaction(TENANT) as store:
                await store.skip(UUID(receipts[0]['task_id']), 'no_changes')
            assert await post(case_url,case_body)==receipts[0]
            assert (await get(receipts[0]['status_url']))['status']=='skipped'
            app.dependency_overrides.pop(analysis_submission_service)
            os.environ.pop('SOCAI2_ANALYSIS_TASKS_CONFIG_FILE',None)
            await post(case_url,case_body,503,'service_unavailable')
        after=await saved()
        assert len(after['analysis_tasks'])==2 and len(after['analysis_subject_state'])==2
        assert not after['analysis_attempts'] and not after['run_ids']
        assert after['retained']==before['retained']
        for task in after['analysis_tasks']:
            assert task['submitted_by']==ACTOR and task['source']=='user' and task['request_payload']=={}
        schema=public_app.openapi()
        assert '202' in schema['paths']['/api/v1/socai2/cases/{case_id}/investigations']['post']['responses']
        assert '202' in schema['paths']['/api/v1/socai2/incidents/{incident_id}/diagnose']['post']['responses']
        assert '/api/v1/socai2/cases/{case_id}/baseline/prepare' not in schema['paths']
        assert '/api/v1/socai2/cases/{case_id}/runs/{run_id}/start' not in schema['paths']
        assert 'securitySchemes' not in app.openapi().get('components',{})
        record('analysis_submission_preparation', True, {'boundary':'isolated ASGI admission only; no dispatch/execution acceptance',
            'public_routes_activated':{'incident':True,'case':True}, 'receipts':receipts, 'calls':calls, 'before':before, 'after':after,
            'model_calls':0, 'tool_calls':0, 'redis_calls':0})
    except Exception:  # noqa: BLE001 -- preserve each failed test batch
        record('analysis_submission_preparation',False,{'trace':traceback.format_exc(),'calls':calls})
    finally:
        if old_policy is None:
            os.environ.pop('SOCAI2_ANALYSIS_TASKS_CONFIG_FILE',None)
        else:
            os.environ['SOCAI2_ANALYSIS_TASKS_CONFIG_FILE']=old_policy
