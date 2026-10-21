"""Risk replay regressions; runtime concurrency is tested against real Redis."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'services/fusion/tests'))
from test_entity_risk import _FakeRedis, _alert, _TENANT
import pytest
from redis.exceptions import WatchError
from app.services.entity_risk import EntityRiskEngine
_SEEN_PREFIX='aisoc:fusion:rba:seen:'

@pytest.mark.asyncio
async def test_replay_changes_no_risk_fields():
    cache=_FakeRedis();engine=EntityRiskEngine(cache);alert=_alert(risk_score=0.5)
    await engine.observe(alert);before=(await engine.get(_TENANT,'user','alice')).to_dict()
    assert await engine.observe(alert)==[]
    assert (await engine.get(_TENANT,'user','alice')).to_dict()==before

@pytest.mark.asyncio
async def test_replay_older_than_display_cap_remains_seen():
    cache=_FakeRedis();engine=EntityRiskEngine(cache);first=_alert()
    await engine.observe(first)
    for _ in range(55):await engine.observe(_alert())
    before=(await engine.get(_TENANT,'user','alice')).to_dict()
    assert str(first.id) not in before['contributing_alerts']
    assert len(before['contributing_alerts'])==50 and len(before['contributors'])==25
    await engine.observe(first)
    assert (await engine.get(_TENANT,'user','alice')).to_dict()==before

@pytest.mark.asyncio
async def test_legacy_visible_ids_seed_full_membership():
    cache=_FakeRedis();engine=EntityRiskEngine(cache);first=_alert()
    await engine.observe(first);cache.sets.clear()
    await engine.observe(first)
    assert (await engine.get(_TENANT,'user','alice')).alert_count==1
    await engine.observe(_alert())
    assert str(first.id) in cache.sets[_SEEN_PREFIX+f'{_TENANT}:user:alice']

@pytest.mark.asyncio
async def test_failure_does_not_claim_contribution_and_retry_can_apply():
    cache=_FakeRedis();engine=EntityRiskEngine(cache);alert=_alert()
    cache.fail_next_execute=RuntimeError('injected before EXEC')
    with pytest.raises(RuntimeError):await engine.observe(alert)
    assert not cache.hashes and not cache.sets
    await engine.observe(alert)
    assert (await engine.get(_TENANT,'user','alice')).alert_count==1

@pytest.mark.asyncio
async def test_watch_conflict_retries_without_double_counting():
    cache=_FakeRedis();engine=EntityRiskEngine(cache);cache.fail_next_execute=WatchError()
    await engine.observe(_alert())
    assert (await engine.get(_TENANT,'user','alice')).alert_count==1
