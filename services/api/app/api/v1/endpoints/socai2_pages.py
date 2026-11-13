"""Read-only new-table page fields. Search/export/manage flows are separate."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.deps import CurrentUser, require_permission
from app.api.v1.endpoints.socai2_subject_management import router as management_router
from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.socai2.baseline_store import StoreError
from app.socai2.page_contracts import (
    ContentView,
    RecordPage,
    Section,
    Subject,
    SubjectPage,
    SubjectView,
    TraceView,
)
from app.socai2.page_reader import PageReadService


def get_service():
    if not settings.SOCAI2_PAGE_READ_ENABLED:
        raise HTTPException(503, "socai2_page_read_not_enabled")
    return PageReadService(AsyncSessionLocal)


User = Annotated[CurrentUser, Depends(require_permission("alerts:read"))]
Service = Annotated[PageReadService, Depends(get_service)]
router = APIRouter(prefix="/socai2", tags=["socai2-page-fields"])
router.include_router(management_router)


async def invoke(call):
    try:
        return await call
    except StoreError as exc:
        raise HTTPException(exc.status, exc.code) from None


@router.get("/alerts", response_model=SubjectPage)
async def alerts(user: User, service: Service, limit: Annotated[int, Query(ge=1, le=50)] = 20, before_id: UUID | None = None):
    return await invoke(service.read(user.tenant_id, "alerts", None, "listing", limit=limit, before_id=before_id))


@router.get("/incidents", response_model=SubjectPage)
async def incidents(user: User, service: Service, limit: Annotated[int, Query(ge=1, le=50)] = 20, before_id: UUID | None = None):
    return await invoke(service.read(user.tenant_id, "incidents", None, "listing", limit=limit, before_id=before_id))


@router.get("/alerts/{alert_id}", response_model=SubjectView)
async def alert(alert_id: UUID, user: User, service: Service):
    return await invoke(service.read(user.tenant_id, "alerts", alert_id, "view"))


@router.get("/incidents/{incident_id}", response_model=SubjectView)
async def incident(incident_id: UUID, user: User, service: Service):
    return await invoke(service.read(user.tenant_id, "incidents", incident_id, "view"))


@router.get("/{subject}/{identity}/records/{section}", response_model=RecordPage)
async def records(subject: Subject, identity: UUID, section: Section, user: User, service: Service,
                  limit: Annotated[int, Query(ge=1, le=200)] = 50, offset: Annotated[int, Query(ge=0, le=100000)] = 0):
    if section == "cases":
        await require_permission("cases:read")(user)
    return await invoke(service.read(user.tenant_id, subject, identity, "records", section=section, limit=limit, offset=offset))


@router.get("/alerts/{alert_id}/materials/{material_id}", response_model=ContentView)
async def material(alert_id: UUID, material_id: UUID, user: User, service: Service):
    return await invoke(service.read(user.tenant_id, "alerts", alert_id, "material_content", material_id=material_id))


@router.get("/{subject}/{identity}/analysis/runs/{run_id}/trace", response_model=TraceView)
async def trace(subject: Subject, identity: UUID, run_id: UUID, user: User, service: Service):
    return await invoke(service.read(user.tenant_id, subject, identity, "trace", run_id=run_id))


@router.get("/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}", response_model=ContentView)
async def artifact(subject: Subject, identity: UUID, run_id: UUID, artifact_id: UUID, user: User, service: Service):
    return await invoke(service.read(user.tenant_id, subject, identity, "artifact_content", run_id=run_id, artifact_id=artifact_id))


@router.get("/alerts/{identity}/artifacts/{artifact_id}", response_model=ContentView)
async def alert_source_artifact(identity: UUID, artifact_id: UUID, user: User, service: Service):
    return await invoke(service.read(user.tenant_id, "alerts", identity, "artifact_content", run_id=None, artifact_id=artifact_id))


@router.get("/incidents/{identity}/artifacts/{artifact_id}", response_model=ContentView)
async def incident_source_artifact(identity: UUID, artifact_id: UUID, user: User, service: Service):
    return await invoke(service.read(user.tenant_id, "incidents", identity, "artifact_content", run_id=None, artifact_id=artifact_id))
