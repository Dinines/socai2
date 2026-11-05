"""Atomic explicit associations and member moves; no automatic investigation."""
from uuid import uuid4, uuid5

from sqlalchemy import insert, select, update

from app.models import socai2 as m

from .baseline_store import A, C, StoreError, digest
from .case_contracts import AssociationReceipt, MoveReceipt

I, IA, CI = m.Incidents.__table__, m.IncidentAlerts.__table__, m.CaseIncidents.__table__


def intent(request, actor):
    return digest({"actor": str(actor.user_id), "request": request.model_dump(mode="json")})


async def replay(store, case_id, request, actor, action, model):
    previous = await store.receipt(case_id, request.operation_key, action)
    if previous is None:
        return None
    if previous["request_hash"] != intent(request, actor):
        raise StoreError("operation_key_conflict")
    return model.model_validate(previous["outcome"])


def editable(case, revision):
    if case["scope_revision"] != revision:
        raise StoreError("case_scope_revision_conflict")
    if case["handling_status"] == "resolved":
        raise StoreError("resolved_case_scope_policy_not_enabled")


async def incident_selection(store, incident_ids):
    if not incident_ids:
        return {}, set()
    # One statement captures membership and namespaces. Do not lock Incident
    # while later checking Alert FKs: Fusion's writer locks Alert -> Incident.
    # Subsequent incident growth is a later operation, not an implicit Case add.
    rows = (await store.db.execute(select(I.c.id, I.c.source_namespace,
        IA.c.alert_id, A.c.source_namespace.label("alert_namespace"))
        .outerjoin(IA, (IA.c.tenant_id == I.c.tenant_id) & (IA.c.incident_id == I.c.id))
        .outerjoin(A, (A.c.tenant_id == IA.c.tenant_id) & (A.c.id == IA.c.alert_id))
        .where(*store.where(I, I.c.id.in_(incident_ids))).order_by(I.c.id, IA.c.alert_id).limit(201))).mappings().all()
    if len(rows) > 200:
        raise StoreError("case_member_limit_exceeded", 422)
    if {r["id"] for r in rows} != set(incident_ids):
        raise StoreError("case_incident_not_found", 404)
    incidents, members = {}, set()
    for row in rows:
        if row["alert_id"] is None or row["alert_namespace"] is None:
            raise StoreError("case_incident_members_unavailable")
        if row["source_namespace"] != row["alert_namespace"] or not row["source_namespace"].strip():
            raise StoreError("case_source_namespace_mismatch")
        incidents.setdefault(row["id"], []).append(row["alert_id"])
        members.add(row["alert_id"])
    return incidents, members


async def associate(store, case_id, request, actor):
    case = await store.case(case_id)
    prior = await replay(store, case_id, request, actor, "case_associated", AssociationReceipt)
    if prior is not None:
        return prior
    editable(case, request.expected_scope_revision)
    incidents, incident_members = await incident_selection(store, request.incident_ids)
    current = await store.members(case_id)
    selected = incident_members | set(request.alert_ids)
    existing = set((await store.db.execute(select(CI.c.incident_id).where(
        *store.where(CI, CI.c.case_id == case_id, CI.c.incident_id.in_(request.incident_ids))))).scalars())
    linked = set(request.incident_ids) - existing
    changed = await store.replace_members(case_id, current | selected,
        expected_revision=request.expected_scope_revision, actor=actor,
        operation_id=uuid5(request.operation_key, "associated-members"),
        membership_sources={aid: "incident_link" for aid in incident_members - set(request.alert_ids)})
    now = await store.now()
    for iid in sorted(linked):
        await store.db.execute(insert(CI).values(id=uuid4(), tenant_id=store.tenant_id,
            case_id=case_id, incident_id=iid, linked_at=now, linked_by=actor.user_id,
            source_operation_id=request.operation_key))
    if linked and not changed["changed"]:
        # Link-only is a business edit, not a new member scope or analysis.
        await store.db.execute(update(C).where(*store.where(C, C.c.id == case_id))
            .values(row_version=C.c.row_version + 1, business_updated_at=now))
    out = AssociationReceipt(**changed, added_alert_ids=sorted(selected - current), linked_incident_ids=sorted(linked))
    await store.event(case_id, request.operation_key, actor.snapshot(), "case_associated",
        {"request_hash": intent(request, actor), "outcome": out.model_dump(mode="json"),
         "incident_member_snapshot": {str(iid): list(map(str, members)) for iid, members in incidents.items()}},
        [("incident_id", iid, {"linked": False}, {"linked": True}) for iid in sorted(linked)])
    return out


async def move(store, case_id, request, actor):
    if case_id == request.target_case_id:
        raise StoreError("case_move_requires_different_target", 422)
    # Every two-Case operation uses the same order, including reverse moves.
    cases = {cid: await store.case(cid) for cid in sorted([case_id, request.target_case_id])}
    prior = await replay(store, case_id, request, actor, "case_members_moved_out", MoveReceipt)
    if prior is not None:
        return prior
    source, target = cases[case_id], cases[request.target_case_id]
    editable(source, request.expected_source_scope_revision)
    editable(target, request.expected_target_scope_revision)
    if source["source_namespace"] is None or target["source_namespace"] is None:
        raise StoreError("case_source_scope_unverified")
    if source["source_namespace"] != target["source_namespace"]:
        raise StoreError("case_source_namespace_mismatch")
    selected = set(request.alert_ids)
    source_members, target_members = await store.members(case_id), await store.members(request.target_case_id)
    if not selected <= source_members:
        raise StoreError("case_move_member_not_in_source")
    # Changes to both Cases and both pending Runs share this transaction.
    left = await store.replace_members(case_id, source_members - selected,
        expected_revision=request.expected_source_scope_revision, actor=actor,
        operation_id=uuid5(request.operation_key, "move-source"))
    right = await store.replace_members(request.target_case_id, target_members | selected,
        expected_revision=request.expected_target_scope_revision, actor=actor,
        operation_id=uuid5(request.operation_key, "move-target"),
        membership_sources={aid: "move" for aid in selected})
    out = MoveReceipt(source=left, target=right, moved_alert_ids=sorted(selected),
        added_to_target_alert_ids=sorted(selected - target_members))
    for cid, action, other in [(case_id, "case_members_moved_out", request.target_case_id),
                              (request.target_case_id, "case_members_moved_in", case_id)]:
        await store.event(cid, request.operation_key, actor.snapshot(), action,
            {"request_hash": intent(request, actor), "outcome": out.model_dump(mode="json"), "other_case_id": str(other)},
            [("alert_id", aid, {"member": aid in (source_members if cid == case_id else target_members)},
              {"member": cid == request.target_case_id}) for aid in sorted(selected)])
    # Explicit incident links describe the original association; a member move
    # neither invents nor transfers those links. Frozen Run/Result rows stay put.
    return out
