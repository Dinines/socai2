"""A managed code deployment must not run graph/lake DDL at startup."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.db import clickhouse, neo4j


@pytest.mark.asyncio
async def test_disabled_graph_migrations_keep_connection_available():
    driver = SimpleNamespace(verify_connectivity=AsyncMock())
    with patch.object(neo4j, "_driver", None), patch.object(neo4j.settings, "AISOC_STARTUP_SCHEMA_MIGRATIONS", False), \
            patch.object(neo4j.AsyncGraphDatabase, "driver", return_value=driver), \
            patch.object(neo4j, "_create_schema", new_callable=AsyncMock) as ddl:
        await neo4j.init_neo4j()
        driver.verify_connectivity.assert_awaited_once()
        ddl.assert_not_awaited()
        assert neo4j.get_driver() is driver


@pytest.mark.asyncio
async def test_enabled_graph_migrations_preserve_existing_behavior():
    driver = SimpleNamespace(verify_connectivity=AsyncMock())
    with patch.object(neo4j, "_driver", None), patch.object(neo4j.settings, "AISOC_STARTUP_SCHEMA_MIGRATIONS", True), \
            patch.object(neo4j.AsyncGraphDatabase, "driver", return_value=driver), \
            patch.object(neo4j, "_create_schema", new_callable=AsyncMock) as ddl:
        await neo4j.init_neo4j()
        ddl.assert_awaited_once()


@pytest.mark.asyncio
async def test_disabled_lake_startup_does_not_call_migration_runner():
    with patch.object(clickhouse.settings, "AISOC_STARTUP_SCHEMA_MIGRATIONS", False), \
            patch("app.db.lake_migrations.run_migrations", new_callable=AsyncMock) as ddl:
        await clickhouse.init_lake_schema()
        ddl.assert_not_awaited()
