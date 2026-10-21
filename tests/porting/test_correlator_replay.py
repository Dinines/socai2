"""Regression: a dedup-cache miss must not count an existing incident member again."""
from uuid import uuid4
import pytest
from app.models.alert import RawAlert
from app.services.correlator import Correlator

class MemoryRedis:
    def __init__(self): self.values={}
    async def get(self,key): return self.values.get(key)
    async def set(self,key,value,ex=None): self.values[key]=value.encode() if isinstance(value,str) else value

@pytest.mark.asyncio
async def test_replayed_member_preserves_count_members_and_observation_time():
    cache=MemoryRedis();correlator=Correlator(cache);tenant=uuid4()
    first=RawAlert(id=uuid4(),tenant_id=tenant,source='test',title='first',hostname='test-host',mitre_tactics=['execution'])
    second=first.model_copy(update={'id':uuid4(),'title':'second'})
    _,original=await correlator.correlate(first)
    related,before=await correlator.correlate(second)
    assert related and before.alert_count==2
    related,after=await correlator.correlate(first)
    assert related and after.id==original.id
    assert after.alert_count==2 and after.alert_ids==before.alert_ids
    assert after.last_seen==before.last_seen

@pytest.mark.asyncio
async def test_new_member_still_increases_count():
    correlator=Correlator(MemoryRedis());tenant=uuid4()
    first=RawAlert(id=uuid4(),tenant_id=tenant,source='test',title='first',hostname='test-host')
    second=first.model_copy(update={'id':uuid4(),'title':'second'})
    _,before=await correlator.correlate(first)
    related,after=await correlator.correlate(second)
    assert related and after.id==before.id and after.alert_count==2
    assert set(after.alert_ids)=={str(first.id),str(second.id)}

@pytest.mark.asyncio
async def test_replayed_member_at_capacity_keeps_existing_incident():
    correlator=Correlator(MemoryRedis());correlator._max_alerts=2;tenant=uuid4()
    first=RawAlert(id=uuid4(),tenant_id=tenant,source='test',title='first',hostname='test-host')
    second=first.model_copy(update={'id':uuid4(),'title':'second'})
    _,initial=await correlator.correlate(first)
    await correlator.correlate(second)
    related,after=await correlator.correlate(first)
    assert related and after.id==initial.id and after.alert_count==2
