"""Measure the final model request with the selected backend's tokenizer."""

import asyncio
import logging

import httpx

from app.core.airgap import AirgapViolation, enforce_airgap_for_url
from app.core.operational_logging import log_exception

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


def context_admission(policy, body, stage, chat_tokens, envelope_tokens):
    """Separate declared server-side schema constraints from the prompt window."""
    response = body.get("response_format")
    tagged = response.get("format") if isinstance(response, dict) else None
    schema = response.get("json_schema") if isinstance(response, dict) else None
    grammar_format = isinstance(response, dict) and (
        (set(response) == {"type", "format"} and response["type"] == "structural_tag"
         and isinstance(tagged, dict) and set(tagged) == {"type", "json_schema", "max_whitespace_cnt"}
         and tagged["type"] == "json_schema" and isinstance(tagged["json_schema"], dict)
         and type(tagged["max_whitespace_cnt"]) is int and tagged["max_whitespace_cnt"] >= 0)
        or (set(response) == {"type", "json_schema"} and response["type"] == "json_schema"
            and isinstance(schema, dict) and set(schema) == {"name", "schema", "strict"}
            and isinstance(schema["name"], str) and bool(schema["name"].strip())
            and isinstance(schema["schema"], dict) and schema["strict"] is True)
    )
    messages = body.get("messages")
    # Only these text-chat shapes use the declared vLLM grammar capability.
    # Extra tool, template or multimodal fields can add unmeasured prompt tokens.
    grammar = (
        set(body) == {"model", "messages", "max_tokens", "temperature", "response_format"}
        and isinstance(messages, list) and bool(messages)
        and all(isinstance(message, dict) and set(message) == {"role", "content"}
                and isinstance(message["role"], str)
                and message["role"] in {"system", "user", "assistant"}
                and isinstance(message["content"], str) for message in messages)
        and grammar_format
    )
    prompt_only = (policy.protocol == "chat_completions"
                   and policy.schema_profile == "vllm_grammar_v1" and grammar)
    input_tokens = chat_tokens + policy.tokenizer["safety_tokens"]
    if not prompt_only:
        input_tokens += envelope_tokens
    required = input_tokens + policy.output_tokens[stage]
    return {
        "context_accounting": "chat_template_plus_output_and_safety" if prompt_only
            else "chat_template_plus_wire_envelope_plus_output_and_safety",
        "context_input_tokens": input_tokens,
        "context_required_tokens": required,
        "context_fits": required <= policy.context_tokens,
    }


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
            log_exception(logging.getLogger(__name__), "token_meter_call_failed", extra={
                "operation": "measure_tokens", "stage": stage, "dependency": "tokenizer_http",
                "error_code": "token_meter_unavailable"})
            raise StoreError("token_meter_unavailable", 503) from None
        estimated_input = sum(counts) + config["safety_tokens"]
        total = estimated_input + policy.output_tokens[stage]
        return {"schema_version": "socai2.token-measurement.v1", "method": "backend_chat_template_plus_wire_envelope",
            "model": policy.alias, "served_model": config["served_model"], "body_sha256": digest(body),
            "chat_tokens": counts[0], "envelope_tokens": counts[1], "safety_tokens": config["safety_tokens"],
            "reserved_input_tokens": estimated_input, "output_tokens": policy.output_tokens[stage],
            "reserved_total_tokens": total, "context_tokens": policy.context_tokens,
            **context_admission(policy, body, stage, *counts), "wire_bytes": len(encoded(body)),
            "limitations": ["envelope_is_conservative_extra_input_not_provider_reported_usage"]}
