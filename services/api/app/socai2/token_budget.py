"""Measure the final model request with the selected backend's tokenizer."""

import asyncio

import httpx

from app.core.airgap import AirgapViolation, enforce_airgap_for_url

from .baseline_store import StoreError, digest, encoded


async def measure_with_deadline(gateway, body, stage, remaining_seconds):
    if remaining_seconds <= 0:
        raise StoreError("token_measurement_deadline_reached", 422)
    try:
        async with asyncio.timeout(remaining_seconds):
            return await gateway.measure(body, stage)
    except TimeoutError:
        # Tokenization never starts generation. A timed-out count is a known
        # pre-dispatch stop, not an unknown model call or an automatic retry.
        raise StoreError("token_measurement_deadline_reached", 422) from None


class BackendTokenMeter:
    def __init__(self, policy, *, transport=None):
        self.policy, self.transport = policy, transport

    async def measure(self, body, stage):
        policy = self.policy
        if body.get("model") != policy.alias or "messages" not in body or stage not in policy.output_tokens:
            raise StoreError("token_meter_model_profile_mismatch", 422)
        if body.get("max_tokens") != policy.output_tokens[stage]:
            raise StoreError("token_meter_output_profile_mismatch", 422)
        config = policy.tokenizer
        try:
            enforce_airgap_for_url(config["endpoint"])
        except AirgapViolation:
            raise StoreError("token_meter_endpoint_disallowed", 503) from None
        common = {"model": config["served_model"], "add_special_tokens": False, "return_token_strs": False}
        # Chat count includes the backend template; the envelope conservatively
        # includes the output schema and every non-message wire field. Provider
        # usage remains the final actual count, recorded separately on response.
        requests = [{**common, "messages": body["messages"], "add_generation_prompt": True},
                    {**common, "prompt": encoded({k: v for k, v in body.items() if k != "messages"}).decode()}]
        counts = []
        try:
            async with httpx.AsyncClient(timeout=config["timeout_seconds"], transport=self.transport, trust_env=False) as client:
                for request in requests:
                    response = await client.post(config["endpoint"], json=request)
                    response.raise_for_status()
                    value = response.json()
                    if (not isinstance(value, dict) or type(value.get("count")) is not int or value["count"] < 0
                            or type(value.get("max_model_len")) is not int or value["max_model_len"] != policy.context_tokens):
                        raise StoreError("token_meter_capacity_or_response_mismatch", 503)
                    counts.append(value["count"])
        except (httpx.HTTPError, ValueError):
            raise StoreError("token_meter_unavailable", 503) from None
        estimated_input = sum(counts) + config["safety_tokens"]
        total = estimated_input + policy.output_tokens[stage]
        return {"schema_version": "socai2.token-measurement.v1", "method": "backend_chat_template_plus_wire_envelope",
            "model": policy.alias, "served_model": config["served_model"], "body_sha256": digest(body),
            "chat_tokens": counts[0], "envelope_tokens": counts[1], "safety_tokens": config["safety_tokens"],
            "reserved_input_tokens": estimated_input, "output_tokens": policy.output_tokens[stage],
            "reserved_total_tokens": total, "context_tokens": policy.context_tokens,
            "context_fits": total <= policy.context_tokens, "wire_bytes": len(encoded(body)),
            "limitations": ["envelope_is_conservative_extra_input_not_provider_reported_usage"]}
