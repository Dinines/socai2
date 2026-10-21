"""Durable live-delivery guard: transactional PG doubles, no model or broker.

Actual concurrent PG connections, query faults and Kafka offset recovery are
covered by the separate bounded operator; these tests exercise the real helper.
"""
import asyncio
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4, uuid5

import pytest

from app.investigator import ledger
from app.workers import triage_delivery as delivery

TENANT = UUID('11111111-1111-1111-1111-111111111111')
OTHER = UUID('33333333-3333-3333-3333-333333333333')
ALERT = '22222222-2222-2222-2222-222222222222'
RUN = uuid5(delivery._NAMESPACE, f'{ALERT}:auto-triage-v1')
FIELDS = dict(run_id=RUN, tenant_id=TENANT, alert_id=ALERT, workflow_version='auto-triage-v1')


def complete(*, versioned=True):
    payload = {'verdict': 'needs_review', 'confidence': .64, 'rationale': 'Synthetic evidence requires review',
               'findings': ['Synthetic finding'], 'proposed_actions': [], 'auto_closed': False}
    run = {'id': RUN, 'tenant_id': TENANT, 'case_id': ALERT, 'raw_alert': json.dumps({'id': ALERT}),
           'model_used': 'kafka:auto_triage:llm', 'status': 'completed',
           'total_tokens': 123, 'total_cost_usd': Decimal('0'), 'measured_call_count': 0,
           'estimated_cost_usd': Decimal('0'), 'estimated_call_count': 0, 'unpriced_call_count': 1}
    if versioned:
        payload['recovery'] = {'schema_version': 1, 'workflow_version': FIELDS['workflow_version'],
            'run_id': str(RUN), 'tenant_id': str(TENANT), 'alert_id': ALERT,
            'incident_id': str(uuid4()), 'shadow': True, 'verdict': 'needs_review', 'confidence': .64,
            'tier': 'llm', 'cost': {'tokens': 123, 'measured_usd': None, 'measured_calls': 0,
                'estimated_usd': None, 'estimated_calls': 0, 'unpriced_calls': 1, 'resolved_models': ['reported-alias']},
            'findings': payload['findings'][:], 'confidence_basis': [], 'business_context_rules': [],
            'business_context_policy': {}, 'proposed_actions': [], 'response_dispatched': False,
            'source_writeback': None, 'approvals_raised': [], 'effect_status': 'not_replayed'}
    event = {'id': uuid4(), 'run_id': RUN, 'tenant_id': TENANT, 'seq': 1,
             'kind': 'triage_verdict', 'agent': 'auto_triage:llm', 'payload': payload,
             'input_hash': None, 'output_hash': None}
    return run, [event], []


def artifact(event, kind, content):
    return {'id': uuid4(), 'run_id': RUN, 'tenant_id': TENANT, 'event_id': event['id'],
            'kind': kind, 'content': content, 'sha256': hashlib.sha256(content.encode()).hexdigest(),
            'size_bytes': len(content.encode())}


class Database:
    def __init__(self, rows=None):
        self.run, self.events, self.artifacts = rows or (None, [], [])
        self.calls = []
        self.lock = asyncio.Lock()
        self.fail = None
        self.commits = 0
        self.rollbacks = 0

    def pool(self):
        db = self
        class Acquire:
            async def __aenter__(self): self.conn = Connection(db); return self.conn
            async def __aexit__(self, *args): return False
        return SimpleNamespace(acquire=Acquire)


class Connection:
    def __init__(self, db):
        self.db = db
        self.active = False
        self.pending_run = None
        self.pending_event = None
        self.owns_lock = False

    def transaction(self, *, isolation):
        assert isolation == 'read_committed'
        conn = self
        class Transaction:
            async def __aenter__(self): conn.active = True
            async def __aexit__(self, typ, exc, tb):
                try:
                    if typ or conn.db.fail == 'commit':
                        conn.db.rollbacks += 1
                        if not typ: raise RuntimeError('controlled commit failure')
                    else:
                        if conn.pending_run is not None: conn.db.run = conn.pending_run
                        if conn.pending_event is not None: conn.db.events.append(conn.pending_event)
                        conn.db.commits += 1
                finally:
                    conn.active = False
                    if conn.owns_lock: conn.db.lock.release()
                return False
        return Transaction()

    async def execute(self, sql, *args):
        assert self.active
        self.db.calls.append((sql, args))
        if 'set_config' in sql:
            assert args == (str(TENANT),)
        elif 'INSERT INTO investigation_events' in sql:
            if self.db.fail == 'event': raise RuntimeError('controlled event insert failure')
            self.pending_event = {'id': args[0], 'run_id': args[1], 'tenant_id': args[2],
                                  'seq': -1, 'kind': 'triage_started', 'payload': json.loads(args[3])}
        else:
            raise AssertionError(sql)
        return 'INSERT 0 1'

    async def fetchrow(self, sql, *args):
        assert self.active
        self.db.calls.append((sql, args))
        if sql == delivery._RUN_SQL:
            if self.db.fail == 'read': raise RuntimeError('controlled select failure')
            value = deepcopy(self.db.run)
            await asyncio.sleep(0)
            return value
        if 'FROM alerts' in sql:
            if self.db.fail == 'alert': return None
            assert args == (UUID(ALERT), TENANT)
            return {'id': UUID(ALERT), 'tenant_id': TENANT}
        if 'INSERT INTO investigation_runs' in sql:
            await self.db.lock.acquire(); self.owns_lock = True
            if self.db.run is not None: return None
            self.pending_run = {'id': args[0], 'tenant_id': args[1], 'case_id': args[2],
                                'raw_alert': args[3], 'model_used': 'kafka:auto_triage:claimed', 'status': 'running'}
            return {'id': args[0]}
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        assert self.active
        self.db.calls.append((sql, args))
        assert args[:2] == (RUN, TENANT)
        if sql == delivery._EVENTS_SQL: return deepcopy(self.db.events)
        if sql == delivery._ARTIFACTS_SQL: return deepcopy(self.db.artifacts)
        raise AssertionError(sql)


@pytest.fixture
def bind(monkeypatch):
    def install(db):
        monkeypatch.setattr(ledger, 'get_pool', AsyncMock(return_value=db.pool()))
        return db
    return install


@pytest.mark.asyncio
async def test_missing_run_is_readonly_none_then_claim_commits_start(bind):
    db = bind(Database())
    assert await delivery.lookup(**FIELDS) is None
    assert db.run is None and db.events == []
    assert await delivery.claim(**FIELDS) is None
    assert db.commits == 2 and db.run['model_used'] == 'kafka:auto_triage:claimed'
    start = db.events[0]
    assert start['seq'] == -1 and start['kind'] == 'triage_started'
    assert start['payload']['workflow_version'] == FIELDS['workflow_version']
    assert start['payload']['tenant_id'] == str(TENANT) and start['payload']['alert_id'] == ALERT
    assert UUID(start['payload']['owner_token'])
    assert start['payload']['processing_started'] is True
    assert start['payload']['model_invocation_established'] is False
    assert db.calls[0][0].find('set_config') >= 0
    assert 'tenant_id' not in delivery._RUN_SQL.split('WHERE')[1]
    with pytest.raises(ledger.LedgerPersistError, match='unknown'):
        await delivery.lookup(**FIELDS)


@pytest.mark.asyncio
async def test_concurrent_claim_has_one_owner_and_one_unknown_without_lease_steal(bind):
    db = bind(Database())
    results = await asyncio.gather(delivery.claim(**FIELDS), delivery.claim(**FIELDS), return_exceptions=True)
    assert results.count(None) == 1
    assert sum(isinstance(r, ledger.LedgerPersistError) for r in results) == 1
    assert len(db.events) == 1 and db.events[0]['seq'] == -1


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['event', 'commit', 'alert', 'read'])
async def test_failed_claim_does_not_authorize_owner_or_leave_partial_rows(bind, fault):
    db = bind(Database()); db.fail = fault
    with pytest.raises(ledger.LedgerPersistError): await delivery.claim(**FIELDS)
    assert db.run is None and db.events == [] and db.rollbacks == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('method', [delivery.lookup, delivery.claim])
async def test_no_pool_is_not_missing(monkeypatch, method):
    monkeypatch.setattr(ledger, 'get_pool', AsyncMock(return_value=None))
    with pytest.raises(ledger.LedgerPersistError, match='database unavailable'): await method(**FIELDS)


@pytest.mark.asyncio
async def test_completed_v1_is_readonly_exact_first_usage_and_no_effects(bind):
    db = bind(Database(complete()))
    original = deepcopy((db.run, db.events, db.artifacts))
    result = await delivery.lookup(**FIELDS)
    assert result['recovery_format'] == 'summary_v1' and result['reused_persisted'] is True
    assert result['cost'] == db.events[0]['payload']['recovery']['cost']
    assert result['response_dispatched'] is False and result['approvals_raised'] == []
    assert result['source_writeback'] is None and result['effect_status'] == 'not_replayed'
    result['findings'].append('caller mutation')
    assert (db.run, db.events, db.artifacts) == original
    again = await delivery.claim(**FIELDS)
    assert again['findings'] == ['Synthetic finding']
    assert (db.run, db.events, db.artifacts) == original
    assert not any('INSERT' in sql or 'UPDATE' in sql for sql, _ in db.calls)


@pytest.mark.asyncio
async def test_legacy_preserves_nonzero_usage_without_inventing_source_or_measurement(bind):
    rows = complete(versioned=False)
    rows[0].update(total_tokens=987, total_cost_usd=Decimal('0.0000'), unpriced_call_count=2)
    db = bind(Database(rows))
    result = await delivery.lookup(**FIELDS)
    assert result['cost']['tokens'] == 987 and result['cost']['unpriced_calls'] == 2
    assert result['cost']['measured_usd'] is None and result['cost']['resolved_models'] is None
    assert result['shadow'] is None and result['incident_id'] is None
    assert result['recovery_format'] == 'legacy_first_verdict'
    assert 'shadow' in result['legacy_missing_fields']
    assert result['persisted_source_reads'] == {} and len(result['source_reads_not_recorded']) == 5
    assert db.run['total_tokens'] == 987


@pytest.mark.asyncio
@pytest.mark.parametrize('field,value', [('tenant_id', OTHER), ('case_id', 'another'),
    ('raw_alert', {'id': 'different'}), ('status', 'running'), ('status', 'failed'),
    ('model_used', 'policy:business_context:suppression-v1'), ('model_used', 'kafka:auto_triage:claimed')])
async def test_existing_run_identity_or_unknown_status_is_never_missing(bind, field, value):
    rows = complete(); rows[0][field] = value; bind(Database(rows))
    with pytest.raises(ledger.LedgerPersistError): await delivery.lookup(**FIELDS)


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['no_verdict', 'wrong_kind', 'bad_confidence', 'unknown_verdict',
    'wrong_recovery_tenant', 'wrong_recovery_version', 'wrong_recovery_usage', 'wrong_recovery_findings'])
async def test_invalid_first_result_is_not_reusable(bind, change):
    rows = complete(); event = rows[1][0]; payload = event['payload']
    if change == 'no_verdict': rows[1].clear()
    elif change == 'wrong_kind': event['kind'] = 'policy_decision'
    elif change == 'bad_confidence': payload['confidence'] = float('nan')
    elif change == 'unknown_verdict': payload['verdict'] = 'unknown-old-label'
    elif change == 'wrong_recovery_tenant': payload['recovery']['tenant_id'] = str(OTHER)
    elif change == 'wrong_recovery_version': payload['recovery']['schema_version'] = 2
    elif change == 'wrong_recovery_usage': payload['recovery']['cost']['tokens'] = 0
    elif change == 'wrong_recovery_findings': payload['recovery']['findings'] = []
    bind(Database(rows))
    with pytest.raises(ledger.LedgerPersistError): await delivery.lookup(**FIELDS)


@pytest.mark.asyncio
async def test_source_and_transcript_artifacts_match_first_payload_without_refetch(bind):
    rows = complete(); first = rows[1][0]
    for kind in delivery._READ_KINDS:
        receipt = {'status': 'success', 'marker': f'synthetic {kind}'}
        first['payload'][kind] = receipt
        rows[2].append(artifact(first, kind, json.dumps(receipt, sort_keys=True, ensure_ascii=False)))
    exchange = {'prompt': 'literal 原 prompt', 'response': 'literal response', 'prompt_truncated': False}
    rows[1].insert(0, {'id': uuid4(), 'run_id': RUN, 'tenant_id': TENANT,
                      'seq': 0, 'kind': 'llm_call', 'agent': 'auto_triage', 'payload': json.dumps(exchange)})
    for kind, key in [('llm_prompt', 'prompt'), ('llm_response', 'response')]:
        rows[2].append(artifact(first, kind, exchange[key]))
    db = bind(Database(rows)); before = deepcopy(rows)
    result = await delivery.lookup(**FIELDS)
    assert len(result['persisted_source_reads']) == 5 and len(result['persisted_artifacts']) == 7
    assert result['source_reads_not_recorded'] == result['source_artifacts_not_recorded'] == []
    assert (db.run, db.events, db.artifacts) == before


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['hash', 'bytes', 'source_mismatch', 'duplicate', 'wrong_tenant', 'wrong_event', 'transcript_mismatch'])
async def test_changed_artifact_fails_closed(bind, fault):
    rows = complete(); first = rows[1][0]; receipt = {'status': 'success', 'adopted': ['source']}
    first['payload']['organisation_memory_read'] = receipt
    a = artifact(first, 'organisation_memory_read', json.dumps(receipt)); rows[2].append(a)
    if fault == 'hash': a['sha256'] = '0' * 64
    elif fault == 'bytes': a['size_bytes'] += 1
    elif fault == 'source_mismatch': first['payload']['organisation_memory_read'] = {'status': 'no_match'}
    elif fault == 'duplicate': rows[2].append(deepcopy(a))
    elif fault == 'wrong_tenant': a['tenant_id'] = OTHER
    elif fault == 'wrong_event': a['event_id'] = uuid4()
    elif fault == 'transcript_mismatch': rows[2].append(artifact(first, 'llm_prompt', 'unverifiable prompt'))
    bind(Database(rows))
    with pytest.raises(ledger.LedgerPersistError): await delivery.lookup(**FIELDS)


@pytest.mark.asyncio
@pytest.mark.parametrize('field,value', [('run_id', str(RUN)), ('tenant_id', 'default'),
    ('alert_id', 'source-id'), ('workflow_version', ''), ('workflow_version', None)])
async def test_invalid_arguments_never_access_pool(monkeypatch, field, value):
    pool = AsyncMock(); monkeypatch.setattr(ledger, 'get_pool', pool)
    with pytest.raises(ledger.LedgerPersistError): await delivery.lookup(**(FIELDS | {field: value}))
    pool.assert_not_awaited()


@pytest.mark.parametrize('modules', [
    ['app.workers.triage_delivery', 'app.workers.fused_alert_consumer'],
    ['app.workers.fused_alert_consumer', 'app.workers.triage_delivery'],
])
def test_fresh_process_delivery_and_worker_import_orders(modules):
    import subprocess
    import sys
    script = 'import importlib\n' + '\n'.join(f'importlib.import_module({m!r})' for m in modules)
    result = subprocess.run([sys.executable, '-c', script], text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_delivery_namespace_and_workflow_match_live_worker():
    from app.workers import fused_alert_consumer as worker
    assert delivery._NAMESPACE == worker._NAMESPACE
    assert FIELDS['workflow_version'] == worker.WORKFLOW_VERSION


@pytest.mark.asyncio
async def test_different_workflow_with_same_run_is_rejected_before_db(monkeypatch):
    pool = AsyncMock(); monkeypatch.setattr(ledger, 'get_pool', pool)
    with pytest.raises(ledger.LedgerPersistError, match='workflow identity'):
        await delivery.lookup(**(FIELDS | {'workflow_version': 'changed-workflow'}))
    pool.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('missing', ['organisation_memory_read', 'llm_prompt', 'llm_response'])
async def test_recorded_first_source_or_transcript_requires_its_artifact(bind, missing):
    rows = complete(); first = rows[1][0]
    if missing == 'organisation_memory_read':
        first['payload'][missing] = {'status': 'success', 'statements': []}
    else:
        exchange = {'prompt': 'literal prompt', 'response': 'literal response'}
        rows[1].insert(0, {'id': uuid4(), 'run_id': RUN, 'tenant_id': TENANT, 'seq': 0,
                          'kind': 'llm_call', 'agent': 'auto_triage', 'payload': exchange})
        for kind, key in [('llm_prompt', 'prompt'), ('llm_response', 'response')]:
            if kind != missing: rows[2].append(artifact(first, kind, exchange[key]))
    bind(Database(rows))
    with pytest.raises(ledger.LedgerPersistError, match='artifact is missing'):
        await delivery.lookup(**FIELDS)


@pytest.mark.asyncio
@pytest.mark.parametrize('broken', ['exchange', 'call', 'verdict', 'missing_call'])
async def test_transcript_hashes_are_linked_across_call_and_first_verdict(bind, broken):
    rows = complete(); first = rows[1][0]
    exchange = {'prompt': 'bounded literal', 'response': 'reply', 'prompt_truncated': True,
                'input_hash': 'a' * 64, 'output_hash': 'b' * 64}
    call = {'id': uuid4(), 'run_id': RUN, 'tenant_id': TENANT, 'seq': 0,
            'kind': 'llm_call', 'agent': 'auto_triage', 'payload': exchange,
            'input_hash': exchange['input_hash'], 'output_hash': exchange['output_hash']}
    first['input_hash'], first['output_hash'] = exchange['input_hash'], exchange['output_hash']
    rows[1].insert(0, call)
    for kind, key in [('llm_prompt', 'prompt'), ('llm_response', 'response')]:
        rows[2].append(artifact(first, kind, exchange[key]))
    if broken == 'exchange': exchange['input_hash'] = 'c' * 64
    elif broken == 'call': call['output_hash'] = 'c' * 64
    elif broken == 'verdict': first['input_hash'] = None
    elif broken == 'missing_call': rows[1].pop(0)
    bind(Database(rows))
    with pytest.raises(ledger.LedgerPersistError, match='hash'):
        await delivery.lookup(**FIELDS)


@pytest.mark.asyncio
async def test_truncated_transcript_links_original_hash_without_hashing_bounded_copy(bind):
    rows = complete(); first = rows[1][0]
    exchange = {'prompt': 'bounded copy', 'response': 'reply', 'prompt_truncated': True,
                'input_hash': 'a' * 64, 'output_hash': 'b' * 64}
    first['input_hash'], first['output_hash'] = exchange['input_hash'], exchange['output_hash']
    rows[1].insert(0, {'id': uuid4(), 'run_id': RUN, 'tenant_id': TENANT, 'seq': 0,
                      'kind': 'llm_call', 'agent': 'auto_triage', 'payload': exchange,
                      'input_hash': exchange['input_hash'], 'output_hash': exchange['output_hash']})
    for kind, key in [('llm_prompt', 'prompt'), ('llm_response', 'response')]:
        rows[2].append(artifact(first, kind, exchange[key]))
    bind(Database(rows))
    result = await delivery.lookup(**FIELDS)
    assert result['reused_persisted'] is True and len(result['persisted_artifacts']) == 2
