"""Live broker admission and durable confirmation; no actual model or broker.

Consumer and pool doubles prove the local control flow. Real SSL Kafka/PG
confirmation, offsets and FK failures remain a separate bounded live probe.
"""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.investigator import ledger
from app.replay.shadow import ShadowTriageWriter
from app.workers import fused_alert_consumer as module
from app.workers.triage_persistence import LiveTriageWriter

TENANT = '11111111-1111-1111-1111-111111111111'
OTHER = '33333333-3333-3333-3333-333333333333'
ALERT = '22222222-2222-2222-2222-222222222222'


def envelope():
    return {'tenant_id': TENANT, 'alert_row_id': ALERT, 'id': ALERT,
            'alert': {'id': 'upstream-source-17', 'title': 'Synthetic delivery boundary',
                      'source': 'test-source', 'connector_id': 'connector-17', 'connector_type': 'test',
                      'source_event_ids': ['source-event-17']}}


def ledger_fields():
    return dict(run_id=uuid4(), alert_id=ALERT, tenant_ref=TENANT, alert_summary='synthetic',
                raw_alert={}, tier='deterministic', verdict='needs_review', confidence=0,
                rationale='No actual model called')


@pytest.mark.asyncio
@pytest.mark.parametrize('unconfirmed', [False, None, 0, 1, {}, {'persisted': True}])
async def test_live_writer_requires_explicit_true(monkeypatch, unconfirmed):
    persist = AsyncMock(return_value=unconfirmed)
    monkeypatch.setattr(ledger, 'persist_auto_triage', persist)
    fields = ledger_fields()
    with pytest.raises(ledger.LedgerPersistError, match='did not confirm persistence'):
        await LiveTriageWriter().persist_auto_triage(**fields)
    persist.assert_awaited_once_with(**fields)


@pytest.mark.asyncio
async def test_live_writer_accepts_confirmation_without_changing_replay_sink(monkeypatch):
    persist = AsyncMock(return_value=True)
    monkeypatch.setattr(ledger, 'persist_auto_triage', persist)
    assert await LiveTriageWriter().persist_auto_triage(**ledger_fields()) is None
    replay = ShadowTriageWriter()
    assert await replay.persist_auto_triage(**ledger_fields()) is None
    assert replay.calls['persist_auto_triage'] == 1 and persist.await_count == 1


@pytest.mark.asyncio
async def test_actual_ledger_no_pool_skip_is_live_writer_failure(monkeypatch):
    monkeypatch.setattr(ledger, 'get_pool', AsyncMock(return_value=None))
    with pytest.raises(ledger.LedgerPersistError, match='did not confirm persistence'):
        await LiveTriageWriter().persist_auto_triage(**ledger_fields())


@pytest.mark.asyncio
async def test_actual_ledger_unknown_slug_skip_is_live_writer_failure(monkeypatch):
    connection = SimpleNamespace(fetchrow=AsyncMock(return_value=None), execute=AsyncMock())

    class Acquire:
        async def __aenter__(self): return connection
        async def __aexit__(self, *args): return False

    pool = SimpleNamespace(acquire=lambda: Acquire())
    monkeypatch.setattr(ledger, 'get_pool', AsyncMock(return_value=pool))
    fields = ledger_fields() | {'tenant_ref': 'unknown-synthetic-slug'}
    with pytest.raises(ledger.LedgerPersistError, match='did not confirm persistence'):
        await LiveTriageWriter().persist_auto_triage(**fields)
    connection.fetchrow.assert_awaited_once()
    connection.execute.assert_not_awaited()


def invalid_inputs():
    valid = envelope()
    values = [None, [], 'not an envelope', 0, {}, valid | {'alert': None}, valid | {'alert': {}},
              valid | {'alert': []}, valid | {'tenant_id': None}, valid | {'tenant_id': ''},
              valid | {'tenant_id': 'default'}, valid | {'tenant_id': False},
              valid | {'alert_row_id': None}, valid | {'alert_row_id': ''},
              valid | {'alert_row_id': 'external-not-canonical'}, valid | {'alert_row_id': {}},
              valid | {'alert': valid['alert'] | {'tenant_id': OTHER}},
              valid | {'alert': valid['alert'] | {'tenant_id': 'default'}}]
    no_tenant = deepcopy(valid); no_tenant.pop('tenant_id'); values.append(no_tenant)
    no_ids = {'tenant_id': TENANT, 'alert': {'title': 'No stable alert ID'}}; values.append(no_ids)
    return values


@pytest.mark.asyncio
@pytest.mark.parametrize('payload', invalid_inputs())
async def test_bad_broker_input_dlq_once_before_any_triage_work(payload):
    business = SimpleNamespace(apply_for_tenant=AsyncMock())
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused', business_context=business, max_attempts=3)
    triage = AsyncMock(wraps=worker.triage); worker.triage = triage
    producer = SimpleNamespace(send_and_wait=AsyncMock(return_value=SimpleNamespace(offset=0)))
    worker._ensure_producer = AsyncMock(return_value=producer)
    before = deepcopy(payload)
    assert await worker._process_with_retry(payload) is False
    triage.assert_not_awaited(); business.apply_for_tenant.assert_not_awaited()
    producer.send_and_wait.assert_awaited_once()
    record = producer.send_and_wait.call_args.kwargs['value']
    assert record['failure_stage'] == 'schema' and record['attempts'] == 1
    assert record['original'] == before == payload
    assert record['tenant_id'] != 'default' and record['canonical_alert_id'] != 'default'


@pytest.mark.asyncio
@pytest.mark.parametrize('selection', ['alert_row_id', 'envelope_id', 'nested_id', 'nested_tenant'])
async def test_valid_explicit_ids_reach_triage_with_source_v1_alias_compatibility(selection):
    payload = envelope()
    if selection != 'alert_row_id': payload.pop('alert_row_id')
    if selection in {'nested_id', 'nested_tenant'}:
        payload.pop('id'); payload['alert']['id'] = ALERT
    if selection == 'nested_tenant':
        payload.pop('tenant_id'); payload['alert']['tenant_id'] = TENANT
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused')
    worker.triage = AsyncMock(return_value={'run_id': str(uuid4()), 'verdict': 'needs_review'})
    worker._send_to_dlq = AsyncMock()
    assert await worker._process_with_retry(payload) is True
    worker.triage.assert_awaited_once_with(payload)
    worker._send_to_dlq.assert_not_awaited()


@pytest.mark.asyncio
async def test_none_triage_result_is_one_schema_dlq_not_success():
    payload = envelope()
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused', max_attempts=3)
    worker.triage = AsyncMock(return_value=None)
    worker._send_to_dlq = AsyncMock()
    assert await worker._process_with_retry(payload) is False
    worker.triage.assert_awaited_once_with(payload)
    worker._send_to_dlq.assert_awaited_once_with(payload, attempts=1, stage='schema', error='triage_returned_no_result')


@pytest.mark.asyncio
async def test_dlq_preserves_explicit_source_and_unknown_identity():
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused')
    producer = SimpleNamespace(send_and_wait=AsyncMock(return_value=SimpleNamespace(offset=0)))
    worker._ensure_producer = AsyncMock(return_value=producer)
    known = envelope()
    await worker._send_to_dlq(known, attempts=1, stage='persist', error='controlled')
    row = producer.send_and_wait.call_args.kwargs['value']
    assert row['tenant_id'] == TENANT and row['canonical_alert_id'] == row['alert_id'] == ALERT
    assert {key: row[key] for key in ['source', 'connector_id', 'connector_type', 'source_event_ids']} == {
        key: known['alert'][key] for key in ['source', 'connector_id', 'connector_type', 'source_event_ids']}
    bad = {'tenant_id': 'default', 'alert_row_id': 'external-source', 'alert': {'title': 'Malformed', 'source_event_ids': [42]}}
    await worker._send_to_dlq(bad, attempts=1, stage='schema', error='controlled')
    row = producer.send_and_wait.call_args.kwargs['value']
    assert row['tenant_id'] is None and row['canonical_alert_id'] is None
    assert row['alert_id'] == 'external-source' and row['original'] == bad
    assert all(row[key] is None for key in ['source', 'connector_id', 'connector_type', 'source_event_ids'])
    conflict = known | {'alert': known['alert'] | {'tenant_id': OTHER}}
    await worker._send_to_dlq(conflict, attempts=1, stage='schema', error='controlled')
    assert producer.send_and_wait.call_args.kwargs['value']['tenant_id'] is None


@pytest.mark.asyncio
@pytest.mark.parametrize('payload', [None, ['original', {'value': 'x' * 2500}], 'x' * 2500, False])
async def test_dlq_keeps_non_object_decoded_input_untruncated(payload):
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused')
    producer = SimpleNamespace(send_and_wait=AsyncMock())
    worker._ensure_producer = AsyncMock(return_value=producer)
    await worker._send_to_dlq(payload, attempts=1, stage='schema', error='controlled')
    row = producer.send_and_wait.call_args.kwargs['value']
    assert row['original'] == payload and row['tenant_id'] is None and row['canonical_alert_id'] is None


@pytest.mark.asyncio
async def test_direct_replay_keeps_explicit_string_id_mapping(monkeypatch):
    from app.core.cost_governor import reset_governor
    reset_governor()
    monkeypatch.setenv('AISOC_AGENT_MEMORY_SUPPRESSION', '0')
    monkeypatch.setenv('AISOC_AGENT_MEMORY_WRITEBACK', '0')
    monkeypatch.setenv('AISOC_AGENT_RAISE_APPROVALS', '0')
    monkeypatch.setenv('AISOC_AGENT_ESCALATE_TO_GRAPH', '0')
    monkeypatch.setattr(module, 'resolve_llm_config', AsyncMock(return_value=SimpleNamespace(
        allowed=False, api_key=None, base_url=None, model=None)))
    payload = {'tenant_id': TENANT, 'id': 'ES-SYNTHETIC-1', 'alert': {'id': 'ES-SYNTHETIC-1', 'title': 'Synthetic replay'}}
    state = module.build_state(payload)
    assert state is not None and state.run_id == module.build_state(payload).run_id
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused', writer=ShadowTriageWriter())
    worker._sink_for = AsyncMock(return_value=worker._writer)
    result = await worker.triage(payload)
    assert result is not None and result['run_id'] == str(state.run_id)
    reset_governor()


@pytest.mark.asyncio
@pytest.mark.parametrize('origin', ['schema', 'ledger_false'])
@pytest.mark.parametrize('confirmation', ['ack', 'missing_producer', 'send_failure'])
async def test_actual_consumer_requires_dlq_ack_before_commit(monkeypatch, origin, confirmation):
    import aiokafka
    from app.core.cost_governor import reset_governor
    reset_governor()
    order = []
    payload = {} if origin == 'schema' else envelope()

    class Consumer:
        def __init__(self, *args, **kwargs):
            self.sent = False
            self.commit = AsyncMock(side_effect=self.commit_offset)
            self.stop = AsyncMock()
        async def start(self): pass
        async def commit_offset(self): order.append('commit')
        def __aiter__(self): return self
        async def __anext__(self):
            if self.sent: raise StopAsyncIteration
            self.sent = True
            return SimpleNamespace(value=payload, partition=0, offset=0)

    async def send(topic, value):
        order.append('dlq_attempt')
        if confirmation == 'send_failure': raise OSError('Controlled unconfirmed send')
        order.append('dlq_ack')
        return SimpleNamespace(partition=0, offset=0)

    monkeypatch.setattr(aiokafka, 'AIOKafkaConsumer', Consumer)
    # The consumer and DLQ producer are in-memory doubles. This test measures
    # commit ordering, not real Kafka transport; keep the production guard.
    monkeypatch.setattr(module, 'kafka_client_kwargs', lambda: {})
    monkeypatch.setattr(module, '_COMMIT_WINDOW_SECONDS', 0)
    monkeypatch.setenv('AISOC_AGENT_MEMORY_SUPPRESSION', '0')
    monkeypatch.setenv('AISOC_AGENT_MEMORY_WRITEBACK', '0')
    monkeypatch.setenv('AISOC_AGENT_RAISE_APPROVALS', '0')
    monkeypatch.setenv('AISOC_AGENT_ESCALATE_TO_GRAPH', '0')
    monkeypatch.setattr(module, 'resolve_llm_config', AsyncMock(return_value=SimpleNamespace(
        allowed=False, api_key=None, base_url=None, model=None)))
    persist = AsyncMock(return_value=False)
    monkeypatch.setattr(ledger, 'persist_auto_triage', persist)
    # Keep the original no-pool confirmation fault as the measured boundary;
    # exact-delivery lookup/claim are independent database substitutes here.
    monkeypatch.setattr(module.triage_delivery, 'lookup', AsyncMock(return_value=None))
    monkeypatch.setattr(module.triage_delivery, 'claim', AsyncMock(return_value=None))
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused', max_attempts=2, entity_concurrency=1)
    worker._sink_for = AsyncMock(return_value=LiveTriageWriter())
    worker._retry_backoff = lambda attempt: 0
    producer = None if confirmation == 'missing_producer' else SimpleNamespace(send_and_wait=AsyncMock(side_effect=send))
    worker._ensure_producer = AsyncMock(return_value=producer)
    worker._llm_triage = AsyncMock(side_effect=AssertionError('No model allowed'))
    if confirmation == 'ack':
        await worker.start()
        assert order == ['dlq_attempt', 'dlq_ack', 'commit']
        worker._consumer.commit.assert_awaited_once()
        record = producer.send_and_wait.call_args.kwargs['value']
        assert record['failure_stage'] == ('schema' if origin == 'schema' else 'persist')
        assert record['attempts'] == (1 if origin == 'schema' else 2)
        assert record['original'] == payload
    else:
        with pytest.raises(ledger.LedgerPersistError, match='window lacks durable'):
            await worker.start()
        worker._consumer.commit.assert_not_awaited()
        assert 'dlq_ack' not in order and 'commit' not in order
    assert persist.await_count == (0 if origin == 'schema' else 2)
    worker._llm_triage.assert_not_awaited()
    worker._consumer.stop.assert_awaited_once()
    reset_governor()
