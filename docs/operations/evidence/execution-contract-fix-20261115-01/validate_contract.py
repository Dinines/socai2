"""One current A/I/Case chain on isolated PG/Redis, with explicit model/query substitutes."""
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
import test_socai2_incident_boundary_pg as incident_fixture
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
    from app.socai2.analysis_dispatch_runtime import validate_executors
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_store import F
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from app.socai2.runtime_policy import active_policy
    from redis.asyncio import Redis
    from sqlalchemy import insert, select, text
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    seed_fixture.HERE = HERE
    await seed_fixture.main(SimpleNamespace(batch=args.batch + "-sources", seed_only=True), config)
    seed = json.loads((HERE / (args.batch + "-sources") / "result.json").read_text())
    tenant, aid, iid = UUID(seed["tenant_id"]), UUID(seed["alert_ids"][0]), uuid4()
    actor = Actor(user_id=seed["actor_id"], name="Synthetic current execution contract")
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev"
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"],
        database=cfg["processing_database"]), hide_parameters=True,
        connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, tasks = CaseService(sessions), AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    handlers = executors({k: config[k] for k in ("investigation_policy_file", "incident", "case")}, tasks)
    validate_executors(handlers)
    calls = []
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor.user_id,
              "alert_id": aid, "incident_id": iid, "tasks": [], "checks": [], "real_model_calls": 0,
              "database": {"host": cfg["host"], "port": cfg["port"], "name": cfg["processing_database"]}}

    class AlertGateway:
        provider, model = "synthetic", "synthetic-current-contract"

        async def configure(self, *_):
            return True

        async def measure(self, body, stage):
            return await synthetic_measure(body, stage)

        async def complete(self, body, timeout):
            async with cases.transaction(tenant, readonly=True) as store:
                request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                    F.c.alert_id == aid, F.c.kind == "model_request")))).scalar_one()
            assert request["alert_boundary"]["version"] == active_policy().alert_io.version
            evidence = [key for key, row in request["source_map"].items() if row["ref"]["role"] == "observation"]
            answer = {"verdict": "needs_review", "confidence": .3, "rationale": "Synthetic observation needs review.",
                      "evidence_ids": evidence[:1], "recommendations": []}
            reply = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}],
                     "usage": {"prompt_tokens": 100, "completion_tokens": 60, "total_tokens": 160}}
            calls.append({"stage": "A", "request": body, "response": reply})
            return reply

    incident_fixture.TENANT = tenant
    incident_gateway = incident_fixture.Gateway(handlers["incident_diagnosis"].service, iid)
    handlers["alert_triage"].gateway_factory, handlers["alert_triage"].query = AlertGateway, empty_query
    handlers["incident_diagnosis"].gateway_factory = lambda: incident_gateway
    # The existing timing reply proposes one actual query and one Deep step.
    handlers["case_investigation"].gateway_factory = lambda claim: Gateway(cases, tenant, claim, "timing", calls)
    handlers["case_investigation"].lake_factory = lambda claim: Lake()
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    policy = DispatchPolicy(**{**config["dispatch"],
        "receipt_directory": str(Path(config["dispatch"]["receipt_directory"]) / str(tenant))})
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

    async def finish(subject_type, subject_id, receipt):
        await drain()
        detail = await tasks.read_task(tenant, subject_type, subject_id, receipt["task_id"])
        result["tasks"].append(detail)
        assert detail["status"] == "completed", detail
        return detail

    async def snapshot():
        models = (m.Alerts, m.AlertMaterials, m.AlertObjects, m.AlertAssessments, m.Incidents, m.IncidentAlerts,
            m.IncidentDiagnoses, m.Cases, m.CaseAlerts, m.CaseIncidents, m.AnalysisTasks, m.AnalysisAttempts,
            m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps, m.Artifacts, m.Results, m.ResultMembers)
        async with cases.transaction(tenant, readonly=True) as store:
            return {model.__tablename__: [dict(row) for row in (await store.db.execute(select(model.__table__)
                .where(model.tenant_id == tenant).order_by(*model.__table__.primary_key.columns))).mappings()]
                for model in models}

    try:
        async with cases.transaction(tenant) as store:
            await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=tenant,
                source_namespace="case-initial-fixture", source_incident_id=str(iid), title="Current contract verification"))
            await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant, incident_id=iid,
                alert_id=aid, membership_source="fusion", correlation_basis={"reason": "explicit synthetic fixture"},
                basis_version="synthetic.execution-contract", source_operation_id=uuid4()))
        with patch.object(baseline_enrichment_sources, "query", empty_query):
            await dispatcher.start()
            for kind, subject_type, identity in [("alert_triage", "alert", aid), ("incident_diagnosis", "incident", iid)]:
                receipt = await tasks.submit(tenant, kind=kind, subject_id=identity, intent="initial", source="ingress", operation_key=uuid4())
                await finish(subject_type, identity, receipt)
            created = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(),
                title="Current A/I/Case and Deep contract", incident_ids=[iid]), actor=actor)
            cid, tid = created.primary_case_id, created.allocations[0].initial_task.task_id
            result.update(case_id=cid, case_task_id=tid)
            completed = await finish("case", cid, {"task_id": tid})
            result.update(case_run_id=completed["latest_run_id"], case_result_id=completed["results"][0]["id"])
            context = await cases.read_context(tenant, cid, completed["latest_run_id"])
            assert context.case_input_profile == active_policy().case_io.identity
            assert context.alerts[str(aid)].triage_usable and context.incidents[str(iid)].diagnosis_usable
            assert {c["stage"] for c in calls} == {"A", "C3", "Deep", "C6"}
            result["checks"] = ["complete_factory_and_registration", "A_then_I_then_Case_saved_current_contracts",
                "current_C3_query_Deep_C6_complete_and_read_back", "C1_current_A_I_sources_and_profile_frozen"]
            save(out / "case-context.json", context)
            save(out / "case-run-readback.json", await cases.read_run(tenant, cid, completed["latest_run_id"]))
            save(out / "case-result-readback.json", await cases.read_result(tenant, cid, result["case_result_id"]))
            result["state"] = "passed"
    except Exception:
        result.update(state="failed", traceback=traceback.format_exc())
        raise
    finally:
        if dispatcher.active:
            await asyncio.gather(*(f for _, f in dispatcher.active.values()), return_exceptions=True)
            dispatcher._collect()
            await dispatcher._flush_receipts()
        result["substitute_model_calls"] = len(calls) + incident_gateway.calls
        save(out / "result.json", result)
        save(out / "calls.json", calls)
        save(out / "incident-calls.json", {"requests": incident_gateway.requests, "responses": incident_gateway.responses})
        save(out / "snapshot.json", await snapshot())
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
