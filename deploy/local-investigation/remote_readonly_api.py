"""Authenticated local read service; no production users, writes or workers."""

import hmac
import os
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from remote_profile import load_profile
from sqlalchemy import text

profile = load_profile(os.environ["SOCAI2_REMOTE_PROFILE"])

from app._health import install_health_routes
from app.api.v1.deps import CurrentUser, get_current_user
from app.api.v1.endpoints import (
    socai2_analysis,
    socai2_cases,
    socai2_pages,
    socai2_tasks,
)
from app.core.config import enforce_secure_defaults, settings
from app.db.database import AsyncSessionLocal, engine
from app.socai2.page_reader import PageReadService
from app.socai2.read_sources import ReadSources


async def service_principal(request: Request):
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token.encode(), profile.secrets["access_token"].encode()):
        raise HTTPException(401, "local_read_service_authentication_required", headers={"WWW-Authenticate": "Bearer"})
    api = profile.config["api"]
    return CurrentUser(
        user_id=UUID(api["service_id"]), tenant_id=UUID(api["tenant_id"]), role=api["service_role"],
        email=api["service_email"], scopes=list(api["permissions"]),
        resolved_permissions=frozenset(api["permissions"]), workload_service=profile.config["name"],
    )


@asynccontextmanager
async def lifespan(application):
    enforce_secure_defaults()
    if str(settings.DATABASE_URL) != profile.database_url():
        raise RuntimeError("readonly_profile_database_url_mismatch")
    expected = profile.config["database"]
    try:
        async with engine.connect() as conn:
            row = (await conn.execute(text("""
                SELECT current_database() AS database, current_user AS role,
                    current_setting('transaction_read_only') AS read_only,
                    (SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) AS tls,
                    (SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user) AS privileged
            """))).mappings().one()
            if (row["database"], row["role"], row["read_only"], row["tls"], row["privileged"]) != (
                expected["name"], expected["user"], "on", True, False,
            ):
                raise RuntimeError("readonly_profile_database_identity_or_safety_mismatch")
            layout = (await conn.execute(text("""
                SELECT count(DISTINCT table_name),count(*)
                FROM information_schema.columns WHERE table_schema='socai2'
            """))).one()
            if tuple(layout) != (expected["expected_tables"], expected["expected_columns"]):
                raise RuntimeError("readonly_profile_schema_version_mismatch")
            unsafe = (await conn.execute(text("""
                SELECT count(*) FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid
                WHERE n.nspname='socai2' AND c.relkind='r' AND (
                    NOT c.relrowsecurity OR NOT c.relforcerowsecurity OR
                    has_table_privilege(current_user,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE') OR
                    has_any_column_privilege(current_user,c.oid,'INSERT,UPDATE'))
            """))).scalar_one()
            if unsafe:
                raise RuntimeError("readonly_profile_requires_read_only_role_and_forced_rls")
            await conn.execute(text("SELECT classification,due_at,current_evidence_artifact_id FROM socai2.cases LIMIT 0"))
            lookup_dependencies = await ReadSources.from_config(profile.config["read_sources"]).check(conn)
            functions = (await conn.execute(text("""SELECT p.proname,
                has_function_privilege(current_user,p.oid,'EXECUTE') AS executable
                FROM pg_proc p WHERE p.oid IN (
                    to_regprocedure('socai2.baseline_input_freshness(uuid,uuid)'),
                    to_regprocedure('socai2.task_feedback_signature(jsonb)'))"""))).mappings().all()
            if len(functions) != 2 or not all(r["executable"] for r in functions):
                raise RuntimeError("readonly_profile_case_function_dependency_unavailable")
            if not all(r["ready"] for r in lookup_dependencies):
                raise RuntimeError("readonly_profile_lookup_dependency_unavailable")
            application.state.database = dict(row)
        mark_ready()
        yield
    finally:
        mark_not_ready()
        await engine.dispose()


app = FastAPI(title="socai2 Local Read Service", lifespan=lifespan)
mark_ready, mark_not_ready = install_health_routes(app, service_name=profile.config["name"])


@app.middleware("http")
async def reject_mutations(request, call_next):
    if request.method not in {"GET", "HEAD"}:
        return JSONResponse({"detail": "local_read_service_is_read_only"}, status_code=405, headers={"Allow": "GET, HEAD"})
    return await call_next(request)


# This entry point authenticates an explicitly configured local service, not
# a production user. Only read routes are mounted; the production JWT/API-key
# resolver (and its last_used_at UPDATE) is never called by this application.
app.dependency_overrides[get_current_user] = service_principal


def page_read_service():
    if not settings.SOCAI2_PAGE_READ_ENABLED:
        raise HTTPException(503, "socai2_page_read_not_enabled")
    return PageReadService(AsyncSessionLocal, read_sources=profile.config["read_sources"])


app.dependency_overrides[socai2_pages.get_service] = page_read_service
for source in (socai2_cases.router, socai2_pages.router, socai2_analysis.router, socai2_tasks.router):
    reads = APIRouter()
    reads.routes.extend(route for route in source.routes if getattr(route, "methods", set()) == {"GET"})
    app.include_router(reads, prefix="/api/v1")
