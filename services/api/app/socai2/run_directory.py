"""Read saved Runs with actual task associations; no execution or model calls."""
from sqlalchemy import and_, case, func, literal, select, tuple_, union
from sqlalchemy.exc import DBAPIError

from app.models import socai2 as m

from .baseline_service import BaselineService
from .baseline_store import StoreError, digest
from .enums import Delivery, RunState
from .run_records import RunRecordLimits, cursor_point, make_cursor, subject
from .stage_inputs import VERSION as STAGE_INPUT_VERSION

R, A, I, C, CA, CI, IA, RM, F, AS, D, RES = (model.__table__ for model in (
    m.Runs, m.Alerts, m.Incidents, m.Cases, m.CaseAlerts, m.CaseIncidents,
    m.IncidentAlerts, m.RunMembers, m.Artifacts, m.AlertAssessments, m.IncidentDiagnoses, m.Results))
AT, T = m.AnalysisAttempts.__table__, m.AnalysisTasks.__table__


def run_source():
    # Migration 128 guarantees at most one attempt for a nonnull tenant/Run pair.
    return R.outerjoin(AT, (AT.c.tenant_id == R.c.tenant_id) & (AT.c.run_id == R.c.id)).outerjoin(
        T, (T.c.tenant_id == AT.c.tenant_id) & (T.c.id == AT.c.task_id))


def selection(tenant, query):
    filters = [R.c.tenant_id == tenant]
    if query.subject_type is not None:
        parent = R.c[query.subject_type + "_id"]
        filters.append(parent == query.subject_id if query.subject_id is not None else parent.is_not(None))
    if query.run_kind is not None:
        filters.append(R.c.kind == query.run_kind)
    if query.intent is not None:
        filters.append(T.c.intent == query.intent)
    if query.state is not None:
        filters.append(R.c.state == query.state)
    if query.time_from is not None:
        filters.append(R.c.requested_at >= query.time_from)
    if query.time_to is not None:
        filters.append(R.c.requested_at < query.time_to)
    return filters


def case_relations(scope, tenant):
    """Current real relations, matching E30; never candidate Case IDs."""
    own = select(scope.c.id.label("run_id"), scope.c.case_id).where(scope.c.case_id.is_not(None))
    alerts = select(scope.c.id, CA.c.case_id).select_from(scope.join(CA,
        (CA.c.tenant_id == tenant) & (CA.c.alert_id == scope.c.alert_id)))
    explicit = select(scope.c.id, CI.c.case_id).select_from(scope.join(CI,
        (CI.c.tenant_id == tenant) & (CI.c.incident_id == scope.c.incident_id)))
    shared = select(scope.c.id, CA.c.case_id).select_from(scope.join(IA,
        (IA.c.tenant_id == tenant) & (IA.c.incident_id == scope.c.incident_id)).join(CA,
        (CA.c.tenant_id == tenant) & (CA.c.alert_id == IA.c.alert_id)))
    return union(own, alerts, explicit, shared).cte("related_cases")


async def statistics(store, filters):
    scope = select(R.c.id, R.c.case_id, R.c.alert_id, R.c.incident_id, R.c.state, R.c.delivery_state).select_from(
        run_source()).where(*filters).cte("filtered_runs")
    by_state = {value.value: 0 for value in RunState}
    by_delivery = {value.value: 0 for value in Delivery}
    counts = (await store.db.execute(select(scope.c.state, scope.c.delivery_state, func.count().label("count"))
        .group_by(scope.c.state, scope.c.delivery_state))).mappings()
    total = 0
    for row in counts:
        total += row["count"]
        by_state[row["state"]] += row["count"]
        by_delivery[row["delivery_state"]] += row["count"]
    relations = case_relations(scope, store.tenant_id)
    linked_runs, cases = (await store.db.execute(select(
        func.count(func.distinct(relations.c.run_id)), func.count(func.distinct(relations.c.case_id))))).one()
    return {"total_runs": total, "by_state": by_state, "by_delivery_state": by_delivery,
            "without_related_case_count": total - linked_runs, "related_case_count": cases}


async def input_counts(store, rows):
    values = {row["id"]: None for row in rows}
    cases = [row["id"] for row in rows if row["case_id"] and row["input_artifact_id"]]
    if cases:
        query = select(RM.c.run_id, func.count().label("count")).where(
            *store.where(RM, RM.c.run_id.in_(cases))).group_by(RM.c.run_id)
        for row in (await store.db.execute(query)).mappings():
            values[row["run_id"]] = row["count"]
    stages = [row["id"] for row in rows if row["alert_id"] or row["incident_id"]]
    if stages:
        members = F.c.content_json["members"]
        known = and_(F.c.kind == "input_snapshot", F.c.schema_version == STAGE_INPUT_VERSION,
                     F.c.material_state == "complete", F.c.blob_ref.is_(None),
                     F.c.content_json["version"].astext == STAGE_INPUT_VERSION,
                     F.c.content_json["kind"].astext == R.c.kind,
                     func.jsonb_typeof(members) == "array")
        query = select(R.c.id, case((known, func.jsonb_array_length(members)), else_=None).label("count")).select_from(
            R.join(F, (F.c.tenant_id == R.c.tenant_id) & (F.c.run_id == R.c.id) & (F.c.id == R.c.input_artifact_id))
        ).where(*store.where(R, R.c.id.in_(stages)))
        for row in (await store.db.execute(query)).mappings():
            values[row["id"]] = row["count"]
    return values


async def result_references(store, rows):
    values = {row["id"]: [] for row in rows}
    if not values:
        return values
    for table, result_type, kind in ((AS, "alert_assessment", AS.c.kind),
                                     (D, "incident_diagnosis", literal("incident_diagnosis")),
                                     (RES, "case_result", RES.c.kind)):
        filters = list(store.where(table, table.c.source_run_id.in_(values)))
        if table is AS:
            filters.append(AS.c.kind == "triage")
        query = select(table.c.id, table.c.source_run_id, kind.label("kind")).where(*filters).order_by(table.c.id)
        for row in (await store.db.execute(query)).mappings():
            values[row["source_run_id"]].append({"result_type": result_type, **dict(row)})
    return values


class RunDirectoryService(BaselineService):
    def __init__(self, sessions, *, limits=None):
        super().__init__(sessions)
        self.limits = limits if limits is not None else RunRecordLimits.load()

    async def read(self, tenant, query):
        size = self.limits.page_size(query.limit)
        fingerprint = digest({"tenant": str(tenant), "directory": "runs", "order": "requested_at,id:desc",
                              **query.model_dump(mode="json", exclude={"limit", "cursor"})})
        point = cursor_point(query.cursor, fingerprint, "runs")
        filters = selection(tenant, query)
        try:
            async with self.transaction(tenant, readonly=True) as store:
                summary = await statistics(store, filters)
                if point:
                    filters.append(tuple_(R.c.requested_at, R.c.id) < point)
                source = run_source().outerjoin(A, (A.c.id == R.c.alert_id) & (A.c.tenant_id == R.c.tenant_id)).outerjoin(
                    I, (I.c.id == R.c.incident_id) & (I.c.tenant_id == R.c.tenant_id)).outerjoin(
                    C, (C.c.id == R.c.case_id) & (C.c.tenant_id == R.c.tenant_id))
                columns = [R.c[k] for k in ("id", "kind", "alert_id", "incident_id", "case_id", "state", "delivery_state",
                           "requested_at", "started_at", "ended_at", "input_artifact_id")]
                rows = list((await store.db.execute(select(*columns, T.c.id.label("task_id"), T.c.intent,
                    func.coalesce(C.c.title, I.c.title, A.c.title).label("subject_title"))
                    .select_from(source).where(*filters).order_by(R.c.requested_at.desc(), R.c.id.desc()).limit(size + 1))).mappings())
                more = len(rows) > size
                rows = rows[:size]
                counts = await input_counts(store, rows)
                results = await result_references(store, rows)
                items = [{"run_id": row["id"], **subject(row), "subject_title": row["subject_title"], "run_kind": row["kind"],
                          **{k: row[k] for k in ("task_id", "intent", "state", "delivery_state", "requested_at", "started_at", "ended_at")},
                          "input_member_count": counts[row["id"]], "results": results[row["id"]]} for row in rows]
                return {"items": items, "total": summary["total_runs"], "statistics": summary,
                        "next_cursor": make_cursor(fingerprint, rows[-1], "requested_at") if more else None,
                        "observed_at": await store.now()}
        except DBAPIError:
            raise StoreError("service_unavailable", 503) from None
