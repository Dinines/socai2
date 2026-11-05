"""Aggregate fixed C4 evidence without changing original receipts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT.parent / "functional-alignment-20261103"
FILES = [
    "socai2-c4-20261103/20261103T130614/receipt.json",
    "socai2-c4-20261103/20261103T130946/receipt.json",
    "socai2-store-20261103/20261103T131021/receipt.json",
    "socai2-c3-20261103/20261103T131021/receipt.json",
    "socai2-c4-20261103/20261103T131221/receipt.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    latest, failures, receipts = {}, [], []
    for name in FILES:
        path = ROOT / "docs/operations/evidence" / name
        payload = json.loads(path.read_text("utf-8"))
        assert payload["database"] == "socai2_schema_review_20261103_a1" and payload["synthetic_only"]
        assert payload["observations"][-1] == {"name": "restricted_test_role_and_tunnel_removed", "passed": True, "detail": None}
        ref = str(path.relative_to(ROOT)).replace("\\", "/")
        receipts.append({"path": ref, "sha256": sha(path)})
        for item in payload["observations"]:
            if not item["name"].startswith("test_"):
                continue
            latest[item["name"]] = {"passed": item["passed"], "receipt": ref, "detail": item["detail"]}
            if not item["passed"]:
                failures.append({"name": item["name"], "receipt": ref, "detail": item["detail"]})
    assert len(latest) == 15 and all(r["passed"] for r in latest.values())
    assert sum(n.startswith("test_c4_") for n in latest) == 11
    mirrored = ["services/api/migrations/123_socai2_page_data_model.sql", "services/api/app/models/socai2.py",
        "services/api/app/socai2/enums.py", "services/api/app/socai2/contracts.schema.json", "services/api/app/socai2/__init__.py"]
    assert all(sha(ROOT / p) == sha(DESIGN / p) for p in mirrored)
    assert sha(ROOT / mirrored[0]) == "ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da"
    paths = ["services/api/app/socai2/" + n for n in ["baseline_evidence.py", "baseline_evidence_tools.py",
        "baseline_semantics.py", "baseline_store.py", "baseline_service.py", "baseline_model_view.py"]]
    paths += ["services/api/tests/test_socai2_baseline_evidence.py", "docs/operations/verify_socai2_store_20261103.py",
              "docs/investigation/socai2-baseline-c4-evidence-20261103.md", str(Path(__file__).relative_to(ROOT))]
    value = {"batch": "socai2-baseline-c4-evidence-20261103", "database": "socai2_schema_review_20261103_a1",
        "synthetic_only": True, "distinct_new_checks": 11, "distinct_regression_checks": 4,
        "all_latest_results_passed": True, "latest_results": latest, "original_failures": failures,
        "receipts": receipts, "current_hashes": {p: sha(ROOT / p) for p in paths},
        "schema_mirrors": {p: sha(ROOT / p) for p in mirrored},
        "validation_notes": ["First C4 batch: seven passed; two failed on nonexistent artifacts.created_at.",
            "After captured_at fix: one test still used nonexistent Results.run_id; corrected test to source_run_id.",
            "Final three view/citation tests passed after interleaving material and query records and compact record keys.",
            "Earlier unchanged direct checks reused; original source hashes and failures remain in each receipt.",
            "Static unused/sorted import diagnostics corrected before first PG suite.",
            "Five isolated PG batches removed their restricted role and SSH tunnel.",
            "Deferred FK COMMIT failure verified zero Tool dispatch; C4 query request and query_id commit before I/O."],
        "boundaries": {"real_business_queries": 0, "real_clickhouse_queries": 0, "real_model_calls": 0,
            "vendor_calls": 0, "new_containers": 0, "business_ddl_changes": 0, "ui_changes": 0,
            "committed": False, "pushed": False, "deployed": False,
            "not_completed": ["question_level_dynamic_deep", "post_evidence_reanalysis", "product_host_adapter",
                "authentication_query_adapter", "C5_graph", "C6_delivery", "remaining_C2_sources",
                "new_business_writers_and_HTTP", "live_quality_acceptance"]}}
    output = ROOT / "docs/operations/socai2-baseline-c4-evidence-20261103.json"
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"new": 11, "regression": 4, "latest_all_pass": True,
        "original_failed_observations_retained": len(failures), "schema_files_unchanged": len(mirrored)}))


if __name__ == "__main__":
    main()
