"""Actual Redis checks using isolated marked entities, not HTTP alert ingestion."""
import asyncio,json,os,sys,uuid
from pathlib import Path
sys.path.insert(0,'/app')
import redis.asyncio as redis
from app.core.config import settings
from app.models.alert import RawAlert
from app.services.entity_risk import EntityRiskEngine,_ENTITY_PREFIX,_SEEN_PREFIX
E=Path('/evidence');B='2b-risk-20261020'
def save(n,v):
    with (E/n).open('x') as f:json.dump(v,f,indent=2,default=str)
async def main():
    save('redis-started.json',{'scope':'direct current-source engine + real shared Redis; no Kafka/PG rows'})
    ids=json.loads(Path('/private/state.json').read_text())['identities'];tenant=ids['a']['tenant_id'];other=ids['b']['tenant_id']
    cache=redis.from_url(os.environ['REDIS_URL']);engine=EntityRiskEngine(cache)
    def alert(label,severity='low',username='socai2-risk-direct',tenant_id=tenant):
        return RawAlert(id=uuid.uuid5(uuid.NAMESPACE_URL,B+'/direct/'+label),tenant_id=tenant_id,source='socai2-'+B,title='Synthetic '+label,severity=severity,username=username)
    first=alert('first','high');key=_ENTITY_PREFIX+tenant+':user:'+first.username;seen=_SEEN_PREFIX+tenant+':user:'+first.username
    assert not await cache.exists(key,seen)
    try:
        results=await asyncio.gather(*(engine.observe(first) for _ in range(32)))
        rec=await engine.get(tenant,'user',first.username);assert rec.alert_count==1 and rec.score==20
        assert not any(results)
        more=[alert('unique-'+str(i)) for i in range(64)]
        results=await asyncio.gather(*(engine.observe(a) for a in more))
        rec=await engine.get(tenant,'user',first.username);assert rec.alert_count==65 and rec.severities=={'high':1,'low':64}
        assert sum(len(x) for x in results)==1 and rec.promoted_at is not None
        assert 211<rec.score<=212 and len(rec.contributing_alerts)==50 and len(rec.contributors)==25
        assert str(first.id) not in rec.contributing_alerts and await cache.scard(seen)==65
        before=await cache.hgetall(key);before_ttl=await cache.pttl(key)
        assert await engine.observe(first)==[] and await cache.hgetall(key)==before
        assert await cache.pttl(key)<=before_ttl
        another=first.model_copy(update={'tenant_id':uuid.UUID(other)})
        await engine.observe(another);assert (await engine.get(other,'user',first.username)).alert_count==1
        # Compatibility with an old hash lacking a membership set.
        old=alert('legacy',username='socai2-risk-legacy-visible');await engine.observe(old)
        old_seen=_SEEN_PREFIX+tenant+':user:'+old.username;assert await cache.unlink(old_seen)==1
        old_before=(await engine.get(tenant,'user',old.username)).to_dict();await engine.observe(old)
        assert (await engine.get(tenant,'user',old.username)).to_dict()==old_before
        await engine.observe(alert('legacy-new',username=old.username));assert await cache.sismember(old_seen,str(old.id))
        # Short TTL belongs to this isolated engine instance only, not service settings.
        ttl_engine=EntityRiskEngine(cache);ttl_engine._window=2
        ttl_alert=alert('ttl',username='socai2-risk-ttl');await ttl_engine.observe(ttl_alert)
        ttl_key=_ENTITY_PREFIX+tenant+':user:'+ttl_alert.username;ttl_seen=_SEEN_PREFIX+tenant+':user:'+ttl_alert.username
        assert 0<await cache.pttl(ttl_key)<=2000 and 0<await cache.pttl(ttl_seen)<=2000
        await asyncio.sleep(1.1);await ttl_engine.observe(ttl_alert)
        assert await cache.pttl(ttl_key)<1100 and await cache.pttl(ttl_seen)<1100
        await asyncio.sleep(1.1);assert not await cache.exists(ttl_key,ttl_seen)
        report={'backend':'real Redis, runtime locked redis SDK','concurrent_same_alert_deliveries':32,'unique_additional_alerts_concurrent':64,'final_unique_count':65,'severity_counts':rec.severities,'score':rec.score,'promotion_returns':sum(len(x) for x in results),'last50_display_count':len(rec.contributing_alerts),'last25_detail_count':len(rec.contributors),'full_membership_count':await cache.scard(seen),'oldest_replay_unchanged':True,'replay_does_not_extend_ttl':True,'another_tenant_independent':True,'visible_legacy_membership_seeded':True,'isolated_2_second_ttl_expired_both_keys':True,'service_window_unmodified':settings.rba_window_seconds,'entity':rec.to_dict(),'redis_memory_bytes':{'record':await cache.memory_usage(key),'seen':await cache.memory_usage(seen)},'risk_storage_is_redis_not_durable_pg_ledger':True}
        save('redis-acceptance.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['entity']}))
    finally:await cache.aclose()
if __name__=='__main__':asyncio.run(asyncio.wait_for(main(),90))
