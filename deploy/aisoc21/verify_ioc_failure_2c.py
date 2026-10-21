"""Direct real SDK failure/recovery, isolated connection target only."""
import asyncio,json,os,sys
from pathlib import Path
sys.path.insert(0,'/app')
from app.services.ioc_match import TenantIocMatcher
async def main():
    e=Path('/evidence');out=e/'failure-recovery.json';assert not out.exists()
    tenant=json.loads(Path('/private/state.json').read_text())['identities']['a']['tenant_id'];args={'tenant_id':tenant,'indicators':[{'ioc_type':'domain','value':'unmatched.socai2.invalid'}]}
    matcher=TenantIocMatcher('postgresql://nobody@127.0.0.1:1/nope')
    failed=await matcher.lookup(**args);assert failed.status=='unavailable' and matcher.available
    matcher._dsn=os.environ['DATABASE_URL'];recovered=await matcher.lookup(**args);assert recovered.status=='no_match'
    with out.open('x') as f:json.dump({'failure':failed.as_dict(),'recovered':recovered.as_dict(),'only_probe_connection_target_changed':True,'shared_pg_not_stopped':True},f,indent=2)
    if matcher._pool is not None:await matcher._pool.close()
    print(json.dumps({'failure':'unavailable','recovered':'no_match','no_global_environment_change':True}))
if __name__=='__main__':asyncio.run(asyncio.wait_for(main(),25))
