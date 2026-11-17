"""Freeze D4b provenance and independent requirements; no product execution."""
import hashlib
import json
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OUT = HERE / "preparation-01"
SOURCE = ROOT / "docs/operations/evidence/ai-unit-continuation-d4-20261116-01/readback-01/database.json"
RELEASE = ROOT / "deploy/aisoc21/streaming-release-20261116-03/release.json"
MOTHERS = {
    "complete": ("75255ae9-8159-5fa4-ae53-af5927e26523", "real_model", 11),
    "partial": ("7ef7bceb-7c93-5894-bd0c-b0343334050b", "controlled_truncation", 1),
    "none": ("3d8b5a17-512d-563d-b34e-6250c3f1bf35", "controlled_empty", 0),
}
# Declared from the current design, never computed by the implementation under test.
SCENARIOS = [
    ("B01", "TC-N11", ["running", "legal_retry_wait"], "no_terminal_signal_or_allocation"),
    ("B02", "TC-N11", ["only_old_stale_complete", "only_old_stale_none"], "no_current_terminal_signal"),
    ("B03", "TC-N06/11", ["terminal_complete", "terminal_partial", "terminal_none"],
     "current_verified_terminal_receipt_can_signal_without_fabricating_diagnosis"),
    ("B04", "TC-N08/11", ["receipt_missing", "original_digest_mismatch"], "no_verified_terminal_signal"),
    ("B05", "TC-N11", ["same_input_content_new_execution_ids_and_mapped_aliases"],
     "equal_semantic_digest_and_no_repeat_trigger_real_sources_and_scope_preserved"),
    ("B06", "TC-N11", ["same_input_none_repeat", "new_business_input_none"],
     "same_input_deduplicates_new_input_changes_neither_is_successful_diagnosis"),
    ("B07", "TC-N11", ["same_input_core_then_partial_or_none", "partial_then_none", "new_partial_after_partial",
                        "new_input_none_after_old_complete"],
     "prefer_latest_core_then_latest_nonempty_then_none_no_cross_run_merging_or_old_input_fallback"),
    ("B08", "TC-N11", ["retained_content_change", "declared_scope_change", "none_to_first_usable"],
     "different_semantic_digest_then_same_content_deduplicates"),
    ("B09", "TC-N05/11", ["four_total_three_selected_one_retained"],
     "allocate_from_all_four_do_not_expand_diagnosis_beyond_actual_scope"),
    ("B10", "TC-N06/08", ["freeze_partial_C1_then_pointer_changes_build_C3"],
     "frozen_source_retained_as_prior_analysis_no_receipt_hash_attempt_or_error_ledger_in_messages"),
    ("B11", "TC-N11", ["single_alert_late_A", "existing_schedule_close_expiry_checks"],
     "no_direct_A_trigger_no_schedule_or_receiver_rule_change"),
    ("B12", "TC-N08", ["owner_saved_component_bundle"],
     "C1_to_selected_I_trace_full_catalog_content_same_identity_scope_and_original"),
]


def read(path):
    return json.loads(path.read_text())


def fingerprint(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write_once(name, value):
    path = OUT / name
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == raw, f"Frozen preparation changed: {path}; create a new preparation batch"
    else:
        path.write_bytes(raw)
    return fingerprint(path)


def main():
    release = read(RELEASE)
    runtime = ROOT / "deploy/aisoc21" / Path(release["prior_runtime_root"]).name / "analysis"
    policy_path = runtime / "investigation-policy.toml"
    policy = tomllib.loads(policy_path.read_text())
    lifecycle = read(runtime / "lifecycle.json")
    # runtime_policy.load_*_profile resolves the selected basename beside its module.
    # These are current packaged profiles, not files adjacent to the deployment TOML.
    profile_root = ROOT / "services/api/app/socai2"
    profiles = [profile_root / policy[key]["profile"] for key in ("alert_io", "incident_io", "case_io")]
    provenance = [SOURCE, RELEASE, policy_path, profile_root / "runtime_policy.py", *profiles,
                  *(runtime / name for name in ("lifecycle.json", "dispatcher.json", "case-allocation.json"))]
    before = [fingerprint(path) for path in provenance]
    data = read(SOURCE)
    artifacts = {row["id"]: row for row in data["artifacts"]}
    mothers = {}
    for state, (run_id, mode, count) in MOTHERS.items():
        run = next(row for row in data["runs"] if row["id"] == run_id)
        attempt = next(row for row in data["analysis_attempts"] if row["run_id"] == run_id)
        task = next(row for row in data["analysis_tasks"] if row["id"] == attempt["task_id"])
        receipt = next(row for row in data["artifacts"] if row["run_id"] == run_id
                       and (row.get("content_json") or {}).get("type") == "stage_delivery")
        body = receipt["content_json"]
        source = artifacts[run["input_artifact_id"]]
        assert body["delivery"]["state"] == state and len(body["retained_units"]) == count
        assert body["run_id"] == run_id and body["input_artifact_id"] == source["id"]
        assert source["content_json"]["input_selection"]["selected_count"] == 4
        assert attempt["local_state"] == "ended" and attempt["local_ended_at"] is not None
        assert task["next_retry_at"] is None
        if state == "partial":
            assert [unit["path"] for unit in body["retained_units"]] == ["$.members[0]"]
        mothers[state] = {
            "evidence_type": mode, "run": run, "attempt": attempt, "task": task,
            "input_artifact_id": source["id"], "input_sha256": source["sha256"],
            "input_selection": source["content_json"]["input_selection"],
            "receipt_artifact_id": receipt["id"], "receipt_sha256": receipt["sha256"],
            "stage_delivery": body,
            "artifact_index": [{key: row.get(key) for key in ("id", "kind", "sha256", "size_bytes", "run_id")}
                               for row in data["artifacts"] if row["run_id"] == run_id],
            "diagnoses": [row for row in data["incident_diagnoses"] if row["source_run_id"] == run_id],
        }
    assert len({row["attempt"]["input_digest"] for row in mothers.values()}) == 1
    incident = next(row for row in data["incidents"] if row["id"] == mothers["complete"]["run"]["incident_id"])
    assert incident["latest_diagnosis_id"] == mothers["complete"]["diagnoses"][0]["id"]
    OUT.mkdir(parents=True, exist_ok=True)
    files = [write_once("mothers.json", {"source": before[0], "incident": incident, "mothers": mothers}),
             write_once("scenarios.json", {"status": "prepared_not_product_tested", "groups": [
                 {"id": sid, "requirement": requirement, "controlled_variants": variants,
                  "expected": expected, "execution": "not_run"}
                 for sid, requirement, variants, expected in SCENARIOS]})]
    assert before == [fingerprint(path) for path in provenance]
    manifest = {"status": "prepared_not_product_tested", "new_model_calls": 0, "database_requests": 0,
                "http_requests": 0, "product_tests_run": 0, "quality": "not_checked",
                "configuration_selection": "r3.prior_runtime_root -> r2 explicit files; historical prompt not reused as config",
                "configuration": {"release": release["release"], "model": policy["model"]["alias"],
                    "context_tokens": policy["model"]["context_tokens"], "output_tokens": policy["model"]["output_tokens"],
                    "lifecycle": lifecycle, "allocation": read(runtime / "case-allocation.json")},
                "sources": before, "files": files, "source_bytes_unchanged": True,
                "mother_count": len(mothers), "scenario_group_count": len(SCENARIOS),
                "pending": ["stable_D4b_entrypoints", "independent_direct_checks", "owner_PG_component_readback"],
                "not_covered": ["D4c_whole_chain", "D5", "D6", "21", "TCP", "4177", "prose_quality"]}
    write_once("manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "mothers": len(mothers), "scenario_groups": len(SCENARIOS),
                      "source_files": len(before), "product_tests_run": 0, "new_requests": 0}))


if __name__ == "__main__":
    main()
