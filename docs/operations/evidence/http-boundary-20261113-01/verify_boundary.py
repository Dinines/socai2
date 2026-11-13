"""One scoped candidate check, reusing the new Case/H batch; no real model calls."""
import asyncio,json,os,sys,urllib.request,urllib.error
from pathlib import Path
from uuid import UUID,uuid4
root=Path('/Users/lychee/Documents/project/socai2')
out=root/'docs/operations/evidence/http-boundary-20261113-01'
cfg=json.loads((root/'deploy/http-service/http-boundary/verify-local.json').read_text())
fixture=json.loads((out/'fixture.json').read_text())
case=json.loads((out/'case-task-http/verification.json').read_text())
credential=json.loads((root/cfg['credential']['file']).read_text())
records=[]
def call(method,path,body=None,expected=200):
    intent={'method':method,'path':path,'input':body}
    (out/f'boundary-{len(records)+1:02}-intent.json').write_text(json.dumps(intent,indent=2)+'\n')
    request=urllib.request.Request(cfg['base_url']+path,method=method,data=json.dumps(body).encode() if body else None,
        headers={'Authorization':'Bearer '+credential['api_key'],'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=cfg['timeout_seconds']) as r: status,payload=r.status,json.load(r)
    except urllib.error.HTTPError as e: status,payload=e.code,json.load(e)
    records.append({**intent,'status':status,'body':payload})
    (out/'boundary-responses.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    assert status==expected,(status,payload)
    return payload
prefix='/api/v1/socai2'
for p in ['/alerts?limit=1','/incidents?limit=1','/cases?limit=1']:
    assert len(call('GET',prefix+p)['items'])==1
alert=prefix+'/alerts/'+fixture['alerts'][0]
original=call('GET',alert)
feedback=call('POST',alert+'/feedback',{'operation_key':str(uuid4()),'expected_row_version':original['facts']['row_version'],
    'disposition':'needs_review','reason':'SYNTHETIC HTTP boundary readback; not a security conclusion'})
alert_final=call('GET',alert)
assert alert_final['facts']['latest_feedback_id']==feedback['feedback_id']
assert alert_final['facts']['latest_triage_id']==original['facts']['latest_triage_id']
incident=prefix+'/incidents/'+fixture['incidents'][0]
i=call('GET',incident)
changed=call('PATCH',incident+'/management',{'operation_key':str(uuid4()),'expected_row_version':i['facts']['row_version'],'handling_status':'in_progress'})
incident_final=call('GET',incident)
assert incident_final['facts']==changed['facts']
cp=prefix+'/cases/'+case['case_id']
view=call('GET',cp+'/management')
updated=call('PATCH',cp+'/management',{'operation_key':str(uuid4()),'expected_row_version':view['case']['row_version'],
    'title':'SYNTHETIC separated external HTTP adapter'})
closed=call('POST',cp+'/close',{'operation_key':str(uuid4()),'expected_row_version':updated['case']['row_version'],'reason':'SYNTHETIC adapter verification'})
assert closed['case']['handling_status']=='resolved'
reopened=call('POST',cp+'/reopen',{'operation_key':str(uuid4()),'expected_row_version':closed['case']['row_version'],'reason':'SYNTHETIC adapter verification'})
case_final=call('GET',cp)
assert case_final['case']==reopened['case'] and reopened['case']['handling_status']=='in_progress'
# A stale application error still has its exact external HTTP status/code.
assert call('PATCH',cp+'/management',{'operation_key':str(uuid4()),'expected_row_version':view['case']['row_version'],'title':'stale'},409)['detail']=='case_row_version_conflict'
os.environ.update(json.loads((root/'.local/subject-management-20261112-01/environment.json').read_text()))
sys.path[:0]=[str(root/'services/api'),str(root/'services/api/tests')]
from sqlalchemy import select,text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.db.database import _normalize_async_pg_url
from app.models import socai2 as m
from app.socai2.baseline_service import BaselineService
from app.socai2.case_contracts import CaseView,project
from app.socai2.page_contracts import AlertFacts,IncidentFacts
from test_socai2_stage_execution_api import run_checks
async def verify():
    url=os.environ['SOCAI2_CASE_DATABASE_URL'];assert make_url(url).database==cfg['database']
    url,args=_normalize_async_pg_url(url);engine=create_async_engine(url,connect_args=args)
    checks=[]
    try:
        service=BaselineService(async_sessionmaker(engine,expire_on_commit=False))
        async with service.transaction(UUID(fixture['tenant_id']),readonly=True) as store:
            assert (await store.db.execute(text('SELECT current_database()'))).scalar_one()==cfg['database']
            for table,model,expected in [(m.Alerts.__table__,AlertFacts,alert_final['facts']),
                    (m.Incidents.__table__,IncidentFacts,incident_final['facts']),
                    (m.Cases.__table__,CaseView,case_final['case'])]:
                row=await store.one(select(table).where(*store.where(table,table.c.id==UUID(expected['id']))))
                assert project(model,row).model_dump(mode='json')==expected
            task=await store.one(select(m.Tasks.__table__).where(m.Tasks.id==UUID(case['task_id'])))
            assert str(task['current_revision_id'])==case['current_revision_id']
            rev=await store.one(select(m.TaskRevisions.__table__).where(m.TaskRevisions.id==task['current_revision_id']))
            assert rev['state']=='completed' and rev['result_text']
            run=await store.one(select(m.Runs.__table__).where(m.Runs.id==UUID(case['run_id'])))
            assert run['state']=='pending_update' and run['started_at'] is None
        def record(name,ok,error=None): checks.append({'check':name,'passed':ok,**({'error':error} if error else {})})
        await run_checks(engine,record)
        (out/'stage-asgi-pg.json').write_text(json.dumps(checks,indent=2)+'\n')
        assert checks and all(c['passed'] for c in checks)
        summary={'state':'passed','transport':'TCP HTTP + actual PostgreSQL; A/I ASGI with unavailable-model substitute',
            'database':cfg['database'],'http_requests':len(records)+case['requests'],'http_errors_expected':[409,501],
            'sql_facts_equal':['alert','incident','case'],'task_revision_and_pending_run_equal':True,
            'stage_checks':len(checks),'real_model_calls':0,'candidate_only':True}
        (out/'functional-check.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
    finally: await engine.dispose()
asyncio.run(verify())
