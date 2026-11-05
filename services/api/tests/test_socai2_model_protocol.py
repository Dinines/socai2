"""DeepSeek wire records, refusal boundaries and unchanged legacy transport."""
import asyncio
import json
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from app.services.llm_resolver import LlmConfig
from app.socai2 import model_protocol as protocol
from app.socai2.alert_basic_contract import Answer
from app.socai2.baseline_analysis_model import TenantChatGateway, usage
from app.socai2.structured_output import response_format


def canonical():
    return {"model": "deepseek-flash", "messages": [{"role": "system", "content": "Return JSON."},
        {"role": "user", "content": "Synthetic summary; no authorization supplied."}],
        "response_format": response_format(Answer, ["S1"]), "max_tokens": 3000, "temperature": 0}


def reply():
    return {"object": "response", "id": "synthetic-response", "status": "completed", "error": None,
        "output": [{"type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": '{"verdict":"needs_review"}'}]}],
        "usage": {"input_tokens": 100, "output_tokens": 30, "total_tokens": 130,
            "input_tokens_details": {"cached_tokens": 20}, "output_tokens_details": {"reasoning_tokens": 0}}}


def test_prepare_is_explicit_preserves_all_inputs_and_schema_and_old_protocol():
    body = canonical()
    original = deepcopy(body)
    assert protocol.prepare_request(SimpleNamespace(provider="chat_completions"), body) is body
    wire = protocol.prepare_request(SimpleNamespace(provider=protocol.DEEPSEEK_PROTOCOL), body)
    assert wire["input"] == body["messages"]
    schema = body["response_format"]["json_schema"]["schema"]
    expected = deepcopy(schema)
    expected["properties"]["decision_basis"]["anyOf"][0] = deepcopy(schema["$defs"]["DecisionBasis"])
    assert wire["text"]["format"]["schema"] == expected
    assert wire["text"]["format"]["strict"] is True
    assert wire["max_output_tokens"] == 3000 and wire["reasoning"] == {"effort": "none"}
    assert not wire["stream"] and not wire["store"] and "tools" not in wire
    assert body == original


def test_exact_recorded_wire_sent_once_with_original_response_and_no_redirects():
    body = protocol.prepare_request(SimpleNamespace(provider=protocol.DEEPSEEK_PROTOCOL), canonical())
    original, seen, factory_args = deepcopy(body), [], []
    response = reply()
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=response)
    real_client = httpx.AsyncClient
    def client(**kwargs):
        factory_args.append(kwargs)
        return real_client(transport=httpx.MockTransport(handler), **kwargs)
    config = LlmConfig(True, protocol.DEEPSEEK_BASE, "deepseek-flash", "synthetic-not-a-key", "environment", "")
    with patch.object(protocol.httpx, "AsyncClient", client):
        actual = asyncio.run(protocol.complete_deepseek(config, body, 2))
    assert actual == response and body == original and len(seen) == 1
    assert json.loads(seen[0].content) == body
    assert str(seen[0].url) == "https://api.deepseek.com/responses"
    assert factory_args == [{"timeout": 2, "follow_redirects": False}]


def test_failed_provider_not_retried_or_downgraded():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(400, json={"error": "synthetic schema failure"})
    real_client = httpx.AsyncClient
    config = LlmConfig(True, protocol.DEEPSEEK_BASE, "deepseek-flash", "synthetic-not-a-key", "environment", "")
    wire = protocol.prepare_request(SimpleNamespace(provider=protocol.DEEPSEEK_PROTOCOL), canonical())
    with patch.object(protocol.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)), \
            pytest.raises(httpx.HTTPStatusError):
        asyncio.run(protocol.complete_deepseek(config, wire, 2))
    assert len(calls) == 1


def test_contract_and_host_guard_precede_network():
    config = LlmConfig(True, protocol.DEEPSEEK_BASE, "deepseek-flash", "synthetic-not-a-key", "environment", "")
    wire = protocol.prepare_request(SimpleNamespace(provider=protocol.DEEPSEEK_PROTOCOL), canonical())
    with patch.object(protocol, "enforce_airgap_for_url", side_effect=ValueError("policy denied")), \
            patch.object(protocol.httpx, "AsyncClient") as client, pytest.raises(ValueError, match="policy denied"):
        asyncio.run(protocol.complete_deepseek(config, wire, 2))
    client.assert_not_called()
    with patch.object(protocol.LLMInputContract, "validate", side_effect=ValueError("contract denied")), \
            patch.object(protocol.httpx, "AsyncClient") as client, pytest.raises(ValueError, match="contract denied"):
        asyncio.run(protocol.complete_deepseek(config, wire, 2))
    client.assert_not_called()


def test_parser_view_keeps_raw_and_rejects_incomplete_refusal_tools_and_ambiguity():
    data = reply()
    original = deepcopy(data)
    assert protocol.response_choices(data)[0]["message"]["content"] == '{"verdict":"needs_review"}'
    assert data == original
    for state in ("incomplete", "failed", "in_progress", None):
        value = {**data, "status": state}
        assert protocol.response_choices(value)[0]["finish_reason"] != "stop"
    for mutate in (
        lambda v: v["output"].append(deepcopy(v["output"][0])),
        lambda v: v["output"].append({"type": "web_search_call"}),
        lambda v: v["output"][0].update(role="user"),
        lambda v: v["output"][0].update(content=[{"type": "refusal", "refusal": "refused"}]),
        lambda v: v["output"][0]["content"].append({"type": "output_text", "text": "extra"}),
    ):
        value = deepcopy(data); mutate(value)
        assert protocol.response_choices(value) == []
    value = deepcopy(data); value["output"][0]["status"] = "incomplete"
    assert protocol.response_choices(value)[0]["finish_reason"] != "stop"


def test_usage_maps_provider_values_without_guessing_missing_or_inconsistent_counts():
    data = reply()
    observed = usage(data)
    assert observed["usage_state"] == "reported" and observed["total_tokens"] == 130
    assert observed["cached_input_tokens"] == 20 and observed["reasoning_tokens"] == 0
    assert observed["cost"] is None and observed["cost_state"] == "unpriced"
    data["usage"]["total_tokens"] = 1
    assert usage(data)["usage_state"] == "partial"
    data["usage"] = {}
    assert usage(data)["usage_state"] == "unavailable"


def test_protocol_opt_in_validates_model_and_does_not_change_shared_env(monkeypatch):
    @asynccontextmanager
    async def transaction(_):
        yield SimpleNamespace(db=None)
    service = SimpleNamespace(transaction=transaction)
    config = LlmConfig(True, protocol.DEEPSEEK_BASE, "deepseek-flash", "synthetic-not-a-key", "environment", "")
    async def resolver(*_):
        return config
    gateway = TenantChatGateway()
    monkeypatch.setenv("SOCAI2_MODEL_PROTOCOL", protocol.DEEPSEEK_PROTOCOL)
    with patch("app.socai2.baseline_analysis_model.resolve_llm_config", resolver):
        assert asyncio.run(gateway.configure(service, "tenant"))
        assert gateway.provider == protocol.DEEPSEEK_PROTOCOL
        config = replace(config, base_url="https://unselected.invalid")
        assert not asyncio.run(gateway.configure(service, "tenant"))
        monkeypatch.delenv("SOCAI2_MODEL_PROTOCOL")
        assert asyncio.run(gateway.configure(service, "tenant"))
        assert gateway.provider == "chat_completions"
