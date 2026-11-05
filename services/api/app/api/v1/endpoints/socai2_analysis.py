"""Opt-in read-only A/I analysis, no generation on GET."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.deps import CurrentUser, require_permission
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.socai2.baseline_store import StoreError
from app.socai2.stage_read_contracts import StageEntry, StagePage
from app.socai2.stage_reader import StageReadService


def get_service():
    if not settings.SOCAI2_ANALYSIS_READ_ENABLED:
        raise HTTPException(503, "socai2_analysis_read_not_enabled")
    return StageReadService(AsyncSessionLocal)


User = Annotated[CurrentUser, Depends(require_permission("alerts:read"))]
Service = Annotated[StageReadService, Depends(get_service)]
Limit = Annotated[int, Query(ge=1, le=50)]
router = APIRouter(prefix="/socai2", tags=["socai2-analysis"])


async def invoke(call):
    try:
        return await call
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None


@router.get("/alerts/{alert_id}/analysis", response_model=StagePage)
async def alert_analysis(alert_id: UUID, user: User, service: Service, limit: Limit = 20, before_run_id: UUID | None = None):
    return await invoke(service.read_page(user.tenant_id, "alert_basic", alert_id, limit=limit, before_run_id=before_run_id))


@router.get("/incidents/{incident_id}/analysis", response_model=StagePage)
async def incident_analysis(incident_id: UUID, user: User, service: Service, limit: Limit = 20, before_run_id: UUID | None = None):
    return await invoke(service.read_page(user.tenant_id, "incident_diagnosis", incident_id, limit=limit, before_run_id=before_run_id))


@router.get("/alerts/{alert_id}/analysis/runs/{run_id}", response_model=StageEntry)
async def alert_run(alert_id: UUID, run_id: UUID, user: User, service: Service):
    return await invoke(service.read_entry(user.tenant_id, "alert_basic", alert_id, run_id))


@router.get("/incidents/{incident_id}/analysis/runs/{run_id}", response_model=StageEntry)
async def incident_run(incident_id: UUID, run_id: UUID, user: User, service: Service):
    return await invoke(service.read_entry(user.tenant_id, "incident_diagnosis", incident_id, run_id))
