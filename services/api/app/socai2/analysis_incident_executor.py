"""Actual I execution and bounded periodic material checks in the common dispatcher."""
import hashlib
import logging
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, update

from .analysis_alert_executor import AlertTaskExecutor
from .analysis_dispatch_types import Material, Outcome
from .analysis_task_store import A, S
from .baseline_store import StoreError, digest
from .incident_diagnosis_executor import IncidentDiagnosisExecutor
from .runtime_policy import active_policy, execution_policy
from .stage_results import F, R, StageResultService, source_input

LOG = logging.getLogger(__name__)
CAPACITY_ERRORS = {"model_context_capacity_exceeded", "model_token_budget_insufficient", "incident_member_directory_too_large"}


@dataclass(frozen=True)
class IncidentTaskPolicy:
    max_alerts_per_diagnosis: int
    scan_batch_size: int

    def __post_init__(self):
        if any(type(v) is not int or v < 1 for v in asdict(self).values()):
            raise ValueError("invalid incident execution configuration")


class IncidentTaskExecutor:
    def __init__(self, service, task_service, policy, *, gateway_factory=None):
        self.service, self.task_service, self.policy = service, task_service, policy
        self.gateway_factory = gateway_factory

    def capacity_profile(self):
        policy = active_policy()
        return {"max_alerts_per_diagnosis": self.policy.max_alerts_per_diagnosis,
                "max_total_tokens": policy.incident_diagnosis.max_total_tokens,
                "context_tokens": policy.model.context_tokens, "output_tokens": policy.model.output_tokens["I"],
                "tokenizer": dict(policy.model.tokenizer)}

    async def load_in_store(self, store, subject_id):
        execution_policy("incident_io")
        source = await source_input(store, "incident_diagnosis", subject_id, validated_triage=True,
            with_queries=True, with_citation_quality=True,
            incident_limit=self.policy.max_alerts_per_diagnosis)
        if not source or not source.get("members"):
            raise StoreError("stage_members_required", 422)
        source["capacity_profile"] = self.capacity_profile()
        state = await store.one(select(S).where(*store.where(S, S.c.subject_type == "incident", S.c.subject_id == subject_id)))
        changed = False
        if state and state["automatic_stop_reason"] == "capacity_exceeded" and state["stopped_task_id"]:
            old = await store.one(select(F.c.content_json).select_from(A.join(R, R.c.id == A.c.run_id)
                .join(F, F.c.id == R.c.input_artifact_id)).where(*store.where(A,
                    A.c.task_id == state["stopped_task_id"])).order_by(A.c.attempt_no.desc()).limit(1))
            changed = bool(old and old["content_json"].get("capacity_profile") != source["capacity_profile"])
        return Material(digest(source["change_view"]), source, changed)

    async def load(self, task):
        async with self.service.transaction(task["tenant_id"], readonly=True) as store:
            return await self.load_in_store(store, task["subject_id"])

    async def execute(self, context, material):
        task = context.task
        gateway = self.gateway_factory() if self.gateway_factory else None
        result = await IncidentDiagnosisExecutor(self.service, gateway=gateway).execute(
            task["tenant_id"], task["subject_id"], context.operation_key, requested_by=task["submitted_by"],
            dispatch_context=context, frozen_source=material.value)
        if result["state"] == "completed":
            return Outcome("completed")
        reason = result.get("stop_reason") or "incident_execution_failed"
        return Outcome("unknown" if result["state"] in {"running", "unknown"} else "failed",
            "capacity_exceeded" if reason in CAPACITY_ERRORS else reason, "incident")

    async def check_updates(self, tenant_id, now):
        """Single claimer, same transaction for check receipt and optional task."""
        async with self.task_service.transaction(tenant_id, readonly=True) as store:
            ids = list((await store.db.execute(select(S.c.subject_id).where(*store.where(S,
                S.c.subject_type == "incident", S.c.next_check_at <= now))
                .order_by(S.c.next_check_at, S.c.subject_id).limit(self.policy.scan_batch_size))).scalars())
        counts = {"checked": 0, "submitted": 0}
        for identity in ids:
            async with self.task_service.transaction(tenant_id) as store:
                await store.subject("incident", identity, lock=True)
                status = await store.automatic_status("incident", identity)
                if status["next_check_at"] is None or status["next_check_at"] > now:
                    continue
                await store.db.execute(update(S).where(*store.where(S, S.c.subject_type == "incident",
                    S.c.subject_id == identity)).values(next_check_at=now + timedelta(
                        seconds=self.task_service.policy.incident_check_interval_seconds)))
                counts["checked"] += 1
                if status["ineligible_reason"] in {"closed", "expired", "not_registered"}:
                    continue
                try:
                    material = await self.load_in_store(store, identity)
                except StoreError as exc:
                    if exc.code == "stage_members_required":
                        continue
                    raise
                state = await store.one(select(S).where(*store.where(S,
                    S.c.subject_type == "incident", S.c.subject_id == identity)))
                completed = await store.one(select(A.c.input_digest).where(*store.where(A,
                    A.c.id == state["last_completed_attempt_id"]))) if state["last_completed_attempt_id"] else None
                if completed and completed["input_digest"] == material.digest and not material.capacity_changed:
                    continue
                if (state["automatic_stop_reason"] and material.digest == state["stopped_input_digest"]
                        and not material.capacity_changed):
                    continue
                await store.accept(kind="incident_diagnosis", subject_id=identity,
                    intent="check", source="periodic", operation_key=uuid4(), observed_input_digest=material.digest)
                counts["submitted"] += 1
        LOG.info("incident_periodic_check", extra=counts)
        return counts


def executors(config, task_service):
    if set(config) != {"investigation_policy_file", "incident"}:
        raise ValueError("invalid A/I executor configuration")
    active_policy().require_execution_profiles("alert_io", "incident_io")
    path = Path(config["investigation_policy_file"])
    if not path.is_absolute() or hashlib.sha256(path.read_bytes()).hexdigest() != active_policy().sha256:
        raise ValueError("A/I executor policy differs from selected runtime policy")
    stage = StageResultService(task_service.sessions)
    return {"alert_triage": AlertTaskExecutor(stage),
            "incident_diagnosis": IncidentTaskExecutor(stage, task_service, IncidentTaskPolicy(**config["incident"]))}
