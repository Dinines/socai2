"""Direct HTTP dependency/connection checks; no database or model calls."""
from unittest.mock import AsyncMock, Mock

import pytest
from app.api.v1.endpoints import socai2_cases, socai2_tasks
from app.db import case_database
from app.socai2.baseline_store import StoreError
from fastapi import HTTPException, Request
from pydantic import SecretStr


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(case_database, "_runtime", None)
    monkeypatch.setattr(case_database.settings, "SOCAI2_CASE_API_ENABLED", True)
    monkeypatch.setattr(case_database.settings, "SOCAI2_PAGE_READ_ENABLED", True)
    monkeypatch.setattr(case_database.settings, "SOCAI2_CASE_DATABASE_URL", SecretStr(""))


@pytest.mark.asyncio
@pytest.mark.parametrize("api", [socai2_cases, socai2_tasks])
async def test_get_keeps_reader_and_writes_require_explicit_connection(configured, monkeypatch, api):
    get = Request({"type": "http", "method": "GET"})
    post = Request({"type": "http", "method": "POST"})
    assert (await api.get_service(get)).sessions is api.AsyncSessionLocal
    with pytest.raises(HTTPException) as error:
        await api.get_service(post)
    assert error.value.status_code == 503
    assert error.value.detail == "case_write_database_not_configured"
    writer = object()
    monkeypatch.setattr(api, "get_case_write_sessions", lambda: writer)
    assert (await api.get_service(post)).sessions is writer
    assert (await api.get_service(get)).sessions is api.AsyncSessionLocal


@pytest.mark.asyncio
async def test_writer_preserves_explicit_target_tls_and_reuses_pool(configured, monkeypatch):
    engine = Mock(dispose=AsyncMock())
    create = Mock(return_value=engine)
    sessions = Mock()
    monkeypatch.setattr(case_database, "create_async_engine", create)
    monkeypatch.setattr(case_database, "async_sessionmaker", Mock(return_value=sessions))
    monkeypatch.setattr(case_database.settings, "SOCAI2_CASE_DATABASE_URL", SecretStr(
        "postgresql+psycopg://synthetic:private-placeholder@db.example:5439/case_test?sslmode=verify-full&sslrootcert=/test/ca.crt"))
    assert case_database.get_case_write_sessions() is case_database.get_case_write_sessions() is sessions
    assert create.call_count == 1
    url = create.call_args.args[0]
    assert (url.username, url.host, url.port, url.database) == ("synthetic", "db.example", 5439, "case_test")
    assert url.query == {"sslmode": "verify-full", "sslrootcert": "/test/ca.crt"}
    await case_database.close_case_database()
    engine.dispose.assert_awaited_once()
    assert case_database._runtime is None


@pytest.mark.parametrize("value", ["postgresql+psycopg:///implicit", "sqlite+aiosqlite:///wrong.db"])
def test_invalid_or_implicit_database_has_safe_error(configured, monkeypatch, value):
    monkeypatch.setattr(case_database.settings, "SOCAI2_CASE_DATABASE_URL", SecretStr(value))
    with pytest.raises(StoreError, match="case_write_database_configuration_invalid"):
        case_database.get_case_write_sessions()
    assert case_database._runtime is None
