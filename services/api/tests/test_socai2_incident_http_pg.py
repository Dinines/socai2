"""I HTTP checks against handed-over, isolated PG samples; no model generation."""
import hashlib
import json
import os
import traceback
from pathlib import Path
from uuid import UUID

from app.models import socai2 as m
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.baseline_service import BaselineService
from app.socai2.page_reader import PageReadService
from app.socai2.run_records import RunRecordLimits
from app.socai2.stage_reader import StageReadService
from httpx import ASGITransport, AsyncClient
from investigation_http.adapters.analysis_submissions import AnalysisSubmissionBackend
from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.run_directory import RunDirectoryBackend
from investigation_http.adapters.run_records import RunRecordBackend
from investigation_http.contracts import IncidentInputSelection
from investigation_http.dependencies import (
    analysis_service,
    analysis_submission_service,
    analysis_task_service,
    page_service,
    run_directory_service,
    run_record_service,
)
from investigation_http.main import app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[3]
TABLES = (m.Alerts, m.AlertMaterials, m.AlertAssessments, m.Incidents, m.IncidentAlerts,
          m.IncidentDiagnoses, m.Runs, m.RunSteps, m.Artifacts, m.AnalysisTasks,
          m.AnalysisAttempts, m.AnalysisSubjectState)


async def run_checks(engine, record, only=None):
    assert only and len(only) == 1
    phase = next(iter(only))
    sample = json.loads(Path(os.environ["SOCAI2_INCIDENT_HTTP_SAMPLE_FILE"]).read_text())
    tenant, identity = UUID(sample["tenant_id"]), UUID(sample["incident_id"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    policy = AnalysisTaskPolicy(**json.loads(Path(sample["lifecycle_policy_file"]).read_text()))
    limits = RunRecordLimits(**json.loads((ROOT / "deploy/http-service/run-records.json").read_text()))
    original, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    calls, before, after, receipt = [], None, None, None

    async def snapshot():
        saved, hashes = {}, {}
        async with service.transaction(tenant, readonly=True) as store:
            for model in TABLES:
                table = model.__table__
                rows = [dict(row) for row in (await store.db.execute(
                    select(table).where(table.c.tenant_id == tenant))).mappings()]
                saved[table.name] = rows
                hashes[table.name] = {str(row.get("id", row.get("subject_id"))): hashlib.sha256(
                    json.dumps(row, sort_keys=True, default=str).encode()).hexdigest() for row in rows}
        return saved, hashes

    def one(saved, name, key):
        rows = [row for row in saved[name] if str(row["id"]) == str(key)]
        assert len(rows) == 1, (name, str(key), len(rows))
        return rows[0]

    try:
        saved, before = await snapshot()
        app.state.business_context = BusinessContext(tenant, UUID(sample["actor_id"]), "事件HTTP联验")
        app.dependency_overrides.update({
            page_service: lambda: PageReadService(sessions),
            analysis_service: lambda: StageReadService(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy),
            analysis_submission_service: lambda: AnalysisSubmissionBackend(sessions, policy=policy),
            run_directory_service: lambda: RunDirectoryBackend(sessions, limits=limits),
            run_record_service: lambda: RunRecordBackend(sessions, limits=limits),
        })
        root = f"/api/v1/socai2/incidents/{identity}"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def request(method, url, *, status=200, **kwargs):
                response = await client.request(method, url, **kwargs)
                data = response.json()
                calls.append({"method": method, "url": str(response.request.url), "request": kwargs,
                              "status": response.status_code, "body": data})
                assert "authorization" not in response.request.headers
                assert response.status_code == status, (url, response.status_code, data)
                return data

            async def entry(run_id):
                value = await request("GET", root + "/analysis/runs/" + str(run_id))
                run = one(saved, "runs", run_id)
                assert value["run"]["state"] == run["state"]
                assert value["run"]["delivery_state"] == run["delivery_state"]
                artifact = one(saved, "artifacts", run["input_artifact_id"])
                source = artifact["content_json"]
                if not source.get("input_selection"):
                    assert value["input_selection"] is None and value["analysis_coverage"] is None
                else:
                    expected_selection = IncidentInputSelection.model_validate({
                        **source["input_selection"], "input_artifact_id": artifact["id"]}).model_dump(mode="json")
                    assert value["input_selection"] == expected_selection
                    selection = value["input_selection"]
                    assert selection["selected_count"] == len(selection["selected_alert_ids"])
                    assert selection["selected_count"] + selection["omitted_count"] == selection["total_member_count"]
                    coverage = value["analysis_coverage"]
                    if coverage["state"] != "unknown":
                        assert sum(coverage[k] for k in ("analyzed_count", "unresolved_count", "not_analyzed_count")) == selection["selected_count"]
                        assert len(coverage["covered_alert_ids"]) == coverage["analyzed_count"] + coverage["unresolved_count"]
                        assert set(coverage["covered_alert_ids"]) <= set(selection["selected_alert_ids"])
                        if selection["omitted_count"] and coverage["covered_alert_ids"]:
                            assert coverage["state"] == "partial"
                if value["result"]:
                    result = one(saved, "incident_diagnoses", value["result"]["id"])
                    assert str(result["source_run_id"]) == str(run_id)
                    for key in ("summary", "diagnosis", "open_questions", "source_fingerprint"):
                        assert value["result"][key] == result[key]
                    assessment = (result["diagnosis"] or {}).get("delivery_assessment")
                    if value["analysis_coverage"] and value["analysis_coverage"]["state"] != "unknown":
                        assert set(value["analysis_coverage"]["covered_alert_ids"]) == set(assessment["member_coverage"]["analyzed_ids"])
                        assert value["analysis_coverage"]["unresolved_count"] == len(set(assessment["review_items"]["unresolved_member_ids"]))
                return value

            if phase == "incident_http_read":
                view = await request("GET", root)
                history = await request("GET", view["analysis_url"])
                data = await entry(sample["run_id"])
                assert any(row == data for row in history["entries"])
                checked = {sample["run_id"]: data}
                for old in history["entries"]:
                    old_id = old["run"]["id"]
                    if old_id not in checked:
                        checked[old_id] = await entry(old_id)
                    assert old == checked[old_id]
                assert history["current_pointer_id"] == view["facts"]["latest_diagnosis_id"]
                if history["current"]:
                    assert history["current"] == checked[history["current"]["run"]["id"]]
                tasks = await request("GET", root + "/analysis-tasks")
                task = await request("GET", root + "/analysis-tasks/" + sample["task_id"])
                assert task in tasks["items"] and task["latest_run_id"] == sample["run_id"]
                directory = await request("GET", "/api/v1/socai2/analysis-runs", params={"subject_type": "incident", "subject_id": str(identity)})
                row = next(row for row in directory["items"] if row["run_id"] == sample["run_id"])
                assert row["task_id"] == sample["task_id"]
                assert row["results"] == task["results"]
                trace = await request("GET", root + "/analysis/runs/" + sample["run_id"] + "/trace")
                for name, table in (("steps", "run_steps"), ("artifacts", "artifacts")):
                    page = await request("GET", trace[name + "_url"])
                    expected = {str(row["id"]) for row in saved[table] if str(row["run_id"]) == sample["run_id"]}
                    assert page["next_cursor"] is None and {row["id"] for row in page["items"]} == expected
                    if name == "artifacts":
                        for artifact in page["items"]:
                            content = await request("GET", artifact["content_url"])
                            stored = one(saved, table, artifact["id"])
                            assert content["metadata"]["id"] == artifact["id"]
                            assert content["content_json"] == stored["content_json"]
                            assert content["content_text"] == stored["content_text"]
                _, after = await snapshot()
                assert before == after
            elif phase in {"incident_submit_check", "incident_submit_rerun"}:
                mode = phase.removeprefix("incident_submit_")
                body = {"operation_key": sample["operation_key"], "mode": mode}
                receipt = await request("POST", root + "/diagnose", status=202, json=body)
                assert receipt == await request("POST", root + "/diagnose", status=202, json=body)
                assert receipt["subject_type"] == "incident" and receipt["subject_id"] == str(identity)
                assert receipt["status"] == "accepted"
                task = await request("GET", receipt["status_url"])
                assert task["status"] == "accepted" and task["intent"] == mode and task["source"] == "user"
                assert task["latest_run_id"] is None and task["attempts"] == [] and task["results"] == []
                conflict = await request("POST", root + "/diagnose", status=409,
                    json={**body, "mode": "rerun" if mode == "check" else "check"})
                assert conflict["detail"]["code"] == "operation_conflict"
                if mode == "check":
                    await request("POST", root + "/diagnose", status=422, json={"operation_key": sample["operation_key"]})
                    await request("POST", root + "/diagnose", status=422, json={**body, "run_id": sample["run_id"]})
                    await request("POST", root + "/diagnose", status=422, json=body, params={"extra": "not-supported"})
                    await request("POST", f"/api/v1/socai2/cases/{identity}/investigations", status=404, json=body)
                latest, after = await snapshot()
                new = set(after["analysis_tasks"]) - set(before["analysis_tasks"])
                assert new == {receipt["task_id"]}
                task_row = one(latest, "analysis_tasks", receipt["task_id"])
                assert str(task_row["submitted_by"]) == sample["actor_id"] and task_row["source"] == "user"
                for table in before:
                    if table not in {"analysis_tasks", "analysis_subject_state"}:
                        assert before[table] == after[table], table
            elif phase in {"incident_after_check", "incident_after_rerun"}:
                submitted = json.loads(Path(sample["submission_evidence"]).read_text())["checks"][0]
                assert submitted["passed"]
                previous = submitted["detail"]
                receipt = previous["receipt"]
                task = await request("GET", receipt["status_url"])
                mode = phase.removeprefix("incident_after_")
                assert receipt == await request("POST", root + "/diagnose", status=202,
                    json={"operation_key": sample["operation_key"], "mode": mode})
                if mode == "check":
                    assert task["status"] == "skipped" and task["reason_code"] == "no_changes"
                    assert task["latest_run_id"] is None and task["results"] == []
                    assert before["runs"] == previous["before"]["runs"]
                else:
                    assert task["status"] == "completed" and task["latest_run_id"]
                    new_runs = set(before["runs"]) - set(previous["before"]["runs"])
                    assert new_runs == {task["latest_run_id"]}
                    value = await entry(task["latest_run_id"])
                    assert value["result"] and task["results"][0]["id"] == value["result"]["id"]
                    assert task["attempts"][-1]["run_id"] == value["run"]["id"]
                for table in ("alerts", "alert_materials", "alert_assessments", "runs", "run_steps", "artifacts", "incident_diagnoses"):
                    assert all(before[table][key] == val for key, val in previous["before"][table].items()), table
                _, after = await snapshot()
                assert before == after, "GET and terminal idempotency replay must not mutate stored records"
            else:
                raise ValueError("unsupported incident HTTP verification phase")
        record(phase, True, {"sample": sample, "calls": calls, "before": before, "after": after,
                            "receipt": receipt, "transport": "ASGI plus real isolated PG", "http_model_calls": 0})
    except Exception as exc:  # noqa: BLE001 -- persist failure; external runner asserts after writing evidence
        location = traceback.extract_tb(exc.__traceback__)[-1]
        record(phase, False, {"sample": sample, "calls": calls, "error_type": type(exc).__name__,
                             "error": str(exc), "failure_location": {"file": location.filename, "line": location.lineno},
                             "before": before, "after": after, "receipt": receipt})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)
        app.state.business_context = context
