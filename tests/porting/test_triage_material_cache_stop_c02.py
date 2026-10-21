"""C02's direct runtime seams; HTTP is MockTransport, stores are explicit doubles.

No Docker, broker, database, external provider, or real model is used here.
SDK requests, safe-call validation, usage tracking and groundedness are real
production functions. Source projection is checked before prompt formatting.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import httpx
import pytest

from app.agents import auto_triage_agent as agent
from app.core import cost_telemetry
from app.core.cost_governor import BudgetConfig, CostGovernor
from app.core.cost_telemetry import CostTracker
from app.llm import contract
from app.llm.factory import make_chat_model
from app.workers import fused_alert_consumer as module
from app.workers import triage_budget as budget
from app.workers.shadow_mode import ShadowDecision, ShadowModeTriageWriter

TENANT = '11111111-1111-1111-1111-111111111111'
ALERT = '22222222-2222-2222-2222-222222222222'


def envelope(alert_id=ALERT, **values):
    return {'id': alert_id, 'alert_row_id': alert_id, 'tenant_id': TENANT,
            'incident_id': '33333333-3333-3333-3333-333333333333',
            'alert': {'id': alert_id, 'tenant_id': TENANT, 'source': 'c02-unit',
                      'title': 'Synthetic fixed pattern', 'severity': 'medium', 'hostname': 'c02-unit-host',
                      'risk_score': 0, 'source_event_ids': ['c02-first'], 'raw_event': {}, **values}}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    for name in ('AISOC_AGENT_MEMORY_SUPPRESSION', 'AISOC_AGENT_MEMORY_WRITEBACK',
                 'AISOC_AGENT_RAISE_APPROVALS', 'AISOC_AGENT_ESCALATE_TO_GRAPH', 'AISOC_ALERT_PLAYBOOKS_ENABLED'):
        monkeypatch.setenv(name, '0')
    monkeypatch.setenv('AISOC_DETERMINISTIC', '0')
    monkeypatch.setenv('AISOC_AGENT_GROUNDEDNESS_GATE', '1')
    monkeypatch.setenv('AISOC_GATEWAY_COST_TRUST', '1')  # Synthetic header values, never provider measurements.
    monkeypatch.setenv('LLM_GATEWAY_URL', 'http://127.0.0.1.invalid/v1')
    monkeypatch.setenv('LITELLM_MASTER_KEY', 'synthetic-unit')
    monkeypatch.delenv('OPENAI_BASE_URL', raising=False)
    monkeypatch.delenv('LLM_BASE_URL', raising=False)
    monkeypatch.setattr(contract, '_RESPONSE_CACHE_ENABLED', False)
    monkeypatch.setattr(contract.egress_privacy, '_FORCE', '0')
    monkeypatch.setattr(agent.closure_policy, 'decide', AsyncMock(return_value=agent.closure_policy.ClosureDecision(
        allowed=False, threshold=.85, reason='unit disabled', source='unit')))
    # Keep the actual CostTracker and record_llm_call; decline only its DB flush.
    monkeypatch.setattr(cost_telemetry, '_flush_to_db', AsyncMock())


@pytest.mark.parametrize('fields', [{}, {'description': None, 'event_time': None, 'created_at': None},
    {'description': 'line one\nline two', 'event_time': '2026-10-20T11:01:00+08:00', 'created_at': '2026-10-21T02:00:00Z'}])
def test_source_material_preserves_presence_null_and_distinct_time_fields(fields):
    state = module.build_state(envelope(**fields))
    for key in ('description', 'event_time', 'created_at'):
        assert (key in state.raw_alert) is (key in fields)
        if key in fields:
            assert state.raw_alert[key] == fields[key]
    assert state.raw_alert['risk_score'] == 0
    assert state.raw_alert['source'] == 'c02-unit' and state.raw_alert['source_event_ids'] == ['c02-first']
    assert module.build_state(envelope()).run_id == state.run_id


def response(content, index=1):
    # This fixed price is a transport fixture for accounting/circuit behavior.
    return httpx.Response(200, headers={'x-litellm-response-cost': '0.01', 'x-litellm-model-name': 'unit-observed'}, json={
        'id': 'c02-unit-' + str(index), 'object': 'chat.completion', 'created': 1, 'model': 'unit-observed',
        'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': json.dumps(content)}, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18}})


def test_naive_empty_and_invalid_source_time_never_fall_back_or_assume_utc():
    created = '2026-10-20T02:00:00Z'
    for value, marker in [('2026-10-20T11:01:00', 'timezone not provided; not assumed UTC'),
                          ('', '[empty source value]'), ('vendor time unknown', 'unparsed source timestamp; timezone not inferred')]:
        state = module.build_state(envelope(event_time=value, created_at=created))
        block = agent._build_alert_context(state, nonce='c02-unit-nonce')
        event_line = next(line for line in block.splitlines() if line.startswith('Event time (source'))
        assert marker in event_line and created not in event_line
        assert state.raw_alert['event_time'] == value and state.raw_alert['created_at'] == created


@pytest.mark.parametrize('fields,expected', [
    ({'description': 'line one\n' + 'x' * 1800, 'event_time': '2026-10-20T11:01:00+08:00'}, 'explicit UTC offset retained'),
    ({'created_at': '2026-10-20T11:02:00Z'}, 'Event time (source alert.event_time; no fallback): [missing from source alert]'),
    ({'description': None, 'event_time': None}, 'Event time (source alert.event_time; no fallback): [explicit null in source alert]'),
])
@pytest.mark.asyncio
async def test_actual_safe_call_sdk_messages_have_dedicated_untrusted_material(monkeypatch, fields, expected):
    requests = []

    async def transport(request):
        requests.append(json.loads(request.content))
        return response({'verdict': 'needs_review', 'confidence': .5, 'rationale': 'Synthetic evidence requires review.'})

    state = module.build_state(envelope(**fields))
    updates = AsyncMock()
    monkeypatch.setattr(budget, '_update', updates)
    invocation = budget.Invocation(state.run_id, state.tenant_id, lambda: False)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        model = make_chat_model('triage', max_tokens=512, json_output=True, http_async_client=client, include_response_headers=True)
        monkeypatch.setattr(agent, 'make_chat_model', lambda *args, **kwargs: model)
        with budget.invocation_scope(invocation):
            async with CostTracker(run_id=str(state.run_id), tenant_id=TENANT, persist=False) as tracker:
                result = await agent.run_auto_triage(state)
    assert len(requests) == 1 and tracker.total_tokens == 18
    messages = requests[0]['messages']
    telemetry = messages[1]['content']
    assert expected in telemetry
    assert telemetry.index('<UNTRUSTED_DATA') < telemetry.index('Alert description (publisher supplied, untrusted):') < telemetry.index('</UNTRUSTED_DATA>')
    assert 'Alert created_at (source creation field; not event time):' in telemetry
    if fields.get('description'):
        assert 'line one\n' in telemetry and '…[truncated]' in telemetry
        assert 'x' * 1300 not in telemetry
    assert json.loads(result.llm_exchanges[0]['prompt']) == messages
    assert result.llm_exchanges[0]['prompt_truncated'] is False
    assert len(result.llm_exchanges[0]['prompt']) <= 8000
    assert requests[0]['max_tokens'] == 512 and updates.await_count == 2
    assert updates.await_args.args[-1] == 18


@pytest.mark.parametrize('shadow', [False, True])
@pytest.mark.asyncio
async def test_live_same_pattern_never_reads_or_publishes_rejected_verdict_but_accounts_spend(monkeypatch, shadow):
    governor = CostGovernor(config=BudgetConfig(soft_usd=.01, hard_usd=.015))
    monkeypatch.setattr(module, 'get_governor', lambda: governor)
    lookup, claim = AsyncMock(return_value=None), AsyncMock(return_value=None)
    monkeypatch.setattr(module.triage_delivery, 'lookup', lookup)
    monkeypatch.setattr(module.triage_delivery, 'claim', claim)
    policy = budget.Policy(3600, 3, 60000, 2)
    monkeypatch.setattr(budget, 'policy_for', Mock(return_value=policy))
    updates = AsyncMock()
    monkeypatch.setattr(budget, '_update', updates)
    monkeypatch.setattr(module, 'resolve_llm_config', AsyncMock(return_value=SimpleNamespace(
        allowed=True, api_key='synthetic-unit', base_url=None, model='unit',
        api_key_from_tenant=False, base_url_from_tenant=False, model_from_tenant=False)))
    reader = SimpleNamespace(fetch_organisation_memory=AsyncMock(return_value={'status': 'not_requested', 'statements': []}))
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused', context_reader=reader)
    writer = worker._writer
    if shadow:
        writer = ShadowModeTriageWriter(writer, ShadowDecision(tenant_ref=TENANT, alert_class='unit', alert_id=ALERT))
    worker._sink_for = AsyncMock(return_value=writer)
    for name in ('_attach_tenant_skill', '_attach_runbooks', '_attach_recent_dispositions', '_attach_identity_context', '_maybe_escalate'):
        setattr(worker, name, AsyncMock())
    worker._raise_approvals = AsyncMock(return_value=[])
    worker._write_back_to_source = AsyncMock(return_value=None)
    worker._record = AsyncMock()
    first = envelope(description='First body', event_time='2026-10-20T11:01:00Z')
    second = envelope('22222222-2222-2222-2222-222222222223', description='Different body', event_time='2026-10-20T14:01:00Z')
    fingerprint = governor.evidence_fingerprint(TENANT, module.build_state(first).raw_alert)
    assert fingerprint == governor.evidence_fingerprint(TENANT, module.build_state(second).raw_alert)
    governor.record_verdict(TENANT, fingerprint, {'verdict': 'false_positive', 'confidence': .99}, usd=0, tokens=0)
    cached_before = deepcopy(governor._cache)
    requests, results = [], []

    async def transport(request):
        requests.append(json.loads(request.content))
        return response({'verdict': 'false_positive', 'confidence': .99, 'rationale': '203.0.113.99 is harmless.'}, len(requests))

    original_triage = worker.triage
    async def capture(message):
        result = await original_triage(message)
        results.append(result)
        return result
    worker.triage = capture
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        model = make_chat_model('triage', max_tokens=512, json_output=True, http_async_client=client, include_response_headers=True)
        monkeypatch.setattr(agent, 'make_chat_model', lambda *args, **kwargs: model)
        assert await worker._process_with_retry(first) is True
        assert await worker._process_with_retry(second) is True
        assert len(requests) == 2 and all(result['tier'] == 'llm' for result in results)
        assert all(result['verdict'] == 'needs_review' and result['confidence_basis'] for result in results)
        assert all(result['shadow'] is shadow for result in results)
        assert all(result['cost']['tokens'] == 18 and result['cost']['measured_usd'] == pytest.approx(.01) for result in results)
        assert governor.spent_tokens(TENANT) == 36 and governor.spent_usd(TENANT) == pytest.approx(.02)
        assert governor._cache == cached_before  # Neither pattern nor admission-key verdict was published.
        assert claim.await_count == 2 and all(call.kwargs['budget'] == policy for call in claim.await_args_list)
        assert updates.await_count == 4
        assert 'First body' in requests[0]['messages'][1]['content'] and 'Different body' in requests[1]['messages'][1]['content']
        third = envelope('22222222-2222-2222-2222-222222222224', description='Circuit now open')
        assert await worker._process_with_retry(third) is True
        assert results[-1]['tier'] == 'deterministic' and len(requests) == 2
        # Same-run PG recovery still returns before model/governor/budget work.
        lookup.return_value = deepcopy(results[0])
        before_claims = claim.await_count
        assert await worker._process_with_retry(first) is True
        assert claim.await_count == before_claims and len(requests) == 2
        lookup.return_value = None
        # Direct calls deliberately retain the prior cache contract.
        direct = await original_triage(first)
        assert direct['tier'] == 'cached' and direct['verdict'] == 'false_positive'
        assert len(requests) == 2


@pytest.mark.parametrize('failure', ['consumer_error', 'consumer_timeout', 'producer_error', 'consumer_cancel'])
@pytest.mark.asyncio
async def test_stop_cleans_lanes_after_each_client_failure_and_preserves_error(monkeypatch, failure):
    monkeypatch.setattr(module, '_STOP_CLIENT_TIMEOUT_SECONDS', .01)
    monkeypatch.setattr(module, '_STOP_DRAIN_TIMEOUT_SECONDS', .01)
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused', entity_concurrency=1)
    entered, finished = asyncio.Event(), asyncio.Event()
    async def work():
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            finished.set()
    await worker._lanes.submit('unit', work)
    await worker._lanes.submit('unit', work)
    await entered.wait()
    consumer = SimpleNamespace(stop=AsyncMock(), commit=AsyncMock())
    producer = SimpleNamespace(stop=AsyncMock(), send_and_wait=AsyncMock())
    if failure == 'consumer_error':
        consumer.stop.side_effect = RuntimeError('unit consumer stop')
    elif failure == 'consumer_timeout':
        async def never_stops():
            await asyncio.Event().wait()
        consumer.stop.side_effect = never_stops
    elif failure == 'consumer_cancel':
        consumer.stop.side_effect = asyncio.CancelledError()
    else:
        producer.stop.side_effect = RuntimeError('unit producer stop')
    worker._consumer, worker._producer = consumer, producer
    expected = asyncio.CancelledError if failure == 'consumer_cancel' else TimeoutError if failure == 'consumer_timeout' else RuntimeError
    with pytest.raises(expected):
        await worker.stop()
    assert finished.is_set() and worker._lanes.in_flight == worker._lanes.tracked_entities == 0
    assert worker._lanes._waiters == {} and worker._stopping is True and worker.attached is False
    producer.stop.assert_awaited_once()
    producer.send_and_wait.assert_not_awaited()
    consumer.commit.assert_not_awaited()
    with pytest.raises(budget.BudgetHold):
        await worker._process_with_retry(envelope())


@pytest.mark.asyncio
async def test_external_cancel_waits_for_owned_cleanup_then_propagates(monkeypatch):
    monkeypatch.setattr(module, '_STOP_DRAIN_TIMEOUT_SECONDS', .01)
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused')
    entered, release = asyncio.Event(), asyncio.Event()
    async def stop_consumer():
        entered.set()
        await release.wait()
    worker._consumer = SimpleNamespace(stop=stop_consumer)
    producer = SimpleNamespace(stop=AsyncMock())
    worker._producer = producer
    await worker._lanes.submit('unit', lambda: asyncio.Event().wait())
    task = asyncio.create_task(worker.stop())
    await entered.wait()
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert worker._lanes.in_flight == worker._lanes.tracked_entities == 0
    producer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_actual_worker_loop_joins_inflight_handler_without_late_commit_when_consumer_stop_fails(monkeypatch):
    import aiokafka
    monkeypatch.setattr(module, '_STOP_DRAIN_TIMEOUT_SECONDS', .01)
    monkeypatch.setattr(module, '_STOP_CLIENT_TIMEOUT_SECONDS', .01)
    monkeypatch.setattr(module, 'kafka_client_kwargs', lambda: {})
    consumers, entered, finished = [], asyncio.Event(), asyncio.Event()
    class Consumer:
        def __init__(self, *args, **kwargs):
            self.yielded = False
            self.commit = AsyncMock()
            self.stop = AsyncMock(side_effect=RuntimeError('unit consumer stop'))
            consumers.append(self)
        async def start(self):
            pass
        def __aiter__(self):
            return self
        async def __anext__(self):
            if self.yielded:
                await asyncio.Event().wait()
            self.yielded = True
            return SimpleNamespace(value=envelope(), partition=0, offset=0)
    monkeypatch.setattr(aiokafka, 'AIOKafkaConsumer', Consumer)
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused')
    async def handling(message):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            finished.set()
    worker._process_with_retry = handling
    task = asyncio.create_task(worker.start())
    await entered.wait()
    with pytest.raises(RuntimeError, match='unit consumer stop'):
        await worker.stop()
    # The cleanup failure must not replace the original unconfirmed-window
    # failure from the actual start/_handle control flow.
    with pytest.raises(module.ledger_module.LedgerPersistError):
        await task
    assert task.done() and finished.is_set() and worker.attached is False
    assert worker._lanes.in_flight == worker._lanes.tracked_entities == 0
    consumers[0].commit.assert_not_awaited()


@pytest.mark.parametrize('stop_failure', [RuntimeError, asyncio.CancelledError])
@pytest.mark.asyncio
async def test_actual_main_lifespan_joins_worker_before_closing_ledger_on_stop_failure(monkeypatch, stop_failure):
    from app import main
    for key in ('AISOC_PLAYBOOK_SEED_DISABLE', 'AISOC_ATTCK_STARTUP_DISABLE', 'AISOC_ATTCK_INDEX_DISABLE', 'AISOC_HUNT_SCHEDULER_DISABLE'):
        monkeypatch.setenv(key, '1')
    monkeypatch.setenv('KAFKA_BOOTSTRAP_SERVERS', 'unused')
    events, entered = [], asyncio.Event()
    class Worker:
        topic, attached = 'unit-fused', True
        async def start(self):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                events.append('worker_joined')
        async def stop(self):
            events.append('stop_attempted')
            raise stop_failure('unit stop failure')
    worker = Worker()
    monkeypatch.setattr(main, 'worker_enabled', lambda: True)
    monkeypatch.setattr(main, 'FusedAlertTriageWorker', lambda **kwargs: worker)
    monkeypatch.setattr(main, 'business_context_enabled', lambda: False)
    monkeypatch.setattr(main, 'preflight_llm', lambda: [])
    monkeypatch.setattr(main, 'register_subscription', lambda *args: None)
    monkeypatch.setattr(main.playbook_sweeper, 'start', lambda app: None)
    monkeypatch.setattr(main.investigation_run_reaper, 'start', lambda app: None)
    monkeypatch.setattr(main.investigation_ledger, 'get_pool', AsyncMock(return_value=None))
    monkeypatch.setattr(main.hunt_scheduler, 'stop_scheduler', AsyncMock())
    monkeypatch.setattr(main.hunt_store, 'close_pool', AsyncMock())
    async def close_ledger():
        assert app.state.triage_worker_task.done()
        events.append('ledger_closed')
    monkeypatch.setattr(main.investigation_ledger, 'close_pool', close_ledger)
    app = SimpleNamespace(state=SimpleNamespace(mark_ready=lambda: None, mark_not_ready=lambda: None))
    async def lifecycle():
        async with main.lifespan(app):
            await entered.wait()
    if stop_failure is asyncio.CancelledError:
        with pytest.raises(asyncio.CancelledError):
            await lifecycle()
    else:
        await lifecycle()
    assert events == ['stop_attempted', 'worker_joined', 'ledger_closed']
    assert app.state.triage_worker_task.cancelled()
