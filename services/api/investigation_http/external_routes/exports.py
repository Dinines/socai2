"""Dedicated CSV download routes, outside internal investigation HTTP."""
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import AwareDatetime

from investigation_http import csv_export
from investigation_http.contracts import (
    AlertListQuery,
    AlertSort,
    AlertStatus,
    AssignmentState,
    CaseMetric,
    CaseQueueQuery,
    CaseSort,
    Classification,
    IncidentListQuery,
    IncidentSort,
    Severity,
    SortOrder,
    WorkStatus,
)
from investigation_http.dependencies import (
    CurrentUser,
    export_service,
    require_permission,
)
from investigation_http.errors import invoke, query_input
from investigation_http.ports import ListExports

AlertUser = Annotated[CurrentUser, Depends(require_permission("alerts:read"))]
CaseUser = Annotated[CurrentUser, Depends(require_permission("cases:read"))]
Service = Annotated[ListExports, Depends(export_service)]
router = APIRouter(prefix="/socai2", tags=["socai2-list-export"])
RESPONSES = {
    200: {"description": "完整CSV，UTF-8 BOM；空结果也返回列头。", "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}},
        "headers": {"Content-Disposition": {"schema": {"type": "string"}}, "X-Export-Count": {"schema": {"type": "integer"}},
            "X-Export-Observed-At": {"schema": {"type": "string", "format": "date-time"}}, "X-Export-Schema": {"schema": {"type": "string"}}}},
    413: {"description": "export_row_limit_exceeded或export_size_limit_exceeded；不返回截断文件。"},
    503: {"description": "export_query_timeout或已有读取依赖不可用；未生成成功CSV。"},
}


@router.get("/alerts/export", response_class=Response, responses=RESPONSES)
async def export_alerts(
    request: Request,
    user: AlertUser,
    service: Service,
    columns: str | None = None,
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
    csv_export.validate_parameters(request, "alerts")
    fields = csv_export.columns_for("alerts", columns)
    query = query_input(AlertListQuery, q=q, severity=severity, handling_status=handling_status,
        owner_id=owner_id, assignment_state=assignment_state, time_from=time_from, time_to=time_to,
        sort_by=sort_by, sort_order=sort_order)
    result = await invoke(service.read(user.tenant_id, "alerts", query))
    return csv_export.response("alerts", fields, result)


@router.get("/incidents/export", response_class=Response, responses=RESPONSES)
async def export_incidents(
    request: Request,
    user: AlertUser,
    service: Service,
    columns: str | None = None,
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
    csv_export.validate_parameters(request, "incidents")
    fields = csv_export.columns_for("incidents", columns)
    query = query_input(IncidentListQuery, q=q, severity=severity, handling_status=handling_status,
        owner_id=owner_id, assignment_state=assignment_state, time_from=time_from, time_to=time_to,
        sort_by=sort_by, sort_order=sort_order)
    result = await invoke(service.read(user.tenant_id, "incidents", query))
    return csv_export.response("incidents", fields, result)


@router.get("/cases/export", response_class=Response, responses=RESPONSES)
async def export_cases(
    request: Request,
    user: CaseUser,
    service: Service,
    columns: str | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    severity: Severity | None = None,
    handling_status: WorkStatus | None = None,
    owner_id: UUID | None = None,
    assignment_state: AssignmentState | None = None,
    time_from: AwareDatetime | None = None,
    time_to: AwareDatetime | None = None,
    sort_by: CaseSort | None = None,
    sort_order: SortOrder | None = None,
    metric: CaseMetric | None = None,
    classification: Classification | Literal["not_set"] | None = None,
):
    csv_export.validate_parameters(request, "cases")
    fields = csv_export.columns_for("cases", columns)
    query = query_input(CaseQueueQuery, q=q, severity=severity, handling_status=handling_status,
        owner_id=owner_id, assignment_state=assignment_state, time_from=time_from, time_to=time_to,
        sort_by=sort_by, sort_order=sort_order, metric=metric, classification=classification)
    result = await invoke(service.read(user.tenant_id, "cases", query))
    return csv_export.response("cases", fields, result)
