"""Policy results report the exact observed content and loading condition."""
from datetime import UTC,datetime
import asyncio
from uuid import uuid4
import pytest
from app.workers import business_context as bc
from app.workers.fused_alert_consumer import FusedAlertTriageWorker

YAML='''rules:
  - id: controlled-suppression
    when: {field: username, op: eq, value: socai2-maint}
    then: {suppress: true}
'''

@pytest.mark.asyncio
async def test_real_loader_shape_cache_revision_and_restore(monkeypatch):
    import asyncpg
    tenant=str(uuid4());row={'yaml_text':YAML,'enabled':True,'updated_at':datetime.now(UTC)}
    class Conn:
        async def fetchrow(self,query,key):assert str(key)==tenant;return row.copy()
        async def close(self):pass
    async def connect(*args,**kwargs):return Conn()
    monkeypatch.setattr(asyncpg,'connect',connect);monkeypatch.setenv('DATABASE_DSN','postgresql://test.invalid/test')
    applier=bc.BusinessContextApplier();alert={'username':'socai2-maint','severity':'low'}
    first=await applier.apply_for_tenant(tenant,alert);assert first.suppressed
    row['yaml_text']='rules: []'
    cached=await applier.apply_for_tenant(tenant,alert)
    assert cached.suppressed and cached.provenance['load_status']=='cache'
    assert cached.provenance['policy_revision']==first.provenance['policy_revision']
    applier.clear_tenant_cache();second=await applier.apply_for_tenant(tenant,alert)
    assert not second.suppressed and second.provenance['policy_revision']!=first.provenance['policy_revision']
    row['yaml_text']=YAML;applier.clear_tenant_cache();restored=await applier.apply_for_tenant(tenant,alert)
    assert restored.suppressed and restored.provenance['policy_revision']==first.provenance['policy_revision']
    from app.replay.shadow import ShadowTriageWriter
    worker=FusedAlertTriageWorker(bootstrap_servers='',business_context=applier,writer=ShadowTriageWriter())
    summary=await worker.triage({'tenant_id':tenant,'id':str(uuid4()),'alert':alert})
    assert summary['suppressed'] and summary['business_context_policy']['policy_revision']==first.provenance['policy_revision']
    assert not summary['response_dispatched']

@pytest.mark.asyncio
async def test_outage_distinguishes_stale_from_unavailable(monkeypatch):
    import asyncpg
    tenant=str(uuid4());applier=bc.BusinessContextApplier()
    applier._tenant_rules[tenant]=(0,bc.load_rules_from_yaml(YAML))
    async def connect(*args,**kwargs):raise OSError('injected failure')
    monkeypatch.setattr(asyncpg,'connect',connect);monkeypatch.setenv('DATABASE_DSN','postgresql://test.invalid/test')
    stale=await applier.apply_for_tenant(tenant,{'username':'socai2-maint'})
    assert stale.suppressed and stale.provenance['load_status']=='stale_cache'
    cold=await bc.BusinessContextApplier().apply_for_tenant(tenant,{'username':'socai2-maint'})
    assert not cold.suppressed and cold.provenance['load_status']=='unavailable'
    assert cold.provenance['policy_revision'] is None
