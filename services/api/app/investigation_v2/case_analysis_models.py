"""Chat-completions calls preserving the tool-call protocol's visible fields."""
import httpx

from app.core.airgap import enforce_airgap_for_url
from app.services import llm_health
from app.services.llm_safety import validate_messages
from app.services.model_aliases import completions_url_for_base


async def call_model(config, messages: list[dict], tools: list[dict]):
    # The shared validator checks content, but its returned normalization
    # omits tool_calls/tool_call_id. Keep those protocol fields explicitly.
    validate_messages(messages)
    visible = [{key: value for key, value in message.items()
                if key in {"role", "content", "tool_calls", "tool_call_id"}} for message in messages]
    url = completions_url_for_base(config.base_url)
    enforce_airgap_for_url(url)
    body = {"model": config.model, "messages": visible, "max_tokens": 1200}
    if tools:
        body["tools"] = tools
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {config.api_key}"}, json=body)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("invalid_model_response")
    except Exception as exc:
        llm_health.record_failure(type(exc).__name__)
        raise
    llm_health.record_success()
    return payload
