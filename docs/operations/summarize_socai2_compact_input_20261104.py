"""Freeze local checks and closed r6 evidence; never call a service or rewrite a receipt."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text("utf-8"))


def save(name, data):
    path = ROOT / "docs/operations" / name
    assert not path.exists(), "immutable receipt; choose a new revision"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return str(path)


def main():
    evidence = ROOT / "docs/operations/evidence"
    methods, failures, receipts = {}, [], []
    for folder in ("socai2-alert-basic-20261104", "socai2-incident-diagnosis-20261104", "socai2-c2-20261103",
            "socai2-c3-20261103", "socai2-executor-20261103", "socai2-delivery-20261103"):
        for path in sorted((evidence / folder).glob("*/receipt.json")):
            if path.parent.name < "20261104T090115":
                continue
            data = read(path)
            relative = path.relative_to(ROOT).as_posix()
            observations = data["observations"]
            receipts.append({"path": relative, "sha256": sha(path), "cleanup_confirmed": any(
                o["name"] == "restricted_test_role_and_tunnel_removed" and o["passed"] for o in observations)})
            for item in observations:
                if not item["name"].startswith("test_"):
                    continue
                methods[item["name"]] = {"passed": item["passed"], "receipt": relative}
                if not item["passed"]:
                    failures.append({"name": item["name"], "receipt": relative})
    assert all(m["passed"] for m in methods.values()) and all(r["cleanup_confirmed"] for r in receipts)
    snapshot = max((evidence / "socai2-next-acceptance-20261104/20261104T092702-r6-export").glob("database-*.json"))
    db = read(snapshot)
    before_path = max((evidence / "socai2-next-acceptance-20261104/20261104T075920-r5-export").glob("database-*.json"))
    before = read(before_path)
    old_materials = {m["id"]: m for m in before["alert_materials"]}
    assert all(old_materials[m["id"]] == m for m in db["alert_materials"])
    real = {"batch": "r6", "release": "next-20261104-n9", "state": "closed_not_accepted",
        "snapshot": snapshot.relative_to(ROOT).as_posix(), "snapshot_sha256": sha(snapshot),
        "previous_snapshot_sha256": sha(before_path), "original_material_rows_unchanged": True,
        "cases": [c["id"] for c in db["cases"]],
        "runs": [{k: r.get(k) for k in ("id", "kind", "state", "stop_reason", "case_id", "alert_id", "incident_id")} for r in db["runs"]],
        "model_calls": sum(s["kind"] == "model" and s["state"] not in {"planned", "skipped"} for s in db["run_steps"]),
        "total_tokens": sum(s["usage"]["total_tokens"] for s in db["run_steps"] if s["kind"] == "model" and s.get("usage")),
        "executed_tools": [{k: s.get(k) for k in ("id", "name", "stage_code", "state")} for s in db["run_steps"]
            if s["kind"] == "tool" and s["state"] not in {"planned", "skipped"}],
        "human_and_second_case_run_executed": False, "model_cost_state": "unpriced",
        "issues": ["A0_visible_prose_sources_missing_from_paired_structured_refs",
            "C_preparation_charged_full_provenance_to_model_budget",
            "C_whole_incident_diagnosis_omitted_by_single_field_limit",
            "C_failed_required_coverage_still_labelled_complete_required"],
        "no_real_Deep_lake_tool_or_C6_model_accepted": True}
    assert real["model_calls"] == 3 and real["total_tokens"] == 11380
    actual = save("socai2-next-r6-validation-20261104.json", real)
    candidate = read(ROOT / ".local/releases/next-20261104-n9-final/manifest.json")
    files = sorted((ROOT / "services/api/app/socai2").glob("*.py"))
    local = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    changed = [p.relative_to(ROOT).as_posix() for p in files
        if candidate["files"]["app/socai2/" + p.name]["sha256"] != sha(p)]
    summary = {"scope": "compact_input_and_layered_A_I_validation", "deployed_release": "next-20261104-n9",
        "local_followup_view": "socai2.baseline-model-view.v3", "local_followup_deployed": False,
        "ddl_changes": 0, "pure_checks_latest_passed": 43, "batch_driver_checks_latest_passed": 6,
        "pure_command": "pytest test_socai2_compact_model_input.py test_socai2_stage_quality.py test_socai2_structured_output.py test_socai2_model_protocol.py -q",
        "postgres_unique_methods": len(methods), "postgres_latest": methods, "postgres_receipts": receipts,
        "initial_postgres_test_failures": failures,
        "other_initial_failures": ["old_failure_code_assertions", "test_helper_import_path",
            "sandbox_SSH_access_denied_before_database_checks", "r6_new_required_diagnosis_capacity_regression",
            "ruff_import_order_and_scalar_policy_noqa_placement", "summary_console_utf8_decode"],
        "frozen_replay": "docs/operations/socai2-compact-input-replay-20261104.json",
        "real_acceptance": actual, "source_sha256": local,
        "local_business_files_different_from_n9": changed,
        "remaining": ["A0_dual_prose_structured_citation_contract_alignment", "new_candidate_and_real_C_H_second_C_acceptance",
            "independent_final_audit", "OpenSpec_archive_after_acceptance"],
        "not_implemented": ["C_multi_error_diagnostics", "Deep_further_question_specific_background_selection",
            "dedicated_visibility_DTO", "large_case_batching"],
        "openspec_completed": 13, "openspec_total": 16, "overall_accepted": False}
    fixed = save("socai2-compact-input-fix-20261104.json", summary)
    print(json.dumps({"local": fixed, "real": actual, "pg_methods": len(methods), "overall_accepted": False}))


if __name__ == "__main__":
    main()
