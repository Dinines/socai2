"""Case-locked management writes; no execution, migration or legacy writes."""
from sqlalchemy import func, select, update

from app.models.socai2 import TaskRevisions, Tasks

from .baseline_store import C, R, StoreError, digest
from .case_contracts import CaseView, project
from .case_management_contracts import CaseManagementReceipt, CaseManagementView
from .case_service import USERS

T, V = Tasks.__table__, TaskRevisions.__table__


async def conditions(store, case_id):
    active = (await store.db.execute(select(R.c.id, R.c.state).where(*store.where(
        R, R.c.case_id == case_id, R.c.state.in_(["running", "unknown"])))
        .order_by(R.c.id))).mappings().all()
    count = (await store.db.execute(select(func.count()).select_from(T.join(V,
        (V.c.tenant_id == T.c.tenant_id) & (V.c.case_id == T.c.case_id)
        & (V.c.task_id == T.c.id) & (V.c.id == T.c.current_revision_id)))
        .where(*store.where(T, T.c.case_id == case_id),
               V.c.state.in_(["not_started", "in_progress"])))).scalar_one()
    return active, count


async def read_management(service, tenant_id, case_id):
    async with service.transaction(tenant_id, readonly=True) as store:
        case = await store.case(case_id, lock=False)
        active, count = await conditions(store, case_id)
        closed = case["handling_status"] == "resolved"
        return CaseManagementView(case=project(CaseView, case), open_task_count=count,
            blocking_runs=active, can_close=not closed and not active, can_reopen=closed,
            requires_open_task_confirmation=not closed and count > 0)


async def manage_case(service, tenant_id, case_id, request, actor, *, action):
    intent = digest({"actor": str(actor.user_id), "request": request.model_dump(mode="json", exclude_unset=True)})
    async with service.transaction(tenant_id) as store:
        await service.actor(store, actor)
        case = await store.case(case_id)
        prior = await store.receipt(case_id, request.operation_key, action)
        if prior:
            if prior["request_hash"] != intent:
                raise StoreError("operation_key_conflict")
            return CaseManagementReceipt.model_validate(prior["outcome"])
        if case["row_version"] != request.expected_row_version:
            raise StoreError("case_row_version_conflict")
        now = await store.now()
        count = None
        if action == "case_management_updated":
            values = request.model_dump(exclude_unset=True, exclude={"operation_key", "expected_row_version"})
            if "handling_status" in values and case["handling_status"] == "resolved":
                raise StoreError("case_reopen_required")
            if "owner_id" in values:
                owner = values["owner_id"]
                if owner is not None and not await store.one(select(USERS.c.id).where(
                    USERS.c.tenant_id == tenant_id, USERS.c.id == owner)):
                    raise StoreError("case_owner_not_in_tenant", 422)
                values.update(assignment_state="assigned" if owner else "unassigned", owner_source_value=None)
                values["assigned_at"] = (case["assigned_at"] if owner == case["owner_id"] else now) if owner else None
            if "severity" in values:
                values["severity_source"] = "manual" if values["severity"] is not None else None
        elif action == "case_closed":
            if case["handling_status"] == "resolved":
                raise StoreError("case_already_resolved")
            active, count = await conditions(store, case_id)
            if active:
                raise StoreError("case_active_run_prevents_close")
            if count and not (request.acknowledge_open_tasks and request.reason):
                raise StoreError("case_open_tasks_confirmation_required")
            values = {"handling_status": "resolved", "resolved_at": now,
                      "resolved_by": actor.user_id, "resolution_note": request.reason}
        elif action == "case_reopened":
            if case["handling_status"] != "resolved":
                raise StoreError("case_not_resolved")
            values = {"handling_status": "in_progress", "reopened_at": now,
                      "resolved_at": None, "resolved_by": None, "resolution_note": None}
        else:
            raise ValueError("unsupported Case management action")
        changed = any(case[k] != value for k, value in values.items())
        before = project(CaseView, case)
        if changed:
            await store.db.execute(update(C).where(*store.where(C, C.c.id == case_id)).values(
                **values, row_version=C.c.row_version + 1, business_updated_at=now))
        after = project(CaseView, await store.case(case_id, lock=False))
        out = CaseManagementReceipt(case=after, changed=changed)
        await store.event(case_id, request.operation_key, actor.snapshot(), action,
            {"request_hash": intent, "outcome": out.model_dump(mode="json"),
             "reason": getattr(request, "reason", None), "open_task_count": count,
             "acknowledge_open_tasks": getattr(request, "acknowledge_open_tasks", None)},
            [("case_id", case_id, before.model_dump(mode="json"), after.model_dump(mode="json"))])
        return out
