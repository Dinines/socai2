"""Read only selected synthetic source records; used inside the deployed API."""
import asyncio,json,os,sys
from pathlib import Path
from uuid import UUID
cfg=json.loads(sys.argv[1] if sys.argv[1].startswith('{') else Path(sys.argv[1]).read_text())
if cfg.get('environment'):os.environ.update(json.loads(Path(cfg['environment']).read_text()))
if cfg.get('pythonpath'):sys.path.insert(0,cfg['pythonpath'])
from sqlalchemy import select,text,or_
from app.db.database import engine
from app.db.case_database import get_case_write_sessions
from app.models import socai2 as m

async def main():
 A,I,L=(x.__table__ for x in (m.Alerts,m.Incidents,m.IncidentAlerts));tenant=UUID(cfg['tenant_id'])
 async with engine.connect() as connection:
  reader=dict((await connection.execute(text('SELECT current_database() AS database,current_user AS role'))).mappings().one())
 async with get_case_write_sessions()() as session,session.begin():
  await session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
  await session.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"),{'tenant':str(tenant)})
  identity=dict((await session.execute(text('SELECT current_database() AS database,current_user AS role'))).mappings().one())
  assert identity['database']==reader['database']==cfg['database']
  alerts=[dict(r) for r in (await session.execute(select(A).where(A.c.tenant_id==tenant,A.c.source_namespace.in_(cfg['sources'])).order_by(A.c.id))).mappings()]
  ids=select(L.c.incident_id).where(L.c.tenant_id==tenant,L.c.alert_id.in_([r['id'] for r in alerts]))
  incidents=[dict(r) for r in (await session.execute(select(I).where(I.c.tenant_id==tenant,or_(I.c.source_namespace.in_(cfg['sources']),I.c.id.in_(ids))).order_by(I.c.id))).mappings()]
  links=[dict(r) for r in (await session.execute(select(L).where(L.c.tenant_id==tenant,L.c.incident_id.in_([r['id'] for r in incidents])).order_by(L.c.id))).mappings()]
 await engine.dispose();print(json.dumps({'reader':reader,'identity':identity,'alerts':alerts,'incidents':incidents,'links':links},ensure_ascii=False,indent=2,default=str))
asyncio.run(main())
