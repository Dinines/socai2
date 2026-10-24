"""Explicit internal read-only v2 app; never included in the legacy app.

The dedicated read token authenticates a trusted API gateway. External user
permissions belong to that gateway; tenant/actor are its verified assertions.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hmac
import os
import ssl
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Request

from .execution_state import ExecutionRejected
from .execution_store import ExecutionPersistenceError
from .result_reader import OwnedReconResultReader
from .scope import TenantPrincipal

TOKEN_ENV = "AISOC_INVESTIGATION_V2_READ_TOKEN"
DSN_ENV = "AISOC_INVESTIGATION_V2_PG_DSN"
CA_ENV = "AISOC_INVESTIGATION_V2_CA_FILE"


def checked_read_token(value) -> str:
    try:
        valid = isinstance(value, str) and 32 <= len(value.encode("ascii")) <= 256 and value == value.strip() and not any(ch.isspace() for ch in value)
    except UnicodeEncodeError:
        valid = False
    if not valid:
        raise ValueError("explicit strong investigation v2 read token required")
    return value


def _assert_gateway(authorization: str | None, token: str) -> None:
    scheme, _, actual = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(actual.encode("utf-8"), token.encode("utf-8")):
        raise HTTPException(401, "investigation_v2_read_credential_required", headers={"WWW-Authenticate": "Bearer"})


def _identity(value: str | None, name: str) -> UUID:
    try:
        identity = UUID(value or "")
        if identity.int == 0:
            raise ValueError()
        return identity
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, "valid_" + name + "_required") from None


def create_app(*, reader=None, read_token: str | None = None) -> FastAPI:
    """Explicit token; inject an owned reader or provide explicit new PG config."""
    configured_token = checked_read_token(os.getenv(TOKEN_ENV) if read_token is None else read_token)

    @asynccontextmanager
    async def lifespan(app):
        pool = None
        try:
            if reader is None:
                import asyncpg
                dsn = (os.getenv(DSN_ENV) or "").strip()
                if not dsn:
                    raise ValueError("explicit investigation v2 PG configuration required")
                tls = ssl.create_default_context(cafile=os.getenv(CA_ENV) or None)
                pool = await asyncpg.create_pool(dsn, ssl=tls, min_size=1, max_size=2, timeout=10, command_timeout=10)
                app.state.reader = OwnedReconResultReader(pool)
            yield
        finally:
            if pool is not None:
                app.state.reader = None
                try:
                    await asyncio.wait_for(pool.close(), timeout=5)
                except TimeoutError:
                    pool.terminate()

    app = FastAPI(title="Investigation v2 internal result read", docs_url=None,
                  redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.reader = reader
    app.state.read_token = configured_token

    @app.get("/internal/investigation-v2/runs/{run_id}")
    async def read_result(run_id: UUID, request: Request,
                          authorization: Annotated[str | None, Header()] = None,
                          tenant_header: Annotated[str | None, Header(alias="X-AiSOC-Tenant-ID")] = None,
                          actor_header: Annotated[str | None, Header(alias="X-AiSOC-Actor-ID")] = None):
        _assert_gateway(authorization, app.state.read_token)
        tenant, actor = _identity(tenant_header, "tenant"), _identity(actor_header, "actor")
        if request.query_params:
            raise HTTPException(400, "result_read_accepts_no_query_overrides")
        async for chunk in request.stream():
            if chunk:
                raise HTTPException(400, "result_read_accepts_no_body")
        if app.state.reader is None:
            raise HTTPException(503, "investigation_v2_reader_not_ready")
        principal = TenantPrincipal(frozenset({tenant}), "verified-api-reader:" + str(actor), True)
        try:
            result = await app.state.reader.read(current_principal=principal, tenant_id=tenant, run_id=run_id)
        except ExecutionRejected as exc:
            if str(exc) == "owned Run not found":
                raise HTTPException(404, "investigation_v2_result_not_found") from None
            raise HTTPException(409, "investigation_v2_result_integrity_or_version_unavailable") from None
        except ExecutionPersistenceError:
            raise HTTPException(503, "investigation_v2_result_read_unavailable") from None
        if not isinstance(result, dict) or (result.get("schema"), result.get("tenant_id"), result.get("run_id")) != ("owned_fixed_recon_result.v1", str(tenant), str(run_id)):
            raise HTTPException(502, "investigation_v2_reader_response_mismatch")
        return result

    return app
