"""Read only this Run's verified frozen sources for configured followups."""
from datetime import datetime

from sqlalchemy import select

from .baseline_contracts import Limits
from .baseline_enrichment import S
from .baseline_store import F, StoreError, digest
from .case_followup_input import build


async def load(owner, tenant, case, run_id):
    async with owner.service.transaction(tenant) as store:
        run = await owner.locked(store, case, run_id)
        context = await store.read_context(case, run_id)
        base = await store.prepare_model_view(case, run_id, case_boundary=True)
        rows = (await store.db.execute(select(F).where(*store.where(F, F.c.run_id == run_id,
            F.c.content_json.is_not(None), F.c.kind.not_in(["model_request", "model_response"]))))).mappings().all()
        if any(digest(r["content_json"]) != r["sha256"] for r in rows):
            raise StoreError("followup_frozen_artifact_invalid", 422)
        artifacts = {str(r["id"]): dict(r) for r in rows}
        steps = (await store.db.execute(select(S).where(*store.where(S, S.c.run_id == run_id)))).mappings().all()
        now = await store.now()
    material = next((r["content_json"] for r in rows if r["content_json"].get("type") == "materials"), None)
    projections = [dict(r) for r in rows if r["content_json"].get("type") == "query_projection"]
    projections.sort(key=lambda r: (r["captured_at"], str(r["id"])))
    if projections and material is None:
        raise StoreError("followup_binding_catalog_missing", 422)
    return run, context, base, artifacts, material, projections, steps, now


def inputs(prepared, base, artifacts, prior_id):
    ids = [base["artifact_id"], *([str(prior_id)] if prior_id else [])]
    ids.extend(r["ref"]["id"] for r in prepared["source_map"].values()
               if r["ref"]["type"] == "artifact" and r["ref"]["id"] in artifacts)
    ids.extend(r["artifact_id"] for r in prepared["followup_boundary"]["query_facts"])
    prepared["input_artifact_ids"] = list(dict.fromkeys(ids))
    return prepared


async def deep(owner, tenant, case, run_id, question_id, previous, prior_id, lake):
    run, context, base, artifacts, material, projections, steps, now = await load(owner, tenant, case, run_id)
    if material is None:
        raise StoreError("followup_binding_catalog_missing", 422)
    limits = Limits.model_validate(run["limits"])
    used = sum(s["kind"] == "tool" and s["state"] not in {"planned", "skipped"} for s in steps)
    available = (lake.configured() and limits.max_tool_calls is not None and used < limits.max_tool_calls
        and limits.max_rows_per_query is not None and limits.max_rows_per_query > 0
        and limits.deadline_at is not None and (limits.deadline_at - now).total_seconds() >= 1)
    attempted = {s["name"] for s in steps if s["stage_code"] == "C4.query"}
    scope = context.scope.model_dump(mode="json")
    valid_window = (scope["window_start"] and scope["window_end"]
                    and datetime.fromisoformat(scope["window_start"]) < datetime.fromisoformat(scope["window_end"]))
    unavailable = getattr(lake, "unavailable_reason", None)
    options, mapping = [], {}
    for bid, binding in sorted(material["catalog"]["bindings"].items()):
        if (not available or bid in attempted or not valid_window and binding["tool_name"] != "product_host_details"
                or unavailable is not None and unavailable(binding) is not None):
            continue
        alias = "B" + str(len(options) + 1)
        mapping[alias] = bid
        options.append({"binding_id": alias, "tool_name": binding["tool_name"], "hostname": binding["hostname"],
                        "alert_ids": binding["alert_ids"], "object_keys": sorted({o["object_key"] for o in binding["objects"]})})
    prepared = build("Deep", context, base, artifacts, previous=previous, prior_id=prior_id,
        question_id=question_id, material=material, projections=projections, options=options, binding_map=mapping)
    return inputs(prepared, base, artifacts, prior_id)


def graph_candidates(bases, artifacts):
    snapshots = [r["content_json"] for r in bases if r["content_json"].get("type") == "graph_snapshot"]
    snapshot = max(snapshots, key=lambda r: r["captured_at"]) if snapshots else None
    current = {str(r["id"]) for r in bases if r["content_json"].get("type") in {"materials", "query_projection"}}
    state = "not_built" if snapshot is None else "available" if current <= set(snapshot["input_artifact_ids"]) else "stale"
    graphs = []
    if state == "available":
        from .baseline_context import reference
        graph_id = snapshot["graph_artifact_id"]
        graph = artifacts[graph_id]["content_json"]
        nodes = {n["id"]: n for n in graph["nodes"]}
        records = {eid: item for item in snapshot["records"] for eid in item["edge_ids"]}
        for i, edge in enumerate(graph["edges"]):
            record = records[edge["id"]]
            owners = record.get("related_alert_ids", [record["alert_id"]] if record.get("alert_id") else [])
            graphs.append({"original": [edge, nodes[edge["from"]], nodes[edge["to"]]],
                "entry": {"value": {"relation": edge["relation"], "strength": edge["strength"],
                    "from": nodes[edge["from"]]["label"], "to": nodes[edge["to"]]["label"],
                    "limitations": edge["limitations"] + graph["limitations"]}},
                "source": {"ref": reference("artifact", graph_id, "prior_analysis", f"$.edges.{i}"), "alert_ids": owners,
                           "membership_basis": record.get("membership_basis", "source_label")}})
    return state, graphs


async def final(owner, tenant, case, run_id, previous, prior_id, bases, extra, lead):
    _, context, base, artifacts, material, projections, _, _ = await load(owner, tenant, case, run_id)
    state, graphs = graph_candidates(bases, artifacts)
    prepared = build("C6", context, base, artifacts, previous=previous, prior_id=prior_id,
        material=material, projections=projections, extra={**extra, "graph_state": state}, lead=lead, graphs=graphs)
    return inputs(prepared, base, artifacts, prior_id)
