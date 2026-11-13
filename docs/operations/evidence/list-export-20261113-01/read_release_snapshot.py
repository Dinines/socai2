"""Only SELECT the explicitly selected acceptance subjects; no fixture writes."""
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import UUID

cfg=json.loads(sys.argv[1] if sys.argv[1].startswith('{') else Path(sys.argv[1]).read_text())
if cfg.get('environment'):
    os.environ.update(json.loads(Path(cfg['environment']).read_text()))
if cfg.get('pythonpath'):
    sys.path.insert(0,cfg['pythonpath'])
from sqlalchemy import select,text
from app.db.database import engine
from app.db.case_database import get_case_write_sessions
from app.models import socai2 as m

async def main():
    async with engine.connect() as conn:
        reader=dict((await conn.execute(text('SELECT current_database() AS database,current_user AS role'))).mappings().one())
    async with get_case_write_sessions()() as session:
        async with session.begin():
            await session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            await session.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"),{'tenant':cfg['tenant_id']})
            writer=dict((await session.execute(text('SELECT current_database() AS database,current_user AS role'))).mappings().one())
            assert reader['database']==writer['database']==cfg['database']
            result={'reader':reader,'writer':writer,'rows':{}}
            for kind,name in [('alerts','Alerts'),('incidents','Incidents'),('cases','Cases')]:
                t=getattr(m,name).__table__
                result['rows'][kind]=[dict(r) for r in (await session.execute(select(t).where(
                    t.c.tenant_id==UUID(cfg['tenant_id']),t.c.id.in_([UUID(x) for x in cfg['ids'][kind]])
                ).order_by(t.c.id))).mappings()]
                assert len(result['rows'][kind])==len(cfg['ids'][kind])
            t=m.IncidentAlerts.__table__
            result['rows']['links']=[dict(r) for r in (await session.execute(select(t).where(
                t.c.tenant_id==UUID(cfg['tenant_id']),t.c.incident_id.in_([UUID(x) for x in cfg['ids']['incidents']])
            ).order_by(t.c.id))).mappings()]
            t=m.CaseAlerts.__table__
            result['rows']['case_links']=[dict(r) for r in (await session.execute(select(t).where(
                t.c.tenant_id==UUID(cfg['tenant_id']),t.c.case_id.in_([UUID(x) for x in cfg['ids']['cases']])
            ).order_by(t.c.id))).mappings()]
    await engine.dispose()
    print(json.dumps(result,ensure_ascii=False,indent=2,default=str))

asyncio.run(main())
