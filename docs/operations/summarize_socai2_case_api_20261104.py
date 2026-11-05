"""Summarize fixed Case HTTP receipts and export the actual opt-in API contract."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from app.api.v1.endpoints.socai2_cases import router
from app.models.socai2 import Socai2Base
from fastapi import FastAPI

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT.parent / "functional-alignment-20261103"
RECEIPTS = [
    "socai2-case-http-20261104/20261104T003940/receipt.json",
    "socai2-case-http-20261104/20261104T004616/receipt.json",
    "socai2-store-20261103/20261104T004643/receipt.json",
    "socai2-case-http-20261104/20261104T004814/receipt.json",
    "socai2-case-http-20261104/20261104T004918/receipt.json",
]
SOURCES = ["services/api/app/socai2/" + p for p in ["case_service.py", "case_reader.py",
    "case_contracts.py", "baseline_service.py"]] + ["services/api/app/api/v1/endpoints/socai2_cases.py",
    "services/api/app/api/v1/router.py", "services/api/app/core/config.py",
    "services/api/tests/test_socai2_case_api.py", "docs/operations/verify_socai2_store_20261103.py"]
LOCAL_DOCS = ["docs/investigation/socai2-case-api-20261104.md", "docs/investigation/README.md", "PROGRESS.md", "AGENTS.md"]
DESIGN_DOCS = ["docs/architecture/investigation-planning-design.md",
    "docs/design/investigation-design-current-gap-review-20261103.md",
    "docs/design/investigation-data-schema-plan-20261103.md",
    "docs/design/socai2-schema-implementation-20261103.md", "docs/design/baseline-execution-handoff-20261103.md",
    "docs/design/investigation-result-field-audit-20261103.md", "docs/investigation/README.md", "PROGRESS.md", "AGENTS.md"]


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
    assert len(latest) == 13 and len(failures) == 4 and all(item["passed"] for item in latest.values())
    assert all(sha(ROOT / p) == tested[p] for p in SOURCES)
    mirrors = ["services/api/migrations/123_socai2_page_data_model.sql", "services/api/app/models/socai2.py",
        "services/api/app/socai2/enums.py", "services/api/app/socai2/contracts.schema.json", "services/api/app/socai2/__init__.py"]
    assert all(sha(ROOT / p) == sha(DESIGN / p) for p in mirrors)
    assert sha(ROOT / mirrors[0]) == "ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da"
    assert len(Socai2Base.metadata.tables) == 29 and sum(len(t.columns) for t in Socai2Base.metadata.tables.values()) == 458

    app = FastAPI(title="socai2 Case API", version="1")
    app.include_router(router, prefix="/api/v1")
    contract = app.openapi()
    assert len(contract["paths"]) == 9
    assert "last_recorded_at" in contract["components"]["schemas"]["RunDetail"]["properties"]
    assert "SavedAnswerReference" in contract["components"]["schemas"]
    body = json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    exported = ROOT / "docs/investigation/socai2-case-api-20261104.openapi.json"
    mirrored = DESIGN / "docs/design/socai2-case-api-v1.openapi.json"
    exported.write_text(body, "utf-8")
    mirrored.write_text(body, "utf-8")
    assert sha(exported) == sha(mirrored)

    config = "services/api/app/core/config.py"
    lint_paths = [p for p in SOURCES if p != config] + [Path(__file__).relative_to(ROOT).as_posix()]
    lint = subprocess.run([sys.executable, "-m", "ruff", "check", "--no-cache", *lint_paths],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
    assert lint.returncode == 0, lint.stdout + lint.stderr
    base_config = subprocess.run(["git", "-c", "safe.directory=" + ROOT.as_posix(), "show", "HEAD:" + config],
        cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
    added = "    # Enable only after the explicit socai2 migration and new data writers are installed.\n    SOCAI2_CASE_API_ENABLED: bool = False\n"
    assert (ROOT / config).read_text("utf-8").replace(added, "", 1) == base_config.replace("\r\n", "\n")
    diagnostics = []
    for content in [base_config, (ROOT / config).read_text("utf-8")]:
        check = subprocess.run([sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format=json",
            "--stdin-filename", config, "-"], cwd=ROOT, input=content, capture_output=True, text=True, encoding="utf-8", check=False)
        diagnostics.append([(r["code"], r["message"]) for r in json.loads(check.stdout)])
    assert diagnostics[0] == diagnostics[1]
    fields = re.findall(r"^\| D(\d+)\b", (ROOT / LOCAL_DOCS[0]).read_text("utf-8"), re.MULTILINE)
    assert list(map(int, fields)) == list(range(1, 37))

    preflight = ROOT / "docs/operations/evidence/socai2-case-http-20261104/preflight-network-unavailable.json"
    paths = [ROOT / p for p in SOURCES + LOCAL_DOCS] + [Path(__file__), exported, preflight]
    summary = {"batch": "socai2-case-api-20261104", "database": "socai2_schema_review_20261103_a1",
        "synthetic_only": True, "distinct_new_checks": 11, "distinct_regression_checks": 2,
        "all_latest_results_passed": True, "latest_results": latest, "original_failures": failures,
        "receipts": receipts, "current_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
        "current_sources_match_latest_passing_receipts": True,
        "schema_mirrors_unchanged": {p: sha(ROOT / p) for p in mirrors}, "schema_tables": 29, "schema_columns": 458,
        "design_hashes": {p: sha(DESIGN / p) for p in DESIGN_DOCS + [mirrored.relative_to(DESIGN).as_posix()]},
        "static_checks": {"ruff_pass_files": lint_paths, "config_only_adds_default_false_flag": True,
            "config_existing_diagnostics_unchanged": diagnostics[1], "openapi_path_count": 9,
            "runtime_openapi_matches_design_copy": True, "distinct_audit_fields": 36},
        "validation_notes": [
            "Initial SSH preflight failed before tests or role creation; user confirmed VPN restoration, then the same isolated DB was reused.",
            "First suite passed eight checks; two fixture setups failed on runs_case_scope and required artifact mime_type.",
            "Next targeted batch passed full delivery and 201-artifact last-record aggregation; AI start-fields and blob_ref text fixture issues remained.",
            "Four original failures remain in immutable receipts. Corrected fixtures satisfy existing constraints; no DDL/guard was relaxed.",
            "Two fixture checks passed after correction; saved AI answer/conversation identity was then exposed and both AI/baseline result paths passed again.",
            "Two targeted transaction regressions passed: COMMIT failure must not dispatch; publication rollback leaves no partial formal result.",
            "Unchanged passing checks were reused; this is thirteen distinct latest-pass checks, not one all-green first run.",
            "ASGI routes and permission dependencies are real; principal, model and lake responses are explicit substitutes. No real JWT/login acceptance.",
            "GET uses repeatable-read read-only transactions. Concurrent member update cannot mix snapshots; attempted UPDATE fails SQLSTATE 25006.",
            "Active baseline keeps frozen scope; consecutive changes coalesce next pending and cannot start it until active run ends; no automatic successor.",
            "Model transport uncertainty remains unknown, with unknown usage and no fabricated result; response omits raw provider exceptions.",
            "Historical AI entries require an actual saved Result; equal-time keyset pagination includes both pending and saved AI without unsaved AI runs.",
            "External blobs/oversize content remain explicitly unavailable; hash mismatch is rejected and private blob location is not returned.",
            "All five batches removed temporary restricted roles and SSH tunnels. Only two public.users columns were granted to Case tests.",
            "Ruff cache permission error was avoided with --no-cache. New-file C408/import style issues were fixed; existing config diagnostics are unchanged.",
            "First local OpenAPI write hit sandbox PermissionError; the same authorized repository output was retried with escalation, not an approval-review rejection.",
            "Summary script import/regex style and Windows subprocess text encoding were corrected before its final static check; no PG tests were repeated for these document-only issues.",
        ],
        "boundaries": {"real_model_calls": 0, "real_clickhouse_queries": 0, "vendor_calls": 0,
            "business_database_reads_or_writes": 0, "new_containers": 0, "business_ddl_changes": 0,
            "ui_changes": 0, "deployed": False, "committed": False, "pushed": False, "api_enabled_in_production": False,
            "remaining": ["Fusion_alert_material_reference_object_incident_member_diagnosis_writers",
                "explicit_Case_incident_relationships_and_moves", "host_authentication_UEBA_knowledge_external_graph_adapters",
                "manual_task_AI_conversation_save_and_adoption_services", "history_migration_production_switch_real_model_source_acceptance"]}}
    target = ROOT / "docs/operations/socai2-case-api-20261104.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"new": 11, "regressions": 2, "all_latest_pass": True, "original_fixture_failures": len(failures),
        "batches": len(receipts), "schema_unchanged": True, "source_hashes_match": True, "openapi_paths": 9}))


if __name__ == "__main__":
    main()
