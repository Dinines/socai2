"""Decode actual versioned requests for model substitutes and field assertions."""
import json

from app.socai2.model_input_view import frozen_items, items, queries


def model_data(content):
    data = json.loads(content)
    if "source_groups" in data:
        data["items"] = items(data)
        data.pop("source_groups")
    elif "frozen_source_groups" in data:
        data["items"] = frozen_items(data)
        data.pop("frozen_source_groups")
    if "query_context" in data:
        data["queries"] = queries(data)
    return data


def model_messages_data(messages):
    """Decode separate C3 capability data; legacy two-message inputs still work."""
    data = model_data(messages[1]["content"])
    for message in messages[2:]:
        catalog = json.loads(message["content"])
        if catalog.get("schema_version") in {"socai2.c3-tool-catalog.v1", "socai2.c3-tool-catalog.v2"}:
            data["tool_options"] = [{**{key: group[key] for key in ("hostname", "alert_ids", "object_keys")}, **option}
                for group in catalog["tool_option_groups"] for option in group["options"]]
    return data


async def synthetic_measure(body, stage):
    """Explicit counter substitute for DB tests, never a production fallback."""
    from app.socai2.baseline_store import digest, encoded
    from app.socai2.runtime_policy import active_policy
    model = active_policy().model
    reserved = 2000 + model.output_tokens[stage]
    return {"method": "explicit_test_substitute_not_backend_measurement", "body_sha256": digest(body),
        "wire_bytes": len(encoded(body)), "reserved_input_tokens": 2000,
        "reserved_total_tokens": reserved, "context_fits": reserved <= model.context_tokens,
        "context_tokens": model.context_tokens}
