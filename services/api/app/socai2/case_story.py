"""One read-only snapshot for the existing Case story; no execution or writes."""
import base64
import binascii
from uuid import UUID

from sqlalchemy import String, case, cast, func, literal, or_, select

from app.models import socai2 as m

from .baseline_service import BaselineService
from .baseline_store import CA, RES, A, R, StoreError, digest
from .case_comparison import project_comparison
from .case_contracts import ResultView, RunView, project
from .case_story_contracts import StoryCursor, StoryEntry, StoryPage
from .human_task_contracts import TaskRevisionView
from .list_query import ordering, seek
from .page_contracts import AlertFacts

T, V, O = m.Tasks.__table__, m.TaskRevisions.__table__, m.AlertObjects.__table__
TERMINAL = ("completed", "failed", "cancelled")


def fingerprint(tenant, case_id, query):
    return digest({"tenant": str(tenant), "case": str(case_id),
        **query.model_dump(mode="json", exclude={"limit", "cursor"})})


def read_cursor(tenant, case_id, query):
    if query.cursor is None:
        return None
    try:
        raw = base64.b64decode(query.cursor, altchars=b"-_", validate=True)
        point = StoryCursor.model_validate_json(raw)
        UUID(point.key.split(":", 1)[1])
    except (ValueError, TypeError, binascii.Error):
        raise StoreError("invalid_story_cursor", 422) from None
    if point.fingerprint != fingerprint(tenant, case_id, query):
        raise StoreError("story_cursor_filters_changed", 422)
    return point


def matches(value, *columns):
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return or_(*(column.ilike("%" + escaped + "%", escape="\\") for column in columns))


def result_scope(tenant, case_id, run_id):
    return (RES.c.tenant_id == tenant, RES.c.case_id == case_id,
        RES.c.source_run_id == run_id, RES.c.kind == "baseline")


def story_index(tenant, case_id, query):
    def columns(kind, identity, at):
        return ((literal(kind + ":") + cast(identity, String)).label("key"),
            literal(kind).label("kind"), identity.label("source_id"), at.label("at"))

    alerts = select(*columns("alert", A.c.id, A.c.event_time)).select_from(CA.join(A,
        (A.c.tenant_id == CA.c.tenant_id) & (A.c.id == CA.c.alert_id))).where(
            CA.c.tenant_id == tenant, CA.c.case_id == case_id)
    if query.severity is not None:
        alerts = alerts.where(A.c.severity == query.severity)
    if query.q:
        objects = select(O.c.id).where(O.c.tenant_id == tenant, O.c.alert_id == A.c.id,
            O.c.material_id == A.c.latest_material_id, O.c.object_type.in_(["host", "user"]),
            matches(query.q, O.c.raw_value, O.c.normalized_value)).exists()
        alerts = alerts.where(or_(matches(query.q, A.c.title, A.c.description), objects))
    run_time = case((R.c.state.in_(TERMINAL), R.c.ended_at),
        (R.c.state.in_(["running", "unknown"]), R.c.started_at), else_=None)
    runs = select(*columns("investigation", R.c.id, run_time)).where(
        R.c.tenant_id == tenant, R.c.case_id == case_id, R.c.kind == "baseline")
    if query.q:
        results = select(RES.c.id).where(*result_scope(tenant, case_id, R.c.id),
            R.c.state.in_(TERMINAL), matches(query.q, RES.c.title, RES.c.conclusion,
                RES.c.change_summary)).exists()
        runs = runs.where(or_(matches(query.q, R.c.title, R.c.purpose), results))
    human = select(*columns("human_result", V.c.id, V.c.completed_at)).where(
        V.c.tenant_id == tenant, V.c.case_id == case_id, V.c.state == "completed")
    if query.q:
        human = human.where(matches(query.q, V.c.title, V.c.description, V.c.result_text))
    return alerts.union_all(runs, human).subquery()


class CaseStoryService(BaselineService):
    async def read(self, tenant_id, case_id, query):
        point = read_cursor(tenant_id, case_id, query)
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.case(case_id, lock=False)
            index = story_index(tenant_id, case_id, query)
            total = (await store.db.execute(select(func.count()).select_from(index))).scalar_one()
            statement = select(index).order_by(*ordering(index.c.at, index.c.key, "desc"))
            if point:
                statement = statement.where(seek(index.c.at, index.c.key, point.at, point.key, "desc"))
            rows = (await store.db.execute(statement.limit(query.limit + 1))).mappings().all()
            page = rows[:query.limit]
            items = [await self.entry(store, case_id, row) for row in page]
            cursor = None
            if len(rows) > query.limit:
                last = page[-1]
                value = StoryCursor(fingerprint=fingerprint(tenant_id, case_id, query), at=last["at"], key=last["key"])
                cursor = base64.urlsafe_b64encode(value.model_dump_json().encode()).decode()
            return StoryPage(items=items, total=total, next_cursor=cursor, observed_at=await store.now())

    async def entry(self, store, case_id, index):
        values = {"id": index["key"], "kind": index["kind"], "occurred_at": index["at"]}
        identity = index["source_id"]
        if index["kind"] == "alert":
            row = await store.one(select(A).where(*store.where(A, A.c.id == identity)))
            return StoryEntry(**values, time_source="event_time" if index["at"] else "unknown",
                alert=project(AlertFacts, row))
        if index["kind"] == "investigation":
            row = await store.one(select(R).where(*store.where(R, R.c.case_id == case_id, R.c.id == identity)))
            results = []
            if row["state"] in TERMINAL:
                results = (await store.db.execute(select(RES).where(*result_scope(store.tenant_id, case_id, identity))
                    .order_by(RES.c.saved_at, RES.c.id))).mappings().all()
            source = "ended_at" if row["state"] in TERMINAL else "started_at"
            return StoryEntry(**values, time_source=source if index["at"] else "unknown",
                run=await project_comparison(store, RunView, row), results=[await project_comparison(store, ResultView, result) for result in results])
        row = await store.one(select(V, T.c.current_revision_id).join(T,
            (T.c.tenant_id == V.c.tenant_id) & (T.c.case_id == V.c.case_id) & (T.c.id == V.c.task_id))
            .where(*store.where(V, V.c.case_id == case_id, V.c.id == identity)))
        return StoryEntry(**values, time_source="completed_at" if index["at"] else "unknown",
            task_revision=project(TaskRevisionView, row), is_current_task_revision=row["current_revision_id"] == identity)
