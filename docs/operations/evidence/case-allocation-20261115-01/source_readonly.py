"""129 routing columns must not alter the established incident analysis input."""
import asyncio
import json
from pathlib import Path
from uuid import UUID

from validate import ROOT, save


async def main():
    from app.socai2.baseline_store import digest
    from app.socai2.stage_inputs import SOURCE_SQL, VERSION
    from sqlalchemy import text
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import create_async_engine
    here=Path(__file__).resolve().parent
    config=json.loads((ROOT/'.local/v1.2-reader-validation/config-dev.json').read_text())
    sample=json.loads((here/'pg-04/result.json').read_text())
    old=json.loads((here/'pg-04/database.json').read_text())['incidents'][0]
    assert config['processing_database']=='v12_upgrade_dev'
    url=URL.create('postgresql+psycopg',username=config['admin'],password=Path(config['password_file']).read_text().strip(),
        host=config['host'],port=config['port'],database=config['processing_database'])
    engine=create_async_engine(url,hide_parameters=True,connect_args={'sslmode':'disable','options':'-c role='+config['processor']})
    try:
        async with engine.begin() as db:
            await db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"),{'tenant':sample['tenant_id']})
            params={'tenant':UUID(sample['tenant_id']),'id':UUID(sample['incident_id']),'kind':'incident_diagnosis','version':VERSION}
            source=(await db.execute(text(SOURCE_SQL),params)).scalar_one()
            current=(await db.execute(text('SELECT to_jsonb(i) FROM socai2.incidents i WHERE tenant_id=:tenant AND id=:id'),params)).scalar_one()
            legacy_fields={k:v for k,v in old.items() if k not in {'active_case_id','latest_diagnosis_id','row_version','business_updated_at'}}
            assert source['parent']==legacy_fields
            assert current['active_case_id']!=old['active_case_id']
            assert 'active_case_id' not in source['parent']
            save(here/'source-readonly.json',{'state':'passed','read_only':True,'tenant_id':sample['tenant_id'],
                'incident_id':sample['incident_id'],'receiver_changed_by_explicit_http_operation':True,
                'parent_matches_original_without_internal_routing':True,'parent_sha256':digest(source['parent']),
                'old_receiver':old['active_case_id'],'current_receiver':current['active_case_id'],'model_calls':0})
    finally:
        await engine.dispose()


if __name__=='__main__':
    asyncio.run(main())
