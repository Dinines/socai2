"""Consume only the HTTP partner's fresh tenant with actual Case code and explicit substitutes."""
import argparse
import asyncio
import json
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from validate7a import environment, save


async def run(args, config):
    from app.socai2 import baseline_enrichment_sources
    from app.socai2.analysis_case_executor import executors
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_service import BaselineService
    from controlled import Gateway, Lake, empty_query
    from redis.asyncio import Redis
    from sqlalchemy import text
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev" and not args.output.exists()
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"]),
        hide_parameters=True, connect_args={"sslmode":config["sslmode"], "options":"-c role="+cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    tasks = AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    cases = BaselineService(sessions)
    handlers = executors({key:config[key] for key in ("investigation_policy_file", "incident", "case")}, tasks)
    calls = []
    handlers["case_investigation"].gateway_factory = lambda claim: Gateway(cases, args.tenant, claim, "normal", calls)
    handlers["case_investigation"].lake_factory = lambda claim: Lake()
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    policy = DispatchPolicy(**{**config["dispatch"], "receipt_directory": str(Path(config["dispatch"]["receipt_directory"])/str(args.tenant))})
    dispatcher = AnalysisDispatcher(DispatchRepository(tasks, args.tenant), AnalysisQueues(redis, policy.namespace, args.tenant), policy, handlers)
    try:
        with patch.object(baseline_enrichment_sources, "query", empty_query):
            async with tasks.transaction(args.tenant, readonly=True) as store:
                before = [dict(row) for row in (await store.db.execute(text("SELECT id,subject_id,intent,state FROM socai2.analysis_tasks WHERE tenant_id=:tenant ORDER BY submitted_at,id"), {"tenant":args.tenant})).mappings()]
            assert len(before) == 3 and [t["intent"] for t in before] == ["initial", "check", "rerun"]
            assert all(t["state"] == "accepted" for t in before)
            await dispatcher.start()
            async with asyncio.timeout(config["check_timeout_seconds"]):
                while True:
                    await dispatcher.tick()
                    async with tasks.transaction(args.tenant, readonly=True) as store:
                        waiting = (await store.db.execute(text("SELECT count(*) FROM socai2.analysis_tasks WHERE tenant_id=:tenant AND state IN ('accepted','waiting','running')"),
                            {"tenant":args.tenant})).scalar_one()
                    if not waiting:
                        break
                    await asyncio.sleep(config["check_interval_seconds"])
        after = [await tasks.read_task(args.tenant,"case",t["subject_id"],t["id"]) for t in before]
        assert [t["status"] for t in after] == ["completed", "skipped", "completed"], after
        assert after[1]["reason_code"] == "no_changes" and not after[1]["attempts"]
        assert after[0]["latest_run_id"] != after[2]["latest_run_id"]
        assert len(calls) == 4
        save(args.output, {"state":"passed", "before":before, "after":after, "tenant_id":args.tenant, "real_model_calls":0, "substitute_model_calls":len(calls), "calls":calls})
    finally:
        for _, future in dispatcher.active.values():
            future.cancel()
        if dispatcher.active:
            await asyncio.gather(*(future for _, future in dispatcher.active.values()), return_exceptions=True)
        dispatcher._collect()
        await dispatcher._flush_receipts()
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tenant", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    environment(config)
    asyncio.run(run(args, config))
