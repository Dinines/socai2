"""Full-wire accounting includes schema and chat template; no generated answers."""

import asyncio
import copy
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from app.socai2.baseline_store import StoreError, digest
from app.socai2.runtime_policy import load_policy
from app.socai2.token_budget import BackendTokenMeter

FILE = Path(__file__).resolve().parents[3] / "deploy/local-investigation/investigation-policy.toml"


def request(policy):
    return {"model": policy.alias, "messages": [{"role": "user", "content": "synthetic evidence"}],
        "max_tokens": policy.output_tokens["C3"], "response_format": {"json_schema": {"schema": {"type": "object"}}}}


def test_schema_and_template_counted_separately_with_preserved_request():
    policy = load_policy(FILE).model
    body, seen = request(policy), []
    def handle(req):
        value = json.loads(req.content)
        seen.append(value)
        return httpx.Response(200, json={"count": 150 if "messages" in value else 70, "max_model_len": policy.context_tokens})
    result = asyncio.run(BackendTokenMeter(policy, transport=httpx.MockTransport(handle)).measure(body, "C3"))
    assert seen[0]["messages"] == body["messages"] and seen[0]["add_generation_prompt"]
    assert json.loads(seen[1]["prompt"])["response_format"] == body["response_format"]
    assert "messages" not in json.loads(seen[1]["prompt"])
    assert result["reserved_total_tokens"] == 220 + policy.tokenizer["safety_tokens"] + policy.output_tokens["C3"]
    assert result["body_sha256"] == digest(body) and body == request(policy)
    assert result["context_fits"]


def test_token_limit_checks_context_with_output_not_serialized_byte_count():
    policy = load_policy(FILE).model
    def handle(req):
        return httpx.Response(200, json={"count": policy.context_tokens, "max_model_len": policy.context_tokens})
    result = asyncio.run(BackendTokenMeter(policy, transport=httpx.MockTransport(handle)).measure(request(policy), "C3"))
    assert result["wire_bytes"] < policy.context_tokens and not result["context_fits"]


@pytest.mark.parametrize("payload", [{"count": 1, "max_model_len": 32768}, {"count": True, "max_model_len": 65536}])
def test_changed_backend_capacity_or_invalid_count_blocks_dispatch(payload):
    policy = load_policy(FILE).model
    with pytest.raises(StoreError, match="token_meter_capacity_or_response_mismatch"):
        asyncio.run(BackendTokenMeter(policy, transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))).measure(request(policy), "C3"))


def test_unreachable_counter_is_not_zero_input_or_a_model_retry():
    policy = load_policy(FILE).model
    calls = []
    def handle(req):
        calls.append(req)
        raise httpx.ReadTimeout("synthetic", request=req)
    with pytest.raises(StoreError, match="token_meter_unavailable"):
        asyncio.run(BackendTokenMeter(policy, transport=httpx.MockTransport(handle)).measure(request(policy), "C3"))
    assert len(calls) == 1


def test_meter_uses_remaining_stage_time_and_never_runs_after_deadline():
    from app.socai2.token_budget import measure_with_deadline
    class SlowMeter:
        calls = 0
        async def measure(self, body, stage):
            self.calls += 1
            await asyncio.sleep(10)
    gateway = SlowMeter()
    with pytest.raises(StoreError, match="token_measurement_deadline_reached"):
        asyncio.run(measure_with_deadline(gateway, {}, "C3", 0))
    assert gateway.calls == 0
    with pytest.raises(StoreError, match="token_measurement_deadline_reached"):
        asyncio.run(measure_with_deadline(gateway, {}, "C3", 0.01))
    assert gateway.calls == 1


@pytest.mark.parametrize("stage", ["A", "I", "C3", "Deep", "C6"])
@pytest.mark.parametrize("excess", [0, 1])
def test_expanded_policy_admits_only_input_plus_output_inside_serving_window(stage, excess):
    policy = load_policy(FILE.with_name("investigation-policy-case-v1.toml")).model
    body = {**request(policy), "max_tokens": policy.output_tokens[stage]}
    input_limit = policy.context_tokens - policy.output_tokens[stage] - policy.tokenizer["safety_tokens"]

    def handle(req):
        value = json.loads(req.content)
        count = input_limit - 64 + excess if "messages" in value else 64
        return httpx.Response(200, json={"count": count, "max_model_len": policy.context_tokens})

    result = asyncio.run(BackendTokenMeter(policy, transport=httpx.MockTransport(handle)).measure(body, stage))
    assert result["reserved_total_tokens"] == policy.context_tokens + excess
    assert result["context_fits"] == (excess == 0)
    assert result["body_sha256"] == digest(body)


def test_expanded_run_budget_keeps_two_full_c6_calls_available(monkeypatch):
    from datetime import UTC, datetime

    from app.socai2 import runtime_policy
    from app.socai2.baseline_analysis import budget_reason
    from app.socai2.baseline_capacity import final_reservation

    policy = load_policy(FILE.with_name("investigation-policy-case-v1.toml"))
    monkeypatch.setattr(runtime_policy, "active_policy", lambda: policy)
    now = datetime.now(UTC)
    window = policy.model.context_tokens
    measurement = {"context_fits": True, "reserved_total_tokens": window}
    reservation = final_reservation(None, None)
    assert reservation["reserved_tokens"] == 2 * window
    for name in ("alert_basic", "incident_diagnosis", "case"):
        configured = getattr(policy, name)
        limits = configured.limits(now, policy.identity)
        steps = []
        for index in range(configured.max_model_calls):
            keep_final = name == "case" and index < configured.max_model_calls - 2
            assert budget_reason(steps, limits, 0, now, measurement=measurement,
                                 reserve_calls=2 if keep_final else 0,
                                 reservation=reservation if keep_final else None) is None
            steps.append({"kind": "model", "state": "completed",
                          "usage": {"usage_state": "reported", "total_tokens": window}})
        assert budget_reason(steps, limits, 0, now, measurement=measurement) == "model_call_budget_exhausted"


def incident_grammar_request(policy):
    return {"model": policy.alias, "messages": [{"role": "user", "content": "synthetic evidence"}],
            "max_tokens": policy.output_tokens["I"], "temperature": 0,
            "response_format": {"type": "structural_tag", "format": {
                "type": "json_schema", "json_schema": {"type": "object"}, "max_whitespace_cnt": 8}}}


def measure_saved_counts(policy, body, stage, chat, envelope):
    def handle(req):
        payload = json.loads(req.content)
        return httpx.Response(200, json={"count": chat if "messages" in payload else envelope,
                                        "max_model_len": policy.context_tokens})
    return asyncio.run(BackendTokenMeter(policy, transport=httpx.MockTransport(handle)).measure(body, stage))


@pytest.mark.parametrize("excess", [0, 1])
def test_incident_grammar_window_uses_chat_but_run_budget_keeps_envelope(excess):
    from datetime import UTC, datetime

    from app.socai2.baseline_analysis import budget_reason

    selected = load_policy(FILE.with_name("investigation-policy-case-v1.toml"))
    policy = replace(selected.model, protocol="chat_completions", schema_profile="vllm_grammar_v1")
    body = incident_grammar_request(policy)
    original = copy.deepcopy(body)
    chat = policy.context_tokens - policy.output_tokens["I"] - policy.tokenizer["safety_tokens"] + excess
    envelope = 1024
    measured = measure_saved_counts(policy, body, "I", chat, envelope)
    assert measured["context_accounting"] == "chat_template_plus_output_and_safety"
    assert measured["context_input_tokens"] == chat + policy.tokenizer["safety_tokens"]
    assert measured["context_required_tokens"] == policy.context_tokens + excess
    assert measured["context_fits"] == (excess == 0)
    assert measured["envelope_tokens"] == envelope
    assert measured["reserved_input_tokens"] == measured["context_input_tokens"] + envelope
    assert measured["reserved_total_tokens"] == measured["context_required_tokens"] + envelope
    assert measured["body_sha256"] == digest(body) and body == original
    now = datetime.now(UTC)
    limits = selected.incident_diagnosis.limits(now, selected.identity)
    assert budget_reason([], limits, 0, now, measurement=measured) == (
        None if excess == 0 else "model_context_capacity_exceeded")
    if excess == 0:
        smaller = limits.model_copy(update={"max_tokens": measured["reserved_total_tokens"] - 1})
        assert budget_reason([], smaller, 0, now, measurement=measured) == "model_token_budget_insufficient"


@pytest.mark.parametrize("stage", ["A", "C3", "Deep", "C6"])
def test_grammar_context_uses_protocol_capability_not_stage(stage):
    policy = replace(load_policy(FILE).model, protocol="chat_completions", schema_profile="vllm_grammar_v1")
    body = {**incident_grammar_request(policy), "max_tokens": policy.output_tokens[stage]}
    chat = policy.context_tokens - policy.output_tokens[stage] - policy.tokenizer["safety_tokens"]
    measured = measure_saved_counts(policy, body, stage, chat, 1)
    assert measured["context_accounting"] == "chat_template_plus_output_and_safety"
    assert measured["context_required_tokens"] == policy.context_tokens
    assert measured["reserved_total_tokens"] == policy.context_tokens + 1
    assert measured["context_fits"]


@pytest.mark.parametrize("excess", [0, 1])
def test_json_schema_window_keeps_full_reservation_and_real_capacity_limit(excess):
    from datetime import UTC, datetime

    from app.socai2.baseline_analysis import budget_reason

    selected = load_policy(FILE.with_name("investigation-policy-case-v1.toml"))
    policy = replace(selected.model, protocol="chat_completions", schema_profile="vllm_grammar_v1")
    body = {**incident_grammar_request(policy), "max_tokens": policy.output_tokens["C3"],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "result", "schema": {"type": "object"}, "strict": True}}}
    original = copy.deepcopy(body)
    chat = policy.context_tokens - policy.output_tokens["C3"] - policy.tokenizer["safety_tokens"] + excess
    measured = measure_saved_counts(policy, body, "C3", chat, 1024)
    assert measured["context_required_tokens"] == policy.context_tokens + excess
    assert measured["context_fits"] == (excess == 0)
    assert measured["reserved_total_tokens"] == measured["context_required_tokens"] + 1024
    assert measured["body_sha256"] == digest(body) and body == original
    now = datetime.now(UTC)
    limits = selected.case.limits(now, selected.identity)
    assert budget_reason([], limits, 0, now, measurement=measured) == (
        None if excess == 0 else "model_context_capacity_exceeded")
    if excess == 0:
        smaller = limits.model_copy(update={"max_tokens": measured["reserved_total_tokens"] - 1})
        assert budget_reason([], smaller, 0, now, measurement=measured) == "model_token_budget_insufficient"


@pytest.mark.parametrize("extension", ["loose_schema", "format_extension", "template", "multimodal"])
def test_json_schema_unknown_shape_keeps_conservative_context(extension):
    policy = replace(load_policy(FILE).model, protocol="chat_completions", schema_profile="vllm_grammar_v1")
    body = {**incident_grammar_request(policy), "max_tokens": policy.output_tokens["C3"],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "result", "schema": {"type": "object"}, "strict": True}}}
    if extension == "loose_schema":
        body["response_format"]["json_schema"]["strict"] = False
    elif extension == "format_extension":
        body["response_format"]["extra"] = True
    elif extension == "template":
        body["chat_template_kwargs"] = {}
    else:
        body["messages"][0]["content"] = []
    measured = measure_saved_counts(policy, body, "C3", 1, policy.context_tokens)
    assert measured["context_accounting"] == "chat_template_plus_wire_envelope_plus_output_and_safety"
    assert measured["context_required_tokens"] == measured["reserved_total_tokens"]
    assert not measured["context_fits"]


@pytest.mark.parametrize("extension", ["unknown_format", "tools"])
def test_incident_unknown_wire_shape_keeps_conservative_context(extension):
    policy = replace(load_policy(FILE).model, protocol="chat_completions", schema_profile="vllm_grammar_v1")
    body = incident_grammar_request(policy)
    if extension == "unknown_format":
        body["response_format"] = {"type": "json_object"}
    else:
        body["tools"] = []
    measured = measure_saved_counts(policy, body, "I", 1, policy.context_tokens)
    assert measured["context_accounting"] == "chat_template_plus_wire_envelope_plus_output_and_safety"
    assert measured["context_required_tokens"] == measured["reserved_total_tokens"]
    assert not measured["context_fits"]


@pytest.mark.parametrize("override", [{"protocol": "other"}, {"schema_profile": "standard"}])
def test_incident_unverified_protocol_or_profile_keeps_conservative_context(override):
    policy = replace(load_policy(FILE).model, protocol="chat_completions", schema_profile="vllm_grammar_v1")
    policy = replace(policy, **override)
    measured = measure_saved_counts(policy, incident_grammar_request(policy), "I", 1, policy.context_tokens)
    assert measured["context_accounting"] == "chat_template_plus_wire_envelope_plus_output_and_safety"
    assert measured["context_required_tokens"] == measured["reserved_total_tokens"]
    assert not measured["context_fits"]
