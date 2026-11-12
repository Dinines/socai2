"""Explicit A/I execution for the independent service; no baseline auto-start."""
from typing import Annotated
from uuid import UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import CurrentUser, require_permission
from app.core.config import settings
from app.db.case_database import get_case_write_sessions
from app.socai2.baseline_contracts import Contract
from app.socai2.baseline_store import StoreError
from app.socai2.stage_read_contracts import StageEntry
from app.socai2.stage_reader import StageReadService
from app.socai2.stage_results import StageResultService


class ExecuteStage(Contract):
    operation_key: UUID


def get_execution_service():
    if not settings.SOCAI2_STAGE_EXECUTION_ENABLED:
        raise HTTPException(503, "socai2_stage_execution_not_enabled")
    try:
        return StageResultService(get_case_write_sessions())
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None


User = Annotated[CurrentUser, Depends(require_permission("alerts:write"))]
Service = Annotated[StageResultService, Depends(get_execution_service)]
router = APIRouter(prefix="/socai2", tags=["socai2-stage-execution"])


async def execute(kind, identity, body, user, service):
    if user.workload_service:
        raise HTTPException(403, "stage_user_actor_required")
    rid = uuid5(user.tenant_id, "socai2.stage:"+str(body.operation_key))
    try:
        action = service.execute_alert if kind == "alert_basic" else service.execute_incident
        await action(user.tenant_id, identity, body.operation_key, requested_by=user.user_id)
        return await StageReadService(service.sessions).read_entry(user.tenant_id, kind, identity, rid)
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None
    except Exception:  # noqa: BLE001 -- never send provider/db exception text
        raise HTTPException(503, {"code": "stage_execution_unavailable_read_run", "run_id": str(rid)}) from None


@router.post("/alerts/{alert_id}/analyze", response_model=StageEntry)
async def alert_analysis(alert_id: UUID, body: ExecuteStage, user: User, service: Service):
    return await execute("alert_basic", alert_id, body, user, service)


@router.post("/incidents/{incident_id}/diagnose", response_model=StageEntry)
async def incident_diagnosis(incident_id: UUID, body: ExecuteStage, user: User, service: Service):
    return await execute("incident_diagnosis", incident_id, body, user, service)
