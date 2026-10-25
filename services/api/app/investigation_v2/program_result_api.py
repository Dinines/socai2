"""Explicit compatible result app using the existing authentication contracts."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.deps import CurrentUser, require_permission
from .query_api import create_app as create_query_app
from .result_api import _explicit_bearer
from .program_result_gateway import CompatibleResultReadGateway
from .incident_api import router as incident_router
from .case_analysis_api import router as case_analysis_router


async def _permitted_reader(_credential: Annotated[None, Depends(_explicit_bearer)],
                            user: Annotated[CurrentUser, Depends(require_permission("cases:read"))]) -> CurrentUser:
    user.require_permission("alerts:read")
    return user


router = APIRouter(prefix="/api/v2/investigation", tags=["investigation-compatible-results"])


@router.get("/runs/{run_id}")
async def read_result(run_id: UUID, request: Request,
                      user: Annotated[CurrentUser, Depends(_permitted_reader)]):
    if not run_id.int:
        raise HTTPException(400, "result_read_requires_nonnil_run")
    if request.query_params:
        raise HTTPException(400, "result_read_accepts_no_query_overrides")
    async for chunk in request.stream():
        if chunk:
            raise HTTPException(400, "result_read_accepts_no_body")
    return await request.app.state.result_gateway.read(tenant_id=user.tenant_id, actor_id=user.user_id, run_id=run_id)


def create_app(*, gateway=None):
    configured = CompatibleResultReadGateway.from_environment() if gateway is None else gateway
    app = create_query_app()
    app.title = "Investigation compatible result read"
    app.state.result_gateway = configured
    app.include_router(router)
    app.include_router(incident_router)
    app.include_router(case_analysis_router)
    return app
