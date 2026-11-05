"""Verify the local n11 candidate and record m3-driven compatibility changes."""
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / ".local/releases/next-20261104-n11"


def read(path):
    return json.loads(path.read_text("utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prep, manifest = read(DIRECTORY / "preparation.json"), read(DIRECTORY / "manifest.json")
    assert sha(DIRECTORY / "candidate.tar") == prep["archive_sha256"]
    assert sha(DIRECTORY / "manifest.json") == prep["manifest_sha256"]
    with tarfile.open(DIRECTORY / "candidate.tar") as archive:
        assert len(archive.getmembers()) == len(manifest["files"]) + 1
        for entry in archive:
            assert entry.isfile() and entry.mode == 0o644 and not entry.name.startswith("/") and ".." not in Path(entry.name).parts
            assert not any(v in entry.name.lower() for v in ("dsapi", ".env", "id_ed25519", "id_rsa", ".pem"))
            body = archive.extractfile(entry).read()
            if entry.name == "manifest.json":
                assert body == (DIRECTORY / "manifest.json").read_bytes()
                continue
            assert hashlib.sha256(body).hexdigest() == manifest["files"][entry.name]["sha256"]
            if entry.name.startswith("app/"):
                assert body == (ROOT / "services/api" / entry.name).read_bytes()
    old = read(ROOT / ".local/releases/next-20261104-n10/manifest.json")["files"]
    changed = sorted(k for k, v in manifest["files"].items() if old.get(k) != v)
    assert changed == sorted(["app/socai2/" + n for n in (
        "model_errors.py", "baseline_analysis_model.py", "alert_basic_executor.py", "incident_diagnosis_executor.py",
        "baseline_analysis.py", "baseline_reasoning.py", "incident_diagnosis_contract.py", "model_protocol.py")]
        + ["compose.next-service.yml"]), changed
    pg_paths = [
        "docs/operations/evidence/socai2-alert-basic-20261104/20261104T153510/receipt.json",
        "docs/operations/evidence/socai2-executor-20261103/20261104T153713/receipt.json"]
    pg = []
    for name in pg_paths:
        receipt = read(ROOT / name)
        assert receipt["database"] == "socai2_schema_review_20261103_a1" and receipt["synthetic_only"]
        assert all(r["passed"] for r in receipt["observations"])
        pg.extend(receipt["observations"])
    m3 = read(ROOT / "docs/operations/socai2-schema-probe-m3-20261104.json")
    assert all(sha(ROOT / p) == h for p, h in m3["evidence_sha256"].items())
    files = ["services/api/app/socai2/model_protocol.py", "services/api/tests/test_socai2_model_protocol.py",
        "services/api/tests/test_socai2_deepseek_union_schema.py", "services/api/tests/test_socai2_alert_basic_executor.py",
        "services/api/tests/test_socai2_baseline_executor.py", "docs/operations/verify_socai2_store_20261103.py",
        Path(__file__).relative_to(ROOT).as_posix()]
    result = {"status": "local_compatibility_fix_verified_live_provider_check_pending", "date": "2026-11-04",
        "root_cause_evidence": "docs/operations/socai2-schema-probe-m3-20261104.json",
        "change": "DeepSeek wire only: inline local refs in anyOf, retain all constraints; canonical and other protocols unchanged",
        "pure_checks": {"existing_related_passed": 33, "new_passed": 11, "different_passed": 44,
            "evidence_type": "tool output transcription, not saved raw process logs",
            "initial_ruff": "one new test import formatting finding, fixed; no behavior change"},
        "postgres_receipts": {p: sha(ROOT / p) for p in pg_paths}, "postgres_observations": pg,
        "candidate": {**prep, "path": DIRECTORY.relative_to(ROOT).as_posix(), "changed_from_n10": changed,
            "archive_hashes_modes_and_application_bytes_verified": True, "private_filename_scan_passed": True},
        "code_and_test_sha256": {p: sha(ROOT / p) for p in files},
        "m3_original_evidence_unchanged": True, "real_model_calls_after_m3": 0,
        "ddl_changes": 0, "deployments": 0, "live_last_verified": "n9",
        "limits": ["new explicit-type anyOf form not yet tested with real provider",
            "PG model and lake responses substituted", "no claim of model accuracy improvement",
            "full real C-H-second C, final review and archive remain open"]}
    out = ROOT / "docs/operations/socai2-deepseek-union-fix-20261104.json"
    with out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"receipt": str(out), "candidate_files": prep["files"], "application_files": prep["application_files"],
        "changed_from_n10": len(changed), "pure_checks": 44, "postgres_methods": 2, "deployed": False}))


if __name__ == "__main__":
    main()
