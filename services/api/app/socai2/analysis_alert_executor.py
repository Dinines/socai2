"""The real A flow behind the common queue; no caller-managed Run or Redis access."""
import hashlib
from pathlib import Path

from .alert_basic_executor import AlertBasicExecutor
from .analysis_dispatch_types import Material, Outcome
from .baseline_store import StoreError, digest
from .runtime_policy import active_policy
from .stage_results import StageResultService, source_input


class AlertTaskExecutor:
    def __init__(self, service, *, gateway_factory=None, query=None):
        self.service, self.gateway_factory, self.query = service, gateway_factory, query

    async def load(self, task):
        async with self.service.transaction(task["tenant_id"], readonly=True) as store:
            source = await source_input(store, "alert_basic", task["subject_id"])
        if not source or not source.get("members"):
            raise StoreError("stage_members_required", 422)
        return Material(digest(source), source)

    async def execute(self, context, material):
        task = context.task
        gateway = self.gateway_factory() if self.gateway_factory else None
        result = await AlertBasicExecutor(self.service, gateway=gateway, query=self.query).execute(
            task["tenant_id"], task["subject_id"], context.operation_key, requested_by=task["submitted_by"],
            dispatch_context=context, frozen_source=material.value)
        if result["state"] == "completed":
            return Outcome("completed")
        return Outcome("unknown" if result["state"] in {"running", "unknown"} else "failed",
            result.get("stop_reason") or "alert_execution_failed", "alert")


def executors(config, task_service):
    if set(config) != {"investigation_policy_file"}:
        raise ValueError("invalid alert executor configuration")
    active_policy().require_execution_profiles("alert_io")
    path = Path(config["investigation_policy_file"])
    if not path.is_absolute() or hashlib.sha256(path.read_bytes()).hexdigest() != active_policy().sha256:
        raise ValueError("alert executor policy differs from selected runtime policy")
    return {"alert_triage": AlertTaskExecutor(StageResultService(task_service.sessions))}
