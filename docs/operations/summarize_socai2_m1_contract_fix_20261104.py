"""Summarize local m1 fixes; no model calls, network or database operations."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/operations/socai2-m1-contract-fix-20261104.json"
EVIDENCE = ROOT / "docs/operations/evidence/socai2-m1-contract-fix-20261104"


def read(path):
    return json.loads(path.read_text("utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("summary already fixed; do not overwrite")
    prior = read(ROOT / "docs/operations/socai2-model-evaluation-m1-20261104.json")
    for path, expected in prior["evidence_sha256"].items():
        assert sha(ROOT / path) == expected, path
    plan = read(ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m1/plan-and-packets.json")
    changes = {path: {"m1_sha256": old, "current_sha256": sha(ROOT / path)}
        for path, old in plan["code_hashes"].items() if sha(ROOT / path) != old}
    assert len(changes) == 14, changes

    latest, attempts, receipts = {}, [], []
    for folder in ["socai2-alert-basic-20261104", "socai2-incident-diagnosis-20261104",
                   "socai2-c3-20261103", "socai2-executor-20261103", "socai2-delivery-20261103"]:
        for path in sorted((ROOT / "docs/operations/evidence" / folder).glob("20261104T11*/receipt.json")):
            if path.parent.name < "20261104T113200":
                continue
            receipt = read(path)
            assert receipt["database"] == "socai2_schema_review_20261103_a1" and receipt["synthetic_only"]
            relative = path.relative_to(ROOT).as_posix()
            cleanup = [o for o in receipt["observations"] if o["name"] == "restricted_test_role_and_tunnel_removed"]
            assert len(cleanup) == 1 and cleanup[0]["passed"], relative
            receipts.append(path)
            for observation in receipt["observations"]:
                if observation["name"].startswith("test_"):
                    item = {"name": observation["name"], "passed": observation["passed"], "receipt": relative}
                    attempts.append(item)
                    latest[observation["name"]] = item
    assert len(latest) == 11 and all(i["passed"] for i in latest.values()), latest
    assert "56 passed" in (EVIDENCE / "pure-final-r4.txt").read_text("utf-8")
    assert "All checks passed!" in (EVIDENCE / "ruff-final.txt").read_text("utf-8")
    assert "is valid" in (EVIDENCE / "openspec-strict.txt").read_text("utf-8")
    assert read(EVIDENCE / "static-contracts.json")["contract_copies_equal"]

    files = set(plan["code_hashes"])
    files.update({"services/api/app/socai2/contracts.schema.json",
        "docs/design/socai2-data-contract-20261103.json",
        "docs/design/socai2-json-contracts-20261103.schema.json"})
    files.update("services/api/tests/" + name for name in ["test_socai2_m1_contract_fixes.py",
        "test_socai2_stage_quality.py", "test_socai2_structured_output.py",
        "test_socai2_compact_model_input.py", "test_socai2_alert_basic_executor.py"])
    files.add(Path(__file__).relative_to(ROOT).as_posix())
    evidence = [*EVIDENCE.glob("*"), *receipts]
    result = {
        "status": "local_implementation_validated_not_deployed_or_model_quality_accepted",
        "branch": "codex/case-baseline-history-20261103",
        "changes_since_m1": changes,
        "versions": {"grouped_input": "socai2.grouped-model-input.v3",
            "case_view": "socai2.baseline-model-view.v4", "alert_executor": "socai2.alert-basic-executor.v3",
            "incident_executor": "socai2.incident-diagnosis-executor.v3"},
        "schema_profile": {"default": "standard", "explicit_vllm_grammar_v1": "remove_only_uniqueItems_before_recording",
            "remote_profile_unchanged": True, "duplicate_checks_remain_local": True},
        "pure_unique_cases_latest_passed": 56,
        "pure_new_parametrized_cases": 13,
        "postgres_unique_methods_latest_passed": len(latest),
        "postgres_latest": list(latest.values()),
        "postgres_attempts_including_original_failures": attempts,
        "postgres_attempted_methods": len(attempts),
        "postgres_failed_attempts_preserved": sum(not a["passed"] for a in attempts),
        "all_test_roles_and_tunnels_removed": True,
        "test_database": "socai2_schema_review_20261103_a1",
        "model_and_lake_responses": "substitutes",
        "m1_original_evidence_hashes_verified": len(prior["evidence_sha256"]),
        "m1_summary_sha256": sha(ROOT / "docs/operations/socai2-model-evaluation-m1-20261104.json"),
        "m1_original_answers_or_historical_status_changed": False,
        "capacity": read(EVIDENCE / "current-input-capacity.json"),
        "new_real_model_calls": 0, "new_real_lake_queries": 0, "deployed": False,
        "ddl_or_orm_changes": False, "business_tables": 29, "business_columns": 459,
        "budget_increased": False, "last_verified_live_candidate": "n9",
        "remote_model_or_original_service_config_changed": False,
        "limits": ["decision_basis validates structure and roles, not semantic truth",
            "known inline IDs are warnings, never auto-added to structured evidence",
            "m1 C3 original parses under corrected general rules; no business adoption",
            "new schema profile and judgment behavior need fresh bounded real-model acceptance",
            "full C-H-second-C quality, final independent review and OpenSpec archive remain incomplete"],
        "code_and_contract_sha256": {p: sha(ROOT / p) for p in sorted(files)},
        "evidence_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(evidence) if p.is_file()},
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"summary": OUT.relative_to(ROOT).as_posix(), "pure": 56,
        "postgres": len(latest), "m1_evidence_unchanged": len(prior["evidence_sha256"]),
        "real_model_calls": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
