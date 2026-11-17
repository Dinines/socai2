"""Read the ended F1 batch through HTTP; no submissions, executors or model calls."""
import hashlib
import json
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
from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.run_directory import RunDirectoryBackend
from investigation_http.adapters.run_records import RunRecordBackend
from investigation_http.adapters.services import CaseBackend
from investigation_http.contracts import IncidentInputSelection
from investigation_http.dependencies import (
    analysis_service,
    analysis_task_service,
    case_service,
    page_service,
    run_directory_service,
    run_record_service,
)
from investigation_http.main import app
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_socai2_case_update_http_pg import snapshot

TABLES = (m.Alerts, m.AlertMaterials, m.AlertObjects, m.AlertAssessments,
          m.Incidents, m.IncidentAlerts, m.IncidentDiagnoses, m.Cases,
          m.CaseAlerts, m.CaseIncidents, m.AnalysisTasks, m.AnalysisAttempts,
          m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps,
          m.Artifacts, m.Results, m.ResultMembers)
BASE = "/api/v1/socai2"


async def run_checks(engine, source_dir, config):
    source = json.loads((source_dir / "result.json").read_text())
    prior = json.loads((source_dir / "snapshot.json").read_text())
    assert source["state"] == "passed" and source["real_model_calls"] == 0
    assert engine.url.database == source["database"] == "v12_upgrade_dev"
    tenant, actor = UUID(source["tenant_id"]), UUID(source["actor_id"])
    cid, iid, rid = source["case_id"], source["incident_id"], source["case_run_id"]
    scope = source["diagnosis_scope"]
    selected = scope["input_selection"]["selected_alert_ids"]
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    policy = AnalysisTaskPolicy(**json.loads(Path(config["lifecycle_policy_file"]).read_text()))
    limits = RunRecordLimits(**json.loads(Path(config["http_limits_file"]).read_text()))
    overrides = dict(app.dependency_overrides)
    context = getattr(app.state, "business_context", None)
    result = {"state": "running", "source": str(source_dir), "tenant_id": str(tenant),
              "case_id": cid, "incident_id": iid, "case_run_id": rid,
              "calls": [], "checks": [], "source_model_substitutes": source["substitute_model_calls"],
              "new_model_calls": 0, "new_execution_calls": 0, "writes": 0}
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("SHOW default_transaction_read_only"))).scalar_one() == "on"
        saved, result["before"] = await snapshot(service, tenant, TABLES)
        assert {k: len(v) for k, v in saved.items()} == {k: len(v) for k, v in prior.items()}
        assert len(saved["analysis_tasks"]) == len(saved["runs"]) == 3
        assert all(t["state"] == "completed" for t in saved["analysis_tasks"])
        artifacts = {str(a["id"]): a for a in saved["artifacts"]}
        frozen_artifacts = {a["id"]: a for a in prior["artifacts"]}
        assert all(a["content_json"] == frozen_artifacts[key]["content_json"]
                   and a["sha256"] == frozen_artifacts[key]["sha256"]
                   for key, a in artifacts.items())
        app.state.business_context = BusinessContext(tenant, actor, "F1 ended batch HTTP readback")
        app.dependency_overrides.update({
            case_service: lambda: CaseBackend(sessions),
            page_service: lambda: PageReadService(sessions),
            analysis_service: lambda: StageReadService(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy),
            run_directory_service: lambda: RunDirectoryBackend(sessions, limits=limits),
            run_record_service: lambda: RunRecordBackend(sessions, limits=limits),
        })
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(url, **params):
                call = {"method": "GET", "path": url, "params": params}
                result["calls"].append(call)
                response = await client.get(url, params=params)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == 200, call
                return call["body"]

            directories = {}

            async def artifact(run_id, artifact_id):
                if run_id not in directories:
                    page = await get(f"{BASE}/analysis-runs/{run_id}/artifacts", limit=100)
                    assert page["next_cursor"] is None
                    directories[run_id] = {a["id"]: a for a in page["items"]}
                item = directories[run_id][artifact_id]
                value = await get(item["content_url"])
                metadata = value["artifact"] if run_id == rid else value["metadata"]
                assert metadata["id"] == artifact_id
                assert value["content_json"] == artifacts[artifact_id]["content_json"]
                assert metadata["sha256"] == artifacts[artifact_id]["sha256"]
                return value["content_json"]

            case = await get(f"{BASE}/cases/{cid}")
            assert case["case"]["id"] == cid and case["member_count"] == 3
            await get(f"{BASE}/incidents/{iid}")
            members = await get(f"{BASE}/incidents/{iid}/records/members", limit=50, offset=0)
            assert members["total"] == 4 and len(members["items"]) == 4
            for subject, identity in (("cases", cid), ("incidents", iid)):
                tasks = await get(f"{BASE}/{subject}/{identity}/analysis-tasks")
                expected = [t for t in source["tasks"] if t["subject_id"] == identity]
                assert {t["task_id"] for t in tasks["items"]} == {t["task_id"] for t in expected}
                for row in tasks["items"]:
                    task = await get(row["status_url"])
                    original = next(t for t in expected if t["task_id"] == row["task_id"])
                    for field in ("task_id", "subject_id", "status", "intent", "latest_run_id"):
                        assert task[field] == original[field]
                    assert len(task["attempts"]) == len(task["results"]) == 1
                    assert task["attempts"][0]["run_id"] == task["latest_run_id"]
                    assert task["results"][0]["source_run_id"] == task["latest_run_id"]
            result["checks"].append("three_original_completed_tasks_case3_current_event4")

            incident_entries = {}
            for irun in (source["first_incident_run_id"], source["latest_incident_run_id"]):
                entry = await get(f"{BASE}/incidents/{iid}/analysis/runs/{irun}")
                incident_entries[irun] = entry
                inp = entry["input_selection"]
                original = await artifact(irun, inp["input_artifact_id"])
                expected_selection = IncidentInputSelection.model_validate({
                    **original["input_selection"], "input_artifact_id": inp["input_artifact_id"]})
                assert inp == expected_selection.model_dump(mode="json")
                assert entry["result"]["source_run_id"] == irun
            old = incident_entries[source["first_incident_run_id"]]
            new = incident_entries[source["latest_incident_run_id"]]
            assert old["input_selection"]["total_member_count"] == 3
            assert old["input_selection"]["selected_alert_ids"] == selected
            assert old["analysis_coverage"] == scope["analysis_coverage"]
            assert new["input_selection"]["total_member_count"] == 4
            assert new["input_selection"]["selected_alert_ids"] == [source["later_alert_id"]]
            history = await get(f"{BASE}/incidents/{iid}/analysis", limit=20)
            assert {e["run"]["id"] for e in history["entries"]} == set(incident_entries)
            assert history["current"]["run"]["id"] == source["latest_incident_run_id"]
            result["checks"].append("I_old3_selected1_covered1_latest4_distinct_source_runs")

            run = await get(f"{BASE}/cases/{cid}/runs/{rid}")
            final = await get(f"{BASE}/cases/{cid}/results/{source['case_result_id']}")
            assert final["result"]["source_run_id"] == rid
            assert run["run"] == final["run"]
            assert final["member_count"] == 3
            manifest = await artifact(rid, run["run"]["input_artifact_id"])
            assert set(manifest["scope"]["alert_ids"]) == set(source["source_alert_ids"])
            contexts = [a for a in saved["artifacts"] if str(a["run_id"]) == rid
                        and isinstance(a["content_json"], dict) and "incidents" in a["content_json"]]
            assert len(contexts) == 1
            c1 = await artifact(rid, str(contexts[0]["id"]))
            assert set(c1["alerts"]) == set(source["source_alert_ids"])
            frozen = c1["incidents"][iid]
            assert frozen["diagnosis_scope"] == scope
            assert set(frozen["member_ids"]) == set(frozen["case_member_ids"]) == set(source["source_alert_ids"])
            assert scope["source_run_id"] == old["run"]["id"] != new["run"]["id"]
            assert scope["input_artifact_id"] == old["input_selection"]["input_artifact_id"]
            assert scope["source_fingerprint"] == old["result"]["source_fingerprint"]
            result["checks"].append("C1_frozen_scope_and_original_I_identity_preserved_after_new_I")

            requests = [a for a in saved["artifacts"] if str(a["run_id"]) == rid and a["kind"] == "model_request"]
            assert len(requests) == 2
            path = f"$.incidents.{iid}.diagnosis.diagnosis.conclusion"
            mappings = []
            for request in requests:
                data = await artifact(rid, str(request["id"]))
                refs = [v for v in data["payload"]["source_map"].values() if v["ref"].get("source_path") == path]
                assert refs and all(v["alert_ids"] == scope["case_covered_alert_ids"] == selected for v in refs)
                assert all(v["original_scope"]["alert_ids"] == selected for v in refs)
                assert all(v["ref"]["id"] == str(contexts[0]["id"]) and v["ref"]["role"] == "prior_analysis" for v in refs)
                mappings.append({"artifact_id": str(request["id"]), "incident_conclusion_refs": refs})
            result["model_request_scope_readback"] = mappings
            expected_final = json.loads((source_dir / "case-result-readback.json").read_text())
            assert final["result"] == expected_final["result"]
            result["checks"].append("C3_C6_I_conclusion_refs_only1_final_result_same_source")
        _, result["after"] = await snapshot(service, tenant, TABLES)
        assert result["before"] == result["after"]
        result["checks"].append("GET_only_no_auth_19_table_snapshots_unchanged")
        result["state"] = "passed"
    except Exception as exc:  # noqa: BLE001 -- preserve failed readback without rerunning tasks
        last = traceback.extract_tb(exc.__traceback__)[-1]
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc),
                      failure_location={"file": last.filename, "line": last.lineno})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context
    result["http_requests"] = len(result["calls"])
    return result


def source_hashes(root, source_dir):
    hashes = json.loads((source_dir / "source-hashes.json").read_text())
    current = {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in hashes}
    assert current == hashes, "F1 source version changed; coordinate before testing"
    return current
