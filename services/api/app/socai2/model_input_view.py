"""Lossless grouping of model-visible fields; original references stay in the ledger."""
from .baseline_context import QUESTIONS
from .baseline_store import digest, encoded

SCHEMA = "socai2.grouped-model-input.v3"
LIMITATIONS = ["selected_fields_not_full_raw_review", "sent_fields_do_not_prove_model_analysis"]


def source_prefix(originals):
    """Choose a current-only namespace absent from all received text.

    History and literal names are never rewritten. The prefix is local to this
    request; exact immutable source references remain the durable identity.
    """
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, child in value.items():
                yield from strings(key)
                yield from strings(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                yield from strings(child)
    # Tool identities may be UUID objects before persistence. Only received
    # text can contain this prefix; no serialization/coercion is needed here.
    text = "\0".join(strings(originals))
    index = 1
    while f"N{index}_" in text:
        index += 1
    return f"N{index}_"


def compact(data):
    """Only hoist repeated metadata. Values, field names and IDs are untouched."""
    groups = {}
    for item in data["items"]:
        header = {k: item[k] for k in ("alert_ids", "role", "origin", "membership_basis", "limitations") if k in item}
        group = groups.setdefault(encoded(header), {**header, "items": []})
        group["items"].append({k: v for k, v in item.items() if k not in header})
    output = {**{k: v for k, v in data.items() if k not in {"items", "omission_details",
        "omission_detail_count", "omission_details_truncated"}},
        "view_schema": SCHEMA, "source_groups": list(groups.values())}
    if "questions" in output:
        fixed = {identity: (question, [requirement]) for identity, question, requirement in QUESTIONS}
        # These six server-owned evidence rules are already stated in SYSTEM /
        # the stage prompt. Preserve changed/custom questions in full.
        output["questions"] = [{k: v for k, v in q.items() if k != "evidence_requirements"}
            if fixed.get(q.get("id")) == (q.get("text"), q.get("evidence_requirements")) else q
            for q in output["questions"]]
    return output


def items(data):
    """Read both immutable legacy flat views and the versioned grouped wire view."""
    if "items" in data:
        return data["items"]
    result = [{**{k: v for k, v in group.items() if k != "items"}, **item}
        for group in data.get("source_groups", []) for item in group["items"]]
    return sorted(result, key=lambda i: (i["id"].rsplit("_", 1)[-1][0], int(i["id"].rsplit("_", 1)[-1][1:])))


def queries(data):
    """Expand C6's explicitly shared query context; legacy views are unchanged."""
    context = data.get("query_context", {})
    shared = {key: value for key, value in context.items() if key != "applies_to"} if context.get("applies_to") == "queries" else {}
    return [{**shared, **query} for query in data.get("queries", [])]


def size(data):
    return len(encoded(compact(data)))


def compact_frozen(data):
    """Compact the persisted C preparation view while keeping every full reference."""
    groups = {}
    for item in data["items"]:
        header = {k: v for k, v in item["source"].items() if k != "source_path"}
        group = groups.setdefault(encoded(header), {"source": header, "items": []})
        group["items"].append({"source_path": item["source"]["source_path"],
            **{k: v for k, v in item.items() if k != "source"}})
    return {**{k: v for k, v in data.items() if k != "items"}, "frozen_source_groups": list(groups.values())}


def frozen_items(data):
    if "items" in data:
        return data["items"]
    return [{"source": {**group["source"], "source_path": item["source_path"]},
        **{k: v for k, v in item.items() if k != "source_path"}}
        for group in data.get("frozen_source_groups", []) for item in group["items"]]


def source_members(context, ref, tool_payloads):
    path = (ref.get("source_path") or "").split(".")
    members = set(context.alerts)
    if ref.get("type") == "alert_material":
        return sorted(aid for aid, alert in context.alerts.items()
                      if alert.material and str(alert.material["id"]) == str(ref["id"]))
    if len(path) > 2 and path[1] == "alerts":
        return sorted(members & {path[2]})
    if len(path) > 2 and path[1] == "incidents":
        return list(map(str, context.incidents[path[2]].case_member_ids))
    if len(path) > 2 and path[1] in {"tasks", "adopted_task_revisions"}:
        revision = (context.tasks[path[2]].revision if path[1] == "tasks"
                    else context.adopted_task_revisions[path[2]])
        return sorted(members & set((revision.get("result_scope") or {}).get("alert_ids", [])))
    if len(path) > 2 and path[1] == "prior_results":
        return sorted(members & {d["alert_id"] for d in context.prior_results[path[2]].get("member_deliveries", [])})
    if len(path) > 1 and path[1] == "current_assessment":
        return sorted(members & {m["alert_id"] for m in context.assessment_members})
    if len(path) > 2 and path[1] == "rows":
        payload = tool_payloads[ref["id"]]
        row = payload["rows"][int(path[2])]
        keys = payload["actual_args"]["parameters"]["selectors"]
        return sorted(members & {aid for k in keys if k["object_key"] == row["object_key"]
            and k["namespace"] == row["namespace"] for aid in k["alert_ids"]})
    return sorted(members) if path == ["$", "case"] else []


def case_model_data(data, context, tool_payloads):
    """One projection for C preparation capacity and the actual C3 wire input."""
    source_map, visible = {}, []
    prefix = source_prefix([context.model_dump(mode="json"), tool_payloads])
    for index, item in enumerate(frozen_items(data), 1):
        sid = f"{prefix}S{index}"
        owned = source_members(context, item["source"], tool_payloads)
        source_map[sid] = {"ref": item["source"], "alert_ids": owned,
            "visible_value_sha256": digest(item["value"]), "required": item.get("required", False)}
        visible.append({"id": sid, "role": item["source"]["role"], "alert_ids": owned,
            "value": item["value"], "limitations": item["limitations"]})
    return compact({**{k: v for k, v in data.items() if k not in {"items", "frozen_source_groups"}},
        "items": visible}), source_map
