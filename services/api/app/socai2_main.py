"""Independent new-schema API. No legacy workers, schedulers or auto-DDL."""
import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app._health import install_health_routes
from app.api.v1.endpoints import (
    auth,
    socai2_analysis,
    socai2_case_ai,
    socai2_cases,
    socai2_pages,
    socai2_stage_execution,
    socai2_tasks,
)
from app.core.config import enforce_secure_defaults, settings
from app.core.cors import build_cors_kwargs
from app.db.database import engine


def isolated_database_name():
    expected = os.environ.get("SOCAI2_SERVICE_DATABASE_NAME", "")
    actual = urlsplit(str(settings.DATABASE_URL)).path.lstrip("/")
    if not expected or expected != actual or expected == "aisoc":
        raise RuntimeError("socai2_service_requires_explicit_independent_database")
    if os.environ.get("AISOC_DEV_AUTH_BYPASS", "").lower() in {"true", "1", "yes"}:
        raise RuntimeError("socai2_service_does_not_allow_auth_bypass")
    return expected


@asynccontextmanager
async def lifespan(app):
    expected = isolated_database_name()
    enforce_secure_defaults()
    async with engine.connect() as conn:
        actual = (await conn.execute(text("SELECT current_database()"))).scalar_one()
        if actual != expected:
            raise RuntimeError("socai2_service_database_mismatch")
        await conn.execute(text("SELECT source_namespace FROM socai2.cases LIMIT 0"))
    mark_ready()
    try:
        yield
    finally:
        mark_not_ready()
        await engine.dispose()


app = FastAPI(title="socai2 Independent Investigation API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, **build_cors_kwargs(service_name="socai2-next-api"))
mark_ready, mark_not_ready = install_health_routes(app, service_name="socai2-next-api")
for router in (auth.router, socai2_cases.router, socai2_case_ai.router, socai2_analysis.router,
               socai2_pages.router, socai2_stage_execution.router, socai2_tasks.router):
    app.include_router(router, prefix="/api/v1")
