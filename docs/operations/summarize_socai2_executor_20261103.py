"""Fixed executor evidence, without rewriting any earlier batch receipt."""
import hashlib
import json
from pathlib import Path

from app.models.socai2 import Socai2Base

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT.parent / "functional-alignment-20261103"
RECEIPTS = [
    "socai2-executor-20261103/20261103T154543/receipt.json",
    "socai2-executor-20261103/20261103T155339/receipt.json",
    "socai2-store-20261103/20261103T155433/receipt.json",
    "socai2-c3-20261103/20261103T155434/receipt.json",
    "socai2-delivery-20261103/20261103T155435/receipt.json",
    "socai2-deep-20261103/20261103T155436/receipt.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    latest, failures, receipts, tested = {}, [], [], {}
    for name in RECEIPTS:
        path = ROOT / "docs/operations/evidence" / name
        data = json.loads(path.read_text("utf-8"))
        assert data["database"] == "socai2_schema_review_20261103_a1" and data["synthetic_only"]
        assert data["observations"][-1] == {"name": "restricted_test_role_and_tunnel_removed", "passed": True, "detail": None}
        rel = path.relative_to(ROOT).as_posix()
        receipts.append({"path": rel, "sha256": sha(path)})
        checks = [item for item in data["observations"] if item["name"].startswith("test_")]
        assert checks
        for item in checks:
            latest[item["name"]] = {"passed": item["passed"], "detail": item["detail"], "receipt": rel}
            if not item["passed"]:
                failures.append({"name": item["name"], **latest[item["name"]]})
        if all(item["passed"] for item in checks):
            tested.update({Path(p).as_posix(): h for p, h in data["hashes"].items()})
    assert len(latest) == 16 and sum(n.startswith("test_full_") for n in latest) == 10
    assert not failures and all(item["passed"] for item in latest.values())
    sources = ["services/api/app/socai2/" + p for p in ["baseline_executor.py", "baseline_contracts.py",
        "baseline_analysis.py", "baseline_reasoning.py", "baseline_service.py", "baseline_delivery.py",
        "baseline_reanalysis.py", "baseline_store.py"]]
    sources += ["services/api/tests/test_socai2_baseline_executor.py", "docs/operations/verify_socai2_store_20261103.py"]
    assert all(sha(ROOT / p) == tested[p] for p in sources)
    mirrors = ["services/api/migrations/123_socai2_page_data_model.sql", "services/api/app/models/socai2.py",
        "services/api/app/socai2/enums.py", "services/api/app/socai2/contracts.schema.json", "services/api/app/socai2/__init__.py"]
    assert all(sha(ROOT / p) == sha(DESIGN / p) for p in mirrors)
    assert sha(ROOT / mirrors[0]) == "ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da"
    assert len(Socai2Base.metadata.tables) == 29 and sum(len(t.columns) for t in Socai2Base.metadata.tables.values()) == 458
    design_docs = ["docs/architecture/investigation-planning-design.md",
        "docs/design/investigation-design-current-gap-review-20261103.md",
        "docs/design/socai2-schema-implementation-20261103.md", "docs/design/baseline-execution-handoff-20261103.md",
        "docs/design/investigation-result-field-audit-20261103.md", "docs/investigation/README.md", "PROGRESS.md", "AGENTS.md"]
    local_docs = ["docs/investigation/socai2-baseline-executor-20261103.md", "docs/investigation/README.md", "PROGRESS.md", "AGENTS.md"]
    paths = [ROOT / p for p in sources + local_docs] + [Path(__file__)]
    summary = {"batch": "socai2-baseline-executor-20261103", "database": "socai2_schema_review_20261103_a1",
        "synthetic_only": True, "distinct_new_checks": 10, "distinct_regression_checks": 6,
        "all_latest_results_passed": True, "latest_results": latest, "original_failures": failures,
        "receipts": receipts, "current_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
        "current_sources_match_latest_passing_receipts": True,
        "schema_mirrors_unchanged": {p: sha(ROOT / p) for p in mirrors},
        "schema_tables": 29, "schema_columns": 458,
        "design_hashes": {p: sha(DESIGN / p) for p in design_docs},
        "validation_notes": [
            "Eight initial executor checks passed; original receipts remain unchanged.",
            "Post-review removed previous-request S aliases from followup projections; original C3 artifacts and references remain.",
            "Two affected executor checks passed again, plus shared C2/C4 Tool allowance and final-token-insufficiency checks.",
            "Six targeted regressions passed: C3 limits, Deep/reanalysis, C6 formal report/comparison/atomic rollback and claim commit before dispatch.",
            "Real PG: repeated start does not dispatch; consecutive member changes coalesce next pending without changing active scope; no automatic successor.",
            "Synthetic C3 + two dynamic query decisions + C6 use four models; C6 sees actual empty/nonempty query receipts.",
            "Three synthetic C2 source reads leave one C4 Tool attempt under the same four-Tool allowance.",
            "Only a model call slot is reserved; shared token/deadline exhaustion still yields a system handoff, not a promised valid conclusion.",
            "Cancellation retains unknown; rejected or unconfigured models are not retried and do not auto-adopt a system-only conclusion.",
            "All six batches removed restricted roles/tunnels. No new container, production data access or real model/lake/source call.",
            "Ruff import/unused-test-import issues were fixed before running; no business check failed in this batch.",
            "One documentation patch had an unmatched title and was not applied; it was corrected after reading the actual title.",
            "The summary's initial local write hit sandbox PermissionError; the same authorized local output was saved with escalation, not an approval-review rejection.",
        ],
        "boundaries": {"real_model_calls": 0, "real_clickhouse_queries": 0, "vendor_calls": 0,
            "business_database_reads_or_writes": 0, "new_containers": 0, "business_ddl_changes": 0,
            "ui_changes": 0, "deployed": False, "committed": False, "pushed": False,
            "remaining": ["business_writers_manual_HTTP_run_result_detail_DTO",
                "host_authentication_UEBA_knowledge_external_graph_adapters", "manual_feedback_AI_conversation_services",
                "historical_migration_production_switch_real_model_and_source_acceptance"]}}
    target = ROOT / "docs/operations/socai2-baseline-executor-20261103.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"new": 10, "regressions": 6, "all_latest_pass": True, "original_business_failures": len(failures),
        "batches": len(receipts), "schema_unchanged": True, "source_hashes_match": True}))


if __name__ == "__main__":
    main()
