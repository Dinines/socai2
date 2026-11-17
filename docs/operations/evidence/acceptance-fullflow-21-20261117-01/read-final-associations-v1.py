"""Read only the existing case's relations needed by the local audit exporter."""
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, '/opt/investigation-test/tools/testdata')
from acceptance_clients import Postgres
from acceptance_materials import control, read_json
from acceptance_runtime_contract import PostgresConnection
from acceptance_session import load_execution


async def main():
    directory = Path(sys.argv[1])
    profile, _ = load_execution(directory)
    saved = read_json(directory/'runs/part2/saved-records.json')
    pg = Postgres(control(PostgresConnection, read_json(Path(profile.connection_files.postgres)), 'postgres'), profile.tenant_id)
    try:
        await pg.connect()
        async with pg.connection.transaction(isolation='repeatable_read', readonly=True):
            await pg.connection.execute("SELECT set_config('app.current_tenant_id',$1,true)", profile.tenant_id)
            selectors = {
                'case_incidents': ('case_id', [r['id'] for r in saved['cases']]),
                'result_members': ('result_id', [r['id'] for r in saved['results']]),
                'alert_objects': ('alert_id', [r['id'] for r in saved['alerts']]),
                'analysis_subject_state': ('subject_id', [r['id'] for t in ['alerts','incidents','cases'] for r in saved[t]]),
            }
            rows = {}
            for table, (column, identities) in selectors.items():
                raw = await pg.connection.fetchval(f"SELECT coalesce(json_agg(t ORDER BY t.id),'[]'::json) FROM {pg.config.schema_name}.{table} t WHERE tenant_id=$1 AND {column}=ANY($2::uuid[])", pg.tenant, [UUID(x) for x in identities])
                rows[table] = json.loads(raw)
            counts = {}
            for table in ['alerts','incidents','cases','analysis_tasks','analysis_attempts','runs','results']:
                counts[table] = await pg.connection.fetchval(f'SELECT count(*) FROM {pg.config.schema_name}.{table} WHERE tenant_id=$1', pg.tenant)
            active = await pg.connection.fetchval(f"SELECT count(*) FROM {pg.config.schema_name}.analysis_attempts WHERE tenant_id=$1 AND local_state='running'", pg.tenant)
            print(json.dumps({'status': 'read_only', 'rows': rows, 'tenant_counts': counts,
                              'open_attempts': active, 'transaction_read_only': await pg.connection.fetchval('SHOW transaction_read_only')}, ensure_ascii=False))
    finally:
        await pg.close()


asyncio.run(main())
