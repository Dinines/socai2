"""Settle known unsent calls without rewriting an uncertain execution."""
import json

from sqlalchemy import select, update

from app.models import socai2 as models

from .analysis_dispatch_types import ExecutionFailure, classify_failure


def unsent_failure(exc):
    outcome = classify_failure(exc, stage="execute")
    if (outcome.retryable and outcome.error_code == "service_unavailable"
            and (not isinstance(exc, ExecutionFailure) or exc.not_executed)):
        return outcome
    return None


async def settle_unsent(store, run, exc):
    """Call only while holding the Run lock; prior uncertain operations win."""
    outcome = unsent_failure(exc) if exc is not None else None
    if outcome is None or run["state"] != "running":
        return False
    steps, runs = models.RunSteps.__table__, models.Runs.__table__
    unsettled = await store.one(select(steps.c.id).where(*store.where(steps,
        steps.c.run_id == run["id"], steps.c.kind.in_(["model", "tool"]),
        steps.c.state.in_(["running", "unknown"]))).limit(1))
    if unsettled:
        return False
    now = await store.now()
    detail = {"code": outcome.error_code, "message": outcome.error_code,
              "retryable": True, "occurred_at": now.isoformat(), **outcome.error_detail}
    await store.db.execute(update(steps).where(*store.where(steps,
        steps.c.run_id == run["id"], steps.c.state == "running"))
        .values(state="failed", ended_at=now, error=detail))
    await store.db.execute(update(steps).where(*store.where(steps,
        steps.c.run_id == run["id"], steps.c.state == "planned"))
        .values(state="skipped", ended_at=now, error=detail))
    await store.db.execute(update(runs).where(*store.where(runs, runs.c.id == run["id"]))
        .values(state="failed", ended_at=now, stop_reason=outcome.error_code,
                stop_detail=json.dumps(outcome.error_detail), row_version=runs.c.row_version + 1))
    return True
