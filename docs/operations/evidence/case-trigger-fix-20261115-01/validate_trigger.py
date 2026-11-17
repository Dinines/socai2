"""Actual A/I/Case executors and PG/Redis; synthetic replies, direct inputs (not Kafka)."""
import argparse
import asyncio
import hashlib
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
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_store import F
    from app.socai2.case_contracts import AssociationRequest, CaseCreate
    from app.socai2.case_service import CaseService
    from redis.asyncio import Redis
    from sqlalchemy import event, insert, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from test_socai2_baseline_evidence import original

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    seed_fixture.HERE = HERE
    await seed_fixture.main(SimpleNamespace(batch=args.batch + "-sources", seed_only=True), config)
    seed = json.loads((HERE / (args.batch + "-sources") / "result.json").read_text())
    tenant, aids = UUID(seed["tenant_id"]), list(map(UUID, seed["alert_ids"]))
    actor = Actor(user_id=seed["actor_id"], name="Synthetic trigger verification")
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev"
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"]),
        hide_parameters=True, connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    sql_errors = []

    @event.listens_for(engine.sync_engine, "handle_error")
    def retain_sql_error(context):
        original_error = context.original_exception
        sql_errors.append({"type": type(original_error).__name__, "sqlstate": getattr(original_error, "sqlstate", None),
            "message": str(original_error)})
        save(out / "sql-errors.json", sql_errors)
    cases, tasks = CaseService(sessions), AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    handlers = executors({k: config[k] for k in ("investigation_policy_file", "incident", "case")}, tasks)
    calls, incident_calls, gates, entered = [], [], {}, {}
    iid = uuid4()
    incident_fixture.TENANT = tenant
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor.user_id, "incident_id": iid,
              "real_model_calls": 0, "checks": [], "tasks": [], "capacity_for_this_test": 2}

    async def case_hook(claim, context):
        if claim.case_id in gates:
            entered[claim.case_id].set()
            await gates[claim.case_id].wait()

    handlers["case_investigation"].gateway_factory = lambda claim: Gateway(cases, tenant, claim, "normal", calls, case_hook)
    handlers["case_investigation"].lake_factory = lambda claim: Lake()

    class IncidentGateway(incident_fixture.Gateway):
        async def complete(self, body, timeout):
            async with cases.transaction(tenant, readonly=True) as store:
                row = await store.one(select(m.Incidents.__table__).where(m.Incidents.id == iid))
                running = (await store.db.execute(select(m.AnalysisTasks.id).where(m.AnalysisTasks.tenant_id == tenant,
                    m.AnalysisTasks.subject_id == iid, m.AnalysisTasks.state == "running"))).scalar_one()
                assert row and running
            reply = await super().complete(body, timeout)
            incident_calls.append({"request": body, "response": reply})
            return reply

    handlers["incident_diagnosis"].gateway_factory = lambda: IncidentGateway(handlers["incident_diagnosis"].service, iid)

    class AlertGateway:
        provider, model = "synthetic", "synthetic-late-A"

        async def configure(self, *_):
            return True

        async def measure(self, body, stage):
            return await synthetic_measure(body, stage)

        async def complete(self, body, timeout):
            async with cases.transaction(tenant, readonly=True) as store:
                request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                    F.c.alert_id == aids[0], F.c.kind == "model_request")))).scalar_one()
            evidence = [key for key, row in request["source_map"].items() if row["ref"]["role"] == "observation"]
            answer = {"verdict": "needs_review", "confidence": .3, "rationale": "Synthetic late first triage.",
                      "evidence_ids": evidence[:1], "recommendations": []}
            reply = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}],
                     "usage": {"prompt_tokens": 100, "completion_tokens": 60, "total_tokens": 160}}
            calls.append({"stage": "A", "request": body, "response": reply})
            return reply

    handlers["alert_triage"].gateway_factory, handlers["alert_triage"].query = AlertGateway, empty_query
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    policy = DispatchPolicy(**{**config["dispatch"], "max_running_tasks": 2,
        "receipt_directory": str(Path(config["dispatch"]["receipt_directory"]) / str(tenant))})
    dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), AnalysisQueues(redis, policy.namespace, tenant), policy, handlers)

    async def create(title, *, event=False):
        created = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title=title,
            **({"incident_ids": [iid]} if event else {"alert_ids": aids[:1]})), actor=actor)
        return created.primary_case_id, created.allocations[0].initial_task.task_id

    async def read(pair, subject="case"):
        value = await tasks.read_task(tenant, subject, *pair)
        return value

    async def drain(target=None):
        async with asyncio.timeout(config["check_timeout_seconds"]):
            while True:
                await dispatcher.tick()
                if target:
                    value = await read(target)
                    if value["status"] in {"completed", "failed", "skipped"}:
                        assert value["status"] == "completed", value
                        return value
                else:
                    async with tasks.transaction(tenant, readonly=True) as store:
                        count = (await store.db.execute(text("SELECT count(*) FROM socai2.analysis_tasks WHERE tenant_id=:tenant AND state IN ('accepted','waiting','running')"), {"tenant": tenant})).scalar_one()
                    if not count:
                        return
                await asyncio.sleep(config["check_interval_seconds"])

    async def submit(cid, *, source="user", key=None):
        return await tasks.submit(tenant, kind="case_investigation", subject_id=cid, intent="check", source=source,
            operation_key=key or uuid4(), submitted_by=actor.user_id if source == "user" else None)

    async def due(subject):
        async with tasks.transaction(tenant) as store:
            now = await store.now()
            await store.db.execute(update(m.AnalysisSubjectState).where(m.AnalysisSubjectState.tenant_id == tenant,
                m.AnalysisSubjectState.subject_type == subject).values(next_check_at=now-timedelta(seconds=1)))
        return now

    async def scan_cases():
        stats = await handlers["case_investigation"].check_updates(tenant, await due("case"))
        result.setdefault("scan_receipts", []).append(stats)
        return stats

    async def link(aid):
        async with cases.transaction(tenant) as store:
            await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant, incident_id=iid,
                alert_id=aid, membership_source="fusion", correlation_basis={"reason": "explicit direct fixture"},
                basis_version="synthetic.trigger", source_operation_id=uuid4()))

    async def snapshot():
        models = (m.Alerts, m.AlertMaterials, m.AlertObjects, m.AlertAssessments, m.Incidents, m.IncidentAlerts,
            m.IncidentDiagnoses, m.Cases, m.CaseAlerts, m.CaseIncidents, m.AnalysisTasks, m.AnalysisAttempts,
            m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps, m.Artifacts, m.Results, m.ResultMembers)
        async with cases.transaction(tenant, readonly=True) as store:
            return {model.__tablename__: [dict(row) for row in (await store.db.execute(select(model.__table__)
                .where(model.tenant_id == tenant).order_by(*model.__table__.primary_key.columns))).mappings()]
                for model in models}

    try:
        with patch.object(baseline_enrichment_sources, "query", empty_query):
            await dispatcher.start()
            qa = await create("A runs while independent checks wait")
            gates[qa[0]], entered[qa[0]] = asyncio.Event(), asyncio.Event()
            await dispatcher.tick()
            await asyncio.wait_for(entered[qa[0]].wait(), config["check_timeout_seconds"])
            key = uuid4()
            second = await submit(qa[0], key=key)
            assert await submit(qa[0], key=key) == second
            extra = [await submit(qa[0]) for _ in range(9)]
            qb = await create("B uses second slot")
            await drain(qb)
            assert (await read(qa))["status"] == "running"
            assert len({r["task_id"] for r in [second, *extra]}) == 10
            result["checks"].append("N2_ten_busy_A_requests_do_not_block_B_or_merge_distinct_keys")
            revision = (await cases.read_case(tenant, qa[0]))["case"].scope_revision
            await cases.associate(tenant, qa[0], AssociationRequest(operation_key=uuid4(),
                expected_scope_revision=revision, alert_ids=aids[1:]), actor=actor)
            gates[qa[0]].set()
            await drain()
            first, updated = await read(qa), await read((qa[0], second["task_id"]))
            assert first["status"] == updated["status"] == "completed"
            old = await cases.read_context(tenant, qa[0], first["latest_run_id"])
            new = await cases.read_context(tenant, qa[0], updated["latest_run_id"])
            assert set(old.alerts) == {str(aids[0])} and set(new.alerts) == set(map(str, aids))
            for task in extra:
                skipped = await read((qa[0], task["task_id"]))
                assert skipped["status"] == "skipped" and skipped["reason_code"] == "no_changes" and not skipped["attempts"]
            result["checks"].append("queued_updates_recheck_latest_members_old_frozen_input_stays_one_and_covered_requests_skip")
            result.update(queue_case_id=qa[0], queue_first_task=qa[1], queue_update_task=second["task_id"],
                          queue_duplicate_tasks=[r["task_id"] for r in extra], second_slot_case_id=qb[0])
            save(out / "queue-snapshot.json", await snapshot())

            async with cases.transaction(tenant) as store:
                await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=tenant,
                    source_namespace="case-initial-fixture", source_incident_id=str(iid), title="Synthetic trigger event"))
            await link(aids[0])
            await tasks.submit(tenant, kind="incident_diagnosis", subject_id=iid, intent="initial", source="ingress", operation_key=uuid4())
            await drain()
            historical = await create("Historical event Case", event=True)
            active = await create("Active event Case", event=True)
            standalone = await create("Standalone alert Case")
            await drain()
            before = await snapshot()
            save(out / "before-updates-snapshot.json", before)
            await tasks.submit(tenant, kind="alert_triage", subject_id=aids[0], intent="initial", source="ingress", operation_key=uuid4())
            await drain()
            stats = await scan_cases()
            assert stats["submitted"] == stats["allocations"] == 0, stats
            await link(aids[1])
            stats = await scan_cases()
            assert stats["submitted"] == stats["allocations"] == 0, stats
            result["checks"].append("late_initial_A_and_new_event_member_do_not_bypass_I_or_start_case")
            await due("incident")
            await drain()
            stats = await scan_cases()
            assert stats["submitted"] == stats["allocations"] == 1, stats
            await drain()
            for pair in (historical, standalone):
                context = await cases.read_context(tenant, pair[0], (await read(pair))["latest_run_id"])
                assert set(context.alerts) == {str(aids[0])}
            fresh = await snapshot()
            new_case_runs = [r for r in fresh["runs"] if r["kind"] == "baseline" and r["id"] not in {x["id"] for x in before["runs"]}]
            assert len(new_case_runs) == 1 and new_case_runs[0]["case_id"] == active[0]
            result["checks"].append("completed_new_I_updates_only_active_whole_event_case_and_single_alert_scope_stays_fixed")
            auto, manual = await submit(historical[0], source="periodic"), await submit(historical[0])
            await drain()
            assert (await read((historical[0], auto["task_id"])))["status"] == "skipped"
            assert (await read((historical[0], manual["task_id"])))["status"] == "completed"
            result["checks"].append("independent_auto_and_manual_tasks_keep_different_applicable_I_scopes")
            result.update(historical_case_id=historical[0], active_case_id=active[0], standalone_case_id=standalone[0],
                auto_task_id=auto["task_id"], manual_task_id=manual["task_id"])

            third, mid = uuid4(), uuid4()
            async with cases.transaction(tenant) as store:
                now = await store.now()
                await store.db.execute(insert(m.Alerts).values(id=third, tenant_id=tenant,
                    source_namespace="case-initial-fixture", source_identity_key=str(third), title="Synthetic continuation alert",
                    event_time=now, event_time_source="source"))
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=third, revision=1,
                    raw_text="Synthetic continuation observation", raw_json=original("trigger.test.invalid"),
                    detection={}, source_scope={}, retention={}, material_state="complete"))
                await store.db.execute(update(m.Alerts).where(m.Alerts.id == third).values(latest_material_id=mid))
            await link(third)
            assert (await scan_cases())["allocations"] == 0
            await due("incident")
            await drain()
            stats = await scan_cases()
            assert stats["allocations"] == 1
            await drain()
            final = await snapshot()
            event = next(r for r in final["incidents"] if r["id"] == iid)
            successor = next(r for r in final["cases"] if r["id"] == event["active_case_id"])
            assert successor["previous_case_id"] == active[0]
            assert {r["alert_id"] for r in final["case_alerts"] if r["case_id"] == successor["id"]} == {third}
            assert any(r["case_id"] == successor["id"] and r["state"] == "completed" for r in final["runs"])
            assert not any(r["state"] == "merged" for r in final["analysis_tasks"])
            result.update(successor_case_id=successor["id"], state="passed")
            result["checks"].append("capacity_continuation_waits_for_valid_I_then_routes_only_new_member_and_runs_initial")
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        for gate in gates.values():
            gate.set()
        if dispatcher.active:
            await asyncio.gather(*(f for _, f in dispatcher.active.values()), return_exceptions=True)
            dispatcher._collect()
            await dispatcher._flush_receipts()
        saved = await snapshot()
        result["tasks"] = [await tasks.read_task(tenant, row["subject_type"], row["subject_id"], row["id"]) for row in saved["analysis_tasks"]]
        result["substitute_model_responses"] = len(calls) + len(incident_calls)
        save(out / "result.json", result)
        save(out / "calls.json", calls)
        save(out / "incident-calls.json", incident_calls)
        save(out / "snapshot.json", saved)
        paths = ["analysis_dispatcher", "analysis_dispatch_redis", "analysis_dispatch_store", "analysis_case_executor",
                 "case_update_inputs", "case_update_scanner"]
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
