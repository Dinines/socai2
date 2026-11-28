"""Read saved Case investigation cards and resolve exact member Runs."""
from collections import defaultdict
from contextlib import asynccontextmanager

from sqlalchemy import and_, case, func, select, tuple_
from sqlalchemy.exc import DBAPIError

from app.models import socai2 as m

from .baseline_service import BaselineService
from .baseline_store import RES, StoreError, digest
from .case_reader import usage_totals
from .case_story_relations import StoryRelations, explicit_run_sources
from .run_records import cursor_point, make_cursor

AS = m.AlertAssessments.__table__
D = m.IncidentDiagnoses.__table__
S = m.RunSteps.__table__
DIRECTORY = "case_investigations"
USAGE_FIELDS = ("model_calls", "total_tokens", "known_total_tokens", "unknown_token_calls")


def card_rows(scope):
    runs = scope.runs
    return select(
        runs.c.id, runs.c.case_id, runs.c.alert_id, runs.c.incident_id, runs.c.kind,
        runs.c.title, runs.c.state, runs.c.delivery_state, runs.c.requested_at,
        runs.c.started_at, runs.c.ended_at, runs.c.overlap,
        func.jsonb_array_length(runs.c.input_ids).label("input_member_count"),
    )


async def measurements(store, run_ids):
    tool_counts = dict((await store.db.execute(select(S.c.run_id, func.count()).where(
        *store.where(S, S.c.run_id.in_(run_ids), S.c.kind == "tool"),
    ).group_by(S.c.run_id))).tuples().all())
    models = (await store.db.execute(select(S.c.run_id, S.c.kind, S.c.state, S.c.usage).where(
        *store.where(S, S.c.run_id.in_(run_ids), S.c.kind == "model",
                     S.c.state.not_in(("planned", "skipped"))),
    ))).mappings()
    by_run = defaultdict(list)
    for step in models:
        by_run[step["run_id"]].append(step)
    usage = {run_id: usage_totals(by_run[run_id], len(by_run[run_id])) for run_id in run_ids}
    return tool_counts, usage


def preview(result_id, result_type, kind, **source_fields):
    for field, text in source_fields.items():
        if text and text.strip():
            return {"result_id": result_id, "result_type": result_type, "kind": kind,
                    "source_field": field, "text": text}
    return None


async def saved_previews(store, case_id, refs):
    previews = {}
    cases = [ref for ref in refs.values() if ref["subject_type"] == "case"]
    if cases:
        baseline_ids = [ref["run_id"] for ref in cases if ref["run_kind"] == "baseline"]
        preferred = case(
            (RES.c.source_run_id.in_(baseline_ids),
             and_(RES.c.kind == "baseline", RES.c.supersedes_result_id.is_(None))),
            else_=RES.c.kind == "ai_saved",
        )
        rows = (await store.db.execute(select(
            RES.c.source_run_id, RES.c.id, RES.c.kind, RES.c.conclusion, RES.c.closing_note,
        ).where(*store.where(RES, RES.c.case_id == case_id,
                             RES.c.source_run_id.in_([ref["run_id"] for ref in cases])))
            .distinct(RES.c.source_run_id)
            .order_by(RES.c.source_run_id, preferred.desc(), RES.c.saved_at.desc(), RES.c.id.desc())
        )).mappings()
        for row in rows:
            previews[row["source_run_id"]] = preview(
                row["id"], "case_result", row["kind"], conclusion=row["conclusion"], closing_note=row["closing_note"],
            )

    for subject_type, table, field in (("alert", AS, "rationale"), ("incident", D, "summary")):
        # The native stage detail exposes one saved result for this Run.
        stage_refs = {
            ref["result_refs"][0]["id"]: ref["result_refs"][0] for ref in refs.values()
            if ref["subject_type"] == subject_type and len(ref["result_refs"]) == 1
        }
        if not stage_refs:
            continue
        rows = (await store.db.execute(select(table.c.id, table.c[field]).where(
            *store.where(table, table.c.id.in_(stage_refs)),
        ))).mappings()
        for row in rows:
            ref = stage_refs[row["id"]]
            previews[ref["source_run_id"]] = preview(ref["id"], ref["result_type"], ref["kind"], **{field: row[field]})
    return previews


async def cards(scope, rows):
    if not rows:
        return []
    refs = await scope.investigation_refs(rows)
    tools, usage = await measurements(scope.store, list(refs))
    previews = await saved_previews(scope.store, scope.case_id, refs)
    items = []
    for row in rows:
        run_id = row["id"]
        started, ended = row["started_at"], row["ended_at"]
        duration = (ended - started).total_seconds() if started and ended and ended >= started else None
        items.append({
            **refs[run_id], "started_at": started, "ended_at": ended, "duration_seconds": duration,
            "input_member_count": row["input_member_count"], "tool_record_count": tools.get(run_id, 0),
            "usage": {field: usage[run_id][field] for field in USAGE_FIELDS}, "preview": previews.get(run_id),
        })
    return items


class CaseInvestigationService(BaselineService):
    @asynccontextmanager
    async def scope(self, tenant_id, case_id):
        try:
            async with self.transaction(tenant_id, readonly=True) as store:
                case_row = await store.case(case_id, lock=False)
                yield StoryRelations(store, case_id, await explicit_run_sources(store, case_row))
        except DBAPIError:
            raise StoreError("service_unavailable", 503) from None

    async def read(self, tenant_id, case_id, *, limit, cursor):
        fingerprint = digest({"tenant": str(tenant_id), "case": str(case_id), "directory": DIRECTORY,
                              "order": "requested_at,id:desc"})
        point = cursor_point(cursor, fingerprint, DIRECTORY)
        async with self.scope(tenant_id, case_id) as scope:
            store, runs = scope.store, scope.runs
            total = await scope.investigation_count()
            statement = card_rows(scope).order_by(runs.c.requested_at.desc(), runs.c.id.desc())
            if point:
                statement = statement.where(tuple_(runs.c.requested_at, runs.c.id) < point)
            page = (await store.db.execute(statement.limit(limit + 1))).mappings().all()
            visible = page[:limit]
            return {
                "case_id": case_id, "items": await cards(scope, visible), "total": total,
                "next_cursor": make_cursor(fingerprint, visible[-1], "requested_at") if len(page) > limit else None,
                "observed_at": await store.now(), "limitations": await scope.limitations(),
            }

    async def lookup(self, tenant_id, case_id, run_id):
        async with self.scope(tenant_id, case_id) as scope:
            store = scope.store
            row = await store.one(card_rows(scope).where(scope.runs.c.id == run_id))
            if row is None:
                raise StoreError("run_not_found", 404)
            return {
                "case_id": case_id, "item": (await cards(scope, [row]))[0],
                "observed_at": await store.now(), "limitations": await scope.limitations(),
            }
