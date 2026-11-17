"""Unique D4b component verification. Controlled copies; zero model/Kafka/HTTP.

Uses new tenant/Case/source identities, never edits any old evidence or tenant.
Saved D4a analysis/receipts are dependencies, not newly generated model answers.
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT/'services/api')]
OUT = Path(__file__).parent
MOTHER = ROOT/'docs/operations/evidence/ai-unit-continuation-d4-20261116-01/real-01/database.json'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=lambda v:
        v.model_dump(mode='json') if hasattr(v, 'model_dump') else str(v))+'\n')


def remapped(source):
    from app.socai2.baseline_store import digest, encoded
    raw = json.dumps(source, ensure_ascii=False)
    mapping = {k: str(uuid4()) for k in set(re.findall(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b', raw))}
    for old, new in mapping.items(): raw = raw.replace(old, new)
    value = json.loads(raw)
    for f in value['artifacts']:
        if f['kind']=='input_snapshot' and 'change_view' in f['content_json']:
            f['content_json']['change_view']['members'].sort(key=lambda m:m['alert_id'])
    # Remap the source graph's stored hashes in dependency order, preserving
    # exact answer text/spans. No receiver or validator invents new analysis.
    for _ in range(12):
        hashes={f['sha256']:digest(f['content_json']) for f in value['artifacts'] if f['content_json'] is not None}
        changes={a:b for a,b in hashes.items() if a!=b}
        if not changes: break
        text=json.dumps(value,ensure_ascii=False)
        for old,new in changes.items(): text=text.replace(old,new)
        value=json.loads(text)
        for f in value['artifacts']:
            if f['content_json'] is not None: f['size_bytes']=len(encoded(f['content_json']))
    for a in value['analysis_attempts']:
        f=next(f for f in value['artifacts'] if f['id']==a['input_artifact_id'])
        if 'change_view' in f['content_json']: a['input_digest']=digest(f['content_json']['change_view'])
    return value,mapping


async def main(config, out, scenario, resume=None, capture_only=False):
    from app.models import socai2 as m
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_context import capture, selected_refs
    from app.socai2.baseline_contracts import Actor, Limits, Start
    from app.socai2.baseline_service import BaselineService
    from app.socai2.case_allocation_policy import CaseAllocationPolicy
    from app.socai2.case_model_boundary import build, messages
    from app.socai2.case_update_inputs import business_view, unchanged
    from app.socai2.case_update_scanner import follow_current
    from app.socai2.runtime_policy import active_policy
    from sqlalchemy import insert, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out.mkdir(exist_ok=False)
    cfg=json.loads(Path(config['database_profile']).read_text())
    assert cfg['host']=='127.0.0.1' and cfg['processing_database']=='v12_upgrade_dev'
    url=URL.create('postgresql+psycopg',username=cfg['admin'],password=Path(cfg['password_file']).read_text().strip(),
        host=cfg['host'],port=cfg['port'],database=cfg['processing_database'])
    admin=create_async_engine(url,hide_parameters=True,connect_args={'sslmode':config['sslmode']})
    engine=create_async_engine(url,hide_parameters=True,connect_args={'sslmode':config['sslmode'],'options':'-c role='+cfg['processor']})
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    service=BaselineService(sessions)
    tasks=AnalysisTaskService(sessions,AnalysisTaskPolicy.load())
    source=json.loads(MOTHER.read_text())
    for i in source['incidents']: i['source_namespace']=source['alerts'][0]['source_namespace']
    excluded = set()
    if scenario in {'partial','none'}: excluded.add('75255ae9-8159-5fa4-ae53-af5927e26523')
    if scenario == 'none': excluded.add('7ef7bceb-7c93-5894-bd0c-b0343334050b')
    removed_attempts={r['id'] for r in source['analysis_attempts'] if r['run_id'] in excluded}
    removed_tasks={r['task_id'] for r in source['analysis_attempts'] if r['run_id'] in excluded}
    removed_diagnoses={r['id'] for r in source['incident_diagnoses'] if r['source_run_id'] in excluded}
    for table in ('artifacts','run_steps','analysis_attempts'): source[table]=[r for r in source[table] if r['run_id'] not in excluded]
    source['runs']=[r for r in source['runs'] if r['id'] not in excluded]
    source['analysis_tasks']=[r for r in source['analysis_tasks'] if r['id'] not in removed_tasks]
    source['incident_diagnoses']=[r for r in source['incident_diagnoses'] if r['id'] not in removed_diagnoses]
    for row in source['analysis_subject_state']:
        for key in ('last_attempt_id','last_completed_attempt_id'):
            if row[key] in removed_attempts: row[key]=None
        if row['last_completed_attempt_id'] is None: row['last_normal_completed_at']=None
        if row['stopped_task_id'] in removed_tasks: row['stopped_task_id']=None
    for row in source['incidents']:
        if row['latest_diagnosis_id'] in removed_diagnoses: row['latest_diagnosis_id']=None
    if scenario=='partial':
        # Controlled dependency variation: 4 event members, 3 selected by I,
        # one saved member analysis. This is not a new real model invocation.
        # Preserve the mother request separately; the component request is an
        # explicit unsent fixture. No old request/receipt is modified.
        selected_input=next(f['content_json'] for f in source['artifacts']
            if f['run_id']=='7ef7bceb-7c93-5894-bd0c-b0343334050b' and f['kind']=='input_snapshot')
        omitted=selected_input['members'][-1]['alert']['id']
        for link in source['incident_alerts']:
            if link['alert_id']==omitted: link['linked_at']='2026-11-15 00:00:00+00:00'
        for f in source['artifacts']:
            if f['incident_id'] is None: continue
            body=f['content_json']
            if f['kind']=='input_snapshot':
                body['members']=[r for r in body['members'] if r['alert']['id']!=omitted]
                body['change_view']['members']=[r for r in body['change_view']['members'] if r['alert_id']!=omitted]
                selection=body['input_selection']
                selection.update(limit=3,selected_count=3,omitted_count=1,
                    selected_alert_ids=[a for a in selection['selected_alert_ids'] if a!=omitted])
            elif f['kind']=='model_request':
                body['mother_request_body']=body['body']
                body['body']={'fixture':'unsent D4b dependency; no generation',
                              'selected_alert_ids':[a for a in selected_input['input_selection']['selected_alert_ids'] if a!=omitted]}
                body['member_coverage']=[r for r in body['member_coverage'] if r['alert_id']!=omitted]
    values,mapping=remapped(source)
    if resume:
        values=json.loads((resume/'seed.json').read_text()); mapping=json.loads((resume/'intent.json').read_text())['mapping']
    tenant=UUID(values['incidents'][0]['tenant_id']); iid=UUID(values['incidents'][0]['id'])
    actor=uuid4(); cid=uuid4()
    if resume:
        cid=UUID(json.loads((resume/'intent.json').read_text())['case_id'])
        async with admin.connect() as db:
            actor=(await db.execute(text('SELECT id FROM public.users WHERE tenant_id=:tenant'),{'tenant':tenant})).scalar_one()
    checks=[]; contexts=[]
    if resume and (resume/'result.json').exists():
        checks=json.loads((resume/'result.json').read_text())['checks']
        contexts=json.loads((resume/'captures.json').read_text())
    result={'state':'running','tenant_id':tenant,'incident_id':iid,'case_id':cid,'checks':checks,
        'controlled_saved_dependencies':True,'model_generations':0,'http_requests':0,'redis_tasks_dispatched':0,
        'full_case_execution':False,'deployment':False}
    save(out/'intent.json',{**result,'mother':str(MOTHER.relative_to(ROOT)),
        'mother_sha256':hashlib.sha256(MOTHER.read_bytes()).hexdigest(),'mapping':mapping,
        'policy':active_policy().snapshot()})
    # The original batch has no requested user on its A/I rows. Source copies
    # are isolated fixtures and keep their original terminal states literally.
    try:
        if not resume:
            async with admin.begin() as db:
                await db.execute(text("INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at) VALUES(:id,'D4b component',:slug,'enterprise',true,'{}','{}',now(),now())"),{'id':tenant,'slug':'d4b-'+str(tenant)})
                await db.execute(text("INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at) VALUES(:id,:tenant,:email,'D4b component','!','soc_analyst',true,false,'{}',now(),now())"),{'id':actor,'tenant':tenant,'email':str(actor)+'@example.invalid'})
                await db.execute(text('SET CONSTRAINTS ALL DEFERRED'))
                order=('alerts','alert_materials','alert_objects','incidents','incident_alerts','artifacts',
                       'runs','run_steps','alert_assessments','incident_diagnoses','analysis_tasks',
                       'analysis_attempts','analysis_subject_state')
                for table in order:
                    rows=values[table]
                    assert table in {x.__tablename__ for x in (m.Alerts,m.AlertMaterials,m.AlertObjects,m.AlertAssessments,m.Incidents,m.IncidentAlerts,m.IncidentDiagnoses,m.AnalysisTasks,m.AnalysisAttempts,m.AnalysisSubjectState,m.Runs,m.RunSteps,m.Artifacts)}
                    for original in rows:
                        row=dict(original)
                        if table=='analysis_tasks': row.update(state='running',ended_at=None,next_retry_at=None)
                        await db.execute(text(f'INSERT INTO socai2.{table} SELECT * FROM jsonb_populate_record(NULL::socai2.{table},CAST(:row AS jsonb))'),{'row':json.dumps(row,ensure_ascii=False)})
                    if table=='analysis_attempts':
                        for task in values['analysis_tasks']:
                            await db.execute(text('UPDATE socai2.analysis_tasks SET state=:state,ended_at=CAST(:ended AS timestamptz) WHERE id=:id'),{'state':task['state'],'ended':task['ended_at'],'id':UUID(task['id'])})
        save(out/'seed.json',values)
        aids=[UUID(v['alert_id']) for v in values['incident_alerts']]
        async with service.transaction(tenant) as store:
            exists=await store.one(select(m.Cases.id).where(m.Cases.id==cid))
            if not exists:
                await store.db.execute(insert(m.Cases).values(id=cid,tenant_id=tenant,continuation_root_case_id=cid,
                    receiving_case_id=cid,title='D4b controlled Case',created_by=actor))
                await store.db.execute(insert(m.CaseAlerts).values(id=uuid4(),tenant_id=tenant,case_id=cid,
                    alert_id=aids[0],membership_source='manual',added_by=actor,source_operation_id=uuid4()))
                await store.db.execute(insert(m.CaseIncidents).values(id=uuid4(),tenant_id=tenant,case_id=cid,incident_id=iid,linked_by=actor,source_operation_id=uuid4()))
            await store.db.execute(update(m.Cases).where(m.Cases.id==cid).values(source_namespace=values['alerts'][0]['source_namespace']))
            await store.db.execute(update(m.Incidents).where(m.Incidents.id==iid).values(active_case_id=cid,source_namespace=values['alerts'][0]['source_namespace']))
        async def read_context(label):
            async with service.transaction(tenant,readonly=True) as store:
                cas=await store.case(cid,lock=False)
                ctx=await capture(store.db,tenant,cid,Start(expected_scope_revision=cas['scope_revision'],operation_key=uuid4()))
            contexts.append({'label':label,'context':ctx.model_dump(mode='json')});save(out/'captures.json',contexts)
            return ctx
        ctx=await read_context(scenario+'_selection')
        mat=ctx.incidents[str(iid)].analysis_material
        expected={'complete':'75255ae9-8159-5fa4-ae53-af5927e26523','partial':'7ef7bceb-7c93-5894-bd0c-b0343334050b','none':'3d8b5a17-512d-563d-b34e-6250c3f1bf35'}[scenario]
        assert mat and mat['source_run_id']==mapping[expected]
        checks.append(scenario+'_selection_over_later_empty_failure')

        if not capture_only and 'receiptless_failure_does_not_replace_valid_material' not in checks:
            # Use a genuine accepted/start_attempt boundary for the running gate.
            accepted=await tasks.submit(tenant,kind='incident_diagnosis',subject_id=iid,intent='rerun',source='user',operation_key=uuid4())
            async with tasks.transaction(tenant) as store:
                attempt=await store.start_attempt(accepted['task_id'])
            ctx_running=await read_context('current_attempt_running')
            assert ctx_running.incidents[str(iid)].analysis_material is None
            checks.append('running_attempt_blocks_material')
            async with tasks.transaction(tenant) as store:
                await store.finish_attempt(attempt['id'],outcome='failed',error_code='service_unavailable',retryable=True)
            ctx_retry=await read_context('legal_retry_waiting')
            assert ctx_retry.incidents[str(iid)].analysis_material is None
            checks.append('legal_retry_blocks_material')
            async with tasks.transaction(tenant) as store:
                await store.stop_retry(await store.task(accepted['task_id']),'component_fixture_finished',await store.now())
            restored=await read_context('no_new_receipt_old_complete_retained')
            assert restored.incidents[str(iid)].analysis_material['source_run_id']==mat['source_run_id']
            checks.append('receiptless_failure_does_not_replace_valid_material')

        executor=SimpleNamespace(service=service,task_service=tasks,allocation_policy=CaseAllocationPolicy.load())
        receipts=await follow_current(executor,tenant,cid,automatic=True)
        full=await read_context('all_incident_members_allocated')
        assert set(full.alerts)==set(map(str,aids))
        checks.append('allocation_uses_all_event_members')
        if scenario=='partial':
            assert len(aids)==4 and len(mat['input_selection']['selected_alert_ids'])==3 and len(mat['units'])==1
            checks.append('four_event_members_three_selected_one_retained_all_four_allocated')
        save(out/'allocation.json',receipts)

        # Store an actual C1 via the current claim boundary. No C3/C6 model or
        # Result is generated. End this component-only Run explicitly failed.
        rid=uuid4()
        async with service.transaction(tenant) as store:
            cas=await store.case(cid)
            now=await store.now()
            await store.db.execute(insert(m.Runs).values(id=rid,tenant_id=tenant,case_id=cid,kind='baseline',title='D4b C1 only',purpose='component capture only; no model execution',trigger='manual',state='pending_update',scope_revision=cas['scope_revision'],scope_kind='whole_case',scope_updated_at=now,requested_at=now,requested_by=actor))
            await store.claim(cid,rid,Start(expected_scope_revision=cas['scope_revision'],operation_key=uuid4()),
                actor=Actor(user_id=actor,name='D4b component'),executor_version='component.d4b',
                limits=Limits(max_model_calls=0,max_tokens=0,max_tool_calls=0,max_rows_per_query=0,deadline_at=None,policy_version='component.d4b'),
                update_context={'comparison_context':{},'capacity_profile':{},'version':'socai2.case-update-input.v1'})
        frozen=await service.read_context(tenant,cid,rid)
        assert frozen.incidents[str(iid)].analysis_material==full.incidents[str(iid)].analysis_material
        save(out/'frozen-context.json',frozen)
        refs=selected_refs(frozen)
        assert mat['receipt_source']['id'] in {r['id'] for r in refs}
        checks.append('c1_save_read_and_selected_source_refs')
        async with service.transaction(tenant,readonly=True) as store:
            arts=[dict(r) for r in (await store.db.execute(select(m.Artifacts.__table__).where(m.Artifacts.tenant_id==tenant,m.Artifacts.run_id==rid))).mappings()]
            materials={aid:dict(await store.one(select(m.AlertMaterials.__table__).where(m.AlertMaterials.id==UUID(v.material['id'])))) for aid,v in frozen.alerts.items()}
        context_art=next(f for f in arts if f['schema_version']=='socai2.baseline-context.v1')
        prepared=build(frozen,str(context_art['id']),[],[],materials,execution_time=frozen.captured_at.isoformat(),run_id=str(rid))
        assert prepared['ready'],prepared.get('reason')
        request=messages(prepared,frozen,[])
        save(out/'c3-prepared.json',prepared);save(out/'c3-messages.json',request);save(out/'case-artifacts.json',arts)
        raw=json.dumps(request,ensure_ascii=False)
        for key in ('receipt_source','local_ended_at','attempt_id','input_digest','tenant_uid'):
            assert key not in raw,key
        retained=[r for r in prepared['input_ledger']['records'] if '.analysis_material.units.' in r['ref'].get('source_path','')]
        assert bool(retained)==(scenario!='none')
        assert all(r['ref']['role']=='prior_analysis' for r in retained)
        if scenario=='partial':
            assert len(retained)==1 and len(retained[0]['alert_ids'])==1
            assert mat['units'][0]['value']['assessment'] in raw
        checks.append('current_profile_c3_actual_business_messages_no_ledger')
        assert unchanged(frozen,business_view(full),{str(iid)})
        checks.append('same_saved_signal_unchanged')
        async with service.transaction(tenant) as store:
            await store.db.execute(update(m.Runs).where(m.Runs.id==rid).values(state='failed',ended_at=await store.now(),stop_reason='component_capture_only',row_version=m.Runs.row_version+1))
        # A newly attached alert makes these frozen I receipts stale. Reading
        # the saved C1 must still return exactly the previously selected I.
        extra=uuid4()
        async with service.transaction(tenant) as store:
            await store.db.execute(insert(m.Alerts).values(id=extra,tenant_id=tenant,title='new original alert',source_namespace=values['alerts'][0]['source_namespace'],source_identity_key=str(extra)))
            await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(),tenant_id=tenant,incident_id=iid,alert_id=extra,
                membership_source='manual',correlation_basis={'test':'new material'},basis_version='v1',source_operation_id=uuid4()))
        stale=await read_context('new_alert_old_i_is_stale')
        assert stale.incidents[str(iid)].analysis_material is None
        assert (await service.read_context(tenant,cid,rid)).incidents[str(iid)].analysis_material==frozen.incidents[str(iid)].analysis_material
        assert await follow_current(executor,tenant,cid,automatic=True)==[]
        checks.append('new_input_stale_does_not_allocate_and_c1_remains_frozen')
        result.update(state='passed',case_run_id=rid,source_run_id=mat['source_run_id'])
    except Exception:  # noqa: BLE001 -- retain the original component failure
        result.update(state='failed',error=traceback.format_exc())
    finally:
        if 'rid' in locals():
            async with service.transaction(tenant) as store:
                await store.db.execute(update(m.Runs).where(m.Runs.id==rid,m.Runs.state=='running').values(
                    state='failed',ended_at=await store.now(),stop_reason='component_capture_only',row_version=m.Runs.row_version+1))
        result['checks']=list(dict.fromkeys(checks))
        save(out/'captures.json',contexts);save(out/'result.json',result)
        await engine.dispose();await admin.dispose()
    print(json.dumps({'state':result['state'],'checks':len(checks),'directory':str(out)}))
    if result['state']!='passed': raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);parser.add_argument('--scenario',choices=['complete','partial','none'],required=True);parser.add_argument('--resume');parser.add_argument('--capture-only',action='store_true')
    args=parser.parse_args();config=json.loads(Path(args.config).read_text())
    os.environ.update(json.loads(Path(config['environment_file']).read_text()))
    os.environ.update(config['runtime_overrides'])
    for env,key in [('SOCAI2_INVESTIGATION_POLICY','investigation_policy_file'),('SOCAI2_ANALYSIS_TASKS_CONFIG_FILE','lifecycle_policy_file'),('SOCAI2_CASE_ALLOCATION_CONFIG_FILE','allocation_policy_file')]:os.environ[env]=config[key]
    asyncio.run(main(config,Path(args.output),args.scenario,Path(args.resume) if args.resume else None,args.capture_only))
