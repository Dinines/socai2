"""Local-only receipt: closed batch evidence, fixed inputs and existing PG checks."""
import hashlib
import json
from pathlib import Path

from app.socai2.baseline_store import encoded
from app.socai2.incident_diagnosis_contract import build
from test_socai2_compact_model_input import snapshot

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((ROOT / path).read_text("utf-8"))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    old_summary = read("docs/operations/socai2-model-evaluation-m2-20261104.json")
    for group in ("evidence_sha256", "script_sha256"):
        for path, expected in old_summary[group].items():
            assert sha(path) == expected, path
    paths = [
        "docs/operations/evidence/socai2-alert-basic-20261104/20261104T145214/receipt.json",
        "docs/operations/evidence/socai2-incident-diagnosis-20261104/20261104T145315/receipt.json",
        "docs/operations/evidence/socai2-executor-20261103/20261104T145500/receipt.json"]
    checks = []
    for path in paths:
        receipt = read(path)
        assert receipt["database"] == "socai2_schema_review_20261103_a1" and receipt["synthetic_only"]
        assert all(row["passed"] for row in receipt["observations"])
        checks.extend(receipt["observations"])
    packet = next(p for p in read("docs/operations/evidence/socai2-model-comparison-20261104/m2/plan-and-packets.json")["packets"]
                  if p["id"] == "I-current")
    db = snapshot("r6")
    run = next(r for r in db["runs"] if r["kind"] == "incident_diagnosis")
    source = next(a["content_json"] for a in db["artifacts"] if a["id"] == run["input_artifact_id"])
    assert hashlib.sha256(encoded(source)).hexdigest() == packet["source_sha256"]
    messages, _, data = build(source, run["input_artifact_id"])
    def entries(items):
        return {(tuple(i["alert_ids"]), i["field"], i["role"]): i["value"] for i in items}
    old, new = entries(packet["data"]["items"]), entries(data["items"])
    assert all(old[k] == new[k] for k in old.keys() & new.keys())
    removed = [{"alert_ids": list(k[0]), "field": k[1], "role": k[2]} for k in old.keys() - new.keys()]
    added = [{"alert_ids": list(k[0]), "field": k[1], "role": k[2]} for k in new.keys() - old.keys()]
    files = ["services/api/app/socai2/" + name for name in (
        "model_errors.py", "baseline_analysis_model.py", "alert_basic_executor.py", "incident_diagnosis_executor.py",
        "baseline_analysis.py", "baseline_reasoning.py", "incident_diagnosis_contract.py")]
    files += ["services/api/tests/test_socai2_" + name + ".py" for name in (
        "model_errors", "model_protocol", "compact_model_input", "stage_quality", "alert_basic_executor",
        "incident_diagnosis_executor", "baseline_executor")]
    files += ["docs/operations/verify_socai2_store_20261103.py", str(Path(__file__).relative_to(ROOT)).replace("\\", "/")]
    result = {"status": "local_fixes_verified_not_deployed", "date": "2026-11-04",
        "evaluation_policy": {"misclassification": "confirmed benign versus malicious reversal only",
            "needs_review": "acceptable abstention; not misclassification or definite correctness",
            "m1_m2_ground_truth": "not independently established; evaluate unsupported definite judgment instead"},
        "closed_m2_evidence_and_scripts_unchanged": True, "postgres_receipts": {p: sha(p) for p in paths},
        "postgres_observations": checks,
        "pure_checks": {"different_latest_passed": 43, "first_combined_passed": 41,
            "final_error_module_passed": 10, "other_unchanged_passes_reused": 33,
            "new_cases": 13, "evidence_type": "tool output transcription; not a saved raw process log",
            "initial_compact_failure": "17 passed/1 failed: generic instruction phrase was not the existing raw-JSON guard fixture; corrected fixture, guard unchanged",
            "initial_ruff": "two import ordering findings corrected; latest 13-file check passed"},
        "incident_fixed_input": {"same_source_sha256": packet["source_sha256"],
            "old_bytes": len(packet["messages"][1]["content"].encode()), "new_bytes": len(messages[1]["content"].encode()),
            "limit_bytes": 8192, "old_detection_bundles": 1, "new_detection_bundles": 2,
            "old_items": len(old), "new_items": len(new), "shared_values_unchanged": True,
            "omissions": data["omissions"], "removed_optional_items": sorted(removed, key=lambda v: (v["alert_ids"], v["field"])),
            "added_items": sorted(added, key=lambda v: (v["alert_ids"], v["field"]))},
        "code_and_test_sha256": {p: sha(p) for p in files}, "ddl_changes": 0,
        "real_model_calls": 0, "real_lake_calls": 0, "deployments": 0,
        "live_last_verified": "n9", "n10_candidate": "unchanged frozen candidate, not uploaded or deployed",
        "unresolved": ["DeepSeek A HTTP400 exact parameter", "small C3 HTTP408 timeout owner",
            "unsupported judgment and narrative scope semantics", "full real C-H-second C acceptance", "final audit and archive"]}
    out = ROOT / "docs/operations/socai2-m2-followup-fix-20261104.json"
    with out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"receipt": str(out), "pure_latest": 43, "postgres_methods": len(checks)-3,
        "input_bytes": result["incident_fixed_input"]["new_bytes"], "closed_m2_unchanged": True}))


if __name__ == "__main__":
    main()
