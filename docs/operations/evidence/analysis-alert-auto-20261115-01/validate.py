"""Bounded PG/Redis validation using the real A executor and controlled model replies."""
import argparse
import asyncio
import json
import os
import re
import sys
import traceback
from pathlib import Path
from uuid import UUID, uuid4, uuid5

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests")]


def save(path, value):
    path.write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2) + "\n")


async def run(args, config):
    import httpx
    from app.models import socai2 as m
    from app.socai2.analysis_alert_executor import AlertTaskExecutor
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.model_errors import ModelCallError, provider_error
    from app.socai2.stage_results import StageResultService
    from redis.asyncio import Redis
    from sqlalchemy import select, text
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from test_socai2_alert_basic_executor import Gateway

    out = HERE / args.batch
    out.mkdir(exist_ok=False)
    cfg = json.loads((ROOT / config["database_profile"]).read_text())
    url = URL.create("postgresql+psycopg", username=cfg["admin"],
        password=Path(cfg["password_file"]).read_text().strip(), host=cfg["host"], port=cfg["port"], database=cfg["processing_database"])
    admin = create_async_engine(url, hide_parameters=True, connect_args={"sslmode": config["sslmode"]})
    engine = create_async_engine(url, hide_parameters=True,
        connect_args={"sslmode": config["sslmode"], "options": "-c role=" + cfg["processor"]})
    tenant = uuid4()
    result = {"tenant_id": tenant, "checks": [], "model": "controlled replies; real A executor and PG queries", "state": "running"}
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip())
    dispatcher = None
    try:
        async with admin.begin() as db:
            await db.execute(text("""INSERT INTO public.tenants
                (id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES (:id,:name,:slug,'enterprise',true,'{}','{}',now(),now())"""),
                {"id": tenant, "name": "Alert automatic validation " + str(tenant), "slug": "alert-auto-" + str(tenant)})
        policy = AnalysisTaskPolicy(**json.loads(Path(config["lifecycle_policy_file"]).read_text()))
        service = AnalysisTaskService(async_sessionmaker(engine, expire_on_commit=False), policy)
        stage = StageResultService(service.sessions)
        repository = DispatchRepository(service, tenant)
        dispatch_policy = DispatchPolicy(**{**config["dispatch"],
            "receipt_directory": str(Path(config["dispatch"]["receipt_directory"]) / str(tenant))})
        queues = AnalysisQueues(redis, dispatch_policy.namespace, tenant)
        behaviors, calls = {}, []

        async def rows(table):
            async with service.transaction(tenant, readonly=True) as s:
                return [dict(x) for x in (await s.db.execute(select(table).where(table.c.tenant_id == tenant))).mappings()]

        class CheckedGateway(Gateway):
            async def complete(self, body, timeout):
                attempts = [x for x in await rows(m.AnalysisAttempts.__table__) if x["local_state"] == "running"]
                assert len(attempts) == 1
                attempt = attempts[0]
                run = next(x for x in await rows(m.Runs.__table__) if x["id"] == attempt["run_id"])
                artifacts = await rows(m.Artifacts.__table__)
                assert run["state"] == "running" and run["input_artifact_id"] == attempt["input_artifact_id"]
                assert attempt["input_digest"] and attempt["policy_artifact_id"]
                assert any(x["id"] == attempt["input_artifact_id"] for x in artifacts)
                assert any(x["id"] == attempt["policy_artifact_id"] for x in artifacts)
                calls.append({"task_id": attempt["task_id"], "run_id": run["id"], "attempt_no": attempt["attempt_no"],
                    "input_artifact_id": run["input_artifact_id"], "request": body})
                behavior = behaviors.get(run["alert_id"])
                if behavior == "read_timeout" or (behavior == "connect_timeout" and attempt["attempt_no"] == 1):
                    error = httpx.ReadTimeout("controlled") if behavior == "read_timeout" else httpx.ConnectTimeout("controlled")
                    raise ModelCallError(provider_error(error, None))
                ids = re.findall(r"\[(N\d+_S\d+)｜原始记录\]", body["messages"][1]["content"])
                assert ids
                answer = {"id": "controlled-automatic-A", "choices": [{"finish_reason": "stop", "message": {
                    "content": json.dumps({"verdict": "needs_review", "confidence": .3,
                        "rationale": "Synthetic process-start observation; authorization remains unknown. The command is observed; successful enumeration is not established.",
                        "evidence_ids": ids[:2], "recommendations": []})}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 60, "total_tokens": 160}}
                calls[-1]["response"] = answer
                return answer

        executor = AlertTaskExecutor(stage, gateway_factory=CheckedGateway)
        dispatcher = AnalysisDispatcher(repository, queues, dispatch_policy, {"alert_triage": executor})
        await dispatcher.start()

        async def ingress(name, *, replay=None, fail=False, incident=None):
            path = out / (name + ".json")
            argv = [sys.executable, str(HERE / "ingress.py"), "--config", str(ROOT / config["database_profile"]),
                "--policy", config["lifecycle_policy_file"], "--tenant", str(tenant), "--output", str(path)]
            if replay:
                argv += ["--replay", str(replay)]
            if incident:
                argv += ["--incident", str(incident)]
            if fail:
                argv += ["--fail-registration"]
            process = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            output, _ = await process.communicate()
            (out / (name + ".log")).write_bytes(output)
            assert process.returncode == 0, name + " ingress failed (see retained log)"
            return path, json.loads(path.read_text())

        async def finish(expected):
            async with asyncio.timeout(config["check_timeout_seconds"]):
                while True:
                    await dispatcher.tick()
                    tasks = await rows(m.AnalysisTasks.__table__)
                    if len(tasks) == expected and all(t["state"] in {"completed", "failed", "skipped"} for t in tasks):
                        return tasks
                    await asyncio.sleep(config["check_interval_seconds"])

        def check(name):
            result["checks"].append(name)
            print(name, flush=True)

        incident = uuid4()
        p1, a1 = await ingress("A1", incident=incident)
        _, a2 = await ingress("A2", incident=incident)
        _, replay = await ingress("A1-replay", replay=p1)
        assert a1["tasks"] == replay["tasks"] and a1["materials"] == replay["materials"]
        check("new alert and exactly one initial task commit together; replay preserves material and task")
        await ingress("rollback", fail=True)
        assert len(await rows(m.AnalysisTasks.__table__)) == 2
        check("task registration failure rolls back alert, material and task")
        aid = UUID(a1["fused"]["id"])
        receipt = await service.submit(tenant, kind="alert_triage", subject_id=aid, intent="initial", source="ingress",
            operation_key=uuid5(aid, "socai2.alert.initial-analysis.v1"))
        assert str(receipt["task_id"]) == a1["tasks"][0]["id"]
        check("ingress operation fingerprint matches core task acceptance")
        assert all(t["state"] == "completed" for t in await finish(2))
        assert len(calls) == 2
        check("two new alerts execute through real A with frozen input, policy and attempt binding before model call")
        before = await rows(m.Runs.__table__)
        await ingress("A1-completed-replay", replay=p1)
        _, a3 = await ingress("A3", incident=incident)
        assert all(t["state"] == "completed" for t in await finish(3))
        assert len(calls) == 3 and len(await rows(m.Runs.__table__)) == len(before) + 1
        check("new member executes only itself; completed alert replay never re-triages")
        _, retry = await ingress("retry")
        behaviors[UUID(retry["fused"]["id"])] = "connect_timeout"
        await finish(4)
        retry_task = await service.read_task(tenant, "alert", UUID(retry["fused"]["id"]), UUID(retry["tasks"][0]["id"]))
        assert retry_task["status"] == "completed" and retry_task["retry_count"] == 1
        assert [x["outcome"] for x in retry_task["attempts"]] == ["failed", "completed"]
        assert len({x["run_id"] for x in retry_task["attempts"]}) == 2
        check("known pre-send failure retries once on same task with separate preserved Runs")
        _, unknown = await ingress("unknown")
        behaviors[UUID(unknown["fused"]["id"])] = "read_timeout"
        _, tail = await ingress("after-unknown")
        await finish(6)
        stopped = await service.read_task(tenant, "alert", UUID(unknown["fused"]["id"]), UUID(unknown["tasks"][0]["id"]))
        assert stopped["status"] == "failed" and stopped["retry_count"] == 0 and len(stopped["attempts"]) == 1
        old_run = next(x for x in await rows(m.Runs.__table__) if x["id"] == stopped["latest_run_id"])
        assert old_run["state"] == "unknown" and old_run["ended_at"] is None and stopped["ended_at"]
        assert (await service.read_task(tenant, "alert", UUID(tail["fused"]["id"]), UUID(tail["tasks"][0]["id"])))["status"] == "completed"
        check("read timeout releases local slot without retry; next alert completes; old unknown stays truthful")
        data = {name: await rows(getattr(m, model).__table__) for name, model in {
            "alerts": "Alerts", "alert_materials": "AlertMaterials", "alert_assessments": "AlertAssessments",
            "incidents": "Incidents", "incident_alerts": "IncidentAlerts", "alert_objects": "AlertObjects",
            "analysis_tasks": "AnalysisTasks", "analysis_attempts": "AnalysisAttempts",
            "analysis_subject_state": "AnalysisSubjectState", "runs": "Runs", "steps": "RunSteps", "artifacts": "Artifacts"}.items()}
        for alert in data["alerts"]:
            if alert["id"] == UUID(unknown["fused"]["id"]):
                assert alert["latest_triage_id"] is None
            else:
                assert alert["latest_triage_id"] and alert["latest_explanation_id"]
        assert all(t["kind"] == "alert_triage" for t in data["analysis_tasks"])
        assert all(r["kind"] == "alert_basic" for r in data["runs"])
        check("saved triage and explanation readable; no I/Case execution introduced")
        result.update(state="passed", counts={k: len(v) for k, v in data.items()}, model_calls=len(calls),
            http_sample={"tenant_id": tenant, "alert_id": aid, "task_id": receipt["task_id"],
                "run_id": next(x["id"] for x in data["runs"] if x["alert_id"] == aid)})
        save(out / "database.json", data)
    except Exception:
        result.update(state="failed", error=traceback.format_exc())
        raise
    finally:
        save(out / "result.json", result)
        if "calls" in locals():
            save(out / "model-io.json", calls)
        if dispatcher:
            for _, future in dispatcher.active.values():
                future.cancel()
            if dispatcher.active:
                await asyncio.gather(*(f for _, f in dispatcher.active.values()), return_exceptions=True)
            dispatcher._collect()
            await dispatcher._flush_receipts()
        await redis.aclose()
        await engine.dispose()
        await admin.dispose()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--batch", required=True)
    args = p.parse_args()
    config = json.loads(args.config.read_text())
    os.environ.update(json.loads((ROOT / config["environment_file"]).read_text()))
    os.environ.update(config["runtime_overrides"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["investigation_policy"])
    os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"] = config["lifecycle_policy_file"]
    os.environ.pop("SOCAI2_KNOWLEDGE_PROFILE", None)
    asyncio.run(run(args, config))
