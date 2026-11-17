"""Server-owned Case query preparation, frozen before C1-C6 starts."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from .baseline_context import Omission


@dataclass(frozen=True)
class CaseExecutionPolicy:
    before_seconds: int
    after_seconds: int
    max_rows_per_query: int

    def __post_init__(self):
        if (any(type(v) is not int or v < 0 for v in (self.before_seconds, self.after_seconds))
                or self.before_seconds + self.after_seconds == 0
                or type(self.max_rows_per_query) is not int or self.max_rows_per_query < 1):
            raise ValueError("invalid Case execution configuration")

    @classmethod
    def from_config(cls, value):
        if (set(value) != {"query_window", "log_query"}
                or set(value["query_window"]) != {"before_seconds", "after_seconds"}
                or set(value["log_query"]) != {"max_rows_per_query"}):
            raise ValueError("invalid Case execution configuration")
        return cls(**value["query_window"], **value["log_query"])

    def snapshot(self):
        return {"query_window": {"before_seconds": self.before_seconds, "after_seconds": self.after_seconds},
                "log_query": {"max_rows_per_query": self.max_rows_per_query}}


def event_time(alert):
    value = alert.get("event_time")
    if alert.get("event_time_source") not in {"source", "derived_source"} or not value:
        return None
    try:
        value = datetime.fromisoformat(value) if isinstance(value, str) else value
    except ValueError:
        return None
    return value if isinstance(value, datetime) and value.tzinfo is not None else None


def window(context, alert_ids, policy):
    times = [value for aid in alert_ids if (value := event_time(context.alerts[str(aid)].alert)) is not None]
    if not times:
        return None, None
    return min(times) - timedelta(seconds=policy.before_seconds), max(times) + timedelta(seconds=policy.after_seconds)


def prepare(context, policy, limits):
    start, end = window(context, context.alerts, policy)
    missing = sorted(aid for aid, item in context.alerts.items() if event_time(item.alert) is None)
    scope = context.scope.model_copy(update={"window_start": start, "window_end": end})
    return context.model_copy(update={
        "scope": scope,
        "questions": [question.model_copy(update={"scope": scope}) for question in context.questions],
        "query_preparation": {**policy.snapshot(),
            "effective_max_rows_per_query": min(policy.max_rows_per_query, limits.max_rows_per_query or 0),
            "missing_time_alert_ids": missing},
        "omissions": [*context.omissions, *(Omission(section="log_query", source_id=UUID(aid),
            reason="reliable_alert_time_unavailable") for aid in missing)],
    })


def binding_scope(context, alert_ids):
    scope = context.scope.model_dump(mode="json")
    if context.query_preparation is not None:
        config = context.query_preparation
        policy = CaseExecutionPolicy.from_config({key: config[key] for key in ("query_window", "log_query")})
        start, end = window(context, alert_ids, policy)
        scope.update(window_start=start.isoformat() if start else None, window_end=end.isoformat() if end else None)
    return scope


def initial_input_versions(context):
    """Initial-only gate: exact selected identities, never a clock or Case output.

    Periodic checks and business-content comparison belong to the next step.
    The immutable C1 artifact retains the complete rows and source roles.
    """
    return {"alerts": {aid: {"material": item.alert["latest_material_id"],
                "triage": item.triage["id"] if item.triage_usable else None,
                "feedback": item.feedback["id"] if item.feedback else None}
            for aid, item in sorted(context.alerts.items())},
        "incidents": {iid: item.diagnosis["id"] if item.diagnosis_usable else None
            for iid, item in sorted(context.incidents.items())},
        "human_feedback": {tid: item.revision["id"] for tid, item in sorted(context.tasks.items())
            if item.usable_feedback}}
