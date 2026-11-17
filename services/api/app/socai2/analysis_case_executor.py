"""Full Case tasks execute C1-C6 with immutable materials and preceding Run selection."""
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update

from app.models.tenant import User

from .analysis_dispatch_types import Material, Outcome
from .analysis_incident_executor import executors as ai_executors
from .analysis_task_store import A, S, T
from .baseline_context import capture
from .baseline_contracts import FULL_EXECUTOR_VERSION, Actor, Start
from .baseline_executor import BaselineExecutor
from .baseline_service import BaselineService
from .baseline_store import F, R, StoreError, digest
from .case_allocation_policy import CaseAllocationPolicy
from .case_comparison import select_previous
from .case_execution_input import CaseExecutionPolicy
from .case_update_inputs import VERSION, business_view, unchanged
from .case_update_scanner import AutomaticCaseActor, check_updates, follow_current
from .runtime_policy import active_policy


class CaseTaskExecutor:
    def __init__(self, service, policy, task_service, scan_batch_size, allocation_policy, *, gateway_factory=None, lake_factory=None):
        if type(scan_batch_size) is not int or scan_batch_size < 1:
            raise ValueError("invalid Case scan batch size")
        self.service, self.policy = service, policy
        self.task_service, self.scan_batch_size, self.allocation_policy = task_service, scan_batch_size, allocation_policy
        self.gateway_factory, self.lake_factory = gateway_factory, lake_factory

    def capacity_profile(self):
        policy = active_policy()
        return {"query": self.policy.snapshot(), "max_total_tokens": policy.case.max_total_tokens,
            "context_tokens": policy.model.context_tokens, "max_prepared_bytes": policy.model.max_prepared_bytes,
            "final_reserved_input_tokens": policy.model.final_reserved_input_tokens,
            "final_reserved_calls": policy.model.final_reserved_calls,
            "output_tokens": {key: policy.model.output_tokens[key] for key in ("C3", "Deep", "C6")},
            "tokenizer": dict(policy.model.tokenizer),
            "input_profile": policy.case_io.identity if policy.case_io else None}

    async def load_in_store(self, store, case_id, *, automatic):
        case = await store.case(case_id, lock=False)
        context = await capture(store.db, store.tenant_id, case_id,
            Start(expected_scope_revision=case["scope_revision"], operation_key=uuid4()))
        if not context.alerts:
            raise StoreError("baseline_scope_empty")
        view = business_view(context)
        selected = {iid for iid, item in context.incidents.items()
            if item.linked_from_case and item.incident.get("active_case_id") == str(case_id)} if automatic else None
        state = await store.one(select(S).where(*store.where(S,
            S.c.subject_type == "case", S.c.subject_id == case_id)))
        completed_id, stopped_id, capacity_changed = None, None, False
        if state:
            if state["last_completed_attempt_id"]:
                attempt = await store.one(select(A).where(*store.where(A, A.c.id == state["last_completed_attempt_id"])))
                if attempt and attempt["run_id"]:
                    old = await store.read_context(case_id, attempt["run_id"])
                    if unchanged(old, view, selected):
                        completed_id = attempt["id"]
            if state["stopped_task_id"]:
                attempt = await store.one(select(A).where(*store.where(A, A.c.task_id == state["stopped_task_id"]))
                    .order_by(A.c.attempt_no.desc()).limit(1))
                if attempt and attempt["run_id"] and attempt["input_artifact_id"]:
                    old = await store.read_context(case_id, attempt["run_id"])
                    if unchanged(old, view, selected):
                        stopped_id = state["stopped_task_id"]
                    if state["automatic_stop_reason"] == "capacity_exceeded":
                        prior_capacity = (old.update_context or {}).get("capacity_profile")
                        capacity_changed = prior_capacity is not None and prior_capacity != self.capacity_profile()
        return Material(digest(view), view, capacity_changed, completed_id, stopped_id)

    async def load(self, task):
        if task["intent"] not in {"initial", "check", "rerun"}:
            raise StoreError("case_update_executor_not_available", 503)
        await follow_current(self, task["tenant_id"], task["subject_id"], automatic=task["source"] != "user")
        async with self.service.transaction(task["tenant_id"], readonly=True) as store:
            return await self.load_in_store(store, task["subject_id"], automatic=task["source"] != "user")

    async def check_updates(self, tenant_id, now):
        return await check_updates(self, tenant_id, now)

    async def prepare(self, context):
        task, tenant_id, case_id = context.task, context.task["tenant_id"], context.task["subject_id"]
        async with self.service.transaction(tenant_id) as store:
            case = await store.case(case_id)
            actor = AutomaticCaseActor()
            if task["submitted_by"] is not None:
                user = (await store.db.execute(select(User.username).where(
                    User.tenant_id == tenant_id, User.id == task["submitted_by"]))).scalar_one_or_none()
                if not user:
                    raise StoreError("case_task_actor_unavailable", 422)
                actor = Actor(user_id=task["submitted_by"], name=user)
            now, run_id = await store.now(), uuid4()
            comparison = await select_previous(store, case_id, await store.members(case_id))
            rid = UUID(comparison["comparison_result_id"]) if comparison["comparison_result_id"] else None
            await store.db.execute(insert(R).values(id=run_id, tenant_id=tenant_id, case_id=case_id,
                kind="baseline", title="完整基础调查", purpose="调查当前 Case 全部关联告警",
                trigger="retry" if context.attempt["attempt_no"] > 1 else "case_created" if task["intent"] == "initial"
                    else "manual" if task["source"] == "user" else "refresh",
                scope_revision=case["scope_revision"], scope_updated_at=now, scope_kind="whole_case",
                state="pending_update", requested_by=task["submitted_by"], requested_at=now))
            policy = active_policy()
            claim = await store.claim(case_id, run_id,
                Start(expected_scope_revision=case["scope_revision"], operation_key=context.operation_key,
                    comparison_result_id=rid),
                actor=actor, executor_version=FULL_EXECUTOR_VERSION,
                limits=policy.case.limits(now, policy.identity), attempt_id=context.attempt["id"], query_policy=self.policy,
                update_context={"version": VERSION, "comparison_context": comparison,
                    "capacity_profile": self.capacity_profile()})
            frozen = await store.read_context(case_id, run_id)
            actual_digest = digest(frozen.update_context["business_view"])
            policy_id = (await store.db.execute(select(F.c.id).where(*store.where(F,
                F.c.run_id == run_id, F.c.schema_version == "socai2.runtime-policy.v1")))).scalar_one()
            await store.db.execute(update(T).where(*store.where(T, T.c.id == task["id"])).values(
                observed_input_digest=actual_digest))
            await context.bind_in_transaction(store, run_id, input_digest=actual_digest, policy_artifact_id=policy_id,
                previous_run_id=UUID(comparison["previous_run_id"]) if comparison["previous_run_id"] else None,
                comparison_result_id=rid)
        return claim

    async def execute(self, context, material):
        # load() only gates preparation. Freeze the latest Case once, in claim's
        # transaction; never substitute whatever membership exists on completion.
        claim = await self.prepare(context)
        gateway = self.gateway_factory(claim) if self.gateway_factory else None
        lake = self.lake_factory(claim) if self.lake_factory else None
        await BaselineExecutor(self.service, context.task["tenant_id"], gateway=gateway, lake=lake)(claim)
        async with self.service.transaction(context.task["tenant_id"], readonly=True) as store:
            run = await store.one(select(R).where(*store.where(R, R.c.id == claim.run_id)))
            if run["state"] == "completed":
                return Outcome("completed")
            return Outcome("unknown" if run["state"] in {"running", "unknown"} else "failed",
                run["stop_reason"] or "case_execution_failed", "case")


def executors(config, task_service):
    if set(config) != {"investigation_policy_file", "incident", "case"}:
        raise ValueError("invalid A/I/Case executor configuration")
    active_policy().require_execution_profiles()
    result = ai_executors({key: config[key] for key in ("investigation_policy_file", "incident")}, task_service)
    case = dict(config["case"])
    if "scan_batch_size" not in case:
        raise ValueError("explicit Case scan batch size required")
    scan_batch_size = case.pop("scan_batch_size")
    result["case_investigation"] = CaseTaskExecutor(BaselineService(task_service.sessions),
        CaseExecutionPolicy.from_config(case), task_service, scan_batch_size, CaseAllocationPolicy.load())
    return result
