"""Read actual Case dependencies with the configured ordinary runtime identities."""
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import UUID

import httpx
from app.core.config import settings
from app.db.clickhouse import close_clickhouse
from app.socai2.analysis_case_executor import executors
from app.socai2.analysis_dispatch_runtime import load_profile, validate_executors
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_evidence_tools import LakeGateway
from app.socai2.knowledge_config import load
from app.socai2.knowledge_vectors import Vectors
from app.socai2.runtime_policy import active_policy
from app.socai2.stage_results import StageResultService
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main():
    c = json.loads(Path('/run/analysis/deployment.json').read_text())
    p = load_profile('/run/analysis/dispatcher.json')
    engine = create_async_engine(Path(p['database_url_file']).read_text().strip(), hide_parameters=True,
                                 connect_args=p['database_connect_args'])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = StageResultService(sessions)
    out = {'generation_calls': 0, 'embedding_calls': 0, 'dispatcher_started': False}
    try:
        lifecycle = AnalysisTaskPolicy(**json.loads(Path(p['lifecycle_policy_file']).read_text()))
        loaded = executors(json.loads(Path(p['executor_config_file']).read_text()), AnalysisTaskService(sessions, lifecycle))
        validate_executors(loaded)
        out['executors'] = sorted(loaded)
        async with service.transaction(UUID(p['tenant_id']), readonly=True) as store:
            row = (await store.db.execute(text('SELECT current_database() AS database,current_user AS role,ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()'))).mappings().one()
            out['postgres'] = dict(row)
            assert row['database'] == c['database'] and row['role'] == c['writer'] and row['ssl']
            for table in c['source_tables']:
                await store.db.execute(text('SELECT * FROM ' + table + ' LIMIT 0'))
            out['knowledge_insert_allowed'] = (await store.db.execute(text("SELECT has_table_privilege(current_user,'public.aisoc_kb_documents','INSERT')"))).scalar_one()
            out['case_count'] = (await store.db.execute(text('SELECT count(*) FROM socai2.cases'))).scalar_one()
            out['running_attempts'] = (await store.db.execute(text("SELECT count(*) FROM socai2.analysis_attempts WHERE local_state='running'"))).scalar_one()
            assert out['case_count'] == out['running_attempts'] == 0
        knowledge, fingerprint = load()
        assert knowledge.vector.collection == c['knowledge_collection'] and not knowledge.history.sync_after_adopted_triage
        vectors = Vectors(knowledge)
        info = await vectors.request('vector', 'GET', vectors.collection, absent=True)
        out['knowledge'] = {'profile_sha256': fingerprint, 'collection': knowledge.vector.collection,
                            'collection_exists_before_import': info is not None, 'calls': vectors.calls}
        async with httpx.AsyncClient(timeout=c['probe_timeout_seconds']) as client:
            response = await client.get(str(knowledge.embedding.url).removesuffix('/api/embed') + '/api/tags')
            response.raise_for_status()
            models = [item['name'] for item in response.json()['models']]
            assert knowledge.embedding.model in models
            out['knowledge']['embedding_model_listed'] = True
        assert settings.CLICKHOUSE_DATABASE == c['database'] and settings.CLICKHOUSE_USER == c['lake_reader']
        lake = LakeGateway(service)
        assert lake.configured()
        args = json.loads(Path('/run/analysis/lake-probe.json').read_text())
        assert lake.unavailable_reason(args['parameters']) is None
        rows = await lake.query(args, c['batch_id'] + '-source-readiness', 20)
        out['lake'] = {'query': args, 'rows': rows, 'row_count': len(rows), 'identity': settings.CLICKHOUSE_USER,
                       'database': settings.CLICKHOUSE_DATABASE, 'is_case_c4': False}
        assert rows and all(row['src_hostname'] == args['parameters']['hostname'] for row in rows)
        out['policy_sha256'] = active_policy().sha256
        out['runtime_files'] = {file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                                for file in Path('/run/analysis').iterdir() if file.is_file()}
        out['status'] = 'passed'
        print(json.dumps(out, default=str))
    finally:
        await close_clickhouse()
        await engine.dispose()


asyncio.run(main())
