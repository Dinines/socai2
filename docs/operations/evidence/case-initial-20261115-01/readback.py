"""Read-only completion of pg-02 verification after its snapshot-driver error."""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from validate import HERE, environment, save


async def run(args, config):
    from app.models import socai2 as m
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_store import digest
    from app.socai2.case_execution_input import initial_input_versions
    from app.socai2.case_service import CaseService
    from redis.asyncio import Redis
    from sqlalchemy import select
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    cfg = json.loads(Path(config["database_profile"]).read_text())
    engine = create_async_engine(URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"]),
        hide_parameters=True, connect_args={"sslmode":config["sslmode"], "options":"-c role="+cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, tasks = CaseService(sessions), AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    models = (m.Alerts, m.AlertMaterials, m.AlertObjects, m.Cases, m.CaseAlerts, m.AnalysisTasks,
        m.AnalysisAttempts, m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps, m.Artifacts,
        m.Results, m.ResultMembers, m.CaseAssessments, m.CaseAssessmentSources, m.CaseAssessmentMembers)
    result = {"state":"running", "tenant_id":str(args.tenant), "execution_source":"pg-02",
        "mode":"read_only_no_task_replay", "real_model_calls":0, "new_model_calls":0, "checks":[], "cases":{}}
    async def snapshot():
        async with cases.transaction(args.tenant, readonly=True) as store:
            data = {model.__tablename__: [dict(r) for r in (await store.db.execute(select(model.__table__)
                .where(model.__table__.c.tenant_id == args.tenant).order_by(*model.__table__.primary_key.columns))).mappings()]
                for model in models}
        return json.loads(json.dumps(data, default=str))
    try:
        data = await snapshot()
        save(out/"snapshot.json", data)
        assert len(data["cases"]) == len(data["analysis_tasks"]) == len(data["runs"]) == 5
        assert len(data["analysis_attempts"]) == 5
        all_calls = []
        for case in data["cases"]:
            mode, cid = case["title"].removeprefix("Case initial "), UUID(case["id"])
            task = next(t for t in data["analysis_tasks"] if t["subject_id"] == str(cid))
            attempts = [a for a in data["analysis_attempts"] if a["task_id"] == task["id"]]
            assert len(attempts) == 1
            attempt = attempts[0]
            run = next(r for r in data["runs"] if r["id"] == attempt["run_id"])
            rid = UUID(run["id"])
            assert task["submitted_at"] <= run["started_at"]
            assert attempt["local_state"] == "ended" and attempt["local_ended_at"]
            assert attempt["input_artifact_id"] == run["input_artifact_id"] and attempt["policy_artifact_id"]
            assert task["state"] == run["state"] == ("failed" if mode == "capacity" else "completed")
            artifacts = [f for f in data["artifacts"] if f["run_id"] == str(rid)]
            for artifact in artifacts:
                if artifact["content_json"] is not None:
                    assert digest(artifact["content_json"]) == artifact["sha256"]
            async with cases.transaction(args.tenant, readonly=True) as store:
                context = await store.read_context(cid, rid)
            assert attempt["input_digest"] == task["observed_input_digest"] == digest(initial_input_versions(context))
            assert context.query_preparation["effective_max_rows_per_query"] == 75
            policy = next(f for f in artifacts if f["id"] == attempt["policy_artifact_id"])["content_json"]
            assert policy["case_execution"] == config["case"]
            members = [member for member in data["run_members"] if member["run_id"] == str(rid)]
            assert {member["alert_id"] for member in members} == set(context.alerts)
            requests = sorted([f for f in artifacts if f["kind"] == "model_request"], key=lambda f:f["captured_at"])
            steps = [s for s in data["run_steps"] if s["run_id"] == str(rid)]
            stages = [r["content_json"]["payload"]["case_boundary"].get("stage", "C3") for r in requests]
            if mode == "capacity":
                assert run["stop_reason"] == "capacity_exceeded" and stages == [] and task["next_retry_at"] is None
                preflight = [f for f in artifacts if (f["content_json"] or {}).get("type") == "capacity_preflight"]
                assert len(preflight) == 1 and preflight[0]["content_json"]["dispatch_state"] == "not_sent"
                assert preflight[0]["content_json"]["token_measurement"]["context_fits"] is False
                assert preflight[0]["content_json"]["body"]["response_format"]
            else:
                assert stages == (["C3", "Deep", "C6"] if mode in {"timing", "query_failure"} else ["C3", "C6"])
            if mode == "missing_time":
                assert context.scope.window_start is None and len(context.query_preparation["missing_time_alert_ids"]) == 1
                assert not [s for s in steps if s["stage_code"] == "C4.query"]
            queries = [f["content_json"] for f in artifacts if f["kind"] == "tool_response"
                       and f["content_json"].get("tool_name") == "process_activity"]
            if mode == "timing":
                assert len(queries) == 1 and queries[0]["returned_rows"] == 75
                assert queries[0]["truncated"] and len(queries[0]["overflow_rows"]) == 1
                assert queries[0]["actual_args"]["limit"] == queries[0]["actual_args"]["row_limit"] == 75
                assert len(context.alerts) == 2 and len([ca for ca in data["case_alerts"] if ca["case_id"] == str(cid)]) == 3
                assert run["scope_revision"] == 2 and case["scope_revision"] == 3
            if mode == "query_failure":
                assert len(queries) == 1 and queries[0]["state"] == "failed" and queries[0]["rows"] is None
            results = [r for r in data["results"] if r["source_run_id"] == str(rid)]
            assert len(results) == 1
            result_id = UUID(results[0]["id"])
            saved = {"task": await tasks.read_task(args.tenant, "case", cid, UUID(task["id"])),
                "run": await cases.read_run(args.tenant, cid, rid), "result": await cases.read_result(args.tenant, cid, result_id),
                "input": await cases.read_artifact(args.tenant, cid, rid, UUID(run["input_artifact_id"]))}
            save(out/(mode+"-readback.json"), saved)
            result["cases"][mode] = {"case_id":str(cid), "task_id":task["id"], "run_id":str(rid), "result_id":str(result_id), "model_stages":stages}
            result["checks"].append(mode+"_actual_freeze_pipeline_saved_readback")
            all_calls.extend(requests)
        assert len(all_calls) == 10
        failed = next(r for r in data["runs"] if r["stop_reason"] == "capacity_exceeded")
        later = next(r for r in data["runs"] if r["case_id"] == result["cases"]["after_capacity"]["case_id"])
        assert later["started_at"] >= failed["ended_at"] and later["state"] == "completed"
        result["checks"].append("capacity_releases_N1_next_case_completes")
        after = await snapshot()
        assert digest(data) == digest(after)
        result["checks"].append("task_run_result_input_readers_have_no_writes")
        redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
        assert await redis.scard(config["dispatch"]["namespace"]+":"+str(args.tenant)+":running") == 0
        await redis.aclose()
        result.update(state="passed", historical_substitute_model_calls=len(all_calls), snapshot_sha256=digest(data))
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        save(out/"result.json", result)
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tenant", type=UUID, required=True)
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    environment(config)
    asyncio.run(run(args, config))
