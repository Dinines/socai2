"""Recent source-backed alert candidates for human review; no model or writes."""
import base64
import binascii
import json
import os
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select, text

from app.models import socai2 as m

from .alert_review_contracts import (
    AlertReviewCandidate,
    AlertReviewCursor,
    AlertReviewMatch,
    AlertReviewPage,
    AlertReviewScope,
)
from .baseline_service import BaselineService
from .baseline_store import CA, A, StoreError, digest
from .case_contracts import project
from .exploration_contracts import ExplorationExcludedObject
from .exploration_matching import matching_value, object_view
from .page_contracts import AlertFacts

M, O, IA = m.AlertMaterials.__table__, m.AlertObjects.__table__, m.IncidentAlerts.__table__
SQL = Path(__file__).with_name("alert_review_query.sql").read_text()
RULES = {"host": "same_host_and_tactic", "ip": "same_ip", "hash": "same_hash_algorithm_and_value"}


def lookback_days():
    path = Path(os.environ.get("SOCAI2_ALERT_REVIEW_CONFIG_FILE", Path(__file__).with_name("alert-review-query.json")))
    value = json.loads(path.read_text())["default_lookback_days"]
    if type(value) not in (int, float) or not 0 < value <= 3650:
        raise StoreError("invalid_alert_review_configuration", 503)
    return value


def tactics(detection):
    labels = defaultdict(list)
    values = detection.get("tactics", [])
    for i, value in enumerate(values if isinstance(values, list) else []):
        if isinstance(value, str) and value.strip():
            labels[value].append(f"$.detection.tactics[{i}]")
    return [{"label": v, "source_paths": labels[v]} for v in sorted(labels)]


def cursor_point(value, fingerprint):
    if value is None:
        return None
    try:
        point = AlertReviewCursor.model_validate_json(base64.b64decode(value, altchars=b"-_", validate=True))
    except (ValueError, TypeError, binascii.Error):
        raise StoreError("invalid_alert_review_cursor", 422) from None
    if point.fingerprint != fingerprint:
        raise StoreError("alert_review_cursor_scope_changed", 409)
    return point


class AlertReviewService(BaselineService):
    async def read(self, tenant_id, alert_id, query):
        async with self.transaction(tenant_id, readonly=True) as store:
            alert = await store.one(select(A).where(*store.where(A, A.c.id == alert_id)))
            if alert is None:
                raise StoreError("alert_review_source_not_found", 404)
            start, end = query.time_from, query.time_to
            if start is None:
                if alert["event_time"] is None:
                    raise StoreError("alert_review_explicit_window_required", 422)
                try:
                    end = alert["event_time"]
                    start = end - timedelta(days=lookback_days())
                except OverflowError:
                    raise StoreError("alert_review_explicit_window_required", 422) from None
            material = await store.one(select(M).where(*store.where(M, M.c.alert_id == alert_id,
                M.c.id == alert["latest_material_id"]))) if alert["latest_material_id"] else None
            tags = tactics(material["detection"]) if material else []
            objects = (await store.db.execute(select(O).where(*store.where(O, O.c.alert_id == alert_id,
                O.c.material_id == alert["latest_material_id"])).order_by(O.c.id))).mappings().all() if material else []
            seeds, views, excluded = [], {}, []
            for obj in objects:
                value, algorithm, reason = matching_value(obj)
                if obj["object_type"] not in RULES:
                    reason = "unsupported_object_type"
                if reason:
                    excluded.append(ExplorationExcludedObject(object_id=obj["id"], reason=reason))
                    continue
                if obj["object_type"] == "host" and not tags:
                    continue
                views[str(obj["id"])] = object_view(obj, algorithm)
                seeds.append({"id": str(obj["id"]), "object_type": obj["object_type"], "namespace": obj["namespace"],
                    "match_value": value, "algorithm": algorithm})
            available = {s["object_type"] for s in seeds}
            scope = AlertReviewScope(source_alert_id=alert_id, source_material_id=alert["latest_material_id"],
                source_event_time=alert["event_time"], source_namespace=alert["source_namespace"], time_from=start,
                time_to=end, window_basis="explicit" if query.time_from else "seed_lookback",
                unavailable_rules=[rule for typ, rule in RULES.items() if typ not in available], excluded_objects=excluded)
            fingerprint = digest({"tenant": str(tenant_id), "scope": scope.model_dump(mode="json"), "seeds": seeds, "tactics": tags})
            point = cursor_point(query.cursor, fingerprint)
            params = {"tenant": tenant_id, "source": alert["source_namespace"], "seed_alert_id": alert_id,
                "seeds": json.dumps(seeds), "tactics": json.dumps(tags), "time_from": start, "time_to": end, "limit": query.limit + 1}
            total, rows = 0, []
            if seeds:
                total = (await store.db.execute(text(SQL + "SELECT count(*) FROM candidates"), params)).scalar_one()
                tail = ""
                if point:
                    params.update(last_time=point.event_time, last_id=point.alert_id)
                    tail = " WHERE (event_time,alert_id)<(:last_time,:last_id)"
                rows = (await store.db.execute(text(SQL + "SELECT * FROM candidates" + tail
                    + " ORDER BY event_time DESC,alert_id DESC LIMIT :limit"), params)).mappings().all()
            items = [await self.candidate(store, row, views, alert["event_time"]) for row in rows[:query.limit]]
            cursor = None
            if len(rows) > query.limit:
                last = rows[query.limit - 1]
                cursor = base64.urlsafe_b64encode(AlertReviewCursor(fingerprint=fingerprint,
                    event_time=last["event_time"], alert_id=last["alert_id"]).model_dump_json().encode()).decode()
            return AlertReviewPage(items=items, total=total, next_cursor=cursor, scope=scope, observed_at=await store.now())

    async def candidate(self, store, row, seeds, seed_time):
        aid = row["alert_id"]
        alert = await store.one(select(A).where(*store.where(A, A.c.id == aid)))
        ids = [p["candidate"] for p in row["pairs"]]
        objects = (await store.db.execute(select(O).where(*store.where(O, O.c.id.in_(ids))))).mappings().all()
        views = {str(obj["id"]): object_view(obj, matching_value(obj)[1]) for obj in objects}
        matches = [AlertReviewMatch(rule=p["rule"], seed=seeds[p["seed"]], candidate=views[p["candidate"]],
            shared_tactics=p["shared_tactics"]) for p in row["pairs"]]
        cases = (await store.db.execute(select(CA.c.case_id).where(*store.where(CA, CA.c.alert_id == aid)).order_by(CA.c.case_id))).scalars().all()
        incidents = (await store.db.execute(select(IA.c.incident_id).where(*store.where(IA, IA.c.alert_id == aid)).order_by(IA.c.incident_id))).scalars().all()
        return AlertReviewCandidate(alert=project(AlertFacts, alert), matches=matches,
            matched_rules=sorted({p.rule for p in matches}), case_ids=cases, incident_ids=incidents,
            time_delta_seconds=abs((row["event_time"] - seed_time).total_seconds()) if seed_time else None)
