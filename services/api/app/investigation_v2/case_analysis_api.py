"""Explicit Case investigation routes for the separate v2 application."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.deps import CurrentUser, require_permission
from app.db.rls import TenantDBSession
from .case_analysis import CaseAnalysisRequest, read_analysis, start_analysis
from .query_api import create_app as create_query_app
from .result_api import _explicit_bearer

router = APIRouter(prefix="/api/v2/investigation/cases", tags=["case-investigation"])


@router.post("/{case_id}/investigate")
async def investigate(
    case_id: UUID, request: CaseAnalysisRequest, db: TenantDBSession,
    _credential: Annotated[None, Depends(_explicit_bearer)],
    user: Annotated[CurrentUser, Depends(require_permission("investigation:run"))],
):
    user.require_permission("cases:read")
    user.require_permission("alerts:read")
    return await start_analysis(db, user.tenant_id, user.user_id, case_id, request)


@router.get("/{case_id}/investigations/{run_id}")
async def read(
    case_id: UUID, run_id: UUID, db: TenantDBSession,
    _credential: Annotated[None, Depends(_explicit_bearer)],
    user: Annotated[CurrentUser, Depends(require_permission("cases:read"))],
):
    user.require_permission("alerts:read")
    return await read_analysis(db, user.tenant_id, case_id, run_id)


def create_app():
    app = create_query_app()
    app.include_router(router)
    app.title = "Case investigation analysis"
    return app
