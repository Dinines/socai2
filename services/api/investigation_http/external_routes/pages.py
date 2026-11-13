"""Read-only new-table page fields. Search/export/manage flows are separate."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime

from investigation_http.contracts import (
    AlertListQuery,
    AlertSort,
    AlertStatus,
    AssignmentState,
    ContentView,
    IncidentListQuery,
    IncidentSort,
    RecordPage,
    Section,
    Severity,
    SortOrder,
    Subject,
    SubjectPage,
    SubjectView,
    TraceView,
    WorkStatus,
)
from investigation_http.dependencies import CurrentUser, require_permission
from investigation_http.dependencies import page_service as get_service
from investigation_http.errors import invoke, query_input
from investigation_http.external_routes.subject_management import (
    router as management_router,
)
from investigation_http.ports import PageReads

User = Annotated[CurrentUser, Depends(require_permission("alerts:read"))]
Service = Annotated[PageReads, Depends(get_service)]
router = APIRouter(prefix="/socai2", tags=["socai2-page-fields"])
router.include_router(management_router)


@router.get("/alerts", response_model=SubjectPage)
async def alerts(
    user: User,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    before_id: UUID | None = None,
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    severity: Severity | None = None,
    handling_status: AlertStatus | None = None,
    owner_id: UUID | None = None,
    assignment_state: AssignmentState | None = None,
    time_from: AwareDatetime | None = None,
    time_to: AwareDatetime | None = None,
    sort_by: AlertSort | None = None,
    sort_order: SortOrder | None = None,
):
    query = query_input(AlertListQuery, limit=limit, before_id=before_id, cursor=cursor,
        q=q, severity=severity, handling_status=handling_status, owner_id=owner_id,
        assignment_state=assignment_state, time_from=time_from, time_to=time_to,
        sort_by=sort_by, sort_order=sort_order)
    return await invoke(
        service.read(
            user.tenant_id, "alerts", None, "listing", query=query
        )
    )


@router.get("/incidents", response_model=SubjectPage)
async def incidents(
    user: User,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    before_id: UUID | None = None,
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    severity: Severity | None = None,
    handling_status: WorkStatus | None = None,
    owner_id: UUID | None = None,
    assignment_state: AssignmentState | None = None,
    time_from: AwareDatetime | None = None,
    time_to: AwareDatetime | None = None,
    sort_by: IncidentSort | None = None,
    sort_order: SortOrder | None = None,
):
    query = query_input(IncidentListQuery, limit=limit, before_id=before_id, cursor=cursor,
        q=q, severity=severity, handling_status=handling_status, owner_id=owner_id,
        assignment_state=assignment_state, time_from=time_from, time_to=time_to,
        sort_by=sort_by, sort_order=sort_order)
    return await invoke(
        service.read(
            user.tenant_id,
            "incidents",
            None,
            "listing",
            query=query,
        )
    )


@router.get("/alerts/{alert_id}", response_model=SubjectView)
async def alert(alert_id: UUID, user: User, service: Service):
    return await invoke(service.read(user.tenant_id, "alerts", alert_id, "view"))


@router.get("/incidents/{incident_id}", response_model=SubjectView)
async def incident(incident_id: UUID, user: User, service: Service):
    return await invoke(service.read(user.tenant_id, "incidents", incident_id, "view"))


@router.get("/{subject}/{identity}/records/{section}", response_model=RecordPage)
async def records(
    subject: Subject,
    identity: UUID,
    section: Section,
    user: User,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    if section == "cases":
        await require_permission("cases:read")(user)
    return await invoke(
        service.read(
            user.tenant_id,
            subject,
            identity,
            "records",
            section=section,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/alerts/{alert_id}/materials/{material_id}", response_model=ContentView)
async def material(alert_id: UUID, material_id: UUID, user: User, service: Service):
    return await invoke(
        service.read(
            user.tenant_id,
            "alerts",
            alert_id,
            "material_content",
            material_id=material_id,
        )
    )


@router.get(
    "/{subject}/{identity}/analysis/runs/{run_id}/trace", response_model=TraceView
)
async def trace(
    subject: Subject, identity: UUID, run_id: UUID, user: User, service: Service
):
    return await invoke(
        service.read(user.tenant_id, subject, identity, "trace", run_id=run_id)
    )


@router.get(
    "/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}",
    response_model=ContentView,
)
async def artifact(
    subject: Subject,
    identity: UUID,
    run_id: UUID,
    artifact_id: UUID,
    user: User,
    service: Service,
):
    return await invoke(
        service.read(
            user.tenant_id,
            subject,
            identity,
            "artifact_content",
            run_id=run_id,
            artifact_id=artifact_id,
        )
    )


@router.get("/alerts/{identity}/artifacts/{artifact_id}", response_model=ContentView)
async def alert_source_artifact(
    identity: UUID, artifact_id: UUID, user: User, service: Service
):
    return await invoke(
        service.read(
            user.tenant_id,
            "alerts",
            identity,
            "artifact_content",
            run_id=None,
            artifact_id=artifact_id,
        )
    )


@router.get("/incidents/{identity}/artifacts/{artifact_id}", response_model=ContentView)
async def incident_source_artifact(
    identity: UUID, artifact_id: UUID, user: User, service: Service
):
    return await invoke(
        service.read(
            user.tenant_id,
            "incidents",
            identity,
            "artifact_content",
            run_id=None,
            artifact_id=artifact_id,
        )
    )
