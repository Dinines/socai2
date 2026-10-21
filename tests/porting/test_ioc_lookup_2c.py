"""Status/citation/persistence contract for local-only IOC consumption."""
from contextlib import asynccontextmanager
from datetime import UTC,datetime
import json
from uuid import UUID
import pytest
from app.services.ioc_match import TenantIocMatcher
from app.services.alert_enricher import AlertEnricher
from app.services.confidence import _ti_contribution
from app.services.alert_sink import _insert_args
from app.models.alert import RawAlert,FusedAlert

class Pool:
    def __init__(self,rows=None,error=None):self.rows=rows or [];self.error=error
    @asynccontextmanager
    async def acquire(self):yield self
    async def fetch(self,*args):
        if self.error:raise self.error
        return self.rows

@pytest.mark.asyncio
async def test_no_match_and_failure_are_different():
    args={'tenant_id':str(UUID(int=1)),'indicators':[{'ioc_type':'domain','value':'example.invalid'}]}
    miss=await TenantIocMatcher(Pool()).lookup(**args)
    failed=await TenantIocMatcher(Pool(error=OSError('injected'))).lookup(**args)
    assert miss.status=='no_match' and failed.status=='unavailable'
    assert failed.reason=='query_failed' and not failed.matches

@pytest.mark.asyncio
async def test_local_only_history_reaches_fused_and_frozen_metadata_without_score_boost():
    row={'id':UUID(int=7),'ioc_type':'domain','value':'example.invalid','confidence':50,'severity':'medium','source':'historical-reference','source_ref':'source:sha256:example','last_seen':datetime(2022,4,8,tzinfo=UTC),'threat_actor':None,'malware_family':None}
    matcher=TenantIocMatcher(Pool([row]));alert=RawAlert(id=UUID(int=2),tenant_id=UUID(int=1),source='test',title='historical lookup',domain='example.invalid')
    data=await AlertEnricher(base_url='',ioc_matcher=matcher).enrich(alert)
    lookup=data['ioc_lookup'];assert lookup['status']=='matched' and lookup['external_status']=='not_configured'
    hit=lookup['matches'][0];assert hit['ioc_id']==str(UUID(int=7)) and hit['source_ref']==row['source_ref'] and hit['weak']
    contribution,label=_ti_contribution(data);assert contribution==-0.3 and 'not used' in label
    fused=FusedAlert(id=alert.id,tenant_id=alert.tenant_id,alert=alert,enrichments=data,fusion_decision='new_incident')
    stored=json.loads(_insert_args(fused)[-1])['socai2_fusion']
    assert stored['ioc_lookup']==lookup and stored['identity']['version']=='legacy-v1'

@pytest.mark.asyncio
async def test_unavailable_is_carried_through_enricher_and_confidence_label():
    data=await AlertEnricher(base_url='',ioc_matcher=TenantIocMatcher(Pool(error=OSError('injected')))).enrich(RawAlert(tenant_id=UUID(int=1),source='test',title='probe',domain='example.invalid'))
    assert data['ioc_lookup']['status']=='unavailable'
    assert _ti_contribution(data)==(-0.3,'tenant TI unavailable; retained default prior')
