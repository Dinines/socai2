"""Standalone route/lifespan guards without any database or model call."""
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app import socai2_main as standalone


def test_only_new_service_routes_and_no_legacy_startup():
    paths = set(standalone.app.openapi()["paths"]) | {r.path for r in standalone.app.routes if hasattr(r, "path")}
    assert "/api/v1/socai2/alerts/{alert_id}/analyze" in paths
    assert "/api/v1/socai2/incidents/{incident_id}/diagnose" in paths
    assert "/api/v1/socai2/cases/{case_id}/members/move" in paths
    assert "/api/v1/alerts" not in paths and "/api/v1/actions" not in paths
    assert "/livez" in paths and "/readyz" in paths
    assert "app.main" not in sys.modules and "app.api.v1.router" not in sys.modules


def test_database_identity_guard_rejects_default_or_mismatch(monkeypatch):
    monkeypatch.delenv("AISOC_DEV_AUTH_BYPASS", raising=False)
    for expected, actual in [("", "isolated"), ("aisoc", "aisoc"), ("isolated", "another")]:
        monkeypatch.setenv("SOCAI2_SERVICE_DATABASE_NAME", expected)
        with patch.object(standalone, "settings", SimpleNamespace(DATABASE_URL=f"postgresql://unused@localhost/{actual}")), \
                pytest.raises(RuntimeError, match="explicit_independent_database"):
            standalone.isolated_database_name()
    monkeypatch.setenv("SOCAI2_SERVICE_DATABASE_NAME", "isolated")
    with patch.object(standalone, "settings", SimpleNamespace(DATABASE_URL="postgresql://unused@localhost/isolated")):
        assert standalone.isolated_database_name() == "isolated"
        monkeypatch.setenv("AISOC_DEV_AUTH_BYPASS", "true")
        with pytest.raises(RuntimeError, match="does_not_allow_auth_bypass"):
            standalone.isolated_database_name()
