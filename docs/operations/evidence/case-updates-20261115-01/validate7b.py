"""Periodic Case updates and active-event routing; explicit time/data/model substitutes."""
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
    from datetime import timedelta
    from app.socai2.baseline_contracts import Actor, Scope
    from app.socai2.baseline_context import reference
    from app.socai2.analysis_task_store import S
    from app.socai2.stage_results import StageResultService
    from app.socai2.stage_result_contracts import AlertOutput, IncidentOutput
    from app.socai2.runtime_policy import active_policy
    from app.socai2.case_management import manage_case
    from app.socai2.case_management_contracts import CaseCloseRequest
    from app.socai2.baseline_store import digest
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.human_task_contracts import TaskCreate, TaskEdit
    from app.socai2.human_task_service import HumanTaskService
    from redis.asyncio import Redis
    from sqlalchemy import insert, select, text, update
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
        models = (m.Incidents, m.IncidentAlerts, m.IncidentDiagnoses, m.AlertAssessments, m.Cases, m.CaseAlerts, m.Alerts, m.AlertMaterials, m.AlertObjects, m.AnalysisTasks, m.AnalysisAttempts,
            m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps, m.Artifacts, m.Results, m.ResultMembers,
            m.Tasks, m.TaskRevisions, m.CaseAssessments, m.CaseAssessmentSources, m.CaseAssessmentMembers)
        async with cases.transaction(tenant, readonly=True) as store:
            return {model.__tablename__: [dict(row) for row in (await store.db.execute(select(model.__table__)
                .where(model.tenant_id == tenant).order_by(*model.__table__.primary_key.columns))).mappings()]
                for model in models}

    executor = handlers["case_investigation"]
    stage = StageResultService(sessions)
    result["time_control"] = "Explicitly make only this tenant's next_check_at due; default interval/window config unchanged."
    hook_pending = set()

    async def late_feedback(claim, frozen):
        if claim.case_id not in hook_pending:
            return
        hook_pending.remove(claim.case_id)
        revision = (await cases.read_case(tenant, claim.case_id))["case"].scope_revision
        await human.write(tenant, claim.case_id, TaskCreate(operation_key=uuid4(), expected_scope_revision=revision,
            title="During-run synthetic H", state="completed", result_text="Synthetic late H; not independent observation.",
            result_scope=frozen.scope), actor=actor)
    executor.gateway_factory = lambda claim: Gateway(cases, tenant, claim, modes.get(claim.case_id, "normal"), calls, late_feedback)

    async def all_rows(model):
        table = model.__table__
        async with cases.transaction(tenant, readonly=True) as store:
            return [dict(r) for r in (await store.db.execute(select(table).where(table.c.tenant_id == tenant))).mappings()]

    async def rounds(cid):
        return sorted([r for r in await all_rows(m.Runs) if r["case_id"] == cid], key=lambda r:(r["started_at"], str(r["id"])))

    async def due(*ids):
        async with tasks.transaction(tenant) as store:
            now = await store.now()
            await store.db.execute(update(S).where(*store.where(S, S.c.subject_type == "case", S.c.subject_id.in_(ids)))
                .values(next_check_at=now-timedelta(seconds=1)))
        await drain()

    async def upstream(kind, identity, message):
        async with cases.transaction(tenant, readonly=True) as store:
            now = await store.now()
        policy = active_policy()
        claim = await stage.begin(tenant, kind, identity, uuid4(), producer="step7.synthetic-source.v1",
            limits=getattr(policy, kind).limits(now, policy.identity))
        async with stage.transaction(tenant, readonly=True) as store:
            from app.socai2.baseline_store import F
            source = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.id == claim["input_artifact_id"])))).scalar_one()
        refs = [reference("alert_material", row["material"]["id"], "observation", "$.raw_json.device.name") for row in source["members"]]
        if kind == "alert_basic":
            output = AlertOutput(verdict="needs_review", rationale=message, confidence=None,
                score_state="not_computed", explanation=message, generation_method="template",
                source_refs=refs, recommendations=[], limitations=["Synthetic upstream fixture."])
            members = None
        else:
            output = IncidentOutput(summary=message, conclusion=message, findings=[], source_refs=refs,
                open_questions=[], limitations=["Synthetic upstream fixture."])
            members = [{"alert_id": row["alert"]["id"], "state": "unresolved"} for row in source["members"]]
        save(out / (str(claim["run_id"]) + "-synthetic-upstream.json"), output)
        try:
            receipt = await stage.finish(tenant, claim["run_id"], output, validated_members=members)
        except Exception:
            await stage.stop(tenant, claim["run_id"], state="failed", code="synthetic_fixture_publication_failed")
            raise
        result.setdefault("synthetic_upstream_publications", []).append({"kind":kind,"run_id":claim["run_id"],"receipt":receipt})

    try:
        with patch.object(baseline_enrichment_sources, "query", empty_query):
            await dispatcher.start()
            aids = [UUID(v) for v in seed["alert_ids"]]
            iid = uuid4()
            async with cases.transaction(tenant) as store:
                await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=tenant, source_namespace="case-initial-fixture",
                    source_incident_id=str(iid), title="Step7 synthetic event"))
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant, incident_id=iid,
                    alert_id=aids[0], membership_source="fusion", correlation_basis={}, basis_version="step7.fixture", source_operation_id=uuid4()))
            created = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="Step7B active Case", incident_ids=[iid]), actor=actor)
            cid = created.primary_case_id
            await drain()
            first = await read(cid, created.allocations[0].initial_task.task_id)
            assert first["status"] == "completed", first
            await due(cid)
            assert len(await rounds(cid)) == 1
            result["checks"].append("periodic_no_changes_no_new_run")

            async with cases.transaction(tenant) as store:
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant, incident_id=iid,
                    alert_id=aids[1], membership_source="fusion", correlation_basis={}, basis_version="step7.fixture", source_operation_id=uuid4()))
            hook_pending.add(cid)
            await due(cid)
            history = await rounds(cid)
            assert len(history) == 2 and history[-1]["state"] == "completed", history
            frozen = await cases.read_context(tenant, cid, history[-1]["id"])
            assert len(frozen.alerts) == 2 and not frozen.update_context["business_view"]["human_feedback"]
            attempts = await all_rows(m.AnalysisAttempts)
            task_id = next(a["task_id"] for a in attempts if a["run_id"] == history[-1]["id"])
            task = next(t for t in await all_rows(m.AnalysisTasks) if t["id"] == task_id)
            assert task["source"] == "periodic" and task["submitted_by"] is None
            await due(cid)
            history = await rounds(cid)
            assert len(history) == 3 and history[-1]["state"] == "completed", history
            assert (await cases.read_context(tenant, cid, history[-1]["id"])).update_context["business_view"]["human_feedback"]
            result["checks"].append("event_follow_and_service_actor_late_H_waits_for_next_round")

            await upstream("alert_basic", aids[0], "Synthetic A authorization unresolved.")
            await due(cid)
            assert len(await rounds(cid)) == 4
            await upstream("incident_diagnosis", iid, "Synthetic I first conclusion.")
            await due(cid)
            assert len(await rounds(cid)) == 5
            await upstream("incident_diagnosis", iid, "Synthetic I first conclusion.")
            await due(cid)
            assert len(await rounds(cid)) == 5
            result["checks"].append("late_A_and_I_trigger_downstream_same_I_business_new_Run_does_not")

            second = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="Independent current receiver", incident_ids=[iid]), actor=actor)
            cid2 = second.primary_case_id
            await drain()
            assert (await rounds(cid2))[-1]["state"] == "completed"
            await upstream("incident_diagnosis", iid, "Synthetic I updated conclusion.")
            await due(cid, cid2)
            assert len(await rounds(cid)) == 5 and len(await rounds(cid2)) == 2
            old_manual = await submit(cid, "check")
            assert old_manual["status"] == "completed", old_manual
            assert len(await rounds(cid)) == 6
            incident = (await all_rows(m.Incidents))[0]
            assert incident["active_case_id"] == cid2
            result["checks"].append("new_I_only_current_receiver_automatic_old_case_manual_uses_I_without_stealing")

            from app.socai2.analysis_task_store import AnalysisTaskStore
            async with tasks.transaction(tenant, readonly=True) as store:
                future = (await store.now()) + timedelta(seconds=tasks.policy.automatic_window_seconds+1)
            async def future_now(_store):
                return future
            await upstream("incident_diagnosis", iid, "Synthetic I after automatic expiry.")
            with patch.object(AnalysisTaskStore, "now", future_now):
                expired = await executor.check_updates(tenant, future)
            assert expired["submitted"] == 0
            assert len(await rounds(cid2)) == 2
            manual = await submit(cid2, "check")
            assert manual["status"] == "completed", manual
            status = (await tasks.list_tasks(tenant,"case",cid2))["update_state"]
            assert status["eligible"]
            row = (await cases.read_case(tenant,cid2))["case"]
            await manage_case(cases,tenant,cid2,CaseCloseRequest(operation_key=uuid4(),expected_row_version=row.row_version),actor,action="case_closed")
            await due(cid2)
            assert len(await rounds(cid2)) == 3
            result["checks"].append("expired_scan_skips_manual_completion_renews_closed_scan_skips")

            before = json.loads(json.dumps(await snapshot(),default=str))
            for case_id in (cid,cid2):
                for record in await rounds(case_id):
                    rv = await cases.read_run(tenant,case_id,record["id"])
                    for result_id in rv["result_ids"]:
                        saved = await cases.read_result(tenant,case_id,result_id)
                        assert saved["result"].comparison_context == rv["run"].comparison_context
                save(out/(str(case_id)+"-history.json"), await cases.read_history(tenant,case_id))
            after = json.loads(json.dumps(await snapshot(),default=str))
            assert digest(before) == digest(after)
            assert all(a["local_state"] == "ended" for a in before["analysis_attempts"])
            assert all(r["state"] == "completed" for r in before["runs"])
            result["checks"].append("periodic_saved_IO_comparison_read_only_unchanged")
            result.update(state="passed", case_ids=[cid,cid2], incident_id=iid, read_only_tables=len(before),
                case_runs=len(await rounds(cid))+len(await rounds(cid2)), snapshot_sha256=digest(before))
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
