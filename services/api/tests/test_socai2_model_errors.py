"""Provider failures remain auditable and never become model answers."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.services.llm_resolver import LlmConfig
from app.socai2.baseline_analysis_model import TenantChatGateway, usage
from app.socai2.model_errors import MAX_ERROR_BODY, ModelCallError, provider_error
from app.socai2.model_protocol import DEEPSEEK_BASE, DEEPSEEK_PROTOCOL
from test_socai2_model_protocol import canonical


def http_error(body=None, *, content=None):
    request = httpx.Request("POST", "https://synthetic.invalid/path?token=url-secret",
        headers={"authorization": "Bearer header-secret"})
    response = httpx.Response(400, request=request, json=body) if content is None else httpx.Response(
        400, request=request, content=content)
    return httpx.HTTPStatusError("unsafe exception with private credentials", request=request, response=response)


def failure():
    return ModelCallError(provider_error(http_error({"error": {
        "code": "upstream_error", "type": "invalid_request_error", "param": "text.format.schema",
        "message": "synthetic upstream failure"}}), "synthetic-unused-key"))


class FailingGateway:
    provider, model = "synthetic", "synthetic-no-network"

    def __init__(self):
        self.calls = 0

    async def configure(self, *_):
        return True

    async def measure(self, body, stage):
        from socai2_test_model_view import synthetic_measure
        return await synthetic_measure(body, stage)

    async def complete(self, *_):
        self.calls += 1
        raise failure()


def test_error_allowlist_redacts_before_limiting_and_omits_request_and_headers():
    key = "synthetic-private-secret"
    exc = http_error({"error": {"code": "invalid_schema", "type": "invalid_request_error",
        "param": "text.format.schema", "message": "前" * 330 + key +
        " https://internal.invalid/?token=other-secret Bearer bearer-secret Basic basic-secret api_key=assigned-secret",
        "request": {"secret": "nested-secret"}}, "headers": {"token": "response-header-secret"}})
    data = provider_error(exc, key)
    encoded = json.dumps(data, ensure_ascii=False)
    for secret in (key, "url-secret", "header-secret", "other-secret", "bearer-secret", "basic-secret", "assigned-secret", "nested-secret"):
        assert secret not in encoded
    assert data["http_status"] == 400 and data["fields"]["code"] == "invalid_schema"
    assert data["fields"]["param"] == "text.format.schema"
    assert data["redacted_fields"] == data["truncated_fields"] == ["message"]
    assert len(data["fields"]["message"].encode()) <= 1024
    assert exc.response.json()["error"]["message"].find(key) > 0


@pytest.mark.parametrize("content,state", [(b"<html>private body</html>", "non_json_omitted"),
    (b"x" * (MAX_ERROR_BODY + 1), "oversize_omitted"), (b"[]", "unsupported_shape_omitted"),
    (b'{"error":{"message": ["private"]}}', "selected_json_fields")])
def test_unsupported_error_bodies_are_not_dumped(content, state):
    data = provider_error(http_error(content=content), "synthetic-unused-key")
    assert data["body_state"] == state and data["fields"] == {}
    assert "private" not in json.dumps(data)


def test_timeout_has_no_invented_http_body_answer_or_usage():
    data = provider_error(httpx.ReadTimeout("unsafe URL with key"), "unused")
    error = ModelCallError(data)
    assert data["body_state"] == "unavailable" and data["http_status"] is None
    assert str(error) == "model_transport_error" and error.payload()["raw"] is None
    assert usage(error.payload())["usage_state"] == "unavailable"
    assert usage(error.payload())["total_tokens"] is None


def test_short_secret_variants_are_redacted_without_relying_on_truncation():
    message = "Basic basic-secret Bearer bearer-secret token=assigned-secret https://internal.invalid/?key=url-secret sk-extra-secret configured-secret"
    data = provider_error(http_error({"error": {"message": message, "param": "configured-secret"}}), "configured-secret")
    assert data["truncated_fields"] == []
    assert "secret" not in json.dumps(data)
    assert set(data["redacted_fields"]) == {"message", "param"}


def test_malformed_unicode_does_not_break_failure_recording():
    data = provider_error(http_error(content=b'{"error":{"message":"\\ud800"}}'), "unused")
    assert data["body_state"] == "selected_json_fields"
    json.dumps(data).encode("utf-8")


@pytest.mark.parametrize("provider,target", [(DEEPSEEK_PROTOCOL, "complete_deepseek"),
    ("chat_completions", "safe_chat_completions_request")])
def test_both_transports_capture_one_failure_without_retry_or_fallback(provider, target):
    gateway = TenantChatGateway()
    gateway.provider = provider
    gateway.config = LlmConfig(True, DEEPSEEK_BASE, "deepseek-flash", "synthetic-key", "environment", "")
    call = AsyncMock(side_effect=http_error({"error": {"message": "schema rejected", "param": "text.format.schema"}}))
    with patch("app.socai2.baseline_analysis_model." + target, call), pytest.raises(ModelCallError) as caught:
        asyncio.run(gateway.complete(canonical(), 2))
    assert call.await_count == 1
    assert caught.value.details["fields"]["param"] == "text.format.schema"
    assert caught.value.details["http_status"] == 400
