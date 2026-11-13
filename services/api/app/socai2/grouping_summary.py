"""Count incident grouping within one alert scope; no HTTP or model calls."""
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from app.models import socai2 as m

from .baseline_service import BaselineService
from .grouping_contracts import GroupingSummary
from .read_sources import lookup_error

A, I, L = (x.__table__ for x in (m.Alerts, m.Incidents, m.IncidentAlerts))


class GroupingSummaryService(BaselineService):
    async def read(self, tenant, query):
        clauses = [A.c.tenant_id == tenant]
        if query.source_namespace is not None:
            clauses.append(A.c.source_namespace == query.source_namespace)
        if query.time_from is not None:
            clauses.append(A.c.event_time >= query.time_from)
        if query.time_to is not None:
            clauses.append(A.c.event_time < query.time_to)
        scoped = select(A.c.id).where(*clauses).cte("scoped_alerts")
        members = select(L.c.alert_id, L.c.incident_id, I.c.handling_status).select_from(
            scoped.join(L, (L.c.alert_id == scoped.c.id) & (L.c.tenant_id == tenant)).join(
                I, (I.c.id == L.c.incident_id) & (I.c.tenant_id == tenant))
        ).cte("scoped_members")
        statement = select(
            select(func.count()).select_from(scoped).scalar_subquery().label("alert_count"),
            select(func.count(func.distinct(members.c.alert_id))).scalar_subquery().label("grouped_alert_count"),
            select(func.count(func.distinct(members.c.incident_id))).scalar_subquery().label("incident_count"),
            select(func.count(func.distinct(members.c.incident_id))).where(
                members.c.handling_status == "in_progress").scalar_subquery().label("in_progress_incident_count"),
        )
        try:
            async with self.transaction(tenant, readonly=True) as store:
                counts = dict((await store.db.execute(statement)).mappings().one())
                grouped, incidents = counts["grouped_alert_count"], counts["incident_count"]
                return GroupingSummary(scope=query, **counts,
                    ungrouped_alert_count=counts["alert_count"] - grouped,
                    compression_rate=(grouped - incidents) / grouped if grouped else None,
                    observed_at=await store.now())
        except DBAPIError as exc:
            lookup_error(exc)
