"""Read-only recent same-host alerts for the alert detail overview."""
import json
import os
from pathlib import Path

from sqlalchemy import select, text

from app.models import socai2 as m

from .alert_host_contracts import AlertHostItem, AlertHostMatch, AlertHostPage
from .baseline_service import BaselineService
from .baseline_store import A, StoreError
from .case_contracts import project
from .exploration_matching import object_view
from .page_contracts import AlertFacts

M, O = m.AlertMaterials.__table__, m.AlertObjects.__table__
SQL = Path(__file__).with_name("alert_host_query.sql").read_text()


def display_limit():
    path = Path(os.environ.get("SOCAI2_ALERT_HOST_CONFIG_FILE", Path(__file__).with_name("alert-host-query.json")))
    try:
        value = json.loads(path.read_text())["display_limit"]
        if type(value) is not int or not 1 <= value <= 100:
            raise ValueError("display_limit")
    except (OSError, ValueError, KeyError, TypeError):
        raise StoreError("invalid_alert_host_configuration", 503) from None
    return value


class AlertHostService(BaselineService):
    async def read(self, tenant_id, alert_id):
        limit = display_limit()
        async with self.transaction(tenant_id, readonly=True) as store:
            alert = await store.one(select(A).where(*store.where(A, A.c.id == alert_id)))
            if alert is None:
                raise StoreError("alert_host_source_not_found", 404)
            objects = (await store.db.execute(select(O).join(M,
                (M.c.id == O.c.material_id) & (M.c.tenant_id == O.c.tenant_id) & (M.c.alert_id == O.c.alert_id)
            ).where(*store.where(O, O.c.alert_id == alert_id, O.c.material_id == alert["latest_material_id"],
                O.c.object_type == "host")).order_by(O.c.id))).mappings().all() if alert["latest_material_id"] else []
            views = {str(o["id"]): object_view(o, None) for o in objects if o["normalized_value"].strip()}
            seeds = [{"id": k, "namespace": v.namespace, "value": v.normalized_value} for k, v in views.items()]
            total, rows = 0, []
            if seeds:
                params = {"tenant": tenant_id, "source": alert["source_namespace"], "seed_alert_id": alert_id,
                    "seeds": json.dumps(seeds), "limit": limit}
                total = (await store.db.execute(text(SQL + "SELECT count(*) FROM candidates"), params)).scalar_one()
                rows = (await store.db.execute(text(SQL + "SELECT * FROM candidates ORDER BY event_time DESC,alert_id DESC LIMIT :limit"), params)).mappings().all()
            items = []
            for row in rows:
                candidate = await store.one(select(A).where(*store.where(A, A.c.id == row["alert_id"])))
                ids = [p["candidate"] for p in row["pairs"]]
                objects = (await store.db.execute(select(O).where(*store.where(O, O.c.id.in_(ids))))).mappings().all()
                targets = {str(o["id"]): object_view(o, None) for o in objects}
                matches = [AlertHostMatch(seed=views[p["seed"]], candidate=targets[p["candidate"]]) for p in row["pairs"]]
                items.append(AlertHostItem(alert=project(AlertFacts, candidate), matches=matches))
            return AlertHostPage(items=items, total=total, limit=limit, source_alert_id=alert_id,
                source_material_id=alert["latest_material_id"], source_namespace=alert["source_namespace"],
                source_hosts=list(views.values()), observed_at=await store.now())
