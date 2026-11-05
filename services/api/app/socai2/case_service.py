"""New Case writers and manual execution adapter; no legacy table fallback."""
from datetime import timedelta
from uuid import UUID, uuid4, uuid5

from sqlalchemy import column, select, table, update
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import insert

from . import case_relations
from .baseline_contracts import Actor, Limits
from .baseline_service import BaselineService
from .baseline_store import C, R, StoreError, digest
from .case_contracts import (
    AssociationReceipt,
    AssociationRequest,
    BaselinePreparation,
    MutationReceipt,
)

USERS = table("users", column("id", PGUUID(as_uuid=True)), column("tenant_id", PGUUID(as_uuid=True)), schema="public")


class CaseService(BaselineService):
    async def actor(self, store, actor):
        exists = await store.one(select(USERS.c.id).where(USERS.c.id == actor.user_id,
            USERS.c.tenant_id == store.tenant_id))
        if not exists:
            raise StoreError("case_actor_not_in_tenant", 403)

    async def create_case(self, tenant_id: UUID, request, *, actor: Actor):
        # The caller chooses an operation key, never a Case ID. A concurrent
        # replay locks the same identity and verifies the recorded intent.
        cid = uuid5(tenant_id, "socai2.case.create:" + str(request.operation_key))
        body = request.model_dump(mode="json")
        if not body["incident_ids"]:
            body.pop("incident_ids")  # preserve original alert-only create keys
        intent = digest({"actor": str(actor.user_id), "request": body})
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            inserted = (await store.db.execute(insert(C).values(id=cid, tenant_id=tenant_id,
                title=request.title, description=request.description, severity=request.severity,
                severity_source="manual" if request.severity else None, tags=request.tags,
                created_by=actor.user_id).on_conflict_do_nothing(index_elements=[C.c.id]).returning(C.c.id))).scalar_one_or_none()
            await store.case(cid)
            if inserted is None:
                receipt = await store.receipt(cid, request.operation_key, "case_created")
                if not receipt or receipt["request_hash"] != intent:
                    raise StoreError("operation_key_conflict")
                return AssociationReceipt.model_validate(receipt["outcome"])
            linked = await case_relations.associate(store, cid, AssociationRequest(
                operation_key=request.operation_key, expected_scope_revision=0,
                alert_ids=request.alert_ids, incident_ids=request.incident_ids), actor)
            changed = linked.model_dump(mode="json")
            await store.db.execute(update(R).where(*store.where(R, R.c.id == UUID(changed["pending_run_id"])))
                .values(trigger="case_created", purpose="建立案件的初始分析"))
            await store.event(cid, request.operation_key, actor.snapshot(), "case_created",
                {"request_hash": intent, "outcome": changed}, [("case_id", cid, None,
                    {"title": request.title, "scope_revision": changed["scope_revision"]})])
        return AssociationReceipt.model_validate(changed)

    async def associate(self, tenant_id, case_id, request, *, actor):
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            return await case_relations.associate(store, case_id, request, actor)

    async def move_members(self, tenant_id, case_id, request, *, actor):
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            return await case_relations.move(store, case_id, request, actor)

    async def change_members(self, tenant_id, case_id, request, *, actor):
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            out = await store.replace_members(case_id, set(request.alert_ids),
                expected_revision=request.expected_scope_revision, actor=actor, operation_id=request.operation_key)
        return MutationReceipt.model_validate(out)

    async def start_case(self, tenant_id, case_id, run_id, request, *, actor):
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            now = await store.now()
        limits = Limits(max_model_calls=4, max_tool_calls=4, max_tokens=48000, max_rows_per_query=200,
            deadline_at=now + timedelta(seconds=120), policy_version="socai2.manual-http.v2")
        # Await the existing executor. No BackgroundTasks, worker or automatic
        # successor. A client can read Run state while this request is active.
        await self.start_full(tenant_id, case_id, run_id, request, actor=actor, limits=limits)
        return await self.read_run(tenant_id, case_id, run_id)

    async def prepare_baseline(self, tenant_id, case_id, request, *, actor):
        """Explicit user refresh after new human/source facts, without a queue."""
        intent = digest({"actor": str(actor.user_id), "request": request.model_dump(mode="json")})
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            cas = await store.case(case_id)
            prior = await store.receipt(case_id, request.operation_key, "baseline_prepared")
            if prior:
                if prior["request_hash"] != intent:
                    raise StoreError("operation_key_conflict")
                return BaselinePreparation.model_validate(prior["outcome"])
            if cas["scope_revision"] != request.expected_scope_revision:
                raise StoreError("case_scope_revision_conflict")
            if cas["handling_status"] == "resolved":
                raise StoreError("resolved_case_start_policy_not_enabled")
            members = await store.members(case_id)
            if not members:
                raise StoreError("baseline_scope_empty")
            if len(members) > 200:
                raise StoreError("case_member_limit_exceeded", 422)
            pending = await store.one(select(R).where(*store.where(R, R.c.case_id == case_id,
                R.c.kind == "baseline", R.c.state == "pending_update")).with_for_update())
            if pending and pending["scope_revision"] != cas["scope_revision"]:
                raise StoreError("baseline_scope_revision_conflict")
            run_id = pending["id"] if pending else uuid4()
            if pending is None:
                now = await store.now()
                await store.db.execute(insert(R).values(id=run_id, tenant_id=tenant_id, case_id=case_id,
                    kind="baseline", title="完整基础调查", purpose="根据当前材料和人工确认重新调查整案",
                    trigger="manual", scope_revision=cas["scope_revision"], scope_updated_at=cas["business_updated_at"],
                    scope_kind="whole_case", state="pending_update", requested_by=actor.user_id, requested_at=now))
                await store.refresh_members(case_id, run_id)
            out = BaselinePreparation(case_id=case_id, scope_revision=cas["scope_revision"],
                pending_run_id=run_id, created=pending is None)
            await store.event(case_id, request.operation_key, actor.snapshot(), "baseline_prepared",
                {"request_hash": intent, "outcome": out.model_dump(mode="json")},
                [("run_id", run_id, None, {"state": "pending_update", "created": out.created})])
            return out

    async def read_cases(self, tenant_id, query):
        from .case_reader import CaseReader
        async with self.transaction(tenant_id, readonly=True) as store:
            return await CaseReader(store).queue(query)

    async def read_case(self, tenant_id, case_id):
        from .case_reader import CaseReader
        async with self.transaction(tenant_id, readonly=True) as store:
            return await CaseReader(store).case(case_id)

    async def read_history(self, tenant_id, case_id, *, limit=20, cursor=None):
        from .case_reader import CaseReader
        async with self.transaction(tenant_id, readonly=True) as store:
            return await CaseReader(store).history(case_id, limit=limit, cursor=cursor)

    async def read_run(self, tenant_id, case_id, run_id):
        from .case_reader import CaseReader
        async with self.transaction(tenant_id, readonly=True) as store:
            return await CaseReader(store).run(case_id, run_id)

    async def read_result(self, tenant_id, case_id, result_id):
        from .case_reader import CaseReader
        async with self.transaction(tenant_id, readonly=True) as store:
            return await CaseReader(store).result(case_id, result_id)

    async def read_artifact(self, tenant_id, case_id, run_id, artifact_id):
        from .case_reader import CaseReader
        async with self.transaction(tenant_id, readonly=True) as store:
            await CaseReader(store).run_row(case_id, run_id)
            return await CaseReader(store).artifact(case_id, run_id, artifact_id)

    async def read_frozen_material(self, tenant_id, case_id, run_id, material_id):
        async with self.transaction(tenant_id, readonly=True) as store:
            return await store.read_material(case_id, run_id, material_id)
