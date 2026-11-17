"""Read-only source comparison; writes only this review's evidence files."""
import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text())


def differences(expected, actual):
    return [{"path": name, "before": expected.get(name), "current": actual.get(name),
             "kind": "added" if name not in expected else "missing" if name not in actual else "changed"}
            for name in sorted(set(expected) | set(actual)) if expected.get(name) != actual.get(name)]


def current_http(profile):
    mapping = dict(profile["patches"])
    for source, target in profile["complete_packages"].items():
        for name in [k for k in mapping if k.startswith(source + "/")]:
            del mapping[name]
        for path in sorted((ROOT / source).rglob("*")):
            parts = path.relative_to(ROOT / source).parts
            if not path.is_file() or any(p.startswith(".") or p == "__pycache__" for p in parts):
                continue
            if path.suffix in {".pyc", ".pyo"}:
                continue
            assert not path.is_symlink()
            mapping[str(path.relative_to(ROOT))] = str(Path(target).joinpath(*parts))
    return mapping, {name: sha((ROOT / name).read_bytes()) for name in mapping}


def main():
    evidence = "docs/operations/evidence/"
    freeze_path = evidence + "acceptance-append-20261117-02/source-freeze-02.json"
    freeze = read(freeze_path)["files"]
    frozen_now = {f: sha((ROOT / f).read_bytes()) for f in freeze if (ROOT / f).exists()}
    proc = ROOT / ".local/processing-release/processing-20261116-r4"
    manifest = json.loads((proc / "manifest.json").read_text())
    expected_proc = {k: v["sha256"] for k, v in manifest["files"].items()}
    with tarfile.open(proc / "release.tar.gz") as archive:
        archived_proc = {k: sha(archive.extractfile(k).read()) for k in expected_proc}
        assert archived_proc == expected_proc
        assert archive.extractfile("manifest.json").read() == (proc / "manifest.json").read_bytes()
    sums = {line.split()[1]: line.split()[0] for line in (proc / "SHA256SUMS").read_text().splitlines()}
    assert all(sha((proc / name).read_bytes()) == value for name, value in sums.items())
    proc_mapping = {}
    for source, target in (("services/api/app", "app"), ("services/fusion/app", "smoke-fusion/app")):
        for path in sorted((ROOT / source).rglob("*")):
            if path.is_file() and path.suffix in {".py", ".json"}:
                parts = path.relative_to(ROOT / source).parts
                if not any(p.startswith(".") or p == "__pycache__" for p in parts):
                    proc_mapping[str(Path(target).joinpath(*parts))] = str(path.relative_to(ROOT))
    for name in ("processing_job.py", "production_ingress.py", "production_projection.py", "projection_config.py", "build_processing_image.py"):
        proc_mapping[name] = "deploy/aisoc21/" + name
    proc_mapping.update({"Dockerfile": "deploy/aisoc21/processing.Dockerfile",
        "investigation-policy.toml": "deploy/local-investigation/investigation-policy-case-v1.toml"})
    current_proc = {target: sha((ROOT / source).read_bytes()) for target, source in proc_mapping.items()}

    http_root = ROOT / ".local/http-release/streaming-http-20261116-r4"
    http_manifest = json.loads((http_root / "manifest.json").read_text())
    archived_http = {f: sha((http_root / f).read_bytes()) for f in http_manifest["files"]}
    assert archived_http == http_manifest["files"]
    profile = read("deploy/aisoc21/streaming-release-20261116-04/http-profile.json")
    assert all(archived_http[target] == profile["expected_source_hashes"][source]
               for source, target in profile["patches"].items())
    http_mapping, current_http_hashes = current_http(profile)
    c1 = read(evidence + "acceptance-case-continuation-20261117-01/core-fix-scope.json")
    assert current_http_hashes[c1["source"]] == c1["sha256"] == freeze[c1["source"]]
    d5 = ["services/api/app/socai2/" + name for name in
          ("case_deep_delivery.py", "baseline_deep.py", "baseline_deep_contract.py", "baseline_reasoning.py")]
    d5_proof = read(evidence + "test-deep-unit-continuation-d5a-20261117-01/receiver-01.json")
    assert all(current_http_hashes[f] == freeze[f] for f in d5)
    assert current_http_hashes[d5[0]] == d5_proof["code_sha256"]["case_deep_delivery.py"]

    freeze_diff = differences(freeze, frozen_now)
    runtime_freeze = read(evidence + "acceptance-docker-20261117-01/runtime-freeze-02/manifest.json")
    tool_freeze = {row["path"]: row["sha256"] for row in runtime_freeze["files"]}
    final_freeze = read(evidence + "acceptance-append-20261117-02/source-freeze-final.json")["files"]
    tool_evidence = [{"path": r["path"], "matches_3d_runtime_freeze": tool_freeze.get(r["path"]) == r["current"],
        "matches_3c2_final_freeze": final_freeze.get(r["path"]) == r["current"]} for r in freeze_diff]
    backend_diff = [r for r in freeze_diff if r["path"].startswith(("services/api/", "services/fusion/"))]
    proc_diff = differences(expected_proc, current_proc)
    http_diff = differences(profile["expected_source_hashes"], current_http_hashes)
    normal = read(evidence + "acceptance-append-20261117-02/final-validation.json")
    independent = read(evidence + "test-acceptance-append-20261117-01/independent-review-04.json")
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(), "status": "source_comparison_complete",
        "source_only": True, "new_model_calls": 0, "new_business_runs": 0, "deployments": 0,
        "worktree_changes": "none; only this review directory is written",
        "live_21_readback": "not repeated; compare archived r4 manifests tied to deployment-ready.json",
        "r4_processing_archive": {"path": str(proc.relative_to(ROOT)), "verified_files": len(archived_proc), **sums},
        "r4_http_archive": {"path": str(http_root.relative_to(ROOT)), "verified_files": len(archived_http),
            "manifest_sha256": sha((http_root / "manifest.json").read_bytes()),
            "runtime_profile_entries_verified": len(profile["patches"])},
        "processing_current_vs_r4": proc_diff, "http_current_vs_r4": http_diff,
        "processing_current_files": len(current_proc), "http_current_files": len(current_http_hashes),
        "freeze02": {"path": freeze_path, "sha256": sha((ROOT / freeze_path).read_bytes()), "files": len(freeze),
            "current_differences": freeze_diff, "backend_current_differences": backend_diff,
            "covered_api_and_fusion_files": sum(f.startswith(("services/api/", "services/fusion/")) for f in freeze)},
        "later_test_tool_differences": tool_evidence,
        "C1": {"path": c1["source"], "sha256": c1["sha256"], "same_3b_and_3c2": True},
        "D5a": {"same_3c2_sources": True, "files": {f: current_http_hashes[f] for f in d5},
            "normal_path_evidence": evidence + "acceptance-append-20261117-02/README.md",
            "exception_target_complete": False,
            "remaining": "valid partial Deep answer -> actual PG/C6 chain and independent stored-output review; D5b/c remain unimplemented"},
        "existing_acceptance": {"status": normal["status"], "runtime_source_freeze": normal["runtime_source_freeze"],
            "model_requests": normal["model_requests"], "total_tokens": normal["total_tokens"],
            "finish_reasons": normal["model_finish_reasons"], "independent_review_status": independent.get("status")},
        "recommendation": "Freeze the current complete backend matching 3c2, include the added Deep receiver in both processing/HTTP manifests, disclose remaining D5a boundaries; do not split/revert the worktree.",
        "alternative": "r4 archives + exactly the verified C1 file is reconstructable but is a new composition, not the 3c2 tested complete source; requires candidate-specific checks before deployment.",
    }
    assert not backend_diff
    assert all(row["matches_3d_runtime_freeze"] or row["matches_3c2_final_freeze"] for row in tool_evidence)
    for f, value in frozen_now.items():
        assert sha((ROOT / f).read_bytes()) == value, "source_changed_during_review:" + f
    for name, value in (("review.json", report), ("current-processing-manifest.json", current_proc),
                        ("current-http-manifest.json", current_http_hashes), ("current-http-targets.json", http_mapping)):
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "processing_differences": len(proc_diff),
        "http_differences": len(http_diff), "freeze02_backend_differences": len(backend_diff),
        "r4_processing_archive_files_verified": len(archived_proc), "r4_http_archive_files_verified": len(archived_http)}))


if __name__ == "__main__":
    main()
