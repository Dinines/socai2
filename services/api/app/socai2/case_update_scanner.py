"""Case periodic producer; one dispatcher owns checks, allocation stays in its use case."""
import logging
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import exists, select, update

from . import case_relations
from .analysis_task_store import A, S
from .baseline_context import capture
from .baseline_contracts import Start
from .baseline_store import CA, C, StoreError
from .case_allocation import IA, I, X
from .case_allocation_contracts import FollowIncident

LOG = logging.getLogger(__name__)


class AutomaticCaseActor:
    user_id = None
    name = "Case update service"

    def snapshot(self):
        return {"type": "service", "user_id": None, "name_snapshot": None,
                "service_name": "socai2.case-updates", "service_version": "v1"}


async def follow_current(executor, tenant_id, case_id, *, automatic):
    async with executor.service.transaction(tenant_id, readonly=True) as store:
        case = await store.case(case_id, lock=False)
        root = case["continuation_root_case_id"]
        chain = select(C.c.id).where(*store.where(C, C.c.continuation_root_case_id == root))
        owned = exists(select(CA.c.alert_id).where(*store.where(CA,
            CA.c.case_id.in_(chain), CA.c.alert_id == IA.c.alert_id)))
        excluded = exists(select(X.c.alert_id).where(*store.where(X,
            X.c.case_id.in_(chain), X.c.alert_id == IA.c.alert_id)))
        new_members = exists(select(IA.c.alert_id).where(*store.where(IA,
            IA.c.incident_id == I.c.id), ~owned, ~excluded))
        incidents = list((await store.db.execute(select(I.c.id).where(*store.where(I,
            I.c.active_case_id == case_id), new_members).order_by(I.c.id))).scalars())
        if automatic and incidents:
            context = await capture(store.db, tenant_id, case_id,
                Start(expected_scope_revision=case["scope_revision"], operation_key=uuid4()))
            # Gate automatic allocation too: a capacity continuation creates an
            # initial task. Check I's actual scope, independently of its overlap
            # with the old Case, so a full Case can hand over to its successor.
            incidents = [iid for iid in incidents if (item := context.incidents.get(str(iid)))
                and item.linked_from_case and item.analysis_material]
    receipts = []
    for iid in incidents:
        async with executor.service.transaction(tenant_id) as store:
            receipt = await case_relations.follow(store, case_id, iid,
                FollowIncident(operation_key=uuid4(), incident_id=iid), AutomaticCaseActor(),
                executor.allocation_policy, executor.task_service.policy)
            if receipt is not None:
                receipts.append(receipt)
    return receipts


async def check_updates(executor, tenant_id, now):
    tasks = executor.task_service
    async with tasks.transaction(tenant_id, readonly=True) as store:
        ids = list((await store.db.execute(select(S.c.subject_id).where(*store.where(S,
            S.c.subject_type == "case", S.c.next_check_at <= now))
            .order_by(S.c.next_check_at, S.c.subject_id).limit(executor.scan_batch_size))).scalars())
    counts = {"checked": 0, "submitted": 0, "allocations": 0}
    for cid in ids:
        async with tasks.transaction(tenant_id) as store:
            await store.subject("case", cid, lock=True)
            status = await store.automatic_status("case", cid)
            if status["next_check_at"] is None or status["next_check_at"] > now:
                continue
            await store.db.execute(update(S).where(*store.where(S, S.c.subject_type == "case", S.c.subject_id == cid))
                .values(next_check_at=now + timedelta(seconds=tasks.policy.case_check_interval_seconds)))
            counts["checked"] += 1
            if status["ineligible_reason"] in {"closed", "expired", "not_registered"}:
                continue
        try:
            counts["allocations"] += len(await follow_current(executor, tenant_id, cid, automatic=True))
            async with tasks.transaction(tenant_id) as store:
                await store.subject("case", cid, lock=True)
                status = await store.automatic_status("case", cid)
                if status["ineligible_reason"] in {"closed", "expired", "not_registered"}:
                    continue
                material = await executor.load_in_store(store, cid, automatic=True)
                state = await store.one(select(S).where(*store.where(S,
                    S.c.subject_type == "case", S.c.subject_id == cid)))
                completed = await store.one(select(A.c.input_digest).where(*store.where(A,
                    A.c.id == state["last_completed_attempt_id"]))) if state["last_completed_attempt_id"] else None
                if completed and (completed["input_digest"] == material.digest
                        or material.unchanged_from_attempt_id == state["last_completed_attempt_id"]) and not material.capacity_changed:
                    continue
                if state["automatic_stop_reason"] and not material.capacity_changed and (
                        state["stopped_input_digest"] is None
                        or state["stopped_input_digest"] == material.digest
                        or material.unchanged_from_stopped_task_id == state["stopped_task_id"]):
                    continue
                await store.accept(kind="case_investigation", subject_id=cid, intent="check", source="periodic",
                    operation_key=uuid4(), observed_input_digest=material.digest)
                counts["submitted"] += 1
        except StoreError as exc:
            # One Case without usable membership must not prevent other checks.
            LOG.warning("case_periodic_check_unavailable", extra={"case_id": str(cid), "code": exc.code})
    return counts
