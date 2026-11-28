"""External business API only; internal tools/callbacks have separate apps."""

import os

from fastapi import FastAPI

from investigation_http.adapters import runtime
from investigation_http.adapters.identity import configure_trusted_access
from investigation_http.adapters.runtime import configured_database_name
from investigation_http.external_routes import (
    alert_hosts,
    alert_review,
    analysis,
    analysis_submissions,
    analysis_tasks,
    attachments,
    case_ai,
    case_investigations,
    cases,
    comments,
    exploration,
    exploration_state,
    exports,
    grouping,
    lake,
    pages,
    run_directory,
    run_records,
    story,
    tasks,
)

app = FastAPI(
    title="socai2 Independent Investigation API",
    version=os.environ.get("SOCAI2_HTTP_RELEASE", "2.0.0"),
    lifespan=runtime.lifespan,
)
runtime.configure_http(app)
for router in (
    exports.router,
    grouping.router,
    cases.router,
    case_investigations.router,
    comments.router,
    attachments.router,
    case_ai.router,
    analysis.router,
    analysis_tasks.router,
    pages.router,
    analysis_submissions.incident_router,
    analysis_submissions.case_router,
    tasks.router,
    story.router,
    exploration.router,
    exploration_state.router,
    alert_review.router,
    alert_hosts.router,
    run_records.router,
    run_directory.router,
    lake.router,
):
    app.include_router(router, prefix="/api/v1")

configure_trusted_access(app)

__all__ = ["app", "configured_database_name"]
