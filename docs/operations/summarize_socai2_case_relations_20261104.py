"""Summarize fixed relation-test receipts without rewriting original failures."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = [
    "docs/operations/evidence/socai2-case-relations-20261104/20261104T042424/receipt.json",
    "docs/operations/evidence/socai2-case-relations-20261104/20261104T042550/receipt.json",
    "docs/operations/evidence/socai2-case-relations-20261104/20261104T042723/receipt.json",
    "docs/operations/evidence/socai2-case-http-20261104/20261104T042804/receipt.json",
    "docs/operations/evidence/socai2-case-relations-20261104/20261104T043059/receipt.json",
    "docs/operations/evidence/socai2-store-20261103/20261104T043114/receipt.json",
]
MIGRATION = "docs/operations/evidence/socai2-case-relations-20261104/20261104T042409/migration.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    latest, failures, hashes = {}, [], {}
    for name in RECEIPTS:
        data = json.loads((ROOT/name).read_text("utf-8"))
        assert data["synthetic_only"] and data["database"] == "socai2_schema_review_20261103_a1"
        assert any(r["name"] == "restricted_test_role_and_tunnel_removed" and r["passed"] for r in data["observations"])
        hashes.update({key.replace("\\", "/"): value for key, value in data["hashes"].items()})
        for row in data["observations"]:
            if row["name"].startswith("test_"):
                latest[row["name"]] = {"passed": row["passed"], "receipt": name}
                if not row["passed"]:
                    failures.append({"name": row["name"], "receipt": name, "detail": row["detail"]})
    assert len(latest) == 19 and all(r["passed"] for r in latest.values()) and len(failures) == 5
    for path, expected in hashes.items():
        assert sha(ROOT/path) == expected, path
    assert sha(ROOT/"services/api/migrations/123_socai2_page_data_model.sql") == "ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da"
    migration = json.loads((ROOT/MIGRATION).read_text("utf-8"))
    assert migration["after"] == {"tables": 29, "columns": 459}
    documents = ["docs/investigation/socai2-case-relations-20261104.md",
        "docs/design/socai2-case-api-v1.openapi.json", "docs/design/socai2-data-contract-20261103.json",
        "docs/design/socai2-field-dictionary-20261103.md", "docs/design/frontend-data-model-audit-20261103.md",
        "docs/design/socai2-schema-implementation-20261103.md", "docs/architecture/investigation-planning-design.md",
        "docs/design/investigation-design-current-gap-review-20261103.md"]
    summary = {"date": "2026-11-04", "branch": "codex/case-baseline-history-20261103",
        "change": "complete-socai2-investigation-chain", "task": "3.4", "new_pg_methods": 12,
        "regression_pg_methods": 7, "latest_results": latest, "preserved_failures": failures,
        "failure_summary": "First four fixture failures omitted correlation_basis/basis_version/source_operation_id. After fixing fixture, three passed and one assertion read the input manifest as the C1 context. Corrected to read exact frozen context; targeted checks plus capacity/closed target and MVCC visibility passed. No business behavior relaxed.",
        "receipts": [{"path": path, "sha256": sha(ROOT/path)} for path in RECEIPTS],
        "migration_receipt": {"path": MIGRATION, "sha256": sha(ROOT/MIGRATION), "result": migration},
        "validation_boundary": {"existing_isolated_pg": True, "synthetic_only": True,
            "real_model_calls": 0, "real_lake_calls": 0, "business_database_changed": False,
            "new_tables_or_containers": False, "schema_tables": 29, "schema_columns": 459,
            "http_authentication": "substitute", "regression_model_and_lake": "substitutes",
            "test_roles_and_tunnels_cleaned": 6, "page_changed": False, "production_switched": False,
            "commit_push_deploy": False, "source_environment": "not supplied; identity namespace is not environment proof"},
        "latest_tested_hashes": hashes, "document_hashes": {p: sha(ROOT/p) for p in documents},
        "next": "3.5 H manual task/result writes and historical references; external sources and migration/real quality remain. Q deferred; r13 paused and 5.3 incomplete."}
    dest = ROOT/"docs/operations/socai2-case-relations-20261104.json"
    dest.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", "utf-8")
    print(json.dumps({"latest_passed": len(latest), "preserved_failures": len(failures), "test_batches": len(RECEIPTS)}))


if __name__ == "__main__":
    main()
