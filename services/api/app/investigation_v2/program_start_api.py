"""Explicit user-authorized manual start app, separate from legacy routes."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.deps import CurrentUser, require_permission
from .result_api import _explicit_bearer
from .program_result_api import create_app as create_result_app
from .program_start_gateway import MAX_BODY_BYTES, ProgramStartGateway, normalized_start_body


async def _permitted_starter(_credential: Annotated[None, Depends(_explicit_bearer)],
                             user: Annotated[CurrentUser, Depends(require_permission("investigation:run"))]) -> CurrentUser:
    user.require_permission("alerts:read")
    return user


async def _invoke(alert_id, request, user, read_only):
    try:
        alert = UUID(alert_id)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, "valid_alert_path_required") from None
    if not alert.int: raise HTTPException(400, "nonnil_alert_path_required")
    if request.query_params: raise HTTPException(400, "start_accepts_no_query_overrides")
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, "start_body_exceeds_limit")
        raw.extend(chunk)
    try:
        body = normalized_start_body(bytes(raw))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise HTTPException(422, "valid_strict_start_body_required") from None
    return await request.app.state.start_gateway.invoke(tenant_id=user.tenant_id, actor_id=user.user_id,
                                                       alert_id=alert, body=body, read_only=read_only)


router = APIRouter(prefix="/api/v2/investigation", tags=["investigation-program-start"])


@router.post("/alerts/{alert_id}/start")
async def start(alert_id: str, request: Request, user: Annotated[CurrentUser, Depends(_permitted_starter)]):
    return await _invoke(alert_id, request, user, False)


@router.post("/alerts/{alert_id}/operation-read")
async def read_operation(alert_id: str, request: Request, user: Annotated[CurrentUser, Depends(_permitted_starter)]):
    return await _invoke(alert_id, request, user, True)


def create_app(*, start_gateway=None, result_gateway=None):
    configured = ProgramStartGateway.from_environment() if start_gateway is None else start_gateway
    app = create_result_app(gateway=result_gateway)
    app.title = "Investigation compatible query, result and manual start"
    app.state.start_gateway = configured
    app.include_router(router)
    return app
