"""Failed policy writes must not become confirmed cached versions."""
from datetime import UTC,datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock,MagicMock
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.api.v1.endpoints import business_context as ep

@pytest.fixture(autouse=True)
def isolate():
    ep._reset_store_for_tests()
    yield
    ep._reset_store_for_tests()

@pytest.mark.asyncio
async def test_failed_save_preserves_confirmed_cache():
    tenant=uuid4();old={'yaml':'rules: []','enabled':True,'updated_at':datetime.now(UTC)}
    ep._rule_store[tenant]=old.copy();db=SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError('injected failure')),commit=AsyncMock())
    with pytest.raises(HTTPException) as exc:await ep._persist_for(db,tenant,yaml_text='rules: [unconfirmed]',enabled=True)
    assert exc.value.status_code==503 and ep._rule_store[tenant]==old
    cached=await ep._load_for(db,tenant)
    assert cached['yaml']==old['yaml'] and cached['load_status']=='stale_cache'

@pytest.mark.asyncio
async def test_cold_read_failure_is_not_reported_as_empty_policy():
    db=SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError('injected failure')))
    with pytest.raises(HTTPException) as exc:await ep._load_for(db,uuid4())
    assert exc.value.status_code==503

@pytest.mark.asyncio
async def test_repeated_get_has_stable_content_revision_despite_local_counter():
    tenant=uuid4();user=SimpleNamespace(tenant_id=tenant,require_permission_db=AsyncMock())
    result=MagicMock();result.first.return_value=('rules: []',True,datetime.now(UTC))
    db=SimpleNamespace(execute=AsyncMock(return_value=result))
    a=await ep.get_rules(user,db);b=await ep.get_rules(user,db)
    assert b.version>a.version and a.policy_revision==b.policy_revision
    assert a.load_status==b.load_status=='current'
    assert ep.policy_revision('rules: []',False)!=a.policy_revision
