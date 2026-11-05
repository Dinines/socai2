"""Lossless C3 capability grouping, separate from the bounded evidence view."""
from .baseline_store import encoded

SCHEMA = "socai2.c3-tool-catalog.v1"


def data(options):
    """Hoist only identical scope fields; preserve every option field and value."""
    groups, previous = [], None
    for option in options:
        scope = {key: option[key] for key in ("hostname", "alert_ids", "object_keys")}
        key = encoded(scope)
        if key != previous:
            groups.append({**scope, "options": []})
        groups[-1]["options"].append({key: value for key, value in option.items() if key not in scope})
        previous = key
    return {"schema_version": SCHEMA, "tool_option_groups": groups}


def message(options):
    return {"role": "user", "content": encoded(data(options)).decode("utf-8")}
