"""Opt-in read-only A/I analysis, no generation on GET."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from investigation_http.contracts import StageEntry, StagePage
from investigation_http.dependencies import CurrentUser, require_permission
from investigation_http.dependencies import analysis_service as get_service
from investigation_http.errors import invoke
from investigation_http.ports import AnalysisReads

User = Annotated[CurrentUser, Depends(require_permission("alerts:read"))]
Service = Annotated[AnalysisReads, Depends(get_service)]
Limit = Annotated[int, Query(ge=1, le=50)]
router = APIRouter(prefix="/socai2", tags=["socai2-analysis"])


@router.get("/alerts/{alert_id}/analysis", response_model=StagePage)
async def alert_analysis(
    alert_id: UUID,
    user: User,
    service: Service,
    limit: Limit = 20,
    before_run_id: UUID | None = None,
):
    return await invoke(
        service.read_page(
            user.tenant_id,
            "alert_basic",
            alert_id,
            limit=limit,
            before_run_id=before_run_id,
        )
    )


@router.get("/incidents/{incident_id}/analysis", response_model=StagePage)
async def incident_analysis(
    incident_id: UUID,
    user: User,
    service: Service,
    limit: Limit = 20,
    before_run_id: UUID | None = None,
):
    return await invoke(
        service.read_page(
            user.tenant_id,
            "incident_diagnosis",
            incident_id,
            limit=limit,
            before_run_id=before_run_id,
        )
    )


@router.get("/alerts/{alert_id}/analysis/runs/{run_id}", response_model=StageEntry)
async def alert_run(alert_id: UUID, run_id: UUID, user: User, service: Service):
    return await invoke(
        service.read_entry(user.tenant_id, "alert_basic", alert_id, run_id)
    )


@router.get(
    "/incidents/{incident_id}/analysis/runs/{run_id}", response_model=StageEntry
)
async def incident_run(incident_id: UUID, run_id: UUID, user: User, service: Service):
    return await invoke(
        service.read_entry(user.tenant_id, "incident_diagnosis", incident_id, run_id)
    )
