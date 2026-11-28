"""Optional page wiring, no real business or model requests."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from investigation_test import __version__
from investigation_test.api import create_app
from investigation_test.config import Config
from investigation_test.viewer import ViewerConfig
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def config(tmp_path):
    return Config.load(ROOT / "deploy/investigation-test/read-only.example.json").model_copy(
        update={"ledger_root": str(tmp_path / "absent-ledger")})


def test_explicit_page_mount_keeps_api_schema_and_never_creates_ledger(config):
    viewer = ViewerConfig.load(ROOT / "deploy/investigation-test/viewer.example.json")
    with TestClient(create_app(config)) as client:
        for path in ("/", "/index.html", "/viewer/"):
            assert client.get(path).status_code == 404
        assert client.get("/test-api/v1/capabilities").json()["viewer_version"] is None
    with TestClient(create_app(config, viewer=viewer)) as client:
        page = client.get("/viewer/")
        assert page.status_code == 200
        for path in ("/", "/index.html"):
            entry = client.get(path, follow_redirects=False)
            assert entry.status_code == 307 and entry.headers["location"] == "/viewer/"
            assert entry.headers["cache-control"] == "no-store"
            assert client.get(path).content == page.content
        assert client.get("/viewer/config.json").json() == {
            "viewer_version": __version__, **viewer.model_dump()}
        for name in ("viewer.css", "viewer.js", "viewer_state.mjs", "execution_flow.mjs", "delivery_view.mjs", "frozen_sources.mjs", "test_sources.mjs", "viewer_links.mjs"):
            asset = client.get("/viewer/assets/" + name)
            assert asset.status_code == 200
            assert asset.headers["cache-control"] == "no-store"
        assert client.get("/test-api/v1/capabilities").json()["viewer_version"] == __version__
        assert len(client.get("/openapi.json").json()["paths"]) == 8
        assert client.post("/viewer/config.json").status_code == 405
    assert not Path(config.ledger_root).exists()


@pytest.mark.parametrize("data", [
    {}, {"poll_interval_seconds": 0, "request_timeout_seconds": 2, "page_size": 1},
    {"poll_interval_seconds": 2, "request_timeout_seconds": float("inf"), "page_size": 1},
    {"poll_interval_seconds": 2, "request_timeout_seconds": 2, "page_size": 101},
    {"poll_interval_seconds": 2, "request_timeout_seconds": 2, "page_size": 1, "test_source_prefixes": [""]},
])
def test_invalid_viewer_settings_rejected(data):
    with pytest.raises(ValidationError):
        ViewerConfig.model_validate(data)


def test_page_size_cannot_exceed_ledger_limit(config):
    viewer = ViewerConfig(poll_interval_seconds=2, request_timeout_seconds=2, page_size=20)
    with pytest.raises(ValueError, match="page_size exceeds"):
        create_app(config.model_copy(update={"max_limit": 10}), viewer=viewer)
