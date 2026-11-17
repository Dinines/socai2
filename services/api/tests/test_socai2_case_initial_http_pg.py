"""Step 6: real Case admission/readback; the separate core runner owns execution."""
import hashlib
import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.models import socai2 as m
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.baseline_service import BaselineService
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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

TABLES = (m.Alerts, m.AlertMaterials, m.AlertObjects, m.Cases, m.CaseAlerts,
          m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState,
          m.Runs, m.RunMembers, m.RunSteps, m.Artifacts, m.Results, m.ResultMembers,
          m.CaseAssessments, m.CaseAssessmentSources, m.CaseAssessmentMembers,
          m.Activities, m.ActivityTargets)


async def snapshot(service, tenant):
    rows, hashes = {}, {}
    async with service.transaction(tenant, readonly=True) as store:
        for model in TABLES:
            table = model.__table__
            values = [dict(row) for row in (await store.db.execute(select(table)
                .where(table.c.tenant_id == tenant).order_by(*table.primary_key.columns))).mappings()]
            rows[table.name] = values
            hashes[table.name] = {"count": len(values), "sha256": hashlib.sha256(
                json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()}
    return rows, hashes


async def run_checks(engine, record, only=None):
    if only == {"case_initial_http_boundaries"}:
        return await boundary_readback(engine, record)
    if only == {"case_initial_http_readback"}:
        return await readback(engine, record)
    phase = "case_initial_http_create"
    assert only == {phase}
    sample = json.loads(Path(os.environ["SOCAI2_CASE_INITIAL_HTTP_SAMPLE_FILE"]).read_text())
    source = json.loads(Path(sample["source_evidence"]).read_text())
    tenant, actor = UUID(source["tenant_id"]), UUID(source["actor_id"])
    assert engine.url.database == source["database"] == "v12_upgrade_dev"
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    saved_overrides = dict(app.dependency_overrides)
    old_context = getattr(app.state, "business_context", None)
    env = {key: os.environ.get(key) for key in (
        "SOCAI2_CASE_ALLOCATION_CONFIG_FILE", "SOCAI2_ANALYSIS_TASKS_CONFIG_FILE")}
    calls, receipts, before, after = [], {}, None, None
    try:
        os.environ["SOCAI2_CASE_ALLOCATION_CONFIG_FILE"] = sample["allocation_policy_file"]
        os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = sample["task_policy_file"]
        policy = AnalysisTaskPolicy.load()
        app.state.business_context = BusinessContext(tenant, actor, "Case initial HTTP fixture")
        app.dependency_overrides.update({case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy)})
        saved, before = await snapshot(service, tenant)
        assert not any(saved[k] for k in ("cases", "analysis_tasks", "analysis_attempts", "runs"))
        assert {str(r["id"]) for r in saved["alerts"]} == set(source["alert_ids"])
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def request(method, path, status=200, **kwargs):
                call = {"method": method, "path": path, "request": kwargs}
                calls.append(call)
                response = await client.request(method, path, **kwargs)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == status, call
                return call["body"]

            created = await request("POST", "/api/v1/socai2/cases", 201, json=sample["create_request"])
            receipts["create"] = created
            assert len(created["allocations"]) == 1 and created["excluded_alert_ids"] == []
            allocated = created["allocations"][0]
            cid, task = created["primary_case_id"], allocated["initial_task"]
            assert allocated["case_id"] == cid == created["receiving_case_id"]
            assert set(allocated["added_alert_ids"]) == set(source["alert_ids"])
            assert task["subject_id"] == cid and task["status"] == "accepted"
            assert "pending_run_id" not in created
            detail = await request("GET", allocated["case_url"])
            assert detail["case"]["id"] == cid and detail["member_count"] == len(source["alert_ids"])
            task_detail = await request("GET", task["status_url"])
            assert task_detail["status"] == "accepted" and task_detail["intent"] == "initial"
            assert task_detail["latest_run_id"] is None and not task_detail["attempts"] and not task_detail["results"]
            tasks = await request("GET", f"/api/v1/socai2/cases/{cid}/analysis-tasks")
            assert tasks["total"] == 1 and tasks["items"][0]["task_id"] == task["task_id"]
        saved, after = await snapshot(service, tenant)
        assert len(saved["cases"]) == len(saved["analysis_tasks"]) == 1
        assert not saved["analysis_attempts"] and not saved["runs"] and not saved["results"]
        stored = saved["analysis_tasks"][0]
        assert str(stored["id"]) == task["task_id"] and str(stored["submitted_by"]) == str(actor)
        assert stored["intent"] == "initial" and stored["state"] == "accepted"
        assert all(before[k] == after[k] for k in ("alerts", "alert_materials", "alert_objects"))
        record(phase, True, {"sample": sample, "source": source, "calls": calls, "receipts": receipts,
            "before": before, "after": after, "saved": saved, "model_calls": 0, "execution_calls": 0})
    except Exception as exc:  # noqa: BLE001 -- preserve failure without retrying a write
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record(phase, False, {"sample": sample, "source": source, "calls": calls, "receipts": receipts,
            "before": before, "after": after, "error_type": type(exc).__name__, "error": str(exc),
            "failure_location": {"file": location.filename, "line": location.lineno}})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved_overrides)
        app.state.business_context = old_context
        for key, value in env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


async def boundary_readback(engine, record):
    """Read ended core cases; never replay tasks or rerun model/queries."""
    root = Path(os.environ["SOCAI2_CASE_INITIAL_BOUNDARY_EVIDENCE"])
    source = json.loads((root / "result.json").read_text())
    assert source["state"] == "passed" and source["new_model_calls"] == 0
    assert engine.url.database == "v12_upgrade_dev"
    tenant = UUID(source["tenant_id"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    calls, before, after = [], None, None
    try:
        saved, before = await snapshot(service, tenant)
        actor = saved["analysis_tasks"][0]["submitted_by"]
        app.state.business_context = BusinessContext(tenant, actor, "Ended core sample readback")
        app.dependency_overrides.update({case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions)})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path):
                call = {"method": "GET", "path": path}
                calls.append(call)
                response = await client.get(path)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == 200, call
                return call["body"]

            for name, ids in source["cases"].items():
                expected = json.loads((root / f"{name}-readback.json").read_text())
                cid, rid, tid = ids["case_id"], ids["run_id"], ids["task_id"]
                base = f"/api/v1/socai2/cases/{cid}"
                task = await get(base + f"/analysis-tasks/{tid}")
                for field in ("task_id", "subject_id", "intent", "status", "reason_code", "latest_run_id"):
                    assert task[field] == expected["task"][field], (name, field)
                assert len(task["attempts"]) == 1 and task["attempts"][0]["run_id"] == rid
                detail = await get(task["attempts"][0]["run_url"])
                for field in ("run", "result_ids", "current_member_count", "input_member_count", "members"):
                    assert detail[field] == expected["run"][field], (name, field)
                assert len(task["results"]) == 1 and task["results"][0]["id"] == ids["result_id"]
                result = await get(task["results"][0]["url"])
                for field in ("result", "run", "members", "member_count", "delivery"):
                    assert result[field] == expected["result"][field], (name, field)
                if name == "capacity":
                    assert task["status"] == detail["run"]["state"] == "failed"
                    assert task["reason_code"] == detail["run"]["stop_reason"] == "capacity_exceeded"
                    assert not ids["model_stages"]
                    original = await get(base + f"/runs/{rid}/artifacts/" + detail["run"]["input_artifact_id"])
                    for field in ("content_json", "content_text", "availability"):
                        assert original[field] == expected["input"][field], field
                    for field, value in expected["input"]["artifact"].items():
                        actual = original["artifact"][field]
                        if field == "captured_at":
                            assert datetime.fromisoformat(actual) == datetime.fromisoformat(value)
                        else:
                            assert actual == value, field
                if name == "timing":
                    view = await get(base)
                    assert view["member_count"] == detail["current_member_count"] == 3
                    assert detail["input_member_count"] == len(detail["members"]) == 2
        _, after = await snapshot(service, tenant)
        assert before == after
        record("case_initial_http_boundaries", True, {"source": str(root), "cases": source["cases"],
            "calls": calls, "before": before, "after": after, "new_model_calls": 0, "database_writes": 0})
    except Exception as exc:  # noqa: BLE001 -- preserve failure without execution
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record("case_initial_http_boundaries", False, {"source": str(root), "calls": calls,
            "before": before, "after": after, "error_type": type(exc).__name__, "error": str(exc),
            "failure_location": {"file": location.filename, "line": location.lineno}})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context


async def readback(engine, record):
    """Follow the actual task and Run links, then compare persisted business data."""
    sample_path = Path(os.environ["SOCAI2_CASE_INITIAL_HTTP_SAMPLE_FILE"])
    sample = json.loads(sample_path.read_text())
    source = json.loads(Path(sample["source_evidence"]).read_text())
    created = json.loads((sample_path.parent / "create-pg-01.json").read_text())["checks"][0]["detail"]["receipts"]["create"]
    consumed = json.loads((sample_path.parent / "consume-01.json").read_text())
    assert consumed["state"] == "drained" and consumed["real_model_calls"] == 0
    tenant, actor = UUID(source["tenant_id"]), UUID(source["actor_id"])
    assert engine.url.database == source["database"] == "v12_upgrade_dev"
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    env = {key: os.environ.get(key) for key in ("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE", "SOCAI2_RUN_RECORDS_CONFIG_FILE")}
    calls, before, after, saved = [], None, None, {}
    try:
        os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = sample["task_policy_file"]
        os.environ["SOCAI2_RUN_RECORDS_CONFIG_FILE"] = sample["run_records_policy_file"]
        app.state.business_context = BusinessContext(tenant, actor, "Case initial readback")
        app.dependency_overrides.update({case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions),
            run_record_service: lambda: RunRecordBackend(sessions),
            run_directory_service: lambda: RunDirectoryBackend(sessions)})
        saved, before = await snapshot(service, tenant)
        assert len(saved["runs"]) == len(saved["analysis_attempts"]) == len(saved["analysis_tasks"]) == 1
        run, attempt, stored_task = saved["runs"][0], saved["analysis_attempts"][0], saved["analysis_tasks"][0]
        cid, rid, tid = str(run["case_id"]), str(run["id"]), str(stored_task["id"])
        assert run["state"] == "completed" and attempt["outcome"] == "completed" and attempt["local_state"] == "ended"
        assert str(attempt["run_id"]) == rid and str(attempt["task_id"]) == tid
        assert str(stored_task["subject_id"]) == cid == created["primary_case_id"]
        assert stored_task["intent"] == "initial" and stored_task["state"] == "completed"
        assert {str(v["alert_id"]) for v in saved["run_members"]} == set(source["alert_ids"])
        assert run["comparison_result_id"] is None and attempt["previous_run_id"] is None
        assert attempt["input_artifact_id"] == run["input_artifact_id"] and attempt["policy_artifact_id"]
        assert saved["results"] and all(v["source_run_id"] == run["id"] for v in saved["results"])
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path, **params):
                call = {"method": "GET", "path": path, "params": params}
                calls.append(call)
                response = await client.get(path, params=params)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == 200, call
                return call["body"]

            task = await get(created["allocations"][0]["initial_task"]["status_url"])
            assert task["task_id"] == tid and task["status"] == "completed" and task["intent"] == "initial"
            assert task["latest_run_id"] == rid and len(task["attempts"]) == 1
            assert task["attempts"][0]["outcome"] == "completed"
            task_page = await get(f"/api/v1/socai2/cases/{cid}/analysis-tasks")
            assert task_page["total"] == 1 and task_page["items"][0] == task
            detail = await get(task["attempts"][0]["run_url"])
            assert detail["run"]["id"] == rid and detail["run"]["case_id"] == cid
            assert detail["run"]["state"] == run["state"] and detail["input_member_count"] == len(source["alert_ids"])
            assert {v["alert_id"] for v in detail["members"]} == set(source["alert_ids"])
            expected_results = {str(v["id"]): v for v in saved["results"]}
            assert set(detail["result_ids"]) == set(expected_results) == {v["id"] for v in task["results"]}
            for reference in task["results"]:
                result = await get(reference["url"])
                actual, stored = result["result"], expected_results[reference["id"]]
                assert actual["source_run_id"] == result["run"]["id"] == rid
                for field in ("title", "purpose", "conclusion", "conclusion_state", "validation_state",
                              "findings", "questions", "recommendations", "case_impact", "delivery_state", "change_kind"):
                    assert actual[field] == stored[field], field
                assert actual["comparison_result_id"] is None
            directory = await get("/api/v1/socai2/analysis-runs", subject_type="case", subject_id=cid, intent="initial")
            assert directory["total"] == 1 and directory["items"][0]["run_id"] == rid
            assert directory["items"][0]["task_id"] == tid
            assert directory["items"][0]["detail_url"] == task["attempts"][0]["run_url"]
            view = await get(f"/api/v1/socai2/cases/{cid}")
            assert view["member_count"] == len(source["alert_ids"])
            assessment = view["current_assessment"]
            stored_assessment = saved["case_assessments"][0]
            assert assessment["value"]["id"] == str(saved["cases"][0]["current_assessment_id"])
            assert assessment["value"]["id"] == str(stored_assessment["id"])
            for field in ("conclusion", "origin", "validity", "revision", "scope_revision", "actor"):
                assert assessment["value"][field] == stored_assessment[field], field
            assert {v["result_id"] for v in assessment["sources"]} == set(expected_results)
            assert {v["alert_id"] for v in assessment["members"]} == set(source["alert_ids"])
            assert assessment["covers_current_members"] is True
            assert assessment["input_freshness"]["state"] == "current"

            async def all_pages(path):
                items, cursor = [], None
                while True:
                    page = await get(path, limit=20, **({"cursor": cursor} if cursor else {}))
                    assert page["run_id"] == rid and page["subject_id"] == cid
                    items.extend(page["items"])
                    cursor = page["next_cursor"]
                    if cursor is None:
                        assert len(items) == page["total"]
                        return items

            steps = await all_pages(detail["steps_url"])
            artifacts = await all_pages(detail["artifacts_url"])
            assert {v["id"] for v in steps} == {str(v["id"]) for v in saved["run_steps"]}
            actual_artifacts = {str(v["id"]): v for v in saved["artifacts"] if v["run_id"] == run["id"]}
            assert {v["id"] for v in artifacts} == set(actual_artifacts)
            final_step = next(v for v in steps if v["stage_code"] == "C6")
            assert await get(detail["steps_url"] + "/" + final_step["id"]) == final_step
            selected = {str(run["input_artifact_id"]), str(attempt["policy_artifact_id"])}
            for kind in ("model_request", "model_response", "tool_response", "report_json", "report_markdown"):
                choices = [v for v in artifacts if v["kind"] == kind]
                if choices:
                    selected.add(choices[0]["id"])
            for row in artifacts:
                if row["id"] not in selected:
                    continue
                original = await get(row["content_url"])
                stored = actual_artifacts[row["id"]]
                assert original["artifact"]["id"] == row["id"] and original["artifact"]["run_id"] == rid
                assert original["content_json"] == stored["content_json"]
                assert original["content_text"] == stored["content_text"]
                assert original["artifact"]["sha256"] == stored["sha256"] == row["sha256"]
            assert {str(v["run_id"]) for v in consumed["calls"]} == {rid}
        _, after = await snapshot(service, tenant)
        assert before == after, "Task/Run/result/record GETs must not change saved data"
        record("case_initial_http_readback", True, {"source": source, "calls": calls,
            "case_id": cid, "task_id": tid, "run_id": rid, "before": before, "after": after,
            "saved": saved, "read_artifact_ids": sorted(selected), "real_model_calls": 0,
            "substitute_model_calls_in_separate_consumer": consumed["substitute_model_calls"], "database_writes": 0})
    except Exception as exc:  # noqa: BLE001 -- reads never retry execution
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record("case_initial_http_readback", False, {"source": source, "calls": calls, "before": before,
            "after": after, "saved": saved, "error_type": type(exc).__name__, "error": str(exc),
            "failure_location": {"file": location.filename, "line": location.lineno}})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context
        for key, value in env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
