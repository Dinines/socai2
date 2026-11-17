"""One fresh native alert, common Redis dispatcher, actual A and configured real model."""
import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "services/api"), str(ROOT / "docs/operations")]
from validate import save


async def run(config):
    from app.socai2.analysis_alert_executor import AlertTaskExecutor, executors
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.stage_results import StageResultService
    from read_processing_audit_20261106 import TABLES
    from redis.asyncio import Redis
    from sqlalchemy import text
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tools.testdata.case_io_eval.model_eval import check_route, remote
    from tools.testdata.case_scope_recovery.real_model import Gateway

    out = HERE / config["batch"]
    out.mkdir(exist_ok=False)
    (out / "calls").mkdir()
    cfg = json.loads((ROOT / config["database_profile"]).read_text())
    assert cfg["processing_database"] == config["expected_database"]
    url = URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    admin = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"]})
    engine = create_async_engine(url, hide_parameters=True,
        connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    tenant = uuid4()
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    dispatcher = gateway = None
    result = {"state": "started", "tenant_id": tenant, "model_quality": "not independently scored"}
    save(out / "intent.json", {**result, "config": config, "created_at": datetime.now(UTC),
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in (ROOT / "services/api/app/socai2", ROOT / "services/fusion/app/services", HERE)
            for p in folder.glob("*") if p.suffix in {".py", ".json", ".toml"}},
        "scope": "one new synthetic alert; real PG/Redis/A/model, SSH transport; no production consumer or deployment"})
    try:
        preflight = await asyncio.to_thread(remote, config, {"phase": "preflight", "timeout_seconds": config["preflight_timeout_seconds"]})
        save(out / "preflight.json", preflight)
        check_route(config, preflight)
        async with admin.begin() as db:
            await db.execute(text("""INSERT INTO public.tenants
                (id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES (:id,:name,:slug,'enterprise',true,'{}','{}',now(),now())"""),
                {"id": tenant, "name": "Automatic A real model " + str(tenant), "slug": "a-auto-real-" + str(tenant)})
        process = await asyncio.create_subprocess_exec(sys.executable, str(HERE / "ingress.py"),
            "--config", str(ROOT / config["database_profile"]), "--policy", config["lifecycle_policy_file"],
            "--tenant", str(tenant), "--output", str(out / "ingress.json"),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        output, _ = await process.communicate()
        (out / "ingress.log").write_bytes(output)
        assert process.returncode == 0, "native_ingress_failed"
        ingress = json.loads((out / "ingress.json").read_text())
        aid, tid = UUID(ingress["fused"]["id"]), UUID(ingress["tasks"][0]["id"])
        lifecycle = AnalysisTaskPolicy(**json.loads(Path(config["lifecycle_policy_file"]).read_text()))
        service = AnalysisTaskService(async_sessionmaker(engine, expire_on_commit=False), lifecycle)
        # Verify the release factory with the selected same policy and session pool.
        registered = executors({"investigation_policy_file": str(ROOT / config["investigation_policy"])}, service)
        assert set(registered) == {"alert_triage"} and registered["alert_triage"].service.sessions is service.sessions
        gateway = Gateway({**config, "preflight": preflight}, out / "calls")
        executor = AlertTaskExecutor(StageResultService(service.sessions), gateway_factory=lambda: gateway)
        policy = DispatchPolicy(**{**config["dispatch"],
            "receipt_directory": str(Path(config["dispatch"]["receipt_directory"]) / str(tenant))})
        dispatcher = AnalysisDispatcher(DispatchRepository(service, tenant), AnalysisQueues(redis, policy.namespace, tenant),
            policy, {"alert_triage": executor})
        await dispatcher.start()
        async with asyncio.timeout(config["check_timeout_seconds"]):
            while True:
                await dispatcher.tick()
                task = await service.read_task(tenant, "alert", aid, tid)
                if task["status"] in {"completed", "failed", "skipped"}:
                    break
                await asyncio.sleep(config["check_interval_seconds"])
        save(out / "task.json", task)
        data = {}
        async with service.transaction(tenant, readonly=True) as store:
            for table in (*TABLES, "analysis_tasks", "analysis_attempts", "analysis_subject_state"):
                data[table] = (await store.db.execute(text(
                    "SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM socai2." + table + " t WHERE tenant_id=:tenant"),
                    {"tenant": tenant})).scalar_one()
        exported = out / "export"
        exported.mkdir()
        save(exported / "database.json", data)
        save(exported / "manifest.json", {"schema_version": "socai2.page-export.v1",
            "batch_id": "analysis-alert-auto-20261115-01-real", "tenant_id": tenant, "case_id": None,
            "exported_at": datetime.now(UTC), "table_counts": {k: len(v) for k, v in data.items()},
            "sources": [{"file": "database.json", "sha256": hashlib.sha256((exported / "database.json").read_bytes()).hexdigest()}]})
        result.update(state=task["status"], real_model_calls=gateway.calls,
            counts={k: len(v) for k, v in data.items()}, http_sample={"tenant_id": tenant, "alert_id": aid,
                "task_id": tid, "run_id": task["latest_run_id"]})
        assert len(data["analysis_tasks"]) == 1 and len(data["analysis_attempts"]) == 1 and len(data["runs"]) == 1
        assert not dispatcher.active and not dispatcher.receipts
        print(json.dumps(result, default=str), flush=True)
    finally:
        if dispatcher:
            for _, future in dispatcher.active.values():
                future.cancel()
            if dispatcher.active:
                await asyncio.gather(*(f for _, f in dispatcher.active.values()), return_exceptions=True)
            dispatcher._collect()
            await dispatcher._flush_receipts()
        result["real_model_calls"] = gateway.calls if gateway else 0
        save(out / "result.json", result)
        await redis.aclose()
        await engine.dispose()
        await admin.dispose()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, type=Path)
    args = p.parse_args()
    config = json.loads(args.config.read_text())
    os.environ.update(json.loads((ROOT / config["environment_file"]).read_text()))
    os.environ.update(config["runtime_overrides"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["investigation_policy"])
    os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = config["lifecycle_policy_file"]
    os.environ.pop("SOCAI2_KNOWLEDGE_PROFILE", None)
    asyncio.run(run(config))
