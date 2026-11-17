"""Read the ended F5 A/I/Case chain and its current model contracts through HTTP."""
import hashlib
import json
import traceback
from pathlib import Path
from uuid import UUID

from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.baseline_service import BaselineService
from app.socai2.page_reader import PageReadService
from app.socai2.run_records import RunRecordLimits
from app.socai2.runtime_policy import active_policy
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
from test_socai2_incident_case_scope_http_pg import TABLES

BASE = "/api/v1/socai2"


def source_hashes(root, source_dir):
    wrapper = json.loads((source_dir.parent.parent / "test-f5-independent-20261115-01/pg-contract-01.json").read_text())
    assert wrapper["state"] == wrapper["driver_state"] == "passed"
    hashes = wrapper["source_sha256_after"]
    assert hashes == wrapper["source_sha256_before"]
    assert {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in hashes} == hashes
    configs = wrapper["configuration_sha256_after"]
    assert configs == wrapper["configuration_sha256_before"]
    assert {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in configs} == configs
    return hashes


async def run_checks(engine, source_dir, config):
    source = json.loads((source_dir / "result.json").read_text())
    original = json.loads((source_dir / "snapshot.json").read_text())
    original_context = json.loads((source_dir / "case-context.json").read_text())
    assert source["state"] == "passed" and source["real_model_calls"] == 0
    assert engine.url.database == source["database"]["name"] == "v12_upgrade_dev"
    assert engine.url.port == source["database"]["port"]
    tenant, actor = UUID(source["tenant_id"]), UUID(source["actor_id"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    policy = AnalysisTaskPolicy(**json.loads(Path(config["lifecycle_policy_file"]).read_text()))
    limits = RunRecordLimits(**json.loads(Path(config["http_limits_file"]).read_text()))
    runtime = active_policy()
    runtime.require_execution_profiles()
    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    result = {"state": "running", "source": str(source_dir), "tenant_id": str(tenant),
              "calls": [], "checks": [], "source_model_substitutes": source["substitute_model_calls"],
              "new_model_calls": 0, "new_execution_calls": 0, "writes": 0}
    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text("SHOW default_transaction_read_only"))).scalar_one() == "on"
        saved, result["before"] = await snapshot(service, tenant, TABLES)
        assert {k: len(v) for k, v in saved.items()} == {k: len(v) for k, v in original.items()}
        assert len(saved["analysis_tasks"]) == len(saved["analysis_attempts"]) == len(saved["runs"]) == 3
        assert all(t["state"] == "completed" for t in saved["analysis_tasks"])
        artifacts = {str(a["id"]): a for a in saved["artifacts"]}
        prior_artifacts = {a["id"]: a for a in original["artifacts"]}
        assert len(artifacts) == 69
        assert all(a["content_json"] == prior_artifacts[key]["content_json"]
                   and a["sha256"] == prior_artifacts[key]["sha256"] for key, a in artifacts.items())
        app.state.business_context = BusinessContext(tenant, actor, "F5 ended current contract readback")
        app.dependency_overrides.update({
            case_service: lambda: CaseBackend(sessions),
            page_service: lambda: PageReadService(sessions),
            analysis_service: lambda: StageReadService(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy),
            run_directory_service: lambda: RunDirectoryBackend(sessions, limits=limits),
            run_record_service: lambda: RunRecordBackend(sessions, limits=limits),
        })
        contents, entries, requests = {}, {}, {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path, **params):
                call = {"method": "GET", "path": path, "params": params}
                result["calls"].append(call)
                response = await client.get(path, params=params)
                call.update(status=response.status_code, body=response.json())
                assert "authorization" not in response.request.headers
                assert response.status_code == 200, call
                return call["body"]

            for expected in source["tasks"]:
                kind, sid, rid = expected["subject_type"], expected["subject_id"], expected["latest_run_id"]
                plural = {"alert": "alerts", "incident": "incidents", "case": "cases"}[kind]
                subject = await get(f"{BASE}/{plural}/{sid}")
                if kind == "case":
                    assert subject["member_count"] == 1
                page = await get(f"{BASE}/{plural}/{sid}/analysis-tasks")
                assert page["total"] == len(page["items"]) == 1
                task = await get(page["items"][0]["status_url"])
                for field in ("task_id", "subject_id", "kind", "intent", "source", "status", "latest_run_id"):
                    assert task[field] == expected[field]
                assert len(task["attempts"]) == len(task["results"]) == 1
                assert task["attempts"][0]["outcome"] == "completed"
                view = await get(task["attempts"][0]["run_url"])
                assert view["run"]["id"] == rid and view["run"]["state"] == "completed"
                entries[kind] = view
                final = await get(task["results"][0]["url"])
                assert final["result"]["source_run_id"] == rid
                if kind == "case":
                    assert final["result"] == json.loads((source_dir / "case-result-readback.json").read_text())["result"]
                steps = await get(f"{BASE}/analysis-runs/{rid}/steps", limit=100)
                directory = await get(f"{BASE}/analysis-runs/{rid}/artifacts", limit=100)
                rows = {str(s["id"]): s for s in saved["run_steps"] if str(s["run_id"]) == rid}
                assert steps["next_cursor"] is None and directory["next_cursor"] is None
                assert {s["id"] for s in steps["items"]} == set(rows)
                assert all(s["state"] == rows[s["id"]]["state"] for s in steps["items"])
                assert {a["id"] for a in directory["items"]} == {k for k, a in artifacts.items() if str(a["run_id"]) == rid}
                for item in directory["items"]:
                    content = await get(item["content_url"])
                    aid = item["id"]
                    metadata = content["artifact"] if kind == "case" else content["metadata"]
                    assert metadata["id"] == aid and metadata["sha256"] == artifacts[aid]["sha256"]
                    assert content["content_json"] == artifacts[aid]["content_json"]
                    assert content["content_text"] == artifacts[aid]["content_text"]
                    contents[aid] = content["content_json"]
                for step in rows.values():
                    if step["kind"] != "model":
                        continue
                    assert step["state"] == "completed"
                    request = contents[str(step["input_artifact_id"])]; response = contents[str(step["output_artifact_id"])]
                    data, reply = (request["payload"], response["payload"]) if kind == "case" else (request, response)
                    assert reply["raw"]
                    if kind == "case":
                        boundary = data["case_boundary"]
                        assert boundary["profile"] == runtime.case_io.identity == original_context["case_input_profile"]
                        stage = boundary.get("stage", "C3")
                        assert all(aid in artifacts for aid in data["input_artifact_ids"])
                    else:
                        profile = runtime.alert_io if kind == "alert" else runtime.incident_io
                        boundary = data[f"{kind}_boundary"]
                        assert boundary["version"] == profile.version
                        assert boundary["profile_sha256"] == profile.sha256
                        stage = "A" if kind == "alert" else "I"
                    requests[stage] = {"run_id": rid, "request_artifact_id": str(step["input_artifact_id"]),
                                       "response_artifact_id": str(step["output_artifact_id"])}
            assert set(contents) == set(artifacts) and set(requests) == {"A", "I", "C3", "Deep", "C6"}
            c1 = next(value for value in contents.values() if isinstance(value, dict)
                      and "alerts" in value and "incidents" in value)
            assert c1 == original_context and set(c1["alerts"]) == {source["alert_id"]}
            assert c1["alerts"][source["alert_id"]]["triage_usable"]
            assert c1["incidents"][source["incident_id"]]["diagnosis_usable"]
            assert c1["incidents"][source["incident_id"]]["diagnosis_scope"]["source_run_id"] == entries["incident"]["run"]["id"]
            query = next(s for s in saved["run_steps"] if s["stage_code"] == "C4.query")
            assert query["state"] == "completed" and query["returned_rows"] == 1
            query_output = contents[str(query["output_artifact_id"])]
            assert query_output["state"] == "completed" and len(query_output["rows"]) == 1
            assert str(query["input_artifact_id"]) in contents
            result.update(model_stages=requests, query_step_id=str(query["id"]),
                          current_case_profile=runtime.case_io.identity)
        _, result["after"] = await snapshot(service, tenant, TABLES)
        assert result["before"] == result["after"]
        result.update(state="passed", checks=["three_completed_A_I_Case_tasks_original_results",
            "all69_artifacts_and25_steps_readable_same_source", "current_A_I_C3_Deep_C6_contracts_and_frozen_profile",
            "Case_original_A_I_sources_query_one_synthetic_row_and_final_Result_preserved",
            "GET_only_no_auth_19_tables_unchanged"])
    except Exception as exc:  # noqa: BLE001 -- preserve failures without replaying execution
        last = traceback.extract_tb(exc.__traceback__)[-1]
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc),
                      failure_location={"file": last.filename, "line": last.lineno})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context
    result["http_requests"] = len(result["calls"])
    return result
