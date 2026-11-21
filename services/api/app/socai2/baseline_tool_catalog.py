"""Lossless C3 capability grouping, separate from the bounded evidence view."""
from .baseline_store import encoded
from .runtime_policy import active_policy

SCHEMA = "socai2.c3-tool-catalog.v2"


def capabilities(available_tools, *, lake_v2=False):
    from .baseline_evidence_tools import (
        FIELDS,
        LIMITATIONS,
        PRODUCT_FIELDS,
        PRODUCT_LIMITATIONS,
        TOOLS,
    )
    specs = active_policy().tools
    names = {*TOOLS, "product_host_details"}
    if set(specs) != names:
        raise ValueError("tool_description_contract_mismatch")
    lake_fields, lake_limits = FIELDS, LIMITATIONS
    if lake_v2:
        from .lake_queries import LIMITATIONS as SCOPED_LIMITATIONS
        lake_fields, lake_limits = (*FIELDS, "device_hostname", "device_ip"), SCOPED_LIMITATIONS
    return [{"tool_name": name, **specs[name],
        "returned_fields": list(PRODUCT_FIELDS if name == "product_host_details" else lake_fields),
        "limitations": PRODUCT_LIMITATIONS if name == "product_host_details" else lake_limits,
        "available": name in available_tools} for name in sorted(names)]


def data(options):
    """Hoist only identical scope fields; preserve every option field and value."""
    groups, previous = [], None
    for option in options:
        subject_key = "selector" if "selector" in option else "hostname"
        scope = {key: option[key] for key in (subject_key, "alert_ids", "object_keys")}
        key = encoded(scope)
        if key != previous:
            groups.append({**scope, "options": []})
        groups[-1]["options"].append({key: value for key, value in option.items() if key not in scope})
        previous = key
    lake_v2 = any("selector" in option for option in options)
    return {"schema_version": "socai2.c3-tool-catalog.v3" if lake_v2 else SCHEMA,
        "capabilities": capabilities({o["tool_name"] for o in options}, lake_v2=lake_v2), "tool_option_groups": groups,
        "selection_rule": "先确定调查方向和缺失证据，再选能回答该问题的工具及已有 binding_id。领域不是工具；多个对象候选可对应同一种工具。selector分别说明设备、源端点或目的端点及其主机名/IP；legacy_host角色未确认。没有可用候选时不执行；未查、查空、失败分别记录。"}


def message(options):
    return {"role": "user", "content": encoded(data(options)).decode("utf-8")}
