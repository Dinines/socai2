"""D4a unique isolated A/I batch: two real generations, then labelled truncations."""
import argparse
import asyncio
import copy
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "services/api")]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=lambda v:
        v.model_dump(mode="json") if hasattr(v, "model_dump") else str(v)) + "\n")


def environment(config):
    for key in ("environment_file", "model_environment_file"):
        os.environ.update(json.loads(Path(config[key]).read_text()))
    os.environ.update(config["runtime_overrides"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = config["investigation_policy_file"]
    os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = config["lifecycle_policy_file"]
    os.environ["SOCAI2_CASE_ALLOCATION_CONFIG_FILE"] = config["allocation_policy_file"]
    os.environ.pop("SOCAI2_KNOWLEDGE_PROFILE", None)


async def snapshot(service, tenant):
    from app.models import socai2 as m
    from app.socai2.baseline_store import digest
    from sqlalchemy import select
    tables = (m.Alerts, m.AlertMaterials, m.AlertObjects, m.AlertAssessments, m.Incidents, m.IncidentAlerts,
              m.IncidentDiagnoses, m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState,
              m.Runs, m.RunSteps, m.Artifacts)
    rows, hashes = {}, {}
    async with service.transaction(tenant, readonly=True) as store:
        for model in tables:
            table = model.__table__
            values = [dict(r) for r in (await store.db.execute(select(table).where(table.c.tenant_id == tenant)
                      .order_by(*table.primary_key.columns))).mappings()]
            # Encode timestamps/Decimal/UUID exactly as the evidence export.
            rows[table.name] = json.loads(json.dumps(values, default=str))
            hashes[table.name] = {"count": len(values), "sha256": digest(rows[table.name])}
    return rows, hashes


async def http_readback(sessions, service, tenant, actor, records, saved, out):
    from app.socai2.baseline_store import digest
    from app.socai2.page_reader import PageReadService
    from app.socai2.stage_reader import StageReadService
    from httpx import ASGITransport, AsyncClient
    from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
    from investigation_http.adapters.identity import BusinessContext
    from investigation_http.adapters.run_records import RunRecordBackend
    from investigation_http.dependencies import (
        analysis_service,
        analysis_task_service,
        page_service,
        run_record_service,
    )
    from investigation_http.main import app
    overrides, prior_context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    replies, directories = [], []
    _, before = await snapshot(service, tenant)
    try:
        app.state.business_context = BusinessContext(tenant, actor, "D4 verification")
        app.dependency_overrides.update({analysis_task_service: lambda: AnalysisTaskBackend(sessions),
            analysis_service: lambda: StageReadService(sessions), page_service: lambda: PageReadService(sessions),
            run_record_service: lambda: RunRecordBackend(sessions)})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated.local") as client:
            async def get(path):
                response = await client.get(path)
                value = response.json()
                replies.append({"method": "GET", "path": path, "status": response.status_code, "body": value})
                save(out / "http.json", replies)
                assert response.status_code == 200, (path, response.status_code)
                return value
            for entry in records:
                base = f"/api/v1/socai2/{entry['subject_type']}s/{entry['subject_id']}"
                task = await get(base + f"/analysis-tasks/{entry['task_id']}")
                assert len(task["attempts"]) == 1
                run_url = task["attempts"][0]["run_url"]
                detail = await get(run_url)
                assert detail["run"]["id"] == entry["run_id"]
                trace = await get(run_url + "/trace")
                found = {}
                for directory in ("steps", "artifacts"):
                    rows, cursor = [], None
                    while True:
                        query = {"limit": 5}
                        if cursor:
                            query["cursor"] = cursor
                        page = await get(trace[directory + "_url"] + "?" + urlencode(query))
                        rows += page["items"]
                        cursor = page.get("next_cursor")
                        if not cursor:
                            break
                    expected = [r for r in saved["run_steps" if directory == "steps" else "artifacts"] if r["run_id"] == entry["run_id"]]
                    assert {r["id"] for r in rows} == {r["id"] for r in expected}
                    found[directory] = len(rows)
                    if directory == "artifacts":
                        by_id = {r["id"]: r for r in expected}
                        for row in rows:
                            body = await get(row["content_url"])
                            assert body["availability"] == "available"
                            stored = by_id[row["id"]]
                            assert body["metadata"]["id"] == row["id"]
                            assert body["content_json"] == stored["content_json"]
                            assert digest(body["content_json"]) == stored["sha256"]
                directories.append({"run_id": entry["run_id"], **found})
        _, after = await snapshot(service, tenant)
        assert before == after
        return {"http_gets": len(replies), "directories": directories, "before": before, "after": after}
    finally:
        save(out / "http.json", replies)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = prior_context


async def main(config, out):
    from app.models import socai2 as m
    from app.socai2.ai_stage_delivery import selection
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_incident_executor import executors
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_analysis_model import TenantChatGateway
    from app.socai2.baseline_store import digest
    from app.socai2.closed_json_units import read_units
    from app.socai2.stage_delivery import VERSION, validate_sources
    from app.socai2.stage_results import F, StageResultService
    from redis.asyncio import Redis
    from sqlalchemy import insert, null, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    out.mkdir(exist_ok=False)
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["host"] == "127.0.0.1" and cfg["processing_database"] == "v12_upgrade_dev"
    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=Path(cfg["password_file"]).read_text().strip(),
        host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    admin = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"]})
    engine = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service, tasks = StageResultService(sessions), AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    tenant, actor, iid = uuid4(), uuid4(), uuid4()
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    source_path = Path(config["source_snapshot_file"])
    source = json.loads(source_path.read_text())["rows"]
    calls, records, dispatcher = [], [], None
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor, "incident_id": iid,
        "database": cfg["processing_database"], "model_route": "current aisoc-investigation",
        "deployment": False, "new_kafka_messages": 0, "case_execution": False, "checks": []}
    save(out / "intent.json", {**result, "fresh_real_model_limit": 2, "controlled_reply_limit": 3,
        "source_snapshot": str(source_path.relative_to(ROOT)), "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "policy_file": config["investigation_policy_file"], "policy_sha256": hashlib.sha256(Path(config["investigation_policy_file"]).read_bytes()).hexdigest()})
    active_mode, mother, last_request = "real", {}, {}

    class Gateway(TenantChatGateway):
        async def complete(self, body, timeout):
            async with service.transaction(tenant, readonly=True) as store:
                row = await store.one(select(F).where(*store.where(F, F.c.kind == "model_request"))
                                     .order_by(F.c.captured_at.desc()).limit(1))
            request = row["content_json"]
            assert request["body"] == body
            stage = "A" if "alert_boundary" in request else "I"
            call = {"stage": stage, "mode": active_mode, "state": "started", "request_artifact_id": str(row["id"]),
                    "run_id": str(row["run_id"]), "request": body}
            calls.append(call)
            save(out / "calls.json", calls)
            print("call started", stage, active_mode, flush=True)
            try:
                if active_mode == "real":
                    assert sum(c["mode"] == "real" for c in calls) <= 2
                    payload = await super().complete(body, timeout)
                    mother[stage], last_request[stage] = copy.deepcopy(payload), request
                else:
                    payload = copy.deepcopy(mother[stage])
                    original = payload["choices"][0]["message"]["content"]
                    if active_mode == "empty":
                        cut = 0
                    else:
                        # Select an actual closed unit boundary from the new real reply.
                        # This is fixture construction, not the acceptance oracle.
                        units = read_units(original, **selection(stage))["units"]
                        unit = next(u for u in units if u["path"] == ("$.rationale" if stage == "A" else "$.members[0]"))
                        cut = unit["value_span"][1]
                    payload["choices"][0]["message"]["content"] = original[:cut]
                    payload["choices"][0]["finish_reason"] = "length"
                    call.update(mother_response_sha256=digest(mother[stage]), cut_offset=cut,
                        mother_request_artifact_id=next(c["request_artifact_id"] for c in calls if c["stage"] == stage and c["mode"] == "real"),
                        current_source_map=request["source_map"], mother_source_map=last_request[stage]["source_map"],
                        usage_note="controlled fixture: recorded usage copied from mother; not a new model charge")
                call.update(state="responded", response=payload)
                print("call returned", stage, active_mode, payload["choices"][0]["finish_reason"], flush=True)
                return payload
            except Exception as exc:
                call.update(state="error", error_type=type(exc).__name__)
                raise
            finally:
                save(out / "calls.json", calls)

    try:
        async with admin.begin() as db:
            await db.execute(text("""INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES(:id,'D4 A/I verification',:slug,'enterprise',true,'{}','{}',now(),now())"""),
                {"id": tenant, "slug": "d4-ai-" + str(tenant)})
            await db.execute(text("""INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
                VALUES(:id,:tenant,:email,'D4 verification','!','soc_analyst',true,false,'{}',now(),now())"""),
                {"id": actor, "tenant": tenant, "email": str(actor) + "@example.invalid"})
        ids, mapping = [], []
        async with service.transaction(tenant) as store:
            await store.db.execute(insert(m.Incidents).values(id=iid, tenant_id=tenant, source_namespace="d4-received",
                source_incident_id=str(iid), title="登录、进程与外联活动", description="关联记录需进一步核实。", handling_status="new"))
            for old in source["alerts"]:
                aid, mid = uuid4(), uuid4()
                material = next(v for v in source["alert_materials"] if v["id"] == old["latest_material_id"])
                values = {k: old[k] for k in ("title", "description", "source_namespace", "original_vendor", "category", "severity", "severity_raw", "event_time_source", "tags")}
                values["event_time"] = datetime.fromisoformat(old["event_time"]) if old["event_time"] else None
                await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant, source_identity_key=str(aid), **values))
                values = {k: material[k] for k in ("raw_text", "raw_json", "ocsf_json", "detection", "enrichment", "source_scope", "material_state", "sha256", "retention")}
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid, revision=1, **values))
                await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
                for obj in source["alert_objects"]:
                    if obj["alert_id"] != old["id"]:
                        continue
                    values = {k: obj[k] for k in ("object_key", "object_type", "source_type", "object_role", "namespace", "raw_value", "normalized_value", "source_path", "attributes", "asset_match_state", "asset_ref", "match_basis")}
                    for key in ("asset_ref", "match_basis"):
                        if values[key] is None:
                            values[key] = null()
                    await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant, alert_id=aid, material_id=mid, **values))
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant, incident_id=iid, alert_id=aid,
                    membership_source="manual", correlation_basis={"reason": "同一活动的关联记录"}, basis_version="v1", source_operation_id=uuid4()))
                ids.append(aid)
                mapping.append({"source_alert_id": old["id"], "alert_id": aid, "source_material_id": material["id"], "material_id": mid})
        save(out / "source-mapping.json", mapping)
        handlers = executors({k: config[k] for k in ("investigation_policy_file", "incident")}, tasks)
        handlers["alert_triage"].gateway_factory = Gateway
        handlers["incident_diagnosis"].gateway_factory = Gateway
        policy = DispatchPolicy(**config["dispatch"])
        dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), AnalysisQueues(redis, policy.namespace, tenant), policy, handlers)
        await dispatcher.start()

        async def run(kind, subject, mode, intent):
            nonlocal active_mode
            active_mode = mode
            accepted = await tasks.submit(tenant, kind=kind, subject_id=subject, intent=intent,
                source="ingress" if kind == "alert_triage" else "user", operation_key=uuid4())
            before, _ = await snapshot(service, tenant)
            assert not any(a["task_id"] == str(accepted["task_id"]) for a in before["analysis_attempts"])
            entry = {**accepted, "mode": mode, "status_before_execution": "accepted"}
            records.append(entry)
            save(out / "tasks.json", records)
            async with asyncio.timeout(config["check_timeout_seconds"]):
                while True:
                    await dispatcher.tick()
                    current = await tasks.read_task(tenant, accepted["subject_type"], subject, accepted["task_id"])
                    if current["status"] not in {"accepted", "running"}:
                        break
                    await asyncio.sleep(config["check_interval_seconds"])
            assert len(current["attempts"]) == 1
            entry.update(run_id=str(current["attempts"][0]["run_id"]), status=current["status"], task=current)
            save(out / "tasks.json", records)
            saved, _ = await snapshot(service, tenant)
            save(out / "checkpoint.json", saved)
            artifacts = {a["id"]: a for a in saved["artifacts"]}
            receipts = [a for a in artifacts.values() if a["run_id"] == entry["run_id"] and a["schema_version"] == VERSION]
            assert len(receipts) == 1, (entry, current)
            receipt = receipts[0]["content_json"]
            validate_sources(receipt, {aid: a["content_json"] for aid, a in artifacts.items()})
            entry.update(delivery=receipt["delivery"]["state"], retained_paths=[u["path"] for u in receipt["retained_units"]],
                         receipt_artifact_id=receipts[0]["id"])
            assert receipt["execution"]["local_state"] == "ended"
            assert not dispatcher.active and not dispatcher.receipts
            assert await redis.scard(dispatcher.queues.key("running")) == 0
            return saved, entry

        saved, first = await run("alert_triage", ids[0], "real", "initial")
        assert first["status"] == "completed", first
        saved, original_i = await run("incident_diagnosis", iid, "real", "initial")
        assert original_i["status"] == "completed", original_i
        initial_pointer = saved["incidents"][0]["latest_diagnosis_id"]
        iinput = next(a["content_json"] for a in saved["artifacts"] if a["run_id"] == original_i["run_id"] and a["kind"] == "input_snapshot")
        assert len([v for v in iinput["triage_validation"].values() if v["usable"]]) == 1
        assert all("tenant_uid" not in json.dumps(call["request"]["messages"]) for call in calls)
        result["checks"] += ["new_real_A_and_I_saved", "I_uses_one_usable_A_and_other_raw_alerts", "models_do_not_receive_tenant_uid"]
        saved, partial_i = await run("incident_diagnosis", iid, "partial", "rerun")
        assert partial_i["status"] == "failed" and partial_i["delivery"] == "partial"
        assert "$.members[0]" in partial_i["retained_paths"]
        assert saved["incidents"][0]["latest_diagnosis_id"] == initial_pointer
        saved, none_i = await run("incident_diagnosis", iid, "empty", "rerun")
        assert none_i["status"] == "failed" and none_i["delivery"] == "none" and not none_i["retained_paths"]
        assert saved["incidents"][0]["latest_diagnosis_id"] == initial_pointer
        # A's second subject has no prior triage and is an independent initial task.
        saved, partial_a = await run("alert_triage", ids[1], "partial", "initial")
        assert partial_a["status"] == "failed" and partial_a["delivery"] == "partial"
        assert next(a for a in saved["alerts"] if a["id"] == str(ids[1]))["latest_triage_id"] is None
        result["checks"] += ["closed_I_member_retained_partial", "empty_I_none_receipt", "failed_same_input_keeps_prior_usable_I", "A_partial_rationale_no_invented_verdict", "all_slots_released"]
        save(out / "database.json", saved)
        save(out / "tasks.json", records)
        result.update(await http_readback(sessions, service, tenant, actor, records, saved, out))
        result["checks"].append("HTTP_directories_originals_receipts_equal_saved")
        result.update(state="passed", steps=len(saved["run_steps"]), artifacts=len(saved["artifacts"]),
                      tasks=len(saved["analysis_tasks"]), runs=len(saved["runs"]))
    except Exception as exc:
        result.update(state="failed", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        if dispatcher:
            for _, future in dispatcher.active.values():
                future.cancel()
            if dispatcher.active:
                await asyncio.gather(*(f for _, f in dispatcher.active.values()), return_exceptions=True)
            dispatcher._collect()
            await dispatcher._flush_receipts()
        result.update(real_model_calls=sum(c["mode"] == "real" for c in calls),
            controlled_responses=sum(c["mode"] != "real" for c in calls))
        save(out / "result.json", result)
        save(out / "snapshot.json", (await snapshot(service, tenant))[0])
        await redis.aclose()
        await engine.dispose()
        await admin.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    environment(config)
    asyncio.run(main(config, args.output))
