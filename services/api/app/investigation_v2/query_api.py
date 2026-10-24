"""Explicit standalone v2 query app; never imported by the legacy app/router.

Start only in an isolated process/configuration, for example with uvicorn's
--factory app.investigation_v2.query_api:create_app. This exposes a typed read
only; Run scope/budget admission stays with the checked Agents caller.
"""
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.deps import CurrentUser, require_permission
from app.db import clickhouse, database
from .dispatch import dispatch

router = APIRouter(prefix="/api/v2/investigation", tags=["investigation-v2-query"])


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


@router.post("/query")
async def query(request: QueryRequest,
                user: Annotated[CurrentUser, Depends(require_permission("lake:query"))]) -> dict[str, Any]:
    result = await dispatch(request.tool, str(user.tenant_id), request.args)
    return result.as_dict()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # No schema initialization, broker, worker, legacy router or model startup.
    try:
        yield
    finally:
        await clickhouse.close_clickhouse()
        await database.engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Investigation v2 typed query", docs_url=None,
                  redoc_url=None, openapi_url=None, lifespan=_lifespan)
    app.include_router(router)
    return app
