"""External business API only; internal tools/callbacks have separate apps."""

import os

from fastapi import FastAPI

from investigation_http.adapters import runtime
from investigation_http.adapters.identity import login_router
from investigation_http.adapters.runtime import configured_database_name
from investigation_http.external_routes import (
    analysis,
    case_ai,
    cases,
    exports,
    grouping,
    pages,
    stage_execution,
    tasks,
)

app = FastAPI(
    title="socai2 Independent Investigation API",
    version=os.environ.get("SOCAI2_HTTP_RELEASE", "2.0.0"),
    lifespan=runtime.lifespan,
)
runtime.configure_http(app)
for router in (
    login_router,
    exports.router,
    grouping.router,
    cases.router,
    case_ai.router,
    analysis.router,
    pages.router,
    stage_execution.router,
    tasks.router,
):
    app.include_router(router, prefix="/api/v1")

__all__ = ["app", "configured_database_name"]
