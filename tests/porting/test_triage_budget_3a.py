"""Policy/transaction/request/stop boundaries; services are explicit substitutes."""
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.llm import contract
from app.workers import triage_budget as budget, triage_delivery as delivery
from app.workers.fused_alert_consumer import FusedAlertTriageWorker
from app.workers.entity_lane import EntityLanes

TENANT = UUID('11111111-1111-1111-1111-111111111111')
POLICY = budget.Policy(3600, 2, 40000, 1)


@pytest.mark.parametrize('first',['app.llm.factory','app.workers.triage_budget','app.workers.fused_alert_consumer'])
def test_independent_process_import_orders(first):
    result=subprocess.run([sys.executable,'-c',f'import importlib;importlib.import_module({first!r});import app.main'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def policy_file(tmp_path, monkeypatch, **values):
    p = tmp_path / 'policy.json'
    p.write_text(json.dumps({'schema_version': 1, 'tenants': {str(TENANT): {**POLICY.__dict__, **values}}}))
    monkeypatch.setenv(budget.POLICY_FILE_ENV, str(p))
    return p


def test_policy_opt_in_and_tenant_failure(tmp_path, monkeypatch):
    monkeypatch.delenv(budget.POLICY_FILE_ENV, raising=False)
    assert budget.policy_for(TENANT) is None
    policy_file(tmp_path, monkeypatch)
    assert budget.policy_for(TENANT) == POLICY
    with pytest.raises(budget.BudgetHold): budget.policy_for(uuid4())


@pytest.mark.parametrize('field,value', [('max_calls',0),('max_calls',True),('max_unsettled',9),
                                        ('window_seconds',-1),('max_reserved_tokens','40000'),('unknown',1)])
def test_invalid_policy_fails_closed(tmp_path, monkeypatch, field, value):
    policy_file(tmp_path, monkeypatch, **{field:value})
    with pytest.raises(budget.BudgetHold): budget.policy_for(TENANT)


@pytest.mark.asyncio
@pytest.mark.parametrize('calls,tokens,unsettled,allowed', [(0,0,0,True),(1,20000,0,True),
                                                          (2,40000,0,False),(0,30000,0,False),(0,0,1,False)])
async def test_locked_admission_counts_reserved_unknown_and_prior_versions(calls,tokens,unsettled,allowed):
    order = []
    async def execute(sql,*args): order.append('lock'); assert 'pg_advisory_xact_lock' in sql
    async def fetch(sql,*args):
        order.append('read')
        assert 'policy_sha256 =' not in sql and 'settled_at IS NULL' in sql
        assert args == (TENANT,3600)
        return dict(calls=calls,tokens=tokens,unsettled=unsettled)
    connection = SimpleNamespace(execute=execute,fetchrow=fetch)
    if allowed: await budget.check_locked(connection,TENANT,POLICY)
    else:
        with pytest.raises(budget.BudgetHold): await budget.check_locked(connection,TENANT,POLICY)
    assert order == ['lock','read']


@pytest.mark.asyncio
async def test_claim_budget_and_start_share_commit_or_rollback(monkeypatch):
    sys.path.insert(0,str(Path(__file__).parent))
    import test_triage_delivery_3a as fixture
    for rejected_at in ['check','reserve','success']:
        db = fixture.Database()
        monkeypatch.setattr(delivery.ledger,'get_pool',AsyncMock(return_value=db.pool()))
        async def check(conn,*args):
            assert conn.active and conn.pending_run is None
            if rejected_at == 'check': raise budget.BudgetHold('unit cap')
        async def reserve(conn,**kwargs):
            assert conn.active and conn.pending_run and conn.pending_event
            assert kwargs['policy'] == POLICY
            if rejected_at == 'reserve': raise RuntimeError('unit insert rollback')
        monkeypatch.setattr(budget,'check_locked',check)
        monkeypatch.setattr(budget,'reserve',reserve)
        if rejected_at == 'success':
            assert await delivery.claim(**fixture.FIELDS,budget=POLICY) is None
            assert db.commits == 1 and db.run and len(db.events)==1
        else:
            with pytest.raises(delivery.LedgerPersistError): await delivery.claim(**fixture.FIELDS,budget=POLICY)
            assert db.rollbacks == 1 and db.run is None and not db.events


def model():
    return SimpleNamespace(model_name='unit',max_tokens=512,request_timeout=45.0,
                           root_async_client=SimpleNamespace(max_retries=0,timeout=45.0),extra_body={'max_tokens':512})


@pytest.mark.asyncio
async def test_request_intent_once_response_usage_and_scope_reset(monkeypatch):
    updates = AsyncMock()
    monkeypatch.setattr(budget,'_update',updates)
    invocation = budget.Invocation(uuid4(),TENANT,lambda:False)
    llm = model()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content='unit response',usage_metadata={'input_tokens':3,'output_tokens':2,'total_tokens':5}))
    with budget.invocation_scope(invocation):
        await contract.safe_ainvoke(llm,[HumanMessage(content='bounded unit evidence')])
        with pytest.raises(budget.BudgetHold):
            await contract.safe_ainvoke(llm,[HumanMessage(content='bounded unit evidence')])
    assert budget.current_invocation() is None and invocation.request_marked and invocation.response_seen
    assert llm.ainvoke.await_count == 1 and updates.await_count == 2
    assert updates.call_args.args[-1] == 5


@pytest.mark.asyncio
@pytest.mark.parametrize('fault',['retries','output','bytes','stopping'])
async def test_bad_request_or_stop_does_not_reach_model(monkeypatch,fault):
    update = AsyncMock();monkeypatch.setattr(budget,'_update',update)
    invocation = budget.Invocation(uuid4(),TENANT,lambda:fault=='stopping')
    llm=model();llm.ainvoke=AsyncMock()
    if fault=='retries':llm.root_async_client.max_retries=2
    if fault=='output':llm.max_tokens=513
    text='bounded' if fault!='bytes' else '字'*6000
    with budget.invocation_scope(invocation),pytest.raises(budget.BudgetHold):
        await contract.safe_ainvoke(llm,[HumanMessage(content=text)])
    update.assert_not_awaited();llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_response_missing_usage_is_null_and_over_reservation_stays_unknown(monkeypatch):
    update=AsyncMock();monkeypatch.setattr(budget,'_update',update)
    invocation=budget.Invocation(uuid4(),TENANT,lambda:False,request_marked=True)
    await invocation.responded(AIMessage(content='no usage'))
    assert update.call_args.args[-1] is None
    with pytest.raises(budget.BudgetHold):
        await invocation.responded(SimpleNamespace(usage_metadata={'total_tokens':20001}))
    assert update.await_count==1


@pytest.mark.asyncio
async def test_request_cancel_keeps_reserved_charge_and_no_fake_response(monkeypatch):
    update=AsyncMock();monkeypatch.setattr(budget,'_update',update)
    entered=asyncio.Event()
    async def never(*a,**k): entered.set();await asyncio.Event().wait()
    llm=model();llm.ainvoke=AsyncMock(side_effect=never)
    invocation=budget.Invocation(uuid4(),TENANT,lambda:False)
    async def run():
        with budget.invocation_scope(invocation):await contract.safe_ainvoke(llm,[HumanMessage(content='cancel unit')])
    task=asyncio.create_task(run());await asyncio.wait_for(entered.wait(),1);task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    assert invocation.request_marked and not invocation.response_seen and update.await_count==1


@pytest.mark.asyncio
async def test_stop_waits_for_returned_result_and_rejects_new_work():
    worker=FusedAlertTriageWorker(bootstrap_servers='unused')
    entered=asyncio.Event();release=asyncio.Event()
    async def saving():entered.set();await release.wait()
    await worker._lanes.submit('unit',saving);await entered.wait()
    task=asyncio.create_task(worker.stop());await asyncio.sleep(0)
    assert not task.done()
    with pytest.raises(budget.BudgetHold):await worker._process_with_retry({})
    release.set();await task
    assert worker._lanes.in_flight==0


@pytest.mark.asyncio
async def test_cancel_joins_started_and_not_yet_started_lanes():
    lanes=EntityLanes(1)
    async def never():await asyncio.Event().wait()
    await lanes.submit('first',never)
    await lanes.submit('second',never)
    await lanes.cancel()
    assert lanes.in_flight==lanes.tracked_entities==0


@pytest.mark.asyncio
async def test_budget_hold_is_not_retried_or_sent_to_dlq():
    worker=FusedAlertTriageWorker(bootstrap_servers='unused',max_attempts=3)
    worker.triage=AsyncMock(side_effect=budget.BudgetHold('unit hold'))
    worker._send_to_dlq=AsyncMock()
    # Use the already validated source-v1 unit input.
    sys.path.insert(0,str(Path(__file__).parent))
    from test_triage_recovery_3a import envelope
    with pytest.raises(budget.BudgetHold):await worker._process_with_retry(envelope())
    assert worker.triage.await_count==1
    worker._send_to_dlq.assert_not_awaited()
