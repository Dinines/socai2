"""PG operations needed by the single dispatcher; no model/Redis operations in a transaction."""
import logging
from dataclasses import asdict, replace

from sqlalchemy import case, func, select, tuple_, update

from .analysis_dispatch_types import Outcome
from .analysis_task_store import A, R, S, T
from .baseline_store import StoreError

LOG = logging.getLogger(__name__)


class DispatchRepository:
    def __init__(self, service, tenant_id):
        self.service, self.tenant_id = service, tenant_id

    async def now(self):
        async with self.service.transaction(self.tenant_id, readonly=True) as store:
            return await store.now()

    async def task(self, task_id):
        async with self.service.transaction(self.tenant_id, readonly=True) as store:
            row = await store.one(select(T).where(*store.where(T, T.c.id == task_id)))
            return dict(row) if row else None

    async def pending_tasks(self, limit, *, all_waiting=False, after=None):
        async with self.service.transaction(self.tenant_id, readonly=True) as store:
            query = select(T).where(*store.where(T, T.c.state.in_(["accepted", "waiting"])))
            if not all_waiting:
                query = query.where(T.c.next_attempt_enqueued_at.is_(None))
            if after:
                query = query.where(tuple_(T.c.submitted_at, T.c.id) > tuple_(*after))
            return [dict(r) for r in (await store.db.execute(
                query.order_by(T.c.submitted_at, T.c.id).limit(limit))).mappings()]

    async def enqueued(self, task_id):
        async with self.service.transaction(self.tenant_id) as store:
            now = await store.now()
            await store.db.execute(update(T).where(*store.where(T, T.c.id == task_id,
                T.c.state.in_(["accepted", "waiting"]))).values(last_enqueued_at=now,
                # A pre-migration task with an old enqueue/start has no known first
                # enqueue. A new replenishment must not rewrite that unknown history.
                first_enqueued_at=func.coalesce(T.c.first_enqueued_at, case(
                    ((T.c.last_enqueued_at.is_(None)) & (T.c.started_at.is_(None)), now), else_=None)),
                next_attempt_enqueued_at=func.coalesce(T.c.next_attempt_enqueued_at, now)))

    async def eligibility(self, task_id):
        async with self.service.transaction(self.tenant_id) as store:
            task = await store.task(task_id)
            if task["state"] not in {"accepted", "waiting"}:
                return "discard"
            subject = await store.subject(task["subject_type"], task["subject_id"], lock=True)
            now = await store.now()
            if subject["handling_status"] in {"resolved", "completed"}:
                if task["started_at"]:
                    await store.stop_retry(task, "retry_stopped", now)
                else:
                    await store.skip(task_id, "closed_before_start")
                return "discard"
            if task["started_at"]:
                status = await store.automatic_status(task["subject_type"], task["subject_id"])
                if status["ineligible_reason"] == "expired" or task["retry_count"] >= task["retry_limit"]:
                    await store.stop_retry(task, "retry_stopped", now)
                    return "discard"
                if task["next_retry_at"] is None or now < task["next_retry_at"]:
                    return "wait"
            elif task["intent"] in {"initial", "check"} and await store.one(select(T.c.id).where(*store.where(T,
                    T.c.subject_type == task["subject_type"], T.c.subject_id == task["subject_id"],
                    T.c.kind == task["kind"], T.c.state == "waiting", T.c.started_at.is_not(None))).limit(1)):
                # Keep the request independent, but do not let it reset or bypass
                # an existing retry's delay/budget. Recompare after that task ends.
                return "wait"
            return "ready"

    async def prepare(self, task, *, started_at):
        async with self.service.transaction(self.tenant_id) as store:
            return await store.start_attempt(task["id"], started_at=started_at)

    async def begin(self, task, material=None, *, started_at=None, load_failed=False, attempt_id=None):
        async with self.service.transaction(self.tenant_id) as store:
            current = await store.task(task["id"])
            prepared = None
            if current["state"] == "running":
                prepared = await store.one(select(A).where(*store.where(A, A.c.task_id == task["id"],
                    A.c.local_state == "running",
                    A.c.id == attempt_id if attempt_id else A.c.started_at == started_at)).with_for_update())
                if prepared is None:
                    return None
            elif current["state"] not in {"accepted", "waiting"}:
                return None
            subject = await store.subject(task["subject_type"], task["subject_id"], lock=True)
            if prepared is None and subject["handling_status"] in {"resolved", "completed"}:
                if current["started_at"]:
                    await store.stop_retry(current, "retry_stopped", await store.now())
                else:
                    await store.skip(task["id"], "closed_before_start")
                return None
            state = await store.one(select(S).where(*store.where(S,
                S.c.subject_type == task["subject_type"], S.c.subject_id == task["subject_id"])))
            ordinary = current["intent"] in {"initial", "check"}
            reason = None
            if ordinary and state:
                completed = await store.one(select(A.c.input_digest).where(*store.where(A,
                    A.c.id == state["last_completed_attempt_id"]))) if state["last_completed_attempt_id"] else None
                if material and completed and (material.digest == completed["input_digest"]
                        or material.unchanged_from_attempt_id == state["last_completed_attempt_id"]) and not material.capacity_changed:
                    reason = "no_changes"
                elif (state["automatic_stop_reason"] and (
                        load_failed
                        or material and (material.digest == state["stopped_input_digest"]
                            or material.unchanged_from_stopped_task_id is not None
                            and material.unchanged_from_stopped_task_id == state["stopped_task_id"]))
                        and not (material and state["automatic_stop_reason"] == "capacity_exceeded" and material.capacity_changed)):
                    reason = "automatic_attempts_stopped"
            if reason:
                if prepared:
                    await store.skip_preparation(prepared["id"], reason)
                else:
                    await store.skip(task["id"], reason)
                return None
            if material:
                await store.db.execute(update(T).where(*store.where(T, T.c.id == task["id"])).values(
                    observed_input_digest=material.digest))
            return dict(prepared) if prepared else await store.start_attempt(task["id"], started_at=started_at)

    async def finish(self, receipt):
        async with self.service.transaction(self.tenant_id) as store:
            attempt = await store.attempt(receipt.attempt_id)
            if attempt["local_state"] != "running":
                # A previous write may have committed before its acknowledgement failed.
                return dict(await store.task(attempt["task_id"]))
            run = (await store.one(select(R).where(*store.where(R, R.c.id == attempt["run_id"])).with_for_update())
                   if attempt["run_id"] else None)
            earliest = attempt["started_at"]
            if run and run["state"] == "running" and run["started_at"]:
                earliest = max(earliest, run["started_at"])
            ended_at = receipt.ended_at
            if ended_at.tzinfo is not None and ended_at < earliest:
                # The execution handle has ended, but a different host's wall
                # clock cannot precede this DB's start. Record when this DB
                # observes that fact; keep the original receipt unchanged.
                ended_at = await store.now()
                LOG.warning("analysis_completion_clock_before_start", extra={
                    "task_id": attempt["task_id"], "attempt_no": attempt["attempt_no"],
                    "operation": "save_attempt_completion", "stage": "persist", "dependency": "postgres",
                    "attempt_id": str(attempt["id"]), "receipt_ended_at": receipt.ended_at.isoformat(),
                    "database_started_at": attempt["started_at"].isoformat(),
                    "database_latest_start": earliest.isoformat(),
                    "database_observed_ended_at": ended_at.isoformat()})
                if ended_at.tzinfo is None or ended_at < earliest:
                    raise StoreError("invalid_attempt_end", 422)
            result = receipt.result
            if attempt["run_id"]:
                if run["state"] == "running":
                    if result.outcome == "completed":
                        result = Outcome("failed", "execution_failed", "missing_saved_result")
                    await store.db.execute(update(R).where(*store.where(R, R.c.id == run["id"])).values(
                        state=result.outcome, ended_at=ended_at if result.outcome == "failed" else None,
                        stop_reason=result.error_code, row_version=R.c.row_version + 1))
                elif run["state"] in {"completed", "failed", "unknown"} and run["state"] != result.outcome:
                    result = (Outcome("completed") if run["state"] == "completed"
                        else replace(result, outcome=run["state"], retryable=False,
                                     error_code=result.error_code or "execution_failed"))
            elif result.outcome == "completed":
                result = Outcome("failed", "execution_failed", "missing_saved_run")
            await store.finish_attempt(receipt.attempt_id, **asdict(result), ended_at=ended_at)
            return dict(await store.task(attempt["task_id"]))

    async def interrupt_remaining(self, *, exclude_attempt_ids=()):
        async with self.service.transaction(self.tenant_id) as store:
            query = select(A).where(*store.where(A, A.c.local_state == "running"))
            if exclude_attempt_ids:
                query = query.where(A.c.id.not_in(exclude_attempt_ids))
            attempts = list((await store.db.execute(query.with_for_update())).mappings())
            observed = await store.now()
            for attempt in attempts:
                task = await store.task(attempt["task_id"])
                if attempt["run_id"]:
                    await store.db.execute(update(R).where(*store.where(R, R.c.id == attempt["run_id"],
                        R.c.state == "running")).values(state="unknown", stop_reason="executor_interrupted",
                                                       row_version=R.c.row_version + 1))
                await store.db.execute(update(A).where(*store.where(A, A.c.id == attempt["id"])).values(
                    local_state="interrupted", interruption_observed_at=observed, outcome="unknown",
                    failed_at=observed, error_code="executor_interrupted", error_stage="process", retryable=False))
                await store.db.execute(update(T).where(*store.where(T, T.c.id == task["id"])).values(
                    state="failed", reason_code="executor_interrupted", ended_at=observed, next_retry_at=None))
                await store.stop_subject(task, attempt, "executor_interrupted")
            return len(attempts)
