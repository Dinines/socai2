"""One read-only snapshot for the existing Case story; no execution or writes."""
import base64
import binascii
from uuid import UUID

from sqlalchemy import String, case, cast, column, func, literal, or_, select, tuple_
from sqlalchemy.dialects.postgresql import JSONB

from app.models import socai2 as m

from .baseline_service import BaselineService
from .baseline_store import CA, RES, A, R, StoreError, digest
from .case_comparison import project_comparison
from .case_contracts import ResultView, RunView, project
from .case_story_contracts import (
    MemberRelationCursor,
    RelatedStoryQuery,
    StoryCursor,
    StoryEntry,
    StoryPage,
    StorySummary,
)
from .case_story_relations import (
    MATERIAL_UNAVAILABLE,
    StoryRelations,
    array_or_empty,
    explicit_run_sources,
    valid_members,
)
from .human_task_contracts import TaskRevisionView
from .list_query import ordering, seek
from .page_contracts import AlertFacts

T, V, O = m.Tasks.__table__, m.TaskRevisions.__table__, m.AlertObjects.__table__
ASSESSMENTS, DIAGNOSES = m.AlertAssessments.__table__, m.IncidentDiagnoses.__table__
TERMINAL = ("completed", "failed", "cancelled")


def fingerprint(tenant, case_id, query):
    return digest({"tenant": str(tenant), "case": str(case_id),
        **query.model_dump(mode="json", exclude={"limit", "cursor", "focus_alert_id"})})


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


def story_columns(kind, identity, at):
    return ((literal(kind + ":") + cast(identity, String)).label("key"),
            literal(kind).label("kind"), identity.label("source_id"), at.label("at"))


def run_time(run):
    return case((run.c.state.in_(TERMINAL), run.c.ended_at),
                (run.c.state.in_(["running", "unknown"]), run.c.started_at), else_=None)


def story_index(tenant, case_id, query):
    alerts = select(*story_columns("alert", A.c.id, A.c.event_time)).select_from(CA.join(A,
        (A.c.tenant_id == CA.c.tenant_id) & (A.c.id == CA.c.alert_id))).where(
            CA.c.tenant_id == tenant, CA.c.case_id == case_id)
    if query.severity is not None:
        alerts = alerts.where(A.c.severity == query.severity)
    if query.q:
        objects = select(O.c.id).where(O.c.tenant_id == tenant, O.c.alert_id == A.c.id,
            O.c.material_id == A.c.latest_material_id, O.c.object_type.in_(["host", "user"]),
            matches(query.q, O.c.raw_value, O.c.normalized_value)).exists()
        alerts = alerts.where(or_(matches(query.q, A.c.title, A.c.description), objects))
    runs = select(*story_columns("investigation", R.c.id, run_time(R))).where(
        R.c.tenant_id == tenant, R.c.case_id == case_id, R.c.kind == "baseline")
    if query.q:
        results = select(RES.c.id).where(*result_scope(tenant, case_id, R.c.id),
            R.c.state.in_(TERMINAL), matches(query.q, RES.c.title, RES.c.conclusion,
                RES.c.change_summary)).exists()
        runs = runs.where(or_(matches(query.q, R.c.title, R.c.purpose), results))
    human = select(*story_columns("human_result", V.c.id, V.c.completed_at)).where(
        V.c.tenant_id == tenant, V.c.case_id == case_id, V.c.state == "completed")
    if query.q:
        human = human.where(matches(query.q, V.c.title, V.c.description, V.c.result_text))
    return alerts.union_all(runs, human).subquery()


def matching_members(scope, query):
    members, objects = scope.members, scope.objects
    statement = select(members.c.id, members.c.event_time)
    if query.severity is not None:
        statement = statement.where(members.c.severity == query.severity)
    if query.q:
        object_match = select(objects.c.id).where(
            objects.c.alert_id == members.c.id,
            matches(query.q, objects.c.raw_value, objects.c.normalized_value),
        ).exists()
        statement = statement.where(or_(matches(query.q, members.c.title, members.c.description), object_match))
    return statement.cte("story_matching_members")


def related_run_text(store, runs, keyword):
    findings = func.jsonb_array_elements(array_or_empty(RES.c.findings)).table_valued(column("value", JSONB))
    finding_match = select(1).select_from(findings).where(
        matches(keyword, findings.c.value["statement"].astext),
    ).correlate(RES).exists()
    saved = select(RES.c.id).where(*store.where(
        RES, RES.c.case_id == runs.c.case_id, RES.c.source_run_id == runs.c.id,
        or_(matches(keyword, RES.c.title, RES.c.conclusion, RES.c.change_summary), finding_match),
    )).exists()
    triage = select(ASSESSMENTS.c.id).where(*store.where(
        ASSESSMENTS, ASSESSMENTS.c.alert_id == runs.c.alert_id, ASSESSMENTS.c.source_run_id == runs.c.id,
        ASSESSMENTS.c.kind == "triage", matches(keyword, ASSESSMENTS.c.rationale),
    )).exists()
    diagnosis = select(DIAGNOSES.c.id).where(*store.where(
        DIAGNOSES, DIAGNOSES.c.incident_id == runs.c.incident_id, DIAGNOSES.c.source_run_id == runs.c.id,
        matches(keyword, DIAGNOSES.c.summary),
    )).exists()
    return or_(matches(keyword, runs.c.title, runs.c.purpose), saved, triage, diagnosis)


def related_index(scope, query, matched):
    runs, store = scope.runs, scope.store
    alerts = select(*story_columns("alert", matched.c.id, matched.c.event_time))
    investigations = select(*story_columns("investigation", runs.c.id, run_time(runs)))
    revisions = select(*story_columns("human_result", V.c.id, V.c.completed_at)).where(
        *store.where(V, V.c.case_id == scope.case_id, V.c.state == "completed"),
    )
    run_overlap = select(matched.c.id).where(runs.c.input_ids.has_key(cast(matched.c.id, String))).exists()
    revision_ids = V.c.result_scope["alert_ids"]
    revision_overlap = select(matched.c.id).where(
        valid_members(revision_ids), revision_ids.has_key(cast(matched.c.id, String)),
    ).exists()
    if query.q:
        investigations = investigations.where(or_(related_run_text(store, runs, query.q), run_overlap))
        revisions = revisions.where(or_(
            matches(query.q, V.c.title, V.c.description, V.c.result_text), revision_overlap,
        ))
    if query.severity is not None:
        investigations = investigations.where(run_overlap)
        revisions = revisions.where(revision_overlap)
    return alerts.union_all(investigations, revisions).subquery()


async def summary(scope, matched, requested_focus):
    members, objects, db = scope.members, scope.objects, scope.store.db
    scope_stats = (await db.execute(select(
        func.count().label("member_alert_count"), func.min(members.c.event_time).label("activity_time_from"),
        func.max(members.c.event_time).label("activity_time_to"),
    ).select_from(members))).mappings().one()
    identities = select(objects.c.object_type, objects.c.namespace, objects.c.object_key).distinct().subquery()
    focus = await db.scalar(select(matched.c.id).order_by(
        (matched.c.id == requested_focus).desc() if requested_focus is not None else matched.c.event_time.desc().nulls_last(),
        matched.c.event_time.desc().nulls_last(), matched.c.id.desc(),
    ).limit(1))
    return StorySummary(
        **scope_stats, member_object_count=await db.scalar(select(func.count()).select_from(identities)),
        members_without_current_material_count=await db.scalar(scope.missing_material()),
        matched_alert_count=await db.scalar(select(func.count()).select_from(matched)), focus_alert_id=focus,
    )


def relation_cursor(cursor, fingerprint, section):
    if cursor is None:
        return None
    try:
        raw = base64.b64decode(cursor, altchars=b"-_", validate=True)
        point = MemberRelationCursor.model_validate_json(raw)
    except (ValueError, TypeError, binascii.Error):
        raise StoreError("invalid_cursor", 422) from None
    if point.fingerprint != fingerprint or (point.at is None) != (section == "objects"):
        raise StoreError("invalid_cursor", 422)
    return point


async def relation_page(scope, alert_id, section, limit, cursor):
    store = scope.store
    fingerprint = digest({"tenant": str(store.tenant_id), "case": str(scope.case_id),
                          "alert": str(alert_id), "section": section})
    point = relation_cursor(cursor, fingerprint, section)
    if section == "objects":
        rows = scope.shared_objects(alert_id)
        statement = select(rows).order_by(rows.c.focus_object_id)
        if point:
            statement = statement.where(rows.c.focus_object_id > point.id)
        unavailable = await store.db.scalar(scope.missing_material())
        limitations = [MATERIAL_UNAVAILABLE] if unavailable else []
    else:
        rows = select(scope.runs.c.id, scope.runs.c.requested_at).where(
            scope.runs.c.input_ids.has_key(str(alert_id)),
        ).subquery()
        statement = select(rows).order_by(rows.c.requested_at.desc(), rows.c.id.desc())
        if point:
            statement = statement.where(tuple_(rows.c.requested_at, rows.c.id) < (point.at, point.id))
        limitations = await scope.limitations()
    page = (await store.db.execute(statement.limit(limit + 1))).mappings().all()
    cursor = None
    if len(page) > limit:
        anchor = page[limit - 1]
        value = MemberRelationCursor(fingerprint=fingerprint, id=anchor.get("focus_object_id") or anchor["id"],
                                     at=anchor.get("requested_at"))
        cursor = base64.urlsafe_b64encode(value.model_dump_json().encode()).decode()
    page = page[:limit]
    if section == "runs":
        refs = await scope.investigations([row["id"] for row in page])
        page = [refs[row["id"]] for row in page]
    return {"items": page, "total": await store.db.scalar(select(func.count()).select_from(rows)),
            "next_cursor": cursor, "limitations": limitations}


class CaseStoryService(BaselineService):
    async def read(self, tenant_id, case_id, query):
        point = read_cursor(tenant_id, case_id, query)
        async with self.transaction(tenant_id, readonly=True) as store:
            cas = await store.case(case_id, lock=False)
            related = isinstance(query, RelatedStoryQuery)
            if related:
                scope = StoryRelations(store, case_id, await explicit_run_sources(store, cas))
                matched = matching_members(scope, query)
                index = related_index(scope, query, matched)
            else:
                index = story_index(tenant_id, case_id, query)
            total = (await store.db.execute(select(func.count()).select_from(index))).scalar_one()
            statement = select(index).order_by(*ordering(index.c.at, index.c.key, "desc"))
            if point:
                statement = statement.where(seek(index.c.at, index.c.key, point.at, point.key, "desc"))
            rows = (await store.db.execute(statement.limit(query.limit + 1))).mappings().all()
            page = rows[:query.limit]
            cursor = None
            if len(rows) > query.limit:
                last = page[-1]
                value = StoryCursor(fingerprint=fingerprint(tenant_id, case_id, query), at=last["at"], key=last["key"])
                cursor = base64.urlsafe_b64encode(value.model_dump_json().encode()).decode()
            pagination = {"total": total, "next_cursor": cursor, "observed_at": await store.now()}
            if not related:
                return StoryPage(items=[await self.entry(store, case_id, row) for row in page], **pagination)
            refs = await scope.investigations([row["source_id"] for row in page if row["kind"] == "investigation"])
            items = []
            for row in page:
                ref = refs[row["source_id"]] if row["kind"] == "investigation" else None
                if ref is not None and ref["subject_type"] != "case":
                    item = StoryEntry(id=row["key"], kind=row["kind"], occurred_at=row["at"],
                                      time_source="ended_at" if row["at"] and ref["state"] in TERMINAL
                                      else "started_at" if row["at"] else "unknown")
                else:
                    item = await self.entry(store, ref["subject_id"] if ref else case_id, row, related=True)
                items.append({**item.model_dump(), "investigation_ref": ref})
            return {**pagination, "items": items, "summary": await summary(scope, matched, query.focus_alert_id),
                    "limitations": await scope.limitations()}

    async def read_member_relations(self, tenant_id, case_id, alert_id, query):
        async with self.transaction(tenant_id, readonly=True) as store:
            cas = await store.case(case_id, lock=False)
            member = await store.one(select(CA.c.id).where(*store.where(
                CA, CA.c.case_id == case_id, CA.c.alert_id == alert_id,
            )))
            if member is None:
                raise StoreError("case_member_not_found", 404)
            scope = StoryRelations(store, case_id, await explicit_run_sources(store, cas))
            objects = await relation_page(scope, alert_id, "objects", query.objects_limit, query.objects_cursor)
            runs = await relation_page(scope, alert_id, "runs", query.runs_limit, query.runs_cursor)
            return {"case_id": case_id, "alert_id": alert_id, "observed_at": await store.now(),
                    "shared_objects": objects, "investigations": runs}

    async def entry(self, store, case_id, index, *, related=False):
        values = {"id": index["key"], "kind": index["kind"], "occurred_at": index["at"]}
        identity = index["source_id"]
        if index["kind"] == "alert":
            row = await store.one(select(A).where(*store.where(A, A.c.id == identity)))
            return StoryEntry(**values, time_source="event_time" if index["at"] else "unknown",
                alert=project(AlertFacts, row))
        if index["kind"] == "investigation":
            row = await store.one(select(R).where(*store.where(R, R.c.case_id == case_id, R.c.id == identity)))
            results = []
            if related or row["state"] in TERMINAL:
                conditions = (store.where(RES, RES.c.case_id == case_id, RES.c.source_run_id == identity)
                              if related else result_scope(store.tenant_id, case_id, identity))
                results = (await store.db.execute(select(RES).where(*conditions)
                    .order_by(RES.c.saved_at, RES.c.id))).mappings().all()
            source = "ended_at" if row["state"] in TERMINAL else "started_at"
            return StoryEntry(**values, time_source=source if index["at"] else "unknown",
                run=await project_comparison(store, RunView, row), results=[await project_comparison(store, ResultView, result) for result in results])
        row = await store.one(select(V, T.c.current_revision_id).join(T,
            (T.c.tenant_id == V.c.tenant_id) & (T.c.case_id == V.c.case_id) & (T.c.id == V.c.task_id))
            .where(*store.where(V, V.c.case_id == case_id, V.c.id == identity)))
        return StoryEntry(**values, time_source="completed_at" if index["at"] else "unknown",
            task_revision=project(TaskRevisionView, row), is_current_task_revision=row["current_revision_id"] == identity)
