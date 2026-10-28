"""The existing host adapter's actual HTTP mapping, with vendor responses substituted."""
from urllib.parse import parse_qs

import httpx
import pytest

from app.live_actions.investigation_reads import CrowdStrikeGetHost
from app.live_actions.models import LiveActionRequest
from app.services.credential_resolver import resolve_params


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["normal", "empty", "failed"])
async def test_case_host_http_mapping(monkeypatch, scenario):
    original = httpx.AsyncClient
    calls = []

    def provider(request):
        calls.append(request)
        assert request.url.host == "product.invalid"
        if request.url.path == "/oauth2/token":
            assert request.method == "POST"
            assert parse_qs(request.content.decode()) == {"client_id": ["source-client"], "client_secret": ["fixture-secret"]}
            return httpx.Response(200, json={"access_token": "fixture-token"})
        assert request.method == "GET"
        assert request.headers["Authorization"] == "Bearer fixture-token"
        if request.url.path == "/devices/queries/devices/v1":
            assert dict(request.url.params) == {"filter": "hostname:'host-01'", "limit": "1"}
            if scenario == "failed":
                return httpx.Response(503, json={"errors": [{"message": "fixture unavailable"}]})
            return httpx.Response(200, json={"resources": [] if scenario == "empty" else ["device-01"]})
        assert request.url.path == "/devices/entities/devices/v2"
        assert dict(request.url.params) == {"ids": "device-01"}
        return httpx.Response(200, json={"resources": [{"device_id": "device-01", "hostname": "host-01",
            "platform_name": "Windows", "status": "normal", "last_seen": "2026-10-28T01:00:00Z"}]})

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(provider), **kwargs))
    params = resolve_params("crowdstrike", {"client_id": "source-client", "client_secret": "fixture-secret",
                                           "base_url": "https://product.invalid"}, extra={})
    request = LiveActionRequest(capability="get_host", vendor_id="crowdstrike", target="host-01", params=params, dry_run=False)
    result = await CrowdStrikeGetHost().execute(request)
    assert result.request_id == request.request_id
    if scenario == "normal":
        assert result.status.value == "succeeded"
        assert result.details["found"] is True
        assert result.details["device_id"] == "device-01"
        assert result.details["platform"] == "Windows"
        assert result.details["containment_status"] == "normal"
        assert len(calls) == 3
    elif scenario == "empty":
        assert result.status.value == "succeeded"
        assert result.details["found"] is False
        assert len(calls) == 2
    else:
        assert result.status.value == "failed"
        assert result.error
        assert len(calls) == 2
