"""Real worker control flow with explicit persistence/model/reader substitutes.

No remote service or model is invoked. SQL claim uniqueness and live Kafka
offsets are separate tests; these cases pin the worker's returned-result and
source/usage preservation rather than grading a substituted model answer.
"""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.cost_governor import CostGovernor
from app.investigator import ledger
from app.models.state import AgentStatus
from app.replay.shadow import ShadowTriageWriter
from app.workers import fused_alert_consumer as module
from app.workers import shadow_mode
from app.workers.triage_persistence import LiveTriageWriter

TENANT = '11111111-1111-1111-1111-111111111111'
ALERT = '22222222-2222-2222-2222-222222222222'
READS = ('organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read',
         'recent_dispositions_read', 'identity_context_read')


def envelope(alert_id=ALERT, tenant=TENANT):
    return {'tenant_id': tenant, 'alert_row_id': alert_id, 'id': alert_id,
            'incident_id': '33333333-3333-3333-3333-333333333333',
            'alert': {'id': alert_id, 'tenant_id': tenant, 'source': 'recovery-unit',
                      'title': 'Bounded source preservation', 'rule_id': 'R-RECOVERY',
                      'hostname': 'RECOVERY-HOST', 'severity': 'medium', 'risk_score': None,
                      'raw_event': {'current_evidence': 'controlled unit material'}}}


class UnexpectedPath(BaseException):
    pass


@pytest.fixture
def harness(monkeypatch):
    for name in ('AISOC_AGENT_MEMORY_SUPPRESSION', 'AISOC_AGENT_MEMORY_WRITEBACK',
                 'AISOC_AGENT_RAISE_APPROVALS', 'AISOC_AGENT_ESCALATE_TO_GRAPH',
                 'AISOC_ALERT_PLAYBOOKS_ENABLED'):
        monkeypatch.setenv(name, '0')
    monkeypatch.setenv('AISOC_DETERMINISTIC', '0')
    governor = CostGovernor()
    monkeypatch.setattr(module, 'get_governor', lambda: governor)
    lookup, claim = AsyncMock(return_value=None), AsyncMock(return_value=None)
    monkeypatch.setattr(module.triage_delivery, 'lookup', lookup)
    monkeypatch.setattr(module.triage_delivery, 'claim', claim)
    config = SimpleNamespace(allowed=True, api_key='synthetic-unit-not-a-credential', model='unit',
                             base_url=None, api_key_from_tenant=False, base_url_from_tenant=False,
                             model_from_tenant=False)
    monkeypatch.setattr(module, 'resolve_llm_config', AsyncMock(return_value=config))
    persist = AsyncMock(return_value=True)
    monkeypatch.setattr(ledger, 'persist_auto_triage', persist)
    trackers = []

    class Tracker:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.total_tokens = self.measured_call_count = self.estimated_call_count = self.unpriced_call_count = 0
            self.measured_cost_usd = self.estimated_cost_usd = None
            self.resolved_models = ()
        async def __aenter__(self):
            trackers.append(self)
            return self
        async def __aexit__(self, *args): return False

    monkeypatch.setattr(module, 'CostTracker', Tracker)
    playbook = AsyncMock(return_value=module.alert_trigger.TriggerOutcome(skipped_reason='unit disabled'))
    monkeypatch.setattr(module.alert_trigger, 'run_for_alert', playbook)
    return SimpleNamespace(monkeypatch=monkeypatch, governor=governor, lookup=lookup, claim=claim,
                            persist=persist, trackers=trackers, playbook=playbook)


def worker_with_model(harness, *, max_attempts=2, writer=None):
    receipt = {'status': 'success', 'statements': [{'statement': 'first source text', 'observations': 2}],
               'prompt_block': 'bounded original organisation guidance', 'prompt_sha256': 'unit-original-org-hash'}
    reader = SimpleNamespace(fetch_organisation_memory=AsyncMock(return_value=deepcopy(receipt)))
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused', max_attempts=max_attempts,
                                            writer=writer, context_reader=reader)
    worker._sink_for = AsyncMock(return_value=worker._writer)
    worker._retry_backoff = lambda attempt: 0
    worker._send_to_dlq = AsyncMock()
    worker._maybe_escalate = AsyncMock()
    worker._raise_approvals = AsyncMock(return_value=[])
    worker._write_back_to_source = AsyncMock(return_value=None)
    attachments = []
    for method, kind in (('_attach_tenant_skill', 'tenant_skill_read'),
                         ('_attach_runbooks', 'knowledge_base_read'),
                         ('_attach_recent_dispositions', 'recent_dispositions_read'),
                         ('_attach_identity_context', 'identity_context_read')):
        async def attach(state, kind=kind):
            setattr(state, kind, {'status': 'success', 'prompt_block': 'original ' + kind,
                                  'source_rows': [{'text': 'exact original ' + kind}],
                                  'prompt_sha256': 'hash-' + kind})
        mock = AsyncMock(side_effect=attach)
        setattr(worker, method, mock)
        attachments.append(mock)
    states = []

    async def model(state):
        harness.trackers[-1].total_tokens = 37
        harness.trackers[-1].unpriced_call_count = 1
        harness.trackers[-1].resolved_models = ('observed:unit-model',)
        state.verdict, state.confidence = 'needs_review', .73
        state.status = AgentStatus.RUNNING
        state.findings = ['First model-method substitute result; no real model request.']
        state.confidence_basis = ['Original bounded evidence only.']
        state.injection_suspected = True
        state.record_llm_exchange(agent='auto_triage', purpose='unit-probe', model='observed:unit-model',
                                  prompt='original literal prompt', response='original literal response', duration_ms=9)
        states.append(state)
        return state, 'llm'

    worker._llm_triage = AsyncMock(side_effect=model)
    return SimpleNamespace(worker=worker, reader=reader, attachments=attachments, states=states)


@pytest.mark.asyncio
async def test_same_process_persist_retry_preserves_full_original_tuple_and_usage(harness):
    test = worker_with_model(harness)
    saved = []

    async def persist(**fields):
        saved.append(deepcopy(fields))
        if len(saved) == 1:
            raise ledger.LedgerPersistError('unit artifact rollback')
        return True

    harness.persist.side_effect = persist
    gate = Mock(wraps=test.worker._apply_groundedness_gate)
    test.worker._apply_groundedness_gate = gate
    assert await test.worker._process_with_retry(envelope()) is True
    assert saved[0] == saved[1]
    assert saved[0]['tokens'] == 37 and saved[0]['tier'] == 'llm' and saved[0]['unpriced_call_count'] == 1
    assert saved[0]['cost_usd'] is None and saved[0]['llm_exchanges'][0]['response'] == 'original literal response'
    assert all(saved[0][kind]['status'] == 'success' for kind in READS)
    assert saved[0]['recovery_projection']['cost']['tokens'] == 37
    assert saved[0]['recovery_projection']['cost']['resolved_models'] == ['observed:unit-model']
    assert saved[0]['recovery_projection']['effect_status'] == 'not_replayed'
    assert saved[0]['recovery_projection']['schema_version'] == 1
    assert test.worker._pending() == {}
    assert len(harness.trackers) == harness.claim.await_count == harness.lookup.await_count == 1
    assert test.worker._llm_triage.await_count == gate.call_count == 1
    test.reader.fetch_organisation_memory.assert_awaited_once()
    assert all(mock.await_count == 1 for mock in test.attachments)
    assert harness.governor.spent_tokens(TENANT) == 37
    test.worker._send_to_dlq.assert_not_awaited()
    test.worker._maybe_escalate.assert_not_awaited()
    test.worker._raise_approvals.assert_not_awaited()
    test.worker._write_back_to_source.assert_not_awaited()
    assert module._BROKER_DELIVERY.get() is False


@pytest.mark.asyncio
async def test_failed_result_is_deeply_preserved_after_external_state_mutation(harness):
    test = worker_with_model(harness, max_attempts=1)
    recorded = []

    async def persist(**fields):
        recorded.append(deepcopy(fields))
        if len(recorded) == 1: raise ledger.LedgerPersistError('first save failed')
        return True

    harness.persist.side_effect = persist
    assert await test.worker._process_with_retry(envelope()) is False
    test.states[0].organisation_memory_read['statements'][0]['statement'] = 'mutated later source'
    test.states[0].identity_context_read['source_rows'][0]['text'] = 'mutated later identity'
    test.states[0].findings.append('not the original model result')
    harness.trackers[0].total_tokens = 999
    assert await test.worker._process_with_retry(envelope()) is True
    assert recorded[0] == recorded[1]
    assert test.worker._llm_triage.await_count == 1 and not test.worker._pending()


@pytest.mark.asyncio
async def test_completed_lookup_returns_before_rules_readers_governor_or_effects(harness):
    prior = {'schema_version': 1, 'run_id': str(module.build_state(envelope()).run_id),
             'tenant_id': TENANT, 'verdict': 'needs_review', 'tier': 'llm',
             'cost': {'tokens': 37, 'measured_usd': None}, 'reused_persisted': True,
             'effect_status': 'not_replayed'}
    harness.lookup.return_value = deepcopy(prior)
    business = SimpleNamespace(apply_for_tenant=AsyncMock(side_effect=UnexpectedPath('business rules')))
    worker = module.FusedAlertTriageWorker(bootstrap_servers='unused', business_context=business)
    worker._sink_for = AsyncMock(side_effect=UnexpectedPath('shadow policy'))
    worker._send_to_dlq = AsyncMock()
    harness.monkeypatch.setattr(module, 'get_governor', lambda: (_ for _ in ()).throw(UnexpectedPath('governor')))
    actual = []
    original = worker.triage
    async def observe(message):
        result = await original(message); actual.append(result); return result
    worker.triage = observe
    assert await worker._process_with_retry(envelope()) is True
    assert actual == [prior] and actual[0] is not harness.lookup.return_value
    harness.claim.assert_not_awaited(); harness.persist.assert_not_awaited()
    business.apply_for_tenant.assert_not_awaited(); worker._sink_for.assert_not_awaited()
    worker._send_to_dlq.assert_not_awaited()
    assert not harness.trackers and module._BROKER_DELIVERY.get() is False


@pytest.mark.asyncio
async def test_lookup_failure_is_not_a_missing_result_and_context_is_reset(harness):
    test = worker_with_model(harness, max_attempts=2)
    harness.lookup.side_effect = ledger.LedgerPersistError('PG read unavailable, not absent')
    assert await test.worker._process_with_retry(envelope()) is False
    assert harness.lookup.await_count == 2
    harness.claim.assert_not_awaited(); harness.persist.assert_not_awaited()
    test.worker._llm_triage.assert_not_awaited()
    test.worker._send_to_dlq.assert_awaited_once()
    assert test.worker._send_to_dlq.call_args.kwargs['stage'] == 'persist'
    assert not test.worker._pending() and module._BROKER_DELIVERY.get() is False
    # A direct caller retains its original contract even after a broker error.
    assert (await test.worker.triage(envelope()))['tier'] == 'llm'
    assert harness.lookup.await_count == 2


@pytest.mark.asyncio
async def test_claim_prior_result_returns_without_model_or_persistence(harness):
    test = worker_with_model(harness)
    prior = {'schema_version': 1, 'verdict': 'needs_review', 'effect_status': 'not_replayed', 'reused_persisted': True}
    harness.claim.return_value = prior
    assert await test.worker._process_with_retry(envelope()) is True
    test.worker._llm_triage.assert_not_awaited(); harness.persist.assert_not_awaited()
    test.reader.fetch_organisation_memory.assert_not_awaited()
    assert not harness.trackers and not test.worker._pending()
    harness.claim.assert_awaited_once_with(run_id=module.build_state(envelope()).run_id,
        tenant_id=module.build_state(envelope()).tenant_id, alert_id=ALERT, workflow_version=module.WORKFLOW_VERSION)


@pytest.mark.asyncio
async def test_started_without_returned_result_never_reenters_model(harness):
    test = worker_with_model(harness, max_attempts=2)
    test.worker._llm_triage.side_effect = RuntimeError('method interrupted before returning a result')
    assert await test.worker._process_with_retry(envelope()) is False
    test.worker._llm_triage.assert_awaited_once()
    harness.claim.assert_awaited_once(); harness.persist.assert_not_awaited()
    assert len(test.worker._pending()) == 1 and next(iter(test.worker._pending().values())) is None
    assert test.worker._send_to_dlq.call_args.kwargs['stage'] == 'persist'


@pytest.mark.asyncio
async def test_fresh_worker_started_unknown_lookup_stops_without_model(harness):
    test = worker_with_model(harness, max_attempts=1)
    harness.lookup.side_effect = ledger.LedgerPersistError('persisted started state; result unknown')
    assert await test.worker._process_with_retry(envelope()) is False
    harness.claim.assert_not_awaited(); harness.persist.assert_not_awaited()
    test.worker._llm_triage.assert_not_awaited()
    assert not test.worker._pending()


@pytest.mark.asyncio
async def test_pending_capacity_closes_before_claim_or_model_but_completed_can_return(harness):
    test = worker_with_model(harness, max_attempts=1)
    test.worker._pending().update({(str(uuid4()), TENANT): None for _ in range(128)})
    assert await test.worker._process_with_retry(envelope()) is False
    assert len(test.worker._pending()) == 128
    harness.claim.assert_not_awaited(); test.worker._llm_triage.assert_not_awaited()
    test.reader.fetch_organisation_memory.assert_not_awaited()
    harness.lookup.return_value = {'schema_version': 1, 'verdict': 'needs_review', 'reused_persisted': True}
    assert await test.worker._process_with_retry(envelope()) is True
    assert len(test.worker._pending()) == 128


@pytest.mark.asyncio
async def test_pending_uses_exact_run_not_governor_pattern_identity(harness):
    test = worker_with_model(harness, max_attempts=1)
    recorded = []
    async def persist(**fields):
        recorded.append(deepcopy(fields))
        if len(recorded) == 1: raise ledger.LedgerPersistError('pending original result')
        return True
    harness.persist.side_effect = persist
    first, other = envelope(), envelope('44444444-4444-4444-4444-444444444444')
    assert harness.governor.evidence_fingerprint(TENANT, module.build_state(first).raw_alert) == harness.governor.evidence_fingerprint(TENANT, module.build_state(other).raw_alert)
    assert await test.worker._process_with_retry(first) is False
    assert await test.worker._process_with_retry(other) is True
    assert recorded[1]['alert_id'] != recorded[0]['alert_id'] and recorded[1]['run_id'] != recorded[0]['run_id']
    # C02 ordinary live must assess the new Run independently, even though
    # the shared pattern matches an older Run whose result awaits saving.
    assert recorded[1]['tokens'] == 37 and recorded[1]['tier'] == 'llm'
    assert all(recorded[1][kind]['status'] == 'success' for kind in READS)
    assert await test.worker._process_with_retry(first) is True
    assert recorded[2] == recorded[0] and not test.worker._pending()
    assert harness.claim.await_count == 2 and test.worker._llm_triage.await_count == 2
    assert harness.governor.spent_tokens(TENANT) == 74
    assert test.reader.fetch_organisation_memory.await_count == 2
    assert all(attachment.await_count == 2 for attachment in test.attachments)


@pytest.mark.asyncio
async def test_pending_snapshot_is_after_groundedness_demotion(harness):
    test = worker_with_model(harness)
    harness.monkeypatch.setenv('AISOC_AGENT_GROUNDEDNESS_GATE', '1')
    original_model = test.worker._llm_triage.side_effect
    async def unsupported(state):
        state, tier = await original_model(state)
        state.verdict, state.confidence, state.status = 'false_positive', .99, AgentStatus.COMPLETED
        state.findings = ['Confirmed source is 203.0.113.244 and file hash 0123456789abcdef0123456789abcdef.']
        return state, tier
    test.worker._llm_triage.side_effect = unsupported
    saved = []
    async def persist(**fields):
        saved.append(deepcopy(fields))
        if len(saved) == 1: raise ledger.LedgerPersistError('retry demoted result')
        return True
    harness.persist.side_effect = persist
    assert await test.worker._process_with_retry(envelope()) is True
    assert saved[0] == saved[1] and saved[0]['verdict'] == 'needs_review'
    assert saved[0]['recovery_projection']['verdict'] == 'needs_review'
    assert saved[0]['groundedness'] < .75


@pytest.mark.asyncio
async def test_live_shadow_completed_reuse_does_not_rewrite_shadow_decision(harness):
    test = worker_with_model(harness)
    decision = shadow_mode.ShadowDecision(tenant_ref=TENANT, alert_class='unit', alert_id=ALERT)
    sink = shadow_mode.ShadowModeTriageWriter(test.worker._writer, decision)
    test.worker._sink_for.return_value = sink
    record_shadow = AsyncMock(return_value=True)
    harness.monkeypatch.setattr(shadow_mode, 'record_shadow_decision', record_shadow)
    completed = {}
    async def persist(**fields):
        completed.update(deepcopy(fields['recovery_projection']))
        return True
    async def lookup(**fields): return deepcopy(completed) if completed else None
    harness.persist.side_effect, harness.lookup.side_effect = persist, lookup
    assert await test.worker._process_with_retry(envelope()) is True
    assert completed['shadow'] is True
    assert await test.worker._process_with_retry(envelope()) is True
    assert record_shadow.await_count == harness.persist.await_count == test.worker._llm_triage.await_count == 1
    assert test.worker._sink_for.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('live', [False, True])
async def test_direct_triage_and_historical_ids_never_use_delivery_lookup_or_claim(harness, live):
    test = worker_with_model(harness, writer=LiveTriageWriter() if live else ShadowTriageWriter())
    harness.lookup.side_effect = UnexpectedPath('direct lookup leak')
    harness.claim.side_effect = UnexpectedPath('direct claim leak')
    value = envelope('ES-HISTORICAL-1')
    result = await test.worker.triage(value)
    assert result['run_id'] == str(module.build_state(value).run_id)
    harness.lookup.assert_not_awaited(); harness.claim.assert_not_awaited()


def test_pending_maps_are_per_worker_even_without_constructor():
    first, second = object.__new__(module.FusedAlertTriageWorker), object.__new__(module.FusedAlertTriageWorker)
    first._pending()[('run', TENANT)] = None
    assert first._pending() is not second._pending() and second._pending() == {}
