"""Aggregate fixed C5 receipts without rewriting failed or empty batches."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT.parent / "functional-alignment-20261103"
RECEIPTS = [
    "socai2-graph-20261103/20261103T143227/receipt.json",
    "socai2-graph-20261103/20261103T143315/receipt.json",
    "socai2-graph-20261103/20261103T143431/receipt.json",
    "socai2-graph-20261103/20261103T143731/receipt.json",
    "socai2-deep-20261103/20261103T143744/receipt.json",
    "socai2-c3-20261103/20261103T143758/receipt.json",
    "socai2-c4-20261103/20261103T144034/receipt.json",
    "socai2-store-20261103/20261103T144048/receipt.json",
    "socai2-store-20261103/20261103T144145/receipt.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    latest, failures, receipts, empty = {}, [], [], []
    tested_hashes = {}
    for name in RECEIPTS:
        path = ROOT / "docs/operations/evidence" / name
        payload = json.loads(path.read_text("utf-8"))
        assert payload["database"] == "socai2_schema_review_20261103_a1" and payload["synthetic_only"]
        assert payload["observations"][-1] == {"name": "restricted_test_role_and_tunnel_removed", "passed": True, "detail": None}
        relative = path.relative_to(ROOT).as_posix()
        receipts.append({"path": relative, "sha256": sha(path)})
        checks = [o for o in payload["observations"] if o["name"].startswith("test_")]
        if not checks:
            empty.append(relative)
        for item in checks:
            latest[item["name"]] = {"passed": item["passed"], "detail": item["detail"], "receipt": relative}
            if not item["passed"]:
                failures.append({"name": item["name"], **latest[item["name"]]})
        if checks and all(c["passed"] for c in checks):
            tested_hashes.update({Path(p).as_posix(): h for p, h in payload["hashes"].items()})
    new = sum(n.startswith("test_c5_") for n in latest)
    assert new == 10 and len(latest) == 15 and all(v["passed"] for v in latest.values())
    assert len(failures) == 17 and len(empty) == 1
    mirrors = ["services/api/migrations/123_socai2_page_data_model.sql", "services/api/app/models/socai2.py",
        "services/api/app/socai2/enums.py", "services/api/app/socai2/contracts.schema.json", "services/api/app/socai2/__init__.py"]
    assert all(sha(ROOT / p) == sha(DESIGN / p) for p in mirrors)
    assert sha(ROOT / mirrors[0]) == "ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da"
    sources = ["services/api/app/socai2/" + p for p in ["baseline_graph.py", "baseline_graph_projection.py",
        "baseline_reanalysis.py", "baseline_service.py", "baseline_store.py"]]
    sources += ["services/api/tests/test_socai2_baseline_graph.py", "docs/operations/verify_socai2_store_20261103.py"]
    assert all(sha(ROOT / p) == tested_hashes[p] for p in sources)
    paths = [ROOT / p for p in sources] + [Path(__file__), ROOT / "docs/investigation/socai2-baseline-graph-20261103.md"]
    result = {"batch": "socai2-baseline-graph-20261103", "database": "socai2_schema_review_20261103_a1",
        "synthetic_only": True, "distinct_new_checks": new, "distinct_regression_checks": len(latest) - new,
        "all_latest_results_passed": True, "latest_results": latest, "original_failures": failures,
        "zero_check_batches_excluded": empty, "receipts": receipts,
        "current_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
        "current_sources_match_latest_passing_receipts": True,
        "schema_mirrors_unchanged": {p: sha(ROOT / p) for p in mirrors},
        "validation_notes": ["First nine checks rejected the synthetic fixture's missing event_time_source.",
            "After fixture repair eight checks exposed UUID graph-key serialization; the active-step/tenant check passed.",
            "The eight failed checks passed after canonicalizing UUID key components; prior valid check reused.",
            "Three targeted checks passed after query identity metadata and stale/latest graph handling were added.",
            "Deep/reanalysis (2), C3 citations (1), C4 citations (1), and publication (1) regressions passed.",
            "One misspelled publication method selected zero checks; excluded. Runner now rejects missing requested checks.",
            "All nine batches removed their temporary restricted role and tunnel; no temporary containers.",
            "Graph construction has no external dispatch and atomically rolls back artifact and step on failure.",
            "Model/ClickHouse responses are synthetic; no claim of live semantic quality or full executor acceptance."],
        "boundaries": {"real_model_calls": 0, "real_clickhouse_queries": 0, "external_graph_queries": 0,
            "vendor_calls": 0, "business_database_reads_or_writes": 0, "new_containers": 0,
            "business_ddl_changes": 0, "ui_changes": 0, "deployed": False, "committed": False, "pushed": False,
            "remaining": ["C6_conclusion_delivery_comparison_impact_and_report", "C6_final_graph_freshness_guard",
                "full_executor_with_final_model_budget_reservation", "external_topology_host_authentication_adapters",
                "remaining_background_sources", "business_writers_HTTP_and_read_DTO", "live_model_and_lake_acceptance"]}}
    (ROOT / "docs/operations/socai2-baseline-graph-20261103.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"new": new, "regressions": len(latest) - new, "latest_all_pass": True,
        "original_failures_retained": len(failures), "zero_check_batches_excluded": len(empty), "schema_unchanged": True}))


if __name__ == "__main__":
    main()
