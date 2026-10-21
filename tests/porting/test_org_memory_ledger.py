"""Memory provenance is part of the first-write verdict transaction, not a later rewrite."""
import hashlib
import json
from uuid import uuid4

import pytest
from app.investigator import ledger


@pytest.mark.asyncio
@pytest.mark.parametrize('inserted', [True, False])
async def test_memory_receipt_is_atomic_and_not_duplicated(monkeypatch, inserted):
    tenant=uuid4();calls=[];inside=False
    class Tx:
        async def __aenter__(self):
            nonlocal inside
            inside=True
        async def __aexit__(self,*args):
            nonlocal inside
            inside=False
    class Conn:
        def transaction(self):return Tx()
        async def execute(self,sql,*args):
            calls.append((sql,args,inside))
            return 'INSERT 0 0' if 'triage_verdict' in sql and not inserted else 'INSERT 0 1'
    conn=Conn()
    class Acquire:
        async def __aenter__(self):return conn
        async def __aexit__(self,*args):return False
    class Pool:
        def acquire(self):return Acquire()
    async def pool():return Pool()
    async def resolve(*args):return tenant
    monkeypatch.setattr(ledger,'get_pool',pool);monkeypatch.setattr(ledger,'_resolve_tenant_id',resolve)
    read={'status':'unavailable','reason':'auth_failed','tenant_id':str(tenant),'statements':[],'adopted_count':0}
    assert await ledger.persist_auto_triage(run_id=uuid4(),alert_id=str(uuid4()),tenant_ref=str(tenant),alert_summary='s',raw_alert={},tier='llm',verdict='needs_review',confidence=.7,rationale='insufficient',organisation_memory_read=read)
    verdict=next(x for x in calls if 'triage_verdict' in x[0])
    assert json.loads(verdict[1][5])['organisation_memory_read']==read and verdict[2]
    rls=next(x for x in calls if "set_config('app.current_tenant_id'" in x[0])
    assert rls[2], 'Transaction-local RLS must be set inside the verdict transaction'
    artifacts=[x for x in calls if 'INSERT INTO investigation_artifacts' in x[0]]
    assert len(artifacts)==int(inserted)
    if inserted:
        _,args,in_tx=artifacts[0]
        assert in_tx and args[4]=='organisation_memory_read'
        assert args[2]==verdict[1][0], 'The receipt must explain the event inserted in this transaction'
        assert json.loads(args[5])==read
        assert args[6]==hashlib.sha256(args[5].encode()).hexdigest() and args[7]==len(args[5].encode())


@pytest.mark.asyncio
async def test_memory_artifact_failure_rolls_back_verdict_and_raises_typed_error(monkeypatch):
    """A transaction double stages writes; the live-PG rollback is a separate gate."""
    tenant=uuid4()
    class Tx:
        async def __aenter__(self):
            conn.inside=True
        async def __aexit__(self,exc_type,exc,tb):
            if exc_type is None:
                conn.committed.extend(conn.pending)
                conn.commit_count+=1
            else:
                conn.rollback_count+=1
            conn.pending.clear()
            conn.inside=False
            return False
    class Conn:
        def __init__(self):
            self.inside=False
            self.pending=[]
            self.committed=[('preexisting material',())]
            self.calls=[]
            self.commit_count=0
            self.rollback_count=0
            self.staged_at_failure=[]
        def transaction(self):return Tx()
        async def execute(self,sql,*args):
            self.calls.append((sql,args,self.inside))
            assert self.inside, 'Every scoped write and RLS setup belongs to the transaction'
            if 'INSERT INTO investigation_artifacts' in sql:
                self.staged_at_failure=list(self.pending)
                raise RuntimeError('injected memory artifact failure')
            if sql.lstrip().startswith(('INSERT','UPDATE')):
                self.pending.append((sql,args))
            return 'INSERT 0 1'
    conn=Conn()
    class Acquire:
        async def __aenter__(self):return conn
        async def __aexit__(self,*args):return False
    class Pool:
        def acquire(self):return Acquire()
    async def pool():return Pool()
    async def resolve(*args):return tenant
    monkeypatch.setattr(ledger,'get_pool',pool)
    monkeypatch.setattr(ledger,'_resolve_tenant_id',resolve)
    read={'status':'success','tenant_id':str(tenant),'statements':[{'statement':'expected maintenance'}],'adopted_count':1}

    with pytest.raises(ledger.LedgerPersistError,match='injected memory artifact failure') as exc:
        await ledger.persist_auto_triage(run_id=uuid4(),alert_id=str(uuid4()),tenant_ref=str(tenant),alert_summary='s',raw_alert={},tier='llm',verdict='needs_review',confidence=.7,rationale='insufficient',organisation_memory_read=read)

    assert isinstance(exc.value.__cause__,RuntimeError)
    assert any('INSERT INTO investigation_runs' in sql for sql,_ in conn.staged_at_failure)
    assert any('triage_verdict' in sql for sql,_ in conn.staged_at_failure)
    assert any('INSERT INTO investigation_artifacts' in sql for sql,_,_ in conn.calls)
    assert conn.rollback_count==1 and conn.commit_count==0
    assert conn.pending==[] and conn.committed==[('preexisting material',())]
    assert not conn.inside
