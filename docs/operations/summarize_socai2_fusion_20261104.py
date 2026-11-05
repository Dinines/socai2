"""Verify fixed Fusion/Case receipts without repeating database or model work."""
import ast
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from app.models.alert import FusedAlert, RawAlert

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT.parent / "functional-alignment-20261103"
EVIDENCE = ROOT / "docs/operations/evidence/socai2-fusion-ingest-20261104"
BATCHES = ["20261104T010809", "20261104T011034", "20261104T011208",
    "20261104T011300", "20261104T011748", "20261104T011840"]
SOURCES = ["services/fusion/app/services/socai2_sink.py", "services/fusion/app/services/socai2_projection.py",
    "services/fusion/app/core/config.py", "services/fusion/app/main.py",
    "services/fusion/tests/test_socai2_sink_postgres.py", "services/api/tests/test_socai2_fusion_case_bridge.py",
    "docs/operations/verify_socai2_store_20261103.py"]
MIRRORS = ["services/api/migrations/123_socai2_page_data_model.sql", "services/api/app/models/socai2.py",
    "services/api/app/socai2/enums.py", "services/api/app/socai2/contracts.schema.json", "services/api/app/socai2/__init__.py"]
LOCAL_DOCS = ["docs/investigation/socai2-fusion-ingestion-20261104.md", "docs/investigation/README.md", "AGENTS.md", "PROGRESS.md"]
DESIGN_DOCS = ["docs/architecture/investigation-planning-design.md",
    "docs/design/investigation-design-current-gap-review-20261103.md",
    "docs/design/investigation-data-schema-plan-20261103.md", "docs/design/socai2-schema-implementation-20261103.md",
    "docs/investigation/README.md", "AGENTS.md", "PROGRESS.md"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False, **kwargs)


def main():
    latest, failures, receipts, tested = {}, [], [], {}
    check_batches = 0
    for batch in BATCHES:
        path = EVIDENCE / batch / "receipt.json"
        data = json.loads(path.read_text("utf-8"))
        assert data["database"] == "socai2_schema_review_20261103_a1" and data["synthetic_only"]
        assert data["observations"][-1] == {"name": "restricted_test_role_and_tunnel_removed", "passed": True, "detail": None}
        rel = path.relative_to(ROOT).as_posix()
        checks = [item for item in data["observations"] if item["name"].startswith("test_")]
        assert bool(checks) == (batch != "20261104T011208")
        check_batches += bool(checks)
        receipts.append({"path": rel, "sha256": sha(path), "executed_checks": len(checks)})
        for item in checks:
            latest[item["name"]] = {"passed": item["passed"], "detail": item["detail"], "receipt": rel}
            if not item["passed"]:
                failures.append({"name": item["name"], **latest[item["name"]]})
        if checks and all(item["passed"] for item in checks):
            tested.update({Path(p).as_posix(): h for p, h in data["hashes"].items()})
    assert check_batches == 5 and len(latest) == 10 and len(failures) == 1
    assert all(item["passed"] for item in latest.values())
    assert all(sha(ROOT / p) == tested[p] for p in SOURCES)
    assert all(sha(ROOT / p) == sha(DESIGN / p) for p in MIRRORS)
    assert sha(ROOT / MIRRORS[0]) == "ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da"
    tree = ast.parse((ROOT / MIRRORS[1]).read_text("utf-8"))
    tables = [node for node in tree.body if isinstance(node, ast.ClassDef) and any(
        isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in stmt.targets)
        for stmt in node.body)]
    columns = sum(isinstance(stmt, ast.AnnAssign) and isinstance(stmt.value, ast.Call)
        and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == "mapped_column"
        for table in tables for stmt in table.body)
    assert len(tables) == 29 and columns == 458
    audit = (ROOT / LOCAL_DOCS[0]).read_text("utf-8")
    raw_fields = re.findall(r"^\| R\d+ \| `([^`]+)`", audit, re.MULTILINE)
    fused_fields = re.findall(r"^\| F\d+ \| `([^`]+)`", audit, re.MULTILINE)
    assert len(raw_fields) == 33 and set(raw_fields) == set(RawAlert.model_fields)
    assert len(fused_fields) == 20 and set(fused_fields) == set(FusedAlert.model_fields)
    regression = EVIDENCE / "legacy-regression.xml"
    suites = list(ET.parse(regression).getroot().iter("testsuite"))
    assert sum(int(s.get("tests", "0")) for s in suites) == 10
    assert all(int(s.get(key, "0")) == 0 for s in suites for key in ("errors", "failures", "skipped"))
    import_failure = EVIDENCE / "bridge-import-failure.json"
    initial_error = json.loads(import_failure.read_text("utf-8"))
    assert initial_error["executed_checks"] == 0 and not initial_error["count_as_passing_test_batch"]

    main_path = "services/fusion/app/main.py"
    lint_paths = [p for p in SOURCES if p != main_path] + [Path(__file__).relative_to(ROOT).as_posix()]
    lint = run([sys.executable, "-m", "ruff", "check", "--no-cache", *lint_paths])
    assert lint.returncode == 0, lint.stdout + lint.stderr
    baseline = run(["git", "-c", "safe.directory=" + ROOT.as_posix(), "show", "HEAD:" + main_path])
    assert baseline.returncode == 0, baseline.stderr
    diagnostics = []
    for content in [baseline.stdout, (ROOT / main_path).read_text("utf-8")]:
        check = run([sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format=json",
            "--stdin-filename", main_path, "-"], input=content)
        diagnostics.append([(r["code"], r["message"]) for r in json.loads(check.stdout)])
    assert sorted(diagnostics[0]) == sorted(diagnostics[1])
    config = (ROOT / "services/fusion/app/core/config.py").read_text("utf-8")
    assert 'alert_store_schema: Literal["public", "socai2"] = Field(default="public"' in config
    assert 'settings.alert_store_schema == "socai2"' in (ROOT / main_path).read_text("utf-8")
    diff = run(["git", "-c", "safe.directory=" + ROOT.as_posix(), "diff", "--check", "--", *SOURCES, *LOCAL_DOCS])
    assert diff.returncode == 0, diff.stdout + diff.stderr

    paths = [ROOT / p for p in SOURCES + LOCAL_DOCS] + [Path(__file__), regression, import_failure]
    summary = {"batch": "socai2-fusion-ingestion-20261104", "database": "socai2_schema_review_20261103_a1",
        "synthetic_only": True, "distinct_new_checks": 10, "distinct_legacy_regression_checks": 10,
        "all_latest_results_passed": True, "latest_results": latest, "original_check_failures": failures,
        "initial_zero_check_import_failure": initial_error, "executed_check_batches": check_batches,
        "temporary_roles_and_tunnels_cleaned": len(BATCHES), "receipts": receipts,
        "current_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
        "current_sources_match_passing_receipts": True,
        "schema_mirrors_unchanged": {p: sha(ROOT / p) for p in MIRRORS}, "schema_tables": 29, "schema_columns": columns,
        "design_hashes": {p: sha(DESIGN / p) for p in DESIGN_DOCS},
        "static_checks": {"ruff_pass_files": lint_paths, "main_existing_diagnostics_unchanged": diagnostics[1],
            "default_store_public": True, "raw_alert_fields": raw_fields, "fused_alert_fields": fused_fields,
            "tracked_diff_whitespace_check": True},
        "validation_notes": [
            "Nine Fusion writer/worker checks and one Fusion-to-Case C1 bridge check have latest passing receipts; ten legacy local regressions also pass.",
            "Existing isolated PostgreSQL is real; Fusion engine, Redis and Kafka boundaries are substitutes. No actual model, lake or vendor execution.",
            "The bridge freezes actual writer-produced RawAlert material, reads C4 process semantics and builds the existing bounded model view.",
            "RawAlert remains complete in material.raw_json; raw logs are not copied into C1 enrichment background. FusedAlert remains in the immutable first-result artifact.",
            "Concurrent duplicate writes, changed material revisions, old-material replay, manual field/membership preservation, tenant isolation and COMMIT rollback are checked.",
            "Incident business time is monotonic even when another member transaction has published a newer clock.",
            "Initial bridge import used a nonexistent helper: zero checks executed; cleanup succeeded, then the corrected import passed.",
            "One later fixture reused a source incident ID and failed its unique constraint; a unique fixture identity passed the targeted rerun. Original receipt remains.",
            "Unchanged passing checks are reused; current source hashes are checked against passing receipts. No claim of one all-green initial run.",
            "Source references are deduplicated and capped at 200 with scope metadata; the complete received array remains in raw material. Candidate windows are not causal chains.",
            "Unknown event times remain NULL; unknown/disabled/failed confidence never becomes an available score. Existing anomaly/priority defaults remain retained-only pending score provenance.",
            "The fixed synthetic database gained one connector fixture; no schema change or new container was needed. All six temporary restricted roles and tunnels were removed.",
            "Default remains public. Existing downstream consumers and action writers still need migration before opting into socai2 in production.",
            "All local summary assertions passed before a sandbox file-write PermissionError; repository output was retried with escalation, not an approval-review rejection. No business tests were repeated.",
        ],
        "boundaries": {"real_model_calls": 0, "real_clickhouse_queries": 0, "vendor_calls": 0,
            "business_database_reads_or_writes": 0, "new_containers": 0, "business_ddl_changes": 0,
            "ui_changes": 0, "deployed": False, "committed": False, "pushed": False,
            "remaining": ["A_basic_lookup_triage_explanation_and_score_provenance_writes",
                "I_frozen_members_and_actual_diagnosis_writes", "new_alert_incident_read_contracts",
                "explicit_case_incident_links_and_moves", "H_Q_services_and_external_source_adapters",
                "downstream_migration_history_production_switch_and_real_quality_acceptance"]}}
    target = ROOT / "docs/operations/socai2-fusion-ingestion-20261104.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"new_latest_pass": 10, "legacy_pass": 10, "original_check_failures": 1,
        "zero_check_import_failures": 1, "check_batches": 5, "cleaned_sessions": 6,
        "field_audit": len(raw_fields) + len(fused_fields), "schema_unchanged": True, "source_hashes_match": True}))


if __name__ == "__main__":
    main()
