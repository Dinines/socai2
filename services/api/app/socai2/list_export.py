"""Complete, bounded list reads in one snapshot; no HTTP or file format here."""
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import column, func, select, table, text
from sqlalchemy.exc import DBAPIError

from app.models import socai2 as m

from . import list_query as lists
from .baseline_service import BaselineService
from .baseline_store import StoreError
from .case_contracts import CaseView, project
from .case_reader import queue_filters, queue_open_tasks
from .page_contracts import AlertFacts, IncidentFacts
from .page_reader import PageReader
from .program_facts import RANK
from .read_sources import lookup_error

C, CA, A, I, L = (x.__table__ for x in (m.Cases, m.CaseAlerts, m.Alerts, m.Incidents, m.IncidentAlerts))
OWNERS = table("users", column("tenant_id"), column("id"), column("username"), schema="public")
REVERSE_RANK = {v: k for k, v in RANK.items()}


@dataclass(frozen=True)
class ExportLimits:
    max_rows: int
    max_bytes: int
    statement_timeout_ms: int

    @classmethod
    def load(cls):
        path = Path(os.environ.get("SOCAI2_EXPORT_CONFIG_FILE", Path(__file__).with_suffix(".json")))
        values = json.loads(path.read_text())
        if set(values) != {"max_rows", "max_bytes", "statement_timeout_ms"} or any(
            type(v) is not int or v < 1 for v in values.values()
        ):
            raise ValueError("invalid_list_export_configuration")
        return cls(**values)


@dataclass(frozen=True)
class ExportRows:
    rows: list[dict]
    observed_at: datetime
    max_bytes: int


class ListExportService(BaselineService):
    def __init__(self, sessions, *, limits=None):
        super().__init__(sessions)
        self.limits = limits or ExportLimits.load()

    async def read(self, tenant, kind, query):
        if kind not in {"alerts", "incidents", "cases"}:
            raise StoreError("export_subject_invalid", 422)
        if query.cursor is not None or getattr(query, "before_id", None) is not None:
            raise StoreError("export_pagination_not_supported", 422)
        try:
            async with self.transaction(tenant, readonly=True) as store:
                await store.db.execute(text("SELECT set_config('statement_timeout', :timeout, true)"),
                    {"timeout": str(self.limits.statement_timeout_ms)})
                if kind == "cases":
                    source, model, prefix = C, CaseView, "case"
                    clauses = queue_filters(tenant, query)
                    sort_by, order = query.sort_by or "business_updated_at", query.sort_order or "desc"
                    sort_column = lists.severity_rank(C.c.severity) if sort_by == "severity" else C.c[sort_by]
                    extra = [select(func.count()).select_from(CA).where(
                        CA.c.tenant_id == tenant, CA.c.case_id == C.c.id).correlate(C).scalar_subquery().label("member_count"),
                        queue_open_tasks(tenant).scalar_subquery().label("open_task_count")]
                else:
                    source, model, prefix = (A if kind == "alerts" else I), (AlertFacts if kind == "alerts" else IncidentFacts), "facts"
                    clauses, sort_column, _, order = PageReader(store, kind).selection(query)
                    extra = [select(OWNERS.c.username).where(OWNERS.c.tenant_id == tenant,
                        OWNERS.c.id == source.c.owner_id).correlate(source).scalar_subquery().label("owner_name")]
                    if kind == "incidents":
                        members = L.join(A, (L.c.tenant_id == A.c.tenant_id) & (L.c.alert_id == A.c.id))
                        scope = [L.c.tenant_id == tenant, L.c.incident_id == I.c.id]
                        for name, expression in (("member_count", func.count()),
                                ("first_activity_at", func.min(A.c.event_time)),
                                ("last_activity_at", func.max(A.c.event_time)),
                                ("severity_rank", func.max(lists.severity_rank(A.c.severity)))):
                            extra.append(select(expression).select_from(members).where(*scope).correlate(I).scalar_subquery().label(name))
                count = (await store.db.execute(select(func.count()).select_from(source).where(*clauses))).scalar_one()
                if count > self.limits.max_rows:
                    raise StoreError("export_row_limit_exceeded", 413)
                selected = (await store.db.execute(select(*[source.c[f] for f in model.model_fields], *extra)
                    .where(*clauses).order_by(*lists.ordering(sort_column, source.c.id, order))
                    .limit(self.limits.max_rows + 1))).mappings().all()
                if len(selected) != count:
                    raise StoreError("export_snapshot_incomplete", 503)
                rows = []
                for row in selected:
                    item = {prefix: project(model, row).model_dump(mode="json")}
                    if kind == "cases":
                        item.update(member_count=row["member_count"], open_task_count=row["open_task_count"])
                    else:
                        item["owner_name"] = row["owner_name"]
                        if kind == "incidents":
                            automatic = REVERSE_RANK.get(row["severity_rank"])
                            effective = row["severity_override"] or automatic
                            item["derived"] = {k: row[k] for k in ("member_count", "first_activity_at", "last_activity_at")}
                            item["derived"].update(severity_auto=automatic, severity_effective=effective,
                                severity_source="manual_override" if row["severity_override"] else "member_max" if automatic else None)
                    rows.append(item)
                return ExportRows(rows, await store.now(), self.limits.max_bytes)
        except DBAPIError as exc:
            cause = exc.orig
            state = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
            if state == "57014" or getattr(cause.__cause__, "sqlstate", None) == "57014":
                raise StoreError("export_query_timeout", 503) from None
            lookup_error(exc)
