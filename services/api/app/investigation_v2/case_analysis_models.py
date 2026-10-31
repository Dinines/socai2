"""Chat-completions calls preserving the tool-call protocol's visible fields."""
import httpx

from app.core.airgap import enforce_airgap_for_url
from app.services import llm_health
from app.services.llm_safety import validate_messages
from app.services.model_aliases import completions_url_for_base

MAX_OUTPUT_TOKENS = 3000


def conclusion_format(schema: dict, evidence_ids: list[str], member_ids: list[str], read_member_ids=None):
    def strict(value):
        if isinstance(value, list):
            return [strict(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: strict(item) for key, item in value.items() if key not in {"default", "title"}}
        if result.get("type") == "object":
            result.update(additionalProperties=False, required=list(result.get("properties", {})))
        return result

    output = strict(schema)
    readable = member_ids if read_member_ids is None else read_member_ids
    output["properties"]["member_assessments"].update(minItems=len(readable), maxItems=len(readable))
    for definition in output.get("$defs", {}).values():
        properties = definition.get("properties", {})
        if "evidence_ids" in properties and evidence_ids:
            properties["evidence_ids"]["items"]["enum"] = evidence_ids
        if "alert_id" in properties:
            properties["alert_id"]["enum"] = readable or member_ids
        if "alert_ids" in properties:
            properties["alert_ids"]["items"]["enum"] = member_ids
    return {"type": "json_schema", "json_schema": {
        "name": "case_analysis_conclusion", "strict": True, "schema": output}}


async def call_model(config, messages: list[dict], tools: list[dict], *, response_format=None, tool_choice=None):
    # The shared validator checks content, but its returned normalization
    # omits tool_calls/tool_call_id. Keep those protocol fields explicitly.
    validate_messages(messages)
    visible = [{key: value for key, value in message.items()
                if key in {"role", "content", "tool_calls", "tool_call_id"}} for message in messages]
    url = completions_url_for_base(config.base_url)
    enforce_airgap_for_url(url)
    body = {"model": config.model, "messages": visible, "max_tokens": MAX_OUTPUT_TOKENS}
    if tools:
        body["tools"] = tools
    if response_format is not None:
        body["response_format"] = response_format
    if tool_choice is not None:
        body["tool_choice"] = tool_choice
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10)) as client:
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
