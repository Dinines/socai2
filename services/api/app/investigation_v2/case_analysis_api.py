"""Explicit Case investigation routes for the separate v2 application."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response

from app.api.v1.deps import CurrentUser, require_permission
from app.db.rls import TenantDBSession
from .case_analysis import CaseAnalysisRequest, CaseAnalysisScope, read_analysis, start_analysis
from .case_history import list_analyses
from .case_views import list_steps, preview_analysis, read_step, saved_report
from .case_links_api import router as links_router
from .query_api import create_app as create_query_app
from .result_api import _explicit_bearer

router = APIRouter(prefix="/api/v2/investigation/cases", tags=["case-investigation"])


@router.post("/{case_id}/investigation-context")
async def preview(case_id: UUID, request: CaseAnalysisScope, db: TenantDBSession,
                  _credential: Annotated[None, Depends(_explicit_bearer)],
                  user: Annotated[CurrentUser, Depends(require_permission("cases:read"))]):
    user.require_permission("alerts:read")
    return await preview_analysis(db, user.tenant_id, case_id, request)


@router.get("/{case_id}/investigations")
async def history(case_id: UUID, db: TenantDBSession,
                  _credential: Annotated[None, Depends(_explicit_bearer)],
                  user: Annotated[CurrentUser, Depends(require_permission("cases:read"))],
                  limit: int = Query(default=20, ge=1, le=50), cursor: str | None = None):
    user.require_permission("alerts:read")
    return await list_analyses(db, user.tenant_id, case_id, limit=limit, cursor=cursor)


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


@router.get("/{case_id}/investigations/{run_id}/steps")
async def steps(case_id: UUID, run_id: UUID, db: TenantDBSession,
                _credential: Annotated[None, Depends(_explicit_bearer)],
                user: Annotated[CurrentUser, Depends(require_permission("cases:read"))],
                after_seq: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=50)):
    user.require_permission("alerts:read")
    return await list_steps(db, user.tenant_id, case_id, run_id, after_seq=after_seq, limit=limit)


@router.get("/{case_id}/investigations/{run_id}/steps/{seq}")
async def step(case_id: UUID, run_id: UUID, seq: Annotated[int, Path(ge=1)], db: TenantDBSession,
               _credential: Annotated[None, Depends(_explicit_bearer)],
               user: Annotated[CurrentUser, Depends(require_permission("cases:read"))]):
    user.require_permission("alerts:read")
    return await read_step(db, user.tenant_id, case_id, run_id, seq)


@router.get("/{case_id}/investigations/{run_id}/report")
async def report(case_id: UUID, run_id: UUID, db: TenantDBSession,
                 _credential: Annotated[None, Depends(_explicit_bearer)],
                 user: Annotated[CurrentUser, Depends(require_permission("cases:read"))]):
    user.require_permission("alerts:read")
    markdown = await saved_report(db, user.tenant_id, case_id, run_id)
    return Response(markdown, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="case-{case_id}-run-{run_id}.md"'})


def create_app():
    app = create_query_app()
    app.include_router(router)
    app.include_router(links_router)
    app.title = "Case investigation analysis"
    return app
