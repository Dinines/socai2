"""Read and freeze original sources for browsing without writing domain state."""
from sqlalchemy import select

from .baseline_store import CA, RES, RM, A, F, R, StoreError, digest
from .case_contracts import project
from .exploration import O
from .exploration_matching import matching_value, object_view
from .exploration_state_contracts import ExplorationBase, ExplorationSources
from .page_contracts import AlertFacts


async def sources(store, pairs):
    alerts, objects = {}, {}
    for aid, mid in pairs:
        if aid not in alerts:
            row = await store.one(select(A).where(*store.where(A, A.c.id == aid)))
            if row is None:
                raise StoreError("exploration_source_not_found", 404)
            alerts[aid] = project(AlertFacts, row)
        if mid is not None:
            rows = (await store.db.execute(select(O).where(*store.where(O,
                O.c.alert_id == aid, O.c.material_id == mid)).order_by(O.c.id))).mappings().all()
            for row in rows:
                objects[row["id"]] = object_view(row, matching_value(row)[1])
    return ExplorationSources(alerts=sorted(alerts.values(), key=lambda v: str(v.id)),
        objects=sorted(objects.values(), key=lambda v: str(v.id)))


async def base(store, case, run_id=None, *, choose_latest=False):
    query = select(R).where(*store.where(R, R.c.case_id == case["id"],
        R.c.kind == "baseline", R.c.state == "completed"))
    run = await store.one(query.order_by(R.c.ended_at.desc(), R.c.id.desc()).limit(1)) if choose_latest else (
        await store.one(query.where(R.c.id == run_id)) if run_id else None)
    if run_id and run is None:
        raise StoreError("exploration_completed_run_not_found", 404)
    result, artifact = None, None
    if run:
        result = await store.one(select(RES).where(*store.where(RES, RES.c.case_id == case["id"],
            RES.c.source_run_id == run["id"], RES.c.kind == "baseline"))
            .order_by(RES.c.saved_at.desc(), RES.c.id.desc()).limit(1))
        if result and result["graph_artifact_id"]:
            artifact = await store.one(select(F).where(*store.where(F, F.c.case_id == case["id"],
                F.c.run_id == run["id"], F.c.id == result["graph_artifact_id"], F.c.kind.in_(["alert_graph", "attack_path", "attack_chain"]))))
        pairs = (await store.db.execute(select(RM.c.alert_id, RM.c.material_id).where(*store.where(RM,
            RM.c.case_id == case["id"], RM.c.run_id == run["id"])).order_by(RM.c.alert_id))).all()
    else:
        pairs = (await store.db.execute(select(A.c.id, A.c.latest_material_id).join(CA,
            (CA.c.tenant_id == A.c.tenant_id) & (CA.c.alert_id == A.c.id)).where(*store.where(CA,
                CA.c.case_id == case["id"])).order_by(A.c.id))).all()
    value = ExplorationBase(kind="investigation" if run else "members", case_id=case["id"],
        run_id=run["id"] if run else None, result_id=result["id"] if result else None,
        graph_artifact_id=result["graph_artifact_id"] if result else None,
        scope_revision=run["scope_revision"] if run else case["scope_revision"],
        delivery_state=run["delivery_state"] if run else None,
        graph_state=artifact["material_state"] if artifact and artifact["content_json"] is not None else
            "unavailable" if run else "members",
        graph=artifact["content_json"] if artifact else None, sources=await sources(store, pairs), fingerprint="")
    return value.model_copy(update={"fingerprint": digest(value.model_dump(mode="json", exclude={"fingerprint"}))})
