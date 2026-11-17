"""Read the already ended 7B batch; never submit or execute another task."""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from validate7a import HERE, environment, save


async def run(args, config):
    from app.models import socai2 as m
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_store import digest
    from app.socai2.case_service import CaseService
    from sqlalchemy import select
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    original = json.loads((HERE / args.source / "result.json").read_text())
    tenant = UUID(original["tenant_id"])
    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["processing_database"] == "v12_upgrade_dev"
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"]),
        hide_parameters=True, connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, tasks = CaseService(sessions), AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    result = {"state": "running", "tenant_id": tenant, "source": args.source,
        "new_model_calls": 0, "new_tasks": 0, "checks": list(original["checks"])}

    async def snapshot():
        models = (m.Incidents, m.IncidentAlerts, m.CaseIncidents, m.Activities, m.ActivityTargets, m.Cases, m.CaseAlerts, m.Alerts, m.AlertMaterials, m.AlertObjects, m.AnalysisTasks, m.AnalysisAttempts,
            m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps, m.Artifacts, m.Results, m.ResultMembers,
            m.Tasks, m.TaskRevisions, m.CaseAssessments, m.CaseAssessmentSources, m.CaseAssessmentMembers)
        async with cases.transaction(tenant, readonly=True) as store:
            value = {model.__tablename__: [dict(row) for row in (await store.db.execute(select(model.__table__)
                .where(model.tenant_id == tenant).order_by(*model.__table__.primary_key.columns))).mappings()]
                for model in models}
        return json.loads(json.dumps(value, default=str))

    try:
        before = await snapshot()
        cases_by_id = {r["id"]: r for r in before["cases"]}
        assert len(cases_by_id) == 2
        child = next(c for c in cases_by_id.values() if c["previous_case_id"] is not None)
        parent = cases_by_id[child["previous_case_id"]]
        assert child["created_by"] is None and child["continuation_root_case_id"] == parent["id"]
        assert before["incidents"][0]["active_case_id"] == child["id"]
        assert [sum(ca["case_id"]==c["id"] for ca in before["case_alerts"]) for c in (parent,child)] == [100,1]
        child_task = next(t for t in before["analysis_tasks"] if t["subject_id"]==child["id"])
        assert child_task["state"] == "accepted" and child_task["intent"] == "initial" and child_task["submitted_by"] is None
        assert not before["runs"] and not before["analysis_attempts"]
        for cid in cases_by_id:
            await cases.read_case(tenant,UUID(cid))
        after = await snapshot()
        assert before == after
        result.update(state="passed",case_ids=list(cases_by_id),snapshot_sha256=digest(before),
            real_model_calls=0,substitute_model_calls=0,read_only_tables=len(before),
            checks=["service_actor_auto_100_plus_1_successor_task_unique_receiver_and_reads"],
            scope="Only existing saved allocation read back; no consumer, no task retry, original driver failure preserved.")
        save(out/"snapshot.json",before)
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        save(out / "result.json", result)
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    environment(config)
    asyncio.run(run(args, config))
