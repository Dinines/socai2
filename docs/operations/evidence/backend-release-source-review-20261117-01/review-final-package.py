"""Verify frozen candidate files against manifests and existing acceptance sources."""
import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E = ROOT / "docs/operations/evidence"
TARGET = E / "acceptance-release-20261117-01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    freeze_file = TARGET / "source-freeze-01.json"
    freeze = json.loads(freeze_file.read_text())
    proc = ROOT / ".local/processing-release/processing-20261117-r1"
    http = ROOT / ".local/http-release/acceptance-http-20261117-r1"
    pm, hm = [json.loads((p / "manifest.json").read_text()) for p in (proc, http)]
    assert sha(proc / "manifest.json") == freeze["processing"]["manifest_sha256"]
    assert sha(proc / "release.tar.gz") == freeze["processing"]["archive_sha256"]
    assert sha(http / "manifest.json") == freeze["http"]["manifest_sha256"]
    with tarfile.open(proc / "release.tar.gz") as archive:
        assert set(archive.getnames()) == set(pm["files"]) | {"manifest.json"}
        assert archive.extractfile("manifest.json").read() == (proc / "manifest.json").read_bytes()
        for name, row in pm["files"].items():
            value = archive.extractfile(name).read()
            assert hashlib.sha256(value).hexdigest() == row["sha256"]
            assert len(value) == row["bytes"]
    assert all(sha(http / name) == value for name, value in hm["files"].items())
    shared = [name for name in pm["files"] if name.startswith("app/")]
    assert all(pm["files"][name]["sha256"] == hm["files"][name] for name in shared)

    prior = E / "backend-release-source-review-20261117-01"
    source_proc = json.loads((prior / "current-processing-manifest.json").read_text())
    source_http = json.loads((prior / "current-http-manifest.json").read_text())
    http_targets = json.loads((prior / "current-http-targets.json").read_text())
    assert {name: row["sha256"] for name, row in pm["files"].items()} == source_proc
    metadata_changes = []
    for source, value in source_http.items():
        target = http_targets[source]
        if hm["files"][target] == value:
            continue
        assert target == "contract/openapi.json"
        before, after = json.loads((ROOT / source).read_text()), json.loads((http / target).read_text())
        assert after["info"]["version"] == hm["release"]
        metadata_changes.append({"target": target, "changed_path": "$.info.version",
            "before": before["info"]["version"], "after": after["info"]["version"]})
        after["info"]["version"] = before["info"]["version"]
        assert before == after

    accepted_file = E / "acceptance-append-20261117-02/source-freeze-02.json"
    accepted = json.loads(accepted_file.read_text())["files"]
    matched = {}
    for source, value in accepted.items():
        if source.startswith("services/api/"):
            name = source.removeprefix("services/api/")
            assert hm["files"][name] == value
            if name.startswith("app/"):
                assert pm["files"][name]["sha256"] == value
        elif source.startswith("services/fusion/app/"):
            name = "smoke-fusion/app/" + source.removeprefix("services/fusion/app/")
            assert pm["files"][name]["sha256"] == value
        else:
            continue
        matched[source] = value
    c1 = json.loads((E / "acceptance-case-continuation-20261117-01/core-fix-scope.json").read_text())
    assert matched[c1["source"]] == c1["sha256"]
    d5 = "app/socai2/case_deep_delivery.py"
    assert pm["files"][d5]["sha256"] == hm["files"][d5]
    old_policy = json.loads((ROOT / ".local/processing-release/processing-20261116-r4/manifest.json").read_text())["policy_sha256"]
    assert pm["policy_sha256"] == old_policy
    config_hashes = {}
    for name, value in freeze["config_files"].items():
        actual = sha(ROOT / name)
        assert actual == value
        config_hashes[name] = actual
    openapi = json.loads((ROOT / "deploy/aisoc21/acceptance-release-20261117-01/contract/openapi.json").read_text())
    operations = sum(method in {"get", "post", "put", "patch", "delete", "head", "options"}
                     for item in openapi["paths"].values() for method in item)
    assert operations == 80
    result = {"observed_at": datetime.now(timezone.utc).isoformat(), "status": "passed_for_frozen_core_sources_normal_chain",
        "source_freeze": str(freeze_file.relative_to(ROOT)), "source_freeze_sha256": sha(freeze_file),
        "processing": {"release": pm["release"], "manifest_sha256": sha(proc / "manifest.json"),
            "archive_sha256": sha(proc / "release.tar.gz"), "verified_files": len(pm["files"])},
        "http": {"release": hm["release"], "manifest_sha256": sha(http / "manifest.json"),
            "verified_files": len(hm["files"]), "source_files_matched_exactly": len(source_http) - len(metadata_changes),
            "release_metadata_changes": metadata_changes},
        "shared_runtime_core_files": len(shared), "shared_core_same_sha": True,
        "accepted_3c2": {"source_freeze": str(accepted_file.relative_to(ROOT)), "sha256": sha(accepted_file),
            "api_fusion_files_matched": len(matched), "normal_chain_evidence": "acceptance-append-20261117-02/final-validation.json",
            "independent_review": "test-acceptance-append-20261117-01/independent-review-04.json"},
        "C1_verified_3b_fix_matches": True, "new_Deep_receiver_in_both_packages": True,
        "policy_same_as_r4": True, "policy_sha256": pm["policy_sha256"], "operations": operations,
        "frozen_config_hashes": config_hashes, "new_model_calls": 0, "new_business_runs": 0, "deployments": 0,
        "D5a_exception_acceptance": "incomplete_not_claimed",
        "not_covered": ["D5a valid truncated answer -> actual PG/C6 persistence chain", "D5b/c", "new image startup/runtime readback",
            "new Kafka business acceptance", "viewer/acceptance UI implementation", "whole-change independent ending audit"],
        "reviewer_note": "Source mapping review by a D5a implementation participant; not an independent whole-change audit."}
    with (TARGET / "core-package-review-01.json").open("x") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps({k: result[k] for k in ("status", "shared_runtime_core_files", "operations", "D5a_exception_acceptance")}))


if __name__ == "__main__":
    main()
