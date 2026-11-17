"""A synthetic recorded actor for HTTP write integration in the isolated fixture tenant."""
import asyncio,json
from pathlib import Path
from uuid import UUID,uuid4
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine
ROOT=Path(__file__).resolve().parents[4]
async def main():
 cfg=json.loads((ROOT/'.local/v1.2-reader-validation/config-dev.json').read_text());assert cfg['processing_database']=='v12_upgrade_dev'
 tenant=UUID('cebc437d-628b-4d0a-83ad-12b735a06ab6');actor=uuid4()
 engine=create_async_engine(URL.create('postgresql+psycopg',username=cfg['admin'],password=Path(cfg['password_file']).read_text().strip(),host=cfg['host'],port=cfg['port'],database=cfg['processing_database']),hide_parameters=True,connect_args={'sslmode':'disable'})
 try:
  async with engine.begin() as db:
   await db.execute(text("""INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
    VALUES(:id,:tenant,:email,'Synthetic event HTTP actor','!','soc_analyst',true,false,'{}',now(),now())"""),{'id':actor,'tenant':tenant,'email':str(actor)+'@example.invalid'})
  value={'tenant_id':str(tenant),'actor_id':str(actor),'purpose':'local synthetic HTTP audit actor; no usable password/token'}
  (Path(__file__).parent/'actor.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
 finally: await engine.dispose()
asyncio.run(main())
