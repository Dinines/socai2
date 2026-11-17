"""PG operations needed by the single dispatcher; no model/Redis operations in a transaction."""
from dataclasses import asdict, replace

from sqlalchemy import select, tuple_, update

from .analysis_dispatch_types import Outcome
from .analysis_task_store import A, R, S, T


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
                query = query.where(T.c.last_enqueued_at.is_(None))
            if after:
                query = query.where(tuple_(T.c.submitted_at, T.c.id) > tuple_(*after))
            return [dict(r) for r in (await store.db.execute(
                query.order_by(T.c.submitted_at, T.c.id).limit(limit))).mappings()]

    async def enqueued(self, task_id):
        async with self.service.transaction(self.tenant_id) as store:
            await store.db.execute(update(T).where(*store.where(T, T.c.id == task_id,
                T.c.state.in_(["accepted", "waiting"]))).values(last_enqueued_at=await store.now()))

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

    async def begin(self, task, material=None, *, started_at=None, load_failed=False):
        async with self.service.transaction(self.tenant_id) as store:
            current = await store.task(task["id"])
            if current["state"] not in {"accepted", "waiting"}:
                return None
            subject = await store.subject(task["subject_type"], task["subject_id"], lock=True)
            if subject["handling_status"] in {"resolved", "completed"}:
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
                await store.skip(task["id"], reason)
                return None
            if material:
                await store.db.execute(update(T).where(*store.where(T, T.c.id == task["id"])).values(
                    observed_input_digest=material.digest))
            return await store.start_attempt(task["id"], started_at=started_at)

    async def finish(self, receipt):
        async with self.service.transaction(self.tenant_id) as store:
            attempt = await store.attempt(receipt.attempt_id)
            if attempt["local_state"] != "running":
                # A previous write may have committed before its acknowledgement failed.
                return dict(await store.task(attempt["task_id"]))
            result = receipt.result
            if attempt["run_id"]:
                run = await store.one(select(R).where(*store.where(R, R.c.id == attempt["run_id"])).with_for_update())
                if run["state"] == "running":
                    if result.outcome == "completed":
                        result = Outcome("failed", "execution_failed", "missing_saved_result")
                    await store.db.execute(update(R).where(*store.where(R, R.c.id == run["id"])).values(
                        state=result.outcome, ended_at=receipt.ended_at if result.outcome == "failed" else None,
                        stop_reason=result.error_code, row_version=R.c.row_version + 1))
                elif run["state"] in {"completed", "failed", "unknown"} and run["state"] != result.outcome:
                    result = (Outcome("completed") if run["state"] == "completed"
                        else replace(result, outcome=run["state"], retryable=False,
                                     error_code=result.error_code or "execution_failed"))
            elif result.outcome == "completed":
                result = Outcome("failed", "execution_failed", "missing_saved_run")
            await store.finish_attempt(receipt.attempt_id, **asdict(result), ended_at=receipt.ended_at)
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
