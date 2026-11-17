"""Fresh tenant, real PG/Redis/C1-C6; explicit model and source substitutes."""
import argparse
import asyncio
import json
import os
import sys
import traceback
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "services/api"), str(ROOT / "services/api/tests")]


def save(path, value):
    path.write_text(json.dumps(value, default=lambda v: v.model_dump(mode="json")
        if hasattr(v, "model_dump") else str(v), ensure_ascii=False, indent=2) + "\n")


def environment(config):
    os.environ.update(json.loads(Path(config["environment_file"]).read_text()))
    os.environ.update(config["runtime_overrides"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = config["investigation_policy_file"]
    os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = config["lifecycle_policy_file"]
    os.environ["SOCAI2_CASE_ALLOCATION_CONFIG_FILE"] = config["allocation_policy_file"]
    os.environ.pop("SOCAI2_KNOWLEDGE_PROFILE", None)


async def main(args, config):
    from app.models import socai2 as m
    from app.socai2 import baseline_enrichment_sources
    from app.socai2.analysis_case_executor import executors
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_store import F, R, digest
    from app.socai2.case_contracts import AssociationRequest, CaseCreate
    from app.socai2.case_execution_input import initial_input_versions
    from app.socai2.case_service import CaseService
    from controlled import Gateway, Lake, empty_query
    from redis.asyncio import Redis
    from sqlalchemy import insert, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from test_socai2_baseline_evidence import original

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev"
    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=Path(cfg["password_file"]).read_text().strip(),
        host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    admin = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"]})
    engine = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"], "options": "-c role="+cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, tasks = CaseService(sessions), AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    tenant, actor_id = uuid4(), uuid4()
    actor = Actor(user_id=actor_id, name="Case initial synthetic verification")
    result = {"tenant_id": tenant, "actor_id": actor_id, "state": "running", "checks": [],
              "database": cfg["processing_database"], "real_model_calls": 0, "cases": {}}
    calls, modes, lakes, rows, dispatcher = [], {}, {}, {}, None
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())

    async def table(model):
        tbl = model.__table__
        async with cases.transaction(tenant, readonly=True) as store:
            return [dict(r) for r in (await store.db.execute(select(tbl).where(tbl.c.tenant_id == tenant)
                .order_by(*tbl.primary_key.columns))).mappings()]

    async def alert(*, missing_time=False):
        aid, mid, host = uuid4(), uuid4(), "case-initial.test.invalid"
        async with cases.transaction(tenant) as store:
            now = await store.now()
            await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant, source_namespace="case-initial-fixture",
                source_identity_key=str(aid), title="Synthetic observed process", description="Explicit synthetic Case input.",
                event_time=None if missing_time else now, event_time_source="unknown" if missing_time else "source"))
            await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid, revision=1,
                raw_text="Synthetic original observation.", raw_json=original(host), detection={}, source_scope={},
                retention={}, material_state="complete"))
            await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
            await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant, alert_id=aid, material_id=mid,
                object_type="host", object_role="entity", object_key="host:"+host, namespace="case-initial-fixture",
                raw_value=host, normalized_value=host, source_path="$.raw_json.device.name", attributes={}))
        return aid

    async def add(cid, aid):
        revision = (await cases.read_case(tenant, cid))["case"].scope_revision
        return await cases.associate(tenant, cid, AssociationRequest(operation_key=uuid4(),
            expected_scope_revision=revision, alert_ids=[aid]), actor=actor)

    async def snapshot():
        models = (m.Alerts, m.AlertMaterials, m.AlertObjects, m.Cases, m.CaseAlerts, m.AnalysisTasks,
            m.AnalysisAttempts, m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps, m.Artifacts,
            m.Results, m.ResultMembers, m.CaseAssessments, m.CaseAssessmentSources, m.CaseAssessmentMembers)
        return {model.__tablename__: await table(model) for model in models}

    try:
        async with admin.begin() as db:
            await db.execute(text("""INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES(:id,'Case initial fixture',:slug,'enterprise',true,'{}','{}',now(),now())"""),
                {"id": tenant, "slug": "case-initial-"+str(tenant)})
            await db.execute(text("""INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
                VALUES(:id,:tenant,:email,:name,'!','soc_analyst',true,false,'{}',now(),now())"""),
                {"id": actor_id, "tenant": tenant, "email": str(actor_id)+"@example.invalid", "name": actor.name})
        if args.seed_only:
            result.update(state="sources_ready_no_tasks", alert_ids=[await alert(), await alert()])
            return
        for mode in ("timing", "missing_time", "query_failure", "capacity", "after_capacity"):
            aid = await alert(missing_time=mode == "missing_time")
            receipt = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="Case initial "+mode,
                alert_ids=[aid]), actor=actor)
            cid, tid = receipt.primary_case_id, receipt.allocations[0].initial_task.task_id
            modes[cid], rows[mode] = mode, {"case_id": cid, "task_id": tid, "initial_alert_id": aid}
            result["cases"][mode] = rows[mode]
        assert await table(m.Runs) == [] and await table(m.AnalysisAttempts) == []
        result["checks"].append("admission_creates_task_without_run")
        save(out/"intent.json", result)
        late_before, late_during = await alert(), await alert()
        timing = rows["timing"]
        handlers = executors({key: config[key] for key in ("investigation_policy_file", "incident", "case")}, tasks)
        executor = handlers["case_investigation"]
        original_load = executor.load

        async def load_then_add(task):
            material = await original_load(task)
            if task["subject_id"] == timing["case_id"]:
                await add(timing["case_id"], late_before)
            return material

        async def running_hook(claim, frozen):
            if modes[claim.case_id] != "timing":
                return
            attempts = await table(m.AnalysisAttempts)
            attempt = next(a for a in attempts if a["run_id"] == claim.run_id)
            assert attempt["input_artifact_id"] == claim.input_artifact_id and attempt["policy_artifact_id"]
            assert set(frozen.alerts) == {str(timing["initial_alert_id"]), str(late_before)}
            assert attempt["input_digest"] == digest(initial_input_versions(frozen))
            before = digest(frozen.model_dump(mode="json"))
            await add(claim.case_id, late_during)
            async with cases.transaction(tenant, readonly=True) as store:
                after = await store.read_context(claim.case_id, claim.run_id)
            assert digest(after.model_dump(mode="json")) == before
            result["checks"].append("fresh_at_claim_immutable_during_execution")

        executor.load = load_then_add
        executor.gateway_factory = lambda claim: Gateway(cases, tenant, claim, modes[claim.case_id], calls, running_hook)
        def make_lake(claim):
            lakes[claim.case_id] = Lake(modes[claim.case_id])
            return lakes[claim.case_id]
        executor.lake_factory = make_lake
        policy = DispatchPolicy(**{**config["dispatch"], "receipt_directory": str(Path(config["dispatch"]["receipt_directory"])/args.batch)})
        dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), AnalysisQueues(redis, policy.namespace, tenant), policy, handlers)
        with patch.object(baseline_enrichment_sources, "query", empty_query):
            await dispatcher.start()
            async with asyncio.timeout(config["check_timeout_seconds"]):
                while True:
                    await dispatcher.tick()
                    current = await table(m.AnalysisTasks)
                    if all(t["state"] not in {"accepted", "waiting", "running"} for t in current):
                        break
                    await asyncio.sleep(config["check_interval_seconds"])
        save(out/"before-assertions.json", await snapshot())
        for mode, row in rows.items():
            detail = await tasks.read_task(tenant, "case", row["case_id"], row["task_id"])
            save(out/(mode+"-task.json"), detail)
            attempts = [a for a in await table(m.AnalysisAttempts) if a["task_id"] == row["task_id"]]
            assert len(attempts) == 1 and attempts[0]["local_state"] == "ended", (mode, attempts)
            run_id = attempts[0]["run_id"]
            row["run_id"] = run_id
            run = next(r for r in await table(m.Runs) if r["id"] == run_id)
            assert run["state"] == ("failed" if mode == "capacity" else "completed"), (mode, run)
            artifacts = [f for f in await table(m.Artifacts) if f["run_id"] == run_id]
            async with cases.transaction(tenant, readonly=True) as store:
                frozen = await store.read_context(row["case_id"], run_id)
            if mode == "capacity":
                assert run["stop_reason"] == "capacity_exceeded" and not [c for c in calls if c["run_id"] == str(run_id)]
                preflight = [f for f in artifacts if (f["content_json"] or {}).get("type") == "capacity_preflight"]
                assert len(preflight) == 1 and preflight[0]["content_json"]["dispatch_state"] == "not_sent"
                task = next(t for t in await table(m.AnalysisTasks) if t["id"] == row["task_id"])
                assert task["next_retry_at"] is None and task["state"] == "failed"
            else:
                expected = ["C3", "Deep", "C6"] if mode in {"timing", "query_failure"} else ["C3", "C6"]
                assert [c["stage"] for c in calls if c["run_id"] == str(run_id)] == expected
            if mode == "missing_time":
                assert frozen.scope.window_start is None and frozen.query_preparation["missing_time_alert_ids"]
                assert lakes[row["case_id"]].calls == 0
            queries = [f["content_json"] for f in artifacts if f["kind"] == "tool_response"
                       and f["content_json"].get("tool_name") == "process_activity"]
            if mode == "timing":
                assert len(queries) == 1 and queries[0]["returned_rows"] == 75
                assert queries[0]["truncated"] and len(queries[0]["overflow_rows"]) == 1
                assert str(late_before) in frozen.alerts and str(late_during) not in frozen.alerts
            if mode == "query_failure":
                assert len(queries) == 1 and queries[0]["state"] == "failed" and queries[0]["rows"] is None
            results = [r for r in await table(m.Results) if r["source_run_id"] == run_id]
            assert len(results) == 1
            row["result_id"] = results[0]["id"]
            save(out/(mode+"-readback.json"), {"run": await cases.read_run(tenant, row["case_id"], run_id),
                "result": await cases.read_result(tenant, row["case_id"], results[0]["id"]),
                "input": await cases.read_artifact(tenant, row["case_id"], run_id, run["input_artifact_id"])})
            result["checks"].append(mode+"_saved_and_read")
        assert not dispatcher.active and not dispatcher.receipts
        assert await redis.scard(dispatcher.queues.key("running")) == 0
        result["checks"].append("capacity_frees_slot_next_case_completes")
        result["state"] = "passed"
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        if dispatcher:
            for _, future in dispatcher.active.values():
                future.cancel()
            if dispatcher.active:
                await asyncio.gather(*(future for _, future in dispatcher.active.values()), return_exceptions=True)
            dispatcher._collect()
            await dispatcher._flush_receipts()
        save(out/"calls.json", calls)
        result["substitute_model_calls"] = len(calls)
        save(out/"result.json", result)
        save(out/"snapshot.json", await snapshot())
        await redis.aclose()
        await engine.dispose()
        await admin.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    environment(config)
    asyncio.run(main(args, config))
