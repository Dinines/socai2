"""Full-wire accounting includes schema and chat template; no generated answers."""

import asyncio
import json
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
