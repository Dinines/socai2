"""
Neo4j driver singleton for AiSOC graph layer.
AiSOC — open-source AI Security Operations Center (MIT License)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from neo4j import READ_ACCESS, AsyncDriver, AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import ServiceUnavailable

from app.core.config import settings
from app.db.graph_migrations import pending_ids, run_migrations

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None


class IdentityGraphNotConfigured(RuntimeError):
    """The isolated identity-read connection has no usable controlled config."""


def _identity_read_config() -> dict[str, str]:
    """Read only the dedicated file; never fall back to the general driver."""
    try:
        name = os.environ.get("AISOC_IDENTITY_GRAPH_CONFIG_FILE", "").strip()
        if not name:
            raise ValueError
        path = Path(name)
        if not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError
        config = json.loads(path.read_text(encoding="utf-8"))
        fields = {"uri", "username", "password", "database"}
        if not isinstance(config, dict) or set(config) != fields:
            raise ValueError
        if any(not isinstance(config[key], str) or not config[key].strip() for key in fields):
            raise ValueError
        uri = urlsplit(config["uri"])
        if (uri.scheme not in {"bolt", "bolt+s", "bolt+ssc", "neo4j", "neo4j+s", "neo4j+ssc"}
                or not uri.hostname or uri.username is not None or uri.password is not None
                or uri.query or uri.fragment or uri.path not in {"", "/"}):
            raise ValueError
        # The deployed Community graph uses this explicit database. No
        # caller-controlled database or query is accepted by the HTTP route.
        if config["database"] != "neo4j":
            raise ValueError
        return config
    except (OSError, UnicodeError, ValueError, TypeError):
        raise IdentityGraphNotConfigured("Identity graph read configuration is unavailable") from None


@asynccontextmanager
async def get_identity_read_session() -> AsyncGenerator[AsyncSession, None]:
    """An isolated read session without schema/bootstrap or global enablement.

    A driver belongs to this request and always closes, including cancellation.
    READ_ACCESS constrains this session; it does not turn the existing shared
    Community credential into a database-enforced read-only role.
    """
    config = _identity_read_config()
    async with AsyncGraphDatabase.driver(
        config["uri"], auth=(config["username"], config["password"]),
        max_connection_pool_size=5, connection_acquisition_timeout=5,
        connection_timeout=5, max_transaction_retry_time=0,
    ) as driver:
        async with driver.session(database=config["database"], default_access_mode=READ_ACCESS) as session:
            yield session


async def init_neo4j() -> None:
    """Initialize the Neo4j async driver and verify connectivity."""
    global _driver
    if _driver is not None:
        return

    _driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        max_connection_pool_size=50,
        connection_acquisition_timeout=30,
    )

    # Verify connectivity with retries
    for attempt in range(5):
        try:
            await _driver.verify_connectivity()
            logger.info("Neo4j connection established uri=%s", settings.NEO4J_URI)

            # Create schema constraints and indexes
            await _create_schema()
            return
        except ServiceUnavailable:
            if attempt < 4:
                wait = 2**attempt
                logger.warning("Neo4j not ready, retrying attempt=%s wait=%s", attempt + 1, wait)
                await asyncio.sleep(wait)
            else:
                logger.error("Neo4j connection failed after retries")
                raise


async def close_neo4j() -> None:
    """Close the Neo4j driver."""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None
        logger.info("Neo4j connection closed")


def get_driver() -> AsyncDriver:
    """Return the singleton Neo4j driver. Raises if not initialized."""
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialized. Call init_neo4j() first.")
    return _driver


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a Neo4j session."""
    driver = get_driver()
    async with driver.session(database="neo4j") as session:
        yield session


async def _create_schema() -> None:
    """Apply any pending graph migrations.

    This used to be a fixed list of ``CREATE … IF NOT EXISTS`` statements with
    every failure swallowed at ``debug``, which meant a schema change could
    only ever land on a fresh install and a constraint that failed to create
    left the deployment running without a guarantee the code assumes. The
    statements now live in ``app.db.graph_migrations`` as numbered, recorded,
    forward-only migrations.

    Non-strict here on purpose: a migration failure must not take the API
    down, because the graph is an enrichment surface and the rest of the
    platform works without it. It is logged at ``error`` rather than
    ``debug``, and the pending list is readable for diagnostics.
    """
    async with get_session() as session:
        applied = await run_migrations(session, strict=False)
        pending = await pending_ids(session)

    if applied:
        logger.info("Neo4j graph migrations applied: %s", ", ".join(applied))
    if pending:
        logger.error(
            "Neo4j graph migrations still pending after startup: %s — graph-backed features may be degraded",
            ", ".join(pending),
        )
    else:
        logger.info("Neo4j schema up to date")
