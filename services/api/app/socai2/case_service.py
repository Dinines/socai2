"""New Case writers and manual execution adapter; no legacy table fallback."""
from uuid import uuid4

from sqlalchemy import column, select, table
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import insert

from . import case_relations
from .baseline_contracts import Actor
from .baseline_service import BaselineService
from .baseline_store import R, StoreError, digest
from .case_contracts import (
    BaselinePreparation,
)

USERS = table("users", column("id", PGUUID(as_uuid=True)), column("tenant_id", PGUUID(as_uuid=True)), schema="public")


class CaseService(BaselineService):
    async def preview_result_adoption(self, tenant_id, case_id, result_id):
        from .case_adoption import read_preview
        return await read_preview(self, tenant_id, case_id, result_id)

    async def adopt_result(self, tenant_id, case_id, result_id, request, *, actor):
        from .case_adoption import adopt
        return await adopt(self, tenant_id, case_id, result_id, request, actor)

    async def read_assessment_history(self, tenant_id, case_id, *, limit=20, offset=0):
        from .case_adoption import read_history
        return await read_history(self, tenant_id, case_id, limit=limit, offset=offset)

    async def update_page_data(self, tenant_id, case_id, request, *, actor):
        from .case_data import write_data
        return await write_data(self, tenant_id, case_id, request, actor)

    async def publish_evidence(self, tenant_id, case_id, request, *, actor):
        from .case_data import write_data
        return await write_data(self, tenant_id, case_id, request, actor, evidence=True)

    async def read_page_data(self, tenant_id, case_id):
        from .case_data import read_page_data
        async with self.transaction(tenant_id, readonly=True) as store:
            return await read_page_data(store, await store.case(case_id, lock=False))

    async def actor(self, store, actor):
        exists = await store.one(select(USERS.c.id).where(USERS.c.id == actor.user_id,
            USERS.c.tenant_id == store.tenant_id))
        if not exists:
            raise StoreError("case_actor_not_in_tenant", 403)

    def allocation_policies(self):
        from .analysis_task_policy import AnalysisTaskPolicy
        from .case_allocation_policy import CaseAllocationPolicy
        return CaseAllocationPolicy.load(), AnalysisTaskPolicy.load()

    async def create_case(self, tenant_id, request, *, actor: Actor):
        policy, tasks = self.allocation_policies()
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            return await case_relations.create(store, request, actor, policy, tasks)

    async def associate(self, tenant_id, case_id, request, *, actor):
        policy, tasks = self.allocation_policies()
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            return await case_relations.associate(store, case_id, request, actor, policy, tasks)

    async def move_members(self, tenant_id, case_id, request, *, actor):
        policy, tasks = self.allocation_policies()
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            return await case_relations.move(store, case_id, request, actor, policy, tasks)

    async def change_members(self, tenant_id, case_id, request, *, actor):
        policy, tasks = self.allocation_policies()
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            return await case_relations.replace(store, case_id, request, actor, policy, tasks)

    async def follow_incident(self, tenant_id, case_id, request, *, actor):
        policy, tasks = self.allocation_policies()
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            return await case_relations.follow(store, case_id, request.incident_id, request, actor, policy, tasks)

    async def read_related_cases(self, tenant_id, case_id, *, limit=None, cursor=None):
        from .case_allocation_policy import CaseAllocationPolicy
        from .case_relationship_reader import related_cases
        policy = CaseAllocationPolicy.load()
        async with self.transaction(tenant_id, readonly=True) as store:
            return await related_cases(store, case_id, limit=policy.page_size(limit), cursor=cursor)

    async def start_case(self, tenant_id, case_id, run_id, request, *, actor):
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            now = await store.now()
        from .runtime_policy import active_policy
        policy = active_policy()
        limits = policy.case.limits(now, policy.identity)
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
            if run_id is None:
                await store.case(case_id, lock=False)
            else:
                await CaseReader(store).run_row(case_id, run_id)
            return await CaseReader(store).artifact(case_id, run_id, artifact_id)

    async def read_activities(self, tenant_id, case_id, *, limit=50, offset=0):
        from .case_reader import CaseReader
        async with self.transaction(tenant_id, readonly=True) as store:
            return await CaseReader(store).activities(case_id, limit=limit, offset=offset)

    async def read_frozen_material(self, tenant_id, case_id, run_id, material_id):
        async with self.transaction(tenant_id, readonly=True) as store:
            return await store.read_material(case_id, run_id, material_id)
