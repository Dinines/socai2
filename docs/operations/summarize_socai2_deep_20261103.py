"""Fixed Deep/reanalysis receipts; original evidence is never rewritten."""
import hashlib
import json
from pathlib import Path

from app.socai2.baseline_deep_contract import Decision

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT.parent / "functional-alignment-20261103"
RECEIPTS = ["socai2-deep-20261103/20261103T133735/receipt.json",
    "socai2-deep-20261103/20261103T133849/receipt.json",
    "socai2-c3-20261103/20261103T133849/receipt.json",
    "socai2-c4-20261103/20261103T134040/receipt.json",
    "socai2-c2-20261103/20261103T134040/receipt.json",
    "socai2-deep-20261103/20261103T134433/receipt.json",
    "socai2-deep-20261103/20261103T134908/receipt.json"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    latest, failed, receipts = {}, [], []
    for name in RECEIPTS:
        path = ROOT / "docs/operations/evidence" / name
        payload = json.loads(path.read_text("utf-8"))
        assert payload["database"] == "socai2_schema_review_20261103_a1" and payload["synthetic_only"]
        assert payload["observations"][-1] == {"name": "restricted_test_role_and_tunnel_removed", "passed": True, "detail": None}
        relative = path.relative_to(ROOT).as_posix()
        receipts.append({"path": relative, "sha256": sha(path)})
        for check in payload["observations"]:
            if not check["name"].startswith("test_"):
                continue
            latest[check["name"]] = {"passed": check["passed"], "detail": check["detail"], "receipt": relative}
            if not check["passed"]:
                failed.append({"name": check["name"], **latest[check["name"]]})
    new = sum(n.startswith(("test_deep_", "test_reanalysis_")) for n in latest)
    assert new == 10 and len(latest) == 19 and all(v["passed"] for v in latest.values())
    mirrored = ["services/api/migrations/123_socai2_page_data_model.sql", "services/api/app/models/socai2.py",
        "services/api/app/socai2/enums.py", "services/api/app/socai2/contracts.schema.json", "services/api/app/socai2/__init__.py"]
    assert all(sha(ROOT / p) == sha(DESIGN / p) for p in mirrored)
    assert sha(ROOT / mirrored[0]) == "ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da"
    schema_path = ROOT / "services/api/app/socai2/baseline_deep.schema.json"
    schema = json.loads(schema_path.read_text("utf-8"))
    assert schema == {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:socai2:baseline-deep:v1", **Decision.model_json_schema()}
    assert sha(schema_path) == sha(DESIGN / "docs/design/socai2-baseline-deep-v1.schema.json")
    paths = list((ROOT / "services/api/app/socai2").glob("baseline_*.py"))
    paths += [schema_path, ROOT / "services/api/tests/test_socai2_baseline_deep.py",
        ROOT / "docs/operations/verify_socai2_store_20261103.py", Path(__file__),
        ROOT / "docs/investigation/socai2-baseline-deep-20261103.md"]
    summary = {"batch": "socai2-baseline-deep-20261103", "synthetic_only": True,
        "database": "socai2_schema_review_20261103_a1", "distinct_new_checks": 10,
        "distinct_regression_checks": 9, "all_latest_results_passed": True, "latest_results": latest,
        "original_failures": failed, "receipts": receipts,
        "current_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
        "schema_mirrors_unchanged": {p: sha(ROOT / p) for p in mirrored},
        "deep_schema_matches_runtime_and_design": True,
        "validation_notes": ["First nine new checks and nine regressions passed.",
            "After query identity/window was added, one synthesis test was rejected by the 12KiB message limit; original failure retained.",
            "Field selection now bounds complete serialized messages as well as the 8192-byte body, without raising either cap.",
            "Added frozen C1/C2 context including human feedback to Deep; original roles and current visibility are retained.",
            "Latest targeted five checks passed, including the new human feedback/message-budget test. Unchanged earlier checks reused.",
            "Syntax parentheses, unused imports and loop closure binding were corrected during static checks before associated PG checks.",
            "Seven batches removed restricted test roles and SSH tunnels. No new containers.",
            "C2 adapters are explicitly unavailable in new loop fixtures; C2 skipped steps do not consume synthetic Tool budget.",
            "4 model calls/1 Tool complete initial analysis, one-query Deep, and reanalysis; 4 model calls/2 Tools stop later reanalysis for budget."],
        "boundaries": {"real_model_calls": 0, "real_clickhouse_queries": 0, "vendor_calls": 0,
            "business_database_reads_or_writes": 0, "new_containers": 0, "business_ddl_changes": 0, "ui_changes": 0,
            "deployed": False, "committed": False, "pushed": False,
            "remaining": ["C5_source_grounded_graph", "C6_delivery_and_cross_run_comparison", "full_C1_C6_executor",
                "product_host_and_authentication_adapters", "remaining_background_sources", "business_HTTP_and_writers",
                "live_model_and_lake_acceptance"]}}
    (ROOT / "docs/operations/socai2-baseline-deep-20261103.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"new": new, "regressions": len(latest) - new, "latest_all_pass": True,
        "original_failures_retained": len(failed), "schema_unchanged": True, "new_contract_mirrored": True}))


if __name__ == "__main__":
    main()
