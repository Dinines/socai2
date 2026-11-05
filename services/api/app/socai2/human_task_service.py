"""Versioned human feedback on existing tasks/task_revisions; Case -> Task locks."""
from uuid import uuid4, uuid5

from sqlalchemy import func, insert, null, select, update

from app.models import socai2 as m

from .baseline_context import reference
from .baseline_store import A, C, StoreError, digest
from .case_contracts import project
from .case_service import USERS, CaseService
from .human_task_contracts import (
    TaskFields,
    TaskMutation,
    TaskRevisionPage,
    TaskRevisionView,
    TaskView,
)

T, V = m.Tasks.__table__, m.TaskRevisions.__table__
M, F, R, O = m.AlertMaterials.__table__, m.Artifacts.__table__, m.Results.__table__, m.AlertObjects.__table__


def task_view(task, revision):
    return TaskView(**{k: task[k] for k in TaskView.model_fields if k != "current"},
        current=project(TaskRevisionView, revision))


class HumanTaskService(CaseService):
    async def task(self, store, case_id, task_id, *, lock=False):
        query = select(T).where(*store.where(T, T.c.case_id == case_id, T.c.id == task_id))
        row = await store.one(query.with_for_update() if lock else query)
        if row is None:
            raise StoreError("case_task_not_found", 404)
        return row

    async def revision(self, store, case_id, task_id, revision_id):
        row = await store.one(select(V).where(*store.where(V, V.c.case_id == case_id,
            V.c.task_id == task_id, V.c.id == revision_id)))
        if row is None:
            raise StoreError("case_task_revision_not_found", 404)
        return row

    async def scope(self, store, case_id, scope, members):
        if scope is None:
            return
        selected = set(scope.alert_ids)
        if not selected or not selected <= members:
            raise StoreError("task_scope_outside_current_case", 422)
        if scope.kind == "whole_case" and selected != members:
            raise StoreError("task_whole_case_scope_incomplete", 422)
        if scope.kind == "explicit_objects" and not scope.object_keys:
            raise StoreError("task_object_scope_empty", 422)
        keys = set((await store.db.execute(select(O.c.object_key).join(A,
            (A.c.tenant_id == O.c.tenant_id) & (A.c.id == O.c.alert_id) & (A.c.latest_material_id == O.c.material_id))
            .where(*store.where(O, O.c.alert_id.in_(selected))))).scalars())
        if len(set(scope.object_keys)) != len(scope.object_keys) or not set(scope.object_keys) <= keys:
            raise StoreError("task_objects_outside_current_scope", 422)

    async def references(self, store, case_id, requested, members):
        out = []
        for ref in requested:
            table = {"alert_material": M, "artifact": F, "result": R, "task_revision": V}[ref.type]
            row = await store.one(select(table).where(*store.where(table, table.c.id == ref.id)))
            if row is None:
                raise StoreError("task_source_reference_not_found", 404)
            if ref.type == "alert_material":
                valid, role = row["alert_id"] in members, "observation"
            elif ref.type == "artifact":
                valid = row["case_id"] == case_id or (row["case_id"] is None and row["alert_id"] in members)
                role = "execution_receipt"
            elif ref.type == "result":
                valid, role = row["case_id"] == case_id, "prior_analysis"
            else:
                valid, role = row["case_id"] == case_id, "human_statement" if row["state"] == "completed" else "execution_receipt"
            if not valid:
                raise StoreError("task_source_reference_outside_case", 422)
            out.append(reference(ref.type, ref.id, role))
        return out

    async def write(self, tenant_id, case_id, request, *, actor, task_id=None):
        creating = task_id is None
        tid = task_id or uuid5(case_id, "socai2.human-task:" + str(request.operation_key))
        action = "human_task_created" if creating else "human_task_updated"
        intent = digest({"task_id": str(tid), "actor": str(actor.user_id), "request": request.model_dump(mode="json")})
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            case = await store.case(case_id)
            prior = await store.receipt(case_id, request.operation_key, action)
            if prior:
                if prior["request_hash"] != intent:
                    raise StoreError("operation_key_conflict")
                return TaskMutation.model_validate(prior["outcome"])
            if case["scope_revision"] != request.expected_scope_revision:
                raise StoreError("case_scope_revision_conflict")
            old_task = None if creating else await self.task(store, case_id, tid, lock=True)
            old = None if creating else await self.revision(store, case_id, tid, old_task["current_revision_id"])
            if old_task and old_task["row_version"] != request.expected_row_version:
                raise StoreError("task_row_version_conflict")
            if request.assignee_id is not None and not await store.one(select(USERS.c.id).where(
                    USERS.c.id == request.assignee_id, USERS.c.tenant_id == tenant_id)):
                raise StoreError("task_assignee_not_in_tenant", 422)
            if creating and request.origin_result_id is not None:
                origin = await store.one(select(R).where(*store.where(R, R.c.case_id == case_id, R.c.id == request.origin_result_id)))
                if origin is None:
                    raise StoreError("task_origin_result_not_found", 404)
                if request.origin_finding_id is not None and request.origin_finding_id not in {f["id"] for f in origin["findings"]}:
                    raise StoreError("task_origin_finding_not_found", 422)
            fields = {key: getattr(request, key) for key in TaskFields.model_fields}
            payload = request.model_dump(mode="json")
            # Metadata-only edits keep immutable confirmed scope and completion.
            # Re-entering completed state or changing feedback re-attests it now.
            feedback_same = old is not None and all(payload[k] == old[k] for k in ("result_text", "result_scope"))
            refs_same = old is not None and [(r["type"], r["id"]) for r in payload["source_refs"]] == [
                (r["type"], r["id"]) for r in old["source_refs"]]
            members = await store.members(case_id)
            if not feedback_same or (request.state == "completed" and old and (old["state"] != "completed" or not refs_same)):
                await self.scope(store, case_id, request.result_scope, members)
            refs = old["source_refs"] if refs_same else await self.references(store, case_id, request.source_refs, members)
            fields["source_refs"] = refs
            fields["result_scope"] = payload["result_scope"]
            unchanged = old is not None and all(fields[k] == old[k] for k in TaskFields.model_fields)
            if unchanged:
                out = TaskMutation(task=task_view(old_task, old), changed=False)
            else:
                now, revision_id = await store.now(), uuid4()
                completed_at = completed_by = None
                if request.state == "completed":
                    if old and old["state"] == "completed" and feedback_same and refs_same:
                        completed_at, completed_by = old["completed_at"], old["completed_by"]
                    else:
                        completed_at, completed_by = now, actor.user_id
                values = {**fields, "id": revision_id, "tenant_id": tenant_id, "case_id": case_id, "task_id": tid,
                    "revision": old["revision"]+1 if old else 1, "completed_at": completed_at, "completed_by": completed_by,
                    "changed_at": now, "changed_by": actor.user_id}
                if values["result_scope"] is None:
                    values["result_scope"] = null()
                if creating:
                    await store.db.execute(insert(T).values(id=tid, tenant_id=tenant_id, case_id=case_id,
                        current_revision_id=revision_id, origin_result_id=request.origin_result_id,
                        origin_finding_id=request.origin_finding_id, created_at=now, created_by=actor.user_id, updated_at=now))
                await store.db.execute(insert(V).values(**values))
                if old_task:
                    await store.db.execute(update(T).where(*store.where(T, T.c.id == tid)).values(
                        current_revision_id=revision_id, updated_at=now, row_version=T.c.row_version+1))
                await store.db.execute(update(C).where(*store.where(C, C.c.id == case_id)).values(
                    business_updated_at=now, row_version=C.c.row_version+1))
                out = TaskMutation(task=task_view(await self.task(store, case_id, tid),
                    await self.revision(store, case_id, tid, revision_id)), changed=True)
            await store.event(case_id, request.operation_key, actor.snapshot(), action,
                {"request_hash": intent, "outcome": out.model_dump(mode="json")},
                [("task_id", tid, {"revision_id": str(old["id"])} if old else None,
                  {"revision_id": str(out.task.current_revision_id), "state": out.task.current.state, "changed": out.changed})])
            return out

    async def read(self, tenant_id, case_id, task_id):
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.case(case_id, lock=False)
            task = await self.task(store, case_id, task_id)
            return task_view(task, await self.revision(store, case_id, task_id, task["current_revision_id"]))

    async def list(self, tenant_id, case_id, *, limit=20, offset=0):
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.case(case_id, lock=False)
            total = (await store.db.execute(select(func.count()).select_from(T).where(*store.where(T, T.c.case_id == case_id)))).scalar_one()
            tasks = (await store.db.execute(select(T).where(*store.where(T, T.c.case_id == case_id))
                .order_by(T.c.created_at.desc(), T.c.id).limit(limit).offset(offset))).mappings().all()
            items = [task_view(t, await self.revision(store, case_id, t["id"], t["current_revision_id"])) for t in tasks]
            return {"items": items, "total": total, "next_offset": offset+len(items) if offset+len(items) < total else None}

    async def revisions(self, tenant_id, case_id, task_id, *, limit=20, offset=0):
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.case(case_id, lock=False)
            await self.task(store, case_id, task_id)
            where = store.where(V, V.c.case_id == case_id, V.c.task_id == task_id)
            total = (await store.db.execute(select(func.count()).select_from(V).where(*where))).scalar_one()
            rows = (await store.db.execute(select(V).where(*where).order_by(V.c.revision.desc()).limit(limit).offset(offset))).mappings().all()
            return TaskRevisionPage(items=[project(TaskRevisionView, r) for r in rows], total=total,
                next_offset=offset+len(rows) if offset+len(rows) < total else None)

    async def read_revision(self, tenant_id, case_id, task_id, revision_id):
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.case(case_id, lock=False)
            await self.task(store, case_id, task_id)
            return project(TaskRevisionView, await self.revision(store, case_id, task_id, revision_id))
