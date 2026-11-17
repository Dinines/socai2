"""Core task acceptance and reads; HTTP owns URLs and external route wiring."""
import base64
import binascii
import json
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.exc import IntegrityError

from app.models import socai2 as m

from .analysis_task_store import A, AnalysisTaskStore, T
from .baseline_service import BaselineService
from .baseline_store import StoreError, digest


def cursor_point(cursor, fingerprint):
    try:
        value = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        if set(value) != {"scope", "at", "id"} or value["scope"] != fingerprint:
            raise ValueError("cursor scope mismatch")
        at = datetime.fromisoformat(value["at"])
        if at.tzinfo is None:
            raise ValueError("timezone required")
        return at, UUID(value["id"])
    except (ValueError, TypeError, KeyError, binascii.Error):
        raise StoreError("invalid_cursor", 422) from None


async def project_task(store, original):
    root = await store.task(original["merged_into_task_id"], lock=False) if original["merged_into_task_id"] else original
    if root["state"] == "merged":
        raise StoreError("analysis_task_link_invalid", 503)
    attempts = [dict(row) for row in (await store.db.execute(select(A).where(
        *store.where(A, A.c.task_id == root["id"])).order_by(A.c.attempt_no))).mappings()]
    run_ids = [a["run_id"] for a in attempts if a["run_id"]]
    results = []
    for result_type, table, result_kind in (
            ("case_result", m.Results.__table__, m.Results.kind),
            ("alert_assessment", m.AlertAssessments.__table__, m.AlertAssessments.kind),
            ("incident_diagnosis", m.IncidentDiagnoses.__table__, literal("incident_diagnosis"))):
        if run_ids:
            query = select(table.c.id, table.c.source_run_id, result_kind.label("kind")).where(
                *store.where(table, table.c.source_run_id.in_(run_ids)))
            if result_type == "alert_assessment":
                query = query.where(table.c.kind == "triage")
            rows = (await store.db.execute(query.order_by(table.c.id))).mappings()
            results.extend({"result_type": result_type, **dict(row)} for row in rows)
    fields = ("attempt_no", "run_id", "started_at", "local_ended_at", "interruption_observed_at",
              "local_state", "outcome", "failed_at", "error_code", "error_stage", "error_detail", "retryable")
    return {"task_id": original["id"], **{k: original[k] for k in (
        "subject_type", "subject_id", "kind", "intent", "source", "submitted_at", "request_payload")},
        "status": "accepted" if root["state"] in {"accepted", "waiting"} else root["state"],
        **{k: root[k] for k in ("reason_code", "started_at", "ended_at", "retry_count", "next_retry_at")},
        "latest_run_id": run_ids[-1] if run_ids else None,
        "attempts": [{k: a[k] for k in fields} for a in attempts], "results": results}


class AnalysisTaskService(BaselineService):
    def __init__(self, session_factory, policy):
        super().__init__(session_factory)
        self.policy = policy

    @asynccontextmanager
    async def transaction(self, tenant_id, *, readonly=False):
        try:
            async with super().transaction(tenant_id, readonly=readonly) as store:
                yield AnalysisTaskStore(store.db, tenant_id, self.policy)
        except IntegrityError as exc:
            diag = getattr(exc.orig, "diag", None)
            constraint = getattr(diag, "constraint_name", None) or getattr(exc.orig.__cause__, "constraint_name", None)
            codes = {"analysis_attempts_one_active": "analysis_subject_busy",
                     "analysis_attempts_run_once": "analysis_run_already_bound",
                     "analysis_tasks_operation_once": "operation_key_conflict"}
            if constraint in codes:
                raise StoreError(codes[constraint]) from exc
            raise

    async def submit(self, tenant_id, **request):
        async with self.transaction(tenant_id) as store:
            row = await store.accept(**request)
            return {"task_id": row["id"], "subject_type": row["subject_type"],
                    "subject_id": row["subject_id"], "status": "accepted"}

    async def read_task(self, tenant_id, subject_type, subject_id, task_id):
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.subject(subject_type, subject_id)
            task = await store.task(task_id, lock=False)
            if (task["subject_type"], task["subject_id"]) != (subject_type, subject_id) or task["kind"] == "knowledge_sync":
                raise StoreError("analysis_task_not_found", 404)
            return await project_task(store, task)

    async def list_tasks(self, tenant_id, subject_type, subject_id, *, limit=None, cursor=None):
        limit = self.policy.page_size(limit)
        fingerprint = digest({"tenant": str(tenant_id), "type": subject_type, "id": str(subject_id)})
        point = cursor_point(cursor, fingerprint) if cursor else None
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.subject(subject_type, subject_id)
            filters = store.where(T, T.c.subject_type == subject_type, T.c.subject_id == subject_id,
                                  T.c.kind != "knowledge_sync")
            total = (await store.db.execute(select(func.count()).select_from(T).where(*filters))).scalar_one()
            query = select(T).where(*filters)
            if point:
                query = query.where(tuple_(T.c.submitted_at, T.c.id) < tuple_(*point))
            rows = list((await store.db.execute(query.order_by(T.c.submitted_at.desc(), T.c.id.desc())
                                               .limit(limit + 1))).mappings())
            next_cursor = None
            if len(rows) > limit:
                last = rows[limit - 1]
                next_cursor = base64.urlsafe_b64encode(json.dumps({"scope": fingerprint,
                    "at": last["submitted_at"].isoformat(), "id": str(last["id"])}).encode()).decode()
            return {"subject_type": subject_type, "subject_id": subject_id,
                "items": [await project_task(store, row) for row in rows[:limit]], "total": total,
                "next_cursor": next_cursor, "observed_at": await store.now(),
                "update_state": await store.automatic_status(subject_type, subject_id)}
