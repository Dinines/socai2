"""B3 durable-memory empty/unavailable semantics using the actual module."""
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import json
from unittest.mock import AsyncMock
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.memory import institutional as memory
from app.context.bundle import ContextBundleBuilder


@pytest.fixture(autouse=True)
def clean_memory(monkeypatch):
    monkeypatch.setattr(memory, "_FALLBACK", {"tenant-a:cached": {"verdict": "needs_review"}})
    monkeypatch.setattr(memory, "_POOL", None)
    monkeypatch.delenv("DATABASE_URL", raising=False)


def pool(monkeypatch, *, rows=(), error=None):
    fetch = AsyncMock(return_value=rows, side_effect=error)
    class Connection:
        pass
    connection = Connection()
    connection.fetch = fetch
    class Pool:
        @asynccontextmanager
        async def acquire(self):
            yield connection
    monkeypatch.setattr(memory, "_get_pool", AsyncMock(return_value=Pool()))
    return fetch


@pytest.mark.asyncio
async def test_strict_missing_database_is_unavailable_even_with_process_fallback():
    with pytest.raises(memory.InstitutionalMemoryUnavailable, match="database unavailable"):
        await memory.institutional_search("tenant-a", strict=True)


@pytest.mark.asyncio
async def test_existing_default_keeps_tenant_scoped_fallback():
    assert (await memory.institutional_search("tenant-a"))[0]["key"] == "cached"
    assert await memory.institutional_search("tenant-b") == []


@pytest.mark.asyncio
async def test_strict_successful_empty_does_not_substitute_cached_rows(monkeypatch):
    fetch = pool(monkeypatch)
    assert await memory.institutional_search("tenant-a", strict=True) == []
    assert fetch.await_args.args[1:] == ("tenant-a", 20)


@pytest.mark.asyncio
async def test_strict_rows_preserve_source_fields_and_tenant_filter(monkeypatch):
    row = {"key": "source-key", "value": json.dumps({"verdict": "needs_review", "source_url": "https://attack.mitre.org/techniques/T1078/"}),
           "tags": ["identity"], "analyst_override": False, "override_reason": None,
           "created_at": datetime(2026, 10, 20, tzinfo=UTC)}
    fetch = pool(monkeypatch, rows=[row])
    rows = await memory.institutional_search("tenant-a", tags=["identity"], limit=3, strict=True)
    assert fetch.await_args.args[1:] == ("tenant-a", ["identity"], 3)
    assert "WHERE tenant_id=$1 AND tags && $2" in fetch.await_args.args[0]
    assert rows[0]["value"]["source_url"].endswith("/T1078/")
    assert rows[0]["created_at"] == "2026-10-20T00:00:00+00:00"


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [TimeoutError("offline timeout"), RuntimeError("offline query failure")])
async def test_strict_read_failure_is_unavailable_without_cached_substitution(monkeypatch, error):
    pool(monkeypatch, error=error)
    with pytest.raises(memory.InstitutionalMemoryUnavailable, match="read failed") as caught:
        await memory.institutional_search("tenant-a", strict=True)
    assert caught.value.__cause__ is error


@pytest.mark.asyncio
async def test_default_read_failure_retains_original_fallback(monkeypatch):
    pool(monkeypatch, error=TimeoutError("offline"))
    assert (await memory.institutional_search("tenant-a"))[0]["key"] == "cached"


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["no_pool", "query_error", "empty"])
async def test_real_bundle_marks_durable_memory_failure_unknown_but_accepts_empty(monkeypatch, source):
    if source != "no_pool":
        pool(monkeypatch, error=TimeoutError("offline") if source == "query_error" else None)
    builder = ContextBundleBuilder()
    for name in ("_fetch_neighborhoods", "_fetch_baselines", "_fetch_threat_intel", "_fetch_incident_context"):
        monkeypatch.setattr(builder, name, AsyncMock(return_value={}))
    result = await builder.build(SimpleNamespace(incident_id=uuid4(), tenant_id="tenant-a", alert_summary="Memory source", raw_alert={}))
    assert result.historical_similar_cases == []
    if source == "empty":
        assert result.errors == []
    else:
        assert "memory:InstitutionalMemoryUnavailable" in result.errors
        assert "unknown" in "\n".join(result.prompt_context_lines())
