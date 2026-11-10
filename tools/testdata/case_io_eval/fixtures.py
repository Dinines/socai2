"""Resolve immutable saved sources, never query a database or create a Case."""
import copy
import hashlib
import json

from app.socai2.baseline_store import digest
from app.socai2.incident_query_receipts import receipts
from app.socai2.stage_inputs import QUERY_RECEIPTS_VERSION


def load(root, config):
    raw = (root / config["snapshot"]).read_bytes()
    data = json.loads(raw)
    artifacts = {a["id"]: a for a in data["artifacts"]}
    steps = {s["id"]: s for s in data["run_steps"]}
    run = next(r for r in data["runs"] if r["id"] == config["source_run_id"])
    if run["kind"] != "baseline":
        raise ValueError("not_a_baseline_run")
    requests = [a for a in artifacts.values() if a["run_id"] == run["id"] and a["kind"] == "model_request"
                and steps[a["step_id"]]["stage_code"] == "C3"]
    if len(requests) != 1:
        raise ValueError("expected_one_saved_c3_request")
    request = requests[0]["content_json"]["payload"]
    context_ids = {v["ref"]["id"] for v in request["source_map"].values()
                   if v["ref"]["type"] == "artifact" and v["ref"]["id"] in artifacts
                   and (artifacts[v["ref"]["id"]].get("content_json") or {}).get("schema_version") == "socai2.baseline-context.v1"}
    if len(context_ids) != 1:
        raise ValueError("ambiguous_frozen_context")
    context_id = context_ids.pop()
    artifact = artifacts[context_id]
    context = artifact["content_json"]
    if artifact["run_id"] != run["id"] or artifact["tenant_id"] != run["tenant_id"] or digest(context) != artifact["sha256"]:
        raise ValueError("context_identity_or_digest_invalid")
    materials = {}
    for aid, row in context["alerts"].items():
        frozen = row.get("material")
        if frozen is None:
            continue
        matches = [m for m in data["alert_materials"] if m["id"] == frozen["id"]]
        if len(matches) != 1:
            raise ValueError("frozen_material_missing")
        material = matches[0]
        if (material["alert_id"] != aid or material["tenant_id"] != run["tenant_id"]
                or any(material[k] != frozen[k] for k in ("revision", "sha256", "material_state"))):
            raise ValueError("frozen_material_pairing_invalid")
        materials[aid] = material
    # A supplementary OFFLINE snapshot; do not pretend old C1 froze these rows.
    query_source = {"query_receipts_version": QUERY_RECEIPTS_VERSION, "members": [],
                    "triage_validation": {}, "triage_queries": {}}
    for aid, row in context["alerts"].items():
        query_source["members"].append({"alert": row["alert"], "triage": row["triage"]})
        triage = row.get("triage")
        if not triage or row.get("triage_usable") is not True or row.get("triage_freshness") != "current":
            continue
        query_source["triage_validation"][aid] = {"usable": True, "triage_id": triage["id"],
                                                   "source_run_id": triage["source_run_id"]}
        query_source["triage_queries"][aid] = [a for a in artifacts.values() if a["kind"] == "tool_response"
            and a["run_id"] == triage["source_run_id"] and a["alert_id"] == aid and a["tenant_id"] == run["tenant_id"]]
    verified = receipts(query_source)
    response_id = steps[requests[0]["step_id"]]["output_artifact_id"]
    response = artifacts[response_id]["content_json"]["payload"]
    return copy.deepcopy({"context": context, "context_id": context_id, "run": run,
        "materials": materials, "request": request, "data": json.loads(request["body"]["messages"][1]["content"]),
        "answer": json.loads(response["raw"]["choices"][0]["message"]["content"]),
        "query_source": query_source, "verified_queries": verified,
        "snapshot_sha256": hashlib.sha256(raw).hexdigest()})
