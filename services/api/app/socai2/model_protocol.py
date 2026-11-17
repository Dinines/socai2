"""Explicit provider wire format for the isolated investigation chain."""
from copy import deepcopy

import httpx

from app.core.airgap import enforce_airgap_for_url
from app.services import llm_health
from app.services.llm_safety import LLMInputContract

DEEPSEEK_PROTOCOL = "deepseek_responses"
DEEPSEEK_BASE = "https://api.deepseek.com"
SCHEMA_PROFILES = {"standard", "vllm_grammar_v1"}


def deepseek_schema(schema):
    """Expose each anyOf branch's type; keep all canonical constraints.

    m3 proved that a bare $ref in anyOf is rejected before inference. Object
    type arrays are also rejected, so retain anyOf and inline only its refs.
    Ordinary property/item refs stay shared to avoid needless schema growth.
    """
    output = deepcopy(schema)
    definitions = schema.get("$defs", {})

    def visit(node, resolving=()):
        if isinstance(node, list):
            return [visit(child, resolving) for child in node]
        if not isinstance(node, dict):
            return node
        result = {}
        for key, value in node.items():
            if key != "anyOf":
                result[key] = visit(value, resolving)
                continue
            branches = []
            for branch in value:
                seen = resolving
                while isinstance(branch, dict) and "$ref" in branch:
                    ref = branch["$ref"]
                    if set(branch) != {"$ref"}:
                        raise ValueError("deepseek_union_ref_siblings_unsupported")
                    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
                        raise ValueError("deepseek_union_ref_not_local")
                    name = ref.removeprefix("#/$defs/").replace("~1", "/").replace("~0", "~")
                    if ref in seen:
                        raise ValueError("deepseek_union_ref_cycle")
                    if name not in definitions:
                        raise ValueError("deepseek_union_ref_missing")
                    seen = (*seen, ref)
                    branch = definitions[name]
                branches.append(visit(branch, seen))
            result[key] = branches
        return result

    return visit(output)


def provider_schema(body, profile):
    """Explicit wire capability, not a retry or a weaker local result contract."""
    if profile not in SCHEMA_PROFILES:
        raise ValueError("unknown_model_schema_profile")
    if profile == "standard":
        return body
    output = deepcopy(body)

    def visit(node):
        if not isinstance(node, dict):
            return
        # xgrammar 0.2.8 treats pattern as a full match: \S permits one
        # character, not a nonblank sentence. Its length grammar also rejects
        # escaped quotes/newlines. Keep these checks in the canonical parser.
        if (node.get("type") == "string" and "enum" not in node and "const" not in node
                and node.get("pattern") in (None, r"\S")):
            for key in ("minLength", "maxLength"):
                node.pop(key, None)
            if node.get("pattern") == r"\S":
                node.pop("pattern")
        # Duplicate IDs remain errors in every local contract parser.
        node.pop("uniqueItems", None)
        # Visit schema positions only: properties and literal data may use
        # the same names as schema keywords without being constraints.
        for key in ("$defs", "definitions", "properties", "patternProperties", "dependentSchemas"):
            for child in node.get(key, {}).values():
                visit(child)
        for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
            for child in node.get(key, []):
                visit(child)
        for key in ("items", "additionalItems", "contains", "additionalProperties",
                    "unevaluatedItems", "unevaluatedProperties", "propertyNames", "not", "if", "then", "else"):
            child = node.get(key)
            for schema in child if isinstance(child, list) else (child,):
                visit(schema)

    visit(output["response_format"]["json_schema"]["schema"])
    return output


def prepare_request(gateway, body):
    """Convert before accounting/persistence; the saved body is sent unchanged."""
    body = provider_schema(body, getattr(gateway, "schema_profile", "standard"))
    if getattr(gateway, "provider", "chat_completions") != DEEPSEEK_PROTOCOL:
        return body
    fmt = body["response_format"]
    if fmt["type"] != "json_schema":
        raise ValueError("deepseek_requires_structured_schema")
    wire_format = deepcopy(fmt["json_schema"])
    wire_format["schema"] = deepseek_schema(wire_format["schema"])
    return {"model": body["model"], "input": deepcopy(body["messages"]),
        "text": {"format": {"type": "json_schema", **wire_format}},
        "max_output_tokens": body["max_tokens"], "temperature": body["temperature"],
        "reasoning": {"effort": "none"}, "stream": False, "store": False}


async def complete_deepseek(config, body, timeout):
    if config.base_url.rstrip("/") != DEEPSEEK_BASE or config.model != "deepseek-flash":
        raise ValueError("deepseek_endpoint_or_model_mismatch")
    url = DEEPSEEK_BASE + "/responses"
    enforce_airgap_for_url(url)
    if LLMInputContract.validate(body["input"]) != body["input"]:
        raise ValueError("recorded_model_input_must_not_change")
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(url, headers={"Authorization": "Bearer " + config.api_key}, json=body)
            response.raise_for_status()
            result = dict(response.json())
    except Exception as exc:
        llm_health.record_failure(type(exc).__name__)
        raise
    llm_health.record_success()
    return result  # Keep the original provider object, including usage and status.


def response_choices(payload):
    """Parser view only; never replace/mutate the raw response artifact."""
    if payload.get("object") != "response":
        return payload.get("choices")
    output = payload.get("output")
    if not isinstance(output, list) or any(not isinstance(item, dict) for item in output):
        return []
    if any(item.get("type") not in {"message", "reasoning"} for item in output):
        return []  # No provider-side tools or hidden source retrieval are authorized.
    messages = [item for item in output if item.get("type") == "message"]
    if len(messages) != 1 or messages[0].get("role") != "assistant":
        return []
    message = messages[0]
    content = message.get("content")
    if not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict):
        return []
    part = content[0]
    if part.get("type") != "output_text" or not isinstance(part.get("text"), str):
        return []
    complete = payload.get("status") == "completed" and message.get("status") == "completed"
    return [{"finish_reason": "stop" if complete else "incomplete",
        "message": {"content": part["text"], "refusal": payload.get("error")}}]


def response_content_path(payload):
    """Original location of the already validated single text message."""
    if payload.get("object") == "response":
        index = next(i for i, item in enumerate(payload["output"]) if item.get("type") == "message")
        return f"$.raw.output[{index}].content[0].text"
    return "$.raw.choices[0].message.content"
