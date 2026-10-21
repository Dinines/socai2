from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import UUID
import json,pytest
from app.models.alert import RawAlert,FusedAlert,FusionDecision
from app.services.alert_sink import AlertSink,PersistOutcome,_insert_args

def fused():
    alert=RawAlert(tenant_id=UUID(int=1),source='test',title='finding',identity_version='source-v1',source_alert_id=UUID(int=2))
    alert.id=alert.deterministic_id()
    return FusedAlert(id=alert.id,tenant_id=alert.tenant_id,incident_id=UUID(int=3),fusion_decision=FusionDecision.DUPLICATE,alert=alert)

@pytest.mark.asyncio
async def test_cached_duplicate_does_not_claim_durable_when_database_unavailable():
    sink=AlertSink('unused');sink._ensure_pool=AsyncMock(return_value=None)
    result=await sink.persist(fused());assert result.outcome==PersistOutcome.UNAVAILABLE

@pytest.mark.asyncio
async def test_cached_duplicate_can_repair_missing_database_insert():
    value=fused();conn=AsyncMock();conn.fetchrow.return_value={'id':value.id}
    class Pool:
        @asynccontextmanager
        async def acquire(self):yield conn
    sink=AlertSink('unused');sink._ensure_pool=AsyncMock(return_value=Pool());sink._link_source_finding=AsyncMock()
    result=await sink.persist(value)
    assert result.outcome==PersistOutcome.INSERTED
    conn.fetchrow.assert_awaited_once()

def test_immutable_identity_and_relation_are_in_existing_metadata_column():
    value=fused();metadata=json.loads(_insert_args(value)[-1])['socai2_fusion']
    assert metadata['identity']['version']=='source-v1' and metadata['identity']['source_alert_id']==str(UUID(int=2))
    assert metadata['incident_id']==str(UUID(int=3))
