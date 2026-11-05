"""Verify fixed A/I receipts and current field/document contracts; no DB calls."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT.parent / "functional-alignment-20261103"
RECEIPTS = ["20261104T013942", "20261104T014133"]
SOURCES = ["services/api/app/socai2/stage_results.py", "services/api/app/socai2/stage_result_contracts.py",
    "services/api/tests/test_socai2_stage_results.py", "docs/operations/verify_socai2_store_20261103.py"]
DOCS = ["docs/investigation/socai2-stage-results-20261104.md", "docs/investigation/README.md", "AGENTS.md", "PROGRESS.md"]
DESIGN_DOCS = ["AGENTS.md", "PROGRESS.md", "docs/investigation/README.md",
    "docs/design/socai2-schema-implementation-20261103.md", "docs/design/investigation-design-current-gap-review-20261103.md",
    "docs/architecture/investigation-planning-design.md"]
MIRRORS = ["services/api/migrations/123_socai2_page_data_model.sql", "services/api/app/models/socai2.py",
    "services/api/app/socai2/enums.py", "services/api/app/socai2/contracts.schema.json", "services/api/app/socai2/__init__.py"]
STYLE_COMMENT = b"  # noqa: SIM114 -- whole receipt and typed field are distinct policies"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    latest, tested, receipts = {}, {}, []
    for batch in RECEIPTS:
        path = ROOT / "docs/operations/evidence/socai2-stage-results-20261104" / batch / "receipt.json"
        data = json.loads(path.read_text("utf-8"))
        assert data["database"] == "socai2_schema_review_20261103_a1" and data["synthetic_only"]
        assert data["observations"][-1] == {"name": "restricted_test_role_and_tunnel_removed", "passed": True, "detail": None}
        for item in data["observations"]:
            assert item["passed"], item
            if item["name"].startswith("test_"):
                latest[item["name"]] = {**item, "receipt": path.relative_to(ROOT).as_posix()}
        tested.update({Path(p).as_posix(): h for p, h in data["hashes"].items()})
        receipts.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})
    assert len(latest) == 10
    for name in SOURCES:
        body = (ROOT / name).read_bytes()
        if name.endswith("stage_results.py") and "/app/" in name:
            assert body.count(STYLE_COMMENT) == 1
            body = body.replace(STYLE_COMMENT, b"")
        assert hashlib.sha256(body).hexdigest() == tested[name], name
    assert all(sha(ROOT / p) == sha(DESIGN / p) for p in MIRRORS)
    assert sha(ROOT / MIRRORS[0]) == "ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da"
    fields = re.findall(r"^\| S(\d+)\b", (ROOT / DOCS[0]).read_text("utf-8"), re.MULTILINE)
    assert list(map(int, fields)) == list(range(1, 29))
    lint = subprocess.run([sys.executable, "-m", "ruff", "check", "--no-cache", *SOURCES,
        str(Path(__file__).relative_to(ROOT))], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
    assert lint.returncode == 0, lint.stdout + lint.stderr
    for tree, paths in [(ROOT, SOURCES + DOCS), (DESIGN, DESIGN_DOCS)]:
        check = subprocess.run(["git", "-c", "safe.directory=" + tree.as_posix(), "diff", "--check", "--", *paths],
            cwd=tree, capture_output=True, text=True, encoding="utf-8", check=False)
        assert check.returncode == 0, check.stdout + check.stderr
    payload = {"batch": "socai2-stage-results-20261104", "database": "socai2_schema_review_20261103_a1",
        "synthetic_only": True, "distinct_checks": 10, "all_latest_results_passed": True,
        "original_business_check_failures": [], "latest_results": latest, "receipts": receipts,
        "temporary_roles_and_tunnels_cleaned": 2, "field_rows": 28,
        "current_hashes": {p: sha(ROOT / p) for p in SOURCES + DOCS + [Path(__file__).relative_to(ROOT).as_posix()]},
        "design_hashes": {p: sha(DESIGN / p) for p in DESIGN_DOCS},
        "schema_mirrors_unchanged": {p: sha(ROOT / p) for p in MIRRORS},
        "schema_tables": 29, "schema_columns": 458,
        "tested_code_match": "Exact receipt hashes; stage_results.py differs only by one verified lint comment, no executable change.",
        "static_checks": {"ruff": "passed", "tracked_diff_whitespace": "passed", "field_sequence": "S01-S28"},
        "validation_notes": [
            "Initial nine independent PostgreSQL checks all passed. After adding typed prior-analysis input references, the A/I-to-Case bridge and one new role rejection check passed.",
            "Synthetic outputs are passed to the real new storage service. No actual A/I executor, model, lake or external source ran; no query/model/usage receipts are fabricated.",
            "Concurrent claims/publications, operation replay/conflict, changed materials, out-of-order completion and later freshness changes are checked.",
            "A and I outputs are read back through the actual Case C1 freeze; triage remains paired and I prior analysis cannot cite itself as an observation.",
            "Unknown and failed diagnosis attempts do not replace a successful current pointer. Explicit failure resolution does not retry the executor.",
            "A deferred foreign-key failure at COMMIT rolls back all output, pointers and Run terminal state; oversize input creates no Run.",
            "Cross-tenant and outside-frozen-input references fail. Missing paths and invalid score state/value pairs fail.",
            "First static checks found import order, an unused import and nested-condition style; corrected without business test failures. Final SIM114 suppression preserves separate receipt/field policies and is byte-verified against tested source.",
            "Current pointer means latest adopted success, not perpetual freshness. The new repeatable-read freshness helper is not yet wired into Case C1 or page DTOs; the existing C1 limitation remains explicit.",
            "No DDL, shared enum/JSON contract changes or legacy consumer writes. The old Agents writer includes memory/action/escalation side effects and was deliberately not swapped piecemeal.",
        ],
        "boundaries": {"real_model_calls": 0, "real_lake_queries": 0, "business_database_operations": 0,
            "new_containers": 0, "ui_changes": 0, "deployed": False, "committed": False, "pushed": False,
            "remaining": ["actual_A_lookup_triage_and_I_diagnosis_executor_adapters", "actual_request_response_steps_usage_and_source_receipts",
                "alert_incident_read_DTO_and_C1_freshness_integration", "explicit_case_incident_relationships",
                "H_Q_external_sources_history_migration_and_production_acceptance"]}}
    (ROOT / "docs/operations/socai2-stage-results-20261104.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"checks": len(latest), "failures": 0, "batches": 2, "fields": len(fields),
        "schema_unchanged": True, "tested_code_verified": True}))


if __name__ == "__main__":
    main()
