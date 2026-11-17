"""Read a completed normal-ingress A batch through public HTTP; never execute it."""
import hashlib
import json
import os
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
from investigation_http.dependencies import (
    analysis_service,
    analysis_task_service,
    page_service,
    run_directory_service,
    run_record_service,
)
from investigation_http.main import app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[3]


async def run_checks(engine, record, only=None):
    if only and "alert_auto_http" not in only:
        return
    sample = json.loads(Path(os.environ["SOCAI2_ALERT_HTTP_SAMPLE_FILE"]).read_text())
    tenant, alert_id, task_id, run_id = (
        UUID(sample[key]) for key in ("tenant_id", "alert_id", "task_id", "run_id")
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = BaselineService(sessions)
    policy = AnalysisTaskPolicy(**json.loads((ROOT / "deploy/local-investigation/analysis-tasks.json").read_text()))
    limits = RunRecordLimits(**json.loads((ROOT / "deploy/http-service/run-records.json").read_text()))
    overrides, old_context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    calls, before, after = [], None, None

    async def snapshot():
        rows_by_table, summary = {}, {}
        async with service.transaction(tenant, readonly=True) as store:
            for model in (m.Alerts, m.AlertMaterials, m.AlertObjects, m.AlertAssessments,
                          m.Runs, m.RunSteps, m.Artifacts, m.AnalysisTasks, m.AnalysisAttempts,
                          m.AnalysisSubjectState):
                table = model.__table__
                rows = [dict(row) for row in (await store.db.execute(
                    select(table).where(table.c.tenant_id == tenant)
                )).mappings()]
                ordered = sorted(json.dumps(row, sort_keys=True, default=str) for row in rows)
                rows_by_table[table.name] = rows
                summary[table.name] = {"count": len(rows), "sha256": hashlib.sha256(
                    json.dumps(ordered).encode()).hexdigest()}
        return rows_by_table, summary

    def one(rows, identity):
        matches = [row for row in rows if row["id"] == identity]
        assert len(matches) == 1, (str(identity), len(matches))
        return matches[0]

    try:
        saved, before = await snapshot()
        alert = one(saved["alerts"], alert_id)
        task = one(saved["analysis_tasks"], task_id)
        run = one(saved["runs"], run_id)
        assessment = one(saved["alert_assessments"], alert["latest_triage_id"])
        assert task["source"] == "ingress" and task["intent"] == "initial"
        assert task["state"] == "completed" and run["state"] == "completed"
        assert task["subject_id"] == alert_id and run["alert_id"] == alert_id
        assert assessment["source_run_id"] == run_id
        assert assessment["input_material_id"] == alert["latest_material_id"]
        assert any(row["task_id"] == task_id and row["run_id"] == run_id for row in saved["analysis_attempts"])
        app.state.business_context = BusinessContext(tenant, UUID(sample["actor_id"]), "自动分诊查询核对")
        app.dependency_overrides.update({
            page_service: lambda: PageReadService(sessions),
            analysis_service: lambda: StageReadService(sessions),
            analysis_task_service: lambda: AnalysisTaskBackend(sessions, policy=policy),
            run_directory_service: lambda: RunDirectoryBackend(sessions, limits=limits),
            run_record_service: lambda: RunRecordBackend(sessions, limits=limits),
        })
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(url, params=None):
                response = await client.get(url, params=params)
                body = response.json()
                calls.append({"method": "GET", "url": str(response.request.url),
                              "status": response.status_code, "body": body})
                assert "authorization" not in response.request.headers
                assert response.status_code == 200, (url, response.status_code, body)
                return body

            root = f"/api/v1/socai2/alerts/{alert_id}"
            view = await get(root)
            assert view["facts"]["id"] == str(alert_id)
            assert view["material"]["id"] == str(alert["latest_material_id"])
            assert view["triage"]["id"] == str(assessment["id"])
            assert view["triage"]["source_run_id"] == str(run_id)
            material = await get(view["material"]["content_url"])
            assert material["metadata"]["id"] == view["material"]["id"]
            stored_material = one(saved["alert_materials"], alert["latest_material_id"])
            assert material["content_json"] == {key: stored_material[key] for key in
                                                ("raw_json", "ocsf_json", "enrichment")}
            assert material["content_text"] == stored_material["raw_text"]
            sources = await get(view["section_urls"]["source_artifacts"])
            expected_sources = {str(row["id"]) for row in saved["artifacts"]
                                if row["alert_id"] == alert_id and row["run_id"] is None}
            assert sources["next_offset"] is None
            assert {row["id"] for row in sources["items"]} == expected_sources
            for source in sources["items"]:
                content = await get(source["content_url"])
                stored = one(saved["artifacts"], UUID(source["id"]))
                assert content["metadata"]["id"] == source["id"]
                assert content["content_json"] == stored["content_json"]
                assert content["content_text"] == stored["content_text"]
            history = await get(view["analysis_url"])
            assert history["current_pointer_id"] == str(assessment["id"])
            assert history["current"]["run"]["id"] == str(run_id)
            entries = [row for row in history["entries"] if row["run"]["id"] == str(run_id)]
            assert len(entries) == 1
            page = await get(root + "/analysis-tasks")
            matched = [row for row in page["items"] if row["task_id"] == str(task_id)]
            assert len(matched) == 1
            detail = await get(matched[0]["status_url"])
            assert detail == matched[0]
            assert detail["status"] == "completed" and detail["source"] == "ingress"
            assert detail["latest_run_id"] == str(run_id)
            attempt = next(row for row in detail["attempts"] if row["run_id"] == str(run_id))
            entry = await get(attempt["run_url"])
            assert entry == entries[0]
            assert entry["result"]["id"] == str(assessment["id"])
            for field in ("verdict", "rationale", "score_state", "recommendations"):
                assert entry["result"][field] == assessment[field]
            refs = [row for row in detail["results"] if row["id"] == str(assessment["id"])]
            assert len(refs) == 1 and refs[0]["kind"] == "triage"
            assert refs[0]["url"] == attempt["run_url"]
            directory = await get("/api/v1/socai2/analysis-runs", {
                "subject_type": "alert", "subject_id": str(alert_id), "intent": "initial"})
            item = next(row for row in directory["items"] if row["run_id"] == str(run_id))
            assert item["task_id"] == str(task_id) and item["results"] == refs
            assert item["detail_url"] == attempt["run_url"]
            trace = await get(attempt["run_url"] + "/trace")
            contents = {}
            for name, table in (("steps", "run_steps"), ("artifacts", "artifacts")):
                url, items, cursor = trace[name + "_url"], [], None
                while True:
                    part = await get(url, {"cursor": cursor} if cursor else None)
                    items.extend(part["items"])
                    cursor = part["next_cursor"]
                    if cursor is None:
                        break
                expected = {str(row["id"]) for row in saved[table] if row["run_id"] == run_id}
                assert {row["id"] for row in items} == expected and len(items) == part["total"]
                for row in items:
                    if name == "steps":
                        assert await get(url + "/" + row["id"]) == row
                        refs_to_read = [(ref["artifact_id"], ref["content_url"]) for ref in row["artifact_refs"]]
                    else:
                        refs_to_read = [(row["id"], row["content_url"])]
                    for artifact_id, content_url in refs_to_read:
                        if content_url not in contents:
                            contents[content_url] = await get(content_url)
                        content = contents[content_url]
                        stored = one(saved["artifacts"], UUID(artifact_id))
                        assert content["metadata"]["id"] == artifact_id
                        if stored["blob_ref"] is None and stored["material_state"] == "complete":
                            assert content["content_json"] == stored["content_json"]
                            assert content["content_text"] == stored["content_text"]
            assert not app.openapi().get("security")
            assert not app.openapi().get("components", {}).get("securitySchemes")
            assert all(not operation.get("security") for methods in app.openapi()["paths"].values()
                       for operation in methods.values())
        _, after = await snapshot()
        assert before == after, "source batch changed during read; coordinate a quiescent batch"
        record("alert_auto_http", True, {"sample": sample, "calls": calls,
            "before": before, "after": after, "http_model_calls": 0, "http_writes": 0,
            "transport": "ASGI + actual isolated PostgreSQL; dependency sessions explicitly bound"})
    except Exception as exc:  # noqa: BLE001 -- preserve failed receipt; runner asserts passed after writing it
        record("alert_auto_http", False, {"sample": sample, "error_type": type(exc).__name__,
            "error": str(exc), "calls": calls, "before": before, "after": after})
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = old_context
