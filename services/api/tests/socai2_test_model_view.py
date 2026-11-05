"""Decode actual versioned requests for model substitutes and field assertions."""
import json

from app.socai2.model_input_view import frozen_items, items


def model_data(content):
    data = json.loads(content)
    if "source_groups" in data:
        data["items"] = items(data)
        data.pop("source_groups")
    elif "frozen_source_groups" in data:
        data["items"] = frozen_items(data)
        data.pop("frozen_source_groups")
    return data
