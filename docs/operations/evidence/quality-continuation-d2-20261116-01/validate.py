"""One fresh Case: real model/PG/Redis, current task entry, read-only HTTP validation."""
import argparse
import asyncio
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "services/api"), str(ROOT / "services/api/tests")]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=lambda v:
        v.model_dump(mode="json") if hasattr(v, "model_dump") else str(v)) + "\n")


def environment(config):
    for key in ("environment_file", "model_environment_file"):
        os.environ.update(json.loads(Path(config[key]).read_text()))
    os.environ.update(config["runtime_overrides"])
    for env, key in (("SOCAI2_INVESTIGATION_POLICY", "investigation_policy_file"),
                     ("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE", "lifecycle_policy_file"),
                     ("SOCAI2_CASE_ALLOCATION_CONFIG_FILE", "allocation_policy_file")):
        os.environ[env] = config[key]
    os.environ.pop("SOCAI2_KNOWLEDGE_PROFILE", None)


async def main(config, out):
    from app.models import socai2 as m
    from app.socai2.analysis_case_executor import executors
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_analysis_model import TenantChatGateway
    from app.socai2.baseline_contracts import Actor
    from app.socai2.baseline_store import F, digest
    from app.socai2.case_contracts import CaseCreate
    from app.socai2.case_service import CaseService
    from redis.asyncio import Redis
    from sqlalchemy import insert, null, select, text, update
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from test_socai2_case_initial_http_pg import snapshot

    out.mkdir(exist_ok=False)
    cfg = json.loads(Path(config["database_profile"]).read_text())
    assert cfg["host"] == "127.0.0.1" and cfg["processing_database"] == "v12_upgrade_dev"
    url = URL.create("postgresql+psycopg", username=cfg["admin"], password=Path(cfg["password_file"]).read_text().strip(),
        host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    admin = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"]})
    engine = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"], "options": "-c role="+cfg["processor"]})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cases, tasks = CaseService(sessions), AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    tenant, actor = uuid4(), uuid4()
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    source_path = Path(config["source_snapshot_file"])
    source = json.loads(source_path.read_text())["rows"]
    result = {"state": "running", "tenant_id": tenant, "actor_id": actor, "database": cfg["processing_database"],
        "database_host": cfg["host"], "database_port": cfg["port"], "substitute_model_calls": 0, "deployment": False,
        "checks": [], "source_snapshot": str(source_path.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "source_content_digest": digest(json.loads(source_path.read_text()))}
    calls, dispatcher = [], None
    save(out / "intent.json", {**result, "input": "prior Kafka fixture originals copied to new isolated identities",
        "policy_file": config["investigation_policy_file"]})

    class RecordingGateway(TenantChatGateway):
        async def complete(self, body, timeout):
            async with cases.transaction(tenant, readonly=True) as store:
                request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                    F.c.run_id == self.run_id, F.c.kind == "model_request"))
                    .order_by(F.c.captured_at.desc()).limit(1))).scalar_one()["payload"]
            assert request["body"] == body
            call = {"stage": request["case_boundary"].get("stage", "C3"), "request": body, "state": "started"}
            calls.append(call)
            save(out / "calls.json", calls)
            print("model call started:", call["stage"], flush=True)
            try:
                response = await super().complete(body, timeout)
                call.update(state="responded", response=response)
                print("model call returned:", call["stage"], response["choices"][0]["finish_reason"], flush=True)
                return response
            except Exception as exc:
                call.update(state="error", error_type=type(exc).__name__)
                raise
            finally:
                save(out / "calls.json", calls)

    try:
        async with admin.begin() as db:
            await db.execute(text("""INSERT INTO public.tenants(id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES(:id,'D2 quality verification',:slug,'enterprise',true,'{}','{}',now(),now())"""),
                {"id": tenant, "slug": "d2-quality-"+str(tenant)})
            await db.execute(text("""INSERT INTO public.users(id,tenant_id,email,username,hashed_password,role,is_active,is_verified,preferences,created_at,updated_at)
                VALUES(:id,:tenant,:email,'D2 quality verification','!','soc_analyst',true,false,'{}',now(),now())"""),
                {"id": actor, "tenant": tenant, "email": str(actor)+"@example.invalid"})
        gateway = RecordingGateway()
        assert await gateway.configure(cases, tenant), "Real model not configured; no Case admitted"
        result["model_route"] = {"base_url": gateway.config.base_url, "model": gateway.model,
            "protocol": gateway.provider, "schema_profile": gateway.schema_profile}
        ids, mapping = [], []
        for old in source["alerts"]:
            aid, mid = uuid4(), uuid4()
            material = next(v for v in source["alert_materials"] if v["id"] == old["latest_material_id"])
            async with cases.transaction(tenant) as store:
                values = {k: old[k] for k in ("title", "description", "source_namespace", "original_vendor",
                    "category", "severity", "severity_raw", "event_time_source", "tags")}
                values["event_time"] = datetime.fromisoformat(old["event_time"]) if old["event_time"] else None
                await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant, source_identity_key=str(aid), **values))
                values = {k: material[k] for k in ("raw_text", "raw_json", "ocsf_json", "detection", "enrichment",
                    "source_scope", "material_state", "sha256", "retention")}
                await store.db.execute(insert(m.AlertMaterials).values(id=mid, tenant_id=tenant, alert_id=aid, revision=1, **values))
                await store.db.execute(update(m.Alerts).where(m.Alerts.id == aid).values(latest_material_id=mid))
                for obj in source["alert_objects"]:
                    if obj["alert_id"] == old["id"]:
                        values = {k: obj[k] for k in ("object_key", "object_type", "source_type", "object_role", "namespace",
                            "raw_value", "normalized_value", "source_path", "attributes", "asset_match_state", "asset_ref", "match_basis")}
                        # A database NULL exported to JSON is not the JSONB null literal.
                        for key in ("asset_ref", "match_basis"):
                            if values[key] is None:
                                values[key] = null()
                        await store.db.execute(insert(m.AlertObjects).values(id=uuid4(), tenant_id=tenant,
                            alert_id=aid, material_id=mid, **values))
            ids.append(aid)
            mapping.append({"source_alert_id": old["id"], "alert_id": aid, "source_material_id": material["id"], "material_id": mid})
        save(out / "source-mapping.json", mapping)
        created = await cases.create_case(tenant, CaseCreate(operation_key=uuid4(), title="登录、进程与外联活动调查",
            alert_ids=ids), actor=Actor(user_id=actor, name="D2 quality verification"))
        cid, tid = created.primary_case_id, created.allocations[0].initial_task.task_id
        result.update(case_id=cid, task_id=tid, alert_ids=ids)
        save(out / "created.json", created)
        admission, _ = await snapshot(cases, tenant)
        assert not admission["runs"] and not admission["analysis_attempts"]
        handlers = executors({k: config[k] for k in ("investigation_policy_file", "incident", "case")}, tasks)
        def factory(claim):
            gateway.run_id = claim.run_id
            return gateway
        handlers["case_investigation"].gateway_factory = factory
        policy = DispatchPolicy(**config["dispatch"])
        dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), AnalysisQueues(redis, policy.namespace, tenant), policy, handlers)
        await dispatcher.start()
        async with asyncio.timeout(config["check_timeout_seconds"]):
            while True:
                await dispatcher.tick()
                current = await tasks.read_task(tenant, "case", cid, tid)
                if current["status"] not in {"accepted", "running"}:
                    break
                await asyncio.sleep(config["check_interval_seconds"])
        save(out / "task.json", current)
        saved, _ = await snapshot(cases, tenant)
        save(out / "database.json", saved)
        assert len(saved["runs"]) == len(saved["analysis_attempts"]) == len(saved["results"]) == 1
        run, attempt, stored = saved["runs"][0], saved["analysis_attempts"][0], saved["results"][0]
        result.update(run_id=run["id"], result_id=stored["id"], task_status=current["status"])
        assert run["state"] == "completed" and attempt["local_state"] == "ended" and attempt["outcome"] == "completed"
        assert calls[0]["stage"] == "C3" and calls[-1]["stage"] == "C6"
        artifacts = {str(a["id"]): a for a in saved["artifacts"]}
        responses = sorted([a for a in artifacts.values() if a["kind"] == "model_response"], key=lambda a: a["captured_at"])
        assert len(responses) == len(calls)
        codes = set()
        for row, call in zip(responses, calls):
            payload = row["content_json"]["payload"]
            assert call["state"] == "responded" and payload["raw"] == call["response"]
            review = payload.get("citation_review")
            if review:
                assert artifacts[review["original_response_artifact_id"]]["content_json"]["raw"] == payload["raw"]
                assert review["original_sha256"] == digest(call["response"]["choices"][0]["message"]["content"])
                assert review["prose_quality"] == "not_checked" and review["conclusion_modified"] is False
                codes.update(i["code"] for i in review["issues"])
        final = json.loads(calls[-1]["response"]["choices"][0]["message"]["content"])
        assert stored["conclusion"] == final["conclusion"]["text"] and stored["conclusion_state"] == final["conclusion"]["state"]
        assert stored["validation_state"] == "accepted" and stored["conclusion_origin"] == "model"
        report = next(a for a in artifacts.values() if a["kind"] == "report_json")["content_json"]
        assert report["delivery"]["conclusion"]["limitations"] == final["conclusion"]["limitations"]
        assert report["citation_review"] == responses[-1]["content_json"]["payload"]["citation_review"]
        result["checks"] += ["one_current_task_one_attempt", "real_C3_through_C6", "originals_and_hashes_preserved",
            "model_conclusion_state_and_limits_retained", "diagnostics_match_saved_report"]
        await http_readback(sessions, cases, tenant, actor, result, saved, out)
        assert not dispatcher.active and not dispatcher.receipts and await redis.scard(dispatcher.queues.key("running")) == 0
        result["checks"].append("slot_released")
        result.update(state="passed", prose_quality="not_checked", diagnosis_codes=sorted(codes))
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
        save(out / "calls.json", calls)
        result["real_model_calls"] = len(calls)
        save(out / "result.json", result)
        save(out / "snapshot.json", (await snapshot(cases, tenant))[0])
        await redis.aclose()
        await engine.dispose()
        await admin.dispose()


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
            report = next(a for a in saved["artifacts"] if a["kind"] == "report_json")["content_json"]
            assert detail["citation_review"] == report["citation_review"]
            for row in saved["artifacts"]:
                content = await get(base + f"/runs/{rid}/artifacts/{row['id']}")
                assert content["content_json"] == row["content_json"] and content["content_text"] == row["content_text"]
        _, after = await snapshot(cases, tenant)
        assert before == after
        result.update(http_gets=len(replies), before_http=before, after_http=after)
        result["checks"] += ["HTTP_values_equal_saved_result_originals_diagnostics", "HTTP_read_does_not_write"]
    finally:
        save(out / "http.json", replies)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state.business_context = context


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    configuration = json.loads(args.config.read_text())
    environment(configuration)
    asyncio.run(main(configuration, args.output))
