"""Freeze local followup fix evidence; PG unavailability is not acceptance."""
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/operations/socai2-followup-fix-20261105.json"
DIRECTORY = ROOT / ".local/releases/next-20261104-n12"
EVIDENCE = ROOT / "docs/operations/evidence/socai2-followup-fix-20261105"


def read(path):
    return json.loads(path.read_text("utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise RuntimeError("fixed receipt already exists")
    manifest, prep = read(DIRECTORY / "manifest.json"), read(DIRECTORY / "preparation.json")
    assert sha(DIRECTORY / "candidate.tar") == prep["archive_sha256"]
    assert sha(DIRECTORY / "manifest.json") == prep["manifest_sha256"]
    with tarfile.open(DIRECTORY / "candidate.tar") as archive:
        assert len(archive.getmembers()) == len(manifest["files"]) + 1
        for entry in archive:
            assert entry.isfile() and entry.mode == 0o644 and not entry.name.startswith("/") and ".." not in Path(entry.name).parts
            assert not any(v in entry.name.lower() for v in ("dsapi", ".env", "id_ed25519", "id_rsa", ".pem"))
            body = archive.extractfile(entry).read()
            if entry.name == "manifest.json":
                assert body == (DIRECTORY / entry.name).read_bytes()
            else:
                assert hashlib.sha256(body).hexdigest() == manifest["files"][entry.name]["sha256"]
                if entry.name.startswith("app/"):
                    assert body == (ROOT / "services/api" / entry.name).read_bytes()
    original = ROOT / ".local/releases/next-20261104-n11"
    old = read(original / "manifest.json")["files"]
    assert sha(original / "candidate.tar") == "7f0dfd8f6d0943badb6191e12455a86c903bd755f9f2b74f9186c579004dfd0a"
    assert sha(original / "manifest.json") == "8329b0505cc23f53b2474ffc80eb6585cac1e22a66d35ff29393b674abf4f29a"
    changed = sorted(k for k, v in manifest["files"].items() if old.get(k) != v)
    expected = ["app/socai2/" + name for name in ["baseline_analysis_contract.py", "baseline_delivery.py",
        "baseline_delivery_contract.py", "baseline_followup_projection.py", "baseline_reanalysis.py",
        "baseline_model_view.py", "alert_basic_contract.py", "incident_diagnosis_contract.py"]] + ["compose.next-service.yml"]
    assert changed == sorted(expected), changed
    audit_path = ROOT / "docs/operations/evidence/socai2-semantic-boundaries-20261105/local-audit.json"
    audit = read(audit_path)
    assert all(sha(ROOT / p) == h for p, h in audit["evidence_sha256"].items())
    m3 = read(ROOT / "docs/operations/socai2-schema-probe-m3-20261104.json")
    assert all(sha(ROOT / p) == h for p, h in m3["evidence_sha256"].items())
    logs = {p.name: p.read_text("utf-8") for p in EVIDENCE.glob("*.txt")}
    assert "1 failed, 23 passed" in logs["pure-initial.txt"]
    assert "19 passed" in logs["pure-targeted.txt"] and "2 passed" in logs["pure-budget-guard.txt"]
    assert "isolated database administrative statement failed" in logs["pg-initial.txt"]
    files = [ROOT / "services/api" / p for p in changed if p.startswith("app/")]
    files += [ROOT / "services/api/tests" / p for p in ["test_socai2_followup_scope.py", "test_socai2_baseline_executor.py",
        "test_socai2_compact_model_input.py", "test_socai2_m1_contract_fixes.py"]]
    files += [ROOT / "docs/operations/verify_socai2_store_20261103.py", Path(__file__), audit_path]
    result = {"date": "2026-11-05", "status": "local_fixes_verified_pg_and_real_model_acceptance_pending",
        "changes": ["followup objects restricted to selected frozen members",
            "C6 original plan artifact and index join with required plan content",
            "latest reanalysis proposals not assigned original execution status",
            "shared action/outcome and endpoint semantics; no keyword truth gate"],
        "pure_checks": {"latest_distinct_passes": 44, "initial": "23 passed, 1 frozen-fixture assignment failed",
            "targeted": "fixed fixture plus 18 compact-input checks passed", "additional_guard_budget": 2,
            "scope": "local parser, projection, budgets and input retention; not model quality"},
        "postgres": {"database": "socai2_schema_review_20261103_a1", "selected_methods": 5,
            "new_methods": 2, "existing_regressions": 3, "started_methods": 0,
            "status": "preflight_failed_before_role_or_fixture_creation",
            "direct_ssh_diagnostic": "192.168.1.21:22 connection timed out; not an approval rejection"},
        "candidate": {**prep, "directory": str(DIRECTORY.relative_to(ROOT)).replace("\\", "/"),
            "changed_from_n11": changed, "byte_hash_mode_and_source_verified": True, "old_n11_unchanged": True},
        "m2_original_files_unchanged": len(audit["evidence_sha256"]), "m3_evidence_unchanged": True,
        "m4": "fixed packet untouched; additional one-call authorization still pending",
        "evidence_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in sorted(EVIDENCE.iterdir()) if p.is_file()},
        "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in files},
        "static_checks": "Ruff and OpenSpec strict and git diff --check passed",
        "new_real_model_calls": 0, "deployments": 0, "ddl_changes": 0,
        "remaining": ["five isolated PG methods after connectivity recovers", "m4 single-call schema acceptance after explicit authorization",
            "new real A/I/C/H/second-C batch with semantic review", "independent final audit and archive"],
    }
    with OUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"receipt": str(OUT.relative_to(ROOT)), "files": prep["files"], "application_files": prep["application_files"],
        "changed_paths": len(changed), "pure_passes": 44, "pg_methods_started": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
