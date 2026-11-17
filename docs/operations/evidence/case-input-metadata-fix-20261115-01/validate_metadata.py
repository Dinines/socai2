"""F2: real management writes and Case capture/check, explicitly synthetic model/query replies."""
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
import validate as seed_fixture
from controlled import Gateway, Lake, empty_query
from socai2_test_model_view import synthetic_measure

save = seed_fixture.save


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
    from app.socai2.baseline_context import capture
    from app.socai2.baseline_contracts import Actor, Start
    from app.socai2.baseline_store import F
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.case_update_inputs import business_view
    from app.socai2.subject_management import SubjectManagementService
    from app.socai2.subject_management_contracts import AlertManagementFields, FeedbackFields, SelectedSubject
    from redis.asyncio import Redis
    from sqlalchemy import select, text
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    seed_fixture.HERE = HERE
    await seed_fixture.main(SimpleNamespace(batch=args.batch + "-sources", seed_only=True), config)
    seed = json.loads((HERE / (args.batch + "-sources") / "result.json").read_text())
    tenant, aid = UUID(seed["tenant_id"]), UUID(seed["alert_ids"][0])
    actor = Actor(user_id=seed["actor_id"], name="Synthetic metadata verification")
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev"
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"]),
        hide_parameters=True, connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, management = CaseService(sessions), SubjectManagementService(sessions)
    tasks = AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    handlers = executors({k: config[k] for k in ("investigation_policy_file", "incident", "case")}, tasks)
    calls = []
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor.user_id, "alert_id": aid,
              "real_model_calls": 0, "checks": [], "tasks": []}

    class AlertGateway:
        provider, model = "synthetic", "synthetic-metadata-check"

        async def configure(self, *_):
            return True

        async def measure(self, body, stage):
            return await synthetic_measure(body, stage)

        async def complete(self, body, timeout):
            async with cases.transaction(tenant, readonly=True) as store:
                request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                    F.c.alert_id == aid, F.c.kind == "model_request")))).scalar_one()
                alert = await store.one(select(m.Alerts.__table__).where(m.Alerts.id == aid))
                assert alert["latest_material_id"] and alert["latest_triage_id"] is None
                task = await store.one(select(m.AnalysisTasks.__table__).where(m.AnalysisTasks.tenant_id == tenant,
                    m.AnalysisTasks.subject_id == aid))
                assert task["state"] == "running"
            result["checks"].append("alert_and_task_readable_before_model_reply")
            evidence = [sid for sid, row in request["source_map"].items() if row["ref"]["role"] == "observation"]
            answer = {"verdict": "needs_review", "confidence": .3, "rationale": "Synthetic observation; authorization needs review.",
                      "evidence_ids": evidence[:1], "recommendations": []}
            reply = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}],
                     "usage": {"prompt_tokens": 100, "completion_tokens": 60, "total_tokens": 160}}
            calls.append({"stage": "A", "request": body, "response": reply})
            return reply

    handlers["alert_triage"].gateway_factory = AlertGateway
    handlers["alert_triage"].query = empty_query
    handlers["case_investigation"].gateway_factory = lambda claim: Gateway(cases, tenant, claim, "normal", calls)
    handlers["case_investigation"].lake_factory = lambda claim: Lake()
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    policy = DispatchPolicy(**{**config["dispatch"], "receipt_directory": str(Path(config["dispatch"]["receipt_directory"]) / str(tenant))})
    dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), AnalysisQueues(redis, policy.namespace, tenant), policy, handlers)

    async def drain():
        async with asyncio.timeout(config["check_timeout_seconds"]):
            while True:
                await dispatcher.tick()
                async with tasks.transaction(tenant, readonly=True) as store:
                    count = (await store.db.execute(text("SELECT count(*) FROM socai2.analysis_tasks WHERE tenant_id=:tenant AND state IN ('accepted','waiting','running')"), {"tenant": tenant})).scalar_one()
                if not count:
                    return
                await asyncio.sleep(config["check_interval_seconds"])

    async def current(cid):
        async with cases.transaction(tenant, readonly=True) as store:
            case = await store.case(cid, lock=False)
            return await capture(store.db, tenant, cid, Start(expected_scope_revision=case["scope_revision"], operation_key=uuid4()))

    async def edit(changes, *, feedback=False):
        async with cases.transaction(tenant, readonly=True) as store:
            row = await store.one(select(m.Alerts.__table__).where(m.Alerts.id == aid))
        return await management.apply(tenant, "alerts", [SelectedSubject(id=aid, expected_row_version=row["row_version"])],
                                      changes, uuid4(), actor, feedback=feedback)

    async def check(cid):
        receipt = await tasks.submit(tenant, kind="case_investigation", subject_id=cid, intent="check",
                                     source="user", operation_key=uuid4(), submitted_by=actor.user_id)
        await drain()
        detail = await tasks.read_task(tenant, "case", cid, receipt["task_id"])
        result["tasks"].append(detail)
        return detail

    async def snapshot():
        models = (m.Alerts, m.AlertMaterials, m.AlertObjects, m.AlertAssessments, m.Cases, m.CaseAlerts,
            m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps,
            m.Artifacts, m.Results, m.ResultMembers, m.Activities, m.ActivityTargets)
        async with cases.transaction(tenant, readonly=True) as store:
            return {model.__tablename__: [dict(row) for row in (await store.db.execute(select(model.__table__)
                .where(model.tenant_id == tenant).order_by(*model.__table__.primary_key.columns))).mappings()]
                for model in models}

    try:
        with patch.object(baseline_enrichment_sources, "query", empty_query):
            await tasks.submit(tenant, kind="alert_triage", subject_id=aid, intent="initial", source="ingress", operation_key=uuid4())
            await dispatcher.start()
            await drain()
            created = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="Owner changes preserve A",
                alert_ids=[aid]), actor=actor)
            cid, tid = created.primary_case_id, created.allocations[0].initial_task.task_id
            result.update(case_id=cid, initial_task_id=tid)
            before = await current(cid)
            assert before.alerts[str(aid)].triage_usable
            if not args.before:
                await drain()
                initial = await tasks.read_task(tenant, "case", cid, tid)
                result["tasks"].append(initial)
                assert initial["status"] == "completed", initial
            save(out / "before-context.json", before)
            save(out / "management.json", await edit(AlertManagementFields(owner_id=actor.user_id, tags=["synthetic-owner-edit"])))
            after = await current(cid)
            save(out / "after-context.json", after)
            assert after.alerts[str(aid)].triage_usable, "management edit incorrectly invalidated same-material A"
            assert after.alerts[str(aid)].triage == before.alerts[str(aid)].triage
            assert after.alerts[str(aid)].queries == before.alerts[str(aid)].queries
            assert business_view(before) == business_view(after)
            count = len(calls)
            checked = await check(cid)
            assert checked["status"] == "skipped" and checked["reason_code"] == "no_changes"
            assert checked["latest_run_id"] is None and not checked["attempts"] and len(calls) == count
            result["checks"].append("owner_tags_edit_preserves_A_queries_and_check_skips_without_run_or_model")
            save(out / "feedback.json", await edit(FeedbackFields(disposition="needs_review", reason="Synthetic human evidence remains unverified."), feedback=True))
            feedback = await current(cid)
            assert feedback.alerts[str(aid)].triage_usable and business_view(feedback) != business_view(after)
            updated = await check(cid)
            assert updated["status"] == "completed", updated
            frozen = await cases.read_context(tenant, cid, updated["latest_run_id"])
            assert frozen.alerts[str(aid)].triage_usable and frozen.alerts[str(aid)].feedback
            save(out / "feedback-context.json", frozen)
            result["checks"].append("manual_check_includes_effective_feedback_and_original_A")
            result["state"] = "passed"
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
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
    parser.add_argument("--before", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    seed_fixture.environment(config)
    asyncio.run(run(args, config))
