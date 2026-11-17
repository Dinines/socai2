"""Read F4 pg-01's completed paths and retained failure; never replay this batch."""
import json
import traceback
from datetime import datetime
from pathlib import Path
from uuid import UUID

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
    TABLES,
    source_hashes,  # noqa: F401 -- explicit read-only runner entry
)

BASE = "/api/v1/socai2"


def instant(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


async def run_checks(engine, source_dir, config):
    source = json.loads((source_dir / "result.json").read_text())
    original = json.loads((source_dir / "snapshot.json").read_text())
    assert source["state"] == "failed" and len(source["checks"]) == 4
    assert source["real_model_calls"] == 0 and engine.url.database == "v12_upgrade_dev"
    tenant, actor = UUID(source["tenant_id"]), UUID(source["actor_id"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    policy = AnalysisTaskPolicy(**json.loads(Path(config["lifecycle_policy_file"]).read_text()))
    limits = RunRecordLimits(**json.loads(Path(config["http_limits_file"]).read_text()))
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    result = {"state": "running", "scope": "partial_F4_ended_pg01_readback",
              "full_F4_accepted": False, "core_batch_state": source["state"],
              "source": str(source_dir), "tenant_id": str(tenant), "calls": [], "checks": [],
              "source_model_substitutes": source["substitute_model_responses"],
              "new_model_calls": 0, "new_execution_calls": 0, "writes": 0,
              "not_proven": ["historical_Case_manual_check_success", "whole_F4_acceptance",
                             "HTTP_POST_idempotent_replay", "Kafka_chain", "real_model", "21_TCP"]}
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("SHOW default_transaction_read_only"))).scalar_one() == "on"
        saved, result["before"] = await snapshot(service, tenant, TABLES)
        assert {k: len(v) for k, v in saved.items()} == {k: len(v) for k, v in original.items()}
        assert len(saved["analysis_tasks"]) == 21 and len(saved["runs"]) == 11
        artifacts = {str(a["id"]): a for a in saved["artifacts"]}
        prior_artifacts = {a["id"]: a for a in original["artifacts"]}
        assert all(a["content_json"] == prior_artifacts[key]["content_json"]
                   and a["sha256"] == prior_artifacts[key]["sha256"] for key, a in artifacts.items())
        queue_tasks = [t for t in saved["analysis_tasks"] if str(t["subject_id"]) == source["queue_case_id"]]
        assert len(queue_tasks) == len({t["operation_key"] for t in queue_tasks}) == 11
        assert all(t["merged_into_task_id"] is None for t in saved["analysis_tasks"])
        app.state.business_context = BusinessContext(tenant, actor, "F4 partial ended batch readback")
        app.dependency_overrides.update({
            case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy),
            run_directory_service: lambda: RunDirectoryBackend(sessions, limits=limits),
            run_record_service: lambda: RunRecordBackend(sessions, limits=limits),
        })
        public, contexts, runs = {}, {}, {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path, **params):
                call = {"method": "GET", "path": path, "params": params}
                result["calls"].append(call)
                response = await client.get(path, params=params)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == 200, call
                return call["body"]

            for row in saved["cases"]:
                cid = str(row["id"])
                case = await get(f"{BASE}/cases/{cid}")
                members = {str(x["alert_id"]) for x in saved["case_alerts"] if str(x["case_id"]) == cid}
                assert case["case"]["id"] == cid and case["member_count"] == len(members)
                expected = {t["task_id"]: t for t in source["tasks"] if t["subject_id"] == cid}
                page = await get(f"{BASE}/cases/{cid}/analysis-tasks", limit=50)
                assert page["total"] == len(page["items"]) == len(expected)
                assert {t["task_id"] for t in page["items"]} == set(expected)
                for item in page["items"]:
                    task = await get(item["status_url"])
                    tid = task["task_id"]
                    public[tid] = task
                    for field in ("task_id", "subject_id", "intent", "source", "status", "reason_code", "latest_run_id"):
                        assert task[field] == expected[tid][field]
                    assert len(task["attempts"]) == len(expected[tid]["attempts"])
                    assert len(task["results"]) == len(expected[tid]["results"])
                    if task["status"] == "skipped":
                        assert task["reason_code"] == "no_changes" and task["latest_run_id"] is None
                        assert task["attempts"] == task["results"] == []
                    for attempt in task["attempts"]:
                        view = await get(attempt["run_url"])
                        rid, run = attempt["run_id"], view["run"]
                        assert run["id"] == rid and run["case_id"] == cid
                        assert run["state"] == attempt["outcome"]
                        runs[rid] = run
                        directory = await get(view["artifacts_url"], limit=100)
                        assert directory["next_cursor"] is None
                        context_rows = [a for a in artifacts.values() if str(a["run_id"]) == rid
                                        and isinstance(a["content_json"], dict)
                                        and "alerts" in a["content_json"] and "incidents" in a["content_json"]]
                        assert len(context_rows) == 1
                        aid = str(context_rows[0]["id"])
                        metadata = next(a for a in directory["items"] if a["id"] == aid)
                        content = await get(metadata["content_url"])
                        assert content["artifact"]["id"] == aid
                        assert content["artifact"]["sha256"] == artifacts[aid]["sha256"]
                        assert content["content_json"] == artifacts[aid]["content_json"]
                        contexts[rid] = content["content_json"]
                    for ref in task["results"]:
                        final = await get(ref["url"])
                        assert final["result"]["id"] == ref["id"]
                        assert final["result"]["source_run_id"] == task["latest_run_id"]

            assert all(public[tid]["status"] == "skipped" for tid in source["queue_duplicate_tasks"])
            first, updated = (public[source[k]] for k in ("queue_first_task", "queue_update_task"))
            old_scope = set(contexts[first["latest_run_id"]]["alerts"])
            new_scope = set(contexts[updated["latest_run_id"]]["alerts"])
            assert len(old_scope) == 1 and len(new_scope) == 2 and old_scope < new_scope
            second_slot = next(t for t in public.values() if t["subject_id"] == source["second_slot_case_id"])
            assert instant(first["started_at"]) <= instant(second_slot["started_at"])
            assert instant(second_slot["ended_at"]) < instant(first["ended_at"])
            assert instant(updated["started_at"]) >= instant(first["ended_at"])
            result["checks"].append("independent_keys_9_no_changes_without_Run_old1_new2_busy_A_overlaps_B")
            result["core_replay_evidence"] = {
                "source_check": source["checks"][0], "task_count": len(queue_tasks),
                "meaning": "Core PG/Redis driver replayed the same key; this HTTP pass performs GET only"}

            active = original["incidents"][0]["active_case_id"]
            auto_updates = [t for t in public.values() if t["source"] == "periodic" and t["status"] == "completed"]
            assert len(auto_updates) == 1 and auto_updates[0]["subject_id"] == active
            changed = auto_updates[0]
            assert set(contexts[changed["latest_run_id"]]["alerts"]) == new_scope
            iid = source["incident_id"]
            diagnosis_run = contexts[changed["latest_run_id"]]["incidents"][iid]["diagnosis_scope"]["source_run_id"]
            incident_task = next(t for t in source["tasks"] if t["latest_run_id"] == diagnosis_run)
            assert incident_task["subject_id"] == iid and incident_task["status"] == "completed"
            assert instant(changed["started_at"]) >= instant(incident_task["ended_at"])
            before = json.loads((source_dir / "before-updates-snapshot.json").read_text())
            old_runs = {r["id"] for r in before["runs"]}
            new_successful_cases = [r for r in runs.values() if r["id"] not in old_runs and r["state"] == "completed"]
            assert [r["id"] for r in new_successful_cases] == [changed["latest_run_id"]]
            standalone = next(c for c in saved["cases"] if c["title"] == "Standalone alert Case")
            standalone_tasks = [t for t in public.values() if t["subject_id"] == str(standalone["id"])]
            assert len(standalone_tasks) == 1
            assert set(contexts[standalone_tasks[0]["latest_run_id"]]["alerts"]) == old_scope
            assert [s["submitted"] for s in source["scan_receipts"]] == [0, 0, 1]
            result["checks"].append("saved_scan_receipts_0_0_1_only_active_whole_event_case_updates_after_I")

            failed = [t for t in public.values() if t["status"] == "failed"]
            assert len(failed) == 1
            manual = failed[0]
            assert manual["source"] == "user" and manual["intent"] == "check"
            assert manual["results"] == [] and len(manual["attempts"]) == 1
            assert runs[manual["latest_run_id"]]["state"] == "unknown"
            assert runs[manual["latest_run_id"]]["ended_at"] is None
            auto = next(t for t in public.values() if t["subject_id"] == manual["subject_id"] and t["source"] == "periodic")
            assert auto["status"] == "skipped" and auto["task_id"] != manual["task_id"]
            result["retained_failure"] = {"task_id": manual["task_id"], "run_id": manual["latest_run_id"],
                                          "task_status": manual["status"], "run_state": "unknown"}
            result["checks"].append("manual_check_distinct_from_auto_but_failed_unknown_retained_not_accepted")
        _, result["after"] = await snapshot(service, tenant, TABLES)
        assert result["before"] == result["after"]
        result["checks"].append("GET_only_no_auth_19_table_snapshots_unchanged")
        result["state"] = "passed"
    except Exception as exc:  # noqa: BLE001 -- preserve failed reads without replaying tasks
        last = traceback.extract_tb(exc.__traceback__)[-1]
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc),
                      failure_location={"file": last.filename, "line": last.lineno})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context
    result["http_requests"] = len(result["calls"])
    return result
