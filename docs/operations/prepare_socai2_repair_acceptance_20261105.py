"""Freeze two new bounded acceptance cards against an immutable n15 candidate.

Local preparation only. No upload, deployment, database or model invocation.
"""
import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[2]
BATCH = "repair-k5"
OUT = ROOT / "docs/operations/evidence/investigation-repair-20261105" / BATCH


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def uid(label):
    return str(uuid5(NAMESPACE_URL, "socai2-kafka-" + BATCH + "-20261105:" + label))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    assert candidate.is_relative_to(ROOT / ".local/releases") and candidate.name.startswith("next-")
    manifest = json.loads((candidate / "manifest.json").read_text())
    for name, item in manifest["files"].items():
        path = candidate / name
        assert path.resolve().is_relative_to(candidate) and not path.is_symlink()
        assert sha(path) == item["sha256"] and path.stat().st_size == item["bytes"]
    assert '"socai2.baseline-executor.v2"' in (candidate / "app/socai2/baseline_contracts.py").read_text()
    start = (candidate / "app/socai2/case_service.py").read_text()
    assert "max_tokens=48000" in start and "socai2.manual-http.v2" in start
    source = ROOT / "docs/operations/evidence/socai2-kafka-chain-20261105/k2/plan.json"
    old = json.loads(source.read_text())
    base = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=2)
    cases = []
    for offset, backend in enumerate(("deepseek", "small")):
        original = next(case for case in old["cases"] if case["key"] == backend + "-maintenance")
        copied = json.dumps(original)
        replacements = {original["host"]: BATCH + "-endpoint-" + str(offset), "k2-" + backend: BATCH + "-" + backend}
        old_base = datetime.fromisoformat(original["alerts"][0]["event_time"])
        new_base = base + timedelta(minutes=offset * 40)
        for value in (original["window_start"], original["window_end"], *[a["event_time"] for a in original["alerts"]]):
            replacements[value] = (new_base + (datetime.fromisoformat(value) - old_base)).isoformat()
        for index, alert in enumerate(original["alerts"]):
            replacements[alert["source_alert_id"]] = uid(backend + "-alert-" + str(index))
            replacements[alert["external_id"]] = uid(backend + "-vendor-" + str(index))
            replacements[alert["source_event_ids"][0]] = uid(backend + "-event-" + str(index))
        for old_value, new_value in replacements.items():
            copied = copied.replace(old_value, new_value)
        case = json.loads(copied)
        case["max_model_calls"] = 11
        case["max_runs"] = 5
        cases.append(case)
    plan = {"batch": BATCH, "tenant_id": old["tenant_id"], "release": candidate.name,
        "image": manifest["image"], "candidate_manifest_sha256": sha(candidate / "manifest.json"),
        "candidate_files": {name: item["sha256"] for name, item in manifest["files"].items()},
        "source_fixture_sha256": sha(source), "new_alerts": 4, "new_incidents": 2, "new_cases": 2,
        "lake_events": 4, "max_runs": 10, "max_model_calls": 22, "retries": 0,
        "baseline_limits": {"max_tokens": 48000, "max_model_calls": 4, "max_tool_calls": 4,
            "deadline_seconds": 120, "max_output_tokens": 3000, "executor_version": "socai2.baseline-executor.v2",
            "policy_version": "socai2.manual-http.v2"},
        "ai_limits": "Existing A/I policy unchanged: each stage at most one model call",
        "initial_analysis_schema": "socai2.baseline-analysis.v2",
        "final_reanalysis_proposal_schema": "socai2.baseline-analysis.v1",
        "topic_prefix": "socai2.validation.repair-k5.20261105", "group": "socai2-validation-repair-k5-20261105",
        "stages": ["Kafka/Fusion", "A0", "A1", "I", "first C", "root semantic review", "H", "second C"],
        "gate": "No mutation before core-review.json approves this manifest; no H/second C before per-card semantic review",
        "oracle_not_sent_to_models": old["oracle_not_sent_to_models"]["maintenance"],
        "semantic_checks": ["process_start success does not prove script completion or authorization",
            "TCP/443 successful connection does not prove HTTPS, process attribution or exfiltration",
            "known destination must not be described as absent", "labels and fixture identity are not authorization",
            "H authorizes only A0 process task within its explicit window, not A1 traffic or completion",
            "second C must consume H revision and valid first C comparison; trace both to persisted artifacts"],
        "quality_rule": "benign/malicious reversal counts as misclassification; needs_review is acceptable abstention, not correct certainty",
        "scope": "One maintenance pair per backend; not population accuracy or all-scenario quality validation",
        "cases": cases}
    OUT.mkdir(parents=True, exist_ok=False)
    files = {"plan.json": json.dumps(plan, ensure_ascii=False, indent=2) + "\n"}
    for name in ("repair_acceptance_remote_20261105.py", "repair_migration_remote_20261105.py",
                 "repair_page_proxy_20261105.py", "kafka_chain_child.py"):
        files[name] = (ROOT / "deploy/aisoc21" / name).read_text()
    for name, value in files.items():
        (OUT / name).write_text(value)
    (OUT / "manifest.json").write_text(json.dumps({name: sha(OUT / name) for name in files}, indent=2) + "\n")
    print(json.dumps({"packet": str(OUT), "plan_sha256": sha(OUT / "plan.json"), "max_model_calls": 22,
        "uploaded": False, "candidate_manifest_sha256": plan["candidate_manifest_sha256"]}))


if __name__ == "__main__":
    main()
