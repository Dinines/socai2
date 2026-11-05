"""Read-only new-schema projections. No synthesis, cache writes or legacy reads."""
import base64
import binascii
import hashlib
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import String, and_, cast, func, literal, or_, select

from app.models import socai2 as m

from .baseline_context import MAX_CONTEXT_BYTES
from .baseline_store import CA, RES, RESM, RM, A, C, F, R, StoreError, digest
from .case_contracts import (
    CaseBaselineRecord,
    CaseQueueCursor,
    CaseQueueItem,
    CaseQueueMetrics,
    CaseQueuePage,
    CaseQueueQuery,
    CaseView,
    ExecutionSummary,
    HistoryCursor,
    HistoryEntry,
    HistoryPage,
    ResultSummary,
    ResultView,
    RunView,
    SavedAnswerReference,
    StartAvailability,
    project,
)

S = m.RunSteps.__table__
TASKS, TASK_REVISIONS = m.Tasks.__table__, m.TaskRevisions.__table__
ASSESS, SOURCES, COVER = (m.CaseAssessments.__table__, m.CaseAssessmentSources.__table__, m.CaseAssessmentMembers.__table__)
ARTIFACT_FIELDS = [c for c in F.c if c.name not in {"tenant_id", "content_json", "content_text", "blob_ref"}]


def queue_open_tasks(tenant_id):
    """Only the current task revision counts; historic completions do not."""
    return select(func.count()).select_from(TASKS.join(TASK_REVISIONS,
        (TASK_REVISIONS.c.tenant_id == TASKS.c.tenant_id)
        & (TASK_REVISIONS.c.case_id == TASKS.c.case_id)
        & (TASK_REVISIONS.c.task_id == TASKS.c.id)
        & (TASK_REVISIONS.c.id == TASKS.c.current_revision_id))).where(
            TASKS.c.tenant_id == tenant_id, TASKS.c.case_id == C.c.id,
            TASK_REVISIONS.c.state.in_(["not_started", "in_progress"])).correlate(C)


def queue_metric_predicates(tenant_id):
    active = C.c.handling_status.in_(["new", "in_progress"])
    return {
        "awaiting_assignment": active & (C.c.assignment_state == "unassigned") & C.c.owner_id.is_(None),
        "in_progress": C.c.handling_status == "in_progress",
        "high_severity": active & (C.c.severity == "high"),
        "awaiting_human": active & (queue_open_tasks(tenant_id).scalar_subquery() > 0),
    }


def queue_filter_fingerprint(tenant_id, query):
    return digest({"tenant_id": str(tenant_id), "sort": "business_updated_at_desc,id_desc",
        **query.model_dump(mode="json", exclude={"limit", "cursor"})})


def queue_cursor(tenant_id, query):
    if query.cursor is None:
        return None
    try:
        raw = base64.b64decode(query.cursor, altchars=b"-_", validate=True)
        point = CaseQueueCursor.model_validate_json(raw)
    except (ValueError, TypeError, binascii.Error):
        raise StoreError("invalid_case_cursor", 422) from None
    if point.filter_fingerprint != queue_filter_fingerprint(tenant_id, query):
        raise StoreError("case_cursor_filters_changed", 422)
    return point


def queue_filters(tenant_id, query):
    clauses = [C.c.tenant_id == tenant_id]
    if query.q:
        escaped = query.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search = C.c.title.ilike("%" + escaped + "%", escape="\\")
        try:
            search = or_(search, C.c.id == UUID(query.q))
        except ValueError:
            pass
        clauses.append(search)
    for field in ("handling_status", "severity", "owner_id", "assignment_state"):
        value = getattr(query, field)
        if value is not None:
            clauses.append(C.c[field] == value)
    if query.metric:
        clauses.append(queue_metric_predicates(tenant_id)[query.metric])
    return clauses


def start_availability(cas, run, member_count, active):
    reason = "ready"
    if run["kind"] != "baseline" or run["state"] != "pending_update":
        reason = "not_pending"
    elif cas["handling_status"] == "resolved":
        reason = "resolved_case"
    elif run["scope_revision"] != cas["scope_revision"]:
        reason = "scope_changed"
    elif not member_count:
        reason = "empty_scope"
    elif active:
        reason = "baseline_active"
    return StartAvailability(can_start=reason == "ready", reason=reason)


def without_internal(row):
    return {k: v for k, v in row.items() if k not in {"tenant_id", "operation_key", "request_hash"}}


def usage_totals(steps, model_count):
    models = [r for r in steps if r["kind"] == "model" and r["state"] not in {"planned", "skipped"}]
    known, known_calls, priced_calls, costs = 0, 0, 0, defaultdict(Decimal)
    for row in models:
        usage = row["usage"] or {}
        value = usage.get("total_tokens")
        if usage.get("usage_state") == "reported" and type(value) is int and value >= 0:
            known += value
            known_calls += 1
        if usage.get("cost_state") == "priced" and usage.get("currency") and usage.get("price_version"):
            try:
                amount = Decimal(str(usage.get("cost")))
            except InvalidOperation:
                continue
            if amount.is_finite() and amount >= 0:
                costs[(usage["currency"], usage["price_version"])] += amount
                priced_calls += 1
    return {"model_calls": model_count, "known_total_tokens": known,
        "unknown_token_calls": model_count - known_calls, "total_tokens": known if known_calls == model_count else None,
        "costs_by_currency_and_price_version": [{"currency": currency, "price_version": version, "cost": str(value)}
            for (currency, version), value in sorted(costs.items())],
        "unpriced_model_calls": model_count - priced_calls}


class CaseReader:
    def __init__(self, store):
        self.store, self.db = store, store.db

    async def rows(self, query):
        return [dict(r) for r in (await self.db.execute(query)).mappings()]

    async def count(self, table, *clauses):
        return (await self.db.execute(select(func.count()).select_from(table).where(
            *self.store.where(table, *clauses)))).scalar_one()

    async def run_row(self, case_id, run_id):
        await self.store.case(case_id, lock=False)
        row = await self.store.one(select(R).where(*self.store.where(R, R.c.case_id == case_id, R.c.id == run_id)))
        if row is None:
            raise StoreError("case_run_not_found", 404)
        return row

    async def eligibility(self, cas, run, member_count):
        eligibility = start_availability(cas, run, member_count, False)
        if not eligibility.can_start:
            return eligibility
        active = await self.store.one(select(R.c.id).where(*self.store.where(R, R.c.case_id == cas["id"],
            R.c.kind == "baseline", R.c.state.in_(["running", "unknown"]))).limit(1))
        return start_availability(cas, run, member_count, bool(active))

    async def queue(self, query: CaseQueueQuery):
        """Called inside one tenant-bound REPEATABLE READ, READ ONLY transaction."""
        tenant = self.store.tenant_id
        point = queue_cursor(tenant, query)
        predicates = queue_metric_predicates(tenant)
        metrics = (await self.rows(select(*[
            func.count().filter(predicate).label(name) for name, predicate in predicates.items()
        ]).select_from(C).where(C.c.tenant_id == tenant)))[0]
        clauses = queue_filters(tenant, query)
        total = (await self.db.execute(select(func.count()).select_from(C).where(*clauses))).scalar_one()
        member_count = select(func.count()).select_from(CA).where(
            CA.c.tenant_id == tenant, CA.c.case_id == C.c.id).correlate(C).scalar_subquery()
        listing = select(C, member_count.label("member_count"),
            queue_open_tasks(tenant).scalar_subquery().label("open_task_count")).where(*clauses)
        if point:
            listing = listing.where(or_(C.c.business_updated_at < point.at,
                and_(C.c.business_updated_at == point.at, C.c.id < point.id)))
        selected = await self.rows(listing.order_by(C.c.business_updated_at.desc(), C.c.id.desc()).limit(query.limit + 1))
        visible = selected[:query.limit]
        runs = defaultdict(list)
        if visible:
            for run in await self.rows(select(R).where(*self.store.where(R,
                    R.c.case_id.in_([row["id"] for row in visible]), R.c.kind == "baseline",
                    R.c.state.in_(["pending_update", "running", "unknown"])))
                    .order_by(R.c.requested_at, R.c.id)):
                runs[run["case_id"]].append(run)
        items = []
        for row in visible:
            baseline = runs[row["id"]]
            active = any(run["state"] in {"running", "unknown"} for run in baseline)
            items.append(CaseQueueItem(case=project(CaseView, row), member_count=row["member_count"],
                open_task_count=row["open_task_count"], baseline_records=[
                    CaseBaselineRecord(run=project(RunView, run), start_eligibility=start_availability(
                        row, run, row["member_count"], active)) for run in baseline]))
        next_cursor = None
        if len(selected) > query.limit:
            last = visible[-1]
            cursor = CaseQueueCursor(at=last["business_updated_at"], id=last["id"],
                filter_fingerprint=queue_filter_fingerprint(tenant, query))
            next_cursor = base64.urlsafe_b64encode(cursor.model_dump_json().encode()).decode()
        return CaseQueuePage(items=items, total=total, next_cursor=next_cursor,
            metrics=CaseQueueMetrics.model_validate(metrics))

    async def case(self, case_id):
        cas = await self.store.case(case_id, lock=False)
        total = await self.count(CA, CA.c.case_id == case_id)
        members = await self.rows(select(CA.c.alert_id, CA.c.added_at, CA.c.added_by, CA.c.membership_source,
            A.c.title, A.c.severity, A.c.handling_status, A.c.event_time, A.c.latest_material_id)
            .join(A, (CA.c.alert_id == A.c.id) & (CA.c.tenant_id == A.c.tenant_id))
            .where(*self.store.where(CA, CA.c.case_id == case_id)).order_by(CA.c.alert_id).limit(200))
        ci, incidents = m.CaseIncidents.__table__, m.Incidents.__table__
        linked_count = await self.count(ci, ci.c.case_id == case_id)
        linked = await self.rows(select(ci.c.incident_id, ci.c.linked_at, ci.c.linked_by,
            ci.c.source_operation_id, incidents.c.title, incidents.c.source_namespace)
            .join(incidents, (ci.c.tenant_id == incidents.c.tenant_id) & (ci.c.incident_id == incidents.c.id))
            .where(*self.store.where(ci, ci.c.case_id == case_id)).order_by(ci.c.incident_id).limit(200))
        baseline = await self.rows(select(R).where(*self.store.where(R, R.c.case_id == case_id,
            R.c.kind == "baseline", R.c.state.in_(["pending_update", "running", "unknown"]))).order_by(R.c.requested_at))
        assessment = None
        if cas["current_assessment_id"]:
            row = await self.store.one(select(ASSESS).where(*self.store.where(ASSESS,
                ASSESS.c.case_id == case_id, ASSESS.c.id == cas["current_assessment_id"])))
            if row is None:
                raise StoreError("current_assessment_reference_invalid")
            covered = await self.rows(select(COVER.c.alert_id, COVER.c.coverage_note).where(*self.store.where(COVER,
                COVER.c.case_id == case_id, COVER.c.assessment_id == row["id"])).order_by(COVER.c.alert_id).limit(201))
            sources = await self.rows(select(SOURCES).where(*self.store.where(SOURCES,
                SOURCES.c.case_id == case_id, SOURCES.c.assessment_id == row["id"])).order_by(SOURCES.c.id).limit(201))
            complete = total <= 200 and len(covered) <= 200
            current, known = {r["alert_id"] for r in members}, {r["alert_id"] for r in covered}
            baseline_sources = await self.rows(select(RES.c.source_run_id)
                .join(SOURCES, (SOURCES.c.tenant_id == RES.c.tenant_id) & (SOURCES.c.result_id == RES.c.id))
                .where(*self.store.where(SOURCES, SOURCES.c.case_id == case_id,
                    SOURCES.c.assessment_id == row["id"]), RES.c.kind == "baseline").limit(2))
            if not baseline_sources and row["origin"] == "system" and row["validity"] == "system_only":
                baseline_sources = await self.rows(select(F.c.run_id.label("source_run_id"))
                    .join(SOURCES, (SOURCES.c.tenant_id == F.c.tenant_id) & (SOURCES.c.artifact_id == F.c.id))
                    .join(R, (R.c.tenant_id == F.c.tenant_id) & (R.c.id == F.c.run_id))
                    .where(*self.store.where(SOURCES, SOURCES.c.case_id == case_id,
                        SOURCES.c.assessment_id == row["id"]), F.c.kind == "report_json", R.c.kind == "baseline").limit(2))
            freshness = {"state": "unverified", "reasons": ["single_baseline_source_unavailable"]}
            if len(baseline_sources) == 1 and baseline_sources[0]["source_run_id"]:
                freshness = (await self.store.db.execute(select(func.socai2.baseline_input_freshness(
                    self.store.tenant_id, baseline_sources[0]["source_run_id"])))).scalar_one()
            assessment = {"value": without_internal(row), "members": covered[:200], "members_truncated": len(covered) > 200,
                "input_freshness": freshness,
                "sources": [without_internal(s) for s in sources[:200]], "sources_truncated": len(sources) > 200,
                "scope_revision_changed": row["scope_revision"] != cas["scope_revision"],
                "covers_current_members": current <= known if complete else None,
                "uncovered_current_alert_ids": sorted(current - known) if complete else None,
                "no_longer_current_alert_ids": sorted(known - current) if complete else None}
        return {"case": project(CaseView, cas), "members": members, "member_count": total,
            "linked_incidents": linked, "linked_incident_count": linked_count,
            "linked_incidents_truncated": linked_count > len(linked),
            "members_truncated": total > len(members), "current_assessment": assessment,
            "baseline_records": [{"run": project(RunView, r), "start_eligibility": await self.eligibility(cas, r, total)} for r in baseline]}

    async def history(self, case_id, *, limit=20, cursor=None):
        await self.store.case(case_id, lock=False)
        if not 1 <= limit <= 100:
            raise StoreError("invalid_history_limit", 422)
        baseline = select((literal("run:") + cast(R.c.id, String)).label("key"), R.c.requested_at.label("at"),
            R.c.id.label("run_id"), RES.c.id.label("result_id")).outerjoin(RES,
                (RES.c.tenant_id == R.c.tenant_id) & (RES.c.case_id == R.c.case_id) & (RES.c.source_run_id == R.c.id)
                & (RES.c.kind == "baseline") & RES.c.supersedes_result_id.is_(None)).where(
                    *self.store.where(R, R.c.case_id == case_id, R.c.kind == "baseline"))
        saved = select((literal("result:") + cast(RES.c.id, String)).label("key"), RES.c.saved_at.label("at"),
            RES.c.source_run_id.label("run_id"), RES.c.id.label("result_id")).where(
                *self.store.where(RES, RES.c.case_id == case_id, RES.c.kind == "ai_saved"))
        index = baseline.union_all(saved).subquery()
        query = select(index)
        if cursor:
            try:
                if len(cursor) > 512:
                    raise ValueError()
                raw = base64.b64decode(cursor, altchars=b"-_", validate=True)
                point = HistoryCursor.model_validate_json(raw)
                UUID(point.key.split(":", 1)[1])
            except (ValueError, TypeError, binascii.Error):
                raise StoreError("invalid_history_cursor", 422) from None
            query = query.where(or_(index.c.at < point.at, and_(index.c.at == point.at, index.c.key < point.key)))
        selected = await self.rows(query.order_by(index.c.at.desc(), index.c.key.desc()).limit(limit + 1))
        visible = selected[:limit]
        runs = {r["id"]: r for r in await self.rows(select(R).where(*self.store.where(R, R.c.case_id == case_id,
            R.c.id.in_([i["run_id"] for i in visible]))))}
        results = {r["id"]: r for r in await self.rows(select(RES).where(*self.store.where(RES, RES.c.case_id == case_id,
            RES.c.id.in_([i["result_id"] for i in visible if i["result_id"]]))))}
        items = [HistoryEntry(id=i["key"], recorded_at=i["at"], run=project(RunView, runs[i["run_id"]]),
            result=project(ResultSummary, results[i["result_id"]]) if i["result_id"] else None) for i in visible]
        more = None
        if len(selected) > limit:
            value = HistoryCursor(at=visible[-1]["at"], key=visible[-1]["key"])
            more = base64.urlsafe_b64encode(value.model_dump_json().encode()).decode()
        return HistoryPage(items=items, next_cursor=more)

    async def execution_summary(self, case_id, run_id, steps):
        """Read the frozen execution plan; never infer today's capabilities for history."""
        plan = next((step for step in steps if step["stage_code"] == "C1.executor"
            and step["state"] == "completed" and step["output_artifact_id"]), None)
        if plan is None:
            return None
        artifact_id = plan["output_artifact_id"]
        saved = await self.artifact(case_id, run_id, artifact_id)
        if saved["availability"] != "available":
            return ExecutionSummary(artifact_id=artifact_id, availability=saved["availability"])
        body = saved["content_json"]
        if not isinstance(body, dict) or body.get("type") != "execution_plan" or body.get("run_id") != str(run_id):
            raise StoreError("execution_plan_link_invalid")
        return ExecutionSummary(artifact_id=artifact_id, availability="available",
            **{key: body[key] for key in ("schema_version", "capabilities", "limits", "final_reservation", "limitations")
                if key in body})

    async def run(self, case_id, run_id):
        row = await self.run_row(case_id, run_id)
        cas = await self.store.case(case_id, lock=False)
        current_count = await self.count(CA, CA.c.case_id == case_id)
        member_count = await self.count(RM, RM.c.case_id == case_id, RM.c.run_id == run_id)
        members = await self.rows(select(RM).where(*self.store.where(RM, RM.c.case_id == case_id,
            RM.c.run_id == run_id)).order_by(RM.c.alert_id).limit(200))
        steps = await self.rows(select(S).where(*self.store.where(S, S.c.run_id == run_id)).order_by(S.c.seq).limit(1000))
        counts = await self.rows(select(S.c.kind, S.c.state, func.count().label("n"),
            func.max(func.greatest(S.c.started_at, S.c.ended_at)).label("last_recorded_at")).where(
            *self.store.where(S, S.c.run_id == run_id)).group_by(S.c.kind, S.c.state))
        models = sum(r["n"] for r in counts if r["kind"] == "model" and r["state"] not in {"planned", "skipped"})
        tools = sum(r["n"] for r in counts if r["kind"] == "tool" and r["state"] not in {"planned", "skipped"})
        artifacts = await self.rows(select(*ARTIFACT_FIELDS).where(*self.store.where(F,
            F.c.case_id == case_id, F.c.run_id == run_id)).order_by(F.c.captured_at, F.c.id).limit(200))
        artifact_counts = await self.rows(select(F.c.kind, func.count().label("n"),
            func.max(F.c.captured_at).label("last_recorded_at")).where(
            *self.store.where(F, F.c.case_id == case_id, F.c.run_id == run_id)).group_by(F.c.kind))
        result_ids = list((await self.db.execute(select(RES.c.id).where(*self.store.where(RES,
            RES.c.case_id == case_id, RES.c.source_run_id == run_id)).order_by(RES.c.saved_at, RES.c.id).limit(200))).scalars())
        result_count = await self.count(RES, RES.c.case_id == case_id, RES.c.source_run_id == run_id)
        read_counts = await self.rows(select(RM.c.read_state, RM.c.analysis_state, func.count().label("n")).where(
            *self.store.where(RM, RM.c.case_id == case_id, RM.c.run_id == run_id)).group_by(RM.c.read_state, RM.c.analysis_state))
        read, analysis = Counter(), Counter()
        for count in read_counts:
            read[count["read_state"]] += count["n"]
            analysis[count["analysis_state"]] += count["n"]
        now = await self.store.now()
        duration = (row["ended_at"] - row["started_at"]).total_seconds() if row["ended_at"] and row["started_at"] else None
        recorded = [row[k] for k in ("requested_at", "scope_updated_at", "started_at", "ended_at")]
        recorded += [r["last_recorded_at"] for r in counts + artifact_counts]
        return {"run": project(RunView, row), "result_ids": result_ids,
            "result_count": result_count, "results_truncated": result_count > len(result_ids),
            "start_eligibility": await self.eligibility(cas, row, current_count),
            "current_member_count": current_count, "input_member_count": member_count,
            "members": [without_internal(r) for r in members], "members_truncated": member_count > len(members),
            "read_counts": dict(read), "analysis_counts": dict(analysis),
            "steps": [without_internal(r) for r in steps], "steps_truncated": sum(r["n"] for r in counts) > len(steps),
            "tool_calls": tools, "usage": usage_totals(steps, models),
            "artifacts": artifacts, "artifact_counts": {r["kind"]: r["n"] for r in artifact_counts},
            "artifacts_truncated": sum(r["n"] for r in artifact_counts) > len(artifacts),
            "duration_seconds": duration,
            "elapsed_seconds": (now - row["started_at"]).total_seconds() if row["started_at"] and not row["ended_at"] else None,
            "last_recorded_at": max(t for t in recorded if t is not None), "observed_at": now,
            "execution_summary": await self.execution_summary(case_id, run_id, steps)}

    async def artifact(self, case_id, run_id, artifact_id):
        filters = self.store.where(F, F.c.case_id == case_id, F.c.run_id == run_id, F.c.id == artifact_id)
        row = await self.store.one(select(*ARTIFACT_FIELDS, F.c.blob_ref.is_not(None).label("external")).where(*filters))
        if not row:
            raise StoreError("run_artifact_not_found", 404)
        meta = dict(row)
        external = meta.pop("external")
        out = {"artifact": meta, "content_json": None, "content_text": None, "availability": "unavailable"}
        if external:
            return {**out, "availability": "external_content_not_loaded"}
        if row["size_bytes"] is None or row["size_bytes"] > MAX_CONTEXT_BYTES:
            return {**out, "availability": "content_exceeds_read_limit_or_size_unknown"}
        body = await self.store.one(select(F.c.content_json, F.c.content_text).where(*filters))
        value = body["content_json"]
        sha = digest(value) if value is not None else hashlib.sha256(body["content_text"].encode()).hexdigest() if body["content_text"] is not None else None
        if not sha or sha != row["sha256"]:
            raise StoreError("artifact_integrity_invalid")
        return {**out, **dict(body), "availability": "available"}

    async def result(self, case_id, result_id):
        await self.store.case(case_id, lock=False)
        row = await self.store.one(select(RES).where(*self.store.where(RES, RES.c.case_id == case_id, RES.c.id == result_id)))
        if not row:
            raise StoreError("case_result_not_found", 404)
        run = await self.run_row(case_id, row["source_run_id"])
        members = await self.rows(select(RESM).where(*self.store.where(RESM, RESM.c.case_id == case_id,
            RESM.c.result_id == result_id)).order_by(RESM.c.alert_id).limit(200))
        count = await self.count(RESM, RESM.c.case_id == case_id, RESM.c.result_id == result_id)
        source_answer = None
        if row["source_answer_id"]:
            messages = m.Messages.__table__
            answer = await self.store.one(select(*[messages.c[k] for k in SavedAnswerReference.model_fields]).where(
                *self.store.where(messages, messages.c.case_id == case_id, messages.c.id == row["source_answer_id"],
                    messages.c.source_run_id == run["id"], messages.c.input_artifact_id == row["input_artifact_id"])))
            if answer is None:
                raise StoreError("result_answer_link_invalid")
            source_answer = project(SavedAnswerReference, answer)
        delivery = None
        if row["kind"] == "baseline":
            step = await self.store.one(select(S).where(*self.store.where(S, S.c.run_id == run["id"],
                S.c.kind == "stage", S.c.stage_code == "C6")))
            if step and step["output_artifact_id"]:
                saved = await self.artifact(case_id, run["id"], step["output_artifact_id"])
                receipt = saved["content_json"] or {}
                if (receipt.get("type") != "delivery_receipt" or receipt.get("outcome", {}).get("result_id") != str(result_id)
                        or receipt.get("report_artifact_id") != str(row["report_artifact_id"])):
                    raise StoreError("result_delivery_link_invalid")
                detail = await self.artifact(case_id, run["id"], UUID(receipt["detail_artifact_id"]))
                if (detail["content_json"] or {}).get("result_id") != str(result_id):
                    raise StoreError("result_delivery_link_invalid")
                delivery = {"receipt_artifact_id": step["output_artifact_id"],
                    "detail_artifact_id": UUID(receipt["detail_artifact_id"]),
                    "markdown_artifact_id": UUID(receipt["markdown_artifact_id"]), "detail": detail["content_json"]}
        return {"result": project(ResultView, row), "run": project(RunView, run),
            "source_answer": source_answer,
            "members": [without_internal(r) for r in members], "member_count": count,
            "members_truncated": count > len(members), "delivery": delivery}
