"""Bounded queue checks: real isolated PG/Redis, retained synthetic Runs, no model calls."""
import asyncio
import copy
import json
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import httpx
from app.models import socai2 as m
from app.socai2.analysis_dispatch_config import DispatchPolicy
from app.socai2.analysis_dispatch_redis import AnalysisQueues
from app.socai2.analysis_dispatch_store import DispatchRepository
from app.socai2.analysis_dispatch_types import ExecutionFailure, Material, Outcome
from app.socai2.analysis_dispatcher import AnalysisDispatcher, AttemptContext
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_task_store import R
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_store import digest, encoded
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[3]
KINDS = {"case": "case_investigation", "alert": "alert_triage", "incident": "incident_diagnosis"}


class ClockService(AnalysisTaskService):
    @asynccontextmanager
    async def transaction(self, tenant_id, *, readonly=False):
        async with super().transaction(tenant_id, readonly=readonly) as store:
            async def now():
                return self.clock
            store.now = now
            yield store


class ControlledExecutor:
    def __init__(self, harness):
        self.h = harness
        self.materials, self.gates, self.started, self.behavior, self.calls, self.load_errors = {}, {}, {}, {}, [], {}

    async def load(self, task):
        if task["subject_id"] in self.load_errors:
            raise self.load_errors[task["subject_id"]]
        value = copy.deepcopy(self.materials[task["subject_id"]])
        return Material(digest(value), value)

    async def execute(self, context, material):
        task, attempt, h = context.task, context.attempt, self.h
        rid, fid, st = uuid4(), uuid4(), task["subject_type"]
        sid = task["subject_id"]
        async with h.service.transaction(h.tenant) as store:
            now = await store.now()
            values = {"id": rid, "tenant_id": h.tenant, st + "_id": sid,
                "kind": {"case": "baseline", "alert": "alert_basic", "incident": "incident_diagnosis"}[st],
                "title": "Synthetic dispatcher validation", "purpose": "Controlled executor, no model", "trigger": "manual"}
            if st == "case":
                case = await store.case(sid)
                values.update(state="pending_update", scope_revision=case["scope_revision"], scope_kind="whole_case")
            else:
                values.update(state="running", started_at=now, input_artifact_id=fid,
                    operation_key=str(context.operation_key), request_hash=material.digest, executor_version="dispatch-fixture.v1")
            await store.db.execute(insert(R).values(**values))
            await store.db.execute(insert(m.Artifacts).values(id=fid, tenant_id=h.tenant, run_id=rid,
                **{st + "_id": sid}, kind="input_snapshot", schema_version="dispatch-fixture.v1",
                mime_type="application/json", captured_at=now, material_state="complete", source_refs=[], retention={},
                content_json=material.value, sha256=material.digest, size_bytes=len(encoded(material.value))))
            if st == "case":
                for member in await store.members(sid):
                    await store.db.execute(insert(m.RunMembers).values(id=uuid4(), tenant_id=h.tenant,
                        case_id=sid, run_id=rid, alert_id=member))
                await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
                    state="running", started_at=now, input_artifact_id=fid, operation_key=str(context.operation_key),
                    request_hash=material.digest, executor_version="dispatch-fixture.v1"))
            await store.bind_run(attempt["id"], rid, input_digest=material.digest)
        self.calls.append({"task_id": task["id"], "subject_id": sid, "run_id": rid, "artifact_id": fid,
            "attempt_id": attempt["id"], "operation_key": context.operation_key, "input": material.value})
        self.started[task["id"]].set()
        if sid in self.gates:
            await self.gates[sid].wait()
        result = self.behavior.get(sid, Outcome("completed"))
        if isinstance(result, Exception):
            raise result
        if result.outcome == "completed":
            async with h.service.transaction(h.tenant) as store:
                await store.db.execute(update(R).where(*store.where(R, R.c.id == rid)).values(
                    state="completed", ended_at=await store.now()))
        return result


class Harness:
    async def initialize(self, engine, admin, redis, config, capacity):
        self.tenant, self.redis, self.cfg = uuid4(), redis, config
        async with admin.begin() as db:
            await db.execute(text("""INSERT INTO public.tenants
                (id,name,slug,plan,is_active,settings,limits,created_at,updated_at)
                VALUES (:id,:name,:slug,'enterprise',true,'{}','{}',now(),now())"""),
                {"id": self.tenant, "name": "Dispatcher validation " + str(self.tenant), "slug": "dispatch-" + str(self.tenant)})
            clock = (await db.execute(text("select clock_timestamp()"))).scalar_one()
        policy = AnalysisTaskPolicy(**json.loads((ROOT / "deploy/local-investigation/analysis-tasks.json").read_text()))
        self.service = ClockService(async_sessionmaker(engine, expire_on_commit=False), policy)
        self.service.clock = clock
        self.repository = DispatchRepository(self.service, self.tenant)
        self.policy = DispatchPolicy(namespace=config["namespace"], max_running_tasks=capacity,
            poll_interval_seconds=config["poll_interval_seconds"], execution_timeout_seconds=config["execution_timeout_seconds"],
            replenish_limit=config["replenish_limit"], priorities=tuple(config["priorities"]),
            receipt_directory=str(Path(config["receipt_directory"]) / str(self.tenant)), lock_file=config["lock_file"])
        self.queues = AnalysisQueues(redis, self.policy.namespace, self.tenant)
        self.executor = ControlledExecutor(self)
        self.dispatcher = self.new_dispatcher()
        await self.dispatcher.start()
        await self.dispatcher.tick()  # initial replenishment is empty
        return self

    def new_dispatcher(self):
        return AnalysisDispatcher(self.repository, self.queues, self.policy,
            dict.fromkeys(KINDS.values(), self.executor), clock=lambda: self.service.clock)

    async def subject(self, st="case"):
        aid, sid = uuid4(), uuid4()
        async with self.service.transaction(self.tenant) as store:
            await store.db.execute(insert(m.Alerts).values(id=aid, tenant_id=self.tenant,
                source_namespace="lyc-dispatch-validation", connector_type="lyc-dispatch-validation",
                source_identity_key=str(aid), title="Synthetic dispatcher alert"))
            if st == "alert":
                sid = aid
            elif st == "case":
                await store.db.execute(insert(m.Cases).values(id=sid, tenant_id=self.tenant, title="Synthetic dispatcher Case"))
                await store.db.execute(insert(m.CaseAlerts).values(id=uuid4(), tenant_id=self.tenant,
                    case_id=sid, alert_id=aid, membership_source="manual", source_operation_id=uuid4()))
            else:
                await store.db.execute(insert(m.Incidents).values(id=sid, tenant_id=self.tenant,
                    source_namespace="lyc-dispatch-validation", source_incident_id=str(sid), title="Synthetic dispatcher event"))
                await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=self.tenant,
                    incident_id=sid, alert_id=aid, membership_source="manual", correlation_basis={},
                    basis_version="fixture.v1", source_operation_id=uuid4()))
        self.executor.materials[sid] = {"fixture": True, "alert_ids": [str(aid)], "version": 1}
        return sid

    async def submit(self, sid, *, st="case", intent="check", source="user", pending=False):
        receipt = await self.service.submit(self.tenant, kind=KINDS[st], subject_id=sid,
            intent=intent, source=source, operation_key=uuid4())
        tid = receipt["task_id"]
        self.executor.started[tid] = asyncio.Event()
        if pending:
            await self.queues.push(await self.repository.task(tid), pending=True)
            await self.repository.enqueued(tid)
        return tid

    async def started(self, task_id):
        await asyncio.wait_for(self.executor.started[task_id].wait(), self.cfg["control_timeout_seconds"])

    async def finish_active(self):
        if self.dispatcher.active:
            await asyncio.wait_for(asyncio.gather(*(f for _, f in self.dispatcher.active.values())), self.cfg["control_timeout_seconds"])
        return await self.dispatcher.tick()

    async def read(self, tid):
        task = await self.repository.task(tid)
        return await self.service.read_task(self.tenant, task["subject_type"], task["subject_id"], tid)

    async def mutate(self, table, identity, **values):
        async with self.service.transaction(self.tenant) as store:
            await store.db.execute(update(table).where(*store.where(table, table.c.id == identity)).values(**values))

    async def row(self, table, identity):
        async with self.service.transaction(self.tenant, readonly=True) as store:
            return dict(await store.one(select(table).where(*store.where(table, table.c.id == identity))))


async def run_checks(engine, admin, redis, config, record):
    harnesses = []

    async def new(capacity=1):
        h = await Harness().initialize(engine, admin, redis, config, capacity)
        harnesses.append(h)
        return h

    try:
        h = await new(2)
        ca, cb = await h.subject(), await h.subject()
        h.executor.gates[ca] = asyncio.Event()
        ta = await h.submit(ca)
        await h.dispatcher.tick()
        await h.started(ta)
        blocked = [await h.submit(ca, pending=True) for _ in range(10)]
        tb = await h.submit(cb)
        status = await h.dispatcher.tick()
        await h.started(tb)
        assert status["pending_examined"] == 10 and len(h.dispatcher.active) == 2
        assert {c["subject_id"] for c in h.executor.calls} == {ca, cb}
        record("ten_busy_pending_do_not_block_normal_second_slot", True, {"tenant": h.tenant, "task_a": ta, "task_b": tb, **status})
        h.executor.gates[ca].set()
        for _ in range(len(blocked) + 2):
            await h.finish_active()
        assert (await h.read(blocked[0]))["status"] == "skipped" and len(h.executor.calls) == 2
        assert not await redis.scard(h.queues.key("running"))
        assert all([(await h.repository.task(t))["merged_into_task_id"] is None for t in blocked])
        record("same_subject_independent_requests_no_changes_no_new_run", True, {"waiting_tasks": blocked, "calls": h.executor.calls})

        h = await new(2)
        ca, cc = await h.subject(), await h.subject()
        h.executor.gates[ca] = asyncio.Event()
        ta = await h.submit(ca)
        await h.dispatcher.tick()
        await h.started(ta)
        await h.submit(ca, pending=True)
        await h.submit(ca, pending=True)
        tc = await h.submit(cc, pending=True)
        status = await h.dispatcher.tick()
        await h.started(tc)
        assert status["pending_examined"] == 3 and len(h.dispatcher.active) == 2
        record("pending_bound_is_length_not_capacity", True, {"tenant": h.tenant, **status})
        h.executor.gates[ca].set()
        for _ in range(3):
            await h.finish_active()

        h = await new(2)
        ci, aa, cc = await h.subject("incident"), await h.subject("alert"), await h.subject()
        ti, ta, tc = await h.submit(ci, st="incident"), await h.submit(aa, st="alert"), await h.submit(cc)
        await h.dispatcher.tick()
        assert set(h.dispatcher.active) == {tc, ta}
        await h.finish_active()
        await h.finish_active()
        for tid in (tc, ta, ti):
            assert (await h.read(tid))["status"] == "completed"
        record("case_alert_incident_priority_and_same_tick_fill", True, {"tenant": h.tenant, "tasks": [tc, ta, ti]})

        h = await new()
        ca = await h.subject()
        h.executor.gates[ca] = asyncio.Event()
        first = await h.submit(ca)
        h.executor.materials[ca]["version"] = 2
        await h.dispatcher.tick()
        await h.started(first)
        second = await h.submit(ca)
        h.executor.materials[ca]["version"] = 3
        assert h.executor.calls[0]["input"]["version"] == 2
        h.executor.gates[ca].set()
        await h.finish_active()
        await h.finish_active()
        assert [c["input"]["version"] for c in h.executor.calls] == [2, 3]
        for call in h.executor.calls:
            saved = await h.row(m.Artifacts.__table__, call["artifact_id"])
            assert saved["content_json"] == call["input"]
        third = await h.submit(ca)
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.read(third))["reason_code"] == "no_changes"
        checked = (await h.read(third))["attempts"]
        assert len(checked) == 1 and checked[0]["local_state"] == "ended" and checked[0]["run_id"] is None
        record("latest_before_start_frozen_during_run_and_completed_digest", True,
            {"tenant": h.tenant, "tasks": [first, second, third], "calls": h.executor.calls})

        h = await new()
        ca, cb = await h.subject(), await h.subject()
        h.executor.behavior[ca] = httpx.ConnectTimeout("controlled not sent")
        t1 = await h.submit(ca)
        await h.dispatcher.tick()
        await h.finish_active()
        waiting = await h.repository.task(t1)
        assert waiting["state"] == "waiting" and waiting["retry_count"] == 0
        assert waiting["next_retry_at"] == h.service.clock + timedelta(seconds=60)
        t2, tb = await h.submit(ca), await h.submit(cb)
        await h.dispatcher.tick()
        await h.finish_active()
        independent = await h.repository.task(t2)
        assert independent["state"] == "accepted" and independent["merged_into_task_id"] is None
        assert (await h.repository.task(t1))["next_retry_at"] == waiting["next_retry_at"]
        assert (await h.read(tb))["status"] == "completed"
        h.service.clock += timedelta(seconds=59)
        await h.dispatcher.tick()
        assert not h.dispatcher.active
        h.service.clock += timedelta(seconds=1)
        await h.dispatcher.tick()
        await h.finish_active()
        done = await h.read(t1)
        assert done["status"] == "failed" and done["reason_code"] == "retry_exhausted" and done["retry_count"] == 1
        await h.finish_active()
        checked = (await h.read(t2))["attempts"]
        assert len(done["attempts"]) == 2 and len(checked) == 1
        assert checked[0]["outcome"] == "completed" and checked[0]["run_id"] is None
        assert (await h.read(t2))["reason_code"] == "automatic_attempts_stopped"
        same = await h.submit(ca)
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.read(same))["reason_code"] == "automatic_attempts_stopped"
        h.executor.materials[ca]["version"] += 1
        h.executor.behavior[ca] = Outcome("completed")
        changed = await h.submit(ca)
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.read(changed))["status"] == "completed"
        ca_calls = [c for c in h.executor.calls if c["subject_id"] == ca]
        assert len(ca_calls) == 3 and len({c["operation_key"] for c in ca_calls}) == 3
        record("retry_60s_once_independent_request_preserves_budget_stopped_input_changes", True,
            {"tenant": h.tenant, "root": done, "independent_task": t2, "stopped_task": same, "changed_task": changed})

        h = await new()
        ca, cb = await h.subject(), await h.subject()
        h.executor.behavior[ca] = httpx.ReadTimeout("controlled uncertain response")
        ta, tb = await h.submit(ca), await h.submit(cb)
        # Explicit order; equal synthetic timestamps use UUID as the DB replenish tie-breaker.
        for tid in (ta, tb):
            await h.queues.push(await h.repository.task(tid))
            await h.repository.enqueued(tid)
        await h.dispatcher.tick()
        await h.finish_active()
        await h.finish_active()
        failed = await h.read(ta)
        assert failed["status"] == "failed" and failed["attempts"][0]["local_state"] == "ended"
        run = await h.row(R, failed["latest_run_id"])
        assert run["state"] == "unknown" and run["ended_at"] is None and failed["attempts"][0]["local_ended_at"]
        assert (await h.read(tb))["status"] == "completed"
        record("unknown_ends_local_attempt_releases_single_slot", True, {"tenant": h.tenant, "failed_task": failed, "following_task": tb})

        h = await new()
        ca, cb = await h.subject(), await h.subject()
        ta, tb = await h.submit(ca), await h.submit(cb)
        await h.mutate(m.Cases.__table__, ca, handling_status="resolved")
        h.executor.behavior[cb] = httpx.ConnectTimeout("controlled")
        h.service.clock += timedelta(days=8)
        await h.dispatcher.tick()
        await h.finish_active()
        closed, expired = await h.read(ta), await h.read(tb)
        assert closed["status"] == "skipped" and not closed["attempts"]
        assert expired["status"] == "failed" and expired["reason_code"] == "retry_stopped" and len(expired["attempts"]) == 1
        record("closed_skips_cross_window_first_attempt_runs_without_retry", True,
            {"tenant": h.tenant, "closed": closed, "cross_window": expired})

        h = await new()
        ca, cb = await h.subject(), await h.subject()
        h.executor.behavior[ca] = h.executor.behavior[cb] = httpx.PoolTimeout("controlled")
        ta = await h.submit(ca)
        await h.dispatcher.tick()
        await h.finish_active()
        tb = await h.submit(cb)
        await h.dispatcher.tick()
        await h.finish_active()
        await h.mutate(m.Cases.__table__, ca, handling_status="resolved")
        h.service.clock += timedelta(days=8)
        await h.dispatcher.tick()
        for tid in (ta, tb):
            result = await h.read(tid)
            assert result["reason_code"] == "retry_stopped" and result["retry_count"] == 0 and len(result["attempts"]) == 1
        record("waiting_retry_closed_or_expired_preserves_attempt", True, {"tenant": h.tenant, "tasks": [ta, tb]})

        h = await new()
        ca = await h.subject()
        h.executor.load_errors[ca] = ValueError("controlled invalid material")
        ta = await h.submit(ca)
        await h.dispatcher.tick()
        await h.finish_active()
        read = await h.read(ta)
        assert read["status"] == "failed" and len(read["attempts"]) == 1 and read["latest_run_id"] is None
        assert read["reason_code"] == "invalid_input" and not h.executor.calls
        record("material_preparation_failure_attempt_without_fake_run", True, {"tenant": h.tenant, "task": read})
        # Explicit rerun is a distinct intent, even after this input stopped automatic attempts.
        del h.executor.load_errors[ca]
        retry = await h.submit(ca, intent="rerun")
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.read(retry))["status"] == "completed"
        record("explicit_rerun_after_input_failure_not_merged_or_skipped", True, {"tenant": h.tenant, "task": retry})

        cb = await h.subject()
        h.executor.load_errors[cb] = ValueError("controlled unavailable initial material")
        failed = await h.submit(cb)
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.read(failed))["status"] == "failed"
        still_missing = await h.submit(cb)
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.read(still_missing))["reason_code"] == "automatic_attempts_stopped"
        checked = (await h.read(still_missing))["attempts"]
        assert len(checked) == 1 and checked[0]["outcome"] == "completed" and checked[0]["run_id"] is None
        del h.executor.load_errors[cb]
        h.executor.materials[cb]["version"] += 1
        available = await h.submit(cb)
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.read(available))["status"] == "completed"
        record("new_readable_material_after_preparation_failure_can_proceed", True,
            {"tenant": h.tenant, "failed_task": failed, "still_missing_task": still_missing, "available_task": available})

        h = await new()
        ca = await h.subject()
        after = h.service.clock + timedelta(seconds=120)
        h.executor.behavior[ca] = ExecutionFailure("rate_limited", stage="execute", not_executed=True,
            temporary=True, status_code=429, retry_after=after)
        ta = await h.submit(ca)
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.repository.task(ta))["next_retry_at"] == after
        h.service.clock += timedelta(seconds=60)
        await h.dispatcher.tick()
        assert not h.dispatcher.active
        h.service.clock += timedelta(seconds=60)
        h.executor.behavior[ca] = Outcome("completed")
        await h.dispatcher.tick()
        await h.finish_active()
        done = await h.read(ta)
        assert done["status"] == "completed" and done["retry_count"] == 1 and len(done["attempts"]) == 2
        record("retry_after_later_than_default_delay_is_respected", True, {"tenant": h.tenant, "task": done})

        h = await new()
        ca = await h.subject()
        h.executor.behavior[ca] = httpx.ConnectTimeout("controlled")
        ta = await h.submit(ca)
        await h.dispatcher.tick()
        await h.finish_active()
        h.executor.behavior[ca] = Outcome("completed")
        explicit = await h.submit(ca, intent="rerun")
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.read(explicit))["status"] == "completed"
        h.service.clock += timedelta(seconds=60)
        await h.dispatcher.tick()
        await h.finish_active()
        read = await h.read(ta)
        assert read["status"] == "skipped" and read["reason_code"] == "no_changes"
        assert len(read["attempts"]) == 2 and read["attempts"][0]["outcome"] == "failed"
        assert read["attempts"][1]["outcome"] == "completed" and read["attempts"][1]["run_id"] is None
        assert read["retry_count"] == 1 and len(h.executor.calls) == 2
        record("covered_waiting_retry_skips_without_erasing_old_failure", True,
            {"tenant": h.tenant, "waiting_task": read, "explicit_task": explicit})

        h = await new()
        ca, cb = await h.subject(), await h.subject()
        ta = await h.submit(ca)
        await h.dispatcher.tick()
        await h.started(ta)
        await asyncio.gather(*(f for _, f in h.dispatcher.active.values()))
        tb = await h.submit(cb)
        original_finish = h.repository.finish
        fail = True

        async def fail_once(receipt):
            nonlocal fail
            if fail:
                fail = False
                raise SQLAlchemyError("controlled completion write unavailable")
            return await original_finish(receipt)

        h.repository.finish = fail_once
        status = await h.dispatcher.tick()
        assert ta in h.dispatcher.receipts and tb in h.dispatcher.active and status["completion_writes_unconfirmed"] == 1
        assert not await redis.sismember(h.queues.key("running"), str(ta))
        assert len(list(Path(h.policy.receipt_directory).glob("*.json"))) == 1
        assert (await h.read(ta))["status"] == "running"  # actual saved PG state, not an invented success
        await h.finish_active()
        assert (await h.read(ta))["status"] == "completed" and (await h.read(tb))["status"] == "completed"
        assert len(h.executor.calls) == 2 and not h.dispatcher.receipts
        record("completion_write_retry_releases_slot_without_reexecution", True, {"tenant": h.tenant, "tasks": [ta, tb]})

        h = await new()
        ca, cb = await h.subject(), await h.subject()
        ta = await h.submit(ca)
        await h.dispatcher.tick()
        await h.started(ta)
        await asyncio.gather(*(f for _, f in h.dispatcher.active.values()))
        tb = await h.submit(cb)
        original_redis = h.queues.redis

        class UnavailableRedis:
            def __getattr__(self, name):
                async def unavailable(*args, **kwargs):
                    raise RedisConnectionError("controlled local Redis unavailable")
                return unavailable

        h.queues.redis = UnavailableRedis()
        status = await h.dispatcher.tick()
        assert status["dependency_unavailable"] and not h.dispatcher.active
        assert (await h.read(ta))["status"] == "completed" and (await h.read(tb))["status"] == "accepted"
        assert len(h.executor.calls) == 1
        h.queues.redis = original_redis
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.read(tb))["status"] == "completed"
        record("redis_unavailable_finishes_pg_stops_claims_then_replenishes", True, {"tenant": h.tenant, "tasks": [ta, tb]})

        h = await new()
        ca, cb = await h.subject(), await h.subject()
        ta = await h.submit(ca)
        await h.dispatcher.tick()
        await h.started(ta)
        await asyncio.gather(*(f for _, f in h.dispatcher.active.values()))
        h.dispatcher._collect()  # durable receipt exists; original dispatcher no longer has an active handle
        original_end = h.service.clock
        h.service.clock += timedelta(seconds=10)
        h.dispatcher = h.new_dispatcher()
        await h.dispatcher.start()
        result = await h.read(ta)
        assert result["status"] == "completed" and result["attempts"][0]["local_ended_at"] == original_end
        assert len(h.executor.calls) == 1
        # A separate saved running fixture has no completion receipt; restart records observation only.
        interrupted = await h.submit(ca, intent="rerun")
        task = await h.repository.task(interrupted)
        attempt = await h.repository.begin(task, await h.executor.load(task))
        assert attempt
        h.executor.behavior[ca] = Outcome("unknown", "execution_unknown")
        await h.executor.execute(AttemptContext(h.repository, task, attempt), await h.executor.load(task))
        tb = await h.submit(cb)
        sentinel = h.queues.key("foreign-sentinel")
        await redis.set(sentinel, "preserve")
        h.dispatcher = h.new_dispatcher()
        await h.dispatcher.start()
        read = await h.read(interrupted)
        assert read["status"] == "failed" and read["attempts"][0]["local_state"] == "interrupted"
        assert read["attempts"][0]["local_ended_at"] is None and read["attempts"][0]["interruption_observed_at"]
        interrupted_run = await h.row(R, read["latest_run_id"])
        assert interrupted_run["state"] == "unknown" and interrupted_run["ended_at"] is None
        assert await redis.get(sentinel) == b"preserve"
        await h.dispatcher.tick()
        await h.finish_active()
        assert (await h.read(tb))["status"] == "completed"
        record("restart_replays_completion_or_marks_interrupted_without_fake_end", True,
            {"tenant": h.tenant, "completed": result, "interrupted": read, "following": tb})
    finally:
        # Only this run's controlled futures; never rewrite or delete prior PG fixtures.
        for h in harnesses:
            for gate in h.executor.gates.values():
                gate.set()
            if h.dispatcher.active:
                for _, future in h.dispatcher.active.values():
                    future.cancel()
                await asyncio.gather(*(f for _, f in h.dispatcher.active.values()), return_exceptions=True)
                h.dispatcher._collect()
                await h.dispatcher._flush_receipts()
