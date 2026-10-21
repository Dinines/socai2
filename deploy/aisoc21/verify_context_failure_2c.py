"""Inject an undefined relation into only the probe's actual PG read path."""
import asyncio,json,os,sys,uuid
from pathlib import Path
sys.path.insert(0,'/app')
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.alert import Alert
from app.services import processing_context as ctx
async def main():
    e=Path('/evidence');out=e/'failure-acceptance.json';assert not out.exists()
    state=json.loads(Path('/private/state.json').read_text());base=json.loads((e/'before-acceptance.json').read_text());tenant=uuid.UUID(state['identities']['a']['tenant_id'])
    async with AsyncSessionLocal() as db:
        alert=(await db.execute(select(Alert).where(Alert.id==uuid.UUID(base['alerts']['current']['id']),Alert.tenant_id==tenant))).scalar_one()
        query=ctx.ASSETS
        try:
            ctx.ASSETS='SELECT id FROM socai2_context_missing_relation_2c'
            failed=await ctx.collect_processing_context(db,alert)
            assert failed['dimensions']['assets']['status']=='unavailable' and failed['partial']
            assert failed['dimensions']['identities']['status']=='matched' and failed['dimensions']['alert_history']['status']=='matched'
            assert failed['priority']['score'] is None
        finally:ctx.ASSETS=query
        recovered=await ctx.collect_processing_context(db,alert)
        assert recovered['priority']['score']==435 and not recovered['partial']
        with out.open('x') as f:json.dump({'failure':failed,'same_session_recovered':recovered,'injection':'undefined relation SELECT only in independent probe process','production_api_and_shared_pg_unchanged':True,'real_pg_savepoint_recovery':True},f,indent=2,default=str)
        print(json.dumps({'real_pg_failure_isolated':True,'other_dimensions_preserved':True,'same_session_recovered_score':435}))
if __name__=='__main__':asyncio.run(asyncio.wait_for(main(),30))
