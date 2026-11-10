"""Tenant model adapter and budget accounting; never persist credentials."""
import os

import httpx

from app.core.airgap import enforce_airgap_for_url
from app.services.llm_resolver import resolve_llm_config
from app.services.llm_safety import safe_chat_completions_request
from app.services.model_aliases import completions_url_for_base

from .model_errors import ModelCallError, provider_error
from .model_protocol import (
    DEEPSEEK_BASE,
    DEEPSEEK_PROTOCOL,
    SCHEMA_PROFILES,
    complete_deepseek,
)


class TenantChatGateway:
    provider = "chat_completions"
    schema_profile = "standard"
    model = "unresolved"

    async def configure(self, service, tenant_id):
        async with service.transaction(tenant_id) as store:
            self.config = await resolve_llm_config(store.db, tenant_id)
        self.model = self.config.model
        self.provider = os.getenv("SOCAI2_MODEL_PROTOCOL", "chat_completions")
        self.schema_profile = os.getenv("SOCAI2_MODEL_SCHEMA_PROFILE", "standard")
        if self.schema_profile not in SCHEMA_PROFILES:
            return False
        if self.provider not in {"chat_completions", DEEPSEEK_PROTOCOL}:
            return False
        if self.provider == DEEPSEEK_PROTOCOL and (
                self.config.base_url.rstrip("/") != DEEPSEEK_BASE or self.model != "deepseek-flash"):
            return False
        return bool(self.config.allowed and self.config.api_key)

    async def complete(self, body, timeout):
        from .runtime_policy import active_policy
        timeout = min(timeout, active_policy().single_model_timeout_seconds)
        if timeout <= 0:
            raise TimeoutError("baseline_analysis_deadline_elapsed")
        try:
            if self.provider == DEEPSEEK_PROTOCOL:
                return await complete_deepseek(self.config, body, timeout)
            url = completions_url_for_base(self.config.base_url)
            enforce_airgap_for_url(url)
            return await safe_chat_completions_request(api_key=self.config.api_key, url=url,
                model=body["model"], messages=body["messages"], timeout=timeout,
                max_tokens=body["max_tokens"], response_format=body["response_format"],
                **({"temperature": body["temperature"]} if "temperature" in body else {}))
        except httpx.HTTPError as exc:
            raise ModelCallError(provider_error(exc, self.config.api_key)) from None

    async def measure(self, body, stage):
        from .baseline_store import StoreError
        from .runtime_policy import active_policy
        from .token_budget import BackendTokenMeter
        policy = active_policy().model
        if (self.provider, self.schema_profile) != (policy.protocol, policy.schema_profile):
            raise StoreError("token_meter_protocol_profile_mismatch", 422)
        return await BackendTokenMeter(policy).measure(body, stage)


def usage(payload):
    raw = payload.get("usage") if isinstance(payload, dict) else None
    raw = raw if isinstance(raw, dict) else {}

    def count(value):
        return value if type(value) is int and value >= 0 else None

    responses = isinstance(payload, dict) and payload.get("object") == "response"
    keys = ("input_tokens", "output_tokens", "total_tokens") if responses else ("prompt_tokens", "completion_tokens", "total_tokens")
    prompt, completion, total = [count(raw.get(k)) for k in keys]
    known = prompt is not None and completion is not None
    if known and total is None:
        total = prompt + completion
    consistent = known and total == prompt + completion
    details_in = raw.get("input_tokens_details" if responses else "prompt_tokens_details") or {}
    details_out = raw.get("output_tokens_details" if responses else "completion_tokens_details") or {}
    request_id = payload.get("id") if isinstance(payload, dict) else None
    return {"input_tokens": prompt, "output_tokens": completion,
        "total_tokens": total, "cached_input_tokens": count(details_in.get("cached_tokens")) if isinstance(details_in, dict) else None,
        "reasoning_tokens": count(details_out.get("reasoning_tokens")) if isinstance(details_out, dict) else None,
        "cost": None, "currency": None, "price_version": None,
        "usage_state": "reported" if consistent else "partial" if any(v is not None for v in (prompt, completion, total)) else "unavailable",
        "cost_state": "unpriced", "request_id": request_id if isinstance(request_id, str) else None}
