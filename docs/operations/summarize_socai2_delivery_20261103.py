"""Summarize fixed C6 evidence; preserve every earlier receipt and failure."""
import hashlib
import json
from pathlib import Path

from app.socai2.baseline_delivery_contract import Delivery

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT.parent / "functional-alignment-20261103"
RECEIPTS = [
    "socai2-delivery-20261103/20261103T150345/receipt.json",
    "socai2-delivery-20261103/20261103T150549/receipt.json",
    "socai2-delivery-20261103/20261103T150932/receipt.json",
    "socai2-graph-20261103/20261103T151303/receipt.json",
    "socai2-deep-20261103/20261103T151319/receipt.json",
    "socai2-store-20261103/20261103T151334/receipt.json",
    "socai2-delivery-20261103/20261103T151707/receipt.json",
    "socai2-store-20261103/20261103T151724/receipt.json",
    "socai2-delivery-20261103/20261103T152157/receipt.json",
    "socai2-delivery-20261103/20261103T152436/receipt.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    latest, failures, receipts, tested = {}, [], [], {}
    for name in RECEIPTS:
        path = ROOT / "docs/operations/evidence" / name
        payload = json.loads(path.read_text("utf-8"))
        assert payload["database"] == "socai2_schema_review_20261103_a1" and payload["synthetic_only"]
        assert payload["observations"][-1] == {"name": "restricted_test_role_and_tunnel_removed", "passed": True, "detail": None}
        rel = path.relative_to(ROOT).as_posix()
        receipts.append({"path": rel, "sha256": sha(path)})
        checks = [o for o in payload["observations"] if o["name"].startswith("test_")]
        assert checks
        for item in checks:
            latest[item["name"]] = {"passed": item["passed"], "detail": item["detail"], "receipt": rel}
            if not item["passed"]:
                failures.append({"name": item["name"], **latest[item["name"]]})
        if all(c["passed"] for c in checks):
            tested.update({Path(p).as_posix(): h for p, h in payload["hashes"].items()})
    assert sum(n.startswith("test_c6_") for n in latest) == 14
    assert len(latest) == 21 and len(failures) == 3 and all(v["passed"] for v in latest.values())
    mirrors = ["services/api/migrations/123_socai2_page_data_model.sql", "services/api/app/models/socai2.py",
        "services/api/app/socai2/enums.py", "services/api/app/socai2/contracts.schema.json", "services/api/app/socai2/__init__.py"]
    assert all(sha(ROOT / p) == sha(DESIGN / p) for p in mirrors)
    assert sha(ROOT / mirrors[0]) == "ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da"
    schema_path = ROOT / "services/api/app/socai2/baseline_delivery.schema.json"
    schema = json.loads(schema_path.read_text("utf-8"))
    assert schema == {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:socai2:baseline-delivery:v1", **Delivery.model_json_schema()}
    assert sha(schema_path) == sha(DESIGN / "docs/design/socai2-baseline-delivery-v1.schema.json")
    sources = ["services/api/app/socai2/" + p for p in ["baseline_delivery.py", "baseline_delivery_contract.py",
        "baseline_delivery_projection.py", "baseline_reanalysis.py", "baseline_service.py", "baseline_store.py"]]
    sources += ["services/api/tests/test_socai2_baseline_delivery.py", "docs/operations/verify_socai2_store_20261103.py"]
    assert all(sha(ROOT / p) == tested[p] for p in sources)
    paths = [ROOT / p for p in sources] + [schema_path, Path(__file__), ROOT / "docs/investigation/socai2-baseline-delivery-20261103.md"]
    summary = {"batch": "socai2-baseline-delivery-20261103", "database": "socai2_schema_review_20261103_a1",
        "synthetic_only": True, "distinct_new_checks": 14, "distinct_regression_checks": 7,
        "all_latest_results_passed": True, "latest_results": latest, "original_failures": failures, "receipts": receipts,
        "current_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
        "current_sources_match_latest_passing_receipts": True,
        "schema_mirrors_unchanged": {p: sha(ROOT / p) for p in mirrors},
        "delivery_schema_matches_runtime_and_design": True,
        "validation_notes": ["The first three cases failed because Markdown content_json is null; citation role handling now supports text artifacts.",
            "Three focused cases passed, followed by ten remaining cases and five regressions.",
            "Final review aligned report_json with the existing report_result contract and reserved Result identity; five C6 cases and two storage regressions passed.",
            "Added failed/unadopted historical Result detection so missing selected baseline is not mislabeled initial; targeted check passed.",
            "Final projection keeps member-only findings/impact object_keys empty rather than claiming all Case objects; targeted report/result check passed.",
            "Ten strict output counterexamples include unseen/duplicate sources or keys, scope escape, blank text, invented comparison and prior-analysis-only impact.",
            "C3 initial + one-query Deep + final C6 use four synthetic model calls and one synthetic Tool; no extra writing call.",
            "Real deferred FK commit failures verify request-before-dispatch and atomic result/report/adoption rollback.",
            "Unknown usage stays null, system handoff is not adopted, cancellation retains unknown, and scope changes prevent stale adoption.",
            "All ten batches removed restricted roles and tunnels; no temporary containers.",
            "Model and ClickHouse responses are substitutes; accepted marks structure/scope/source checks, not proven prose semantics."],
        "boundaries": {"real_model_calls": 0, "real_clickhouse_queries": 0, "vendor_calls": 0,
            "business_database_reads_or_writes": 0, "new_containers": 0, "business_ddl_changes": 0,
            "ui_changes": 0, "deployed": False, "committed": False, "pushed": False,
            "remaining": ["unified_C1_C6_executor_and_final_model_reservation", "business_writers_HTTP_read_DTO",
                "host_authentication_UEBA_knowledge_external_graph_adapters", "manual_task_and_AI_conversation_services",
                "migration_switch_and_real_model_lake_quality_acceptance"]}}
    (ROOT / "docs/operations/socai2-baseline-delivery-20261103.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"new": 14, "regressions": 7, "latest_all_pass": True,
        "original_failures_retained": len(failures), "schema_unchanged": True, "delivery_contract_mirrored": True}))


if __name__ == "__main__":
    main()
