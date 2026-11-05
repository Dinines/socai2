"""Baseline metadata shared by history and actual execution readers."""
from sqlalchemy import func

from app.models.investigation import InvestigationRun

PENDING_BASELINE = "pending_update"
ACTIVE_STATUSES = ("queued", "running", "unknown", "awaiting_human")


def history_time():
    """Use a stable creation timestamp while no actual start exists."""
    return func.coalesce(InvestigationRun.started_at, InvestigationRun.created_at)


def baseline_fields(run):
    data = run.raw_alert or {}
    return {"investigation_kind": run.investigation_kind,
            "scope_revision": run.scope_revision,
            "scope_updated_at": run.scope_updated_at,
            "requested_at": run.created_at,
            "started_at": run.started_at, "completed_at": run.completed_at,
            "baseline": data.get("baseline"),
            "can_start_baseline": bool(run.investigation_kind == "baseline"
                and run.status == PENDING_BASELINE and (data.get("scope") or {}).get("selected_member_ids"))}
