"""F1 only: real isolated PG/Redis, actual I/Case executors, synthetic model replies."""
import argparse
import asyncio
import json
import sys
import traceback
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "services/api"), str(ROOT / "services/api/tests"),
               str(HERE.parent / "case-initial-20261115-01")]
import validate as initial_fixture
import test_socai2_incident_boundary_pg as incident_fixture
import controlled
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
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_store import digest
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from redis.asyncio import Redis
    from sqlalchemy import insert, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from test_socai2_baseline_evidence import original

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    initial_fixture.HERE = HERE
    await initial_fixture.main(SimpleNamespace(batch=args.batch + "-sources", seed_only=True), config)
    seed = json.loads((HERE / (args.batch + "-sources") / "result.json").read_text())
    tenant = UUID(seed["tenant_id"])
    actor = Actor(user_id=seed["actor_id"], name="Synthetic incident scope verification")
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev"
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"],
        database=cfg["processing_database"]), hide_parameters=True,
        connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases = CaseService(sessions)
    tasks = AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    handlers = executors({key: config[key] for key in ("investigation_policy_file", "incident", "case")}, tasks)
    iid, calls, incident_gateways = uuid4(), [], []
    incident_fixture.TENANT = tenant

    def incident_gateway():
        gateway = incident_fixture.Gateway(handlers["incident_diagnosis"].service, iid)
        incident_gateways.append(gateway)
        return gateway

    async def during_case_model(claim, context):
        async with cases.transaction(tenant, readonly=True) as store:
            assert len((await cases.read_case(tenant, claim.case_id))["case"].model_dump()) > 0
            saved = await store.one(select(m.AnalysisTasks.__table__).where(m.AnalysisTasks.tenant_id == tenant,
                m.AnalysisTasks.subject_id == claim.case_id))
            assert saved["state"] == "running"
            assert len(context.alerts) == 3
            assert len(context.incidents[str(iid)].diagnosis_scope["case_covered_alert_ids"]) == 1
        result["checks"].append("case_and_running_task_readable_before_model_reply")

    handlers["incident_diagnosis"].gateway_factory = incident_gateway
    handlers["case_investigation"].gateway_factory = lambda claim: Gateway(cases, tenant, claim, "normal", calls, during_case_model)
    handlers["case_investigation"].lake_factory = lambda claim: Lake()
    original_answer = controlled.answer_for

    def scoped_answer(prepared, context):
        answer = original_answer(prepared, context)
        prior = next(sid for sid, row in prepared["source_map"].items()
                     if row["ref"].get("source_path") == f"$.incidents.{iid}.diagnosis.diagnosis.conclusion")
        answer["questions"][0]["evidence_ids"].append(prior)
        return answer
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    policy = DispatchPolicy(**{**config["dispatch"], "receipt_directory": str(Path(config["dispatch"]["receipt_directory"]) / str(tenant))})
    dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), AnalysisQueues(redis, policy.namespace, tenant), policy, handlers)
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor.user_id, "incident_id": iid,
              "real_model_calls": 0, "database": cfg["processing_database"], "checks": [], "tasks": []}

    async def new_alert():
        aid, mid = uuid4(), uuid4()
        async with cases.transaction(tenant) as store:
            now = await store.now()
            await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant,
                source_namespace="case-initial-fixture", source_identity_key=str(aid), title="Synthetic scope observation",
                description="Explicit local integration fixture, not Kafka acceptance.", event_time=now, event_time_source="source"))
            await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid, revision=1,
                raw_text="Synthetic observed process.", raw_json=original("scope-fix.test.invalid"),
                detection={}, source_scope={}, retention={}, material_state="complete"))
            await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
        return aid

    async def drain():
        async with asyncio.timeout(config["check_timeout_seconds"]):
            while True:
                await dispatcher.tick()
                async with tasks.transaction(tenant, readonly=True) as store:
                    count = (await store.db.execute(text("SELECT count(*) FROM socai2.analysis_tasks WHERE tenant_id=:tenant AND state IN ('accepted','waiting','running')"), {"tenant": tenant})).scalar_one()
                if not count:
                    return
                await asyncio.sleep(config["check_interval_seconds"])

    async def diagnosis():
        receipt = await tasks.submit(tenant, kind="incident_diagnosis", subject_id=iid, intent="rerun",
            source="user", operation_key=uuid4(), submitted_by=actor.user_id)
        await drain()
        detail = await tasks.read_task(tenant, "incident", iid, receipt["task_id"])
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
        aids = [UUID(a) for a in seed["alert_ids"]] + [await new_alert()]
        async with cases.transaction(tenant) as store:
            now = await store.now()
            await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=tenant, source_namespace="case-initial-fixture",
                source_incident_id=str(iid), title="Three event members, one selected for diagnosis"))
            for index, aid in enumerate(aids):
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant, incident_id=iid,
                    alert_id=aid, linked_at=now + timedelta(microseconds=index), membership_source="fusion",
                    correlation_basis={"reason": "explicit synthetic fixture"}, basis_version="synthetic.scope-fix",
                    source_operation_id=uuid4()))
        with patch.object(baseline_enrichment_sources, "query", empty_query), patch.object(controlled, "answer_for", scoped_answer):
            await dispatcher.start()
            first = await diagnosis()
            result["first_incident_run_id"] = first["latest_run_id"]
            created = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="Case preserves actual I scope",
                incident_ids=[iid]), actor=actor)
            cid, tid = created.primary_case_id, created.allocations[0].initial_task.task_id
            result.update(case_id=cid, case_task_id=tid)
            pending = await tasks.read_task(tenant, "case", cid, tid)
            assert pending["status"] == "accepted" and pending["latest_run_id"] is None
            save(out / "case-accepted.json", pending)
            await drain()
            detail = await tasks.read_task(tenant, "case", cid, tid)
            result["tasks"].append(detail)
            assert detail["status"] == "completed", detail
            frozen = await cases.read_context(tenant, cid, detail["latest_run_id"])
            scope = frozen.incidents[str(iid)].diagnosis_scope
            assert len(frozen.alerts) == len(aids) == 3
            assert scope["source_run_id"] == str(first["latest_run_id"])
            assert scope["input_selection"]["total_member_count"] == 3
            assert scope["input_selection"]["selected_alert_ids"] == [str(aids[-1])]
            assert scope["analysis_coverage"]["covered_alert_ids"] == [str(aids[-1])]
            saved = await snapshot()
            requests = [a["content_json"]["payload"] for a in saved["artifacts"]
                        if a["run_id"] == detail["latest_run_id"] and a["kind"] == "model_request"]
            assert len(requests) == 2
            for request in requests:
                entries = [s for s in request["source_map"].values()
                           if s["ref"].get("source_path") == f"$.incidents.{iid}.diagnosis.diagnosis.conclusion"]
                assert entries and all(s["alert_ids"] == [str(aids[-1])] for s in entries)
                assert all(s["original_scope"]["alert_ids"] == [str(aids[-1])] for s in entries)
            result.update(case_run_id=detail["latest_run_id"], case_result_id=detail["results"][0]["id"],
                          diagnosis_scope=scope, case_input_sha256=digest(frozen.model_dump(mode="json")))
            save(out / "case-context.json", frozen)
            result["checks"].append("I_selects_one_Case_keeps_three_C3_C6_associate_only_one")
            later = await new_alert()
            async with cases.transaction(tenant) as store:
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant, incident_id=iid,
                    alert_id=later, membership_source="fusion", correlation_basis={"reason": "later synthetic member"},
                    basis_version="synthetic.scope-fix", source_operation_id=uuid4()))
            second = await diagnosis()
            result["latest_incident_run_id"] = second["latest_run_id"]
            after = await cases.read_context(tenant, cid, detail["latest_run_id"])
            assert digest(after.model_dump(mode="json")) == result["case_input_sha256"]
            result["checks"].append("later_event_member_and_new_I_do_not_rewrite_old_case_input")
            result.update(state="passed", source_alert_ids=aids, later_alert_id=later)
            save(out / "case-run-readback.json", await cases.read_run(tenant, cid, detail["latest_run_id"]))
            save(out / "case-result-readback.json", await cases.read_result(tenant, cid, detail["results"][0]["id"]))
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
        result["substitute_model_calls"] = len(calls) + sum(g.calls for g in incident_gateways)
        save(out / "result.json", result)
        save(out / "case-calls.json", calls)
        save(out / "incident-calls.json", [{"requests": g.requests, "responses": g.responses} for g in incident_gateways])
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
