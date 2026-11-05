"""Offline C6 reconstruction from sealed c originals; no DB/model or adoption."""
import asyncio
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))

from app.socai2.baseline_analysis import budget_reason
from app.socai2.baseline_capacity import final_wire_reason
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_delivery_contract import Delivery
from app.socai2.baseline_store import digest, encoded
from app.socai2.model_input_view import items, queries
from app.socai2.model_protocol import prepare_request
from app.socai2.structured_output import response_format
from diagnose_socai2_kafka_inputs_20261105 import one
from pydantic import ValidationError
from rebuild_socai2_followup_wire_20261105 import rebuild

BATCH = ROOT / ".local/local-investigation/validation/local-maintenance-20261105c"
DATABASE = BATCH / "exports/20261105T110746110174Z/database.json"
OUTPUT = ROOT / "docs/operations/evidence/investigation-repair-20261105/final-query-projection-20261105.json"
SOURCES = ["services/api/app/socai2/" + name for name in (
    "baseline_final_evidence.py", "baseline_reanalysis.py", "baseline_reasoning.py", "model_input_view.py",
    "baseline_delivery_contract.py", "model_protocol.py", "structured_output.py")]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(ref):
    return encoded(ref)


async def main():
    database_hash, plan_hash = sha(DATABASE), sha(BATCH / "plan.json")
    db = json.loads(DATABASE.read_text())
    run = next(r for r in db["runs"] if r["kind"] == "baseline")
    artifacts = [a for a in db["artifacts"] if a["run_id"] == run["id"]]
    assert all(digest(a["content_json"]) == a["sha256"] for a in artifacts if a["content_json"] is not None)
    by_id = {a["id"]: a for a in artifacts}
    steps = [s for s in db["run_steps"] if s["run_id"] == run["id"]]
    c6 = next(s for s in steps if s["kind"] == "model" and s["stage_code"] == "C6")
    old_request = by_id[c6["input_artifact_id"]]["content_json"]["payload"]
    old_body, old_map = old_request["body"], old_request["source_map"]
    original_response = by_id[c6["output_artifact_id"]]["content_json"]["payload"]["raw"]
    response_value = json.loads(original_response["output"][0]["content"][0]["text"])
    try:
        Delivery.model_validate(response_value)
    except ValidationError as exc:
        old_errors = [{"path": list(e["loc"]), "type": e["type"]} for e in exc.errors(include_input=False)]
    else:
        raise AssertionError("sealed original response unexpectedly accepted")
    assert old_errors == [{"path": ["analysis", "conflicts_note"], "type": "extra_forbidden"}]
    result = await one(db, run)
    prepared = result["prepared"]
    assert prepared["ready"], prepared["reason"]
    assert all(not r["omitted"] for r in result["required"])
    data = json.loads(prepared["messages"][1]["content"])
    context = Context.model_validate(next(a["content_json"] for a in artifacts
        if a["schema_version"] == "socai2.baseline-context.v1"))
    body = prepare_request(SimpleNamespace(provider="deepseek_responses", schema_profile="standard"), {
        "model": old_body["model"], "messages": prepared["messages"], "max_tokens": 3000, "temperature": 0,
        "response_format": response_format(Delivery, prepared["source_map"], members=context.alerts,
            questions=[q.id for q in context.questions], objects=context.scope.object_keys)})
    old_schema, new_schema = copy.deepcopy(old_body["text"]), copy.deepcopy(body["text"])
    old_schema["format"]["schema"]["$defs"]["SourceId"]["enum"] = []
    new_schema["format"]["schema"]["$defs"]["SourceId"]["enum"] = []
    assert old_schema == new_schema  # only this request's source IDs change
    old_required = {(key(s["ref"]), s["visible_value_sha256"]) for s in old_map.values() if s.get("required")}
    now_visible = {(key(s["ref"]), s["visible_value_sha256"]) for s in prepared["source_map"].values()}
    assert old_required <= now_visible and len(old_required) == 22 and result["required_count"] == 25
    receipts = queries(data)
    # Every inherited field reconstructs to the saved original query metadata.
    before_queries = json.loads(old_body["input"][1]["content"])["queries"]
    assert [{k: v for k, v in q.items() if k not in {"projected_fields", "visible_fields", "view_state"}}
        for q in receipts] == before_queries
    visible, omitted = {}, {key(o["ref"]): o["reason"] for o in prepared["omissions"]}
    for item in items(data):
        source = prepared["source_map"][item["id"]]
        if source.get("membership_basis") != "query_binding_only":
            continue
        ref = source["ref"]
        projection = by_id[ref["id"]]["content_json"]
        bits = ref["source_path"].split(".")
        field = projection["rows"][int(bits[2])]["semantics"]["fields"][int(bits[-1])]
        assert {k: v for k, v in item["value"].items() if k != "record_key"} == field
        assert ref["role"] == item["role"] == "observation" and source["required"]
        visible[key(ref)] = {"ref": ref, "field": field, "membership_basis": source["membership_basis"]}
    assert {v["field"]["name"] for v in visible.values()} == {"process_command_line", "dest_ip", "dst_port"}
    assert len(visible) == 3 and all(q["view_state"] == "partial" for q in receipts)
    field_inventory = []
    for candidate in result["captured"]["candidates"]:
        if candidate["source"]["ref"]["id"] not in {q["artifact_id"] for q in receipts}:
            continue
        ref = candidate["source"]["ref"]
        field = candidate["entry"]["value"]
        assert key(ref) in visible or key(ref) in omitted
        field_inventory.append({"ref": ref, "name": field["name"], "field_sha256": digest(field),
            "conflict": field["conflict"], "required": candidate.get("required", False),
            "visible": key(ref) in visible, "omission_reason": omitted.get(key(ref))})
    c4 = next(a["content_json"] for a in artifacts if (a.get("content_json") or {}).get("type") == "model_view"
        and any(s["ref"]["id"] in {q["artifact_id"] for q in receipts} for s in a["content_json"]["source_map"].values()))
    c4_nine = [s["ref"] for s in c4["source_map"].values() if s["ref"]["id"] in {q["artifact_id"] for q in receipts}]
    assert len(c4_nine) == 9
    prior_steps = [s for s in steps if s["seq"] < c6["seq"]]
    used = sum(s["usage"]["total_tokens"] for s in prior_steps if s["kind"] == "model" and s["state"] not in {"planned", "skipped"})
    assert used == 7738
    budget = budget_reason(prior_steps, Limits.model_validate(run["limits"]), len(encoded(body)), datetime.fromisoformat(c6["started_at"]))
    reserved = final_wire_reason(body, old_request["final_reservation"])
    assert budget is None and reserved is None
    assert prepared["bytes"] <= 8192 and len(encoded(prepared["messages"])) <= 12288
    old_packet = await rebuild()
    assert not old_packet["fits"] and old_packet["byte_limit"] == 17744
    assert sha(DATABASE) == database_hash and sha(BATCH / "plan.json") == plan_hash
    report = {"kind": "offline_final_query_projection_replay_not_model_validation_or_adoption",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": ".local/conda-envs/socai2/bin/python docs/operations/measure_socai2_final_query_projection_20261105.py",
        "database": {"path": str(DATABASE.relative_to(ROOT)), "sha256_before": database_hash, "sha256_after": sha(DATABASE)},
        "plan_sha256_unchanged": plan_hash, "source_sha256": {name: sha(ROOT / name) for name in SOURCES},
        "script_sha256": sha(Path(__file__)), "run_id": run["id"], "sealed_result_unchanged": old_errors,
        "original_required_preserved": len(old_required), "new_required_count": result["required_count"],
        "projection_field_counts_not_raw_completeness": [{k: q[k] for k in ("artifact_id", "tool_name", "projected_fields", "visible_fields", "view_state")} for q in receipts],
        "visible_query_fields": list(visible.values()), "all_projected_field_dispositions": field_inventory,
        "old_c4_nine_fields": [{"ref": ref, "visible_in_new_c6": key(ref) in visible} for ref in c4_nine],
        "shared_query_context_roundtrip_exact": True, "canonical_output_schema_unchanged_except_source_ids": True,
        "capacity": {"old_view_bytes": len(old_body["input"][1]["content"].encode()), "new_view_bytes": prepared["bytes"],
            "messages_bytes": len(encoded(prepared["messages"])), "full_wire_bytes": len(encoded(body)),
            "real_prior_c3_tokens": used, "output_limit": 3000, "margin": 256, "run_limit": run["limits"]["max_tokens"],
            "remaining_conservative_units": run["limits"]["max_tokens"] - used - len(encoded(body)) - 3000 - 256,
            "budget_reason": budget, "final_wire_reason": reserved},
        "legacy_24k_packet": {"byte_limit_unchanged": old_packet["byte_limit"], "minimum_full_wire_bytes": old_packet["after_bytes"],
            "over_by": old_packet["after_bytes"] - old_packet["byte_limit"], "fits": False,
            "reason": "required_query_endpoints_must_not_be_dropped_to_restore_old_fit; old run is not redispatched"},
        "limits": ["only_one_row_minimum_per_nonempty_query; other_rows_and_fields_may_be_omitted",
            "query_host_time_binding_does_not_establish_alert_ownership_or_process_network_causality",
            "visible_command_not_completion_or_authorization; destination_not_exfiltration",
            "IP_conflict_flag_preserved: IPv4_mapped_IPv6_representation_difference_is_not_itself_adversarial_conflict",
            "C4_and_Deep_views_unchanged_and_may_still_omit_semantic_fields",
            "C6_provider_extra_property_failure_is_unfixed; no_model_call_or_retry"],
        "model_calls": 0, "database_calls": 0}
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "capacity": report["capacity"],
        "queries": report["projection_field_counts_not_raw_completeness"], "legacy": report["legacy_24k_packet"]}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
