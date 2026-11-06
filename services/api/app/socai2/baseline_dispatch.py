"""Service-owned C3 choices and deterministic, separately deduplicated routing."""
from datetime import datetime

from .baseline_capacity import FINAL_SECONDS
from .baseline_evidence_tools import TOOLS
from .baseline_semantics import EVENT_KINDS
from .baseline_store import encoded


def ranked_bindings(catalog, members):
    observations = {}
    for aid, material in (members or {}).items():
        fields = material.get("fields", [])
        # Fusion projects device.name, then src_endpoint.hostname, into the
        # case-sensitive src_hostname column used by all three lake queries.
        device = next((f for f in fields if f.get("name") == "device_name"
            and (f.get("source_path") or "").endswith(".device.name")), None)
        host = device or next((f for f in fields if f.get("name") == "src_hostname"
            and (f.get("source_path") or "").endswith(".src_endpoint.hostname")), None)
        if host and host.get("conflict") is False and isinstance(host.get("value"), str):
            kind = next((f.get("value") for f in fields if f.get("name") == "event_kind"
                and f.get("conflict") is False), None)
            observations[aid] = (host["value"], kind)

    def rank(item):
        bid, binding = item
        host, tool = binding["hostname"], binding["tool_name"]
        matched = [observations[aid][1] for aid in binding["alert_ids"]
            if aid in observations and observations[aid][0] == host]
        event_kind = EVENT_KINDS.get(TOOLS.get(tool))
        return (-len(matched), -matched.count(event_kind) if event_kind else 0,
            -len(binding["alert_ids"]), host, tool, bid)

    return sorted(catalog["bindings"].items(), key=rank)


def offered_bindings(catalog, limits, now, steps, lake, *, members=None):
    options, mapping, excluded = [], {}, []
    used = sum(s["kind"] == "tool" and s["state"] not in {"planned", "skipped"} for s in steps)
    available = (lake.configured() and limits.max_tool_calls is not None and used < limits.max_tool_calls
        and limits.max_rows_per_query is not None and limits.max_rows_per_query > 0
        and limits.deadline_at is not None and (limits.deadline_at - now).total_seconds() > FINAL_SECONDS)
    for bid, binding in ranked_bindings(catalog, members):
        scope = binding["scope"]
        window = (scope["window_start"] and scope["window_end"]
            and datetime.fromisoformat(scope["window_start"]) < datetime.fromisoformat(scope["window_end"]))
        unavailable = getattr(lake, "unavailable_reason", lambda _: None)(binding)
        reason = ("source_or_remaining_budget_unavailable" if not available else unavailable
            or ("query_window_unavailable" if binding["tool_name"] != "product_host_details" and not window else None))
        if reason:
            excluded.append({"binding_id": bid, "reason": reason})
            continue
        alias = "B" + str(len(options) + 1)
        option = {"binding_id": alias, "tool_name": binding["tool_name"], "hostname": binding["hostname"],
            "alert_ids": binding["alert_ids"], "object_keys": sorted({o["object_key"] for o in binding["objects"]})}
        if len(encoded([*options, option])) > 1800:
            excluded.append({"binding_id": bid, "reason": "binding_catalog_input_limit"})
            continue
        options.append(option)
        mapping[alias] = {**binding, "binding_id": bid}
    return options, mapping, excluded


async def dispatch_followups(service, tenant_id, case_id, run_id, followups, bindings, *, gateway, lake):
    routes, by_binding, by_question = [], {}, {}
    ordered = sorted(enumerate(followups), key=lambda pair: (
        pair[1]["priority"] != "decision_critical", {"query": 0, "deep": 1}.get(pair[1]["mode"], 2), pair[0]))
    for order, (index, item) in enumerate(ordered):
        qid, mode = item["question_id"], item["mode"]
        route = {"followup_index": index, "execution_order": order, "question_id": qid,
            "mode": mode, "priority": item["priority"], "binding_id": item["binding_id"]}
        if mode == "human":
            route.update(state="handoff", reason="human_confirmation_required_no_task_created")
        elif mode == "graph":
            route.update(state="scheduled", reason="C5_retained_evidence_graph_only")
        elif mode == "query":
            bid = bindings[item["binding_id"]]["binding_id"]
            route["resolved_binding_id"] = bid
            route["reused"] = bid in by_binding
            if bid not in by_binding:
                result = await service.query_evidence(tenant_id, case_id, run_id, bid, qid, gateway=lake)
                # Deep and direct queries share the persisted binding ledger.
                # The first direct lookup may already reuse a Deep query.
                route["reused"] = result["reused"]
                receipt = result["result"]
                by_binding[bid] = {"state": receipt["state"], "reason": result["projection"].get("reason"),
                    "query_artifact_id": result["artifact_id"], "projection_id": result["projection_id"],
                    "answer_available": False}
            route.update(by_binding[bid])
        else:
            route["reused"] = qid in by_question
            if qid not in by_question:
                result = await service.deepen(tenant_id, case_id, run_id, qid, gateway=gateway, lake=lake)
                by_question[qid] = {"state": result["state"], "reason": result["stop_reason"],
                    "deep_artifact_id": result["deep_artifact_id"], "answer_available": result["answer"] is not None}
            route.update(by_question[qid])
        routes.append(route)
    return routes
