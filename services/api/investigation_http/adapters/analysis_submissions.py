"""Persist admission through the core; no Redis access or investigation calls."""
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.analysis_tasks import AnalysisTaskService
from app.socai2.baseline_store import StoreError
from sqlalchemy.exc import DBAPIError


class AnalysisSubmissionBackend:
    def __init__(self, sessions, *, policy=None):
        self.service = AnalysisTaskService(sessions, policy if policy is not None else AnalysisTaskPolicy.load())

    async def submit(self, tenant, subject_type, subject_id, request, *, actor_id):
        kinds = {"case": "case_investigation", "incident": "incident_diagnosis"}
        if subject_type not in kinds:
            raise StoreError("invalid_input", 422)
        try:
            receipt = await self.service.submit(tenant, kind=kinds[subject_type], subject_id=subject_id,
                intent=request.mode, source="user", operation_key=request.operation_key, submitted_by=actor_id)
        except StoreError as exc:
            code = {"operation_key_conflict": "operation_conflict", "subject_scope_empty": "empty_scope"}.get(exc.code, exc.code)
            raise StoreError(code, exc.status) from None
        except DBAPIError:
            # If commit was unconfirmed, callers replay the same operation key.
            raise StoreError("service_unavailable", 503) from None
        return {**receipt, "status_url": f"/api/v1/socai2/{receipt['subject_type']}s/"
                f"{receipt['subject_id']}/analysis-tasks/{receipt['task_id']}"}
