"""F3: read ended retries, retained failures and unknown through public HTTP."""
import json
import traceback
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.models import socai2 as m
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.baseline_service import BaselineService
from app.socai2.run_records import RunRecordLimits
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.run_directory import RunDirectoryBackend
from investigation_http.adapters.run_records import RunRecordBackend
from investigation_http.adapters.services import CaseBackend
from investigation_http.dependencies import (
    analysis_task_service,
    case_service,
    run_directory_service,
    run_record_service,
)
from investigation_http.main import app
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_socai2_case_update_http_pg import snapshot
from test_socai2_incident_case_scope_http_pg import (
    source_hashes,  # noqa: F401 -- explicit read-only runner entry
)

TABLES = (m.Cases, m.CaseAlerts, m.AnalysisTasks, m.AnalysisAttempts,
          m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps, m.Artifacts,
          m.Results, m.ResultMembers, m.CaseAssessments, m.CaseAssessmentSources,
          m.Activities, m.ActivityTargets)
BASE = "/api/v1/socai2"


def instant(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


async def run_checks(engine, source_dir, config):
    source = json.loads((source_dir / "result.json").read_text())
    original = json.loads((source_dir / "snapshot.json").read_text())
    assert source["state"] == "passed" and source["real_model_calls"] == 0
    assert engine.url.database == "v12_upgrade_dev"
    latest = {t["task_id"]: t for t in source["tasks"]}
    waiting = {t["task_id"]: t for t in source["tasks"] if t["status"] == "accepted"}
    assert len(latest) == 4 and len(waiting) == 2
    tenant, actor = UUID(source["tenant_id"]), UUID(source["actor_id"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    policy = AnalysisTaskPolicy(**json.loads(Path(config["lifecycle_policy_file"]).read_text()))
    limits = RunRecordLimits(**json.loads(Path(config["http_limits_file"]).read_text()))
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    result = {"state": "running", "source": str(source_dir), "tenant_id": str(tenant),
              "calls": [], "checks": [], "core_clock_offsets_seconds": source["clock_offsets_seconds"],
              "source_model_substitutes": source["substitute_model_responses"],
              "source_transport_faults": source["substituted_transport_failures"],
              "new_model_calls": 0, "new_execution_calls": 0, "writes": 0}
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("SHOW default_transaction_read_only"))).scalar_one() == "on"
        saved, result["before"] = await snapshot(service, tenant, TABLES)
        assert {k: len(v) for k, v in saved.items()} == {k: len(v) for k, v in original.items()}
        assert len(saved["analysis_tasks"]) == 4 and len(saved["analysis_attempts"]) == len(saved["runs"]) == 6
        artifacts = {str(a["id"]): a for a in saved["artifacts"]}
        original_artifacts = {a["id"]: a for a in original["artifacts"]}
        assert all(a["content_json"] == original_artifacts[key]["content_json"]
                   and a["sha256"] == original_artifacts[key]["sha256"]
                   for key, a in artifacts.items())
        for name in ("connect-first-snapshot.json", "pool-first-snapshot.json"):
            first = json.loads((source_dir / name).read_text())
            assert all(original_artifacts[a["id"]] == a for a in first["artifacts"])
        app.state.business_context = BusinessContext(tenant, actor, "F3 ended retries readback")
        app.dependency_overrides.update({
            case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy),
            run_directory_service: lambda: RunDirectoryBackend(sessions, limits=limits),
            run_record_service: lambda: RunRecordBackend(sessions, limits=limits),
        })
        public_tasks, run_states, model_steps = {}, {}, {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path, **params):
                call = {"method": "GET", "path": path, "params": params}
                result["calls"].append(call)
                response = await client.get(path, params=params)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == 200, call
                return call["body"]

            for tid, expected in latest.items():
                cid = expected["subject_id"]
                case = await get(f"{BASE}/cases/{cid}")
                assert case["member_count"] == 1
                page = await get(f"{BASE}/cases/{cid}/analysis-tasks")
                assert page["total"] == len(page["items"]) == 1
                task = await get(page["items"][0]["status_url"])
                public_tasks[tid] = task
                for field in ("task_id", "subject_id", "status", "reason_code", "retry_count", "latest_run_id"):
                    assert task[field] == expected[field]
                assert task["next_retry_at"] is None
                assert len(task["attempts"]) == len(expected["attempts"])
                assert [a["attempt_no"] for a in task["attempts"]] == list(range(1, len(task["attempts"]) + 1))
                for attempt, original_attempt in zip(task["attempts"], expected["attempts"], strict=True):
                    for field in ("run_id", "local_state", "outcome", "retryable", "error_code", "error_detail"):
                        assert attempt[field] == original_attempt[field]
                    assert attempt["local_state"] == "ended" and attempt["local_ended_at"]
                    view = await get(attempt["run_url"])
                    rid, run = attempt["run_id"], view["run"]
                    assert run["id"] == rid and run["case_id"] == cid and run["state"] == attempt["outcome"]
                    if run["state"] == "unknown":
                        assert run["ended_at"] is None and attempt["retryable"] is False
                    else:
                        assert run["ended_at"]
                    run_states[rid] = run["state"]
                    steps = await get(view["steps_url"], limit=100)
                    assert steps["next_cursor"] is None
                    models = [s for s in steps["items"] if s["kind"] == "model"]
                    rows = {str(s["id"]): s for s in saved["run_steps"] if str(s["run_id"]) == rid and s["kind"] == "model"}
                    assert {s["id"] for s in models} == set(rows)
                    directory = await get(view["artifacts_url"], limit=100)
                    assert directory["next_cursor"] is None
                    items = {a["id"]: a for a in directory["items"]}
                    model_steps[rid] = []
                    for step in models:
                        assert step["state"] == rows[step["id"]]["state"]
                        contents = {}
                        for key in ("input_artifact_id", "output_artifact_id"):
                            aid = str(rows[step["id"]][key])
                            content = await get(items[aid]["content_url"])
                            assert content["artifact"]["id"] == aid
                            assert content["artifact"]["sha256"] == artifacts[aid]["sha256"]
                            assert content["content_json"] == artifacts[aid]["content_json"]
                            contents[key] = content["content_json"]["payload"]
                        stage = contents["input_artifact_id"]["case_boundary"].get("stage", "C3")
                        if step["state"] in {"failed", "unknown"}:
                            assert contents["output_artifact_id"]["transport_error"]
                        else:
                            assert contents["output_artifact_id"]["raw"]
                        model_steps[rid].append({"state": step["state"], "stage": stage, "step_id": step["id"]})
                assert len(task["results"]) == len(expected["results"])
                for ref in task["results"]:
                    final = await get(ref["url"])
                    assert final["result"]["id"] == ref["id"]
                    assert final["result"]["source_run_id"] == ref["source_run_id"]
                    assert run_states[ref["source_run_id"]] == "completed"
                if tid in waiting:
                    first = waiting[tid]
                    assert first["status"] == "accepted" and first["reason_code"] == "retry_scheduled"
                    assert (instant(first["next_retry_at"]) - instant(first["attempts"][0]["failed_at"])).total_seconds() == 60
                    assert len(task["attempts"]) == 2 and task["retry_count"] == 1
                    assert len({a["run_id"] for a in task["attempts"]}) == 2
                    assert instant(task["attempts"][1]["started_at"]) >= instant(first["next_retry_at"])
                    assert task["attempts"][0]["outcome"] == "failed"

            connected = next(t for t in public_tasks.values() if t["status"] == "completed" and t["retry_count"] == 1)
            assert [a["outcome"] for a in connected["attempts"]] == ["failed", "completed"]
            pool = next(t for t in public_tasks.values() if t["reason_code"] == "retry_exhausted")
            for attempt in pool["attempts"]:
                assert attempt["outcome"] == "failed"
                assert {(s["stage"], s["state"]) for s in model_steps[attempt["run_id"]]} == {("C3", "completed"), ("C6", "failed")}
            unknown = next(t for t in public_tasks.values() if t["reason_code"] == "call_timeout")
            assert unknown["status"] == "failed" and unknown["retry_count"] == 0 and len(unknown["attempts"]) == 1
            assert unknown["results"] == [] and unknown["attempts"][0]["outcome"] == "unknown"
            survivor = next(t for t in public_tasks.values() if t["status"] == "completed" and t["retry_count"] == 0)
            assert instant(survivor["started_at"]) >= instant(unknown["ended_at"])
            assert len(survivor["results"]) == 1
        _, result["after"] = await snapshot(service, tenant, TABLES)
        assert result["before"] == result["after"]
        result.update(state="passed", run_states=run_states, model_steps=model_steps)
        result["checks"] = ["ConnectTimeout_same_task_failed_then_completed_one_retry",
            "C6_PoolTimeout_exhausted_one_retry_retains_both_C3_outputs",
            "ReadTimeout_preserves_unknown_no_retry_next_case_completed",
            "frozen60_second_retry_schedule_and_first_failure_artifacts_preserved",
            "GET_only_no_auth_15_table_snapshots_unchanged"]
    except Exception as exc:  # noqa: BLE001 -- record failed reads without replaying tasks
        last = traceback.extract_tb(exc.__traceback__)[-1]
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc),
                      failure_location={"file": last.filename, "line": last.lineno})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context
    result["http_requests"] = len(result["calls"])
    return result
