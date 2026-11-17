"""Read the ended F4 retry guard fixture through HTTP; no task executions."""
import json
import traceback
from pathlib import Path
from uuid import UUID

from app.models import socai2 as m
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.baseline_service import BaselineService
from app.socai2.run_records import RunRecordLimits
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.run_records import RunRecordBackend
from investigation_http.adapters.services import CaseBackend
from investigation_http.dependencies import (
    analysis_task_service,
    case_service,
    run_record_service,
)
from investigation_http.main import app
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_socai2_case_retry_http_pg import instant
from test_socai2_case_update_http_pg import snapshot
from test_socai2_incident_case_scope_http_pg import (
    source_hashes,  # noqa: F401 -- explicit read-only runner entry
)

TABLES = (m.Alerts, m.Cases, m.CaseAlerts, m.AnalysisTasks, m.AnalysisAttempts,
          m.AnalysisSubjectState, m.Runs, m.RunMembers, m.Artifacts, m.Results)
BASE = "/api/v1/socai2"


async def run_checks(engine, source_dir, config):
    source_path = source_dir.parent / "test-retry-guard-01.json"
    source = json.loads(source_path.read_text())
    main_source = json.loads((source_dir / "result.json").read_text())
    assert source["state"] == "passed" and source["real_model_calls"] == 0
    assert engine.url.database == "v12_upgrade_dev"
    tenant, actor = UUID(source["tenant_id"]), UUID(main_source["actor_id"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    policy = AnalysisTaskPolicy(**json.loads(Path(config["lifecycle_policy_file"]).read_text()))
    limits = RunRecordLimits(**json.loads(Path(config["http_limits_file"]).read_text()))
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    result = {"state": "running", "source": str(source_path), "tenant_id": str(tenant),
              "calls": [], "checks": [], "executor": "core_controlled_executor_not_Case_model_chain",
              "new_model_calls": 0, "new_execution_calls": 0, "writes": 0}
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("SHOW default_transaction_read_only"))).scalar_one() == "on"
        saved, result["before"] = await snapshot(service, tenant, TABLES)
        assert len(saved["analysis_tasks"]) == len(saved["analysis_attempts"]) == len(saved["runs"]) == 3
        assert len(saved["results"]) == 0 and len(saved["artifacts"]) == 3
        assert all(t["merged_into_task_id"] is None for t in saved["analysis_tasks"])
        app.state.business_context = BusinessContext(tenant, actor, "F4 retry guard read-only context")
        app.dependency_overrides.update({
            case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy),
            run_record_service: lambda: RunRecordBackend(sessions, limits=limits),
        })
        public = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path, **params):
                call = {"method": "GET", "path": path, "params": params}
                result["calls"].append(call)
                response = await client.get(path, params=params)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == 200, call
                return call["body"]

            for cid in {source[k]["subject_id"] for k in ("first", "independent", "other")}:
                page = await get(f"{BASE}/cases/{cid}/analysis-tasks")
                expected_ids = {source[k]["task_id"] for k in ("first", "independent", "other")
                                if source[k]["subject_id"] == cid}
                assert {t["task_id"] for t in page["items"]} == expected_ids
                for item in page["items"]:
                    public[item["task_id"]] = await get(item["status_url"])
            for name in ("first", "independent", "other"):
                expected = source[name]
                task = public[expected["task_id"]]
                for field in ("task_id", "subject_id", "status", "reason_code", "retry_count", "latest_run_id", "next_retry_at"):
                    assert task[field] == expected[field]
                assert task["results"] == []
                assert len(task["attempts"]) == len(expected["attempts"])
                for attempt, original in zip(task["attempts"], expected["attempts"], strict=True):
                    for field in ("run_id", "local_state", "outcome", "retryable", "error_code", "error_detail"):
                        assert attempt[field] == original[field]
                    view = await get(attempt["run_url"])
                    run = view["run"]
                    assert run["id"] == attempt["run_id"] and run["state"] == attempt["outcome"]
                    assert run["ended_at"] and attempt["local_ended_at"]
                    call = next(c for c in source["calls"] if c["run_id"] == run["id"])
                    content = await get(f"{BASE}/cases/{task['subject_id']}/runs/{run['id']}/artifacts/{call['artifact_id']}")
                    row = next(a for a in saved["artifacts"] if str(a["id"]) == call["artifact_id"])
                    assert content["artifact"]["sha256"] == row["sha256"]
                    assert content["content_json"] == row["content_json"] == call["input"]
            waiting = source["first_waiting"]
            first = public[source["first"]["task_id"]]
            assert waiting["status"] == "accepted" and waiting["reason_code"] == "retry_scheduled"
            assert (instant(waiting["next_retry_at"]) - instant(waiting["attempts"][0]["failed_at"])).total_seconds() == 60
            assert first["status"] == "failed" and first["reason_code"] == "retry_exhausted"
            assert first["retry_count"] == 1 and len(first["attempts"]) == 2
            assert instant(first["attempts"][1]["started_at"]) == instant(waiting["next_retry_at"])
            independent = public[source["independent"]["task_id"]]
            assert independent["status"] == "skipped" and independent["reason_code"] == "automatic_attempts_stopped"
            assert independent["attempts"] == [] and independent["latest_run_id"] is None
            other = public[source["other"]["task_id"]]
            assert other["status"] == "completed" and instant(other["ended_at"]) < instant(first["ended_at"])
        _, result["after"] = await snapshot(service, tenant, TABLES)
        assert result["before"] == result["after"]
        result.update(state="passed", checks=["same_task_frozen60_one_retry_exhausted_both_failed_Runs_readable",
            "new_same_subject_request_independent_skipped_stopped_without_Run_other_subject_completes",
            "controlled_executor_inputs_retained_no_fake_Result", "GET_only_no_auth_10_tables_unchanged"])
    except Exception as exc:  # noqa: BLE001 -- retain failures without new execution
        last = traceback.extract_tb(exc.__traceback__)[-1]
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc),
                      failure_location={"file": last.filename, "line": last.lineno})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context
    result["http_requests"] = len(result["calls"])
    return result
