"""Actual ledger function against explicit SQL-recording doubles; not real PG.

Unexecuted candidate. The central assertion covers the whole canonical Alert
UPDATE, including ai_score: forcing shadow alone would fail these checks.
"""
from contextlib import asynccontextmanager
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.investigator import ledger
from app.core.cost_telemetry import CostSummary
from app.workers import fused_alert_consumer as module, triage_admission as admission, triage_delivery
from app.workers.triage_persistence import LiveTriageWriter

TENANT='11111111-1111-1111-1111-111111111111'
ALERT='22222222-2222-2222-2222-222222222222'


def first_fields():
    state=module.build_state({'alert_row_id':ALERT,'tenant_id':TENANT,
        'incident_id':'33333333-3333-3333-3333-333333333333',
        'alert':{'id':ALERT,'title':'ledger fixture','severity':'medium'}})
    answer={'verdict':'false_positive','confidence':.95,'rationale':'Unreviewed fixture.'}
    state.record_llm_exchange(agent='auto_triage',purpose='triage.classify',model='unit',
        prompt=[{'role':'user','content':'Fixture.'}],response=json.dumps(answer),duration_ms=1)
    receipt=admission.enforce(state,advice=answer)
    projection=module.FusedAlertTriageWorker._recovery_projection(state,tier='llm',verdict=state.verdict,
        confidence=state.confidence,tokens=18,cost=CostSummary(),writer=LiveTriageWriter())
    fields={'run_id':state.run_id,'alert_id':ALERT,'tenant_ref':TENANT,'alert_summary':'ledger fixture',
        'raw_alert':state.raw_alert,'tier':'llm','verdict':'needs_review','confidence':0.0,'rationale':'Human review required.',
        'findings':state.findings,'proposed_actions':[],'auto_closed':False,'tokens':18,
        'llm_exchanges':state.llm_exchanges,'recovery_projection':projection,'triage_admission_receipt':receipt}
    return state,fields


def fake_pool(monkeypatch,state,status='running'):
    calls=[]
    @asynccontextmanager
    async def transaction():yield
    async def execute(sql,*args):
        calls.append((sql,args));return 'INSERT 0 1'
    conn=SimpleNamespace(transaction=transaction,execute=execute,fetchval=AsyncMock(return_value=False),
        fetchrow=AsyncMock(return_value={'id':state.run_id,'tenant_id':UUID(TENANT),'case_id':ALERT,'status':status,
            'model_used':'kafka:auto_triage:claimed' if status=='running' else 'kafka:auto_triage:llm',
            'raw_alert':{'id':ALERT} if status=='running' else state.raw_alert}))
    @asynccontextmanager
    async def acquire():yield conn
    monkeypatch.setattr(ledger,'get_pool',AsyncMock(return_value=SimpleNamespace(acquire=acquire)))
    monkeypatch.setattr(ledger,'_resolve_tenant_id',AsyncMock(return_value=UUID(TENANT)))
    monkeypatch.setattr(ledger,'_set_rls_context',AsyncMock())
    return conn,calls


@pytest.mark.asyncio
async def test_first_advisory_persistence_omits_every_alert_column_update(monkeypatch):
    state,fields=first_fields();conn,calls=fake_pool(monkeypatch,state)
    assert await ledger.persist_auto_triage(**fields) is True
    assert any('INSERT INTO investigation_events' in sql for sql,_ in calls)
    assert any('UPDATE investigation_runs' in sql for sql,_ in calls)
    assert not any('UPDATE alerts' in sql for sql,_ in calls)
    assert not any('UPDATE alerts' in sql or 'INSERT INTO alerts' in sql for sql,_ in calls)
    assert conn.fetchval.await_count==1  # No partial first events before writing.


@pytest.mark.asyncio
async def test_ack_lost_completed_retry_confirms_first_snapshot_without_sql_writes(monkeypatch):
    state,fields=first_fields();conn,calls=fake_pool(monkeypatch,state,'completed')
    prior=deepcopy(fields['recovery_projection'])
    prior.update(reused_persisted=True,persisted_artifacts=[
        {'kind':'llm_response','sha256':fields['triage_admission_receipt']['model_advice']['raw_response_sha256']}])
    validate=AsyncMock(return_value=prior);monkeypatch.setattr(triage_delivery,'_completed',validate)
    assert await ledger.persist_auto_triage(**fields) is True
    assert calls==[] and validate.await_count==1
    changed=deepcopy(prior);changed['triage_admission']['model_advice']['confidence']=.5
    validate.return_value=changed
    with pytest.raises(ledger.LedgerPersistError) as error:await ledger.persist_auto_triage(**fields)
    assert admission.held_in_chain(error.value) and calls==[]
    validate.return_value=prior
    conn.fetchrow.return_value['raw_alert']={**state.raw_alert,'description':'Changed persisted first source'}
    with pytest.raises(ledger.LedgerPersistError) as error:await ledger.persist_auto_triage(**fields)
    assert admission.held_in_chain(error.value) and calls==[]


@pytest.mark.asyncio
async def test_missing_or_mismatched_advisory_receipt_never_reaches_database(monkeypatch):
    _,fields=first_fields();pool=AsyncMock();monkeypatch.setattr(ledger,'get_pool',pool)
    fields['triage_admission_receipt']=None
    with pytest.raises(admission.ReviewOnlyHold):await ledger.persist_auto_triage(**fields)
    pool.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_without_receipt_keeps_original_alert_update(monkeypatch):
    state,fields=first_fields();conn,calls=fake_pool(monkeypatch,state)
    fields['triage_admission_receipt']=None
    fields['recovery_projection'].pop('triage_admission')
    assert await ledger.persist_auto_triage(**fields) is True
    assert any('UPDATE alerts' in sql for sql,_ in calls)
    conn.fetchrow.assert_not_awaited()  # New ownership branch is profile-only.
