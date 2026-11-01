
from pathlib import Path
import json,subprocess
root=Path('/opt/sting-aisoc-socai2/investigation-v2/20261101-r12/retest')
plan=json.loads((root/'plan.json').read_text())
ids=[s['planned_run_id'] for s in plan['cases']]
queries=[e['query_id'] for label in ['A','B'] for e in json.loads((root/'results'/label/'summary.json').read_text())['run']['tools']]
code='RUN_IDS='+repr(ids)+'\nQUERY_IDS='+repr(queries)+'\n'+r"""
import asyncio,json
from uuid import UUID
from sqlalchemy import text
from app.db.database import engine
from app.db.clickhouse import get_clickhouse_client
async def main():
    qids=tuple(str(UUID(x)) for x in QUERY_IDS)
    client=await get_clickhouse_client()
    rows,cols=client.execute('SELECT query_id,type,event_time,query_duration_ms,read_rows,result_rows,exception_code,query FROM system.query_log WHERE query_id IN %(ids)s ORDER BY event_time,type',{'ids':qids},with_column_types=True)
    result={'query_log':[dict(zip([c[0] for c in cols],row)) for row in rows]}
    async with engine.connect() as conn:
        args={'ids':[UUID(x) for x in RUN_IDS]}
        result['runs']=[dict(r) for r in (await conn.execute(text('SELECT id,tenant_id,case_id,status,total_tokens,iterations,total_cost_usd,measured_call_count,estimated_cost_usd,estimated_call_count,unpriced_call_count FROM investigation_runs WHERE id=ANY(:ids) ORDER BY id'),args)).mappings()]
        for table in ['investigation_events','investigation_artifacts']:
            result[table]=[dict(r) for r in (await conn.execute(text('SELECT run_id,count(*) AS count FROM '+table+' WHERE run_id=ANY(:ids) GROUP BY run_id ORDER BY run_id'),args)).mappings()]
    await engine.dispose()
    print(json.dumps(result,default=str))
asyncio.run(main())
"""
response=subprocess.run(['docker','exec','-i','socai2-investigation-api','python','-B','-'],input=code.encode(),capture_output=True,check=True)
print(response.stdout.decode())
