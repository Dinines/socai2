"""Candidate A/I readiness only: real resolver/tokenizer, never generation or dispatch."""
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import UUID

import httpx
from app.socai2.analysis_case_executor import executors
from app.socai2.analysis_dispatch_runtime import load_profile, validate_executors
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_analysis_model import TenantChatGateway
from app.socai2.runtime_policy import active_policy
from app.socai2.stage_results import StageResultService
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main():
    config = json.loads(Path('/run/probe/deployment.json').read_text())
    profile = load_profile('/run/analysis/dispatcher.json')
    policy = active_policy()
    engine = create_async_engine(Path(profile['database_url_file']).read_text().strip(),
        hide_parameters=True, connect_args=profile['database_connect_args'])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    lifecycle = AnalysisTaskPolicy(**json.loads(Path(profile['lifecycle_policy_file']).read_text()))
    task_service = AnalysisTaskService(sessions, lifecycle)
    stage_service = StageResultService(sessions)
    redis = Redis.from_url(Path(profile['redis_url_file']).read_text().strip(),
        socket_timeout=profile['redis_socket_timeout_seconds'],
        socket_connect_timeout=profile['redis_connect_timeout_seconds'])
    out = {'generation_calls': 0, 'dispatcher_started': False}
    try:
        loaded = executors(json.loads(Path(profile['executor_config_file']).read_text()), task_service)
        validate_executors(loaded)
        out['executors'] = sorted(loaded)
        async with stage_service.transaction(UUID(profile['tenant_id']), readonly=True) as store:
            row = (await store.db.execute(text('SELECT current_database() AS database, current_user AS role, ssl, version FROM pg_stat_ssl WHERE pid=pg_backend_pid()'))).mappings().one()
            out['postgres'] = dict(row)
            assert row['database'] == config['database'] and row['role'] == config['writer'] and row['ssl']
            for table in config['source_tables']:
                await store.db.execute(text('SELECT * FROM '+table+' LIMIT 0'))
            out['readable_sources'] = config['source_tables']
            out['guard_counts'] = {name: (await store.db.execute(text('SELECT count(*) FROM socai2.'+name))).scalar_one()
                for name in ('runs', 'analysis_attempts', 'cases')}
            assert not any(out['guard_counts'].values())
        out['redis'] = {'ping': await redis.ping(), 'keys': await redis.dbsize(), 'database': config['redis_db']}
        assert out['redis']['keys'] == 0
        gateway = TenantChatGateway()
        assert await gateway.configure(stage_service, UUID(profile['tenant_id']))
        assert gateway.model == config['model_alias'] and gateway.config.base_url == config['model_base_url']
        assert gateway.provider == policy.model.protocol and gateway.schema_profile == policy.model.schema_profile
        out['model'] = {'allowed': True, 'source': gateway.config.source, 'alias': gateway.model,
            'base_url': gateway.config.base_url, 'protocol': gateway.provider, 'schema_profile': gateway.schema_profile}
        async with httpx.AsyncClient(timeout=config['probe_timeout_seconds'], trust_env=False) as client:
            response = await client.get(config['model_base_url']+'/models', headers={'Authorization': 'Bearer '+gateway.config.api_key})
            response.raise_for_status()
            aliases = [item['id'] for item in response.json()['data']]
            assert gateway.model in aliases
            out['model']['alias_listed'] = True
            response = await client.get(config['backend_base_url']+'/models')
            response.raise_for_status()
            models = [item['id'] for item in response.json()['data']]
            assert config['backend_model'] in models
            out['model']['backend_models'] = models
        body = {'model': gateway.model, 'messages': [{'role': 'user', 'content': 'Token counting readiness only.'}],
            'max_tokens': policy.model.output_tokens['A'], 'temperature': 0}
        out['token_measurement'] = await gateway.measure(body, 'A')
        assert out['token_measurement']['context_fits']
        out['policy_sha256'] = policy.sha256
        out['runtime_files'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path('/run/analysis').iterdir() if p.is_file()}
        out['status'] = 'passed'
        print(json.dumps(out))
    finally:
        await redis.aclose()
        await engine.dispose()


asyncio.run(main())
