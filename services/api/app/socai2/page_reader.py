"""Current page facts and bounded relationship reads, in one read-only snapshot."""
import hashlib

from sqlalchemy import String, and_, case, cast, func, literal, or_, select, text
from sqlalchemy.exc import DBAPIError

from app.models import socai2 as m

from .baseline_service import BaselineService
from .baseline_store import StoreError, encoded
from .case_contracts import project
from .case_reader import ARTIFACT_FIELDS, usage_totals
from .page_contracts import (
    AlertFacts,
    IncidentFacts,
    RecordPage,
    SubjectPage,
    SubjectView,
)
from .program_facts import RANK
from .read_sources import ReadSources, lookup_error
from .stage_inputs import freshness_sql
from .stage_reader import StageReader
from . import list_query as lists
from .list_query_contracts import AlertListQuery, IncidentListQuery

A, I, M, O, L, R, S, F = (x.__table__ for x in (m.Alerts, m.Incidents, m.AlertMaterials,
    m.AlertObjects, m.IncidentAlerts, m.Runs, m.RunSteps, m.Artifacts))
from .runtime_policy import retention_limit

MAX_STEPS = 1000
MAX_ARTIFACTS = 200
REVERSE_RANK = {v: k for k, v in RANK.items()}
SECTIONS = ("members", "incidents", "objects", "sources", "source_artifacts", "assets", "cases", "comments", "activities", "related_alerts", "responses")


def band(value):
    return "high" if value in {"high", "critical"} else "medium" if value == "medium" else "low" if value in {"info", "low"} else None


def public(row, *extra):
    return {k: v for k, v in row.items() if k not in {"tenant_id", "source_identity_key", "operation_key", "request_hash",
        "source_operation_id", "operation_id", "blob_ref", *extra}}


class PageReader:
    def __init__(self, store, kind, identity=None, *, read_sources=None):
        if kind not in {"alerts", "incidents"}:
            raise StoreError("page_subject_invalid", 422)
        self.store, self.db, self.kind, self.identity = store, store.db, kind, identity
        self.table = A if kind == "alerts" else I
        self.read_sources = read_sources

    def lookup_relation(self, name):
        # Existing business entry points keep their public schema contract.
        # An explicitly selected read service supplies its file-backed adapter.
        if self.read_sources is not None:
            return self.read_sources.relation(name)
        return "public.assets" if name == "assets" else "public.users"

    async def rows(self, query):
        return (await self.db.execute(query)).mappings().all()

    async def subject(self):
        row = await self.store.one(select(self.table).where(*self.store.where(self.table, self.table.c.id == self.identity)))
        if row is None:
            raise StoreError("page_subject_not_found", 404)
        return row

    def member_ids(self):
        if self.kind == "alerts":
            return select(A.c.id).where(*self.store.where(A, A.c.id == self.identity))
        return select(L.c.alert_id).where(*self.store.where(L, L.c.incident_id == self.identity))

    def current_objects(self):
        return select(O).join(A, and_(A.c.tenant_id == O.c.tenant_id, A.c.id == O.c.alert_id,
            A.c.latest_material_id == O.c.material_id)).where(*self.store.where(O, O.c.alert_id.in_(self.member_ids())))

    async def view(self, row):
        self.identity = row["id"]
        model = AlertFacts if self.kind == "alerts" else IncidentFacts
        name = None
        if row["owner_id"]:
            name = (await self.db.execute(text(f"SELECT u.username FROM {self.lookup_relation('owners')} u WHERE u.tenant_id=:tenant AND u.id=:id"),
                {"tenant": self.store.tenant_id, "id": row["owner_id"]})).scalar_one_or_none()
        owner_state = "unassigned" if row["assignment_state"] == "unassigned" else "resolved" if name else "unresolved"
        material, triage, feedback = None, None, None
        if self.kind == "alerts":
            cols = [c for c in M.c if c.name not in {"raw_json", "raw_text", "ocsf_json", "enrichment"}]
            mat = await self.store.one(select(*cols).where(*self.store.where(M, M.c.alert_id == self.identity,
                M.c.id == row["latest_material_id"])))
            material = public(mat) if mat else None
            if material:
                material["content_url"] = f"/api/v1/socai2/alerts/{self.identity}/materials/{mat['id']}"
            ass = m.AlertAssessments.__table__
            for pointer, kind in (("latest_triage_id", "triage"), ("latest_feedback_id", "human_feedback")):
                val = await self.store.one(select(ass).where(*self.store.where(ass, ass.c.alert_id == self.identity,
                    ass.c.id == row[pointer], ass.c.kind == kind))) if row[pointer] else None
                data = public(val, "legacy_execution_ref") if val else None
                if kind == "triage" and data:
                    data["freshness"] = (await self.db.execute(text("SELECT " + freshness_sql("alert_basic", ":subject", ":run")),
                        {"tenant": self.store.tenant_id, "subject": self.identity, "run": val["source_run_id"]})).scalar_one()
                    data["confidence_percent"] = float(val["confidence"]) * 100 if val["score_state"] == "available" and val["confidence"] is not None else None
                    data["run_state"] = (await self.db.execute(select(R.c.state).where(*self.store.where(R,
                        R.c.id == val["source_run_id"], R.c.alert_id == self.identity, R.c.kind == "alert_basic")))).scalar_one_or_none()
                    data["valid_for_current_input"] = data["freshness"] == "current" and data["run_state"] == "completed" and val["input_material_id"] == row["latest_material_id"]
                if kind == "triage":
                    triage = data
                else:
                    feedback = data
            derived = {"severity_group": band(row["severity"]), "false_positive": row["disposition"] == "false_positive"}
        else:
            rank = case(*[(A.c.severity == value, rank) for value, rank in RANK.items()], else_=None)
            agg = (await self.rows(select(func.count().label("members"), func.min(A.c.event_time).label("first_activity_at"),
                func.max(A.c.event_time).label("last_activity_at"), func.max(A.c.business_updated_at).label("member_updated_at"),
                func.max(rank).label("rank"), func.count().filter(A.c.event_time.is_(None)).label("unknown_times"),
                func.count().filter(A.c.severity.is_(None)).label("unknown_severities")).where(
                *self.store.where(A, A.c.id.in_(self.member_ids())))))[0]
            auto = REVERSE_RANK.get(agg["rank"])
            effective = row["severity_override"] or auto
            derived = {"member_count": agg["members"], "first_activity_at": agg["first_activity_at"],
                "last_activity_at": agg["last_activity_at"], "unknown_event_time_count": agg["unknown_times"],
                "unknown_severity_count": agg["unknown_severities"], "severity_auto": auto, "severity_effective": effective,
                "severity_source": "manual_override" if row["severity_override"] else "member_max" if auto else None,
                "severity_group": band(effective), "updated_at": max(t for t in (row["business_updated_at"], agg["member_updated_at"]) if t)}
        params = {"tenant": self.store.tenant_id, "id": self.identity}
        predicate = "a.id=:id" if self.kind == "alerts" else "EXISTS(SELECT 1 FROM socai2.incident_alerts l WHERE l.tenant_id=a.tenant_id AND l.alert_id=a.id AND l.incident_id=:id)"
        tactics = (await self.db.execute(text(f"""SELECT label, count(DISTINCT a.id) AS alert_count
          FROM socai2.alerts a JOIN socai2.alert_materials m ON m.tenant_id=a.tenant_id AND m.alert_id=a.id AND m.id=a.latest_material_id
          CROSS JOIN LATERAL jsonb_array_elements_text(coalesce(m.detection->'tactics','[]'::jsonb)) tag(label)
          WHERE a.tenant_id=:tenant AND {predicate} GROUP BY label ORDER BY label"""), params)).mappings().all()
        derived["tactics"] = [dict(v) for v in tactics]
        derived["tactic_counting_note"] = "同一告警可在多个阶段各计一次，各阶段之和可能超过告警总数。"
        obj = self.current_objects().subquery()
        derived["object_count"] = (await self.db.execute(select(func.count()).select_from(
            select(obj.c.namespace, obj.c.object_type, obj.c.object_key).distinct().subquery()))).scalar_one()
        rm = m.RunMembers.__table__
        progress = await self.rows(select(R.c.state, func.count(func.distinct(R.c.id)).label("n")).join(rm,
            and_(rm.c.run_id == R.c.id, rm.c.tenant_id == R.c.tenant_id)).where(*self.store.where(R,
                R.c.kind == "baseline", R.c.state.in_(["running", "unknown"])), rm.c.alert_id.in_(self.member_ids())).group_by(R.c.state))
        derived["baseline_execution_counts"] = {"running": 0, "unknown": 0, **{v["state"]: v["n"] for v in progress}}
        root = f"/api/v1/socai2/{self.kind}/{self.identity}"
        return SubjectView(kind=self.kind, facts=project(model, row), owner_name=name, owner_resolution=owner_state,
            derived=derived, material=material, triage=triage, feedback=feedback, analysis_url=root + "/analysis",
            section_urls={key: root + "/records/" + key for key in SECTIONS
                if not (key == "members" and self.kind == "alerts" or key == "incidents" and self.kind == "incidents")})

    def selection(self, query):
        """Shared SQL conditions/order for paging and complete exports."""
        table, tenant = self.table, self.store.tenant_id
        sort_by = query.sort_by or ("ingested_at" if self.kind == "alerts" else "created_at")
        order = query.sort_order or "desc"
        clauses = list(self.store.where(table))
        if query.q:
            clauses.append(lists.title_match(table, query.q))
        for field in ("handling_status", "owner_id", "assignment_state"):
            if (value := getattr(query, field)) is not None:
                clauses.append(table.c[field] == value)
        if self.kind == "alerts":
            rank = lists.severity_rank(A.c.severity)
            clocks = {"ingested_at": A.c.ingested_at, "event_time": A.c.event_time}
            clauses.extend(lists.time_filters(A.c.event_time, query))
        else:
            members = L.join(A, and_(L.c.tenant_id == A.c.tenant_id, L.c.alert_id == A.c.id))
            member_scope = [L.c.tenant_id == tenant, L.c.incident_id == I.c.id]
            maximum = select(func.max(lists.severity_rank(A.c.severity))).select_from(members).where(
                *member_scope).correlate(I).scalar_subquery()
            rank = func.coalesce(lists.severity_rank(I.c.severity_override), maximum)
            last_time = select(func.max(A.c.event_time)).select_from(members).where(
                *member_scope).correlate(I).scalar_subquery()
            clocks = {"created_at": I.c.created_at, "last_activity_at": last_time}
            if query.time_from is not None or query.time_to is not None:
                clauses.append(select(L.c.id).select_from(members).where(
                    *member_scope, *lists.time_filters(A.c.event_time, query)).correlate(I).exists())
        if query.severity is not None:
            clauses.append(rank == RANK[query.severity])
        sort_column = rank if sort_by == "severity" else clocks[sort_by]
        return clauses, sort_column, sort_by, order

    async def listing(self, *, limit=20, before_id=None, query=None):
        if not 1 <= limit <= 50:
            raise StoreError("invalid_page_limit", 422)
        table, tenant = self.table, self.store.tenant_id
        query = query or (AlertListQuery if self.kind == "alerts" else IncidentListQuery)(limit=limit, before_id=before_id)
        limit = query.limit
        clauses, sort_column, sort_by, order = self.selection(query)
        filtered_total = (await self.db.execute(select(func.count()).select_from(table).where(*clauses))).scalar_one()
        listing = select(table, sort_column.label("_list_sort_value")).where(*clauses)
        point = lists.read_cursor(tenant, self.kind, query, sort_by)
        if point:
            value = point.rank if sort_by == "severity" else point.at
            listing = listing.where(lists.seek(sort_column, table.c.id, value, point.id, order))
        if query.before_id:
            self.identity = query.before_id
            before = await self.subject()
            listing = listing.where(lists.seek(sort_column, table.c.id, before[sort_by], query.before_id, order))
        rows = await self.rows(listing.order_by(*lists.ordering(sort_column, table.c.id, order)).limit(limit + 1))
        stats = await self.stats()
        more = len(rows) > limit
        next_cursor = lists.write_cursor(tenant, self.kind, query, sort_by,
            rows[limit - 1]["id"], rows[limit - 1]["_list_sort_value"]) if more else None
        return SubjectPage(kind=self.kind, items=[await self.view(row) for row in rows[:limit]], total=stats["total"],
            next_before_id=rows[limit - 1]["id"] if more and query.legacy else None,
            filtered_total=filtered_total, next_cursor=next_cursor, overall_stats=stats, observed_at=await self.store.now())

    async def stats(self):
        # Overall tenant counts; independent of the current page/cursor.
        table = self.table
        by_state = await self.rows(select(table.c.handling_status, func.count().label("n")).where(
            *self.store.where(table)).group_by(table.c.handling_status))
        counts = {r["handling_status"]: r["n"] for r in by_state}
        out = {"total": sum(counts.values()), "new": counts.get("new", 0), "in_progress": counts.get("in_progress", 0),
            "unknown": counts.get("unknown", 0)}
        if self.kind == "alerts":
            rm = m.RunMembers.__table__
            out["high_severity"] = (await self.db.execute(select(func.count()).select_from(A).where(
                *self.store.where(A, A.c.severity.in_(["critical", "high"]))))).scalar_one()
            out["investigating"] = (await self.db.execute(select(func.count(func.distinct(rm.c.alert_id))).join(R,
                and_(R.c.id == rm.c.run_id, R.c.tenant_id == rm.c.tenant_id)).where(*self.store.where(rm),
                    R.c.kind == "baseline", R.c.state == "running"))).scalar_one()
        else:
            # Every incident is counted once; resolved and unknown are distinct.
            out["active"] = counts.get("new", 0) + counts.get("in_progress", 0)
            out["unassigned"] = (await self.db.execute(select(func.count()).select_from(I).where(*self.store.where(I,
                I.c.assignment_state == "unassigned")))).scalar_one()
            out["grouped_alert_count"] = (await self.db.execute(select(func.count(func.distinct(L.c.alert_id))).where(*self.store.where(L)))).scalar_one()
            out["new_alerts_24h"] = (await self.db.execute(text("""SELECT count(*) FROM socai2.incidents i WHERE i.tenant_id=:tenant AND EXISTS
                (SELECT 1 FROM socai2.incident_alerts l JOIN socai2.alerts a ON a.tenant_id=l.tenant_id AND a.id=l.alert_id
                WHERE l.tenant_id=i.tenant_id AND l.incident_id=i.id AND a.event_time>=transaction_timestamp()-interval '24 hours'
                  AND a.event_time<=transaction_timestamp())"""), {"tenant": self.store.tenant_id})).scalar_one()
            out["high_severity"] = (await self.db.execute(text("""SELECT count(*) FROM socai2.incidents i WHERE i.tenant_id=:tenant AND
                (i.severity_override IN ('critical','high') OR (i.severity_override IS NULL AND EXISTS
                 (SELECT 1 FROM socai2.incident_alerts l JOIN socai2.alerts a ON a.tenant_id=l.tenant_id AND a.id=l.alert_id
                  WHERE l.tenant_id=i.tenant_id AND l.incident_id=i.id AND a.severity IN ('critical','high'))))"""),
                {"tenant": self.store.tenant_id})).scalar_one()
        return out

    async def records(self, section, *, limit=50, offset=0):
        await self.subject()
        if section not in SECTIONS or not 1 <= limit <= 200 or not 0 <= offset <= 100000:
            raise StoreError("invalid_record_page", 422)
        limitations = []
        if section == "members":
            if self.kind != "incidents":
                raise StoreError("section_not_applicable", 404)
            query = select(A, L.c.linked_at, L.c.membership_source, L.c.correlation_basis, L.c.basis_version).join(L,
                and_(L.c.tenant_id == A.c.tenant_id, L.c.alert_id == A.c.id)).where(*self.store.where(A), L.c.incident_id == self.identity)
        elif section == "incidents":
            if self.kind != "alerts":
                raise StoreError("section_not_applicable", 404)
            query = select(I, L.c.linked_at, L.c.membership_source, L.c.correlation_basis, L.c.basis_version).join(L,
                and_(L.c.tenant_id == I.c.tenant_id, L.c.incident_id == I.c.id)).where(*self.store.where(I), L.c.alert_id == self.identity)
        elif section == "objects":
            query = self.current_objects()
            limitations.append("member_object_edges_not_causal_graph")
        elif section == "sources":
            ref = m.AlertSourceRefs.__table__
            query = select(ref).join(A, and_(A.c.tenant_id == ref.c.tenant_id, A.c.id == ref.c.alert_id,
                A.c.latest_material_id == ref.c.material_id)).where(*self.store.where(ref, ref.c.alert_id.in_(self.member_ids())))
        elif section == "source_artifacts":
            key = "alert_id" if self.kind == "alerts" else "incident_id"
            query = select(*ARTIFACT_FIELDS).where(*self.store.where(F,
                F.c[key] == self.identity, F.c.run_id.is_(None)))
            limitations.append("saved_source_versions_not_investigation_runs")
        elif section == "cases":
            c, ca, ci = m.Cases.__table__, m.CaseAlerts.__table__, m.CaseIncidents.__table__
            members = select(ca.c.case_id).where(*self.store.where(ca, ca.c.alert_id.in_(self.member_ids())))
            explicit = select(ci.c.case_id).where(*self.store.where(ci, ci.c.incident_id == self.identity))
            query = select(c.c.id, c.c.title, c.c.handling_status, c.c.scope_revision,
                c.c.id.in_(members).label("via_member_alert"),
                (c.c.id.in_(explicit) if self.kind == "incidents" else literal(False)).label("explicit_incident_link")).where(
                *self.store.where(c), or_(c.c.id.in_(members), c.c.id.in_(explicit) if self.kind == "incidents" else False))
            limitations.append("shared_member_does_not_imply_explicit_incident_link")
        elif section == "activities":
            acts, targets = m.Activities.__table__, m.ActivityTargets.__table__
            key = "alert_id" if self.kind == "alerts" else "incident_id"
            target_ids = select(targets.c.activity_id).where(*self.store.where(targets, targets.c[key] == self.identity))
            query = select(acts).where(*self.store.where(acts), or_(acts.c["subject_" + key] == self.identity, acts.c.id.in_(target_ids)))
            limitations.append("only_explicit_subject_or_target_not_shared_case_activity")
        elif section in {"comments", "responses"}:
            table = m.Comments.__table__ if section == "comments" else m.ResponseLinks.__table__
            key = "alert_id" if self.kind == "alerts" else "incident_id"
            query = select(table).where(*self.store.where(table, table.c[key] == self.identity))
            if section == "responses":
                limitations.append("link_ids_do_not_prove_approval_or_execution")
        elif section == "related_alerts":
            obj = self.current_objects().subquery()
            other = O.alias("other_object")
            matches = select(other.c.alert_id).select_from(other.join(obj, and_(other.c.namespace == obj.c.namespace,
                other.c.object_type == obj.c.object_type, other.c.object_key == obj.c.object_key))).where(
                other.c.tenant_id == self.store.tenant_id, other.c.material_id == A.c.latest_material_id)
            query = select(A).where(*self.store.where(A), A.c.id.in_(matches), A.c.id.not_in(self.member_ids()))
            limitations.append("same_typed_namespaced_object_not_causality_or_feedback_selection")
        else:
            return await self.assets(limit, offset)
        sub = query.subquery()
        total = (await self.db.execute(select(func.count()).select_from(sub))).scalar_one()
        rows = await self.rows(select(sub).order_by(sub.c.id).offset(offset).limit(limit))
        items = [public(r) for r in rows]
        if section == "source_artifacts":
            for item in items:
                item["content_url"] = f"/api/v1/socai2/{self.kind}/{self.identity}/artifacts/{item['id']}"
        if section == "activities":
            targets = m.ActivityTargets.__table__
            for item in items:
                own = await self.rows(select(targets).where(*self.store.where(targets, targets.c.activity_id == item["id"],
                    targets.c[key] == self.identity)).order_by(targets.c.id).limit(201))
                item["matching_targets"] = [public(t) for t in own[:200]]
                item["targets_truncated"] = len(own) > 200
        return RecordPage(items=items, total=total, next_offset=offset + len(rows) if offset + len(rows) < total else None,
            observed_at=await self.store.now(), limitations=limitations)

    async def assets(self, limit, offset):
        # Same exact host/IP inventory rules as C2. This read never saves a match.
        predicate = "a.id=:id" if self.kind == "alerts" else "EXISTS(SELECT 1 FROM socai2.incident_alerts l WHERE l.tenant_id=a.tenant_id AND l.alert_id=a.id AND l.incident_id=:id)"
        base = f"""FROM socai2.alert_objects o JOIN socai2.alerts a ON a.tenant_id=o.tenant_id AND a.id=o.alert_id AND a.latest_material_id=o.material_id
          JOIN {self.lookup_relation('assets')} v ON v.tenant_id=o.tenant_id AND ((o.object_type='host' AND
          (lower(v.name)=lower(o.normalized_value) OR lower(v.fqdn)=lower(o.normalized_value)))
          OR (o.object_type='ip' AND o.normalized_value=ANY(v.ip_addresses)))
          WHERE o.tenant_id=:tenant AND {predicate}"""
        params = {"tenant": self.store.tenant_id, "id": self.identity, "limit": limit, "offset": offset}
        total = (await self.db.execute(text("SELECT count(*) " + base), params)).scalar_one()
        rows = (await self.db.execute(text("""SELECT o.id AS object_id,o.alert_id,o.material_id,o.object_key,o.namespace,
          v.id AS asset_id,v.name,v.fqdn,v.asset_type,v.tags,v.criticality,v.os,v.os_version,v.ip_addresses,
          CASE WHEN o.object_type='ip' THEN 'exact_ip' WHEN lower(v.name)=lower(o.normalized_value)
            THEN 'exact_name_casefold' ELSE 'exact_fqdn_casefold' END AS match_basis """ + base +
          " ORDER BY o.id,v.id LIMIT :limit OFFSET :offset"), params)).mappings().all()
        return RecordPage(items=[dict(r) for r in rows], total=total, next_offset=offset + len(rows) if offset + len(rows) < total else None,
            observed_at=await self.store.now(), limitations=["current_inventory_matches_not_saved_identity_links",
                "inventory_has_no_object_namespace_all_matches_retained", "total_counts_object_asset_edges_not_unique_assets"])

    async def material_content(self, material_id):
        await self.subject()
        if self.kind != "alerts":
            raise StoreError("material_subject_invalid", 404)
        filters = self.store.where(M, M.c.alert_id == self.identity, M.c.id == material_id)
        size = sum(func.coalesce(func.octet_length(cast(M.c[k], String)), 0) for k in ("raw_json", "raw_text", "ocsf_json", "enrichment"))
        cols = [c for c in M.c if c.name not in {"raw_json", "raw_text", "ocsf_json", "enrichment"}]
        row = await self.store.one(select(*cols, size.label("content_bytes")).where(*filters))
        if not row:
            raise StoreError("alert_material_not_found", 404)
        out = {"metadata": public(row), "availability": "content_exceeds_read_limit", "content_json": None, "content_text": None}
        if row["content_bytes"] > retention_limit():
            return out
        body = await self.store.one(select(M.c.raw_json, M.c.raw_text, M.c.ocsf_json, M.c.enrichment).where(*filters))
        return {**out, "availability": "available" if row["material_state"] == "complete" else "retained_" + row["material_state"],
            "content_json": {k: body[k] for k in ("raw_json", "ocsf_json", "enrichment")}, "content_text": body["raw_text"]}

    async def trace(self, run_id):
        reader = StageReader(self.store, "alert_basic" if self.kind == "alerts" else "incident_diagnosis", self.identity)
        await reader.subject()
        run = await reader.run(run_id)
        base = self.store.where(S, S.c.run_id == run_id)
        counts = await self.rows(select(S.c.kind, S.c.state, func.count().label("n"),
            func.max(func.greatest(S.c.started_at, S.c.ended_at)).label("last")).where(*base).group_by(S.c.kind, S.c.state))
        steps = await self.rows(select(S).where(*base).order_by(S.c.seq).limit(MAX_STEPS))
        # Usage totals read every model step, independent of directory truncation.
        all_usage = await self.rows(select(S.c.kind, S.c.state, S.c.usage).where(*base, S.c.kind == "model"))
        models = sum(v["n"] for v in counts if v["kind"] == "model" and v["state"] not in {"planned", "skipped"})
        arts = await self.rows(select(*ARTIFACT_FIELDS).where(*self.store.where(F, F.c.run_id == run_id)).order_by(F.c.captured_at, F.c.id).limit(MAX_ARTIFACTS))
        count, last = (await self.db.execute(select(func.count(), func.max(F.c.captured_at)).where(*self.store.where(F, F.c.run_id == run_id)))).one()
        return {"run": public(run), "steps": [public(s) for s in steps], "steps_total": sum(v["n"] for v in counts),
            "steps_truncated": sum(v["n"] for v in counts) > len(steps), "artifacts": [public(a) for a in arts],
            "artifacts_total": count, "artifacts_truncated": count > len(arts), "usage": usage_totals(all_usage, models),
            "tool_calls": sum(v["n"] for v in counts if v["kind"] == "tool" and v["state"] not in {"planned", "skipped"}),
            "duration_seconds": (run["ended_at"] - run["started_at"]).total_seconds() if run["ended_at"] and run["started_at"] else None,
            "last_recorded_at": max(t for t in [run["requested_at"], run["started_at"], run["ended_at"], last, *[v["last"] for v in counts]] if t),
            "observed_at": await self.store.now()}

    async def artifact_content(self, run_id, artifact_id):
        reader = StageReader(self.store, "alert_basic" if self.kind == "alerts" else "incident_diagnosis", self.identity)
        await reader.subject()
        if run_id is not None:
            await reader.run(run_id)
        key = "alert_id" if self.kind == "alerts" else "incident_id"
        filters = self.store.where(F, F.c.run_id == run_id, F.c[key] == self.identity, F.c.id == artifact_id)
        row = await self.store.one(select(*ARTIFACT_FIELDS, F.c.blob_ref.is_not(None).label("external")).where(*filters))
        if not row:
            raise StoreError("stage_artifact_not_found", 404)
        out = {"metadata": public(row, "external"), "availability": "unavailable", "content_json": None, "content_text": None}
        if row["external"]:
            return {**out, "availability": "external_content_not_loaded"}
        if row["size_bytes"] is None or row["size_bytes"] > retention_limit():
            return {**out, "availability": "content_exceeds_read_limit_or_size_unknown"}
        body = await self.store.one(select(F.c.content_json, F.c.content_text).where(*filters))
        value = body["content_json"]
        raw = encoded(value) if value is not None else body["content_text"].encode() if body["content_text"] is not None else None
        if raw is None or hashlib.sha256(raw).hexdigest() != row["sha256"] or len(raw) != row["size_bytes"]:
            return {**out, "availability": "content_integrity_mismatch"}
        return {**out, "availability": "available" if row["material_state"] == "complete" else "retained_" + row["material_state"], **dict(body)}


class PageReadService(BaselineService):
    def __init__(self, session_factory, *, read_sources=None):
        super().__init__(session_factory)
        self.read_sources = ReadSources.from_config(read_sources) if read_sources is not None else None

    async def read(self, tenant, kind, identity, method, **kwargs):
        try:
            async with self.transaction(tenant, readonly=True) as store:
                reader = PageReader(store, kind, identity, read_sources=self.read_sources)
                if method == "view":
                    return await reader.view(await reader.subject())
                return await getattr(reader, method)(**kwargs)
        except DBAPIError as exc:
            lookup_error(exc)
