"""Direct event boundaries on fresh synthetic fixtures, not a recovery/stress matrix."""
import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2.analysis_incident_executor import IncidentTaskPolicy
from app.socai2.baseline_contracts import Limits
from app.socai2.stage_result_contracts import AlertOutput
from app.socai2.stage_results import A, AS, F, I, R
from sqlalchemy import insert, select, update


async def run(ctx):
    service,stage,reader,dispatcher,gateway,ie,tenant,rows,drain,check = [ctx[k] for k in
        ('service','stage','reader','dispatcher','gateway','i_executor','tenant','rows','drain','check')]
    samples={}

    async def submit(iid,intent='check'):
        return await service.submit(tenant,kind='incident_diagnosis',subject_id=iid,intent=intent,source='user',operation_key=uuid4())

    async def detail(iid,receipt):
        return await service.read_task(tenant,'incident',iid,receipt['task_id'])

    async def fixture(count):
        iid=uuid4();aids=[uuid4() for _ in range(count)];mids=[uuid4() for _ in aids]
        async with service.transaction(tenant) as s:
            now=await s.now()
            await s.db.execute(insert(I).values(id=iid,tenant_id=tenant,source_namespace='fusion.v1',source_incident_id=str(iid),title='Synthetic event'))
            for n,(aid,mid) in enumerate(zip(aids,mids)):
                await s.db.execute(insert(A).values(id=aid,tenant_id=tenant,source_namespace='step4.fixture',source_identity_key=str(aid),
                    title='Synthetic process observation',event_time=now,event_time_source='source'))
                await s.db.execute(insert(m.AlertMaterials).values(id=mid,tenant_id=tenant,alert_id=aid,revision=1,
                    raw_json={'process':{'pid':n+1,'command':'inventory.exe'}},detection={'rule_id':'synthetic'},source_scope={},retention={},material_state='complete'))
                await s.db.execute(update(A).where(A.c.id==aid).values(latest_material_id=mid))
                await s.db.execute(insert(m.IncidentAlerts).values(id=uuid4(),tenant_id=tenant,incident_id=iid,alert_id=aid,
                    linked_at=now-timedelta(seconds=count-n),membership_source='fusion',correlation_basis={'reason':'synthetic shared host'},
                    basis_version='synthetic',source_operation_id=uuid4()))
        return iid,aids,mids

    async def state(iid):
        return next(x for x in await rows(m.AnalysisSubjectState) if x['subject_id']==iid)

    async def due(iid):
        # Make only this scheduled check due; stored completion/activity stays real.
        async with service.transaction(tenant) as s:
            await s.db.execute(update(m.AnalysisSubjectState).where(m.AnalysisSubjectState.tenant_id==tenant,
                m.AnalysisSubjectState.subject_id==iid).values(next_check_at=await s.now()))
        return await ie.check_updates(tenant,datetime.now(UTC)+timedelta(seconds=1))

    async def triage(aid,mid):
        limits=Limits(max_model_calls=0,max_tokens=0,max_tool_calls=0,max_rows_per_query=0,deadline_at=None,policy_version='synthetic.late-A')
        claim=await stage.begin(tenant,'alert_basic',aid,uuid4(),producer='synthetic.late-A',limits=limits)
        result=AlertOutput(verdict='needs_review',rationale='Authorization remains unresolved.',confidence=.3,score_state='available',
            explanation='Synthetic late A fixture.',generation_method='template',source_refs=[{'type':'alert_material','id':mid,'external':None,
            'source_path':'$.raw_json.process.pid','row_keys':[],'role':'observation'}],recommendations=[],limitations=[])
        await stage.finish(tenant,claim['run_id'],result)

    # First I with absent A; then an actually saved late A and an identical new A result.
    iid,aids,mids=await fixture(2)
    await submit(iid,'initial');await drain()
    before=len(gateway.calls)
    await triage(aids[0],mids[0]);assert (await due(iid))['submitted']==1
    await drain();assert len(gateway.calls)==before+1
    newpage=await reader.read_page(tenant,'incident_diagnosis',iid)
    frozen=next(x['content_json'] for x in await rows(m.Artifacts) if x['id']==newpage.current.run.input_artifact_id)
    assert frozen['triage_validation'][str(aids[0])]['usable']
    check('late completed A triggers next I and is frozen as prior analysis')
    before=len(gateway.calls)
    async with service.transaction(tenant) as s:
        await s.db.execute(update(A).where(A.c.id==aids[0]).values(tags=['operator-only'],business_updated_at=await s.now()))
        await s.db.execute(update(I).where(I.c.id==iid).values(tags=['operator-event-only']))
    await triage(aids[0],mids[0])
    assert (await due(iid))['submitted']==0
    assert (await reader.read_page(tenant,'incident_diagnosis',iid)).current.valid_for_current_input
    assert len(gateway.calls)==before
    check('operator metadata and identical new A identity/time do not trigger or stale I')
    async with service.transaction(tenant) as s:
        fid=uuid4()
        await s.db.execute(insert(AS).values(id=fid,tenant_id=tenant,alert_id=aids[0],input_material_id=mids[0],kind='human_feedback',
            verdict='benign',rationale='Synthetic operator confirms scheduled inventory.',score_state='not_provided',producer='human',
            actor={'name':'synthetic operator'},assessed_at=await s.now(),operation_key=str(fid)))
        await s.db.execute(update(A).where(A.c.id==aids[0]).values(latest_feedback_id=fid))
    assert (await due(iid))['submitted']==1;await drain()
    check('effective human feedback changes I input without re-triaging members')

    # A running input never expands; a queued input is fetched again just before execution.
    gateway.behaviors[iid]='hold';gateway.entered.clear();gateway.release.clear()
    receipt=await submit(iid,'rerun')
    await dispatcher.tick();await asyncio.wait_for(gateway.entered.wait(),30)
    await ctx['ingress']('running-new-member',iid)
    gateway.release.set();await drain();gateway.behaviors.pop(iid)
    held=await detail(iid,receipt);held_entry=await reader.read_entry(tenant,'incident_diagnosis',iid,held['latest_run_id'])
    assert held_entry.input_selection.selected_count==2 and held_entry.freshness=='stale'
    assert (await due(iid))['submitted']==1;await drain()
    assert (await reader.read_page(tenant,'incident_diagnosis',iid)).current.input_selection.selected_count==3
    receipt=await submit(iid,'check')
    await ctx['ingress']('queued-new-member',iid)
    await drain();queued=await detail(iid,receipt)
    assert queued['status']=='completed'
    assert (await reader.read_entry(tenant,'incident_diagnosis',iid,queued['latest_run_id'])).input_selection.selected_count==4
    check('queued I reads latest members; running I keeps two frozen members and next check covers arrivals')

    # Total members and selected input/actual coverage are independent.
    large,laids,lmids=await fixture(260)
    first=await submit(large,'initial');await drain();large_detail=await detail(large,first)
    page=await reader.read_page(tenant,'incident_diagnosis',large)
    assert page.current.input_selection.total_member_count==260 and page.current.input_selection.selected_count==100
    assert page.current.input_selection.omitted_count==160
    assert page.current.input_selection.selected_alert_ids==list(reversed(laids[-100:]))
    assert page.current.analysis_coverage.state=='partial' and page.current.analysis_coverage.unresolved_count==100
    assert page.current.run.delivery_state=='complete'
    assert len([r for r in await rows(m.IncidentAlerts) if r['incident_id']==large])==260
    await triage(laids[0],lmids[0]);assert (await due(large))['submitted']==0
    samples['partial_coverage']={'incident_id':large,'task_id':first['task_id'],'run_id':large_detail['latest_run_id']}
    check('260 saved event members select latest 100; delivery complete with partial event coverage; omitted A does not trigger')

    # Same-input capacity stops, changed capacity permits one check, original pointer survives.
    old=page.current.result.id
    gateway.behaviors[large]='capacity';receipt=await submit(large,'rerun');before=len(gateway.calls);await drain()
    failed=await detail(large,receipt)
    assert failed['status']=='failed' and failed['reason_code']=='capacity_exceeded' and failed['retry_count']==0
    assert len(gateway.calls)==before
    frozen=next(x for x in await rows(m.Artifacts) if x['run_id']==failed['latest_run_id'] and x['kind']=='model_request')
    assert not frozen['content_json']['preflight_passed'] and frozen['content_json']['body'] and frozen['content_json']['token_measurement']
    assert (await reader.read_page(tenant,'incident_diagnosis',large)).current.result.id==old
    assert (await due(large))['submitted']==0
    samples['capacity_failure']={'incident_id':large,'task_id':receipt['task_id'],'run_id':failed['latest_run_id']}
    # Change capacity while retaining the same selected members: use the 4-member event.
    gateway.behaviors[iid]='capacity';receipt2=await submit(iid,'rerun');await drain()
    assert (await detail(iid,receipt2))['reason_code']=='capacity_exceeded'
    ie.policy=IncidentTaskPolicy(max_alerts_per_diagnosis=101,scan_batch_size=100)
    gateway.behaviors.pop(iid)
    assert (await due(iid))['submitted']==1
    await drain();ie.policy=IncidentTaskPolicy(**ctx['config']['incident'])
    check('capacity failure retains prepared request/meter and prior result, sends no model, stops same config, permits changed config')

    # Close/expiry use the shared lifecycle. No ambiguous model call blocks other objects.
    closed,_,_=await fixture(1);receipt=await submit(closed,'initial')
    async with service.transaction(tenant) as s:
        await s.db.execute(update(I).where(I.c.id==closed).values(handling_status='resolved'))
    await drain();assert (await detail(closed,receipt))['reason_code']=='closed_before_start'
    exp,_,_=await fixture(1);receipt=await submit(exp,'initial')
    async with service.transaction(tenant) as s:
        await s.db.execute(update(I).where(I.c.id==exp).values(created_at=(await s.now())-timedelta(days=8)))
    gateway.behaviors[exp]='connect_timeout';await drain();expired=await detail(exp,receipt)
    assert expired['status']=='failed' and expired['retry_count']==0 and len(expired['attempts'])==1 and expired['reason_code']=='retry_stopped'
    assert (await due(exp))['submitted']==0
    unknown,_,_=await fixture(1);u=await submit(unknown,'initial');gateway.behaviors[unknown]='read_timeout'
    tail,_,_=await fixture(1);t=await submit(tail,'initial');await drain()
    stopped=await detail(unknown,u);tail_detail=await detail(tail,t)
    assert stopped['status']=='failed' and stopped['attempts'][0]['outcome']=='unknown' and stopped['ended_at']
    run=next(r for r in await rows(m.Runs) if r['id']==stopped['latest_run_id']);assert run['state']=='unknown' and run['ended_at'] is None
    assert tail_detail['status']=='completed' and not dispatcher.active and not dispatcher.receipts
    samples['unknown']={'incident_id':unknown,'task_id':u['task_id'],'run_id':stopped['latest_run_id']}
    samples['expired_first_attempt']={'incident_id':exp,'task_id':receipt['task_id'],'run_id':expired['latest_run_id']}
    check('queued closed I skips; accepted first attempt crosses expiry but never retries; unknown releases N=1 for next event')
    ctx['result']['http_boundary_samples']=samples
