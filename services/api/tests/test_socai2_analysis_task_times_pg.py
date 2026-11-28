"""S5 direct checks over isolated PG/Redis and real TCP HTTP; no gateway/model.

The caller supplies an explicit fresh batch config and private evidence recorder.
All generated rows are retained. This is deliberately not a reusable test framework.
"""
import asyncio
import copy
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import httpx
from app.models import socai2 as m
from app.socai2.analysis_dispatch_config import DispatchPolicy
from app.socai2.analysis_dispatch_redis import AnalysisQueues
from app.socai2.analysis_dispatch_store import DispatchRepository
from app.socai2.analysis_dispatch_types import Material, Outcome
from app.socai2.analysis_dispatcher import AnalysisDispatcher
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_task_store import A, R, S, T
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_store import StoreError, digest, encoded
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker


def date(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value


class ControlledExecutor:
    def __init__(self, service, tenant):
        self.service, self.tenant = service, tenant
        self.materials, self.preparing, self.release_prepare = {}, {}, {}
        self.running, self.release_execute, self.outcomes, self.calls = {}, {}, {}, []
        self.load_errors = {}

    async def load(self, task):
        key = task["id"]
        self.preparing.setdefault(key, asyncio.Event()).set()
        if key in self.release_prepare:
            await self.release_prepare[key].wait()
        if key in self.load_errors:
            raise self.load_errors[key]
        value = copy.deepcopy(self.materials[task["subject_id"]])
        return Material(digest(value), value)

    async def execute(self, context, material):
        task = context.task
        rid, fid, parent, child = (uuid4() for _ in range(4))
        sid = task["subject_id"]
        async with self.service.transaction(self.tenant) as store:
            now = await store.now()
            case = await store.case(sid)
            await store.db.execute(insert(R).values(id=rid, tenant_id=self.tenant, case_id=sid,
                kind="baseline", title="Controlled task timing", purpose="Timing persistence validation",
                trigger="manual", state="pending_update", scope_revision=case["scope_revision"], scope_kind="whole_case"))
            await store.db.execute(insert(m.Artifacts).values(id=fid, tenant_id=self.tenant, case_id=sid,
                run_id=rid, kind="input_snapshot", schema_version="lyc.s5.timing.v1", captured_at=now,
                mime_type="application/json", material_state="complete", source_refs=[], retention={},
                content_json=material.value, sha256=material.digest, size_bytes=len(encoded(material.value))))
            for member in await store.members(sid):
                await store.db.execute(insert(m.RunMembers).values(id=uuid4(), tenant_id=self.tenant,
                    case_id=sid, run_id=rid, alert_id=member))
            await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
                state="running", started_at=now, input_artifact_id=fid, operation_key=str(context.operation_key),
                request_hash=material.digest, executor_version="lyc.s5.controlled.v1"))
            await store.bind_run(context.attempt["id"], rid, input_digest=material.digest)
            # Equal start times deliberately exercise the seq tie-breaker.
            for step, seq, kind, parent_id in ((parent, 1, "stage", None), (child, 2, "tool", parent)):
                await store.db.execute(insert(m.RunSteps).values(id=step, tenant_id=self.tenant, run_id=rid,
                    seq=seq, kind=kind, stage_code="C1", name="Controlled timing step", state="running",
                    started_at=now, parent_step_id=parent_id, input_artifact_id=fid))
        self.calls.append({"task_id": task["id"], "attempt_id": context.attempt["id"],
            "run_id": rid, "parent_step_id": parent, "child_step_id": child, "subject_id": sid})
        self.running.setdefault(task["id"], asyncio.Event()).set()
        if task["id"] in self.release_execute:
            await self.release_execute[task["id"]].wait()
        outcomes = self.outcomes.get(sid, [])
        result = outcomes.pop(0) if outcomes else Outcome("completed")
        if result.outcome != "unknown":
            async with self.service.transaction(self.tenant) as store:
                now = await store.now()
                await store.db.execute(update(m.RunSteps).where(m.RunSteps.tenant_id == self.tenant,
                    m.RunSteps.run_id == rid).values(state=result.outcome, ended_at=now, output_artifact_id=fid))
                await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
                    state=result.outcome, ended_at=now))
        return result


async def run_checks(engine, redis, config, record):
    assert config["allow_real_models"] is False and config["source_prefix"].startswith("lyc")
    tenant = UUID(config["tenant_id"])
    lifecycle = AnalysisTaskPolicy(**json.loads(Path(config["lifecycle_file"]).read_text()))
    service = AnalysisTaskService(async_sessionmaker(engine, expire_on_commit=False), lifecycle)
    repository = DispatchRepository(service, tenant)
    queues = AnalysisQueues(redis, config["namespace"], tenant)
    policy = DispatchPolicy(namespace=config["namespace"], max_running_tasks=1,
        poll_interval_seconds=config["poll_interval_seconds"], execution_timeout_seconds=config["execution_timeout_seconds"],
        replenish_limit=config["replenish_limit"], priorities=tuple(config["priorities"]),
        receipt_directory=config["receipt_directory"], lock_file=config["lock_file"])
    executor = ControlledExecutor(service, tenant)
    dispatcher = AnalysisDispatcher(repository, queues, policy, {"case_investigation": executor})
    timeout = config["control_timeout_seconds"]
    http_calls = []
    client = httpx.AsyncClient(base_url=config["http_base"], timeout=timeout, trust_env=False)

    async def get(path):
        response = await client.get(path)
        http_calls.append({"method": "GET", "path": path, "status": response.status_code,
            "headers": dict(response.headers), "body": response.text})
        assert response.status_code == 200, "tcp_get_failed"
        return response.json()

    async def subject():
        aid, sid = uuid4(), uuid4()
        async with service.transaction(tenant) as store:
            await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant,
                source_namespace=config["source_prefix"], connector_type=config["source_prefix"],
                source_identity_key=str(aid), title="Neutral timing observation"))
            await store.db.execute(insert(m.Cases).values(id=sid, tenant_id=tenant, title="Neutral timing investigation"))
            await store.db.execute(insert(m.CaseAlerts).values(id=uuid4(), tenant_id=tenant, case_id=sid,
                alert_id=aid, membership_source="manual", source_operation_id=uuid4()))
        executor.materials[sid] = {"version": "lyc.s5.timing.v1", "members": [{"alert": {
            "id": str(aid), "source": config["source_prefix"], "connector_type": config["source_prefix"]}}]}
        return sid

    async def submit(sid, intent="check"):
        receipt = await service.submit(tenant, kind="case_investigation", subject_id=sid,
            intent=intent, source="user", operation_key=uuid4())
        tid = receipt["task_id"]
        executor.preparing[tid] = asyncio.Event()
        executor.running[tid] = asyncio.Event()
        return tid

    async def read(sid, tid):
        value = await get(f"/api/v1/socai2/cases/{sid}/analysis-tasks/{tid}")
        async with service.transaction(tenant, readonly=True) as store:
            row = await store.task(tid, lock=False)
            assert date(value["submitted_at"]) == row["submitted_at"]
            assert date(value["first_enqueued_at"]) == row["first_enqueued_at"] if value["first_enqueued_at"] else row["first_enqueued_at"] is None
            assert date(value["last_enqueued_at"]) == row["last_enqueued_at"] if value["last_enqueued_at"] else row["last_enqueued_at"] is None
            attempts = list((await store.db.execute(select(A).where(*store.where(A, A.c.task_id == tid))
                .order_by(A.c.attempt_no))).mappings())
        assert len(value["attempts"]) == len(attempts)
        for actual, expected in zip(value["attempts"], attempts, strict=True):
            assert date(actual["started_at"]) == expected["started_at"]
            assert date(actual["enqueued_at"]) == expected["enqueued_at"] if actual["enqueued_at"] else expected["enqueued_at"] is None
            end = date(value["observed_at"]) if actual["local_state"] == "running" else expected["local_ended_at"]
            expected_seconds = (end - expected["started_at"]).total_seconds() if end else None
            assert actual["timing"]["execution_seconds"] == expected_seconds
        return value

    async def state(sid):
        async with service.transaction(tenant, readonly=True) as store:
            return dict(await store.one(select(S).where(*store.where(S, S.c.subject_type == "case", S.c.subject_id == sid))))

    async def settle():
        if dispatcher.active:
            await asyncio.wait_for(asyncio.gather(*(future for _, future in dispatcher.active.values())), timeout)
        dispatcher._collect()
        await dispatcher._flush_receipts()
        assert not dispatcher.receipts

    async def run(tid):
        await dispatcher.tick()
        await settle()

    async def checkpoint(name, view):
        if not config.get("browser_gate_directory"):
            return
        directory = Path(config["browser_gate_directory"])
        directory.mkdir(parents=True, exist_ok=True)
        (directory / (name + ".json")).write_text(json.dumps(view, default=str, indent=2))
        if name in {"preparing", "running"}:
            async with asyncio.timeout(config["browser_gate_timeout_seconds"]):
                while not (directory / (name + ".release")).exists():
                    await asyncio.sleep(.2)

    try:
        await dispatcher.start()
        sid = await subject()
        tid = await submit(sid)
        value = await read(sid, tid)
        assert value["status"] == "accepted" and not value["attempts"] and value["active_step"] is None
        assert value["first_enqueued_at"] is None and value["last_enqueued_at"] is None
        assert value["timing"]["pending_queue_seconds"] is None
        record("accepted_without_queue_has_null_enqueue", True, value)

        await queues.push(await repository.task(tid))
        await repository.enqueued(tid)
        first = await repository.task(tid)
        await queues.push(first, pending=True)
        await repository.enqueued(tid)
        repeated = await repository.task(tid)
        assert first["submitted_at"] == repeated["submitted_at"]
        assert first["first_enqueued_at"] == repeated["first_enqueued_at"] == repeated["next_attempt_enqueued_at"]
        assert repeated["last_enqueued_at"] >= first["last_enqueued_at"]
        record("repeated_enqueue_preserves_first_and_attempt_origin", True, await read(sid, tid))

        executor.release_prepare[tid] = asyncio.Event()
        executor.release_execute[tid] = asyncio.Event()
        await dispatcher.tick()
        await asyncio.wait_for(executor.preparing[tid].wait(), timeout)
        preparing = await read(sid, tid)
        assert preparing["status"] == "running" and preparing["latest_run_id"] is None
        assert len(preparing["attempts"]) == 1 and preparing["attempts"][0]["local_state"] == "running"
        assert preparing["active_step"] is None and not executor.calls
        assert date(preparing["attempts"][0]["enqueued_at"]) == first["next_attempt_enqueued_at"]
        assert preparing["attempts"][0]["timing"]["queue_seconds"] >= 0
        record("preparation_is_saved_running_attempt_without_run", True, preparing)
        await checkpoint("preparing", preparing)
        executor.release_prepare[tid].set()
        await asyncio.wait_for(executor.running[tid].wait(), timeout)
        running = await read(sid, tid)
        active = running["active_step"]
        assert active["step_id"] == str(executor.calls[-1]["child_step_id"])
        assert active["run_id"] == running["latest_run_id"]
        assert active["elapsed_seconds"] == (date(running["observed_at"]) - date(active["started_at"])).total_seconds()
        step = await get(active["url"])
        assert str(step.get("id", step.get("step_id"))) == active["step_id"]
        record("real_running_child_step_same_observation_and_url", True, {"task": running, "step": step})
        await checkpoint("running", running)
        executor.release_execute[tid].set()
        await settle()
        ended = await read(sid, tid)
        assert ended["status"] == "completed" and ended["active_step"] is None
        assert ended["attempts"][0]["local_ended_at"] is not None
        record("completed_task_keeps_attempt_and_clears_active_step", True, ended)
        await checkpoint("completed", ended)

        before = await state(sid)
        skip = await submit(sid)
        await run(skip)
        skipped = await read(sid, skip)
        after = await state(sid)
        assert skipped["status"] == "skipped" and skipped["reason_code"] == "no_changes"
        assert skipped["latest_run_id"] is None and len(skipped["attempts"]) == 1
        assert skipped["attempts"][0]["local_state"] == "ended" and skipped["attempts"][0]["outcome"] == "completed"
        assert skipped["attempts"][0]["run_id"] is None and len(executor.calls) == 1
        assert all(before[k] == after[k] for k in ("last_completed_attempt_id", "last_normal_completed_at", "next_check_at"))
        record("no_changes_preparation_ended_without_normal_completion", True, {"task": skipped, "before": before, "after": after})
        await checkpoint("skipped", skipped)

        retry_sid = await subject()
        retry = await submit(retry_sid)
        executor.outcomes[retry_sid] = [Outcome("failed", "service_unavailable", "execute", retryable=True), Outcome("completed")]
        await run(retry)
        waiting = await read(retry_sid, retry)
        assert waiting["status"] == "accepted" and waiting["reason_code"] == "retry_scheduled"
        assert waiting["last_enqueued_at"] is not None and waiting["active_step"] is None
        await run(retry)
        retried = await read(retry_sid, retry)
        assert retried["status"] == "completed" and len(retried["attempts"]) == 2
        assert retried["first_enqueued_at"] == waiting["first_enqueued_at"]
        assert date(retried["attempts"][1]["enqueued_at"]) > date(retried["attempts"][0]["enqueued_at"])
        assert retried["attempts"][0] == waiting["attempts"][0]
        record("known_retry_has_new_enqueue_origin_and_retains_prior_attempt", True, {"waiting": waiting, "completed": retried})

        unknown_sid = await subject()
        unknown = await submit(unknown_sid)
        executor.outcomes[unknown_sid] = [Outcome("unknown", "execution_unknown")]
        await run(unknown)
        unknown_view = await read(unknown_sid, unknown)
        assert unknown_view["status"] == "failed" and unknown_view["active_step"] is None
        assert unknown_view["attempts"][0]["outcome"] == "unknown" and unknown_view["attempts"][0]["local_ended_at"]
        async with service.transaction(tenant, readonly=True) as store:
            unknown_run = dict(await store.one(select(R).where(*store.where(R, R.c.id == UUID(unknown_view["latest_run_id"])))))
        assert unknown_run["state"] == "unknown" and unknown_run["ended_at"] is None
        record("local_unknown_end_does_not_fabricate_run_end_or_active_step", True, {"task": unknown_view, "run": unknown_run})
        stopped_before = await state(unknown_sid)
        stopped = await submit(unknown_sid)
        await run(stopped)
        stopped_view = await read(unknown_sid, stopped)
        stopped_after = await state(unknown_sid)
        assert stopped_view["status"] == "skipped" and stopped_view["reason_code"] == "automatic_attempts_stopped"
        assert stopped_view["latest_run_id"] is None and stopped_view["attempts"][0]["outcome"] == "completed"
        assert all(stopped_before[k] == stopped_after[k] for k in ("last_completed_attempt_id", "last_normal_completed_at", "next_check_at", "stopped_task_id"))
        record("automatic_stop_check_does_not_refresh_normal_window", True, {"task": stopped_view, "before": stopped_before, "after": stopped_after})

        failed_sid = await subject()
        failed = await submit(failed_sid)
        executor.load_errors[failed] = StoreError("analysis_subject_busy")
        await run(failed)
        failed_view = await read(failed_sid, failed)
        assert failed_view["status"] == "failed" and failed_view["latest_run_id"] is None
        assert len(failed_view["attempts"]) == 1 and failed_view["attempts"][0]["local_state"] == "ended"
        assert failed_view["attempts"][0]["outcome"] == "failed" and failed_view["active_step"] is None
        assert not dispatcher.active and not dispatcher.receipts
        record("failure_after_preparation_start_ends_actual_attempt_without_requeue", True, failed_view)

        legacy_sid = await subject()
        legacy = await submit(legacy_sid)
        async with service.transaction(tenant) as store:
            await store.db.execute(update(T).where(*store.where(T, T.c.id == legacy)).values(last_enqueued_at=await store.now()))
        await repository.enqueued(legacy)
        legacy_row = await repository.task(legacy)
        assert legacy_row["first_enqueued_at"] is None and legacy_row["last_enqueued_at"] is not None
        async with service.transaction(tenant) as store:
            # Simulates an old in-flight task whose per-attempt enqueue origin was never recorded.
            await store.db.execute(update(T).where(*store.where(T, T.c.id == legacy)).values(next_attempt_enqueued_at=None))
            attempt = await store.start_attempt(legacy)
        legacy_view = await read(legacy_sid, legacy)
        assert legacy_view["attempts"][0]["enqueued_at"] is None
        assert legacy_view["attempts"][0]["timing"]["queue_seconds"] is None
        denied = False
        try:
            async with service.transaction(tenant) as store:
                await store.finish_attempt(attempt["id"], outcome="completed")
        except IntegrityError:
            denied = True
        assert denied
        async with service.transaction(tenant) as store:
            await store.finish_attempt(attempt["id"], outcome="failed", error_code="invalid_input", error_stage="input")
        record("legacy_nulls_preserved_and_arbitrary_completed_without_run_rejected", True, legacy_view)

        page = await get(f"/api/v1/socai2/cases/{sid}/analysis-tasks")
        assert all(item["observed_at"] == page["observed_at"] for item in page["items"])
        record("page_uses_one_database_observation", True, page)
        return {"case_id": str(sid), "completed_task_id": str(tid), "skipped_task_id": str(skip),
            "unknown_case_id": str(unknown_sid), "unknown_task_id": str(unknown),
            "calls": executor.calls, "http_calls": len(http_calls), "model_calls": 0}
    finally:
        for gate in (*executor.release_prepare.values(), *executor.release_execute.values()):
            gate.set()
        if dispatcher.active:
            for _, future in dispatcher.active.values():
                future.cancel()
            await asyncio.gather(*(future for _, future in dispatcher.active.values()), return_exceptions=True)
            dispatcher._collect()
            await dispatcher._flush_receipts()
        record("private_http_evidence", True, http_calls)
        await client.aclose()


async def run_incident_capacity_check(engine, config, record):
    """The new preparation pointer must not hide a stopped I Run's profile."""
    from app.socai2 import analysis_incident_executor as incident_module

    assert not config["allow_real_models"] and config["source_prefix"].startswith("lyc")
    tenant, aid, sid, rid, fid = UUID(config["tenant_id"]), uuid4(), uuid4(), uuid4(), uuid4()
    policy = AnalysisTaskPolicy(**json.loads(Path(config["lifecycle_file"]).read_text()))
    service = AnalysisTaskService(async_sessionmaker(engine, expire_on_commit=False), policy)
    repository = DispatchRepository(service, tenant)
    view = {"members": [{"alert": {"id": str(aid)}}], "change_view": {"material_revision": 1}}
    previous_profile, current_profile = {"max_alerts_per_diagnosis": 1}, {"max_alerts_per_diagnosis": 2}
    old_input = {**copy.deepcopy(view), "capacity_profile": previous_profile}
    async with service.transaction(tenant) as store:
        await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=tenant,
            source_namespace=config["source_prefix"], connector_type=config["source_prefix"],
            source_identity_key=str(aid), title="Neutral capacity observation"))
        await store.db.execute(insert(m.Incidents).values(id=sid, tenant_id=tenant,
            source_namespace=config["source_prefix"], source_incident_id=str(sid), title="Neutral capacity event"))
        await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant,
            incident_id=sid, alert_id=aid, membership_source="manual", correlation_basis={},
            basis_version="lyc.s5.timing.v1", source_operation_id=uuid4()))
    old_task = (await service.submit(tenant, kind="incident_diagnosis", subject_id=sid,
        intent="check", source="user", operation_key=uuid4()))["task_id"]
    async with service.transaction(tenant) as store:
        old_attempt = await store.start_attempt(old_task)
        now = await store.now()
        await store.db.execute(insert(R).values(id=rid, tenant_id=tenant, incident_id=sid,
            kind="incident_diagnosis", title="Controlled stopped capacity Run", purpose="Capacity source verification",
            trigger="manual", state="running", started_at=now, input_artifact_id=fid,
            operation_key=str(uuid4()), request_hash=digest(old_input), executor_version="lyc.s5.controlled.v1"))
        await store.db.execute(insert(m.Artifacts).values(id=fid, tenant_id=tenant, incident_id=sid,
            run_id=rid, kind="input_snapshot", schema_version="lyc.s5.timing.v1", captured_at=now,
            mime_type="application/json", material_state="complete", source_refs=[], retention={},
            content_json=old_input, sha256=digest(old_input), size_bytes=len(encoded(old_input))))
        await store.bind_run(old_attempt["id"], rid, input_digest=digest(view["change_view"]))
        await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
            state="failed", ended_at=await store.now(), stop_reason="capacity_exceeded"))
        await store.finish_attempt(old_attempt["id"], outcome="failed", error_code="capacity_exceeded", error_stage="input")
    current_task = (await service.submit(tenant, kind="incident_diagnosis", subject_id=sid,
        intent="check", source="user", operation_key=uuid4()))["task_id"]
    async with service.transaction(tenant) as store:
        current_attempt = await store.start_attempt(current_task)
        state = dict(await store.one(select(S).where(*store.where(S,
            S.c.subject_type == "incident", S.c.subject_id == sid))))
    assert state["last_attempt_id"] == current_attempt["id"] and current_attempt["run_id"] is None
    assert state["stopped_task_id"] == old_task

    def no_gateway():
        raise AssertionError("capacity_load_must_not_create_gateway")

    executor = incident_module.IncidentTaskExecutor(service, service,
        incident_module.IncidentTaskPolicy(max_alerts_per_diagnosis=2, scan_batch_size=1), gateway_factory=no_gateway)
    source = AsyncMock(return_value=copy.deepcopy(view))
    with patch.object(incident_module, "source_input", source), patch.object(incident_module, "execution_policy"), \
            patch.object(executor, "capacity_profile", return_value=current_profile):
        async with service.transaction(tenant, readonly=True) as store:
            material = await executor.load_in_store(store, sid)
    assert source.await_count == 1 and material.capacity_changed is True
    assert material.digest == state["stopped_input_digest"]
    started = await repository.begin(await repository.task(current_task), material, attempt_id=current_attempt["id"])
    assert started["id"] == current_attempt["id"] and started["run_id"] is None
    async with service.transaction(tenant) as store:
        # Deliberately end the controlled preparation; no new I Run or model is started.
        await store.finish_attempt(current_attempt["id"], outcome="failed", error_code="invalid_input", error_stage="input")
    wire = []
    async with httpx.AsyncClient(base_url=config["http_base"], timeout=config["control_timeout_seconds"], trust_env=False) as client:
        for tid in (old_task, current_task):
            path = f"/api/v1/socai2/incidents/{sid}/analysis-tasks/{tid}"
            response = await client.get(path)
            assert response.status_code == 200
            value = response.json()
            assert value["active_step"] is None and value["status"] == "failed"
            assert value["latest_run_id"] == (str(rid) if tid == old_task else None)
            wire.append({"method": "GET", "path": path, "status": response.status_code, "body": value})
    result = {"incident_id": sid, "alert_id": aid, "old_task_id": old_task, "current_task_id": current_task,
        "run_id": rid, "input_artifact_id": fid, "state_during_preparation": state,
        "new_attempt": current_attempt, "capacity_changed": material.capacity_changed,
        "http": wire, "model_calls": 0, "new_analysis_executed": False}
    record("incident_capacity_uses_stopped_run_despite_new_preparation_pointer", True, result)
    return result
