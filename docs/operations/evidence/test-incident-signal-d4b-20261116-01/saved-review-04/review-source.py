"""Read-only independent D4b PG evidence review; standard library, no requests."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUNS = {"complete": "75255ae9-8159-5fa4-ae53-af5927e26523",
        "partial": "7ef7bceb-7c93-5894-bd0c-b0343334050b", "none": "3d8b5a17-512d-563d-b34e-6250c3f1bf35"}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def at(value, path):
    for key in re.findall(r"[^.\[\]]+", path[2:]):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def review(directory, readback_root=None, capture_only=False):
    state = directory.name.split("-")[1]
    files = {p.name: p for p in directory.glob("*.json")}
    final = (readback_root or directory.parent / "final-readback-01") / state
    files.update({"final/" + p.name: p for p in final.glob("*.json")})
    if directory.name == "pg-complete-07":
        # The first actual allocation succeeded before a later C1 fixture error;
        # resumed calls correctly returned no second allocation.
        files["allocation-original.json"] = directory.parent / "pg-complete-05/allocation.json"
    hashes = {name: sha(path.read_bytes()) for name, path in files.items()}
    data = {name: json.loads(path.read_text()) for name, path in files.items()}
    checks = []

    def check(name, condition):
        assert condition, f"{directory.name}: {name}"
        checks.append(name)

    result, intent = (data[name + ".json"] for name in ("result", "intent"))
    check("owner_component_passed_without_model_http_or_whole_case", result["state"] == "passed"
          and result["model_generations"] == result["http_requests"] == result["redis_tasks_dispatched"] == 0
          and result["full_case_execution"] is False and result["deployment"] is False)
    check("original_mother_bytes_match", sha((ROOT / intent["mother"]).read_bytes()) == intent["mother_sha256"])
    iid, cid, rid = result["incident_id"], result["case_id"], result["case_run_id"]
    captures = {entry["label"]: entry["context"] for entry in data["captures.json"]}
    # A resumed component retains earlier captures with the same label. The
    # running/retry sequence follows the first selection, before allocation.
    initial = next(entry["context"]["incidents"][iid]["analysis_material"]
                   for entry in data["captures.json"] if entry["label"] == state + "_selection")
    check("selected_run_from_expected_actual_mother", initial["source_run_id"] == intent["mapping"][RUNS[state]]
          == result["source_run_id"])
    if not capture_only:
        check("running_and_legal_retry_have_no_material", all(captures[label]["incidents"][iid]["analysis_material"] is None
              for label in ("current_attempt_running", "legal_retry_waiting")))
        restored = captures["no_new_receipt_old_complete_retained"]["incidents"][iid]["analysis_material"]
        check("receiptless_failure_keeps_existing_selected_material", restored == initial)
    check("new_input_old_I_is_stale", captures["new_alert_old_i_is_stale"]["incidents"][iid]["analysis_material"] is None)
    context = data["frozen-context.json"]
    material = context["incidents"][iid]["analysis_material"]
    full = captures["all_incident_members_allocated"]
    check("frozen_readback_same_selected_I", material == full["incidents"][iid]["analysis_material"]
          and material["source_run_id"] == initial["source_run_id"] and context["case_id"] == cid)
    selected = set(material["input_selection"]["selected_alert_ids"])
    all_members = set(full["incidents"][iid]["member_ids"])
    allocations = data.get("allocation-original.json", data["allocation.json"])
    allocated = {aid for receipt in allocations for row in receipt["allocations"]
                 for key in ("added_alert_ids", "existing_alert_ids") for aid in row[key]}
    check("real_allocation_uses_full_incident_members", len(all_members) == 4
          and set(full["alerts"]) == all_members == allocated
          and all(row["case_id"] == cid for receipt in allocations for row in receipt["allocations"]))
    if state == "partial":
        check("four_total_three_selected_one_retained", len(selected) == 3 and len(material["units"]) == 1
              and len(material["units"][0]["scope"]["alert_ids"]) == 1
              and len(all_members - selected) == 1 and set(context["alerts"]) == all_members)
    arts = data["case-artifacts.json"]
    source = next(a for a in arts if a["schema_version"] == "socai2.baseline-context.v1")
    manifest = next(a for a in arts if a["kind"] == "input_snapshot")
    check("Case_artifacts_subject_and_integrity", all(a["run_id"] == rid and a["case_id"] == cid
          and a["tenant_id"] == result["tenant_id"] and a["sha256"] == sha(encoded(a["content_json"]))
          and a["size_bytes"] == len(encoded(a["content_json"])) for a in arts))
    check("full_C1_matches_read_context", source["content_json"] == context)
    source_ids = {r["id"] for r in manifest["content_json"]["source_materials"] if r["type"] == "artifact"}
    identities = [material["input"], material["response"], material["receipt_source"], *material["originals"]]
    check("page_manifest_locates_C1_and_frozen_I_sources", source["id"] in source_ids
          and {r["id"] for r in identities} <= source_ids)
    seed_arts = {a["id"]: a for a in data["final/source-artifacts-readback.json"]}
    check("frozen_I_sources_resolve_to_exact_saved_run", all(
        seed_arts[r["id"]]["run_id"] == material["source_run_id"]
        and seed_arts[r["id"]]["incident_id"] == iid
        and r["sha256"] == seed_arts[r["id"]]["sha256"] == sha(encoded(seed_arts[r["id"]]["content_json"]))
        and r["size_bytes"] == len(encoded(seed_arts[r["id"]]["content_json"])) for r in identities))
    check("stage_receipt_same_saved_body", material["receipt"] == seed_arts[material["receipt_source"]["id"]]["content_json"])
    receipt = material["receipt"]
    check("availability_and_actual_selection", receipt["delivery"]["state"] == state
          and receipt["use"]["conclusion_available"] is (state == "complete")
          and material["business_view"]["conclusion_available"] is (state == "complete")
          and set(material["business_view"]["member_ids"]) == selected)
    for raw in receipt["retained_units"]:
        original = seed_arts[raw["original_artifact_id"]]["content_json"]
        text = at(original, raw["original_content_path"])
        start, end = raw["value_span"]
        fragment = text[start:end]
        check("raw_span_hash_and_value:" + raw["path"], 0 <= start < end <= len(text)
              and sha(fragment.encode()) == raw["value_sha256"] and json.loads(fragment) == raw["value"])
    normalized = seed_arts[material["response"]["id"]]["content_json"]["received_analysis"]
    for unit in material["units"]:
        if unit["path"].startswith("$.diagnosis."):
            value = normalized["diagnosis"][unit["path"].split(".")[-1]]
            owners = selected if receipt["use"]["conclusion_available"] else set()
        else:
            section, index = re.match(r"\$\.(\w+)\[(\d+)\]", unit["path"]).groups()
            entry = normalized[section][int(index)]
            owners = {entry["alert_id"]} if section == "members" else set(entry["alert_ids"])
            value = {k: v for k, v in entry.items() if k not in {"id", "alert_id", "alert_ids", "source_ids"}}
        check("retained_business_and_scope:" + unit["path"], unit["value"] == value
              and set(unit["scope"]["alert_ids"]) == owners and owners <= selected)
    prepared = data["c3-prepared.json"]
    messages, mapping = data["c3-messages.json"]
    wire = "\n".join(m["content"] for m in messages)
    check("current_C3_profile_matches_source_file", prepared["ready"] and context["case_input_profile"]["sha256"]
          == sha((ROOT / "services/api/app/socai2/case-input-v1.json").read_bytes()))
    for index, unit in enumerate(material["units"]):
        path = f"$.incidents.{iid}.analysis_material.units.{index}.value"
        refs = [v for v in mapping.values() if v["ref"].get("source_path") == path]
        check("C3_prior_analysis_original_scope:" + unit["path"], bool(refs)
              and context["citation_roles"][path] == "prior_analysis"
              and all(v["ref"]["role"] == "prior_analysis" and v["ref"]["id"] == source["id"]
                      and set(v["alert_ids"]) == set(unit["scope"]["alert_ids"])
                      and v["original_scope"] == unit["scope"] for v in refs))
        if isinstance(unit["value"], dict) and unit["value"].get("assessment"):
            check("C3_keeps_actual_member_text:" + unit["path"], unit["value"]["assessment"] in wire)
    check("no_execution_ledger_in_model_messages", not any(x in wire for x in (
        "receipt_source", "local_ended_at", "attempt_id", "input_digest", "tenant_uid", material["source_run_id"],
        material["receipt_source"]["sha256"], material["attempt_id"], material["task_id"])))
    database = data["final/database-readback.json"]
    check("C1_still_identical_after_new_alert", data["final/frozen-context-after-new-alert.json"] == context)
    counts = data["final/read-only-counts.json"]
    check("17_table_row_counts_unchanged_during_owner_readback", len(counts["before"]) == 17
          and counts["before"] == counts["after"])
    case_run = next(r for r in database["runs"] if r["id"] == rid)
    check("Case_Run_explicitly_failed_C1_component_not_whole_execution", case_run["state"] == "failed"
          and case_run["stop_reason"] == "component_capture_only")
    check("no_running_Run_or_attempt", not any(r["state"] == "running" for r in database["runs"])
          and not any(a["local_state"] == "running" for a in database["analysis_attempts"]))
    check("database_has_actual_frozen_Case_and_I_artifacts", all(
        any(a["id"] == artifact["id"] and a["sha256"] == artifact["sha256"] for a in database["artifacts"])
        for artifact in [source, manifest, *seed_arts.values()]))
    check("no_mother_files_modified_during_review", hashes == {name: sha(path.read_bytes()) for name, path in files.items()})
    return {"directory": str(directory.relative_to(ROOT)), "status": "passed", "checks": checks,
            "source_files": hashes, "case_run_id": rid, "source_run_id": material["source_run_id"],
            "retained_units": len(receipt["retained_units"]), "model_generations": 0, "requests": 0,
            "dynamic_running_retry_evidence": "prior saved-review-03; not repeated" if capture_only else "this component"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--readback-root", type=Path)
    parser.add_argument("--capture-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    results = []
    try:
        for bundle in args.bundle:
            results.append(review(bundle.resolve(), args.readback_root, args.capture_only))
    except (AssertionError, KeyError, IndexError, TypeError, ValueError, OSError) as exc:
        result = {"status": "failed", "error": repr(exc), "completed": results, "requests": 0}
    else:
        result = {"status": "passed", "checks": sum(len(r["checks"]) for r in results), "bundles": results,
                  "requests": 0, "scope": "offline saved PG component review; no HTTP/full Case/model execution"}
    (args.output / "review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (args.output / "review-source.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k: v for k, v in result.items() if k not in {"bundles", "completed"}}, ensure_ascii=False))
    if result["status"] != "passed":
        raise SystemExit(1)
