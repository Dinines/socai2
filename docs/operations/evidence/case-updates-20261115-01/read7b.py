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
        models = (m.Incidents, m.IncidentAlerts, m.IncidentDiagnoses, m.AlertAssessments, m.Cases, m.CaseAlerts, m.Alerts, m.AlertMaterials, m.AlertObjects, m.AnalysisTasks, m.AnalysisAttempts,
            m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps, m.Artifacts, m.Results, m.ResultMembers,
            m.Tasks, m.TaskRevisions, m.CaseAssessments, m.CaseAssessmentSources, m.CaseAssessmentMembers)
        async with cases.transaction(tenant, readonly=True) as store:
            value = {model.__tablename__: [dict(row) for row in (await store.db.execute(select(model.__table__)
                .where(model.tenant_id == tenant).order_by(*model.__table__.primary_key.columns))).mappings()]
                for model in models}
        return json.loads(json.dumps(value, default=str))

    try:
        before = await snapshot()
        saved, histories = {}, {}
        for task in before["analysis_tasks"]:
            cid = UUID(task["subject_id"])
            detail = await tasks.read_task(tenant, "case", cid, UUID(task["id"]))
            assert detail["status"] == "completed"
            detail["run_readback"] = await cases.read_run(tenant, cid, detail["latest_run_id"])
            for ref in detail["results"]:
                rv = await cases.read_result(tenant, cid, ref["id"])
                assert rv["result"].comparison_context == rv["run"].comparison_context
                saved[str(ref["id"])] = rv
            saved[task["id"]] = detail
        for case in before["cases"]:
            cid = UUID(case["id"])
            history = await cases.read_history(tenant, cid)
            for entry in history.items:
                assert entry.run.comparison_context is not None
                if entry.result:
                    assert entry.result.comparison_context == entry.run.comparison_context
            histories[str(cid)] = history
        after = await snapshot()
        assert digest(before) == digest(after)
        assert before == json.loads((HERE / args.source / "snapshot.json").read_text())
        assert all(row["local_state"] == "ended" for row in before["analysis_attempts"])
        assert len(before["runs"]) == 12 and len(before["analysis_attempts"]) == 8
        assert all(row["state"] == "completed" for row in before["runs"])
        result.update(state="passed", case_ids=[c["id"] for c in before["cases"]], read_only_tables=len(before), snapshot_sha256=digest(before),
            source_substitute_model_calls=original["substitute_model_calls"], real_model_calls=0,
            case_runs=8, synthetic_upstream_runs=4, completed_runs=sum(r["state"] == "completed" for r in before["runs"]))
        result["checks"].append("ended_records_stable_comparison_and_reads_do_not_write")
        save(out / "readback.json", saved)
        save(out / "history.json", histories)
        save(out / "snapshot.json", before)
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
