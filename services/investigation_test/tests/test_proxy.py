"""Read-proxy component evidence uses an explicitly simulated HTTP transport."""
import hashlib
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from investigation_test.api import create_app
from investigation_test.config import Config
from investigation_test.proxy import UpstreamConfig

ROOT = Path(__file__).resolve().parents[3]
PREFIX = "/api/v1/socai2"
IDENTITY = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def config(tmp_path):
    base = Config.load(ROOT / "deploy/investigation-test/read-only.example.json")
    return base.model_copy(update={"environment_label": "streaming-20261115-01",
                                   "ledger_root": str(tmp_path / "absent-ledger")})


@pytest.fixture
def upstream():
    return UpstreamConfig.load(ROOT / "deploy/investigation-test/upstream.example.json").model_copy(
        update={"base_url": "http://candidate.invalid"})


def response(status, body, **headers):
    return httpx.Response(status, headers={"content-type": "application/json", **headers},
                          stream=httpx.ByteStream(body))


def test_no_startup_request_and_exact_runtime_contract(config, upstream):
    calls = []
    def handle(request):
        calls.append(request)
        return response(200, b'{"items":[],"total":0,"next_cursor":null}')
    with TestClient(create_app(config, upstream, transport=httpx.MockTransport(handle))) as client:
        meta = client.get("/test-api/v1/capabilities").json()["investigation_http"]
        assert meta["get_operations"] == 55 and meta["runtime_verified"] is False
        assert meta["tenant_id"] == str(upstream.tenant_id)
        assert calls == []
        assert len(client.get("/openapi.json").json()["paths"]) == 8
        result = client.get(PREFIX + "/analysis-runs?limit=1")
        assert result.status_code == 200 and result.json()["items"] == []
    assert len(calls) == 1
    assert not Path(config.ledger_root).exists()


def test_preserves_pages_queries_errors_and_does_not_forward_caller_identity(config, upstream):
    calls = []
    page1 = b'{"items":[{"id":"synthetic-run"}],"next_cursor":"a+/=","total":2}'
    page2 = b'{"items":[{"id":"synthetic-run-2"}],"next_cursor":null,"total":2}'
    error = b'{"detail":{"code":"not_found","source":"upstream"}}'
    def handle(request):
        calls.append(request)
        assert "authorization" not in request.headers and "cookie" not in request.headers
        assert "x-tenant-id" not in request.headers
        if request.url.path.endswith(IDENTITY):
            return response(404, error)
        return response(200, page2 if request.url.params.get("cursor") == "a+/=" else page1)
    with TestClient(create_app(config, upstream, transport=httpx.MockTransport(handle))) as client:
        first = client.get(PREFIX + "/analysis-runs", params={"limit": 1}, headers={
            "Authorization": "not-forwarded", "Cookie": "not-forwarded", "X-Tenant-ID": "not-forwarded"})
        second = client.get(PREFIX + "/analysis-runs", params={"limit": 1, "cursor": first.json()["next_cursor"]})
        missing = client.get(PREFIX + "/cases/" + IDENTITY)
        assert first.content == page1 and second.content == page2
        assert missing.status_code == 404 and missing.content == error
        assert missing.headers["x-investigation-environment"] == upstream.environment_label
    assert len(calls) == 3 and calls[1].url.params["cursor"] == "a+/="


def test_large_original_stream_is_complete_and_response_closed(config, upstream):
    original = b'large-original\x00' * 160000
    digest = hashlib.sha256(original).hexdigest()
    class Tracked(httpx.AsyncByteStream):
        closed = False
        async def __aiter__(self):
            for offset in range(0, len(original), 32768):
                yield original[offset:offset + 32768]
        async def aclose(self):
            self.closed = True
    stream = Tracked()
    def handle(request):
        return httpx.Response(200, stream=stream, headers={"content-type": "application/octet-stream",
            "content-length": str(len(original)), "x-content-sha256": digest,
            "content-disposition": 'attachment; filename="original.bin"', "etag": '"frozen"'})
    with TestClient(create_app(config, upstream, transport=httpx.MockTransport(handle))) as client:
        result = client.get(f"{PREFIX}/cases/{IDENTITY}/artifacts/{IDENTITY}")
        assert len(result.content) > config.max_document_bytes // 2
        assert result.content == original and result.headers["x-content-sha256"] == digest
        assert result.headers["content-length"] == str(len(original)) and result.headers["etag"] == '"frozen"'
    assert stream.closed


def test_rejects_non_get_unknown_paths_and_caller_targets_without_upstream_calls(config, upstream):
    calls = []
    def handle(request):
        calls.append(request)
        return response(200, b'{}')
    with TestClient(create_app(config, upstream, transport=httpx.MockTransport(handle))) as client:
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)(PREFIX + "/cases").status_code == 405
        assert client.get(PREFIX + "/not-a-read-path").status_code == 404
        assert client.get(PREFIX + "/alerts?upstream=http://different.invalid").status_code == 422
        assert client.get(PREFIX + "/alerts?limit=1&limit=2").status_code == 422
    assert calls == []


@pytest.mark.parametrize("kind,status,code", [
    ("connect", 502, "upstream_unavailable"), ("timeout", 504, "upstream_timeout"),
    ("redirect", 502, "upstream_redirect_rejected")])
def test_errors_are_not_empty_success_and_never_retry(config, upstream, kind, status, code):
    calls = []
    def handle(request):
        calls.append(request)
        if kind == "connect":
            raise httpx.ConnectError("controlled component failure", request=request)
        if kind == "timeout":
            raise httpx.ReadTimeout("controlled component timeout", request=request)
        return response(302, b"", location="http://different.invalid")
    with TestClient(create_app(config, upstream, transport=httpx.MockTransport(handle))) as client:
        result = client.get(PREFIX + "/alerts")
        assert result.status_code == status and result.json()["detail"]["code"] == code
    assert len(calls) == 1


def test_explicit_environment_and_contract_no_fallback(config, upstream):
    with pytest.raises(ValueError, match="environments differ"):
        create_app(config, upstream.model_copy(update={"environment_label": "other"}))
    with pytest.raises(ValueError, match="digest mismatch"):
        create_app(config, upstream.model_copy(update={"openapi_sha256": "0" * 64}))
    data = json.loads((ROOT / "deploy/investigation-test/upstream.example.json").read_text())
    for url in ("http://user:secret@candidate.invalid", "http://candidate.invalid/api", "file:///tmp/data"):
        with pytest.raises(ValueError):
            UpstreamConfig.model_validate_json(json.dumps({**data, "base_url": url}))
