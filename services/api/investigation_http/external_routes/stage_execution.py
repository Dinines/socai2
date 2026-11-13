"""Explicit A/I execution for the independent service; no baseline auto-start."""

from typing import Annotated
from uuid import UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException

from investigation_http.contracts import ExecuteStage, StageEntry, StoreError
from investigation_http.dependencies import CurrentUser, require_permission
from investigation_http.dependencies import execution_service as get_execution_service
from investigation_http.ports import StageExecution

User = Annotated[CurrentUser, Depends(require_permission("alerts:write"))]
Service = Annotated[StageExecution, Depends(get_execution_service)]
router = APIRouter(prefix="/socai2", tags=["socai2-stage-execution"])


async def execute(kind, identity, body, user, service):
    if user.workload_service:
        raise HTTPException(403, "stage_user_actor_required")
    rid = uuid5(user.tenant_id, "socai2.stage:" + str(body.operation_key))
    try:
        return await service.execute(
            user.tenant_id,
            kind,
            identity,
            body.operation_key,
            requested_by=user.user_id,
        )
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None
    except Exception:  # noqa: BLE001 -- never send provider/db exception text
        raise HTTPException(
            503, {"code": "stage_execution_unavailable_read_run", "run_id": str(rid)}
        ) from None


@router.post("/alerts/{alert_id}/analyze", response_model=StageEntry)
async def alert_analysis(
    alert_id: UUID, body: ExecuteStage, user: User, service: Service
):
    return await execute("alert_basic", alert_id, body, user, service)


@router.post("/incidents/{incident_id}/diagnose", response_model=StageEntry)
async def incident_diagnosis(
    incident_id: UUID, body: ExecuteStage, user: User, service: Service
):
    return await execute("incident_diagnosis", incident_id, body, user, service)
