"""Standalone route/lifespan guards without any database or model call."""
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import SecretStr
from app import socai2_main as standalone


def test_only_new_service_routes_and_no_legacy_startup():
    paths = set(standalone.app.openapi()["paths"]) | {r.path for r in standalone.app.routes if hasattr(r, "path")}
    assert "/api/v1/socai2/alerts/{alert_id}/analyze" in paths
    assert "/api/v1/socai2/incidents/{incident_id}/diagnose" in paths
    assert "/api/v1/socai2/cases/{case_id}/members/move" in paths
    assert "/api/v1/alerts" not in paths and "/api/v1/actions" not in paths
    assert "/livez" in paths and "/readyz" in paths
    assert "app.main" not in sys.modules and "app.api.v1.router" not in sys.modules


def config(database, writer=None, *, writes=True):
    return SimpleNamespace(DATABASE_URL=f"postgresql://reader@localhost:5432/{database}",
        SOCAI2_CASE_API_ENABLED=writes, SOCAI2_STAGE_EXECUTION_ENABLED=False,
        SOCAI2_CASE_DATABASE_URL=SecretStr(writer or f"postgresql://writer@localhost:5432/{database}"))


def test_database_identity_guard_rejects_default_or_mismatch(monkeypatch):
    monkeypatch.delenv("AISOC_DEV_AUTH_BYPASS", raising=False)
    for expected, actual in [("", "isolated"), ("isolated", "another")]:
        monkeypatch.setenv("SOCAI2_SERVICE_DATABASE_NAME", expected)
        with patch.object(standalone, "settings", config(actual)), \
                pytest.raises(RuntimeError, match="matching_explicit_database_targets"):
            standalone.configured_database_name()
    monkeypatch.setenv("SOCAI2_SERVICE_DATABASE_NAME", "isolated")
    with patch.object(standalone, "settings", config("isolated")):
        assert standalone.configured_database_name() == "isolated"
        monkeypatch.setenv("AISOC_DEV_AUTH_BYPASS", "true")
        with pytest.raises(RuntimeError, match="does_not_allow_auth_bypass"):
            standalone.configured_database_name()


def test_formal_target_requires_matching_explicit_writer(monkeypatch):
    monkeypatch.delenv("AISOC_DEV_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("SOCAI2_SERVICE_DATABASE_NAME", "aisoc")
    with patch.object(standalone, "settings", config("aisoc")):
        assert standalone.configured_database_name() == "aisoc"
    for writer in ["postgresql://writer@localhost:5432/old", "postgresql://writer@other:5432/aisoc",
                   "postgresql://writer@localhost:5439/aisoc", "invalid-private-connection"]:
        with patch.object(standalone, "settings", config("aisoc", writer)), \
                pytest.raises(RuntimeError, match="^socai2_service_requires_matching_explicit_database_targets$"):
            standalone.configured_database_name()
    missing = config("aisoc")
    missing.SOCAI2_CASE_DATABASE_URL = SecretStr("")
    with patch.object(standalone, "settings", missing), pytest.raises(RuntimeError):
        standalone.configured_database_name()


def test_manual_stage_service_uses_explicit_writer(monkeypatch):
    from app.api.v1.endpoints import socai2_stage_execution as api
    from app.socai2.baseline_store import StoreError
    from fastapi import HTTPException
    sessions = object()
    monkeypatch.setattr(api.settings, "SOCAI2_STAGE_EXECUTION_ENABLED", True)
    monkeypatch.setattr(api, "get_case_write_sessions", lambda: sessions)
    assert api.get_execution_service().sessions is sessions
    def absent():
        raise StoreError("case_write_database_not_configured", 503)
    monkeypatch.setattr(api, "get_case_write_sessions", absent)
    with pytest.raises(HTTPException) as error:
        api.get_execution_service()
    assert error.value.status_code == 503 and error.value.detail == "case_write_database_not_configured"
