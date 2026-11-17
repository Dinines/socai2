"""Stage7 HTTP: isolated admission and read-only reuse; never execute tasks."""
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
from app.socai2.case_story import CaseStoryService
from app.socai2.page_reader import PageReadService
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.analysis_submissions import AnalysisSubmissionBackend
from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.run_directory import RunDirectoryBackend
from investigation_http.adapters.run_records import RunRecordBackend
from investigation_http.adapters.services import CaseBackend
from investigation_http.dependencies import (
    analysis_submission_service,
    analysis_task_service,
    case_service,
    page_service,
    run_directory_service,
    run_record_service,
    story_service,
)
from investigation_http.main import app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

TABLES = (m.Cases, m.CaseAlerts, m.Alerts, m.AlertMaterials, m.AlertObjects,
          m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState, m.Runs,
          m.RunMembers, m.RunSteps, m.Artifacts, m.Results, m.ResultMembers,
          m.Tasks, m.TaskRevisions, m.CaseAssessments, m.CaseAssessmentSources,
          m.CaseAssessmentMembers)


async def snapshot(service, tenant, tables=TABLES):
    rows, hashes = {}, {}
    async with service.transaction(tenant, readonly=True) as store:
        for model in tables:
            table = model.__table__
            values = [dict(row) for row in (await store.db.execute(select(table)
                .where(table.c.tenant_id == tenant).order_by(*table.primary_key.columns))).mappings()]
            rows[table.name] = values
            hashes[table.name] = {"count": len(values), "sha256": hashlib.sha256(
                json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()}
    return rows, hashes


async def run_checks(engine, record, only=None):
    if only == {"case_update_http_periodic_readback"}:
        return await periodic_readback(engine, record)
    if only == {"case_update_http_execution_readback"}:
        return await execution_readback(engine, record)
    if only == {"case_update_http_admission"}:
        return await admission(engine, record)
    phase = "case_update_http_core_readback"
    assert only == {phase}
    root = Path(os.environ["SOCAI2_CASE_UPDATE_CORE_EVIDENCE"])
    source = json.loads((root / "result.json").read_text())
    expected = json.loads((root / "readback.json").read_text())
    assert source["state"] == "passed" and source["new_tasks"] == source["new_model_calls"] == 0
    assert engine.url.database == "v12_upgrade_dev"
    tenant, cid = UUID(source["tenant_id"]), source["case_id"]
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    calls, before, after, saved = [], None, None, {}
    try:
        saved, before = await snapshot(service, tenant)
        assert len(saved["cases"]) == 1 and str(saved["cases"][0]["id"]) == cid
        assert len(saved["runs"]) == source["case_runs"] == 5
        assert len(saved["analysis_tasks"]) == 8
        assert all(t["state"] in {"completed", "failed", "skipped"} for t in saved["analysis_tasks"])
        actor = saved["analysis_tasks"][0]["submitted_by"]
        app.state.business_context = BusinessContext(tenant, actor, "Ended Case update readback")
        app.dependency_overrides.update({case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions),
            story_service: lambda: CaseStoryService(sessions)})
        base = f"/api/v1/socai2/cases/{cid}"
        contexts, links, visited, tasks = {}, [], set(), {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path, **params):
                call = {"method": "GET", "path": path, "params": params}
                calls.append(call)
                response = await client.get(path, params=params)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == 200, call
                visited.add(path)
                return call["body"]

            cursor, items = None, []
            while True:
                page = await get(base + "/analysis-tasks", limit=3, **({"cursor": cursor} if cursor else {}))
                items.extend(page["items"])
                assert page["total"] == 8
                cursor = page["next_cursor"]
                if cursor is None:
                    break
            assert {v["task_id"] for v in items} == {str(v["id"]) for v in saved["analysis_tasks"]}
            for row in items:
                task = await get(row["status_url"])
                assert task == row
                prior = expected[task["task_id"]]
                for field in ("task_id", "subject_id", "intent", "status", "reason_code", "latest_run_id"):
                    assert task[field] == prior[field], field
                tasks[task["task_id"]] = task
                if task["status"] == "skipped":
                    assert task["reason_code"] == "no_changes"
                    assert task["latest_run_id"] is None and task["attempts"] == task["results"] == []
                    continue
                assert len(task["attempts"]) == len(task["results"]) == 1
                detail = await get(task["attempts"][0]["run_url"])
                run = detail["run"]
                assert run["id"] == task["latest_run_id"] and run["case_id"] == cid
                result = await get(task["results"][0]["url"])
                assert result["result"] == expected[result["result"]["id"]]["result"]
                assert result["run"] == run
                frozen = await get(base + f"/runs/{run['id']}/artifacts/{run['input_artifact_id']}")
                stored = next(a for a in saved["artifacts"] if str(a["id"]) == run["input_artifact_id"])
                comparison = frozen["content_json"]["comparison_context"]
                assert frozen["content_json"] == stored["content_json"]
                assert frozen["artifact"]["sha256"] == stored["sha256"]
                assert run["comparison_context"] == result["result"]["comparison_context"] == comparison
                assert run["comparison_result_id"] == result["result"]["comparison_result_id"] == comparison["comparison_result_id"]
                contexts[run["id"]] = comparison
                for value in (detail, result):
                    previous, selected = comparison["previous_run_id"], comparison["comparison_result_id"]
                    assert value["previous_run_url"] == (base + f"/runs/{previous}" if previous else None)
                    assert value["comparison_result_url"] == (base + f"/results/{selected}" if selected else None)
                    links.extend(v for v in (value["previous_run_url"], value["comparison_result_url"]) if v)
            assert set(links) <= visited, "Every returned previous-run/result URL was actually read"
            assert {v["state"] for v in contexts.values()} == {"initial", "eligible", "unavailable"}
            ended = sorted(saved["runs"], key=lambda r: (r["started_at"], r["id"]))
            for n, run in enumerate(ended):
                assert contexts[str(run["id"])]["previous_run_id"] == (str(ended[n - 1]["id"]) if n else None)
            last = contexts[str(ended[-1]["id"])]
            assert ended[-2]["state"] == "failed" and last["state"] == "unavailable"
            assert last["comparison_result_id"] is None and last["reason_code"] == "previous_conclusion_unusable"

            history = await get(base + "/history", limit=100)
            assert history["next_cursor"] is None
            for row in history["items"]:
                assert row["run"]["comparison_context"] == contexts[row["run"]["id"]]
                if row["result"]:
                    assert row["result"]["comparison_context"] == row["run"]["comparison_context"]
            story = await get(base + "/story", limit=100)
            assert story["next_cursor"] is None
            for row in story["items"]:
                if row.get("run"):
                    assert row["run"]["comparison_context"] == contexts[row["run"]["id"]]
                    for value in row["results"]:
                        assert value["comparison_context"] == contexts[value["source_run_id"]]
        _, after = await snapshot(service, tenant)
        assert before == after
        record(phase, True, {"source": str(root), "calls": calls, "case_id": cid,
            "before": before, "after": after, "comparison_by_run": contexts, "tasks": tasks,
            "source_substitute_model_calls": source["source_substitute_model_calls"],
            "new_model_calls": 0, "database_writes": 0})
    except Exception as exc:  # noqa: BLE001 -- preserve failed reads, never retry execution
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record(phase, False, {"source": str(root), "calls": calls, "before": before,
            "after": after, "error_type": type(exc).__name__, "error": str(exc),
            "failure_location": {"file": location.filename, "line": location.lineno}})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context


async def admission(engine, record):
    """Save one fresh Case and initial/check/rerun receipts; leave execution to core."""
    phase = "case_update_http_admission"
    sample = json.loads(Path(os.environ["SOCAI2_CASE_UPDATE_HTTP_SAMPLE_FILE"]).read_text())
    source = json.loads(Path(sample["source_evidence"]).read_text())
    config = json.loads(Path(sample["verification_config_file"]).read_text())
    assert source["state"] == "sources_ready_no_tasks"
    assert engine.url.database == source["database"] == "v12_upgrade_dev"
    tenant, actor = UUID(source["tenant_id"]), UUID(source["actor_id"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    env = {key: os.environ.get(key) for key in (
        "SOCAI2_CASE_ALLOCATION_CONFIG_FILE", "SOCAI2_ANALYSIS_TASKS_CONFIG_FILE")}
    calls, receipts, before, after = [], {}, None, None
    try:
        os.environ["SOCAI2_CASE_ALLOCATION_CONFIG_FILE"] = config["allocation_policy_file"]
        os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = config["lifecycle_policy_file"]
        policy = AnalysisTaskPolicy.load()
        app.state.business_context = BusinessContext(tenant, actor, "Case update HTTP fixture")
        app.dependency_overrides.update({case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy),
            analysis_submission_service: lambda: AnalysisSubmissionBackend(sessions, policy=policy)})
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
            cid = created["primary_case_id"]
            assert cid == created["receiving_case_id"] == created["allocations"][0]["case_id"]
            receipts["initial"] = created["allocations"][0]["initial_task"]
            detail = await request("GET", created["allocations"][0]["case_url"])
            assert detail["case"]["id"] == cid and detail["member_count"] == len(source["alert_ids"])
            path = f"/api/v1/socai2/cases/{cid}/investigations"
            for mode in ("check", "rerun"):
                body = {"operation_key": sample["operation_keys"][mode], "mode": mode}
                receipts[mode] = await request("POST", path, 202, json=body)
                assert await request("POST", path, 202, json=body) == receipts[mode]
                conflict = await request("POST", path, 409,
                    json={**body, "mode": "rerun" if mode == "check" else "check"})
                assert conflict["detail"]["code"] == "operation_conflict"
            assert len({receipts[k]["task_id"] for k in ("initial", "check", "rerun")}) == 3
            for intent in ("initial", "check", "rerun"):
                receipt = receipts[intent]
                assert receipt["subject_type"] == "case" and receipt["subject_id"] == cid
                assert receipt["status"] == "accepted"
                task = await request("GET", receipt["status_url"])
                assert task["intent"] == intent and task["status"] == "accepted"
                assert task["latest_run_id"] is None and task["attempts"] == task["results"] == []

            # Failed submissions must not create extra tasks or edit saved records.
            _, before_rejections = await snapshot(service, tenant)
            missing_path = f"/api/v1/socai2/cases/{sample['missing_subject_id']}/investigations"
            conflict = await request("POST", missing_path, 409,
                json={"operation_key": sample["operation_keys"]["check"], "mode": "check"})
            assert conflict["detail"]["code"] == "operation_conflict"
            missing = await request("POST", missing_path, 404,
                json={"operation_key": sample["operation_keys"]["missing"], "mode": "check"})
            assert missing["detail"]["code"] == "subject_not_found"
            body = {"operation_key": sample["operation_keys"]["invalid"], "mode": "check"}
            for key, value in (("expected_scope_revision", 1), ("tenant_id", str(tenant)),
                    ("comparison_result_id", sample["missing_subject_id"])):
                await request("POST", path, 422, json={**body, key: value})
            await request("POST", path + "?mode=check", 422, json=body)
            page = await request("GET", f"/api/v1/socai2/cases/{cid}/analysis-tasks")
            assert page["total"] == 3 and page["next_cursor"] is None
            assert {r["task_id"] for r in page["items"]} == {
                receipts[k]["task_id"] for k in ("initial", "check", "rerun")}
            for old in (f"/api/v1/socai2/cases/{cid}/baseline/prepare",
                    f"/api/v1/socai2/cases/{cid}/runs/{sample['missing_subject_id']}/start"):
                await request("POST", old, 404, json={})
        saved, after = await snapshot(service, tenant)
        assert before_rejections == after
        assert len(saved["cases"]) == 1 and len(saved["case_alerts"]) == 2
        assert len(saved["analysis_tasks"]) == 3 and len(saved["analysis_subject_state"]) == 1
        assert not any(saved[k] for k in ("analysis_attempts", "runs", "results", "artifacts"))
        for task in saved["analysis_tasks"]:
            assert str(task["id"]) == receipts[task["intent"]]["task_id"]
            assert str(task["submitted_by"]) == str(actor) and task["state"] == "accepted"
            assert task["source"] == ("case_create" if task["intent"] == "initial" else "user")
        assert all(before[k] == after[k] for k in ("alerts", "alert_materials", "alert_objects"))
        record(phase, True, {"sample": sample, "source": source, "calls": calls,
            "case_id": cid, "receipts": receipts, "before": before, "after": after,
            "before_rejections": before_rejections, "saved": saved, "model_calls": 0, "execution_calls": 0})
    except Exception as exc:  # noqa: BLE001 -- preserve actual admission, never replay with new keys
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record(phase, False, {"sample": sample, "source": source, "calls": calls, "receipts": receipts,
            "before": before, "after": after, "error_type": type(exc).__name__, "error": str(exc),
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


async def periodic_readback(engine, record):
    """Read finished 7B samples as saved; no scan-clock substitute or consumption."""
    phase = "case_update_http_periodic_readback"
    root = Path(os.environ["SOCAI2_CASE_UPDATE_PERIODIC_EVIDENCE"])
    assert engine.url.database == "v12_upgrade_dev"
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    tables = (*TABLES, m.Incidents, m.IncidentAlerts, m.IncidentDiagnoses, m.AlertAssessments)
    batches, calls = [], []
    try:
        for name in ("read-7b-03", "lifecycle-02"):
            source = json.loads((root / name / "result.json").read_text())
            expected = (json.loads((root / name / "readback.json").read_text()) if name == "read-7b-03" else {})
            assert source["state"] == "passed" and source["real_model_calls"] == 0
            tenant = UUID(source["tenant_id"])
            saved, before = await snapshot(service, tenant, tables)
            batch = {"source": str(root / name), "before": before}
            batches.append(batch)
            actor = next(t["submitted_by"] for t in saved["analysis_tasks"] if t["submitted_by"])
            app.state.business_context = BusinessContext(tenant, actor, "Ended periodic Case sample")
            app.dependency_overrides.update({case_service: lambda: CaseBackend(sessions),
                analysis_task_service: lambda: AnalysisTaskBackend(sessions),
                page_service: lambda: PageReadService(sessions)})
            saved_cases = {str(c["id"]): c for c in saved["cases"]}
            assert set(saved_cases) == set(source["case_ids"])
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
                async def get(path, source_name=name):
                    call = {"source": source_name, "method": "GET", "path": path}
                    calls.append(call)
                    response = await client.get(path)
                    call.update(status=response.status_code, body=response.json())
                    assert "authorization" not in response.request.headers
                    assert response.status_code == 200, call
                    return call["body"]

                contexts = {}
                for cid, case in saved_cases.items():
                    base = f"/api/v1/socai2/cases/{cid}"
                    detail = await get(base)
                    assert detail["case"]["handling_status"] == case["handling_status"]
                    assert detail["member_count"] == sum(str(r["case_id"]) == cid for r in saved["case_alerts"])
                    tasks = await get(base + "/analysis-tasks")
                    stored_tasks = {str(t["id"]): t for t in saved["analysis_tasks"] if str(t["subject_id"]) == cid}
                    assert tasks["next_cursor"] is None and tasks["total"] == len(stored_tasks)
                    if case["handling_status"] == "resolved":
                        assert tasks["update_state"]["eligible"] is False
                        assert tasks["update_state"]["ineligible_reason"] == "closed"
                    for row in tasks["items"]:
                        task = await get(row["status_url"])
                        assert task == row
                        stored = stored_tasks[task["task_id"]]
                        assert task["status"] == stored["state"] == "completed"
                        assert task["source"] == stored["source"]
                        if task["source"] == "periodic":
                            assert stored["submitted_by"] is None
                        run_detail = await get(task["attempts"][0]["run_url"])
                        run = run_detail["run"]
                        result_detail = await get(task["results"][0]["url"])
                        result = result_detail["result"]
                        expect_result = (expected[result["id"]] if name == "read-7b-03" else
                            json.loads((root / name / (result["id"] + "-result.json")).read_text()))
                        assert result == expect_result["result"] and result_detail["run"] == run
                        original = await get(base + f"/runs/{run['id']}/artifacts/{run['input_artifact_id']}")
                        stored_artifact = next(a for a in saved["artifacts"] if str(a["id"]) == run["input_artifact_id"])
                        assert original["content_json"] == stored_artifact["content_json"]
                        frozen = original["content_json"]["comparison_context"]
                        assert frozen == run["comparison_context"] == result["comparison_context"]
                        contexts[run["id"]] = frozen
                        expected_members = {str(m["alert_id"]) for m in saved["run_members"] if str(m["run_id"]) == run["id"]}
                        assert {m["alert_id"] for m in run_detail["members"]} == expected_members
                        for value in (run_detail, result_detail):
                            previous, selected = frozen["previous_run_id"], frozen["comparison_result_id"]
                            assert value["previous_run_url"] == (base + f"/runs/{previous}" if previous else None)
                            assert value["comparison_result_url"] == (base + f"/results/{selected}" if selected else None)
                assert len(contexts) == source["case_runs"]
                for incident in saved["incidents"]:
                    view = await get(f"/api/v1/socai2/incidents/{incident['id']}")
                    assert view["case_receiving"]["active_case_id"] == str(incident["active_case_id"])
                    assert view["case_receiving"]["can_receive_automatically"] is True
            _, after = await snapshot(service, tenant, tables)
            assert before == after
            batch.update(after=after, comparison_by_run=contexts, passed=True)
        record(phase, True, {"batches": batches, "calls": calls, "new_model_calls": 0,
            "new_tasks": 0, "database_writes": 0, "clock_substituted_by_http": False})
    except Exception as exc:  # noqa: BLE001 -- read-only failure never restarts ended work
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record(phase, False, {"batches": batches, "calls": calls, "error_type": type(exc).__name__,
            "error": str(exc), "failure_location": {"file": location.filename, "line": location.lineno}})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context


async def execution_readback(engine, record):
    """Read the three uniquely consumed tasks; replay only their original keys."""
    phase = "case_update_http_execution_readback"
    root = Path(os.environ["SOCAI2_CASE_UPDATE_HTTP_EVIDENCE"])
    admitted = json.loads((root / "admission-pg-01.json").read_text())["checks"][0]
    assert admitted["passed"]
    admission = admitted["detail"]
    sample, source, receipts = (admission[k] for k in ("sample", "source", "receipts"))
    consumed = json.loads(Path(os.environ["SOCAI2_CASE_UPDATE_HTTP_CONSUMED"]).read_text())
    assert consumed["state"] == "passed" and consumed["real_model_calls"] == 0
    assert consumed["tenant_id"] == source["tenant_id"]
    expected = {v["intent"]: v for v in consumed["after"]}
    assert set(expected) == {"initial", "check", "rerun"}
    assert {k: v["status"] for k, v in expected.items()} == {
        "initial": "completed", "check": "skipped", "rerun": "completed"}
    config = json.loads(Path(sample["verification_config_file"]).read_text())
    assert engine.url.database == source["database"] == "v12_upgrade_dev"
    tenant, actor, cid = UUID(source["tenant_id"]), UUID(source["actor_id"]), admission["case_id"]
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    keys = ("SOCAI2_CASE_ALLOCATION_CONFIG_FILE", "SOCAI2_ANALYSIS_TASKS_CONFIG_FILE",
        "SOCAI2_RUN_RECORDS_CONFIG_FILE")
    env = {key: os.environ.get(key) for key in keys}
    calls, saved, before, after = [], {}, None, None
    try:
        os.environ[keys[0]], os.environ[keys[1]] = config["allocation_policy_file"], config["lifecycle_policy_file"]
        os.environ[keys[2]] = str(Path(__file__).resolve().parents[3] / "deploy/http-service/run-records.json")
        policy = AnalysisTaskPolicy.load()
        app.state.business_context = BusinessContext(tenant, actor, "Ended HTTP Case update batch")
        app.dependency_overrides.update({case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy),
            analysis_submission_service: lambda: AnalysisSubmissionBackend(sessions, policy=policy),
            run_directory_service: lambda: RunDirectoryBackend(sessions),
            run_record_service: lambda: RunRecordBackend(sessions)})
        tables = (*TABLES, m.Activities, m.ActivityTargets)
        saved, before = await snapshot(service, tenant, tables)
        assert len(saved["analysis_tasks"]) == 3 and len(saved["analysis_attempts"]) == len(saved["runs"]) == 2
        assert len(saved["results"]) == 2
        base = f"/api/v1/socai2/cases/{cid}"
        contexts, details, results, originals, tasks = {}, {}, {}, {}, {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def request(method, path, status=200, **kwargs):
                call = {"method": method, "path": path, "request": kwargs}
                calls.append(call)
                response = await client.request(method, path, **kwargs)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == status, call
                return call["body"]

            for intent in ("initial", "check", "rerun"):
                receipt = receipts[intent]
                task = await request("GET", receipt["status_url"])
                tasks[intent] = task
                for key in ("task_id", "subject_id", "status", "reason_code", "latest_run_id", "retry_count"):
                    assert task[key] == expected[intent][key], (intent, key)
                assert task["intent"] == intent and task["subject_id"] == cid
                if intent == "check":
                    assert task["reason_code"] == "no_changes" and task["latest_run_id"] is None
                    assert task["attempts"] == task["results"] == []
                    continue
                assert len(task["attempts"]) == len(task["results"]) == 1
                assert task["attempts"][0]["outcome"] == "completed"
                detail = await request("GET", task["attempts"][0]["run_url"])
                run = detail["run"]
                rid = run["id"]
                assert rid == task["latest_run_id"] and run["state"] == "completed"
                assert detail["input_member_count"] == len(source["alert_ids"])
                assert {r["alert_id"] for r in detail["members"]} == set(source["alert_ids"])
                result = await request("GET", task["results"][0]["url"])
                assert result["run"] == run and result["result"]["source_run_id"] == rid
                stored_result = next(r for r in saved["results"] if str(r["id"]) == result["result"]["id"])
                for key in ("title", "conclusion", "validation_state", "findings", "questions", "recommendations",
                        "delivery_state", "change_kind", "change_summary"):
                    assert result["result"][key] == stored_result[key], key
                details[intent], results[intent] = detail, result
                contexts[intent] = run["comparison_context"]
                assert result["result"]["comparison_context"] == contexts[intent]

                async def all_pages(path, run_id=rid):
                    rows, cursor = [], None
                    while True:
                        page = await request("GET", path, params={"limit": 20, **({"cursor": cursor} if cursor else {})})
                        assert page["run_id"] == run_id and page["subject_id"] == cid
                        rows.extend(page["items"])
                        cursor = page["next_cursor"]
                        if cursor is None:
                            assert len(rows) == page["total"]
                            return rows

                steps = await all_pages(detail["steps_url"])
                artifacts = await all_pages(detail["artifacts_url"])
                assert {r["id"] for r in steps} == {str(r["id"]) for r in saved["run_steps"] if str(r["run_id"]) == rid}
                stored_artifacts = {str(r["id"]): r for r in saved["artifacts"] if str(r["run_id"]) == rid}
                assert {r["id"] for r in artifacts} == set(stored_artifacts)
                c6 = next(r for r in steps if r["stage_code"] == "C6")
                assert await request("GET", detail["steps_url"] + "/" + c6["id"]) == c6
                attempt = next(r for r in saved["analysis_attempts"] if str(r["run_id"]) == rid)
                selected = {run["input_artifact_id"], str(attempt["policy_artifact_id"])}
                for kind in ("model_request", "model_response", "report_json", "report_markdown"):
                    selected.add(next(r["id"] for r in artifacts if r["kind"] == kind))
                for row in artifacts:
                    if row["id"] in selected:
                        original = await request("GET", row["content_url"])
                        stored = stored_artifacts[row["id"]]
                        assert original["content_json"] == stored["content_json"]
                        assert original["content_text"] == stored["content_text"]
                        assert original["artifact"]["sha256"] == stored["sha256"] == row["sha256"]
                        originals[row["id"]] = original
                frozen = originals[run["input_artifact_id"]]["content_json"]["comparison_context"]
                assert frozen == contexts[intent] and frozen["comparison_result_id"] == run["comparison_result_id"]

            assert contexts["initial"] == {"previous_run_id": None, "comparison_result_id": None,
                "state": "initial", "reason_code": None}
            assert contexts["rerun"] == {"previous_run_id": details["initial"]["run"]["id"],
                "comparison_result_id": results["initial"]["result"]["id"], "state": "eligible", "reason_code": None}
            for value in (details["rerun"], results["rerun"]):
                for field, original in (("previous_run_url", details["initial"]),
                        ("comparison_result_url", results["initial"])):
                    linked = await request("GET", value[field])
                    if field == "previous_run_url":
                        assert datetime.fromisoformat(linked["observed_at"]) >= datetime.fromisoformat(original["observed_at"])
                    assert {k: v for k, v in linked.items() if k != "observed_at"} == {
                        k: v for k, v in original.items() if k != "observed_at"}
            page = await request("GET", base + "/analysis-tasks")
            assert page["total"] == 3 and {r["task_id"] for r in page["items"]} == {r["task_id"] for r in tasks.values()}
            assert page["update_state"]["last_normal_completed_at"] == tasks["rerun"]["ended_at"]
            assert page["update_state"]["eligible"] is True
            directory = await request("GET", "/api/v1/socai2/analysis-runs", params={"subject_type": "case", "subject_id": cid})
            assert directory["total"] == 2 and {r["task_id"] for r in directory["items"]} == {
                tasks[k]["task_id"] for k in ("initial", "rerun")}
            view = await request("GET", base)
            current = view["current_assessment"]
            assert current["value"]["id"] == str(saved["cases"][0]["current_assessment_id"])
            assert current["covers_current_members"] is True
            assert {r["result_id"] for r in current["sources"]} == {results["rerun"]["result"]["id"]}

            # Terminal replay retains the original admission, never schedules another task.
            assert await request("POST", "/api/v1/socai2/cases", 201, json=sample["create_request"]) == receipts["create"]
            for mode in ("check", "rerun"):
                body = {"operation_key": sample["operation_keys"][mode], "mode": mode}
                assert await request("POST", base + "/investigations", 202, json=body) == receipts[mode]
                assert await request("GET", receipts[mode]["status_url"]) == tasks[mode]
        _, after = await snapshot(service, tenant, tables)
        assert before == after, "Reads and original-key replays must preserve all 21 table snapshots"
        record(phase, True, {"case_id": cid, "calls": calls, "before": before, "after": after,
            "tasks": tasks, "comparison": contexts, "saved": saved,
            "source_consumer": os.environ["SOCAI2_CASE_UPDATE_HTTP_CONSUMED"],
            "consumer_substitute_model_calls": consumed["substitute_model_calls"],
            "new_model_calls": 0, "new_execution_calls": 0, "new_tasks": 0})
    except Exception as exc:  # noqa: BLE001 -- preserve failed reads/replays without re-executing
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record(phase, False, {"case_id": cid, "calls": calls, "before": before, "after": after,
            "error_type": type(exc).__name__, "error": str(exc),
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
