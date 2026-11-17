"""Read one layer of Case candidates from existing records; no graph mutations."""
import base64
import binascii
import json
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select, text

from app.models import socai2 as m

from .baseline_service import BaselineService
from .baseline_store import CA, A, StoreError, digest
from .case_contracts import project
from .exploration_contracts import (
    ExplorationCandidate,
    ExplorationCursor,
    ExplorationExcludedObject,
    ExplorationMatch,
    ExplorationPage,
    ExplorationScope,
)
from .exploration_matching import matching_value, object_view, window_hours
from .page_contracts import AlertFacts

O, IA = m.AlertObjects.__table__, m.IncidentAlerts.__table__
SQL = Path(__file__).with_name("exploration_query.sql").read_text()


def cursor_point(query, fingerprint):
    if query.cursor is None:
        return None
    try:
        point = ExplorationCursor.model_validate_json(base64.b64decode(query.cursor, altchars=b"-_", validate=True))
    except (ValueError, TypeError, binascii.Error):
        raise StoreError("invalid_exploration_cursor", 422) from None
    if point.fingerprint != fingerprint:
        raise StoreError("exploration_cursor_scope_changed", 409)
    return point


class ExplorationService(BaselineService):
    async def seeds(self, store, case, query):
        alerts = select(A.c.id, A.c.event_time, A.c.latest_material_id).where(*store.where(A))
        if query.object_id:
            obj = await store.one(select(O).where(*store.where(O, O.c.id == query.object_id)))
            if obj is None:
                raise StoreError("exploration_start_not_found", 404)
            alerts = alerts.where(A.c.id == obj["alert_id"])
        elif query.alert_id:
            alerts = alerts.where(A.c.id == query.alert_id)
        else:
            alerts = alerts.where(A.c.id.in_(select(CA.c.alert_id).where(*store.where(CA, CA.c.case_id == case["id"]))))
        alerts = alerts.where(A.c.source_namespace == case["source_namespace"])
        rows = (await store.db.execute(alerts.order_by(A.c.id))).mappings().all()
        if (query.alert_id or query.object_id) and not rows:
            raise StoreError("exploration_start_not_found", 404)
        if query.object_id and obj["material_id"] != rows[0]["latest_material_id"]:
            raise StoreError("exploration_start_material_changed", 409)
        objects = select(O).join(A, (A.c.tenant_id == O.c.tenant_id) & (A.c.id == O.c.alert_id)
            & (A.c.latest_material_id == O.c.material_id)).where(*store.where(O, O.c.alert_id.in_([r["id"] for r in rows])))
        if query.object_id:
            objects = objects.where(O.c.id == query.object_id)
        return rows, (await store.db.execute(objects.order_by(O.c.id))).mappings().all()

    async def read(self, tenant_id, case_id, query):
        async with self.transaction(tenant_id, readonly=True) as store:
            case = await store.case(case_id, lock=False)
            alerts, objects = await self.seeds(store, case, query)
            times = {r["id"]: r["event_time"] for r in alerts}
            seeds, views, excluded = [], {}, []
            for obj in objects:
                value, algorithm, reason = matching_value(obj)
                if reason:
                    if query.object_id:
                        raise StoreError("exploration_" + reason, 422)
                    excluded.append(ExplorationExcludedObject(object_id=obj["id"], reason=reason))
                    continue
                views[str(obj["id"])] = object_view(obj, algorithm)
                seeds.append({"id": str(obj["id"]), "alert_id": str(obj["alert_id"]), "object_type": obj["object_type"],
                    "namespace": obj["namespace"], "match_value": value, "algorithm": algorithm,
                    "event_time": times[obj["alert_id"]].isoformat() if times[obj["alert_id"]] else None})
            start, end = query.time_from, query.time_to
            basis = "explicit" if start else "no_seeds"
            known = [t for t in times.values() if t is not None]
            if start is None and seeds:
                if not known:
                    raise StoreError("exploration_explicit_window_required", 422)
                try:
                    margin = timedelta(hours=window_hours())
                    start, end = min(known) - margin, max(known) + margin
                except OverflowError:
                    raise StoreError("exploration_explicit_window_required", 422) from None
                basis = "seed_event_times"
            scope = ExplorationScope(seed_kind="object" if query.object_id else "alert" if query.alert_id else "case",
                seed_alert_ids=list(times), source_namespace=case["source_namespace"], case_scope_revision=case["scope_revision"],
                time_from=start, time_to=end, window_basis=basis, excluded_objects=excluded)
            fingerprint = digest({"tenant": str(tenant_id), "case": str(case_id), "scope": scope.model_dump(mode="json"),
                "seeds": seeds, "materials": [str(r["latest_material_id"]) for r in alerts]})
            point = cursor_point(query, fingerprint)
            if not seeds:
                return ExplorationPage(items=[], total=0, next_cursor=None, scope=scope, observed_at=await store.now())
            params = {"tenant": tenant_id, "source": case["source_namespace"], "seeds": json.dumps(seeds),
                "seed_alert_ids": list(times), "time_from": start, "time_to": end, "limit": query.limit + 1}
            total = (await store.db.execute(text(SQL + "SELECT count(*) FROM candidates"), params)).scalar_one()
            where = ""
            if point:
                params.update(shared=point.shared, delta=point.delta, last_id=point.alert_id)
                tail = "delta IS NULL AND alert_id>:last_id" if point.delta is None else (
                    "delta>:delta OR delta IS NULL OR (delta=:delta AND alert_id>:last_id)")
                where = " WHERE shared<:shared OR (shared=:shared AND (" + tail + "))"
            rows = (await store.db.execute(text(SQL + "SELECT * FROM candidates" + where
                + " ORDER BY shared DESC,delta ASC NULLS LAST,alert_id ASC LIMIT :limit"), params)).mappings().all()
            items = [await self.candidate(store, case_id, row, views) for row in rows[:query.limit]]
            cursor = None
            if len(rows) > query.limit:
                last = rows[query.limit - 1]
                out = ExplorationCursor(fingerprint=fingerprint, shared=last["shared"], delta=last["delta"], alert_id=last["alert_id"])
                cursor = base64.urlsafe_b64encode(out.model_dump_json().encode()).decode()
            return ExplorationPage(items=items, total=total, next_cursor=cursor, scope=scope, observed_at=await store.now())

    async def candidate(self, store, case_id, row, seeds):
        aid = row["alert_id"]
        alert = await store.one(select(A).where(*store.where(A, A.c.id == aid)))
        ids = [pair["candidate"] for pair in row["pairs"]]
        objects = (await store.db.execute(select(O).where(*store.where(O, O.c.id.in_(ids))))).mappings().all()
        views = {str(obj["id"]): object_view(obj, matching_value(obj)[1]) for obj in objects}
        case_ids = (await store.db.execute(select(CA.c.case_id).where(*store.where(CA, CA.c.alert_id == aid))
            .order_by(CA.c.case_id))).scalars().all()
        incidents = (await store.db.execute(select(IA.c.incident_id).where(*store.where(IA, IA.c.alert_id == aid))
            .order_by(IA.c.incident_id))).scalars().all()
        matches = [ExplorationMatch(seed=seeds[p["seed"]], candidate=views[p["candidate"]],
            basis="same_hash_algorithm_and_value" if seeds[p["seed"]].algorithm else "same_source_value") for p in row["pairs"]]
        return ExplorationCandidate(alert=project(AlertFacts, alert), shared_object_count=row["shared"],
            time_delta_seconds=row["delta"], already_in_case=case_id in case_ids,
            case_ids=case_ids, incident_ids=incidents, matches=matches)
