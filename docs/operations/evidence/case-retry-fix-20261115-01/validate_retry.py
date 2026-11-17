"""Real Case/PG/Redis retry checks, controlled clock and explicit model substitutes."""
import argparse
import asyncio
import hashlib
import json
import sys
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "services/api"), str(ROOT / "services/api/tests"),
               str(HERE.parent / "case-initial-20261115-01")]
import validate as seed_fixture
from controlled import Gateway, Lake, empty_query

save = seed_fixture.save


async def run(args, config):
    import httpx
    from app.models import socai2 as m
    from app.socai2 import baseline_context, baseline_enrichment_sources
    from app.socai2.analysis_case_executor import executors
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_store import BaselineStore, F
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.model_errors import ModelCallError, provider_error
    from redis.asyncio import Redis
    from sqlalchemy import select
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    seed_fixture.HERE = HERE
    await seed_fixture.main(SimpleNamespace(batch=args.batch + "-sources", seed_only=True), config)
    seed = json.loads((HERE / (args.batch + "-sources") / "result.json").read_text())
    tenant, aid = UUID(seed["tenant_id"]), UUID(seed["alert_ids"][0])
    actor = Actor(user_id=seed["actor_id"], name="Synthetic retry verification")
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev"
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"]),
        hide_parameters=True, connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases = CaseService(sessions)
    tasks = AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    handlers = executors({k: config[k] for k in ("investigation_policy_file", "incident", "case")}, tasks)
    calls, faults, modes = [], [], {}
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor.user_id,
              "real_model_calls": 0, "checks": [], "tasks": [], "clock_offsets_seconds": [0]}
    offset = 0
    original_now = BaselineStore.now
    original_capture = baseline_context.capture

    async def controlled_now(store):
        return await original_now(store) + timedelta(seconds=offset)

    async def controlled_capture(*args, **kwargs):
        context = await original_capture(*args, **kwargs)
        return context.model_copy(update={"captured_at": context.captured_at + timedelta(seconds=offset)})

    class FaultGateway(Gateway):
        async def complete(self, body, timeout):
            async with cases.transaction(tenant, readonly=True) as store:
                request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                    F.c.run_id == self.claim.run_id, F.c.kind == "model_request"))
                    .order_by(F.c.captured_at.desc()).limit(1))).scalar_one()["payload"]
            stage = request["case_boundary"].get("stage", "C3")
            mode = modes[self.claim.case_id]
            prior_faults = sum(row["case_id"] == str(self.claim.case_id) for row in faults)
            error_type = (httpx.ConnectTimeout if mode == "connect" and stage == "C3" and not prior_faults
                else httpx.PoolTimeout if mode == "pool" and stage == "C6"
                else httpx.ReadTimeout if mode == "read" and stage == "C3" else None)
            if error_type:
                failure = ModelCallError(provider_error(error_type("Synthetic transport failure"), ""))
                faults.append({"case_id": str(self.claim.case_id), "run_id": str(self.claim.run_id),
                    "stage": stage, "request": body, "transport_error": failure.payload()})
                raise failure
            return await super().complete(body, timeout)

    handlers["case_investigation"].gateway_factory = lambda claim: FaultGateway(cases, tenant, claim, "normal", calls)
    handlers["case_investigation"].lake_factory = lambda claim: Lake()
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    policy = DispatchPolicy(**{**config["dispatch"], "max_running_tasks": 1,
        "receipt_directory": str(Path(config["dispatch"]["receipt_directory"]) / str(tenant))})
    dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), AnalysisQueues(redis, policy.namespace, tenant),
        policy, handlers, clock=lambda: datetime.now(UTC) + timedelta(seconds=offset))

    async def create(mode):
        created = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="Synthetic retry: " + mode,
            alert_ids=[aid]), actor=actor)
        modes[created.primary_case_id] = mode
        return created.primary_case_id, created.allocations[0].initial_task.task_id

    async def read(pair):
        return await tasks.read_task(tenant, "case", *pair)

    async def until(pair, status):
        async with asyncio.timeout(config["check_timeout_seconds"]):
            while True:
                await dispatcher.tick()
                current = await read(pair)
                internal = await dispatcher.repository.task(pair[1])
                if internal["state"] == status:
                    result["tasks"].append(current)
                    return current
                if current["status"] in {"completed", "failed", "skipped", "merged"}:
                    raise AssertionError(current)
                await asyncio.sleep(config["check_interval_seconds"])

    async def snapshot():
        models = (m.Cases, m.CaseAlerts, m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState,
            m.Runs, m.RunMembers, m.RunSteps, m.Artifacts, m.Results, m.ResultMembers, m.CaseAssessments,
            m.CaseAssessmentSources, m.Activities, m.ActivityTargets)
        async with cases.transaction(tenant, readonly=True) as store:
            return {model.__tablename__: [dict(row) for row in (await store.db.execute(select(model.__table__)
                .where(model.tenant_id == tenant).order_by(*model.__table__.primary_key.columns))).mappings()]
                for model in models}

    try:
        with (patch.object(BaselineStore, "now", controlled_now),
              patch.object(baseline_context, "capture", controlled_capture),
              patch.object(baseline_enrichment_sources, "query", empty_query)):
            await dispatcher.start()
            connect = await create("connect")
            waiting = await until(connect, "waiting")
            assert len(waiting["attempts"]) == 1 and waiting["reason_code"] == "retry_scheduled"
            first = waiting["attempts"][0]
            assert first["outcome"] == "failed" and first["retryable"]
            save(out / "connect-first-snapshot.json", await snapshot())
            for _ in range(2):
                await dispatcher.tick()
            assert (await read(connect))["status"] == "accepted" and len(faults) == 1
            raw_waiting = await dispatcher.repository.task(connect[1])
            assert raw_waiting["retry_limit"] == 1 and raw_waiting["retry_delay_seconds"] == 60
            assert raw_waiting["next_retry_at"] == first["failed_at"] + timedelta(seconds=60)
            offset += 61
            result["clock_offsets_seconds"].append(offset)
            completed = await until(connect, "completed")
            assert len(completed["attempts"]) == 2 and completed["attempts"][0] == first
            assert len({a["run_id"] for a in completed["attempts"]}) == 2
            result["checks"].append("connect_failed_then_same_task_new_run_once_after_60_seconds")

            pool = await create("pool")
            waiting = await until(pool, "waiting")
            pool_first = waiting["attempts"][0]
            save(out / "pool-first-snapshot.json", await snapshot())
            offset += 61
            result["clock_offsets_seconds"].append(offset)
            exhausted = await until(pool, "failed")
            assert exhausted["reason_code"] == "retry_exhausted" and len(exhausted["attempts"]) == 2
            assert exhausted["attempts"][0] == pool_first
            result["checks"].append("C6_pool_failure_keeps_C3_and_exhausts_one_retry")

            read_timeout, survivor = await create("read"), await create("normal")
            uncertain = await until(read_timeout, "failed")
            assert uncertain["attempts"][0]["outcome"] == "unknown" and len(uncertain["attempts"]) == 1
            save(out / "unknown-snapshot.json", await snapshot())
            await until(survivor, "completed")
            assert await read(read_timeout) == uncertain
            assert not dispatcher.active and not dispatcher.receipts
            result["checks"].append("ReadTimeout_keeps_unknown_without_retry_and_next_case_completes_at_N1")
            result["state"] = "passed"
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        result.update(substitute_model_responses=len(calls), substituted_transport_failures=len(faults))
        save(out / "result.json", result)
        save(out / "calls.json", calls)
        save(out / "faults.json", faults)
        save(out / "snapshot.json", await snapshot())
        paths = ["baseline_failure", "baseline_reasoning", "baseline_analysis", "baseline_deep", "baseline_delivery",
                 "baseline_reanalysis", "baseline_executor", "baseline_closing", "analysis_dispatch_store", "analysis_task_store"]
        save(out / "source-hashes.json", {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for name in paths if (p := ROOT / "services/api/app/socai2" / (name + ".py")).is_file()})
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    seed_fixture.environment(config)
    asyncio.run(run(args, config))
