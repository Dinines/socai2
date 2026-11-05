"""Summarize fixed A/I read checks and export runtime contracts, no DB work."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from app.api.v1.endpoints.socai2_analysis import router
from app.socai2.baseline_context import AlertInput, Context
from fastapi import FastAPI

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT.parent / "functional-alignment-20261103"
RECEIPTS = ["socai2-stage-reader-20261104/20261104T020251/receipt.json",
    "socai2-stage-reader-20261104/20261104T020355/receipt.json",
    "socai2-stage-reader-20261104/20261104T020521/receipt.json",
    "socai2-c1-20261103/20261104T020558/receipt.json",
    "socai2-stage-results-20261104/20261104T020750/receipt.json"]
SOURCES = ["services/api/app/socai2/" + n for n in ["stage_inputs.py", "stage_results.py", "stage_result_contracts.py",
    "stage_reader.py", "stage_read_contracts.py", "baseline_context.py", "baseline_context.schema.json", "baseline_model_view.py"]]
SOURCES += ["services/api/app/api/v1/endpoints/socai2_analysis.py", "services/api/app/api/v1/router.py",
    "services/api/app/core/config.py", "services/api/tests/test_socai2_stage_reader.py",
    "services/api/tests/test_socai2_baseline_context.py", "docs/operations/verify_socai2_store_20261103.py"]
DOCS = ["docs/investigation/socai2-stage-reader-20261104.md", "docs/investigation/README.md", "AGENTS.md", "PROGRESS.md"]
DESIGN_DOCS = ["AGENTS.md", "PROGRESS.md", "docs/investigation/README.md",
    "docs/design/socai2-schema-implementation-20261103.md", "docs/design/investigation-design-current-gap-review-20261103.md",
    "docs/architecture/investigation-planning-design.md"]
MIRRORS = ["services/api/migrations/123_socai2_page_data_model.sql", "services/api/app/models/socai2.py",
    "services/api/app/socai2/enums.py", "services/api/app/socai2/contracts.schema.json", "services/api/app/socai2/__init__.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False, **kwargs)


def main():
    # The final DTO check batch is explicitly supplied, never selected by latest mtime.
    assert len(sys.argv) == 2
    receipt_names = RECEIPTS + ["socai2-stage-reader-20261104/" + sys.argv[1] + "/receipt.json"]
    latest, failures, tested, receipts = {}, [], {}, []
    for name in receipt_names:
        p = ROOT / "docs/operations/evidence" / name
        d = json.loads(p.read_text("utf-8"))
        assert d["database"] == "socai2_schema_review_20261103_a1" and d["synthetic_only"]
        assert d["observations"][-1] == {"name": "restricted_test_role_and_tunnel_removed", "passed": True, "detail": None}
        checks = [r for r in d["observations"] if r["name"].startswith("test_")]
        assert checks
        for r in checks:
            latest[r["name"]] = {**r, "receipt": p.relative_to(ROOT).as_posix()}
            if not r["passed"]:
                failures.append(latest[r["name"]])
        if all(r["passed"] for r in checks):
            tested.update({Path(n).as_posix(): h for n, h in d["hashes"].items()})
        receipts.append({"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p)})
    assert len(latest) == 13 and len(failures) == 6 and all(r["passed"] for r in latest.values())
    assert all(sha(ROOT / n) == tested[n] for n in SOURCES)
    assert all(sha(ROOT / n) == sha(DESIGN / n) for n in MIRRORS)
    assert sha(ROOT / MIRRORS[0]) == "ceb9a68012f84d6558cd0f75aa67b4047ae6245e1be64e79dd9b86587b8579da"
    runtime = Context.model_json_schema()
    frozen = ROOT / "services/api/app/socai2/baseline_context.schema.json"
    assert json.loads(frozen.read_text("utf-8")) == runtime
    legacy = AlertInput.model_validate({"alert": {}, "membership": {}, "material": None, "source_refs": [],
        "objects": [], "triage": None, "feedback": None, "limitations": []})
    assert legacy.triage_usable is None and legacy.triage_freshness == "unverified"
    context_copy = DESIGN / "docs/design/socai2-baseline-context-v1.schema.json"
    context_copy.write_bytes(frozen.read_bytes())
    app = FastAPI(title="socai2 A/I analysis read API", version="1")
    app.include_router(router, prefix="/api/v1")
    contract = app.openapi()
    assert len(contract["paths"]) == 4
    assert "TriageView" in contract["components"]["schemas"] and "DiagnosisView" in contract["components"]["schemas"]
    assert "ScoreState" in contract["components"]["schemas"]
    local_openapi = ROOT / "docs/investigation/socai2-stage-reader-20261104.openapi.json"
    design_openapi = DESIGN / "docs/design/socai2-stage-reader-v1.openapi.json"
    body = json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    local_openapi.write_text(body, "utf-8"); design_openapi.write_text(body, "utf-8")
    assert sha(local_openapi) == sha(design_openapi) and sha(frozen) == sha(context_copy)
    config = "services/api/app/core/config.py"
    paths = [p for p in SOURCES if p.endswith(".py") and p != config] + [Path(__file__).relative_to(ROOT).as_posix()]
    lint = command([sys.executable, "-m", "ruff", "check", "--no-cache", *paths])
    assert lint.returncode == 0, lint.stdout + lint.stderr
    base = command(["git", "-c", "safe.directory=" + ROOT.as_posix(), "show", "HEAD:" + config])
    assert base.returncode == 0
    diagnostics = []
    for content in [base.stdout, (ROOT / config).read_text("utf-8")]:
        result = command([sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format=json", "--stdin-filename", config, "-"], input=content)
        diagnostics.append(sorted((r["code"], r["message"]) for r in json.loads(result.stdout)))
    assert diagnostics[0] == diagnostics[1]
    assert "SOCAI2_ANALYSIS_READ_ENABLED: bool = False" in (ROOT / config).read_text("utf-8")
    fields = re.findall(r"^\| V(\d+)\b", (ROOT / DOCS[0]).read_text("utf-8"), re.MULTILINE)
    assert list(map(int, fields)) == list(range(1, 21))
    for tree, names in [(ROOT, SOURCES + DOCS), (DESIGN, DESIGN_DOCS)]:
        d = command(["git", "-c", "safe.directory=" + tree.as_posix(), "-C", str(tree), "diff", "--check", "--", *names])
        assert d.returncode == 0, d.stdout + d.stderr
    out = {"batch": "socai2-stage-reader-20261104", "database": "socai2_schema_review_20261103_a1",
        "synthetic_only": True, "distinct_new_checks": 7, "distinct_regression_checks": 6,
        "all_latest_passed": True, "latest_results": latest, "original_failures": failures, "receipts": receipts,
        "temporary_roles_and_tunnels_cleaned": 6, "source_hashes_match_passing_receipts": True,
        "current_hashes": {p: sha(ROOT / p) for p in SOURCES + DOCS + [Path(__file__).relative_to(ROOT).as_posix(), local_openapi.relative_to(ROOT).as_posix()]},
        "design_hashes": {p: sha(DESIGN / p) for p in DESIGN_DOCS + [context_copy.relative_to(DESIGN).as_posix(), design_openapi.relative_to(DESIGN).as_posix()]},
        "schema_mirrors_unchanged": {p: sha(ROOT / p) for p in MIRRORS}, "schema_tables": 29, "schema_columns": 458,
        "static_checks": {"ruff_passed_files": paths, "config_existing_diagnostics_unchanged": diagnostics[1],
            "context_runtime_schema_mirrored": True, "legacy_context_default_compatibility": True,
            "openapi_paths": 4, "default_flag_disabled": True, "field_rows": 20},
        "notes": [
            "First read batch passed two checks and failed five because UUID bind parameters in a derived table inferred text. Explicit UUID casts fixed the independent read query; C1 source comparison was already inside its single statement snapshot.",
            "One targeted assertion then confused a raw_json source path with raw content exposure. Checking the actual raw sentinel fixed the test; both original failures remain.",
            "Seven new checks and four C1 plus two A/I regressions have latest passing results; unchanged passes were reused. Typed DTO/enum finalization rechecked current results and all-state pagination only.",
            "PG, ASGI routes and permission dependencies are real; authentication principals and all analysis outputs are synthetic. No model, lake or production login was exercised.",
            "C1 excludes stale/unverified/unavailable analysis from newly prepared model views but retains source records and limitations. Old frozen contexts remain unchanged; new optional fields preserve old v1 parsing.",
            "Read-only repeatable-read preserves a snapshot across a concurrent material commit, and rejects UPDATE with SQLSTATE 25006. New transactions observe stale state.",
            "Shared input SQL matches producer semantics; current pointer and validity are separate. Failed/unknown attempts remain in history; Explain uses its own Run and verifies hash/size/limit.",
            "C2 similar-alert prior analyses remain historical background and exclude Case members; this batch does not claim every historical analysis source is current.",
            "Initial static unused imports were removed before database tests. Pre-existing core config lint diagnostics are unchanged.",
        ],
        "boundaries": {"real_model_calls": 0, "real_lake_queries": 0, "business_database_operations": 0, "new_containers": 0,
            "ddl_changes": 0, "ui_changes": 0, "deployed": False, "committed": False, "pushed": False,
            "remaining": ["actual_A_I_executor_and_source_request_response_steps_usage_adapters", "complete_alert_incident_page_DTOs",
                "explicit_case_incident_links_H_Q_external_sources_history_migration_production_acceptance"]}}
    (ROOT / "docs/operations/socai2-stage-reader-20261104.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"new": 7, "regressions": 6, "original_failures": 6, "latest_pass": True,
        "paths": 4, "fields": 20, "schema_unchanged": True, "sources_match": True}))


if __name__ == "__main__":
    main()
