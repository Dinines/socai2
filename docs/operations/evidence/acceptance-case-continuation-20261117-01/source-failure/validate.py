"""One ASGI rerun -> current joint dispatcher -> real Case model -> saved HTTP readback."""
import argparse
import asyncio
import hashlib
import json
import os
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from support import ROOT, engine, environment, same, save, snapshot

OUT = Path(__file__).parent


class Http:
    """Record real ASGI receipts; reuse the acceptance CLI's synchronous verifier."""
    def __init__(self, client, loop, output, page_size):
        from acceptance_clients import Http as BusinessHttp
        self.client, self.loop, self.output, self.sequence = client, loop, output, 0
        self.config = SimpleNamespace(page_size=page_size)
        self.pages = BusinessHttp.pages.__get__(self)
        output.mkdir()

    async def call(self, method, path, body=None, *, allowed=(200,)):
        self.sequence += 1
        stem = f"{self.sequence:05d}"
        receipt = {"request": {"method": method, "path": path, "body": body,
            "started_at": datetime.now(timezone.utc).isoformat()}, "transport": "ASGITransport"}
        if method != "GET":
            save(self.output / (stem + ".intent.json"), {"state": "started_outcome_unknown", **receipt})
        response = await self.client.request(method, path, json=body if method != "GET" else None)
        (self.output / (stem + ".body")).write_bytes(response.content)
        value = response.json()
        receipt.update(outcome="returned", response={"status": response.status_code, "body": value,
            "body_file": stem + ".body", "sha256": hashlib.sha256(response.content).hexdigest()})
        save(self.output / (stem + ".json"), receipt)
        assert response.status_code in allowed, (path, response.status_code, value)
        return value

    def request(self, method, path, body=None, *, allowed=(200,)):
        assert method == "GET", "verification_must_be_readonly"
        return asyncio.run_coroutine_threadsafe(self.call(method, path, body, allowed=allowed), self.loop).result()


def source_freeze(config):
    paths = [*sorted((ROOT / "services/api/app/socai2").glob("*.py")),
        *sorted((ROOT / "services/api/app/socai2").glob("*.json")),
        *sorted((ROOT / "services/api/investigation_http").rglob("*.py")),
        ROOT / "services/api/app/services/llm_resolver.py", ROOT / "services/api/app/services/llm_safety.py",
        *sorted(OUT.glob("*.py")), *sorted((ROOT / "tools/testdata").glob("acceptance*.py")),
        *sorted(Path(config["investigation_policy_file"]).parent.glob("*")),
        *[Path(config[k]) for k in ("lifecycle_policy_file", "allocation_policy_file", "run_records_config_file")]]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


async def main(config, mode):
    from acceptance_verify import verify_readback
    from app.socai2.analysis_case_executor import executors
    from app.socai2.analysis_dispatch_config import DispatchPolicy
    from app.socai2.analysis_dispatch_redis import AnalysisQueues
    from app.socai2.analysis_dispatch_runtime import (
        exclusive_process,
        validate_executors,
    )
    from app.socai2.analysis_dispatch_store import DispatchRepository
    from app.socai2.analysis_dispatcher import AnalysisDispatcher
    from app.socai2.analysis_task_policy import AnalysisTaskPolicy
    from app.socai2.analysis_tasks import AnalysisTaskService
    from app.socai2.baseline_context import capture
    from app.socai2.baseline_contracts import Start
    from app.socai2.case_service import CaseService
    from app.socai2.page_reader import PageReadService
    from app.socai2.run_records import RunRecordLimits
    from app.socai2.stage_reader import StageReadService
    from httpx import ASGITransport, AsyncClient
    from investigation_http import dependencies as dep
    from investigation_http.adapters.analysis_submissions import (
        AnalysisSubmissionBackend,
    )
    from investigation_http.adapters.analysis_tasks import AnalysisTaskBackend
    from investigation_http.adapters.identity import BusinessContext
    from investigation_http.adapters.run_records import RunRecordBackend
    from investigation_http.adapters.services import CaseBackend
    from investigation_http.main import app
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import async_sessionmaker

    db_engine = engine(config)
    sessions = async_sessionmaker(db_engine, expire_on_commit=False)
    cases = CaseService(sessions)
    tasks = AnalysisTaskService(sessions, AnalysisTaskPolicy.load())
    tenant, cid, actor = UUID(config["tenant_id"]), UUID(config["case_ids"][0]), UUID(config["actor_id"])
    redis = Redis.from_url(Path(config["redis_url_file"]).read_text().strip(),
        socket_timeout=config["redis_socket_timeout_seconds"], socket_connect_timeout=config["redis_connect_timeout_seconds"])
    policy = DispatchPolicy(**config["dispatch"])
    queues = AnalysisQueues(redis, policy.namespace, tenant)
    handlers = executors({k: config[k] for k in ("investigation_policy_file", "incident", "case")}, tasks)
    validate_executors(handlers)
    dispatcher = AnalysisDispatcher(DispatchRepository(tasks, tenant), queues, policy, handlers)
    original_overrides, original_context = dict(app.dependency_overrides), getattr(app.state, "business_context", None)
    app.state.business_context = BusinessContext(tenant, actor, "Operations analyst")
    page_size = config["directory_page_size"]
    app.dependency_overrides.update({dep.case_service: lambda: CaseBackend(sessions),
        dep.analysis_task_service: lambda: AnalysisTaskBackend(sessions),
        dep.analysis_submission_service: lambda: AnalysisSubmissionBackend(sessions),
        dep.analysis_service: lambda: StageReadService(sessions), dep.page_service: lambda: PageReadService(sessions),
        dep.run_record_service: lambda: RunRecordBackend(sessions, limits=RunRecordLimits(page_size, page_size))})
    receipt, peak = None, 0
    frozen = source_freeze(config)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=config["asgi_base_url"], timeout=config["http_timeout_seconds"]) as client:
            http = Http(client, asyncio.get_running_loop(), OUT / ("http" if mode == "run" else "readback-http"), page_size)
            if mode == "run":
                assert not (OUT / "submission-intent.json").exists(), "submitted_batch_must_not_be_replayed"
                before, _ = await snapshot(db_engine, str(tenant))
                assert len(before["incidents"]) == 2 and len(before["runs"]) == 2 and not before["results"]
                assert all(t["state"] in {"completed", "failed", "skipped"} for t in before["analysis_tasks"])
                horizon = datetime.now(timezone.utc) + timedelta(seconds=config["check_timeout_seconds"])
                assert all(not s["next_check_at"] or datetime.fromisoformat(s["next_check_at"]) > horizon
                           for s in before["analysis_subject_state"]), "periodic_work_outside_this_batch"
                async with cases.transaction(tenant, readonly=True) as store:
                    case = await store.case(cid, lock=False)
                    c1 = await capture(store.db, tenant, cid,
                        Start(expected_scope_revision=case["scope_revision"], operation_key=UUID(config["operation_key"])))
                assert set(c1.alerts) == set(config["alert_ids"])
                assert config["control_incident_id"] not in c1.incidents and len(c1.incidents) == 1
                save(OUT / "preflight-c1.json", c1.model_dump(mode="json"))
                await redis.ping()
                async with AsyncClient(timeout=config["model_preflight_timeout_seconds"], trust_env=False) as model_http:
                    response = await model_http.get(os.environ["OPENAI_BASE_URL"] + "/models",
                        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
                    assert response.status_code == 200
                    save(OUT / "model-readiness.json", {"http_status": response.status_code,
                        "models": response.json(), "generations": 0})
                save(OUT / "source-before.json", frozen)
                save(OUT / "verification-public.json", {k: config[k] for k in
                    ("tenant_id", "alert_ids", "case_ids", "actor_id", "operation_key", "control_incident_id",
                     "dispatch", "case", "incident", "forward", "check_interval_seconds", "check_timeout_seconds", "runtime_overrides")})
                body = {"mode": "rerun", "operation_key": config["operation_key"]}
                path = f"/api/v1/socai2/cases/{cid}/investigations"
                save(OUT / "submission-intent.json", {"state": "started_outcome_unknown", "method": "POST", "path": path, "body": body})
                receipt = await http.call("POST", path, body, allowed=(202,))
                save(OUT / "submission-receipt.json", receipt)
                with exclusive_process(policy.lock_file):
                    await dispatcher.start()
                    end, previous = time.monotonic() + config["check_timeout_seconds"], None
                    while time.monotonic() < end:
                        await dispatcher.tick()
                        peak = max(peak, len(dispatcher.active))
                        assert peak <= policy.max_running_tasks
                        async with tasks.transaction(tenant, readonly=True) as store:
                            row = await store.task(UUID(receipt["task_id"]))
                        progress = {"task_id": receipt["task_id"], "status": row["state"],
                            "running": len(dispatcher.active), "completion_writes_unconfirmed": len(dispatcher.receipts)}
                        if progress != previous:
                            save(OUT / "progress.json", progress)
                            print(json.dumps(progress), flush=True)
                            previous = progress
                        if row["state"] in {"completed", "failed", "skipped", "merged"} and not dispatcher.active and not dispatcher.receipts:
                            break
                        await asyncio.sleep(config["check_interval_seconds"])
                    else:
                        raise TimeoutError("case_validation_deadline")
            else:
                receipt = json.loads((OUT / "submission-receipt.json").read_text())
            rows, hashes = await snapshot(db_engine, str(tenant))
            save(OUT / "saved-records.json", rows)
            result = await asyncio.to_thread(verify_readback, http, rows)
            _, after = await snapshot(db_engine, str(tenant))
            assert hashes == after
            source = json.loads(Path(config["source_snapshot_file"]).read_text())
            unchanged = []
            for table in source:
                if table in {"cases", "analysis_subject_state"}:
                    continue
                actual = {r["id"]: r for r in rows[table]}
                assert all(same(r, actual[r["id"]]) for r in source[table]), table
                unchanged.append(table)
            new_tasks = [t for t in rows["analysis_tasks"] if t["id"] not in {t["id"] for t in source["analysis_tasks"]}]
            assert len(new_tasks) == 1 and new_tasks[0]["id"] == receipt["task_id"]
            case_runs = [r for r in rows["runs"] if r["case_id"] == str(cid)]
            assert len(case_runs) == 1 and len(rows["results"]) == 1
            context = next(a for a in rows["artifacts"] if a["run_id"] == case_runs[0]["id"]
                and a["schema_version"] == "socai2.baseline-context.v1")
            c1 = context["content_json"]
            assert set(c1["alerts"]) == set(config["alert_ids"])
            assert set(c1["incidents"]) == {i["id"] for i in source["incidents"]}
            for iid, item in c1["incidents"].items():
                material = item["analysis_material"]
                assert material["source_run_id"] == source["incident_diagnoses"][0]["source_run_id"]
                original = next(a for a in source["artifacts"] if a["id"] == material["input"]["id"])
                assert original["content_json"]["parent"]["id"] == iid
            assert not dispatcher.active and not dispatcher.receipts and await redis.scard(queues.key("running")) == 0
            assert source_freeze(config) == frozen
            result.update(http_transport="ASGITransport", http_requests=http.sequence, readonly_before=hashes, readonly_after=after,
                new_case_task=new_tasks[0]["id"], new_case_run=case_runs[0]["id"], new_case_result=rows["results"][0]["id"],
                task_state=new_tasks[0]["state"], run_state=case_runs[0]["state"], result_delivery=rows["results"][0]["delivery_state"],
                original_rows_unchanged=unchanged, multi_incident_c1_correct=True, configured_max_running=policy.max_running_tasks,
                observed_peak_running=peak if mode == "run" else None, final_running=0, kafka_sends=0,
                new_alert_or_incident_model_calls=0, active_21_services_changed=False, deployed_21_case_restored=False)
            save(OUT / "validation.json", result)
            save(OUT / "source-after.json", source_freeze(config))
            assert new_tasks[0]["state"] == "completed" and case_runs[0]["state"] == "completed"
            print(json.dumps({k: result[k] for k in ("status", "new_case_run", "http_requests", "steps", "artifacts", "result_delivery")}), flush=True)
    except Exception as exc:
        Path(config["database_profile"]).with_name("driver-error.log").write_text(traceback.format_exc())
        save(OUT / "driver-error.json", {"exception_type": type(exc).__name__,
            "code": getattr(exc, "code", None), "task_receipt_recorded": receipt is not None,
            "note": "Original failure retained; do not repeat the POST or model execution."})
        try:
            rows, hashes = await snapshot(db_engine, str(tenant))
            save(OUT / "saved-records.json", rows)
        except Exception as snapshot_error:  # noqa: BLE001 -- preserve the original driver failure too
            save(OUT / "failure-snapshot-error.json", {"exception_type": type(snapshot_error).__name__})
        raise
    finally:
        for _, future in dispatcher.active.values():
            future.cancel()
        if dispatcher.active:
            await asyncio.gather(*(f for _, f in dispatcher.active.values()), return_exceptions=True)
            dispatcher._collect()
            await dispatcher._flush_receipts()
        save(OUT / "dispatcher-final.json", {"active": len(dispatcher.active), "unconfirmed_receipts": len(dispatcher.receipts),
            "redis_running": await redis.scard(queues.key("running")), "peak_active": peak})
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
        app.state.business_context = original_context
        await redis.aclose()
        await db_engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--mode", choices=("run", "readback"), default="run")
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    environment(cfg)
    asyncio.run(main(cfg, args.mode))
