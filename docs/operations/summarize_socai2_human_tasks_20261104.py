"""Freeze H/manual-prepare evidence; preserve independent original receipts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = [
    "docs/operations/evidence/socai2-human-tasks-20261104/20261104T044843/receipt.json",
    "docs/operations/evidence/socai2-c2-20261103/20261104T045617/receipt.json",
    "docs/operations/evidence/socai2-c1-20261103/20261104T045618/receipt.json",
    "docs/operations/evidence/socai2-baseline-prepare-20261104/20261104T050127/receipt.json",
]
OWNED = [
    "services/api/app/socai2/human_task_contracts.py", "services/api/app/socai2/human_task_service.py",
    "services/api/app/api/v1/endpoints/socai2_tasks.py", "services/api/tests/test_socai2_human_tasks.py",
    "services/api/app/socai2/baseline_context.py", "services/api/app/socai2/baseline_model_view.py",
    "services/api/app/socai2/case_service.py", "services/api/app/socai2/case_contracts.py",
    "services/api/app/api/v1/endpoints/socai2_cases.py", "services/api/tests/test_socai2_baseline_prepare.py",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    results, failures, fingerprints = {}, [], {}
    for path in RECEIPTS:
        data = json.loads((ROOT/path).read_text("utf-8"))
        assert data["synthetic_only"] and data["database"] == "socai2_schema_review_20261103_a1"
        assert any(r["name"] == "restricted_test_role_and_tunnel_removed" and r["passed"] for r in data["observations"])
        fingerprints.update({k.replace("\\", "/"): v for k, v in data["hashes"].items()})
        for row in data["observations"]:
            if row["name"].startswith("test_"):
                results[row["name"]] = {"passed": row["passed"], "receipt": path}
                if not row["passed"]:
                    failures.append({**row, "receipt": path})
    assert len(results) == 21 and all(r["passed"] for r in results.values()) and not failures
    for path in OWNED:
        assert sha(ROOT/path) == fingerprints[path], path
    docs = ["docs/investigation/socai2-human-tasks-20261104.md",
        "docs/design/socai2-human-tasks-v1.openapi.json", "docs/design/socai2-case-api-v1.openapi.json",
        "docs/operations/export_socai2_human_tasks_20261104.py"]
    out = {"date": "2026-11-04", "branch": "codex/case-baseline-history-20261103",
        "change": "complete-socai2-investigation-chain", "task": "3.5",
        "new_human_pg_methods": 10, "new_prepare_pg_methods": 5, "regression_pg_methods": 6,
        "latest_results": results, "preserved_failures": failures,
        "initial_static_findings": "Import order and unused imports corrected before PG checks; fixture Delivery corrected to existing partial before execution.",
        "receipts": [{"path": p, "sha256": sha(ROOT/p)} for p in RECEIPTS],
        "owned_latest_tested_hashes": {p: fingerprints[p] for p in OWNED},
        "all_recorded_source_fingerprints": fingerprints,
        "fingerprint_boundary": "Owned task/prepare/C1/model-view code matches tested bytes. Shared runner/source adapters may advance in parallel; their recorded fingerprints are historical, not asserted to be current.",
        "documents": {p: sha(ROOT/p) for p in docs},
        "validation_boundary": {"database": "socai2_schema_review_20261103_a1", "synthetic_only": True,
            "real_pg_transactions": True, "real_model_calls": 0, "real_lake_calls": 0,
            "test_roles_and_tunnels_cleaned": 4, "new_ddl_or_tables": False,
            "schema_tables": 29, "schema_columns": 459, "page_changed": False,
            "http_identity": "substitute", "old_service_replaced": False,
            "automatic_run_or_adoption": False, "explicit_prepare_requires_manual_start": True},
        "scope_policy": "Completed feedback must have a valid nonempty scope entirely inside current members to enter a new model; otherwise retained as execution receipt with limitations. Historical C1 stays unchanged.",
        "next": "Independent service acceptance and remaining real sources/quality; Q deferred, r13 paused, 5.3 unchanged."}
    destination = ROOT/"docs/operations/socai2-human-tasks-20261104.json"
    destination.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", "utf-8")
    print(json.dumps({"latest_pg_passed": len(results), "preserved_failures": len(failures), "batches": len(RECEIPTS)}))


if __name__ == "__main__":
    main()
