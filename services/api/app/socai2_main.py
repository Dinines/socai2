"""Independent new-schema API. No legacy workers, schedulers or auto-DDL."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.engine import make_url

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
from app.db.case_database import close_case_database, get_case_write_sessions
from app.db.database import engine


def configured_database_name():
    expected = os.environ.get("SOCAI2_SERVICE_DATABASE_NAME", "")
    try:
        reader = make_url(str(settings.DATABASE_URL))
        target = (reader.host, reader.port, reader.database)
        if not expected or reader.database != expected or not all(target):
            raise ValueError("explicit target required")
        if settings.SOCAI2_CASE_API_ENABLED or settings.SOCAI2_STAGE_EXECUTION_ENABLED:
            writer = make_url(settings.SOCAI2_CASE_DATABASE_URL.get_secret_value().strip())
            if (writer.host, writer.port, writer.database) != target:
                raise ValueError("writer target differs")
    except Exception:
        # URL parsing errors may contain credentials; only expose a stable code.
        raise RuntimeError("socai2_service_requires_matching_explicit_database_targets") from None
    if os.environ.get("AISOC_DEV_AUTH_BYPASS", "").lower() in {"true", "1", "yes"}:
        raise RuntimeError("socai2_service_does_not_allow_auth_bypass")
    return expected


@asynccontextmanager
async def lifespan(app):
    expected = configured_database_name()
    enforce_secure_defaults()
    try:
        async with engine.connect() as conn:
            actual = (await conn.execute(text("SELECT current_database()"))).scalar_one()
            if actual != expected:
                raise RuntimeError("socai2_service_database_mismatch")
            await conn.execute(text("SELECT source_namespace FROM socai2.cases LIMIT 0"))
        if settings.SOCAI2_CASE_API_ENABLED or settings.SOCAI2_STAGE_EXECUTION_ENABLED:
            async with get_case_write_sessions()() as session:
                actual = (await session.execute(text("SELECT current_database()"))).scalar_one()
                if actual != expected:
                    raise RuntimeError("socai2_service_write_database_mismatch")
        mark_ready()
        yield
    finally:
        mark_not_ready()
        await close_case_database()
        await engine.dispose()


app = FastAPI(title="socai2 Independent Investigation API",
              version=os.environ.get("SOCAI2_HTTP_RELEASE", "2.0.0"), lifespan=lifespan)
app.add_middleware(CORSMiddleware, **build_cors_kwargs(service_name="socai2-next-api"))
mark_ready, mark_not_ready = install_health_routes(app, service_name="socai2-next-api")
for router in (auth.router, socai2_cases.router, socai2_case_ai.router, socai2_analysis.router,
               socai2_pages.router, socai2_stage_execution.router, socai2_tasks.router):
    app.include_router(router, prefix="/api/v1")
