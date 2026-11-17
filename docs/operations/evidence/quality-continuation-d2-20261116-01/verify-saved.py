"""Read the ended real-02 Run; never create tasks or call a model."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import traceback
from pathlib import Path
from uuid import UUID

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("d2_original_driver", HERE / "validate.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


async def verify(config, output):
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.baseline_store import digest
    from app.socai2.case_service import CaseService
    from redis.asyncio import Redis
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from test_socai2_case_initial_http_pg import snapshot

    output.mkdir(exist_ok=False)
    previous = HERE / "real-02"
    old = json.loads((previous / "result.json").read_text())
    evidence = [p for p in previous.iterdir() if p.is_file()]
    fingerprints = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence}
    result = {k: old[k] for k in ("tenant_id", "actor_id", "case_id", "task_id", "run_id", "result_id")}
    result.update(state="checking", checks=[], model_calls=0, business_writes=0,
                  http_transport="ASGITransport", original_driver_error="KeyError: delivery",
                  explanation="report_json is compact; full delivery is a delivery_report source_snapshot",
                  original_evidence_sha256=fingerprints)
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["host"] == "127.0.0.1" and cfg["processing_database"] == "v12_upgrade_dev"
    url = URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"],
        port=cfg["port"], database=cfg["processing_database"])
    engine = create_async_engine(url, hide_parameters=True,
        connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases = CaseService(sessions)
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    tenant, actor = UUID(old["tenant_id"]), UUID(old["actor_id"])
    try:
        saved, before = await snapshot(cases, tenant)
        normalized = json.loads(json.dumps(saved, default=str))
        assert normalized == json.loads((previous / "snapshot.json").read_text())
        driver.save(output / "database.json", saved)
        artifacts = {str(a["id"]): a for a in saved["artifacts"]}
        stored, run, attempt = saved["results"][0], saved["runs"][0], saved["analysis_attempts"][0]
        assert len(saved["runs"]) == len(saved["results"]) == len(saved["analysis_attempts"]) == 1
        assert run["state"] == "completed" and attempt["local_state"] == "ended"
        assert attempt["outcome"] == "completed"
        calls = json.loads((previous / "calls.json").read_text())
        responses = sorted((a for a in artifacts.values() if a["kind"] == "model_response"), key=lambda a: a["captured_at"])
        requests = sorted((a for a in artifacts.values() if a["kind"] == "model_request"), key=lambda a: a["captured_at"])
        assert len(responses) == len(requests) == len(calls) == 3
        issues, usages = [], []
        for response, request, call in zip(responses, requests, calls):
            payload = response["content_json"]["payload"]
            assert call["state"] == "responded" and payload["raw"] == call["response"]
            assert request["content_json"]["payload"]["body"] == call["request"]
            assert "tenant_uid" not in json.dumps(call["request"]["messages"])
            review = payload.get("citation_review")
            if review:
                assert artifacts[review["original_response_artifact_id"]]["content_json"]["raw"] == payload["raw"]
                assert review["original_sha256"] == digest(call["response"]["choices"][0]["message"]["content"])
                assert review["prose_quality"] == "not_checked" and review["conclusion_modified"] is False
                issues.extend({"stage": call["stage"], **i} for i in review["issues"])
            usages.append({"stage": call["stage"], "finish_reason": call["response"]["choices"][0]["finish_reason"],
                           "usage": call["response"]["usage"]})
        final = json.loads(calls[-1]["response"]["choices"][0]["message"]["content"])
        derived = responses[-1]["content_json"]["payload"]["derived"]
        full = [a["content_json"] for a in artifacts.values()
                if a["kind"] == "source_snapshot" and a["content_json"].get("type") == "delivery_report"]
        assert len(full) == 1
        report = artifacts[str(stored["report_artifact_id"])]["content_json"]
        assert str(stored["id"]) == report["result_id"] == full[0]["result_id"]
        assert stored["conclusion"] == report["conclusion"] == final["conclusion"]["text"]
        assert stored["conclusion_state"] == final["conclusion"]["state"]
        assert stored["validation_state"] == "accepted" and stored["conclusion_origin"] == "model"
        # Model aliases are restored to frozen alert UUIDs by the adapter.
        for field in ("text", "state", "limitations", "support_ids"):
            assert derived["conclusion"][field] == final["conclusion"][field], field
        assert set(derived["conclusion"]["alert_ids"]) == set(old["alert_ids"])
        assert full[0]["delivery"]["conclusion"]["limitations"] == final["conclusion"]["limitations"]
        assert report["citation_review"] == full[0]["citation_review"] == responses[-1]["content_json"]["payload"]["citation_review"]
        for field in ("findings", "questions", "conclusion", "closing_note", "recommendations", "case_impact"):
            assert report[field] == stored[field], field
        result["checks"] += ["ended_Run_unchanged", "one_current_task_one_attempt", "real_C3_Deep_C6",
            "wire_equals_saved_requests", "three_model_inputs_exclude_tenant_uid", "raw_responses_and_hashes_unchanged",
            "model_conclusion_state_limits_retained", "compact_and_full_reports_match_saved_result_and_diagnostics"]
        await http_readback(sessions, cases, tenant, actor, result, saved, output)
        queues = AnalysisQueues(redis, config["dispatch"]["namespace"], tenant)
        running = await redis.scard(queues.key("running"))
        assert running == 0
        result["checks"].append("redis_running_slot_released")
        _, after = await snapshot(cases, tenant)
        assert before == after
        assert fingerprints == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence}
        result.update(state="passed", original_evidence_unchanged=True, running_slots=running,
            diagnosis_issues=issues, real_run_usage=usages, prose_quality="not_checked",
            result_state={k: stored[k] for k in ("validation_state", "conclusion_state", "delivery_state")},
            table_counts={k: len(v) for k, v in saved.items()}, before=before, after=after)
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        driver.save(output / "result.json", result)
        await redis.aclose()
        await engine.dispose()


async def http_readback(sessions, cases, tenant, actor, result, saved, out):
    from httpx import ASGITransport, AsyncClient
    from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
    from investigation_http.adapters.identity import BusinessContext
    from investigation_http.adapters.services import CaseBackend
    from investigation_http.dependencies import analysis_task_service, case_service
    from investigation_http.main import app
    from test_socai2_case_initial_http_pg import snapshot

    overrides, context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    replies = []
    try:
        _, before = await snapshot(cases, tenant)
        app.state.business_context = BusinessContext(tenant, actor, "D2 quality HTTP readback")
        app.dependency_overrides.update({case_service: lambda: CaseBackend(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions)})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path):
                response = await client.get(path)
                body = response.json()
                replies.append({"method": "GET", "path": path, "status": response.status_code, "body": body})
                assert response.status_code == 200, (path, response.status_code, body)
                return body
            cid, rid, tid = result["case_id"], result["run_id"], result["task_id"]
            stored, base = saved["results"][0], f"/api/v1/socai2/cases/{cid}"
            task = await get(base + f"/analysis-tasks/{tid}")
            assert task["status"] == "completed" and task["latest_run_id"] == str(rid)
            detail = await get(base + f"/runs/{rid}")
            assert detail["run"]["state"] == "completed" and detail["result_ids"] == [str(stored["id"])]
            detail = await get(base + f"/results/{stored['id']}")
            for field in ("conclusion", "conclusion_state", "validation_state", "findings", "questions", "delivery_state"):
                assert detail["result"][field] == stored[field], field
            report = next(a for a in saved["artifacts"] if str(a["id"]) == str(stored["report_artifact_id"]))["content_json"]
            assert detail["delivery"]["detail"]["citation_review"] == report["citation_review"]
            for row in saved["artifacts"]:
                content = await get(base + f"/runs/{rid}/artifacts/{row['id']}")
                assert content["content_json"] == row["content_json"] and content["content_text"] == row["content_text"]
        _, after = await snapshot(cases, tenant)
        assert before == after
        result.update(http_gets=len(replies), before_http=before, after_http=after)
        result["checks"] += ["HTTP_values_equal_saved_result_originals_diagnostics", "HTTP_read_does_not_write"]
    finally:
        driver.save(out / "http.json", replies)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    configuration = json.loads(args.config.read_text())
    driver.environment(configuration)
    asyncio.run(verify(configuration, args.output))
