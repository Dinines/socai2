"""Review-only direct regressions; SDK uses MockTransport, all stores explicit doubles.

This file is an unexecuted candidate. These are delivery/effect guards, never
classification-quality tests or provider/model calls.
"""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import httpx
import pytest

from app.agents import auto_triage_agent as agent
from app.core import cost_telemetry
from app.core.cost_governor import CostGovernor, BudgetConfig
from app.llm import contract
from app.llm.factory import make_chat_model
from app.workers import fused_alert_consumer as worker_module, triage_admission as admission, triage_budget as budget
from app.workers import shadow_mode

TENANT='11111111-1111-1111-1111-111111111111'
ALERT='22222222-2222-2222-2222-222222222222'
ADVICE={'verdict':'false_positive','confidence':.95,'rationale':'Unreviewed transport fixture suggestion.'}


def message():
    return {'id':ALERT,'alert_row_id':ALERT,'tenant_id':TENANT,
        'incident_id':'33333333-3333-3333-3333-333333333333',
        'alert':{'id':ALERT,'tenant_id':TENANT,'title':'Review delivery fixture','source':'c03-review-unit',
            'severity':'medium','source_event_ids':['review-first'],'raw_event':{},'description':'Synthetic guard fixture.'}}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv(admission.ENV,admission.REVIEW_ONLY)
    monkeypatch.setenv('AISOC_DETERMINISTIC','0')
    # Turn every effect ON: policy guards, not these flags, must prevent them.
    for key in ('AISOC_AGENT_MEMORY_SUPPRESSION','AISOC_AGENT_MEMORY_WRITEBACK','AISOC_AGENT_RAISE_APPROVALS',
                'AISOC_AGENT_ESCALATE_TO_GRAPH','AISOC_ALERT_PLAYBOOKS_ENABLED'):
        monkeypatch.setenv(key,'1')
    monkeypatch.setenv('LLM_GATEWAY_URL','http://127.0.0.1.invalid/v1')
    monkeypatch.setenv('LITELLM_MASTER_KEY','synthetic-offline-key')
    monkeypatch.setenv('AISOC_GATEWAY_COST_TRUST','0')  # No measured-dollar claim.
    for key in ('OPENAI_BASE_URL','LLM_BASE_URL'):
        monkeypatch.delenv(key,raising=False)
    monkeypatch.setattr(contract,'_RESPONSE_CACHE_ENABLED',False)
    monkeypatch.setattr(contract.egress_privacy,'_FORCE','0')
    monkeypatch.setattr(cost_telemetry,'_flush_to_db',AsyncMock())
    monkeypatch.setattr(agent.closure_policy,'decide',AsyncMock(return_value=agent.closure_policy.ClosureDecision(
        allowed=True,threshold=.5,reason='unit would close',source='unit')))
    monkeypatch.setattr(agent,'_sample_for_qa',AsyncMock())
    monkeypatch.setattr(worker_module,'_RETRY_BACKOFF_S',0)


def sdk_response():
    return httpx.Response(200,json={'id':'review-unit','object':'chat.completion','created':1,'model':'unit',
        'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(ADVICE)},'finish_reason':'stop'}],
        'usage':{'prompt_tokens':11,'completion_tokens':7,'total_tokens':18}})


@pytest.mark.parametrize('shadow',[False,True])
@pytest.mark.asyncio
async def test_actual_sdk_warm_and_cold_review_never_invokes_effects(monkeypatch,shadow):
    governor=CostGovernor(config=BudgetConfig(soft_usd=50,hard_usd=100))
    monkeypatch.setattr(worker_module,'get_governor',lambda:governor)
    lookup,claim=AsyncMock(return_value=None),AsyncMock(return_value=None)
    monkeypatch.setattr(worker_module.triage_delivery,'lookup',lookup)
    monkeypatch.setattr(worker_module.triage_delivery,'claim',claim)
    policy=budget.Policy(3600,3,60000,2)
    monkeypatch.setattr(budget,'policy_for',Mock(return_value=policy))
    updates=AsyncMock();monkeypatch.setattr(budget,'_update',updates)
    monkeypatch.setattr(worker_module,'resolve_llm_config',AsyncMock(return_value=SimpleNamespace(
        allowed=True,api_key='synthetic-unit',base_url=None,model='unit',
        api_key_from_tenant=False,base_url_from_tenant=False,model_from_tenant=False)))
    reader=SimpleNamespace(fetch_organisation_memory=AsyncMock(return_value={'status':'not_requested','statements':[]}))
    worker=worker_module.FusedAlertTriageWorker(bootstrap_servers='unused',context_reader=reader,max_attempts=2)
    writer=worker._writer
    if shadow:
        writer=shadow_mode.ShadowModeTriageWriter(writer,shadow_mode.ShadowDecision(
            tenant_ref=TENANT,alert_class='unit',alert_id=ALERT))
    worker._sink_for=AsyncMock(return_value=writer)
    for name in ('_attach_tenant_skill','_attach_runbooks','_attach_recent_dispositions','_attach_identity_context'):
        setattr(worker,name,AsyncMock())
    forbidden=[]
    for name in ('_maybe_suppress_from_memory','_maybe_escalate','_raise_approvals','_write_back_to_source'):
        mock=AsyncMock(side_effect=AssertionError('Forbidden review-only effect'))
        setattr(worker,name,mock);forbidden.append(mock)
    trigger=AsyncMock(side_effect=AssertionError('No playbook preview or execution'))
    monkeypatch.setattr(worker_module.alert_trigger,'run_for_alert',trigger)
    prior=AsyncMock(side_effect=AssertionError('No outcome memory write'))
    monkeypatch.setattr(type(writer),'record_outcome',prior)
    # Fail persistence once after the actual SDK reply. Warm retry must save
    # the same first result rather than re-enter the SDK or spend loop.
    persist=AsyncMock(side_effect=[worker_module.ledger_module.LedgerPersistError('unit confirmation lost'),True])
    monkeypatch.setattr(worker_module.ledger_module,'persist_auto_triage',persist)
    shadow_record=AsyncMock(return_value=True)
    monkeypatch.setattr(shadow_mode,'record_shadow_decision',shadow_record)
    class_counts={key:agent._metrics[key] for key in ('fp_count','btp_count','tp_count','benign_count')}
    requests=[]
    async def transport(request):
        requests.append(json.loads(request.content));return sdk_response()
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        model=make_chat_model('triage',max_tokens=512,json_output=True,http_async_client=client)
        monkeypatch.setattr(agent,'make_chat_model',lambda *args,**kwargs:model)
        assert await worker._process_with_retry(message()) is True
        assert len(requests)==1 and updates.await_count==2 and claim.await_count==1
        assert claim.await_args.kwargs['budget']==policy
        assert governor.spent_tokens(TENANT)==18
        fields=deepcopy(persist.await_args_list[-1].kwargs)
        receipt=fields['triage_admission_receipt'];projection=fields['recovery_projection']
        assert fields['verdict']=='needs_review' and fields['confidence']==0 and fields['auto_closed'] is False
        assert receipt['model_advice']['verdict']=='false_positive' and receipt['model_advice']['confidence']==.95
        assert receipt['effective_decision']['confidence'] is None and receipt['review_status']=='unreviewed'
        assert receipt['effective_decision']['review_required'] is True
        assert fields['proposed_actions']==[] and fields['llm_exchanges'][0]['response']==json.dumps(ADVICE)
        assert projection['triage_admission']==receipt and worker._pending()=={}
        assert persist.await_args_list[0].kwargs==persist.await_args_list[1].kwargs
        # Fresh process-equivalent worker with completed PG result: no model,
        # writer/reader selection, new claim, effects or new persistence.
        cold=worker_module.FusedAlertTriageWorker(bootstrap_servers='unused')
        cold._sink_for=AsyncMock(side_effect=AssertionError('Cold recovery must precede sources'))
        lookup.return_value=deepcopy(projection)
        lookup.return_value.update(reused_persisted=True,persisted_artifacts=[
            {'kind':'llm_response','sha256':receipt['model_advice']['raw_response_sha256']}])
        assert await cold._process_with_retry(message()) is True
        cold._sink_for.assert_not_awaited()
        assert len(requests)==1 and claim.await_count==1 and persist.await_count==2
        # The old delivery parser proved the artifact itself; the new profile
        # must additionally bind its advice hash to that exact first response.
        lookup.return_value['persisted_artifacts'][0]['sha256']='0'*64
        with pytest.raises(budget.BudgetHold):await cold._process_with_retry(message())
        assert len(requests)==1 and persist.await_count==2
    agent.closure_policy.decide.assert_not_awaited();agent._sample_for_qa.assert_not_awaited()
    trigger.assert_not_awaited();prior.assert_not_awaited()
    for mock in forbidden:mock.assert_not_awaited()
    assert shadow_record.await_count==int(shadow)
    assert {key:agent._metrics[key] for key in class_counts}==class_counts


@pytest.mark.asyncio
async def test_legacy_default_still_runs_original_auto_close_and_qa(monkeypatch):
    monkeypatch.delenv(admission.ENV)
    state=worker_module.build_state(message())
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:sdk_response())) as client:
        model=make_chat_model('triage',max_tokens=512,json_output=True,http_async_client=client)
        monkeypatch.setattr(agent,'make_chat_model',lambda *args,**kwargs:model)
        result=await agent.run_auto_triage(state)
    assert result.triage_admission is None and result.verdict=='false_positive' and result.confidence==.95
    assert result.status is agent.AgentStatus.COMPLETED
    agent.closure_policy.decide.assert_awaited_once();agent._sample_for_qa.assert_awaited_once()


@pytest.mark.asyncio
async def test_profile_actually_denies_direct_and_replay_before_reads_or_models(monkeypatch):
    lookup=AsyncMock();monkeypatch.setattr(worker_module.triage_delivery,'lookup',lookup)
    for writer in (None,object()):
        worker=worker_module.FusedAlertTriageWorker(bootstrap_servers='unused',writer=writer)
        with pytest.raises(budget.BudgetHold):
            if writer is None:await worker.triage(message())
            else:await worker._process_with_retry(message())
    with pytest.raises(admission.ReviewOnlyHold):await agent.run_auto_triage(worker_module.build_state(message()))
    lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_old_completed_result_unknown_and_explicit_suppression_are_holds(monkeypatch):
    lookup=AsyncMock(return_value={'verdict':'false_positive','confidence':.95})
    monkeypatch.setattr(worker_module.triage_delivery,'lookup',lookup)
    claim=AsyncMock();monkeypatch.setattr(worker_module.triage_delivery,'claim',claim)
    worker=worker_module.FusedAlertTriageWorker(bootstrap_servers='unused')
    worker._sink_for=AsyncMock(side_effect=AssertionError('No persistence or source access'))
    with pytest.raises(budget.BudgetHold):await worker._process_with_retry(message())
    lookup.side_effect=worker_module.ledger_module.LedgerPersistError('Original started/unknown')
    with pytest.raises(budget.BudgetHold):await worker._process_with_retry(message())
    lookup.side_effect=None;lookup.return_value=None
    worker._business_context=SimpleNamespace(apply_for_tenant=AsyncMock(return_value=SimpleNamespace(
        suppressed=True,matched_rule_ids=['policy'],provenance={})))
    with pytest.raises(budget.BudgetHold):await worker._process_with_retry(message())
    worker._sink_for.assert_not_awaited();claim.assert_not_awaited()


@pytest.mark.asyncio
async def test_original_boolean_confidence_cannot_be_admitted_as_numeric_one(monkeypatch):
    original={'verdict':'false_positive','confidence':True,'rationale':'Original boolean must hold.'}
    state=worker_module.build_state(message())
    state.record_llm_exchange(agent='auto_triage',purpose='triage.classify',model='unit',
        prompt=[{'role':'user','content':'Fixture.'}],response=json.dumps(original),duration_ms=1)
    normalized={**original,'confidence':1.0}
    with pytest.raises(admission.ReviewOnlyHold):admission.enforce(state,advice=normalized)
    assert state.triage_admission is None


@pytest.mark.parametrize('answered',[False,True])
@pytest.mark.asyncio
async def test_started_unknown_or_invalid_original_reply_holds_without_reentry(monkeypatch,answered):
    governor=CostGovernor(config=BudgetConfig(soft_usd=50,hard_usd=100))
    monkeypatch.setattr(worker_module,'get_governor',lambda:governor)
    monkeypatch.setattr(worker_module.triage_delivery,'lookup',AsyncMock(return_value=None))
    claim=AsyncMock(return_value=None);monkeypatch.setattr(worker_module.triage_delivery,'claim',claim)
    monkeypatch.setattr(budget,'policy_for',Mock(return_value=budget.Policy(3600,3,60000,2)))
    monkeypatch.setattr(budget,'_update',AsyncMock())
    monkeypatch.setattr(worker_module,'resolve_llm_config',AsyncMock(return_value=SimpleNamespace(
        allowed=True,api_key='synthetic-unit',base_url=None,model='unit',
        api_key_from_tenant=False,base_url_from_tenant=False,model_from_tenant=False)))
    reader=SimpleNamespace(fetch_organisation_memory=AsyncMock(return_value={'status':'not_requested','statements':[]}))
    worker=worker_module.FusedAlertTriageWorker(bootstrap_servers='unused',context_reader=reader)
    worker._sink_for=AsyncMock(return_value=worker._writer)
    for name in ('_attach_tenant_skill','_attach_runbooks','_attach_recent_dispositions','_attach_identity_context'):
        setattr(worker,name,AsyncMock())
    persist=AsyncMock();monkeypatch.setattr(worker_module.ledger_module,'persist_auto_triage',persist)
    trigger=AsyncMock();monkeypatch.setattr(worker_module.alert_trigger,'run_for_alert',trigger)
    requests=[]
    async def transport(request):
        requests.append(json.loads(request.content))
        if not answered:raise httpx.ConnectError('Synthetic unknown transport',request=request)
        response=sdk_response()
        body=json.loads(response.content)
        body['choices'][0]['message']['content']='not a JSON object'
        return httpx.Response(200,json=body)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        model=make_chat_model('triage',max_tokens=512,json_output=True,http_async_client=client)
        monkeypatch.setattr(agent,'make_chat_model',lambda *args,**kwargs:model)
        for _ in range(2):
            with pytest.raises(budget.BudgetHold):await worker._process_with_retry(message())
    assert len(requests)==1 and claim.await_count==1
    assert governor.spent_tokens(TENANT)==(18 if answered else 0)  # Accounting, not an unknown-usage claim.
    persist.assert_not_awaited();trigger.assert_not_awaited()
    agent.closure_policy.decide.assert_not_awaited();agent._sample_for_qa.assert_not_awaited()


# r02 branch additions share the original offline fixture/message/SDK assertions.
# No new SDK transport; these selected branches must never enter a model method.
def branch_harness(monkeypatch):
    governor=CostGovernor(config=BudgetConfig(soft_usd=50,hard_usd=100))
    monkeypatch.setattr(worker_module,'get_governor',lambda:governor)
    lookup,claim=AsyncMock(return_value=None),AsyncMock(return_value=None)
    monkeypatch.setattr(worker_module.triage_delivery,'lookup',lookup)
    monkeypatch.setattr(worker_module.triage_delivery,'claim',claim)
    policy=budget.Policy(3600,3,60000,2)
    policy_for=Mock(return_value=policy);monkeypatch.setattr(budget,'policy_for',policy_for)
    updates=AsyncMock();monkeypatch.setattr(budget,'_update',updates)
    resolve=AsyncMock(return_value=SimpleNamespace(allowed=True,api_key='synthetic-unit',base_url=None,model='unit',
        api_key_from_tenant=False,base_url_from_tenant=False,model_from_tenant=False))
    monkeypatch.setattr(worker_module,'resolve_llm_config',resolve)
    reader=SimpleNamespace(fetch_organisation_memory=AsyncMock(side_effect=AssertionError('No source read on this branch')))
    worker=worker_module.FusedAlertTriageWorker(bootstrap_servers='unused',context_reader=reader)
    worker._sink_for=AsyncMock(return_value=worker._writer)
    forbidden=[]
    for name in ('_attach_tenant_skill','_attach_runbooks','_attach_recent_dispositions','_attach_identity_context',
                 '_maybe_suppress_from_memory','_maybe_escalate','_raise_approvals','_write_back_to_source'):
        mock=AsyncMock(side_effect=AssertionError('Forbidden branch side effect'))
        setattr(worker,name,mock);forbidden.append(mock)
    trigger=AsyncMock(side_effect=AssertionError('No playbook preview or execution'))
    monkeypatch.setattr(worker_module.alert_trigger,'run_for_alert',trigger);forbidden.append(trigger)
    outcome=AsyncMock(side_effect=AssertionError('No outcome memory write'))
    monkeypatch.setattr(type(worker._writer),'record_outcome',outcome);forbidden.append(outcome)
    model=Mock(side_effect=AssertionError('Zero SDK branch'))
    monkeypatch.setattr(agent,'make_chat_model',model)
    llm=AsyncMock(side_effect=AssertionError('No model method'))
    monkeypatch.setattr(worker_module,'run_auto_triage',llm)
    deterministic=AsyncMock(wraps=worker_module.run_triage)
    monkeypatch.setattr(worker_module,'run_triage',deterministic)
    persist=AsyncMock(return_value=True)
    monkeypatch.setattr(worker_module.ledger_module,'persist_auto_triage',persist)
    return SimpleNamespace(worker=worker,governor=governor,lookup=lookup,claim=claim,policy=policy,
        policy_for=policy_for,updates=updates,resolve=resolve,reader=reader,forbidden=forbidden,
        model=model,llm=llm,deterministic=deterministic,persist=persist)


def assert_branch_has_no_model_or_effects(h):
    h.model.assert_not_called();h.llm.assert_not_awaited()
    h.reader.fetch_organisation_memory.assert_not_awaited()
    h.updates.assert_not_awaited()
    agent.closure_policy.decide.assert_not_awaited();agent._sample_for_qa.assert_not_awaited()
    for mock in h.forbidden:mock.assert_not_awaited()


@pytest.mark.parametrize('reason',['configured_deterministic','hard_circuit'])
@pytest.mark.asyncio
async def test_profile_actual_deterministic_zero_sdk_keeps_advice_none_and_effects_off(monkeypatch,reason):
    h=branch_harness(monkeypatch)
    if reason=='configured_deterministic':monkeypatch.setenv('AISOC_DETERMINISTIC','1')
    else:h.governor.record_spend(TENANT,usd=100,tokens=0)  # Exercise the actual governor circuit.
    incoming=message()
    incoming['alert'].update(title='ransomware on host',hostname='synthetic-guard-host')
    assert await h.worker._process_with_retry(incoming) is True
    h.deterministic.assert_awaited_once();h.lookup.assert_awaited_once();h.claim.assert_awaited_once()
    assert 'budget' not in h.claim.await_args.kwargs
    h.policy_for.assert_not_called()
    fields=h.persist.await_args.kwargs
    receipt=fields['triage_admission_receipt']
    assert receipt['model_advice'] is None and fields['llm_exchanges']==[] and fields['tokens']==0
    assert receipt['effective_decision']['review_required'] is True
    assert receipt['effective_decision']['confidence'] is None and fields['confidence']==0
    assert fields['verdict']=='needs_review' and fields['proposed_actions']==[] and fields['auto_closed'] is False
    assert h.governor.spent_tokens(TENANT)==0
    assert_branch_has_no_model_or_effects(h)


@pytest.mark.parametrize('mode',['invalid_config','worker_profile_changed'])
@pytest.mark.asyncio
async def test_profile_configuration_or_instance_drift_holds_before_reads(monkeypatch,mode):
    h=branch_harness(monkeypatch)
    if mode=='invalid_config':monkeypatch.setenv(admission.ENV,'not-a-profile')
    else:
        assert h.worker._review_only() is True  # Pin this actual instance to its first configuration.
        monkeypatch.setenv(admission.ENV,admission.LEGACY)
        # Reader-await drift can reach the agent with the original ON scope
        # and a now-legacy environment; it must fail before building the model.
        with admission.ordinary_live_scope(admission.REVIEW_ONLY):
            with pytest.raises(admission.ReviewOnlyHold):await agent.run_auto_triage(worker_module.build_state(message()))
    with pytest.raises(budget.BudgetHold):await h.worker._process_with_retry(message())
    h.lookup.assert_not_awaited();h.claim.assert_not_awaited();h.resolve.assert_not_awaited()
    h.worker._sink_for.assert_not_awaited();h.persist.assert_not_awaited();h.deterministic.assert_not_awaited()
    assert_branch_has_no_model_or_effects(h)


@pytest.mark.parametrize('prior_kind',['profile_first','old_fp','missing_profile'])
@pytest.mark.asyncio
async def test_claim_race_second_guard_reuses_only_confirmed_profile_first_result(monkeypatch,prior_kind):
    from app.core.cost_telemetry import CostSummary
    h=branch_harness(monkeypatch)
    state=worker_module.build_state(message())
    # Explicit stored-result double, not a newly executed reader/model/provider.
    state.record_llm_exchange(agent='auto_triage',purpose='triage.classify',model='unit',
        prompt=[{'role':'user','content':'Stored first fixture.'}],response=json.dumps(ADVICE),duration_ms=1)
    receipt=admission.enforce(state,advice=ADVICE)
    first=h.worker._recovery_projection(state,tier='llm',verdict=state.verdict,confidence=state.confidence,
        tokens=18,cost=CostSummary(unpriced_calls=1),writer=h.worker._writer)
    first.update(reused_persisted=True,persisted_artifacts=[
        {'kind':'llm_response','sha256':receipt['model_advice']['raw_response_sha256']}])
    if prior_kind=='old_fp':first={'verdict':'false_positive','confidence':.95}
    elif prior_kind=='missing_profile':first['triage_admission'].pop('profile')
    h.claim.return_value=deepcopy(first)  # First lookup misses; another process won before claim.
    if prior_kind=='profile_first':
        token=worker_module._BROKER_DELIVERY.set(True)
        try:result=await h.worker.triage(message())
        finally:worker_module._BROKER_DELIVERY.reset(token)
        assert result==first and result is not first
        assert result['triage_admission']['model_advice']['confidence']==.95
        assert result['verdict']=='needs_review' and result['triage_admission']['effective_decision']['confidence'] is None
    else:
        with pytest.raises(budget.BudgetHold):await h.worker._process_with_retry(message())
    h.lookup.assert_awaited_once();h.claim.assert_awaited_once()
    assert h.claim.await_args.kwargs['budget']==h.policy and h.worker._pending()=={}
    h.persist.assert_not_awaited();h.deterministic.assert_not_awaited()
    assert_branch_has_no_model_or_effects(h)


@pytest.mark.parametrize('initial,changed,seam',[
    (admission.REVIEW_ONLY,admission.LEGACY,'sdk'),
    (admission.LEGACY,admission.REVIEW_ONLY,'sdk'),
    (admission.LEGACY,admission.REVIEW_ONLY,'closure_policy'),
])
@pytest.mark.asyncio
async def test_actual_sdk_profile_drift_at_awaits_holds_before_closure_qa_or_persist(monkeypatch,initial,changed,seam):
    monkeypatch.setenv(admission.ENV,initial)
    h=branch_harness(monkeypatch)
    # Reuse the branch harness, restoring only the actual model path and its
    # four attachment doubles. The legacy entry also needs its original prior
    # lookup to miss before reaching the SDK drift seam. Review entry must skip
    # that lookup; no provider/source infrastructure or effect is introduced.
    monkeypatch.setattr(worker_module,'run_auto_triage',agent.run_auto_triage)
    h.reader.fetch_organisation_memory=AsyncMock(return_value={'status':'not_requested','statements':[]})
    for name in ('_attach_tenant_skill','_attach_runbooks','_attach_recent_dispositions','_attach_identity_context'):
        setattr(h.worker,name,AsyncMock())
    prior_miss=AsyncMock(return_value=None)
    monkeypatch.setattr(h.worker,'_maybe_suppress_from_memory',prior_miss)
    if seam=='closure_policy':
        async def change_in_policy(**kwargs):
            monkeypatch.setenv(admission.ENV,changed)
            return agent.closure_policy.ClosureDecision(allowed=True,threshold=.5,reason='unit would close',source='unit')
        closure=AsyncMock(side_effect=change_in_policy)
        monkeypatch.setattr(agent.closure_policy,'decide',closure)
    else:closure=agent.closure_policy.decide
    requests=[]
    async def transport(request):
        requests.append(json.loads(request.content))
        if seam=='sdk':monkeypatch.setenv(admission.ENV,changed)
        return sdk_response()
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        model=make_chat_model('triage',max_tokens=512,json_output=True,http_async_client=client)
        monkeypatch.setattr(agent,'make_chat_model',lambda *args,**kwargs:model)
        for _ in range(2):
            with pytest.raises(budget.BudgetHold):await h.worker._process_with_retry(message())
    assert len(requests)==1 and h.claim.await_count==1 and h.lookup.await_count==1
    assert prior_miss.await_count==int(initial==admission.LEGACY)
    # The ON profile accounts before hold; a legacy entry retains its original
    # governor timing. Both still have an observed/settled 18-token SDK reply.
    assert h.governor.spent_tokens(TENANT)==(18 if initial==admission.REVIEW_ONLY else 0)
    assert h.updates.await_count==2 and h.updates.await_args.args[-1]==18
    cost_telemetry._flush_to_db.assert_awaited_once()
    records=cost_telemetry._flush_to_db.await_args.args[2]
    assert len(records)==1 and records[0].prompt_tokens==11 and records[0].completion_tokens==7
    assert records[0].cost_usd is None  # Usage is known; provider USD is unpriced.
    assert closure.await_count==int(seam=='closure_policy')
    agent._sample_for_qa.assert_not_awaited();h.persist.assert_not_awaited()
    for effect in h.forbidden[4:]:effect.assert_not_awaited()
