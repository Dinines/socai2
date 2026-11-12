"""Release readback only: actual loaded source/profile and existing writer identity."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from app.db.case_database import close_case_database, get_case_write_sessions
from app.socai2 import knowledge_config, knowledge_history, knowledge_source, knowledge_sync, stage_results


async def main():
    profile, fingerprint = knowledge_config.load()
    service = stage_results.StageResultService(get_case_write_sessions())
    try:
        async with service.transaction(UUID(sys.argv[1]), readonly=True) as store:
            connection = dict((await store.db.execute(text("""SELECT current_database() AS database,
                current_user AS role, current_setting('app.current_tenant_id') AS tenant,
                has_table_privilege(current_user,'public.aisoc_kb_documents','SELECT') AS kb_select,
                has_table_privilege(current_user,'public.aisoc_kb_documents','INSERT') AS kb_insert"""))).mappings().one())
            policies = [dict(row) for row in (await store.db.execute(text("""SELECT policyname,roles,cmd,qual,with_check
                FROM pg_policies WHERE schemaname='public' AND tablename='aisoc_kb_documents'"""))).mappings()]
        assert connection['kb_select'] and connection['kb_insert']
        assert profile.history.sync_after_adopted_triage
        print(json.dumps({'state': 'loaded', 'connection': connection, 'existing_policies': policies,
            'profile_sha256': fingerprint, 'sync_enabled': profile.history.sync_after_adopted_triage,
            'sync_timeout_seconds': profile.history.sync_timeout_seconds,
            'embedding_model': profile.embedding.model, 'dimension': profile.embedding.dimension,
            'collection': profile.vector.collection, 'receipt_schema': knowledge_sync.VERSION,
            'source_sha256': {Path(module.__file__).name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                for module in (knowledge_config, knowledge_history, knowledge_source, knowledge_sync, stage_results)},
            'analysis_model_calls': 0, 'run_writes': 0, 'knowledge_writes': 0,
            'boundary': 'Production loaded configuration and read-only writer/RLS inspection; end-to-end synchronization was exercised locally.'}))
    finally:
        await close_case_database()


asyncio.run(main())
