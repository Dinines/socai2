"""Explicit v2 result gateway app, separate from the legacy application."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.deps import CurrentUser, require_permission
from .query_api import create_app as create_query_app
from .result_gateway import ResultReadGateway


async def _explicit_bearer(request: Request) -> None:
    # The original auth dependency retains its local demo shortcut. This new
    # result GET always requires a credential before invoking that dependency.
    scheme, _, token = (request.headers.get("Authorization") or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401, "investigation_v2_result_bearer_required", headers={"WWW-Authenticate": "Bearer"})


async def _permitted_reader(_credential: Annotated[None, Depends(_explicit_bearer)],
                            user: Annotated[CurrentUser, Depends(require_permission("cases:read"))]) -> CurrentUser:
    user.require_permission("alerts:read")
    return user


router = APIRouter(prefix="/api/v2/investigation", tags=["investigation-v2-results"])


@router.get("/runs/{run_id}")
async def read_result(run_id: UUID, request: Request,
                       user: Annotated[CurrentUser, Depends(_permitted_reader)]):
    if request.query_params:
        raise HTTPException(400, "result_read_accepts_no_query_overrides")
    async for chunk in request.stream():
        if chunk:
            raise HTTPException(400, "result_read_accepts_no_body")
    return await request.app.state.result_gateway.read(tenant_id=user.tenant_id, actor_id=user.user_id, run_id=run_id)


def create_app(*, gateway=None):
    configured = ResultReadGateway.from_environment() if gateway is None else gateway
    app = create_query_app()
    app.title = "Investigation v2 query and result read"
    app.state.result_gateway = configured
    app.include_router(router)
    return app
