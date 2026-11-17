"""This batch's read-only progress snapshot; never submits or retries work."""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '/opt/investigation-test/tools/testdata')
from acceptance_clients import Postgres
from acceptance_materials import control, read_json
from acceptance_runtime_contract import PostgresConnection
from acceptance_session import load_execution


async def observe(directory):
    profile, session = load_execution(directory)
    config = control(PostgresConnection, read_json(Path(profile.connection_files.postgres)), 'postgres')
    pg = Postgres(config, profile.tenant_id)
    try:
        await pg.connect()
        async with pg.connection.transaction(isolation='repeatable_read', readonly=True):
            await pg.connection.execute("SELECT set_config('app.current_tenant_id',$1,true)", profile.tenant_id)
            s = config.schema_name
            tables = {}
            fields = {
                'analysis_tasks': 'id,subject_type,subject_id,kind,state,reason_code,submitted_at,started_at,ended_at',
                'analysis_attempts': 'id,task_id,run_id,local_state,outcome,started_at,local_ended_at',
                'runs': 'id,case_id,alert_id,incident_id,state,started_at,ended_at',
                'run_steps': 'id,run_id,seq,stage_code,name,state,started_at,ended_at',
            }
            for table, columns in fields.items():
                rows = await pg.connection.fetch(f'SELECT {columns} FROM {s}.{table} WHERE tenant_id=$1 ORDER BY id', pg.tenant)
                tables[table] = [dict(row) for row in rows]
            return {
                'observed_at': datetime.now(timezone.utc).isoformat(),
                'execution_id': session['execution']['execution_id'],
                'readonly': await pg.connection.fetchval('SHOW transaction_read_only') == 'on',
                'running_tasks': sum(row['state'] == 'running' for row in tables['analysis_tasks']),
                'open_attempts': sum(row['local_state'] == 'running' for row in tables['analysis_attempts']),
                'tables': tables,
            }
    finally:
        await pg.close()


parser = argparse.ArgumentParser()
parser.add_argument('--prepared', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
value = asyncio.run(observe(args.prepared))
with args.output.open('x') as out:
    json.dump(value, out, ensure_ascii=False, indent=2, default=str)
print(json.dumps(value, ensure_ascii=False, default=str))
