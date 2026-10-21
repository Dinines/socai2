"""Rule decisions persist before success, while replay and shadow stay distinct."""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.investigator import ledger, policy_decisions as pd
from app.replay.shadow import ShadowTriageWriter
from app.workers.fused_alert_consumer import FusedAlertTriageWorker
from app.workers.shadow_mode import ShadowModeTriageWriter, ShadowDecision

TENANT='11111111-1111-1111-1111-111111111111'
ALERT='22222222-2222-2222-2222-222222222222'
POLICY={'policy_revision':'a'*64,'load_status':'current'}
MESSAGE={'tenant_id':TENANT,'id':ALERT,'alert':{'id':ALERT,'title':'fixture','username':'svc-backup'}}

def worker(writer):
    applier=SimpleNamespace(apply_for_tenant=AsyncMock(return_value=SimpleNamespace(suppressed=True,matched_rule_ids=['backup'],provenance=POLICY)))
    w=FusedAlertTriageWorker(bootstrap_servers='unused',business_context=applier,writer=writer)
    w._sink_for=AsyncMock(return_value=writer)
    w._llm_triage=AsyncMock(side_effect=AssertionError('must not call model'))
    return w

@pytest.mark.asyncio
async def test_success_requires_receipt_and_returns_frozen_provenance():
    receipt={'persisted':True,'run_id':str(uuid.uuid4()),'business_context_policy':{**POLICY,'load_status':'first-read'}}
    writer=SimpleNamespace(persist_policy_suppression=AsyncMock(return_value=receipt))
    w=worker(writer);out=await w.triage(MESSAGE)
    assert out['policy_receipt']==receipt and out['business_context_policy']['load_status']=='first-read'
    assert out['suppressed'] and 'verdict' not in out and not out['response_dispatched']
    assert writer.persist_policy_suppression.call_args.kwargs['raw_alert']==MESSAGE['alert']
    w._llm_triage.assert_not_called()

@pytest.mark.asyncio
async def test_write_error_is_not_success_and_reaches_retry_dlq():
    writer=SimpleNamespace(persist_policy_suppression=AsyncMock(side_effect=ledger.LedgerPersistError('injected')))
    w=worker(writer);w._max_attempts=2;w._retry_backoff=lambda _:0;w._send_to_dlq=AsyncMock()
    assert await w._process_with_retry(MESSAGE) is False
    assert writer.persist_policy_suppression.await_count==2
    assert w._send_to_dlq.call_args.kwargs['stage']=='persist'

@pytest.mark.asyncio
async def test_replay_sink_records_attempt_without_database(monkeypatch):
    monkeypatch.setattr(ledger,'get_pool',AsyncMock(side_effect=AssertionError('replay touched DB')))
    sink=ShadowTriageWriter();out=await worker(sink).triage(MESSAGE)
    assert not out['policy_receipt']['persisted'] and out['shadow']
    assert sink.calls['persist_policy_suppression']==1

@pytest.mark.asyncio
async def test_live_shadow_delegates_observation_flag_only():
    delegate=SimpleNamespace(persist_policy_suppression=AsyncMock(return_value={'persisted':True,'shadow':True}))
    sink=ShadowModeTriageWriter(delegate,ShadowDecision(tenant_ref=TENANT,alert_class='endpoint',alert_id=ALERT))
    await sink.persist_policy_suppression(tenant_ref=TENANT,alert_id=ALERT,raw_alert={},policy=POLICY,matched_rules=['backup'])
    assert delegate.persist_policy_suppression.call_args.kwargs['shadow'] is True
    assert sink.recorded is False  # no model-agreement decision fabricated

@pytest.mark.asyncio
async def test_missing_database_is_retryable_not_silent_skip(monkeypatch):
    monkeypatch.setattr(ledger,'get_pool',AsyncMock(return_value=None))
    with pytest.raises(ledger.LedgerPersistError,match='database unavailable'):
        await pd.persist_policy_suppression(tenant_ref=TENANT,alert_id=ALERT,raw_alert={},policy=POLICY,matched_rules=['backup'])

@pytest.mark.asyncio
@pytest.mark.parametrize('override',[{'tenant_ref':'default'},{'alert_id':'missing'},{'policy':{}},{'raw_alert':{'tenant_id':ALERT}}])
async def test_invalid_or_unobserved_input_cannot_claim_durable_suppression(monkeypatch,override):
    get=AsyncMock(side_effect=AssertionError('invalid input touched DB'));monkeypatch.setattr(ledger,'get_pool',get)
    args=dict(tenant_ref=TENANT,alert_id=ALERT,raw_alert={},policy=POLICY,matched_rules=['backup']);args.update(override)
    with pytest.raises(ledger.LedgerPersistError):await pd.persist_policy_suppression(**args)
    get.assert_not_called()

@pytest.mark.asyncio
async def test_dlq_requires_broker_confirmation(monkeypatch):
    w=worker(SimpleNamespace());producer=SimpleNamespace(send_and_wait=AsyncMock(side_effect=OSError('injected')))
    w._ensure_producer=AsyncMock(return_value=producer)
    with pytest.raises(ledger.LedgerPersistError,match='DLQ not confirmed'):
        await w._send_to_dlq(MESSAGE,attempts=1,stage='persist',error='injected')
    w._ensure_producer=AsyncMock(return_value=None)
    with pytest.raises(ledger.LedgerPersistError,match='uncommitted'):
        await w._send_to_dlq(MESSAGE,attempts=1,stage='persist',error='injected')

@pytest.mark.asyncio
async def test_consumer_cannot_commit_past_failed_durability(monkeypatch):
    import aiokafka
    from app.workers import fused_alert_consumer as module
    class Consumer:
        commit=AsyncMock();stop=AsyncMock();start=AsyncMock()
        def __init__(self,*a,**kw):self.sent=False
        def __aiter__(self):return self
        async def __anext__(self):
            if self.sent:raise StopAsyncIteration
            self.sent=True;return SimpleNamespace(value=MESSAGE,partition=0,offset=0)
    monkeypatch.setattr(aiokafka,'AIOKafkaConsumer',Consumer)
    monkeypatch.setattr(module,'_COMMIT_WINDOW_SECONDS',0)
    w=worker(SimpleNamespace());w._process_with_retry=AsyncMock(side_effect=ledger.LedgerPersistError('no DB or DLQ'))
    with pytest.raises(ledger.LedgerPersistError,match='window lacks durable'):
        await w.start()
    w._consumer.commit.assert_not_called();w._consumer.stop.assert_awaited_once()
