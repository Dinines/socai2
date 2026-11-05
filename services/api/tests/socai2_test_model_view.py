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
        if catalog.get("schema_version") == "socai2.c3-tool-catalog.v1":
            data["tool_options"] = [{**{key: group[key] for key in ("hostname", "alert_ids", "object_keys")}, **option}
                for group in catalog["tool_option_groups"] for option in group["options"]]
    return data
