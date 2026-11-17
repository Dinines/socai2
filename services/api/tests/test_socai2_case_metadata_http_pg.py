"""F2 ended-batch HTTP checks: management is retained without losing prior A."""
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
from test_socai2_incident_case_scope_http_pg import (
    source_hashes,  # noqa: F401 -- explicit read-only runner entry
)

TABLES = (m.Alerts, m.AlertMaterials, m.AlertObjects, m.AlertAssessments,
          m.Cases, m.CaseAlerts, m.AnalysisTasks, m.AnalysisAttempts,
          m.AnalysisSubjectState, m.Runs, m.RunMembers, m.RunSteps,
          m.Artifacts, m.Results, m.ResultMembers, m.Activities, m.ActivityTargets)
BASE = "/api/v1/socai2"


async def run_checks(engine, source_dir, config):
    source = json.loads((source_dir / "result.json").read_text())
    original = json.loads((source_dir / "snapshot.json").read_text())
    managed = json.loads((source_dir / "management.json").read_text())["items"][0]
    before_context = json.loads((source_dir / "before-context.json").read_text())
    after_context = json.loads((source_dir / "after-context.json").read_text())
    feedback_context = json.loads((source_dir / "feedback-context.json").read_text())
    assert source["state"] == "passed" and source["real_model_calls"] == 0
    assert engine.url.database == "v12_upgrade_dev"
    cid, aid = source["case_id"], source["alert_id"]
    tenant, actor = UUID(source["tenant_id"]), UUID(source["actor_id"])
    prior = before_context["alerts"][aid]
    after_edit = after_context["alerts"][aid]
    after_feedback = feedback_context["alerts"][aid]
    assert prior["triage_usable"] and after_edit["triage_usable"]
    assert prior["triage"] == after_edit["triage"] == after_feedback["triage"]
    assert prior["queries"] == after_edit["queries"] == after_feedback["queries"]
    assert prior["feedback"] is None and after_feedback["feedback"]
    arun = prior["triage"]["source_run_id"]
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    policy = AnalysisTaskPolicy(**json.loads(Path(config["lifecycle_policy_file"]).read_text()))
    limits = RunRecordLimits(**json.loads(Path(config["http_limits_file"]).read_text()))
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    result = {"state": "running", "source": str(source_dir), "tenant_id": str(tenant),
              "case_id": cid, "alert_id": aid, "alert_run_id": arun, "calls": [], "checks": [],
              "source_model_substitutes": source["substitute_model_calls"],
              "new_model_calls": 0, "new_execution_calls": 0, "writes": 0}
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("SHOW default_transaction_read_only"))).scalar_one() == "on"
        saved, result["before"] = await snapshot(service, tenant, TABLES)
        assert {k: len(v) for k, v in saved.items()} == {k: len(v) for k, v in original.items()}
        artifacts = {str(a["id"]): a for a in saved["artifacts"]}
        original_artifacts = {a["id"]: a for a in original["artifacts"]}
        assert all(a["content_json"] == original_artifacts[key]["content_json"]
                   and a["sha256"] == original_artifacts[key]["sha256"]
                   for key, a in artifacts.items())
        app.state.business_context = BusinessContext(tenant, actor, "F2 ended batch readback")
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
                    directories[run_id] = {item["id"]: item for item in page["items"]}
                response = await get(directories[run_id][artifact_id]["content_url"])
                metadata = response["metadata"] if run_id == arun else response["artifact"]
                assert metadata["id"] == artifact_id and metadata["sha256"] == artifacts[artifact_id]["sha256"]
                assert response["content_json"] == artifacts[artifact_id]["content_json"]
                return response["content_json"]

            view = await get(f"{BASE}/alerts/{aid}")
            for field in ("id", "owner_id", "assignment_state", "tags", "latest_material_id", "latest_triage_id"):
                assert view["facts"][field] == managed["facts"][field]
            assert view["triage"]["id"] == prior["triage"]["id"]
            assert view["triage"]["source_run_id"] == arun
            assert view["facts"]["latest_feedback_id"] == after_feedback["feedback"]["id"]
            material = await get(view["material"]["content_url"])
            assert material["metadata"]["id"] == prior["triage"]["input_material_id"]
            stored = next(row for row in saved["alert_materials"] if str(row["id"]) == material["metadata"]["id"])
            assert material["content_text"] == stored["raw_text"]
            assert material["content_json"] == {k: stored[k] for k in ("raw_json", "ocsf_json", "enrichment")}
            result["checks"].append("owner_tags_saved_original_material_and_A_preserved_feedback_separate")

            atasks = await get(f"{BASE}/alerts/{aid}/analysis-tasks")
            assert len(atasks["items"]) == atasks["total"] == 1
            atask = await get(atasks["items"][0]["status_url"])
            assert atask["status"] == "completed" and atask["latest_run_id"] == arun
            entry = await get(atask["attempts"][0]["run_url"])
            assert entry["result"]["id"] == prior["triage"]["id"]
            for field in ("verdict", "rationale", "score_state", "recommendations"):
                assert entry["result"][field] == prior["triage"][field]
            assert entry["freshness"] == "stale" and entry["valid_for_current_input"] is False
            result["public_A_freshness"] = {k: entry[k] for k in ("freshness", "valid_for_current_input")}
            history = await get(view["analysis_url"])
            assert history["current_pointer_id"] == prior["triage"]["id"]
            assert history["current"]["run"]["id"] == arun
            await artifact(arun, entry["run"]["input_artifact_id"])
            for query in prior["queries"]:
                body = await artifact(arun, query["id"])
                assert body == query["content_json"]
            result["checks"].append("A_public_historical_freshness_unchanged_prior_query_receipts_readable")

            case = await get(f"{BASE}/cases/{cid}")
            assert case["member_count"] == 1
            page = await get(f"{BASE}/cases/{cid}/analysis-tasks")
            assert {v["task_id"] for v in page["items"]} == {v["task_id"] for v in source["tasks"]}
            case_contexts = {}
            for row in page["items"]:
                task = await get(row["status_url"])
                expected = next(t for t in source["tasks"] if t["task_id"] == task["task_id"])
                for field in ("task_id", "status", "intent", "reason_code", "latest_run_id"):
                    assert task[field] == expected[field]
                if task["status"] == "skipped":
                    assert task["reason_code"] == "no_changes" and task["latest_run_id"] is None
                    assert task["attempts"] == task["results"] == []
                    continue
                assert task["status"] == "completed" and len(task["attempts"]) == len(task["results"]) == 1
                run = await get(task["attempts"][0]["run_url"])
                final = await get(task["results"][0]["url"])
                rid = task["latest_run_id"]
                assert run["run"] == final["run"] and final["result"]["source_run_id"] == rid
                assert final["member_count"] == 1
                contexts = [a for a in saved["artifacts"] if str(a["run_id"]) == rid
                            and isinstance(a["content_json"], dict) and "incidents" in a["content_json"]]
                assert len(contexts) == 1
                c1 = await artifact(rid, str(contexts[0]["id"]))
                alert = c1["alerts"][aid]
                assert alert["triage_usable"] and alert["triage_freshness"] == "current"
                assert alert["triage"] == prior["triage"] and alert["queries"] == prior["queries"]
                if task["intent"] == "initial":
                    assert alert["feedback"] is None and alert["alert"]["owner_id"] is None
                else:
                    assert task["source"] == "user" and task["intent"] == "check"
                    assert alert["feedback"] == after_feedback["feedback"]
                    assert alert["alert"]["owner_id"] == managed["facts"]["owner_id"]
                    assert alert["alert"]["tags"] == managed["facts"]["tags"]
                case_contexts[rid] = {"c1_artifact_id": str(contexts[0]["id"]),
                    "triage_id": alert["triage"]["id"], "triage_usable": alert["triage_usable"],
                    "feedback_id": (alert["feedback"] or {}).get("id"),
                    "query_artifact_ids": [q["id"] for q in alert["queries"]]}
            assert len(case_contexts) == 2
            result["case_contexts"] = case_contexts
            result["checks"].extend(["management_check_skipped_no_attempt_or_Run",
                "manual_feedback_check_saved_original_A_queries_and_human_statement"])
        _, result["after"] = await snapshot(service, tenant, TABLES)
        assert result["before"] == result["after"]
        result["checks"].append("GET_only_no_auth_17_table_snapshots_unchanged")
        result["state"] = "passed"
    except Exception as exc:  # noqa: BLE001 -- preserve failed reads, never replay execution
        last = traceback.extract_tb(exc.__traceback__)[-1]
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc),
                      failure_location={"file": last.filename, "line": last.lineno})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context
    result["http_requests"] = len(result["calls"])
    return result
