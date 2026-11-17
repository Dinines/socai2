"""One asynchronous dispatcher; concurrent execution, sequential queue ownership."""
import asyncio
import logging
import re
from datetime import UTC, datetime
from uuid import uuid5

from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from .analysis_dispatch_types import (
    Completion,
    CompletionFiles,
    Outcome,
    classify_failure,
)
from .baseline_store import StoreError

LOG = logging.getLogger(__name__)


def subject_key(task):
    return task["tenant_id"], task["subject_type"], task["subject_id"], task["kind"]


class AttemptContext:
    def __init__(self, repository, task, attempt):
        self.repository, self.task, self.attempt = repository, task, attempt
        self.operation_key = uuid5(task["id"], str(attempt["attempt_no"]))

    async def bind_run(self, run_id, **frozen):
        async with self.repository.service.transaction(self.repository.tenant_id) as store:
            return await store.bind_run(self.attempt["id"], run_id, **frozen)

    async def bind_in_transaction(self, store, run_id, **frozen):
        from .analysis_task_store import AnalysisTaskStore
        if store.tenant_id != self.task["tenant_id"]:
            raise StoreError("analysis_attempt_subject_mismatch")
        tasks = AnalysisTaskStore(store.db, store.tenant_id, self.repository.service.policy)
        return await tasks.bind_run(self.attempt["id"], run_id, **frozen)


class AnalysisDispatcher:
    def __init__(self, repository, queues, policy, executors, *, clock=None):
        self.repository, self.queues, self.policy, self.executors = repository, queues, policy, executors
        self.clock = clock or (lambda: datetime.now(UTC))
        self.files = CompletionFiles(policy.receipt_directory)
        self.active = {}  # task_id -> (task, future); only this object mutates it
        self.receipts = {}
        self.replenish_all, self.replenish_after = True, None
        self._ticking = False
        self.started = False
        self.last_status = {}

    async def start(self):
        """Called under the entry point's process lock, after the old process exited."""
        if self.started:
            raise RuntimeError("dispatcher already started")
        self.receipts = {r.task["id"]: r for r in self.files.load()}
        if any(r.task["tenant_id"] != self.repository.tenant_id for r in self.receipts.values()):
            raise ValueError("receipt directory belongs to another tenant")
        await self.queues.redis.ping()
        await self._flush_receipts()
        await self.repository.interrupt_remaining(exclude_attempt_ids=[r.attempt_id for r in self.receipts.values() if r.attempt_id])
        await self.queues.reset_hints()
        self.started = True

    def _busy(self, task):
        key = subject_key(task)
        return any(subject_key(t) == key for t, _ in self.active.values()) or any(
            subject_key(r.task) == key for r in self.receipts.values())

    async def _run(self, task):
        attempt, result, stage, action = None, None, "input", "finish"
        began = task["_claimed_at"]
        try:
            async with asyncio.timeout(self.policy.execution_timeout_seconds):
                material = await self.executors[task["kind"]].load(task)
                if not re.fullmatch(r"[0-9a-f]{64}", material.digest):
                    raise ValueError("invalid material digest")
                attempt = await self.repository.begin(task, material)
                if attempt is None:
                    return Completion(task, None, self.clock(), action="done")
                stage = "execute"
                result = await self.executors[task["kind"]].execute(
                    AttemptContext(self.repository, task, attempt), material)
                if not isinstance(result, Outcome) or result.outcome not in {"completed", "failed", "unknown"}:
                    raise ValueError("invalid execution outcome")
        except TimeoutError as error:
            result = classify_failure(error, stage=stage, deadline=True)
        except asyncio.CancelledError as error:
            result = classify_failure(error, stage=stage)
        except StoreError as error:
            if error.code in {"analysis_subject_busy", "retry_not_due"}:
                return Completion(task, None, self.clock(), action="requeue")
            result = Outcome("failed", "invalid_input", stage, {"code": error.code})
        except Exception as error:  # noqa: BLE001 -- one task failure must not stop the queue
            result = classify_failure(error, stage=stage)
        if attempt is None:
            try:
                attempt = await self.repository.begin(task, started_at=began, load_failed=True)
                if attempt is None:
                    action = "done"
            except (SQLAlchemyError, StoreError):
                action = "prepare_failed"
        return Completion(task, attempt["id"] if attempt else None, self.clock(), result, action, began)

    def _collect(self):
        for task_id, (task, future) in list(self.active.items()):
            if not future.done():
                continue
            try:
                receipt = future.result()
            except BaseException as error:  # task wrapper failure/cancellation still preserves an unknown end
                if isinstance(error, (KeyboardInterrupt, SystemExit)):
                    raise
                receipt = Completion(task, None, self.clock(),
                    classify_failure(error, stage="execute"), "prepare_failed", task["_claimed_at"])
            self.receipts[task_id] = receipt
            try:
                self.files.put(receipt)
            except OSError:
                LOG.error("analysis_completion_file_unconfirmed", extra={"task_id": str(task_id)})
            del self.active[task_id]  # the execution handle has actually ended

    async def _flush_receipts(self):
        for task_id, receipt in list(self.receipts.items()):
            # The handle has ended even when its PG completion write must wait.
            # Redis failure must not prevent the independent PG completion write.
            released = False
            try:
                await self.queues.release(receipt.task)
                released = True
            except RedisError:
                LOG.warning("analysis_running_index_unconfirmed", extra={"task_id": str(task_id)})
            try:
                if receipt.action == "prepare_failed":
                    attempt = await self.repository.begin(receipt.task,
                        started_at=receipt.preparation_started_at, load_failed=True)
                    receipt.attempt_id = attempt["id"] if attempt else None
                    receipt.action = "finish" if attempt else "done"
                    self.files.put(receipt)
                if receipt.attempt_id is not None:
                    current = await self.repository.finish(receipt)
                else:
                    current = await self.repository.task(task_id)
                # Redis failures here cannot undo a saved completion or rerun the model.
                if not released:
                    continue
                if current and current["state"] in {"accepted", "waiting"}:
                    await self.queues.push(current, pending=True)
                    await self.repository.enqueued(task_id)
                self.files.remove(receipt)
                del self.receipts[task_id]
            except (SQLAlchemyError, StoreError, RedisError, OSError):
                LOG.warning("analysis_completion_persistence_unconfirmed", extra={"task_id": str(task_id)})
                # Other subjects can continue. Same subject waits for this small write receipt.

    async def _replenish(self):
        tasks = await self.repository.pending_tasks(self.policy.replenish_limit,
            all_waiting=self.replenish_all, after=self.replenish_after if self.replenish_all else None)
        for task in tasks:
            if task["id"] in self.active or task["id"] in self.receipts:
                continue
            await self.queues.push(task, pending=task["started_at"] is not None)
            await self.repository.enqueued(task["id"])
        if self.replenish_all:
            if len(tasks) < self.policy.replenish_limit:
                self.replenish_all, self.replenish_after = False, None
            elif tasks:
                self.replenish_after = tasks[-1]["submitted_at"], tasks[-1]["id"]

    async def _candidate(self, task_id):
        if task_id in self.active:
            return
        task = await self.repository.task(task_id)
        if not task or task["state"] not in {"accepted", "waiting"}:
            return
        eligibility = await self.repository.eligibility(task_id)
        if eligibility == "discard":
            return
        if eligibility == "wait" or self._busy(task):
            await self.queues.push(task, pending=True)
            return
        if task["kind"] not in self.executors:
            await self.queues.push(task)
            self.last_status["unconfigured_executor"] = task["kind"]
            return
        task["_claimed_at"] = await self.repository.now()
        await self.queues.mark_running(task)
        future = asyncio.create_task(self._run(task), name="analysis-" + str(task_id))
        self.active[task_id] = task, future

    async def tick(self):
        if not self.started or self._ticking:
            raise RuntimeError("dispatcher not started or concurrent tick")
        self._ticking = True
        self.last_status = {"pending_examined": 0, "normal_examined": 0}
        try:
            self._collect()
            await self._flush_receipts()
            for executor in self.executors.values():
                checker = getattr(executor, "check_updates", None)
                if checker:
                    try:
                        self.last_status["periodic_checks"] = await checker(self.repository.tenant_id, self.clock())
                    except (SQLAlchemyError, StoreError):
                        self.last_status["periodic_check_unavailable"] = True
                        LOG.warning("analysis_periodic_check_unavailable")
            await self.queues.redis.ping()
            await self._replenish()
            queues = [(self.queues.pending, "pending_examined")]
            queues += [(self.queues.normal(kind), "normal_examined") for kind in self.policy.priorities]
            for key, counter in queues:
                if len(self.active) >= self.policy.max_running_tasks:
                    break
                count = await self.queues.redis.llen(key)
                for _ in range(count):
                    if len(self.active) >= self.policy.max_running_tasks:
                        break
                    self.last_status[counter] += 1
                    try:
                        task_id = await self.queues.pop(key)
                    except ValueError:
                        self.last_status["invalid_queue_entry"] = True
                        continue
                    if task_id is None:
                        break
                    await self._candidate(task_id)
        except (RedisError, SQLAlchemyError, StoreError):
            self.replenish_all, self.replenish_after = True, None
            self.last_status["dependency_unavailable"] = True
            LOG.warning("analysis_dispatch_dependency_unavailable")
        finally:
            self._ticking = False
        self.last_status.update(running=len(self.active), completion_writes_unconfirmed=len(self.receipts))
        return dict(self.last_status)

    async def serve(self, stop):
        await self.start()
        try:
            while not stop.is_set():
                await self.tick()
                try:
                    await asyncio.wait_for(stop.wait(), timeout=self.policy.poll_interval_seconds)
                except TimeoutError:
                    pass
        finally:
            # Cancellation must finish locally before a slot is reported as released.
            for _, future in self.active.values():
                future.cancel()
            if self.active:
                await asyncio.gather(*(f for _, f in self.active.values()), return_exceptions=True)
            self._collect()
            await self._flush_receipts()
