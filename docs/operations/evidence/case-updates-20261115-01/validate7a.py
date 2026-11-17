"""Fresh Case updates through actual PG/Redis/C1-C6; explicit no-network dependencies."""
import argparse
import asyncio
import json
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "services/api"), str(ROOT / "services/api/tests"),
    str(HERE.parent / "case-initial-20261115-01")]
import validate as initial_fixture
from controlled import Gateway, Lake, empty_query

save, environment = initial_fixture.save, initial_fixture.environment


async def run(args, config):
    from app.models import socai2 as m
    from app.socai2 import baseline_enrichment_sources
    from app.socai2.analysis_case_executor import executors
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_contracts import Actor, Scope
    from app.socai2.baseline_store import digest
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.human_task_contracts import TaskCreate, TaskEdit
    from app.socai2.human_task_service import HumanTaskService
    from redis.asyncio import Redis
    from sqlalchemy import select, text
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    initial_fixture.HERE = HERE
    await initial_fixture.main(SimpleNamespace(batch=args.batch + "-sources", seed_only=True), config)
    seed = json.loads((HERE / (args.batch + "-sources") / "result.json").read_text())
    tenant, actor = UUID(seed["tenant_id"]), Actor(user_id=seed["actor_id"], name="Case updates synthetic verification")
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev"
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"]),
        hide_parameters=True, connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, human = CaseService(sessions), HumanTaskService(sessions)
    tasks = AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    handlers = executors({key: config[key] for key in ("investigation_policy_file", "incident", "case")}, tasks)
    calls, modes = [], {}
    handlers["case_investigation"].gateway_factory = lambda claim: Gateway(cases, tenant, claim, modes.get(claim.case_id, "normal"), calls)
    handlers["case_investigation"].lake_factory = lambda claim: Lake()
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    policy = DispatchPolicy(**{**config["dispatch"], "receipt_directory": str(Path(config["dispatch"]["receipt_directory"]) / str(tenant))})
    dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), AnalysisQueues(redis, policy.namespace, tenant), policy, handlers)
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor.user_id, "checks": [],
              "real_model_calls": 0, "database": cfg["processing_database"], "tasks": []}

    async def drain():
        async with asyncio.timeout(config["check_timeout_seconds"]):
            while True:
                await dispatcher.tick()
                async with tasks.transaction(tenant, readonly=True) as store:
                    count = (await store.db.execute(text("SELECT count(*) FROM socai2.analysis_tasks WHERE tenant_id=:tenant AND state IN ('accepted','waiting','running')"), {"tenant": tenant})).scalar_one()
                if not count:
                    return
                await asyncio.sleep(config["check_interval_seconds"])

    async def read(cid, tid):
        detail = await tasks.read_task(tenant, "case", cid, tid)
        result["tasks"].append(detail)
        save(out / (str(tid) + ".json"), detail)
        if detail["latest_run_id"]:
            save(out / (str(tid) + "-run.json"), await cases.read_run(tenant, cid, detail["latest_run_id"]))
            for ref in detail["results"]:
                save(out / (str(ref["id"]) + "-result.json"), await cases.read_result(tenant, cid, ref["id"]))
        return detail

    async def submit(cid, mode):
        receipt = await tasks.submit(tenant, kind="case_investigation", subject_id=cid, intent=mode,
            source="user", operation_key=uuid4(), submitted_by=actor.user_id)
        await drain()
        return await read(cid, receipt["task_id"])

    async def snapshot():
        models = (m.Cases, m.CaseAlerts, m.Alerts, m.AlertMaterials, m.AlertObjects, m.AnalysisTasks, m.AnalysisAttempts,
            m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps, m.Artifacts, m.Results, m.ResultMembers,
            m.Tasks, m.TaskRevisions, m.CaseAssessments, m.CaseAssessmentSources, m.CaseAssessmentMembers)
        async with cases.transaction(tenant, readonly=True) as store:
            return {model.__tablename__: [dict(row) for row in (await store.db.execute(select(model.__table__)
                .where(model.tenant_id == tenant).order_by(*model.__table__.primary_key.columns))).mappings()]
                for model in models}

    try:
        with patch.object(baseline_enrichment_sources, "query", empty_query):
            await dispatcher.start()
            created = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="Step7A initial and updates",
                alert_ids=seed["alert_ids"]), actor=actor)
            cid = created.primary_case_id
            await drain()
            first = await read(cid, created.allocations[0].initial_task.task_id)
            assert first["status"] == "completed", first
            initial = await cases.read_run(tenant, cid, first["latest_run_id"])
            assert initial["run"].comparison_context.state == "initial"
            before_calls = len(calls)
            checked = await submit(cid, "check")
            assert checked["status"] == "skipped" and checked["reason_code"] == "no_changes"
            assert checked["latest_run_id"] is None and checked["attempts"] == [] and len(calls) == before_calls
            result["checks"].append("initial_completed_then_check_no_run_or_generation")

            rerun = await submit(cid, "rerun")
            assert rerun["status"] == "completed", rerun
            run = (await cases.read_run(tenant, cid, rerun["latest_run_id"]))["run"]
            assert run.comparison_context.state == "eligible" and run.comparison_context.previous_run_id == first["latest_run_id"]
            assert run.comparison_result_id == first["results"][0]["id"]
            result["checks"].append("rerun_same_material_new_run_compares_previous_actual_run")

            scope = Scope(kind="whole_case", alert_ids=seed["alert_ids"], object_keys=[], window_start=None, window_end=None, limitations=[])
            revision = (await cases.read_case(tenant, cid))["case"].scope_revision
            feedback = await human.write(tenant, cid, TaskCreate(operation_key=uuid4(), expected_scope_revision=revision,
                title="Synthetic H", state="completed", result_text="Synthetic analyst statement; authorization remains unverified.",
                result_scope=scope), actor=actor)
            updated = await submit(cid, "check")
            assert updated["status"] == "completed", updated
            frozen = await cases.read_context(tenant, cid, updated["latest_run_id"])
            assert str(feedback.task.id) in frozen.update_context["business_view"]["human_feedback"]
            current = (await cases.read_run(tenant, cid, updated["latest_run_id"]))["run"]
            assert current.comparison_context.previous_run_id == rerun["latest_run_id"]
            result["checks"].append("effective_H_change_runs_full_pipeline_with_frozen_prior_and_original")

            fields = dict(title="Rename only", state="completed", result_text=feedback.task.current.result_text, result_scope=scope)
            await human.write(tenant, cid, TaskEdit(operation_key=uuid4(), expected_scope_revision=revision,
                expected_row_version=feedback.task.row_version, **fields), actor=actor, task_id=feedback.task.id)
            same = await submit(cid, "check")
            assert same["status"] == "skipped" and same["reason_code"] == "no_changes", same
            result["checks"].append("H_new_revision_same_business_skips")

            modes[cid] = "capacity"
            failed = await submit(cid, "rerun")
            assert failed["status"] == "failed" and failed["reason_code"] == "capacity_exceeded", failed
            stopped = await submit(cid, "check")
            assert stopped["status"] == "skipped" and not stopped["attempts"]
            modes[cid] = "normal"
            after = await submit(cid, "rerun")
            assert after["status"] == "completed", after
            previous = (await cases.read_run(tenant, cid, after["latest_run_id"]))["run"].comparison_context
            assert previous.previous_run_id == failed["latest_run_id"]
            assert previous.state == "unavailable" and previous.comparison_result_id is None
            result["checks"].append("failed_previous_is_preserved_no_fallback_to_older_success")

            before = await snapshot()
            history = await cases.read_history(tenant, cid)
            detail = await cases.read_case(tenant, cid)
            for entry in history.items:
                assert entry.run.comparison_context is not None
                if entry.result:
                    assert entry.result.comparison_context == entry.run.comparison_context
            save(out / "history.json", history)
            save(out / "case.json", detail)
            for ref in after["results"]:
                save(out / "adoption-preview.json", await cases.preview_result_adoption(tenant, cid, ref["id"]))
            old_first = await cases.read_run(tenant, cid, first["latest_run_id"])
            assert old_first["run"].comparison_context == initial["run"].comparison_context
            after_reads = await snapshot()
            assert digest(json.loads(json.dumps(before, default=str))) == digest(json.loads(json.dumps(after_reads, default=str)))
            result["checks"].append("all_frozen_comparison_views_remain_stable_reads_do_not_write")
            result.update(state="passed", case_id=cid, read_only_tables=len(before),
                snapshot_sha256=digest(json.loads(json.dumps(before, default=str))))
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        for _, future in dispatcher.active.values():
            future.cancel()
        if dispatcher.active:
            await asyncio.gather(*(future for _, future in dispatcher.active.values()), return_exceptions=True)
        dispatcher._collect()
        await dispatcher._flush_receipts()
        result["substitute_model_calls"] = len(calls)
        save(out / "result.json", result)
        save(out / "calls.json", calls)
        save(out / "snapshot.json", await snapshot())
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    environment(config)
    asyncio.run(run(args, config))
