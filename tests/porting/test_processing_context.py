"""Context provenance, ambiguity and failed-read boundaries, not implementation mirrors."""
from contextlib import asynccontextmanager
from datetime import UTC,datetime
from types import SimpleNamespace
from uuid import UUID
import pytest
from app.services.processing_context import collect_processing_context

def alert():
    return SimpleNamespace(id=UUID(int=1),tenant_id=UUID(int=2),severity='medium',priority=50,
        affected_hosts=['socai2-host'],affected_users=['SVC-Test'],affected_ips=['198.18.5.1'],
        created_at=datetime.now(UTC),event_time=datetime.now(UTC))

class DB:
    def __init__(self,assets=None,identities=None,vulns=None,history=None,fail=None):
        self.rows=[assets or [],identities or [],vulns or [],history or []];self.fail=fail;self.calls=[];self.rolled_back=False
    @asynccontextmanager
    async def begin_nested(self):
        try:yield self
        except Exception:self.rolled_back=True;raise
    async def execute(self,stmt,params=None):
        query=str(stmt)
        if query.startswith('SET LOCAL'):return None
        self.calls.append((query,params))
        index=0 if 'FROM assets a' in query else 1 if 'FROM identity_privilege' in query else 2 if 'FROM asset_vulnerabilities' in query else 3
        if self.fail==index:raise RuntimeError('injected lookup failure')
        return SimpleNamespace(mappings=lambda:SimpleNamespace(all=lambda:self.rows[index]))

def asset():return {'id':UUID(int=3),'criticality':'high','metadata':{'source':'fixture'},'updated_at':datetime.now(UTC)}
def identity():return {'id':UUID(int=4),'principal':'svc-test','privilege_tier':'admin','is_service':True,'is_break_glass':False,'source':'fixture'}

@pytest.mark.asyncio
async def test_material_actually_changes_independent_priority_and_keeps_original():
    original=alert();db=DB(assets=[asset()],identities=[identity()],vulns=[{'id':UUID(int=5),'is_exploited':True,'metadata':{}}])
    result=await collect_processing_context(db,original)
    assert result['priority']['score']==706 and result['priority']['base']==350
    assert len(result['priority']['rationale'])==3 and result['priority']['material_complete']
    assert original.priority==50 and original.severity=='medium'
    for query,params in db.calls:assert str(original.tenant_id)==params['tenant_id'] and 'tenant_id' in query
    assert result['external_event_history']['status']=='not_configured'

@pytest.mark.asyncio
async def test_optional_failed_read_rolls_back_savepoint_preserves_other_dimensions():
    db=DB(identities=[identity()],history=[{'id':UUID(int=9)}],fail=0)
    result=await collect_processing_context(db,alert())
    assert db.rolled_back and result['partial'] and result['dimensions']['assets']['status']=='unavailable'
    assert result['dimensions']['identities']['status']=='matched' and result['dimensions']['alert_history']['status']=='matched'
    assert result['priority']['status']=='unavailable' and result['priority']['score'] is None

@pytest.mark.asyncio
async def test_empty_context_is_not_failure_or_complete_material():
    result=await collect_processing_context(DB(),alert())
    assert not result['partial'] and result['dimensions']['assets']['status']=='no_match'
    assert result['dimensions']['vulnerabilities']['status']=='not_requested'
    assert result['priority']['score']==350 and not result['priority']['material_complete']

@pytest.mark.asyncio
async def test_multiple_candidates_or_truncated_exposure_do_not_guess_score():
    multiple=await collect_processing_context(DB(assets=[asset(),asset()]),alert())
    capped=await collect_processing_context(DB(assets=[asset()],vulns=[{'id':UUID(int=5)}]*21),alert())
    assert multiple['priority']['status']==capped['priority']['status']=='ambiguous'
    assert multiple['priority']['score'] is None and capped['dimensions']['vulnerabilities']['truncated']
