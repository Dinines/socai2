"""Transactional lifecycle primitives. No Redis, HTTP, model or automatic producer."""
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from app.models import socai2 as m

from .baseline_store import BaselineStore, StoreError, digest

T, A, S, R = (x.__table__ for x in (m.AnalysisTasks, m.AnalysisAttempts, m.AnalysisSubjectState, m.Runs))
SUBJECTS = {"alert": m.Alerts.__table__, "incident": m.Incidents.__table__, "case": m.Cases.__table__}
KINDS = {"alert_triage": "alert", "incident_diagnosis": "incident", "case_investigation": "case"}


async def active_case_work(store, case_id, *, excluding_attempt_id=None):
    """Running preparation counts even without a Run; ended unknown does not."""
    attempts = select(A.c.id, A.c.run_id).where(*store.where(A,
        A.c.subject_type == "case", A.c.subject_id == case_id, A.c.local_state == "running"))
    if excluding_attempt_id is not None:
        attempts = attempts.where(A.c.id != excluding_attempt_id)
    actual = [dict(r) for r in (await store.db.execute(attempts)).mappings()]
    linked = [a["run_id"] for a in actual if a["run_id"]]
    runs = [dict(r) for r in (await store.db.execute(select(R.c.id, R.c.state).where(
        *store.where(R, R.c.case_id == case_id),
        (R.c.state == "running") | R.c.id.in_(linked)).order_by(R.c.id))).mappings()]
    return actual, runs


class AnalysisTaskStore(BaselineStore):
    def __init__(self, db, tenant_id, policy):
        super().__init__(db, tenant_id)
        self.policy = policy

    async def subject(self, subject_type, subject_id, *, lock=False):
        table = SUBJECTS.get(subject_type)
        if table is None:
            raise StoreError("invalid_input", 422)
        query = select(table).where(*self.where(table, table.c.id == subject_id))
        row = await self.one(query.with_for_update() if lock else query)
        if row is None:
            raise StoreError("subject_not_found", 404)
        return row

    async def task(self, task_id, *, lock=True):
        query = select(T).where(*self.where(T, T.c.id == task_id))
        row = await self.one(query.with_for_update() if lock else query)
        if row is None:
            raise StoreError("analysis_task_not_found", 404)
        return row

    async def register(self, subject_type, subject_id, now):
        await self.db.execute(insert(S).values(tenant_id=self.tenant_id, subject_type=subject_type,
            subject_id=subject_id, registered_at=now).on_conflict_do_nothing())

    async def accept(self, *, kind, subject_id, intent, source, operation_key,
                     submitted_by=None, request_payload=None, observed_input_digest=None):
        # Dedicated and knowledge flows are wired in later bounded steps.
        if kind not in KINDS or intent not in {"initial", "check", "rerun"}:
            raise StoreError("analysis_intent_not_implemented", 501)
        if (source not in {"ingress", "case_create", "periodic", "user"}
                or not isinstance(operation_key, UUID) or not isinstance(subject_id, UUID)
                or request_payload not in (None, {})):
            raise StoreError("invalid_input", 422)
        subject_type = KINDS[kind]
        fingerprint = digest({"kind": kind, "subject_type": subject_type, "subject_id": str(subject_id),
            "intent": intent, "source": source, "submitted_by": str(submitted_by) if submitted_by else None,
            "request_payload": {}})
        prior = await self.one(select(T).where(*self.where(T,
            T.c.kind == kind, T.c.operation_key == operation_key)))
        if prior:
            if prior["request_hash"] != fingerprint:
                raise StoreError("operation_key_conflict")
            return dict(prior)
        subject = await self.subject(subject_type, subject_id, lock=True)
        if subject["handling_status"] in {"resolved", "completed"}:
            raise StoreError("subject_closed")
        if subject_type in {"case", "incident"}:
            members = m.CaseAlerts.__table__ if subject_type == "case" else m.IncidentAlerts.__table__
            if not await self.one(select(members.c.alert_id).where(*self.where(members,
                    members.c[subject_type + "_id"] == subject_id)).limit(1)):
                raise StoreError("subject_scope_empty")
        now = await self.now()
        values = {"tenant_id": self.tenant_id, "id": uuid4(), "kind": kind, "subject_type": subject_type,
            "subject_id": subject_id, "intent": intent, "source": source, "operation_key": operation_key,
            "request_hash": fingerprint, "request_payload": {}, "submitted_at": now, "submitted_by": submitted_by,
            "state": "accepted", "retry_limit": self.policy.retry_limit,
            "retry_delay_seconds": self.policy.retry_delay_seconds, "observed_input_digest": observed_input_digest}
        row = await self.one(insert(T).values(**values).on_conflict_do_nothing(
            constraint="analysis_tasks_operation_once").returning(T))
        if row is None:
            row = await self.one(select(T).where(*self.where(T, T.c.kind == kind, T.c.operation_key == operation_key)))
            if row["request_hash"] != fingerprint:
                raise StoreError("operation_key_conflict")
        await self.register(subject_type, subject_id, now)
        return dict(row)

    async def automatic_status(self, subject_type, subject_id):
        subject = await self.subject(subject_type, subject_id)
        state = await self.one(select(S).where(*self.where(S,
            S.c.subject_type == subject_type, S.c.subject_id == subject_id)))
        last = state["last_normal_completed_at"] if state else None
        created = subject["ingested_at"] if subject_type == "alert" else subject["created_at"]
        expires = (last or created) + timedelta(seconds=self.policy.automatic_window_seconds)
        now = await self.now()
        reason = ("not_periodic" if subject_type == "alert" else "not_registered" if state is None
            else "closed" if subject["handling_status"] == "resolved" else "expired" if now >= expires
            else state["automatic_stop_reason"])
        return {"eligible": reason is None, "last_normal_completed_at": last,
            "auto_expires_at": expires if subject_type != "alert" else None,
            "next_check_at": state["next_check_at"] if state and subject_type != "alert" else None,
            "ineligible_reason": reason}

    async def skip(self, task_id, reason_code):
        task = await self.task(task_id)
        if task["state"] not in {"accepted", "waiting"}:
            raise StoreError("analysis_task_not_unstarted")
        if reason_code not in {"no_changes", "closed_before_start", "automatic_attempts_stopped"}:
            raise StoreError("invalid_input", 422)
        return await self.one(update(T).where(*self.where(T, T.c.id == task_id)).values(
            state="skipped", reason_code=reason_code, next_retry_at=None, ended_at=await self.now()).returning(T))

    async def start_attempt(self, task_id, *, started_at=None):
        task = await self.task(task_id)
        if task["state"] not in {"accepted", "waiting"}:
            raise StoreError("analysis_task_not_waiting")
        subject = await self.subject(task["subject_type"], task["subject_id"], lock=True)
        now = await self.now()
        began = started_at or now
        if began.tzinfo is None or began > now:
            raise StoreError("invalid_attempt_start", 422)
        retry = task["started_at"] is not None
        if subject["handling_status"] in {"resolved", "completed"}:
            if retry:
                await self.stop_retry(task, "retry_stopped", now)
            else:
                await self.skip(task_id, "closed_before_start")
            return None
        if retry:
            status = await self.automatic_status(task["subject_type"], task["subject_id"])
            # Alert has no periodic scan, but a bounded first-triage retry is allowed.
            if (task["retry_count"] >= task["retry_limit"]
                    or status["ineligible_reason"] in {"expired", "closed"}):
                await self.stop_retry(task, "retry_stopped", now)
                return None
            if task["next_retry_at"] is None or now < task["next_retry_at"]:
                raise StoreError("retry_not_due")
        if await self.one(select(A.c.id).where(*self.where(A, A.c.subject_type == task["subject_type"],
                A.c.subject_id == task["subject_id"], A.c.kind == task["kind"], A.c.local_state == "running"))):
            raise StoreError("analysis_subject_busy")
        field = R.c[task["subject_type"] + "_id"]
        if await self.one(select(R.c.id).where(*self.where(R, field == task["subject_id"],
                R.c.state == "running")).limit(1)):
            raise StoreError("analysis_subject_busy")
        attempt_no = (await self.db.execute(select(func.coalesce(func.max(A.c.attempt_no), 0)).where(
            *self.where(A, A.c.task_id == task_id)))).scalar_one() + 1
        await self.db.execute(update(T).where(*self.where(T, T.c.id == task_id)).values(
            state="running", started_at=task["started_at"] or began, reason_code=None, error_detail=None,
            next_retry_at=None, retry_count=task["retry_count"] + int(retry)))
        attempt = await self.one(insert(A).values(tenant_id=self.tenant_id, id=uuid4(), task_id=task_id,
            attempt_no=attempt_no, subject_type=task["subject_type"], subject_id=task["subject_id"],
            kind=task["kind"], started_at=began, local_state="running").returning(A))
        await self.db.execute(update(S).where(*self.where(S, S.c.subject_type == task["subject_type"],
            S.c.subject_id == task["subject_id"])).values(last_attempt_id=attempt["id"]))
        return dict(attempt)

    async def attempt(self, attempt_id):
        row = await self.one(select(A).where(*self.where(A, A.c.id == attempt_id)).with_for_update())
        if row is None:
            raise StoreError("analysis_attempt_not_found", 404)
        return row

    async def bind_run(self, attempt_id, run_id, *, input_digest, previous_run_id=None,
                       comparison_result_id=None, policy_artifact_id=None):
        attempt = await self.attempt(attempt_id)
        if attempt["local_state"] != "running" or attempt["run_id"] is not None:
            raise StoreError("analysis_attempt_already_bound")
        run = await self.one(select(R).where(*self.where(R, R.c.id == run_id)))
        if run is None:
            raise StoreError("run_not_found", 404)
        if run["input_artifact_id"] is None:
            raise StoreError("run_input_not_frozen")
        return await self.one(update(A).where(*self.where(A, A.c.id == attempt_id)).values(
            run_id=run_id, input_artifact_id=run["input_artifact_id"], input_digest=input_digest,
            previous_run_id=previous_run_id, comparison_result_id=comparison_result_id,
            policy_artifact_id=policy_artifact_id).returning(A))

    async def stop_retry(self, task, reason, now):
        await self.db.execute(update(T).where(*self.where(T, T.c.id == task["id"])).values(
            state="failed", reason_code=reason, next_retry_at=None, ended_at=now))
        previous = await self.one(select(A).where(*self.where(A, A.c.task_id == task["id"]))
            .order_by(A.c.attempt_no.desc()).limit(1))
        await self.stop_subject(task, previous, reason)

    async def stop_subject(self, task, attempt, reason):
        if task["intent"] == "targeted" or task["kind"] == "knowledge_sync":
            return
        if task["intent"] == "synthesis" and (attempt is None or attempt["input_artifact_id"] is None):
            return
        await self.db.execute(update(S).where(*self.where(S, S.c.subject_type == task["subject_type"],
            S.c.subject_id == task["subject_id"])).values(stopped_task_id=task["id"],
            stopped_input_digest=(attempt["input_digest"] if attempt else None) or task["observed_input_digest"],
            automatic_stop_reason=reason))
        if task["subject_type"] in {"incident", "case"}:
            interval = self.policy.incident_check_interval_seconds if task["subject_type"] == "incident" else self.policy.case_check_interval_seconds
            await self.db.execute(update(S).where(*self.where(S, S.c.subject_type == task["subject_type"],
                S.c.subject_id == task["subject_id"])).values(next_check_at=func.coalesce(S.c.next_check_at,
                    (await self.now()) + timedelta(seconds=interval))))

    async def finish_attempt(self, attempt_id, *, outcome, error_code=None, error_stage=None,
                             error_detail=None, retryable=False, retry_after=None, ended_at=None):
        attempt = await self.attempt(attempt_id)
        task = await self.task(attempt["task_id"])
        if attempt["local_state"] != "running" or task["state"] != "running":
            raise StoreError("analysis_attempt_already_ended")
        if outcome not in {"completed", "failed", "unknown"} or (outcome != "completed" and not error_code):
            raise StoreError("invalid_input", 422)
        if (error_detail is not None and (not isinstance(error_detail, dict)
                or set(error_detail) - {"exception_type", "http_status", "stage", "code"}
                or any(not isinstance(v, (str, int, bool)) for v in error_detail.values()))):
            raise StoreError("invalid_error_detail", 422)
        now = ended_at or await self.now()
        if now.tzinfo is None or now < attempt["started_at"]:
            raise StoreError("invalid_attempt_end", 422)
        # The caller invokes this only after its execution handle has actually ended.
        # Preserve unknown Runs and their NULL ended_at; do not rewrite remote outcomes.
        if attempt["run_id"]:
            run = await self.one(select(R).where(*self.where(R, R.c.id == attempt["run_id"])).with_for_update())
            if outcome == "unknown" and run["state"] == "running":
                await self.db.execute(update(R).where(*self.where(R, R.c.id == run["id"])).values(
                    state="unknown", row_version=R.c.row_version + 1))
            elif run["state"] != outcome:
                raise StoreError("analysis_run_outcome_mismatch")
        known_retry = outcome == "failed" and retryable
        ended = await self.one(update(A).where(*self.where(A, A.c.id == attempt_id)).values(
            local_state="ended", local_ended_at=now, outcome=outcome,
            failed_at=now if outcome != "completed" else None, error_code=error_code,
            error_stage=error_stage, error_detail=error_detail, retryable=known_retry).returning(A))
        if outcome == "completed":
            await self.db.execute(update(T).where(*self.where(T, T.c.id == task["id"])).values(
                state="completed", ended_at=now, reason_code=None, next_retry_at=None))
            if task["intent"] != "targeted" and task["kind"] != "knowledge_sync":
                interval = {"case": self.policy.case_check_interval_seconds,
                            "incident": self.policy.incident_check_interval_seconds}.get(task["subject_type"])
                await self.db.execute(update(S).where(*self.where(S, S.c.subject_type == task["subject_type"],
                    S.c.subject_id == task["subject_id"])).values(last_completed_attempt_id=attempt_id,
                    last_normal_completed_at=now, next_check_at=now + timedelta(seconds=interval) if interval else None,
                    stopped_input_digest=None, stopped_task_id=None, automatic_stop_reason=None))
        else:
            status = await self.automatic_status(task["subject_type"], task["subject_id"])
            subject = await self.subject(task["subject_type"], task["subject_id"])
            eligible = (subject["handling_status"] not in {"resolved", "completed"}
                and status["ineligible_reason"] not in {"expired", "closed"})
            may_retry = known_retry and task["retry_count"] < task["retry_limit"] and eligible
            reason = ("retry_scheduled" if may_retry else "retry_stopped" if known_retry and not eligible
                else "retry_exhausted" if known_retry and task["retry_count"] >= task["retry_limit"] else error_code)
            earliest = now + timedelta(seconds=task["retry_delay_seconds"])
            if retry_after is not None:
                if retry_after.tzinfo is None:
                    raise StoreError("invalid_input", 422)
                earliest = max(earliest, retry_after)
            await self.db.execute(update(T).where(*self.where(T, T.c.id == task["id"])).values(
                state="waiting" if may_retry else "failed", reason_code=reason, error_detail=error_detail,
                next_retry_at=earliest if may_retry else None, ended_at=None if may_retry else now,
                last_enqueued_at=None if may_retry else task["last_enqueued_at"]))
            if not may_retry:
                await self.stop_subject(task, ended, reason)
        return dict(ended)
