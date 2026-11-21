"""One asynchronous dispatcher; concurrent execution, sequential queue ownership."""
import asyncio
import logging
import re
import sys
from datetime import UTC, datetime
from uuid import uuid5

from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.core.operational_logging import bind_log_context, log_context, log_exception

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
            result = await store.bind_run(self.attempt["id"], run_id, **frozen)
        bind_log_context(run_id=run_id)
        return result

    async def bind_in_transaction(self, store, run_id, **frozen):
        from .analysis_task_store import AnalysisTaskStore
        if store.tenant_id != self.task["tenant_id"]:
            raise StoreError("analysis_attempt_subject_mismatch")
        tasks = AnalysisTaskStore(store.db, store.tenant_id, self.repository.service.policy)
        result = await tasks.bind_run(self.attempt["id"], run_id, **frozen)
        bind_log_context(run_id=run_id)
        return result


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
        try:
            await self.queues.redis.ping()
        except RedisError:
            log_exception(LOG, "analysis_redis_start_failed", extra={"operation": "redis_ping", "stage": "startup",
                "dependency": "redis", "error_code": "service_unavailable"})
            raise
        await self._flush_receipts()
        await self.repository.interrupt_remaining(exclude_attempt_ids=[r.attempt_id for r in self.receipts.values() if r.attempt_id])
        await self.queues.reset_hints()
        self.started = True

    def _busy(self, task):
        key = subject_key(task)
        return any(subject_key(t) == key for t, _ in self.active.values()) or any(
            subject_key(r.task) == key for r in self.receipts.values())

    async def _run(self, task):
        with log_context(task_id=task["id"], subject_type=task.get("subject_type"),
                         subject_id=task.get("subject_id"), retry_count=task.get("retry_count"),
                         operation="analysis_attempt", stage="input"):
            return await self._run_attempt(task)

    async def _run_attempt(self, task):
        attempt, result, stage, action = None, None, "input", "finish"
        began = task["_claimed_at"]
        try:
            async with asyncio.timeout(self.policy.execution_timeout_seconds):
                attempt = await self.repository.prepare(task, started_at=began)
                if attempt is None:
                    return Completion(task, None, self.clock(), action="done")
                bind_log_context(attempt_id=attempt["id"], attempt_no=attempt.get("attempt_no"),
                    retry_count=(task["retry_count"] + int(task.get("started_at") is not None)
                                 if "retry_count" in task else None))
                material = await self.executors[task["kind"]].load(task)
                if not re.fullmatch(r"[0-9a-f]{64}", material.digest):
                    raise ValueError("invalid material digest")
                attempt = await self.repository.begin(task, material, attempt_id=attempt["id"])
                if attempt is None:
                    return Completion(task, None, self.clock(), action="done")
                stage = "execute"
                bind_log_context(stage=stage)
                result = await self.executors[task["kind"]].execute(
                    AttemptContext(self.repository, task, attempt), material)
                if not isinstance(result, Outcome) or result.outcome not in {"completed", "failed", "unknown"}:
                    raise ValueError("invalid execution outcome")
                if result.outcome != "completed":
                    LOG.error("analysis_attempt_outcome", extra={"stage": result.error_stage,
                        "error_code": result.error_code, "outcome": result.outcome,
                        "retryable": result.retryable, "dependency": "executor",
                        "exception_type": (result.error_detail or {}).get("exception_type")})
        except TimeoutError as error:
            result = classify_failure(error, stage=stage, deadline=True)
            self._log_failure(result)
        except asyncio.CancelledError as error:
            result = classify_failure(error, stage=stage)
            self._log_failure(result)
        except StoreError as error:
            if attempt is None and error.code in {"analysis_subject_busy", "retry_not_due"}:
                return Completion(task, None, self.clock(), action="requeue")
            result = Outcome("failed", "invalid_input", stage, {"code": error.code})
            self._log_failure(result)
        except Exception as error:  # noqa: BLE001 -- one task failure must not stop the queue
            result = classify_failure(error, stage=stage)
            self._log_failure(result)
        if attempt is None or stage == "input":
            try:
                attempt = await self.repository.begin(task, started_at=began, load_failed=True,
                    attempt_id=attempt["id"] if attempt else None)
                if attempt is None:
                    action = "done"
            except (SQLAlchemyError, StoreError):
                action = "prepare_failed"
                log_exception(LOG, "analysis_preparation_persistence_unconfirmed", extra={
                    "operation": "prepare_attempt", "dependency": "postgres", "error_code": "save_unconfirmed"})
        return Completion(task, attempt["id"] if attempt else None, self.clock(), result, action, began)

    @staticmethod
    def _log_failure(result):
        error = sys.exc_info()[1]
        log_exception(LOG, "analysis_attempt_failed", extra={"stage": result.error_stage,
            "error_code": result.error_code, "outcome": result.outcome, "retryable": result.retryable,
            "dependency": dependency_name(error) if isinstance(error, (RedisError, SQLAlchemyError)) else "executor"})

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
                log_exception(LOG, "analysis_completion_file_unconfirmed", extra={"task_id": task_id,
                    "attempt_id": receipt.attempt_id, "operation": "save_completion_receipt",
                    "stage": "persist", "dependency": "filesystem", "error_code": "save_unconfirmed"})
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
                log_exception(LOG, "analysis_running_index_unconfirmed", level=logging.WARNING, extra={"task_id": task_id,
                    "attempt_id": receipt.attempt_id, "operation": "release_running_index", "stage": "persist",
                    "dependency": "redis", "error_code": "save_unconfirmed"})
            try:
                if receipt.action == "prepare_failed":
                    attempt = await self.repository.begin(receipt.task,
                        started_at=receipt.preparation_started_at, load_failed=True)
                    receipt.attempt_id = attempt["id"] if attempt else None
                    receipt.action = "finish" if attempt else "done"
                    self.files.put(receipt)
                if receipt.attempt_id is not None:
                    current = await self.repository.finish(receipt)
                    if current:
                        LOG.info("analysis_completion_saved", extra={"task_id": task_id,
                            "attempt_id": receipt.attempt_id, "operation": "save_attempt_completion", "stage": "persist",
                            "dependency": "postgres", "retry_count": current.get("retry_count"),
                            "next_retry_at": current.get("next_retry_at"), "outcome": current["state"]})
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
            except (SQLAlchemyError, StoreError, RedisError, OSError) as error:
                log_exception(LOG, "analysis_completion_persistence_unconfirmed", level=logging.WARNING, extra={"task_id": task_id,
                    "attempt_id": receipt.attempt_id, "operation": "save_completion", "stage": "persist",
                    "dependency": dependency_name(error), "error_code": "save_unconfirmed"})
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
        with log_context(task_id=task_id, operation="claim_task", stage="queue"):
            try:
                return await self._candidate_task(task_id)
            except (RedisError, SQLAlchemyError, StoreError) as error:
                log_exception(LOG, "analysis_task_claim_failed", extra={
                    "dependency": dependency_name(error), "error_code": "service_unavailable"})
                raise

    async def _candidate_task(self, task_id):
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
            await self.repository.enqueued(task_id)
            return
        if task["kind"] not in self.executors:
            await self.queues.push(task)
            await self.repository.enqueued(task_id)
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
                        log_exception(LOG, "analysis_periodic_check_unavailable", level=logging.WARNING, extra={
                            "operation": "periodic_check", "stage": "input", "dependency": "postgres",
                            "error_code": "service_unavailable"})
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
        except (RedisError, SQLAlchemyError, StoreError) as error:
            self.replenish_all, self.replenish_after = True, None
            self.last_status["dependency_unavailable"] = True
            log_exception(LOG, "analysis_dispatch_dependency_unavailable", level=logging.WARNING, extra={
                "operation": "dispatch_tick", "stage": "queue", "dependency": dependency_name(error),
                "error_code": "service_unavailable"})
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


def dependency_name(error):
    if isinstance(error, RedisError):
        return "redis"
    if isinstance(error, (SQLAlchemyError, StoreError)):
        return "postgres"
    if isinstance(error, OSError):
        return "filesystem"
    return "executor"
