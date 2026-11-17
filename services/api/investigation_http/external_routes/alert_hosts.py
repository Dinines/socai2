"""External same-host recent alert query through a dedicated read-only port."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from investigation_http.contracts import AlertHostPage
from investigation_http.dependencies import (
    CurrentUser,
    alert_host_service,
    require_permission,
)
from investigation_http.errors import invoke
from investigation_http.ports import AlertHosts

router = APIRouter(prefix="/socai2/alerts", tags=["socai2-alert-hosts"])
ReadUser = Annotated[CurrentUser, Depends(require_permission("alerts:read"))]
Service = Annotated[AlertHosts, Depends(alert_host_service)]


@router.get("/{alert_id}/same-host-alerts", response_model=AlertHostPage)
async def recent(request: Request, alert_id: UUID, user: ReadUser, service: Service):
    if request.query_params:
        raise HTTPException(422, "alert_host_query_parameter_not_supported")
    return await invoke(service.read(user.tenant_id, alert_id))
