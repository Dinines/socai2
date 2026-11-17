"""Small operational terminal-state observation; tests own full saved-data assertions."""
import asyncio
import json
from pathlib import Path
from uuid import UUID

from app.socai2.analysis_dispatch_runtime import load_profile
from app.socai2.stage_results import StageResultService
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main():
    profile = load_profile('/run/analysis/dispatcher.json')
    engine = create_async_engine(Path(profile['database_url_file']).read_text().strip(), hide_parameters=True,
                                connect_args=profile['database_connect_args'])
    service = StageResultService(async_sessionmaker(engine, expire_on_commit=False))
    try:
        async with service.transaction(UUID(profile['tenant_id']), readonly=True) as store:
            tasks = (await store.db.execute(text('SELECT id,subject_id,kind,intent,state,reason_code,retry_count,started_at,ended_at FROM socai2.analysis_tasks ORDER BY submitted_at,id'))).mappings().all()
            attempts = (await store.db.execute(text('SELECT task_id,attempt_no,run_id,local_state,outcome,error_code FROM socai2.analysis_attempts ORDER BY started_at,id'))).mappings().all()
            out = {'observed_at': str(await store.now()), 'tasks': [dict(x) for x in tasks], 'attempts': [dict(x) for x in attempts],
                   'all_terminal': bool(tasks) and all(x['state'] in {'completed', 'failed', 'skipped'} for x in tasks),
                   'running_attempts': sum(x['local_state'] == 'running' for x in attempts)}
        print(json.dumps(out, default=str))
    finally:
        await engine.dispose()


asyncio.run(main())
